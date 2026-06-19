#!/usr/bin/env dash
# Render one snapshot of the spectator pages.
#
# Usage: render.sh <db_path> <out_dir> <token>
#
# Reads the cloud-twin SQLite and writes a fresh
#   <out_dir>/tokens/<token>/{schedule.html, recent.html, health.json}
# tree, then atomically swings the <out_dir>/current symlink to it.
#
# Exits non-zero on DB unreachable or sqlite errors — entrypoint logs and
# keeps the previous output in place.

set -eu

DB="$1"
OUT="$2"
TOKEN="$3"

SELF_DIR=$(cd "$(dirname "$0")" && pwd)

DEST_DIR="$OUT/tokens/$TOKEN"
TMP_DIR=$(mktemp -d -p "$OUT/tokens" ".tmp.XXXXXX")
trap 'rm -rf "$TMP_DIR"' EXIT INT TERM

GEN_AT=$(TZ=America/Edmonton date "+%m-%d-%Y %H:%M:%S")
DB_MTIME="(missing)"
[ -f "$DB" ] && DB_MTIME=$(TZ=America/Edmonton date -r "$DB" "+%m-%d-%Y %H:%M:%S" 2>/dev/null || echo "(unknown)")

# Content version for the browser version-bump refresh. We key it on the DB
# mtime (the source of the content), NOT wall-clock, so the periodic "floor"
# render of an idle DB does NOT bump the version — spectators only reload when
# the race data actually changed. Fallback to epoch if the DB is absent
# (pre-event). Published to version.txt and embedded as {{VERSION}} in the
# auto-refreshing pages. See docs/PUBLIC_STATS.md.
VERSION=$([ -f "$DB" ] && stat -c %Y "$DB" 2>/dev/null || date +%s)

# ---- Splash gate -------------------------------------------------------------
# Operator-toggled "race starting soon" landing page. The gate is a single flag
# file at the output volume ROOT (NOT under tokens/, so render never touches it
# and it survives every pass; it's event-wide, independent of the token). Its
# presence = gate ON; its contents = the headline message (empty -> default).
# Toggled via `scripts/derbyvps.sh splash {on|off}`. When ON we render the
# splash into the schedule + recent slots and suffix the content version with
# "-splash" so the browser version-bump poll reloads every open phone — onto the
# splash when flipped on, back to the live page when flipped off. See
# docs/PUBLIC_STATS.md.
SPLASH_ON=0
SPLASH_MSG=""
if [ -f "$OUT/splash.flag" ]; then
    SPLASH_ON=1
    SPLASH_MSG=$(cat "$OUT/splash.flag" 2>/dev/null || true)
    [ -n "$SPLASH_MSG" ] || SPLASH_MSG="Race starting soon — all carts must be checked in"
    VERSION="${VERSION}-splash"
fi

# Helper: run a single SQL statement, return TSV. Empty on missing DB.
sql() {
    if [ ! -f "$DB" ]; then return 0; fi
    # Open via URI with immutable=1 so SQLite skips WAL/SHM sidecar probing.
    # The bind-mount is RO and the Pi pushes WAL-mode DBs; without immutable
    # we get SQLITE_CANTOPEN (14) on every query. Safe because cloud-sync
    # replaces the file atomically — we're only ever reading a stable snapshot.
    sqlite3 -separator "	" "file:${DB}?immutable=1" "$1" 2>/dev/null || return 1
}

# Helper: escape <, >, & for safe HTML interpolation.
esc() {
    printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}

# Helper: escape characters that have special meaning in a sed replacement
# string — backslash, the '|' delimiter we use, and '&' (the match back-ref).
# Without this, an HTML-escaped value like "A&amp;B" coming back through
# `s|{{KEY}}|...&amp;...|` would expand the '&' to the matched LHS instead
# of staying literal.
sed_subst_escape() {
    printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'
}

# ---- 1. Current racing state -------------------------------------------------
ROUND_ID=""
HEAT_NOW=""
STATE=""
CLASS_ID=""
if [ -f "$DB" ]; then
    while IFS='	' read -r k v; do
        case "$k" in
            RoundID) ROUND_ID="$v" ;;
            Heat) HEAT_NOW="$v" ;;
            NowRacingState) STATE="$v" ;;
            ClassID) CLASS_ID="$v" ;;
        esac
    done <<EOF
$(sql "SELECT itemkey, itemvalue FROM RaceInfo WHERE itemkey IN ('RoundID','Heat','NowRacingState','ClassID');" || true)
EOF
fi

# ---- 2. Round metadata -------------------------------------------------------
# Join Classes so the header chip can read e.g. "Ages 6-8, 1 Preliminary"
# instead of just the round name.
CLASS_NAME=""
ROUND_NAME=""
ROUND_NUM=""
if [ -n "$ROUND_ID" ] && [ "$ROUND_ID" != "0" ]; then
    while IFS='	' read -r cls rname rnum; do
        CLASS_NAME="$cls"
        ROUND_NAME="$rname"
        ROUND_NUM="$rnum"
    done <<EOF
$(sql "SELECT COALESCE(c.class,''), COALESCE(r.roundname,''), r.round
         FROM Rounds r
         LEFT JOIN Classes c ON r.classid = c.classid
        WHERE r.roundid = $ROUND_ID;" || true)
EOF
fi

ROUND_DISPLAY=""
if [ -n "$ROUND_NAME" ]; then
    ROUND_DISPLAY="$(esc "$ROUND_NAME")"
elif [ -n "$ROUND_NUM" ]; then
    ROUND_DISPLAY="Round $(esc "$ROUND_NUM")"
fi
if [ -n "$CLASS_NAME" ] && [ -n "$ROUND_DISPLAY" ]; then
    ROUND_DISPLAY="$(esc "$CLASS_NAME"), $ROUND_DISPLAY"
elif [ -n "$CLASS_NAME" ]; then
    ROUND_DISPLAY="$(esc "$CLASS_NAME")"
fi

# ---- 3. Schedule rows for current round --------------------------------------
SCHEDULE_ROWS=""
SCHEDULE_PLACEHOLDER=""

if [ -z "$ROUND_ID" ] || [ "$ROUND_ID" = "0" ]; then
    SCHEDULE_PLACEHOLDER='<tr><td colspan="5" class="empty">Awaiting race start.</td></tr>'
else
    # Build all rows in one awk pass. Status logic:
    #   completed IS NOT NULL → "done"  (show place + time)
    #   heat == HEAT_NOW       → "now"   (highlight row)
    #   else                   → "upcoming"
    SCHEDULE_ROWS=$(
        sql "SELECT rc.heat, rc.lane, reg.carnumber,
                    COALESCE(rc.finishtime, ''),
                    COALESCE(rc.finishplace, ''),
                    CASE WHEN rc.completed IS NULL OR rc.completed = '' THEN 0 ELSE 1 END
               FROM RaceChart rc
               JOIN RegistrationInfo reg ON reg.racerid = rc.racerid
              WHERE rc.roundid = $ROUND_ID
              ORDER BY rc.heat, rc.lane;" 2>/dev/null \
        | awk -F'\t' -v now="${HEAT_NOW:-0}" '
            BEGIN { prev_heat = "" }
            {
                heat=$1; lane=$2; pinny=$3; t=$4; place=$5; done=$6;
                # Trim history: once racing is underway, hide heats older than
                # the last two — keeps the schedule focused on "what is coming
                # up" while preserving a couple of recent rows for context.
                # If now is unset/0, fall through and show everything (pre-race).
                if (now+0 > 0 && heat+0 < now+0 - 2) next;
                # Zero-pad pinny to 4 digits ("9" -> "0009") so spectators
                # can find their kid with the browsers Ctrl+F at a glance.
                pinny_display = (pinny == "" ? "----" : sprintf("%04d", pinny));
                # Darker separator line on the first row of each heat group.
                sep = (prev_heat != "" && heat != prev_heat) ? " heat-sep" : "";
                prev_heat = heat;
                if (done == 1) {
                    status="done";
                    # Medal emoji for top-3 finishers — matches recent.html
                    # visual treatment so finished rows on the schedule are
                    # instantly recognizable.
                    if (place == "1")      medal = "🥇 ";
                    else if (place == "2") medal = "🥈 ";
                    else if (place == "3") medal = "🥉 ";
                    else                   medal = "";
                    label = (place != "" ? medal "#" place : "");
                    # Times are ~20s tracked to 0.1s; cap at 99.9 so a stray
                    # timer-error 3-digit reading cannot blow the column width.
                    tcap = (t+0 > 99.9 ? 99.9 : t+0);
                    timecell = (t != "" ? sprintf("%.1fs", tcap) : "");
                } else if (heat == now) {
                    status="now";
                    label = "← NOW";
                    timecell = "";
                } else {
                    status="up";
                    label = "";
                    timecell = "";
                }
                printf "<tr class=\"%s%s\"><td class=\"h\">%s</td><td class=\"l\">%s</td><td class=\"p\">%s</td><td class=\"r\">%s</td><td class=\"t\">%s</td></tr>\n",
                       status, sep, heat, lane, pinny_display, label, timecell;
            }'
    )
    if [ -z "$SCHEDULE_ROWS" ]; then
        SCHEDULE_PLACEHOLDER='<tr><td colspan="5" class="empty">No heats scheduled yet.</td></tr>'
    fi
fi

SCHEDULE_BODY="${SCHEDULE_ROWS:-$SCHEDULE_PLACEHOLDER}"

# ---- 4. Most recent completed heats (current round) -------------------------
RECENT_BODY=""
if [ -n "$ROUND_ID" ] && [ "$ROUND_ID" != "0" ]; then
    HEATS=$(sql "SELECT heat FROM RaceChart
                  WHERE roundid = $ROUND_ID
                    AND completed IS NOT NULL AND completed != ''
                  GROUP BY heat
                  ORDER BY MAX(completed) DESC
                  LIMIT 10;" 2>/dev/null || true)

    if [ -z "$HEATS" ]; then
        RECENT_BODY='<p class="empty">No completed heats yet.</p>'
    else
        for h in $HEATS; do
            ROWS=$(
                sql "SELECT rc.lane, reg.carnumber,
                            COALESCE(rc.finishplace, ''),
                            COALESCE(rc.finishtime, '')
                       FROM RaceChart rc
                       JOIN RegistrationInfo reg ON reg.racerid = rc.racerid
                      WHERE rc.roundid = $ROUND_ID AND rc.heat = $h
                      ORDER BY (CASE WHEN rc.finishplace IS NULL OR rc.finishplace = '' THEN 999 ELSE rc.finishplace END), rc.lane;" \
                | awk -F'\t' '
                    {
                        lane=$1; pinny=$2; place=$3; t=$4;
                        # Zero-pad pinny to 4 digits ("9" -> "0009"); see schedule note.
                        pinny_display = (pinny == "" ? "----" : sprintf("%04d", pinny));
                        placecell = (place != "" ? "#" place : "—");
                        # Times tracked to 0.1s, capped at 99.9 for column-width safety.
                        tcap = (t+0 > 99.9 ? 99.9 : t+0);
                        timecell  = (t != "" ? sprintf("%.1fs", tcap) : "—");
                        printf "<tr><td class=\"r\">%s</td><td class=\"l\">%s</td><td class=\"p\">%s</td><td class=\"t\">%s</td></tr>\n",
                               placecell, lane, pinny_display, timecell;
                    }'
            )
            RECENT_BODY="${RECENT_BODY}<section class=\"heat\"><h3>Heat ${h}</h3><table class=\"recent\"><thead><tr><th>Place</th><th>Lane</th><th>Pinny</th><th>Time</th></tr></thead><tbody>${ROWS}</tbody></table></section>"
        done
    fi
else
    RECENT_BODY='<p class="empty">Awaiting race start.</p>'
fi

# ---- 5. My Races: per-racer pages (persistent, cross-round) -----------------
# Pre-render one static HTML page at me/<XXXX>.html for EVERY registered racer
# (not just those in the current round), showing that racer's heats across ALL
# rounds of the event — preliminary through finals — grouped into a section per
# round. The page persists from before the racer's group starts (a "check back"
# state) through end of day (final times stay visible). Spectators reach these
# by entering their 4-digit pinny on the keypad page (template-myraces.html);
# unknown pinnies fall through to me/notfound.html via Caddy try_files. The
# whole surface stays static — no dynamic backend, no rate-limit module.
#
# Generated by 3 queries + ONE awk pass that splits per-racer body fragments to
# disk + a SQL-free shell loop that wraps each fragment in the template. This is
# O(racers) sed calls but only O(1) sqlite spawns, regardless of roster size.
#
# busybox awk note: the container's awk (Alpine, no gawk/mawk) keeps a file
# descriptor open per `print > file` target until close(). We rely on the
# query's `ORDER BY carnumber` to keep each racer's rows contiguous, open
# exactly one body file at a time, and close() it on carnumber change — so the
# open-FD count is always 1, immune to roster size.
ME_DIR="$TMP_DIR/me"
mkdir -p "$ME_DIR"
# Body fragments live OUTSIDE the published me/ tree so they are never served.
BODIES_DIR="$TMP_DIR/bodies"
mkdir -p "$BODIES_DIR"

# Shared header values (don't vary per racer) — sed-escaped once.
UPDATED_SUB=$(sed_subst_escape "$GEN_AT")

# ---- 5a. Body fragments for all racers, all rounds (single awk pass) --------
# NOW-highlight matches on roundid (not the round number, which repeats across
# classes) AND the current heat. DNF (finishtime sentinel 99.999) shows "DNF".
sql "SELECT reg.carnumber, r.round, r.roundid, COALESCE(r.roundname,''),
            rc.heat, rc.lane,
            COALESCE(rc.finishtime, ''),
            COALESCE(rc.finishplace, ''),
            CASE WHEN rc.completed IS NULL OR rc.completed = '' THEN 0 ELSE 1 END
       FROM RaceChart rc
       JOIN RegistrationInfo reg ON reg.racerid = rc.racerid
       JOIN Rounds r             ON r.roundid   = rc.roundid
      WHERE reg.carnumber IS NOT NULL AND reg.carnumber != ''
      ORDER BY reg.carnumber, r.round, rc.heat, rc.lane;" 2>/dev/null \
    | awk -F'\t' -v outdir="$BODIES_DIR" \
          -v cur_roundid="${ROUND_ID:-0}" -v cur_heat="${HEAT_NOW:-0}" '
        function flush_table() {
            if (in_table) { printf "</tbody></table></section>\n" > fn; in_table = 0 }
        }
        function flush_racer() {
            if (cur_car != "") {
                flush_table();
                if (rows == 0) printf "<p class=\"empty\">No heats recorded.</p>\n" > fn;
                close(fn);
            }
        }
        BEGIN { cur_car = ""; cur_round = ""; in_table = 0; fn = "" }
        {
            car=$1; round=$2; roundid=$3; rname=$4;
            heat=$5; lane=$6; t=$7; place=$8; done=$9;

            if (car != cur_car) {                    # new racer -> new file
                flush_racer();
                cur_car = car; cur_round = ""; rows = 0;
                fn = sprintf("%s/%04d.body", outdir, car);
            }
            if (round != cur_round) {                # new round section
                flush_table();
                cur_round = round;
                hdr = (rname != "" ? rname : "Round " round);
                printf "<section class=\"rnd\"><h3>%s</h3><table class=\"me\"><thead><tr><th>Heat</th><th>Lane</th><th>Status</th><th>Time</th></tr></thead><tbody>\n", hdr > fn;
                in_table = 1;
            }

            rows++;
            if (done == 1) {
                status = "done";
                if (t != "" && t+0 >= 99.99) {        # DNF sentinel (99.999)
                    label = "DNF"; timecell = "—";
                } else {
                    if (place == "1")      medal = "🥇 ";
                    else if (place == "2") medal = "🥈 ";
                    else if (place == "3") medal = "🥉 ";
                    else                   medal = "";
                    label = (place != "" ? medal "#" place : "finished");
                    tcap = (t+0 > 99.9 ? 99.9 : t+0);
                    timecell = (t != "" ? sprintf("%.1fs", tcap) : "—");
                }
            } else if (cur_roundid+0 > 0 && roundid+0 == cur_roundid+0 && heat+0 == cur_heat+0) {
                status = "now"; label = "← NOW"; timecell = "—";
            } else {
                status = "up"; label = "upcoming"; timecell = "—";
            }
            printf "<tr class=\"%s\"><td class=\"h\">%s</td><td class=\"l\">%s</td><td class=\"r\">%s</td><td class=\"t\">%s</td></tr>\n",
                   status, heat, lane, label, timecell > fn;
        }
        END { flush_racer() }' || true

# ---- 5b. The set of classes that have "started" racing ----------------------
# A group has started when any heat in its class is completed, OR its class is
# the currently-active racing class. Stored as a space-delimited set for cheap
# membership testing in the loop below.
STARTED_CLASSIDS=" $(sql "SELECT DISTINCT r.classid
                            FROM RaceChart rc
                            JOIN Rounds r ON r.roundid = rc.roundid
                           WHERE rc.completed IS NOT NULL AND rc.completed != '';" 2>/dev/null \
                       | tr '\n' ' ' || true)"
if [ -n "$CLASS_ID" ] && [ "$CLASS_ID" != "0" ]; then
    STARTED_CLASSIDS="$STARTED_CLASSIDS $CLASS_ID "
fi

# Reusable state-A / empty payload fragments (written once, reused per racer).
CHECKBACK_BODY="$TMP_DIR/.me_checkback"
printf '%s\n' '<div class="checkback"><div class="cb-emoji">⏳</div><p>Hang tight — your results will show up here once your group starts racing.</p></div>' > "$CHECKBACK_BODY"
NORESULTS_BODY="$TMP_DIR/.me_noresults"
printf '%s\n' '<div class="checkback"><p class="empty">No heats recorded for this pinny.</p></div>' > "$NORESULTS_BODY"

# ---- 5c. Wrap each registered racer's fragment in the template --------------
# No names — pinny + age-group (class) only. The class is the racer's group and
# is shown prominently in the header so spectators can confirm they typed the
# right pinny.
sql "SELECT reg.carnumber, reg.classid, COALESCE(c.class,'')
       FROM RegistrationInfo reg
       LEFT JOIN Classes c ON c.classid = reg.classid
      WHERE reg.carnumber IS NOT NULL AND reg.carnumber != ''
        AND COALESCE(reg.exclude,0) = 0
      ORDER BY reg.carnumber;" 2>/dev/null \
    | while IFS='	' read -r carnumber classid classname; do
        [ -n "$carnumber" ] || continue
        p4=$(printf "%04d" "$carnumber" 2>/dev/null || echo "$carnumber")
        PINNY_SUB=$(sed_subst_escape "$p4")
        GROUP_SUB=$(sed_subst_escape "$(esc "$classname")")

        started=0
        case "$STARTED_CLASSIDS" in *" $classid "*) started=1 ;; esac

        if [ "$started" = "1" ]; then
            if [ -f "$BODIES_DIR/$p4.body" ]; then
                body_file="$BODIES_DIR/$p4.body"
            else
                # Group started but this racer has no chart rows (e.g. withdrawn
                # via pull-forward, whose unraced heats were deleted upstream).
                body_file="$NORESULTS_BODY"
            fi
            if [ "$classid" = "$CLASS_ID" ]; then
                STATUS="Racing now"
            else
                STATUS="Group finished"
            fi
        else
            body_file="$CHECKBACK_BODY"
            STATUS="Hasn't started yet"
        fi
        STATUS_SUB=$(sed_subst_escape "$(esc "$STATUS")")

        sed -e "s|{{PINNY}}|$PINNY_SUB|g" \
            -e "s|{{GROUP}}|$GROUP_SUB|g" \
            -e "s|{{STATUS}}|$STATUS_SUB|g" \
            -e "s|{{UPDATED}}|$UPDATED_SUB|g" \
            -e "s|{{VERSION}}|$VERSION|g" \
            -e "/__STATSGEN_PAYLOAD__/{ r $body_file" -e "d; }" \
            "$SELF_DIR/template-me-detail.html" > "$ME_DIR/$p4.html"
    done

# Notfound page — rendered regardless of round state so the keypad's fallback
# always lands somewhere friendly.
NOTFOUND_ROUND=$(sed_subst_escape "${ROUND_DISPLAY:-—}")
sed -e "s|{{ROUND}}|$NOTFOUND_ROUND|g" \
    "$SELF_DIR/template-me-notfound.html" > "$ME_DIR/notfound.html"

# ---- 6. Templating -----------------------------------------------------------
# Sub-marker so sed never sees the payload bytes.
SUB_MARK="__STATSGEN_PAYLOAD__"

render_template() {
    template="$1"
    out="$2"
    payload_var="$3"
    eval payload=\$$payload_var

    # Write payload to a temp file, then use sed r to insert. Avoids the
    # "huge sed s/.../.../" delimiter-collision problem.
    payload_file="$TMP_DIR/.payload"
    printf '%s\n' "$payload" > "$payload_file"

    # Sed-escape the simple replacement strings — values like a class name
    # containing `&` would otherwise be re-expanded by sed's `&` back-ref.
    round_sub=$(sed_subst_escape "$ROUND_DISPLAY")
    heatnow_sub=$(sed_subst_escape "${HEAT_NOW:-—}")
    state_sub=$(sed_subst_escape "${STATE:-0}")
    updated_sub=$(sed_subst_escape "$GEN_AT")

    sed -e "s|{{ROUND}}|$round_sub|g" \
        -e "s|{{HEAT_NOW}}|$heatnow_sub|g" \
        -e "s|{{STATE}}|$state_sub|g" \
        -e "s|{{UPDATED}}|$updated_sub|g" \
        -e "s|{{VERSION}}|$VERSION|g" \
        -e "/$SUB_MARK/{ r $payload_file" -e "d; }" \
        "$template" > "$out"
}

# The keypad page has no dynamic payload — feed it an empty body so the
# __STATSGEN_PAYLOAD__ marker line is simply removed.
EMPTY_BODY=""

if [ "$SPLASH_ON" = "1" ]; then
    # Gate ON: the two public landing pages show the splash instead of live
    # data. My Races + feedback (below) still render normally, so the footer's
    # "Submit feedback" link keeps working. Only {{MESSAGE}}/{{UPDATED}}/
    # {{VERSION}} are substituted — the template carries no dynamic payload.
    msg_sub=$(sed_subst_escape "$(esc "$SPLASH_MSG")")
    updated_sub=$(sed_subst_escape "$GEN_AT")
    for slot in schedule recent; do
        sed -e "s|{{MESSAGE}}|$msg_sub|g" \
            -e "s|{{UPDATED}}|$updated_sub|g" \
            -e "s|{{VERSION}}|$VERSION|g" \
            "$SELF_DIR/template-splash.html" > "$TMP_DIR/$slot.html"
    done
else
    render_template "$SELF_DIR/template-schedule.html" "$TMP_DIR/schedule.html" SCHEDULE_BODY
    render_template "$SELF_DIR/template-recent.html"   "$TMP_DIR/recent.html"   RECENT_BODY
fi
render_template "$SELF_DIR/template-myraces.html"  "$TMP_DIR/myraces.html"  EMPTY_BODY
# Static audience-feedback page — no dynamic payload (empty body strips the
# marker) and no version-bump refresh in the template. See docs/PUBLIC_STATS.md.
render_template "$SELF_DIR/template-feedback.html" "$TMP_DIR/feedback.html" EMPTY_BODY

# Generator-side health snapshot (no token leakage).
cat > "$TMP_DIR/health.json" <<EOF
{"generated_at":"$GEN_AT","round_id":"${ROUND_ID:-}","heat":"${HEAT_NOW:-}","state":"${STATE:-}","db_mtime":"$DB_MTIME","version":"$VERSION"}
EOF

# Content version for the browser version-bump poll. The auto-refreshing pages
# embed this same value as {{VERSION}} and reload when version.txt differs.
printf '%s\n' "$VERSION" > "$TMP_DIR/version.txt"

# ---- 7. Atomic publish -------------------------------------------------------
mkdir -p "$DEST_DIR"
# Move the contents into place — DEST_DIR may already exist for the same token,
# so swap files individually rather than the directory.
for f in schedule.html recent.html myraces.html feedback.html health.json version.txt; do
    mv -f "$TMP_DIR/$f" "$DEST_DIR/$f"
done

# Swap the me/ directory atomically. Files in $ME_DIR were built in the same
# tmp filesystem, so `mv` is a rename(2) (single atomic op for the directory).
# We move the old one aside first so requests served between the two mvs
# either see the previous set or 404 — never a half-written tree.
if [ -d "$DEST_DIR/me" ]; then
    rm -rf "$DEST_DIR/me.old"
    mv "$DEST_DIR/me" "$DEST_DIR/me.old"
fi
mv "$ME_DIR" "$DEST_DIR/me"
rm -rf "$DEST_DIR/me.old"

# Point "current" at the active token (idempotent).
ln -sfn "tokens/$TOKEN" "$OUT/current"

exit 0

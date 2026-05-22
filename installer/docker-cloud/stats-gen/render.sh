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
            {
                heat=$1; lane=$2; pinny=$3; t=$4; place=$5; done=$6;
                # Zero-pad pinny to 4 digits ("9" -> "0009") so spectators
                # can find their kid with the browsers Ctrl+F at a glance.
                pinny_display = (pinny == "" ? "----" : sprintf("%04d", pinny));
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
                    timecell = (t != "" ? sprintf("%.3fs", t) : "");
                } else if (heat == now) {
                    status="now";
                    label = "← NOW";
                    timecell = "";
                } else {
                    status="up";
                    label = "";
                    timecell = "";
                }
                printf "<tr class=\"%s\"><td class=\"h\">%s</td><td class=\"l\">%s</td><td class=\"p\">%s</td><td class=\"r\">%s</td><td class=\"t\">%s</td></tr>\n",
                       status, heat, lane, pinny_display, label, timecell;
            }'
    )
    if [ -z "$SCHEDULE_ROWS" ]; then
        SCHEDULE_PLACEHOLDER='<tr><td colspan="5" class="empty">No heats scheduled yet.</td></tr>'
    fi
fi

SCHEDULE_BODY="${SCHEDULE_ROWS:-$SCHEDULE_PLACEHOLDER}"

# ---- 4. Last 3 completed heats ----------------------------------------------
RECENT_BODY=""
if [ -n "$ROUND_ID" ] && [ "$ROUND_ID" != "0" ]; then
    HEATS=$(sql "SELECT heat FROM RaceChart
                  WHERE roundid = $ROUND_ID
                    AND completed IS NOT NULL AND completed != ''
                  GROUP BY heat
                  ORDER BY MAX(completed) DESC
                  LIMIT 3;" 2>/dev/null || true)

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
                        timecell  = (t != "" ? sprintf("%.3fs", t) : "—");
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

# ---- 5. Templating -----------------------------------------------------------
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

    sed -e "s|{{ROUND}}|$ROUND_DISPLAY|g" \
        -e "s|{{HEAT_NOW}}|${HEAT_NOW:-—}|g" \
        -e "s|{{STATE}}|${STATE:-0}|g" \
        -e "s|{{UPDATED}}|$GEN_AT|g" \
        -e "/$SUB_MARK/{ r $payload_file" -e "d; }" \
        "$template" > "$out"
}

render_template "$SELF_DIR/template-schedule.html" "$TMP_DIR/schedule.html" SCHEDULE_BODY
render_template "$SELF_DIR/template-recent.html"   "$TMP_DIR/recent.html"   RECENT_BODY

# Generator-side health snapshot (no token leakage).
cat > "$TMP_DIR/health.json" <<EOF
{"generated_at":"$GEN_AT","round_id":"${ROUND_ID:-}","heat":"${HEAT_NOW:-}","state":"${STATE:-}","db_mtime":"$DB_MTIME"}
EOF

# ---- 6. Atomic publish -------------------------------------------------------
mkdir -p "$DEST_DIR"
# Move the contents into place — DEST_DIR may already exist for the same token,
# so swap files individually rather than the directory.
for f in schedule.html recent.html health.json; do
    mv -f "$TMP_DIR/$f" "$DEST_DIR/$f"
done

# Point "current" at the active token (idempotent).
ln -sfn "tokens/$TOKEN" "$OUT/current"

exit 0

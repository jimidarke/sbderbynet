#!/bin/bash
# test-stats-render.sh — Offline test for the stats-gen render contract that
# backs the spectator-page version-bump refresh.
#
# Builds a small but realistic SQLite event DB, runs render.sh against it, and
# asserts the properties the live pipeline depends on:
#   1. version.txt is published, numeric, and equals the DB mtime.
#   2. Re-rendering an UNCHANGED DB keeps the same version  → no needless phone
#      reloads (the headline "reload only on change" claim).
#   3. A changed DB (newer mtime) bumps the version          → phones reload.
#   4. {{VERSION}} is fully substituted and the page's embedded poll value
#      matches version.txt.
#   5. Page content sanity: pinny appears (zero-padded), current heat marked,
#      a finish time renders, and the per-racer page polls ../version.txt.
#
# Fully offline (local sqlite3 + dash/sh). No Pi, cloud, or server needed.
# Usage: ./test-stats-render.sh

set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
RENDER="$REPO/installer/docker-cloud/stats-gen/render.sh"
SHELL_BIN=$(command -v dash || command -v sh)
PASS=0; FAIL=0
ok()  { echo "  PASS: $1"; PASS=$((PASS + 1)); }
bad() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

command -v sqlite3 >/dev/null || { echo "FATAL: sqlite3 not found"; exit 2; }
[ -f "$RENDER" ] || { echo "FATAL: render.sh not found at $RENDER"; exit 2; }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
DB="$WORK/derbynet.sqlite3"
OUT="$WORK/out"; mkdir -p "$OUT/tokens"
TOKEN="TESTTOKEN0001"
DEST="$OUT/tokens/$TOKEN"

# ---- minimal event DB (only the columns render.sh reads) --------------------
sqlite3 "$DB" <<'SQL'
CREATE TABLE RaceInfo (ItemKey TEXT, ItemValue TEXT);
CREATE TABLE Classes (ClassID INTEGER, Class TEXT);
CREATE TABLE Rounds (RoundID INTEGER, ClassID INTEGER, Round INTEGER, RoundName TEXT);
CREATE TABLE RegistrationInfo (RacerID INTEGER, CarNumber INTEGER);
CREATE TABLE RaceChart (ResultID INTEGER, RoundID INTEGER, Heat INTEGER, Lane INTEGER,
                        RacerID INTEGER, FinishTime DOUBLE, FinishPlace INTEGER, Completed DATETIME);

INSERT INTO RaceInfo VALUES ('RoundID','1'),('Heat','2'),('NowRacingState','1'),('ClassID','1');
INSERT INTO Classes VALUES (1,'Ages 6-8');
INSERT INTO Rounds VALUES (1,1,1,'1 Preliminary');
INSERT INTO RegistrationInfo VALUES (1,4),(2,9),(3,15),(4,23),(5,31),(6,42);

-- Heat 1: completed (times + places).  Heat 2: current, not yet finished.
INSERT INTO RaceChart VALUES
 (101,1,1,1,1,22.1,1,'2026-06-15 10:00:01'),
 (102,1,1,2,2,22.5,2,'2026-06-15 10:00:02'),
 (103,1,1,3,3,23.0,3,'2026-06-15 10:00:03'),
 (201,1,2,1,4,NULL,NULL,NULL),
 (202,1,2,2,5,NULL,NULL,NULL),
 (203,1,2,3,6,NULL,NULL,NULL);
SQL

run_render() { "$SHELL_BIN" "$RENDER" "$DB" "$OUT" "$TOKEN" >/dev/null 2>&1; }
version() { cat "$DEST/version.txt" 2>/dev/null; }

# ---- 1. version == DB mtime, numeric ----------------------------------------
echo "Test 1: version.txt published and equals DB mtime"
touch -d @1000000000 "$DB"
run_render
v1=$(version)
dbm=$(stat -c %Y "$DB")
case "$v1" in ''|*[!0-9]*) bad "version.txt not numeric: '$v1'";; *) ok "numeric version ($v1)";; esac
[ "$v1" = "$dbm" ] && ok "version equals DB mtime" || bad "version $v1 != DB mtime $dbm"

# ---- 2. unchanged DB → stable version (no needless reload) -------------------
echo "Test 2: re-render of an unchanged DB keeps the same version"
run_render
v2=$(version)
[ "$v2" = "$v1" ] && ok "version stable when idle ($v2)" || bad "version changed with no DB change ($v1 -> $v2)"

# ---- 3. changed DB → version bumps ------------------------------------------
echo "Test 3: a changed DB bumps the version"
touch -d @1000000042 "$DB"
run_render
v3=$(version)
[ "$v3" != "$v1" ] && [ "$v3" = "1000000042" ] && ok "version bumped on change ($v1 -> $v3)" \
    || bad "version did not track DB change (got $v3)"

# ---- 4. {{VERSION}} substituted + embedded poll value matches ---------------
echo "Test 4: template substitution + embedded poll value"
left=$(grep -c "{{VERSION}}" "$DEST/schedule.html" "$DEST/recent.html" "$DEST/me/0023.html" 2>/dev/null | awk -F: '{s+=$2} END{print s}')
[ "${left:-1}" = "0" ] && ok "no unsubstituted {{VERSION}}" || bad "found $left unsubstituted {{VERSION}}"
emb=$(grep -o 'var V="[0-9]*"' "$DEST/schedule.html" | grep -o '[0-9]*')
[ "$emb" = "$v3" ] && ok "schedule embeds current version ($emb)" || bad "embedded V ($emb) != version.txt ($v3)"

# ---- 5. content sanity ------------------------------------------------------
echo "Test 5: rendered content"
grep -q "0004" "$DEST/schedule.html" && ok "pinny zero-padded (0004) on schedule" || bad "pinny 0004 missing from schedule"
grep -q "NOW" "$DEST/schedule.html" && ok "current heat marked (NOW)" || bad "current-heat marker missing"
grep -q "22.1s" "$DEST/recent.html" && ok "finish time rendered on recent" || bad "finish time missing from recent"
if [ -f "$DEST/me/0023.html" ]; then
    ok "per-racer page generated (me/0023.html)"
    grep -q '"../version.txt"' "$DEST/me/0023.html" && ok "per-racer page polls ../version.txt" \
        || bad "per-racer page does not poll ../version.txt"
else
    bad "per-racer page me/0023.html not generated"
fi

# ---- 6. audience feedback page ----------------------------------------------
echo "Test 6: audience feedback page + footer button"
if [ -f "$DEST/feedback.html" ]; then
    ok "feedback.html generated"
    grep -q 'id="fb-form"' "$DEST/feedback.html" && ok "feedback form present" \
        || bad "feedback form missing from feedback.html"
    grep -q 'maxlength="150"' "$DEST/feedback.html" && ok "150-char limit on textarea" \
        || bad "150-char maxlength missing"
    grep -q 'feedback-submit' "$DEST/feedback.html" && ok "posts to feedback-submit endpoint" \
        || bad "feedback-submit endpoint reference missing"
    # The feedback page must NOT self-refresh (a reload would wipe a draft).
    grep -q 'location.reload' "$DEST/feedback.html" && bad "feedback page should not auto-reload" \
        || ok "feedback page does not auto-reload"
else
    bad "feedback.html not generated"
fi
grep -q 'href="feedback.html"' "$DEST/schedule.html" && ok "schedule footer links to feedback" \
    || bad "schedule missing feedback button"
grep -q 'href="../feedback.html"' "$DEST/me/0023.html" 2>/dev/null && ok "per-racer footer links to ../feedback" \
    || bad "per-racer page missing feedback button"

echo
echo "stats-gen render tests: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]

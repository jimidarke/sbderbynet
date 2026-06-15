#!/bin/bash
# test-stats-render-loop.sh — Offline test for the stats-gen entrypoint render
# loop (the cloud-side mirror of the Pi's event-driven push).
#
# Asserts the loop:
#   1. Renders once on startup.
#   2. Renders again when the synced DB's mtime changes (event landed).
#   3. Does NOT render while the DB is idle (no needless work / phone reloads),
#      within the REFRESH_SECONDS floor.
#
# render.sh is stubbed (RENDER_BIN override) and just logs each invocation, so
# this runs fully offline with no sqlite/templates needed. Timing-based but uses
# generous windows (POLL_SECONDS=1, 3 s observation windows) to stay reliable.
#
# Usage: ./test-stats-render-loop.sh

set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
ENTRY="$REPO/installer/docker-cloud/stats-gen/entrypoint.sh"
SHELL_BIN=$(command -v dash || command -v sh)
PASS=0; FAIL=0
ok()  { echo "  PASS: $1"; PASS=$((PASS + 1)); }
bad() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

[ -f "$ENTRY" ] || { echo "FATAL: entrypoint.sh not found at $ENTRY"; exit 2; }

WORK=$(mktemp -d)
DB="$WORK/derbynet.sqlite3"
OUT="$WORK/out"
LOG="$WORK/renders.log"
: > "$LOG"
touch -d @1000000000 "$DB"

cat > "$WORK/render-stub.sh" <<EOF
#!/bin/bash
echo render >> "$LOG"
exit 0
EOF
chmod +x "$WORK/render-stub.sh"

count() { wc -l < "$LOG" | tr -d ' '; }

# High floor so only DB-change (not the periodic floor) can drive renders here.
RENDER_BIN="$WORK/render-stub.sh" DB_PATH="$DB" OUT_DIR="$OUT" \
    LIVE_STATS_TOKEN="TESTTOKEN0001" POLL_SECONDS=1 REFRESH_SECONDS=1000 \
    "$SHELL_BIN" "$ENTRY" >/dev/null 2>&1 &
LOOP_PID=$!
cleanup() { kill "$LOOP_PID" 2>/dev/null; wait "$LOOP_PID" 2>/dev/null; rm -rf "$WORK"; }
trap cleanup EXIT

# 1. startup render
sleep 3
c1=$(count)
[ "$c1" = "1" ] && ok "rendered once on startup (got $c1)" || bad "expected 1 startup render, got $c1"

# 2. idle → no extra render
sleep 3
c2=$(count)
[ "$c2" = "$c1" ] && ok "no render while DB idle (stayed $c2)" || bad "rendered while idle ($c1 -> $c2)"

# 3. DB change → one more render
touch -d @1000000050 "$DB"
sleep 3
c3=$(count)
[ "$c3" = "$(( c2 + 1 ))" ] && ok "rendered once on DB change ($c2 -> $c3)" \
    || bad "expected one render on change, got $c2 -> $c3"

# 4. idle again → still no extra
sleep 3
c4=$(count)
[ "$c4" = "$c3" ] && ok "no render after change settles (stayed $c4)" || bad "rendered while idle again ($c3 -> $c4)"

echo
echo "stats-gen render-loop tests: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]

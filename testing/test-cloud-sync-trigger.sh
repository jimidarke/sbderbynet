#!/bin/bash
# test-cloud-sync-trigger.sh — Unit test for cloud-sync.sh single-flight +
# coalesce-to-one-catch-up retry semantics (the event-driven push safety).
#
# Runs fully offline: scp/ssh/sqlite3/logger are stubbed onto PATH so no Pi,
# cloud, or real DB is needed. Each completed push ends in exactly one ssh `mv`,
# so we count ssh stub invocations to count pushes.
#
# Covers:
#   1. No trigger during a push        → exactly 1 push.
#   2. A trigger arrives mid-push       → exactly 2 pushes (one coalesced retry).
#   3. Lock already held by another proc → 0 pushes (won't transmit in-flight).
#
# Usage: ./test-cloud-sync-trigger.sh      (no server required)

set -u

SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/extras/soapbox/infra/server/cloud-sync.sh"
PASS=0
FAIL=0

ok()   { echo "  PASS: $1"; PASS=$((PASS + 1)); }
bad()  { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }

[ -f "$SCRIPT" ] || { echo "FATAL: cannot find cloud-sync.sh at $SCRIPT"; exit 2; }

# ---- per-test sandbox -------------------------------------------------------
# Builds a fresh tmp env + stub bin dir. STUB_TOUCH_FUTURE=1 makes the first
# push's ssh stub bump the trigger file's mtime to a fixed far-future epoch,
# simulating an event landing mid-push (and dodging 1 s mtime granularity).
make_env() {
    WORK=$(mktemp -d)
    BIN="$WORK/bin"; mkdir -p "$BIN"
    PUSH_LOG="$WORK/pushes.log"; : > "$PUSH_LOG"
    FIRST_DONE="$WORK/first_done"

    : > "$WORK/key";         chmod 0600 "$WORK/key"
    : > "$WORK/known_hosts"
    : > "$WORK/db.sqlite3"
    : > "$WORK/trigger"
    : > "$WORK/lock"

    cat > "$BIN/sqlite3" <<'EOF'
#!/bin/bash
exit 0
EOF
    cat > "$BIN/scp" <<'EOF'
#!/bin/bash
exit 0
EOF
    # ssh stub == the atomic remote mv == one completed push.
    cat > "$BIN/ssh" <<EOF
#!/bin/bash
echo push >> "$PUSH_LOG"
if [ "\${STUB_TOUCH_FUTURE:-0}" = "1" ] && [ ! -f "$FIRST_DONE" ]; then
    : > "$FIRST_DONE"
    touch -d @2000000000 "$WORK/trigger"   # simulate an event mid-push
fi
exit 0
EOF
    cat > "$BIN/logger" <<'EOF'
#!/bin/bash
exit 0
EOF
    chmod +x "$BIN"/*

    export PATH="$BIN:$PATH"
    export CLOUD_HOST="example.invalid"
    export CLOUD_USER="x"
    export CLOUD_DB_PATH="$WORK/remote.sqlite3"
    export DERBYNET_DB="$WORK/db.sqlite3"
    export SYNC_KEY="$WORK/key"
    export SYNC_KNOWN_HOSTS="$WORK/known_hosts"
    export STATE_FILE="$WORK/state"
    export TRIGGER_FILE="$WORK/trigger"
    export LOCK_FILE="$WORK/lock"
}

teardown() {
    rm -rf "$WORK"
    # Drop the stub dir from PATH for the next test (make_env re-prepends).
    PATH="${PATH#"$BIN":}"
}

push_count() { wc -l < "$PUSH_LOG" | tr -d ' '; }

# ---- Test 1: no mid-push trigger → exactly 1 push ---------------------------
echo "Test 1: single push when nothing triggers during the run"
make_env
STUB_TOUCH_FUTURE=0 bash "$SCRIPT" >/dev/null 2>&1
n=$(push_count)
[ "$n" = "1" ] && ok "exactly 1 push (got $n)" || bad "expected 1 push, got $n"
teardown

# ---- Test 2: trigger mid-push → exactly 2 pushes (one coalesced retry) ------
echo "Test 2: one coalesced catch-up when a trigger lands mid-push"
make_env
STUB_TOUCH_FUTURE=1 bash "$SCRIPT" >/dev/null 2>&1
n=$(push_count)
[ "$n" = "2" ] && ok "exactly 2 pushes (got $n)" || bad "expected 2 pushes, got $n"
teardown

# ---- Test 3: lock held → won't transmit in-flight ---------------------------
echo "Test 3: no push while the lock is already held"
make_env
# Hold an exclusive lock on the lock file from this (parent) process, then run
# cloud-sync.sh as a child — its flock -n must fail and it must exit 0 cleanly.
exec 8>"$LOCK_FILE"
flock 8
STUB_TOUCH_FUTURE=0 bash "$SCRIPT" >/dev/null 2>&1
rc=$?
flock -u 8
exec 8>&-
n=$(push_count)
[ "$n" = "0" ] && ok "no push while locked (got $n)" || bad "expected 0 pushes, got $n"
[ "$rc" = "0" ] && ok "exited 0 when lock contended (got $rc)" || bad "expected exit 0, got $rc"
teardown

# ---- summary ----------------------------------------------------------------
echo
echo "cloud-sync trigger tests: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]

#!/bin/bash
# cloud-sync.sh — Sync DerbyNet SQLite from the race-day Pi to the cloud VPS.
#
# Runs on the Pi via systemd: a 30 s timer backstop (derbynet-cloud-sync.timer)
# plus a .path unit (derbynet-cloud-sync.path) that fires on demand when race
# code touches the trigger file. Uses SQLite's
# .backup command for a safe, consistent snapshot even during active racing
# (WAL mode). Writes the DB into a `.tmp` path on the cloud and renames it
# atomically so concurrent readers (the stats-gen container) cannot see a
# torn file if cellular drops mid-push.
#
# Direction is strictly Pi -> Cloud. The cloud twin's canonical DB is a
# read-only replica; local edits there are overwritten on the next sync.
# We also push a `.cloud_readonly` sentinel + timestamp so the cloud
# operator can see when the last sync landed.
#
# Configuration (env vars; defaults set below):
#   CLOUD_HOST          — VPS hostname (REQUIRED).
#   CLOUD_USER          — SSH user (default: claude).
#   CLOUD_DB_PATH       — Remote DB path (default: production data dir).
#   DERBYNET_DB         — Local DB path; auto-detected if unset.
#   SYNC_KEY            — SSH private key path (default: /etc/derbynet/cloud-sync-key).
#   SYNC_KNOWN_HOSTS    — Known-hosts file (default: /etc/derbynet/cloud-sync-known_hosts).
#   STATE_FILE          — Failure-streak counter (default: /run/derbynet-cloud-sync.state).
#
# Exit codes:
#   0  successful push
#   1  configuration error (missing env, key, etc.)
#   2  local DB not found
#   3  scp/ssh failure (cellular drop, auth, etc.)

set -eu

CLOUD_HOST="${CLOUD_HOST:-}"
CLOUD_USER="${CLOUD_USER:-claude}"
CLOUD_DB_PATH="${CLOUD_DB_PATH:-/opt/derbynet/production/data/derbynet.sqlite3}"
SYNC_KEY="${SYNC_KEY:-/etc/derbynet/cloud-sync-key}"
SYNC_KNOWN_HOSTS="${SYNC_KNOWN_HOSTS:-/etc/derbynet/cloud-sync-known_hosts}"
STATE_FILE="${STATE_FILE:-/run/derbynet-cloud-sync/state}"
TEMP_BACKUP="$(mktemp -t derbynet-cloud-sync.sqlite3.XXXXXX)"
TEMP_SENTINEL="$(mktemp -t derbynet-cloud-readonly.txt.XXXXXX)"

trap 'rm -f "$TEMP_BACKUP" "$TEMP_SENTINEL"' EXIT

# ---- helpers ----------------------------------------------------------------

# Read the current consecutive-failure count (0 if missing).
read_failures() {
    [ -f "$STATE_FILE" ] && cat "$STATE_FILE" 2>/dev/null || echo 0
}

# Bump or clear the streak counter.
bump_failures() {
    local n
    n=$(read_failures)
    echo $((n + 1)) > "$STATE_FILE" 2>/dev/null || true
}
clear_failures() {
    rm -f "$STATE_FILE" 2>/dev/null || true
}

# Log to journal, but suppress when in a long failure streak so a multi-hour
# cellular outage doesn't fill the journal. First failure + every 10th
# thereafter is logged; recovery is always logged.
log_failure() {
    local msg="$1" n
    n=$(read_failures)
    if [ "$n" -le 1 ] || [ $((n % 10)) -eq 0 ]; then
        logger -t derbynet-cloud-sync -p user.warn "FAIL #$n: $msg"
    fi
}
log_recovery() {
    local n
    n=$(read_failures)
    if [ "$n" -gt 0 ]; then
        logger -t derbynet-cloud-sync -p user.notice "recovered after $n failure(s)"
    fi
}

# Common SSH options. Tuned for cellular: tolerate 15 s to handshake, send
# keepalives every 5 s, fail after 3 misses (~15 s of no response). Strict
# host key checking against the baked-in known_hosts file.
ssh_common_opts=(
    -i "$SYNC_KEY"
    -o "UserKnownHostsFile=$SYNC_KNOWN_HOSTS"
    -o "StrictHostKeyChecking=yes"
    -o "ConnectTimeout=15"
    -o "ServerAliveInterval=5"
    -o "ServerAliveCountMax=3"
    -o "BatchMode=yes"
)

# ---- preflight --------------------------------------------------------------

if [ -z "$CLOUD_HOST" ]; then
    logger -t derbynet-cloud-sync -p user.err "CLOUD_HOST not set; edit /etc/default/derbynet-cloud-sync"
    exit 1
fi
if [ ! -r "$SYNC_KEY" ]; then
    logger -t derbynet-cloud-sync -p user.err "SSH key not readable: $SYNC_KEY"
    exit 1
fi
if [ ! -r "$SYNC_KNOWN_HOSTS" ]; then
    logger -t derbynet-cloud-sync -p user.err "known_hosts not readable: $SYNC_KNOWN_HOSTS"
    exit 1
fi

# ---- single-flight lock -----------------------------------------------------
#
# Only one push may run at a time. If a trigger fires while a push is in flight,
# the in-flight holder catches it via the mtime recheck below (and the 30 s
# timer is the final backstop), so a blocked invocation simply exits 0. The lock
# file lives OUTSIDE the service RuntimeDirectory (which systemd recreates on
# every start) so contention is visible across the timer- and event-driven
# (.path unit) invocations alike. See docs/PUBLIC_STATS.md.
TRIGGER_FILE="${TRIGGER_FILE:-/run/derbynet-cloud-sync.trigger}"
LOCK_FILE="${LOCK_FILE:-/run/derbynet-cloud-sync.lock}"

exec 9>"$LOCK_FILE" 2>/dev/null || exit 0
if ! flock -n 9; then
    exit 0
fi

flag_mtime() { stat -c %Y "$TRIGGER_FILE" 2>/dev/null || echo 0; }

# do_one_push: locate the active DB, snapshot it WAL-safely, and push the DB +
# sentinel to the cloud with an atomic remote rename. Returns 0 on success, 2 if
# no DB was found, 3 on snapshot/scp/ssh failure. Updates the failure-streak
# state on every outcome so both the initial and catch-up pushes count.
do_one_push() {
    local DB_PATH SYNC_TS CLOUD_DIR REMOTE_DB_TMP REMOTE_SENT_TMP REMOTE_SENT

    # Locate the active DB. Multi-event layouts put it under
    # /var/lib/derbynet/<year>/<event>/derbynet.sqlite3; pick the most recently
    # modified one.
    if [ -n "${DERBYNET_DB:-}" ]; then
        DB_PATH="$DERBYNET_DB"
    else
        DB_PATH=$(find /var/lib/derbynet -name "derbynet.sqlite3" -printf '%T@ %p\n' 2>/dev/null \
                  | sort -rn | head -1 | cut -d' ' -f2-)
    fi

    if [ -z "$DB_PATH" ] || [ ! -f "$DB_PATH" ]; then
        log_failure "DB not found at: ${DB_PATH:-<auto-detect empty>}"
        bump_failures
        return 2
    fi

    # ---- active-DB marker (ad-hoc mode) -------------------------------------
    # Mirror the selection the PHP rig makes in inc/db-marker.inc: in ad-hoc
    # ("come-as-you-are") mode the rig races into a SEPARATE sibling *.sqlite3
    # (adhoc.sqlite3) named by the marker file, leaving the official DB frozen.
    # Push whatever the rig is live on so the cloud twin mirrors it; the cloud
    # render auto-detects ad-hoc from RaceInfo.adhoc-mode. Fail-safe: any
    # malformed / out-of-bounds / missing marker keeps the official DB (same
    # allowlist as the PHP side — sibling of the official DB, .sqlite3, no `..`).
    local MARKER CAND OFFICIAL_DIR CAND_DIR
    MARKER="${ACTIVE_DB_MARKER:-/var/lib/derbynet/active-db}"
    if [ -r "$MARKER" ]; then
        CAND=$(tr -d '\r\000' < "$MARKER" 2>/dev/null | head -n1)
        CAND="${CAND#"${CAND%%[![:space:]]*}"}"   # strip leading whitespace
        CAND="${CAND%"${CAND##*[![:space:]]}"}"    # strip trailing whitespace
        case "$CAND" in *..*) CAND="" ;; esac      # no path traversal
        if [ -n "$CAND" ] && [ "${CAND%.sqlite3}" != "$CAND" ] && [ -f "$CAND" ]; then
            OFFICIAL_DIR=$(cd "$(dirname "$DB_PATH")" 2>/dev/null && pwd || true)
            CAND_DIR=$(cd "$(dirname "$CAND")" 2>/dev/null && pwd || true)
            if [ -n "$OFFICIAL_DIR" ] && [ "$CAND_DIR" = "$OFFICIAL_DIR" ]; then
                DB_PATH="$CAND"
            fi
        fi
    fi

    # ---- snapshot -----------------------------------------------------------
    # .backup is WAL-safe and does not lock the main DB. Tiny CPU cost; runs in
    # tens of milliseconds for typical race-day DB sizes (< 10 MB).
    if ! sqlite3 "$DB_PATH" ".backup $TEMP_BACKUP" 2>/dev/null; then
        log_failure "sqlite3 .backup failed for $DB_PATH"
        bump_failures
        return 3
    fi

    SYNC_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    cat > "$TEMP_SENTINEL" <<EOF
# DerbyNet Cloud Twin Sentinel
# Presence of this file marks the host as a read-only replica of a Pi.
# Local edits will be overwritten on the next cloud-sync.
last_sync_utc=$SYNC_TS
source_host=$(hostname)
EOF

    # ---- push ---------------------------------------------------------------
    # Atomic remote write: scp to .tmp paths, then a single ssh `mv` so a partial
    # transfer never replaces a good DB. -C enables compression; saves ~30-60%
    # on a typical SQLite file over a slow uplink.
    CLOUD_DIR=$(dirname "$CLOUD_DB_PATH")
    REMOTE_DB_TMP="${CLOUD_DB_PATH}.tmp"
    REMOTE_SENT_TMP="${CLOUD_DIR}/.cloud_readonly.tmp"
    REMOTE_SENT="${CLOUD_DIR}/.cloud_readonly"

    if ! scp -O -q -C "${ssh_common_opts[@]}" \
           "$TEMP_BACKUP"   "${CLOUD_USER}@${CLOUD_HOST}:${REMOTE_DB_TMP}" \
           2>/dev/null; then
        log_failure "scp DB failed (cellular outage or auth)"
        bump_failures
        return 3
    fi

    if ! scp -O -q -C "${ssh_common_opts[@]}" \
           "$TEMP_SENTINEL" "${CLOUD_USER}@${CLOUD_HOST}:${REMOTE_SENT_TMP}" \
           2>/dev/null; then
        log_failure "scp sentinel failed"
        bump_failures
        return 3
    fi

    # Single ssh round-trip swaps both files atomically (each `mv` is atomic on
    # POSIX; back-to-back means at most a few ms of inconsistency, which the
    # stats-gen render won't notice).
    if ! ssh "${ssh_common_opts[@]}" \
           "${CLOUD_USER}@${CLOUD_HOST}" \
           "mv $REMOTE_DB_TMP $CLOUD_DB_PATH && mv $REMOTE_SENT_TMP $REMOTE_SENT" \
           2>/dev/null; then
        log_failure "ssh mv failed"
        bump_failures
        return 3
    fi

    # ---- success ------------------------------------------------------------
    log_recovery
    clear_failures
    # Quiet success log — at info level so it doesn't clutter default-priority
    # filters even when events fire several pushes a minute.
    logger -t derbynet-cloud-sync -p user.info "synced $DB_PATH -> ${CLOUD_USER}@${CLOUD_HOST}:${CLOUD_DB_PATH} @ $SYNC_TS"
    return 0
}

# Run a push, then — if a trigger arrived while it was running — exactly one
# catch-up push. This coalesces any number of mid-push triggers into a single
# retry; anything that arrives after the catch-up rides the next 30 s timer
# tick. `before` is captured AFTER acquiring the lock so triggers that landed
# while we were blocked on flock aren't double-counted. The `if` form keeps
# `set -e` from aborting before the retry check.
before=$(flag_mtime)
if do_one_push; then rc=0; else rc=$?; fi

if [ "$(flag_mtime)" != "$before" ]; then
    if do_one_push; then rc=0; else rc=$?; fi
fi

exit $rc

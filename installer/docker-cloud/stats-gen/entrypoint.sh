#!/usr/bin/env dash
# Render loop for the public spectator pages.
#
# Reads $DB_PATH (read-only) and publishes $OUT_DIR/tokens/$LIVE_STATS_TOKEN/
# atomically every $REFRESH_SECONDS. The "current" symlink is what Caddy serves.
#
# Required env:
#   LIVE_STATS_TOKEN   — token string used as the per-event directory name.
#                        Must match the path component Caddy routes on.
# Optional:
#   DB_PATH            — default /var/lib/derbynet/derbynet.sqlite3
#   OUT_DIR            — default /out
#   REFRESH_SECONDS    — default 30

set -eu

DB_PATH="${DB_PATH:-/var/lib/derbynet/derbynet.sqlite3}"
OUT_DIR="${OUT_DIR:-/out}"
REFRESH_SECONDS="${REFRESH_SECONDS:-30}"
TZ="${TZ:-UTC}"
export TZ

log() { printf '%s stats-gen: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

if [ -z "${LIVE_STATS_TOKEN:-}" ]; then
    log "ERROR LIVE_STATS_TOKEN is empty; refusing to start"
    exit 1
fi

mkdir -p "$OUT_DIR/tokens"

# Best-effort tmp cleanup if a previous run died mid-publish.
find "$OUT_DIR/tokens" -maxdepth 1 -type d -name ".tmp.*" -mmin +5 -exec rm -rf {} + 2>/dev/null || true

cleanup() {
    log "received signal, exiting"
    exit 0
}
trap cleanup INT TERM

log "starting render loop: db=$DB_PATH out=$OUT_DIR token=${LIVE_STATS_TOKEN%????????}… interval=${REFRESH_SECONDS}s"

while true; do
    start_ts=$(date +%s)

    if ! /opt/stats-gen/render.sh "$DB_PATH" "$OUT_DIR" "$LIVE_STATS_TOKEN"; then
        log "WARN render failed; keeping previous output"
    fi

    elapsed=$(( $(date +%s) - start_ts ))
    sleep_for=$(( REFRESH_SECONDS - elapsed ))
    [ $sleep_for -lt 1 ] && sleep_for=1
    sleep $sleep_for
done

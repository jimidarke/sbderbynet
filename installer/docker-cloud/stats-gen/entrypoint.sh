#!/usr/bin/env dash
# Render loop for the public spectator pages.
#
# Reads $DB_PATH (read-only) and publishes $OUT_DIR/tokens/$LIVE_STATS_TOKEN/
# atomically whenever the DB changes (mtime poll), with $REFRESH_SECONDS as an
# idle floor. The "current" symlink is what Caddy serves.
#
# Required env:
#   LIVE_STATS_TOKEN   — token string used as the per-event directory name.
#                        Must match the path component Caddy routes on.
# Optional:
#   DB_PATH            — default /var/lib/derbynet/derbynet.sqlite3
#   OUT_DIR            — default /out
#   REFRESH_SECONDS    — periodic-render floor, default 30
#   POLL_SECONDS       — DB mtime poll cadence, default 2
#
# The Pi pushes the DB via cloud-sync (event-driven + a 30 s backstop), landing
# it with an atomic rename. We poll the DB's mtime every POLL_SECONDS and render
# as soon as it changes, so a race event surfaces within ~POLL_SECONDS instead
# of waiting out the old fixed 30 s loop. REFRESH_SECONDS is kept as a floor so
# the "generated at" stamp and any time-relative content stay fresh even when
# the DB is idle. See docs/PUBLIC_STATS.md.

set -eu

DB_PATH="${DB_PATH:-/var/lib/derbynet/derbynet.sqlite3}"
OUT_DIR="${OUT_DIR:-/out}"
REFRESH_SECONDS="${REFRESH_SECONDS:-30}"
POLL_SECONDS="${POLL_SECONDS:-2}"
RENDER_BIN="${RENDER_BIN:-/opt/stats-gen/render.sh}"  # overridable for tests
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

log "starting render loop: db=$DB_PATH out=$OUT_DIR token=${LIVE_STATS_TOKEN%????????}… poll=${POLL_SECONDS}s floor=${REFRESH_SECONDS}s"

# Current mtime of the synced DB, or 0 if it isn't there yet. The Pi replaces
# the file by rename, so the path always re-stats to the new inode's mtime.
db_mtime() { [ -f "$DB_PATH" ] && stat -c %Y "$DB_PATH" 2>/dev/null || echo 0; }

last_mtime=0
last_render=0

while true; do
    now=$(date +%s)
    cur=$(db_mtime)

    # Render when the DB changed (event-driven) OR the floor has elapsed since
    # the last render (idle refresh of the timestamp / time-relative content).
    if [ "$cur" != "$last_mtime" ] || [ $(( now - last_render )) -ge "$REFRESH_SECONDS" ]; then
        if "$RENDER_BIN" "$DB_PATH" "$OUT_DIR" "$LIVE_STATS_TOKEN"; then
            last_mtime="$cur"
            last_render="$now"
        else
            log "WARN render failed; keeping previous output"
            # Don't latch last_mtime on failure, so the next tick retries.
        fi
    fi

    sleep "$POLL_SECONDS"
done

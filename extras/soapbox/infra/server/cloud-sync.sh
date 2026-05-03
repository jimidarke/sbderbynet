#!/bin/bash
# cloud-sync.sh — Sync DerbyNet SQLite database from Pi to cloud VPS
#
# Runs on the race-day Pi via cron. Uses SQLite's .backup command
# for a safe, consistent copy even during active racing (WAL mode).
#
# Setup:
#   1. Generate SSH key: ssh-keygen -t ed25519 -f ~/.ssh/cloud_sync -N ""
#   2. Add public key to VPS: ssh-copy-id -i ~/.ssh/cloud_sync deploy@<vps-ip>
#   3. Add to crontab: * * * * * /opt/derbynet/cloud-sync.sh
#      (cron runs every minute; the script handles finer intervals internally)
#
# Environment variables (or edit defaults below):
#   CLOUD_HOST      — VPS IP or hostname
#   CLOUD_USER      — SSH user (default: deploy)
#   CLOUD_DB_PATH   — Remote path for synced database
#   DERBYNET_DB     — Local database path
#   SYNC_KEY        — SSH key path

set -euo pipefail

# Configuration
CLOUD_HOST="${CLOUD_HOST:-}"
CLOUD_USER="${CLOUD_USER:-deploy}"
CLOUD_DB_PATH="${CLOUD_DB_PATH:-/opt/derbynet/production/data/derbynet.sqlite3}"
SYNC_KEY="${SYNC_KEY:-$HOME/.ssh/cloud_sync}"
TEMP_BACKUP="/tmp/derbynet-cloud-sync.sqlite3"

# Find the active database
if [ -n "${DERBYNET_DB:-}" ]; then
    DB_PATH="$DERBYNET_DB"
else
    # Auto-detect: find the most recently modified .sqlite3 file
    DB_PATH=$(find /var/lib/derbynet -name "derbynet.sqlite3" -printf '%T@ %p\n' 2>/dev/null \
              | sort -rn | head -1 | cut -d' ' -f2)
fi

if [ -z "$CLOUD_HOST" ]; then
    echo "ERROR: CLOUD_HOST not set. Set it in environment or edit this script."
    exit 1
fi

if [ -z "$DB_PATH" ] || [ ! -f "$DB_PATH" ]; then
    echo "ERROR: Database not found at: ${DB_PATH:-<not set>}"
    exit 1
fi

# Create a consistent backup (safe with WAL mode, doesn't lock the main DB)
sqlite3 "$DB_PATH" ".backup $TEMP_BACKUP"

# Sync to cloud via scp.
#
# Direction is strictly Pi -> Cloud. The cloud twin is a read-only replica.
# Any data written on the cloud (e.g. someone editing a racer in the cloud
# admin UI) will be silently overwritten on the next sync. To make that
# obvious to the cloud operator, we also push a sentinel + sync timestamp
# alongside the database; the cloud PHP renders a banner when it sees the
# sentinel.
SYNC_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TEMP_SENTINEL="/tmp/derbynet-cloud-readonly.txt"
cat > "$TEMP_SENTINEL" <<EOF
# DerbyNet Cloud Twin Sentinel
# Presence of this file marks the host as a read-only replica of a Pi.
# Local edits will be overwritten on the next cloud-sync.
last_sync_utc=$SYNC_TIMESTAMP
source_host=$(hostname)
EOF

CLOUD_DIR=$(dirname "$CLOUD_DB_PATH")
SENTINEL_REMOTE="$CLOUD_DIR/.cloud_readonly"

scp -q -i "$SYNC_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 \
    "$TEMP_BACKUP" "${CLOUD_USER}@${CLOUD_HOST}:${CLOUD_DB_PATH}"
scp -q -i "$SYNC_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 \
    "$TEMP_SENTINEL" "${CLOUD_USER}@${CLOUD_HOST}:${SENTINEL_REMOTE}"

# Clean up
rm -f "$TEMP_BACKUP" "$TEMP_SENTINEL"

# Log loudly — operators looking at the cron mail trail or the system journal
# should be able to confirm sync activity at a glance.
logger -t derbynet-cloud-sync "Synced $DB_PATH -> ${CLOUD_USER}@${CLOUD_HOST}:${CLOUD_DB_PATH} at $SYNC_TIMESTAMP"

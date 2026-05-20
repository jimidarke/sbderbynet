#!/bin/bash
# derbynet-backup.sh — every 15 min, snapshot the active event DB.
# Keeps last 24 snapshots (~6h race coverage). Uses SQLite's online backup
# API so it's safe against concurrent writers.

set -uo pipefail

BACKUP_DIR=/var/lib/derbynet/backups
MAX_KEEP=24

mkdir -p "$BACKUP_DIR"

# Find the most-recently-modified event DB. The path convention is
# /var/lib/derbynet/<year>/<event>/derbynet.sqlite3.
ACTIVE_DB=$(find /var/lib/derbynet -maxdepth 3 -name derbynet.sqlite3 -type f \
            -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)

if [[ -z $ACTIVE_DB || ! -f $ACTIVE_DB ]]; then
    echo "no active DB found; skipping backup"
    exit 0
fi

TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$BACKUP_DIR/auto-$TS.sqlite3"

sqlite3 "$ACTIVE_DB" ".backup '$OUT'"
chmod 0644 "$OUT"

# Keep only the most recent $MAX_KEEP
ls -1t "$BACKUP_DIR"/auto-*.sqlite3 2>/dev/null | tail -n +$((MAX_KEEP + 1)) | xargs -r rm -f

echo "backup: $OUT ($(du -h "$OUT" | cut -f1))"

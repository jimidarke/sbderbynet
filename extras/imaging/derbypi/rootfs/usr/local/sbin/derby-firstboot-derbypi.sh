#!/bin/bash
# derby-firstboot-derbypi.sh — invoked once by derby-firstboot.sh on the
# central race-server Pi. Handles: clear stale retained MQTT, restore DB
# backup if operator dropped one in /boot/firmware/restore/.

set -uo pipefail

LOG=/var/log/derby-firstboot.log
log() { echo "[$(date -Iseconds)] [derbypi] $*" | tee -a "$LOG"; }

# 1. Wait for mosquitto to be listening, then clear stale retained topics.
log "waiting for mosquitto on 127.0.0.1:1883..."
for _ in $(seq 1 30); do
    if mosquitto_pub -h 127.0.0.1 -t 'derbynet/firstboot/ping' -m "$(date -Iseconds)" 2>/dev/null; then
        log "mosquitto reachable"
        break
    fi
    sleep 2
done

# Clearing retained derbynet/# topics — see docs/RACE_SYSTEM_AUDIT_2026-05.md §D.
# We blast a null retained payload to every observed retained topic. Easiest
# to do that by subscribing briefly and replaying with retain+null.
log "clearing stale retained MQTT topics..."
timeout 5 mosquitto_sub -h 127.0.0.1 -v -t 'derbynet/#' 2>/dev/null \
    | awk '{print $1}' | sort -u \
    | while read -r topic; do
        mosquitto_pub -h 127.0.0.1 -r -n -t "$topic" 2>/dev/null && \
            log "  cleared retained: $topic"
    done || true

# 2. Operator-supplied DB restore at /boot/firmware/restore/*.sqlite3.gz
RESTORE_DIR=/boot/firmware/restore
if compgen -G "$RESTORE_DIR/*.sqlite3.gz" >/dev/null; then
    log "found DB restore payload(s) in $RESTORE_DIR"
    for gz in "$RESTORE_DIR"/*.sqlite3.gz; do
        log "processing $gz"

        # SHA verification: expect a sibling .sha256 file containing
        # "<sha256>  <basename>". Strict — refuse on mismatch.
        sha_file="${gz%.gz}.sha256"
        [[ -f $sha_file ]] || sha_file="$(dirname "$gz")/$(basename "$gz").sha256"
        if [[ -f $sha_file ]]; then
            if ! (cd "$(dirname "$gz")" && sha256sum -c "$(basename "$sha_file")"); then
                log "FATAL: sha256 mismatch on $gz — refusing to restore"
                continue
            fi
            log "sha256 OK"
        else
            log "WARN: no .sha256 sibling for $gz — proceeding without verification"
        fi

        # Path convention: /var/lib/derbynet/<year>/<eventid>/derbynet.sqlite3
        # We pick year from the current date and event id from the filename.
        # Filename expected: derbynet-snapshot-<event>-<date>.sqlite3.gz
        base=$(basename "$gz" .sqlite3.gz)
        event=$(echo "$base" | sed -nE 's/^derbynet-snapshot-([^-]+).*/\1/p')
        [[ -z $event ]] && event=restored
        year=$(date +%Y)
        dst_dir=/var/lib/derbynet/$year/$event
        mkdir -p "$dst_dir"
        gunzip -c "$gz" > "$dst_dir/derbynet.sqlite3"
        chown www-data:www-data "$dst_dir/derbynet.sqlite3"
        chmod 0664 "$dst_dir/derbynet.sqlite3"
        log "restored $gz to $dst_dir/derbynet.sqlite3"
    done
    # Remove the restore directory so subsequent boots don't re-restore.
    rm -rf "$RESTORE_DIR"
    log "removed $RESTORE_DIR"
fi

# 3. Ensure the seeded skeleton DB has WAL + NORMAL set (no-op if already so).
if [[ -f /var/lib/derbynet/skeleton.sqlite3 ]]; then
    sqlite3 /var/lib/derbynet/skeleton.sqlite3 \
        "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;" >/dev/null
    log "skeleton DB pragmas verified"
fi

log "derbypi first-boot hook complete"

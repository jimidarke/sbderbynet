#!/bin/bash
# =============================================================================
# DerbyNet Log Rotation and Archival Script
# =============================================================================
#
# This script performs daily log maintenance:
# 1. Archives the previous day's JSONL file (compressed)
# 2. Records archive metadata in SQLite database
# 3. Purges old log entries from SQLite (3 days)
# 4. Deletes old archives (90 days)
# 5. Rotates traditional log files
#
# Designed to run via cron at 00:05 daily:
#   5 0 * * * /usr/local/bin/derby-log-rotate.sh >> /var/log/derbynet/rotation.log 2>&1
#
# Installation:
#   sudo cp derby-log-rotate.sh /usr/local/bin/
#   sudo chmod +x /usr/local/bin/derby-log-rotate.sh
#   sudo crontab -e  # Add the cron entry above
#
# Version: 1.0.0
# Date: 2025-12-08
# =============================================================================

set -e

# Configuration
LOG_DIR="${DERBY_LOG_DIR:-/var/log/derbynet}"
ARCHIVE_DIR="${DERBY_ARCHIVE_DIR:-/var/lib/derbynet/logs/archive}"
DB_PATH="${DERBY_DB_PATH:-/var/lib/derbynet/derbynet.sqlite3}"
RETENTION_DAYS="${DERBY_LOG_RETENTION_DAYS:-3}"
ARCHIVE_RETENTION_DAYS="${DERBY_ARCHIVE_RETENTION_DAYS:-90}"
POSITION_FILE="${DERBY_POSITION_FILE:-/var/lib/derbynet/log_import_position}"

# Files
JSONL_FILE="${LOG_DIR}/derby.jsonl"
TRADITIONAL_LOG="${LOG_DIR}/derby.log"

# Timestamp for logging
timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

log() {
    echo "[$(timestamp)] $1"
}

error() {
    echo "[$(timestamp)] ERROR: $1" >&2
}

# =============================================================================
# MAIN SCRIPT
# =============================================================================

log "=== DerbyNet Log Rotation Started ==="
log "Log Directory: ${LOG_DIR}"
log "Archive Directory: ${ARCHIVE_DIR}"
log "Database: ${DB_PATH}"
log "Retention: ${RETENTION_DAYS} days (active), ${ARCHIVE_RETENTION_DAYS} days (archive)"

# Create directories if needed
mkdir -p "${ARCHIVE_DIR}"
mkdir -p "${LOG_DIR}"

# Get yesterday's date for archiving
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d)
log "Archiving logs for: ${YESTERDAY}"

# =============================================================================
# STEP 1: Archive JSONL file
# =============================================================================

if [ -f "${JSONL_FILE}" ] && [ -s "${JSONL_FILE}" ]; then
    log "Archiving JSONL file..."

    # Count entries before archiving
    ENTRY_COUNT=$(wc -l < "${JSONL_FILE}" 2>/dev/null || echo "0")
    ARCHIVE_FILE="${ARCHIVE_DIR}/derby-${YESTERDAY}.jsonl.gz"

    # Compress the file (keeping original until we're sure it worked)
    if gzip -c "${JSONL_FILE}" > "${ARCHIVE_FILE}"; then
        FILE_SIZE=$(stat -f%z "${ARCHIVE_FILE}" 2>/dev/null || stat -c%s "${ARCHIVE_FILE}" 2>/dev/null || echo "0")

        log "Created archive: ${ARCHIVE_FILE} (${ENTRY_COUNT} entries, ${FILE_SIZE} bytes)"

        # Record in database
        if [ -f "${DB_PATH}" ]; then
            sqlite3 "${DB_PATH}" <<EOF
INSERT INTO LogArchive (archive_date, archive_file, entry_count, file_size)
VALUES ('${YESTERDAY}', '${ARCHIVE_FILE}', ${ENTRY_COUNT}, ${FILE_SIZE});
EOF
            log "Recorded archive in database"
        else
            log "Warning: Database not found at ${DB_PATH}"
        fi

        # Clear the JSONL file (truncate, keeping file handle for rsyslog)
        > "${JSONL_FILE}"

        # Reset the import position since we truncated the file
        if [ -f "${POSITION_FILE}" ]; then
            echo "0" > "${POSITION_FILE}"
            log "Reset import position file"
        fi

        log "JSONL file truncated"
    else
        error "Failed to create archive: ${ARCHIVE_FILE}"
    fi
else
    log "No JSONL file to archive or file is empty"
fi

# =============================================================================
# STEP 2: Purge old log entries from SQLite
# =============================================================================

if [ -f "${DB_PATH}" ]; then
    log "Purging old log entries (older than ${RETENTION_DAYS} days)..."

    CUTOFF_TIMESTAMP=$(($(date +%s) - (RETENTION_DAYS * 86400)))

    DELETED_COUNT=$(sqlite3 "${DB_PATH}" <<EOF
SELECT COUNT(*) FROM LogEntries WHERE created_at < ${CUTOFF_TIMESTAMP};
EOF
)

    if [ "${DELETED_COUNT}" -gt 0 ]; then
        sqlite3 "${DB_PATH}" "DELETE FROM LogEntries WHERE created_at < ${CUTOFF_TIMESTAMP};"
        log "Deleted ${DELETED_COUNT} old log entries"

        # Run VACUUM to reclaim space (only if we deleted something significant)
        if [ "${DELETED_COUNT}" -gt 1000 ]; then
            log "Running VACUUM to reclaim space..."
            sqlite3 "${DB_PATH}" "VACUUM;"
            log "VACUUM complete"
        fi
    else
        log "No old log entries to purge"
    fi
else
    log "Warning: Database not found at ${DB_PATH}"
fi

# =============================================================================
# STEP 3: Rotate traditional log file
# =============================================================================

if [ -f "${TRADITIONAL_LOG}" ] && [ -s "${TRADITIONAL_LOG}" ]; then
    log "Rotating traditional log file..."

    ROTATED_LOG="${LOG_DIR}/derby-${YESTERDAY}.log"

    # Move the log file
    mv "${TRADITIONAL_LOG}" "${ROTATED_LOG}"

    # Create new empty log file with proper permissions
    touch "${TRADITIONAL_LOG}"
    chmod 644 "${TRADITIONAL_LOG}"
    chown syslog:adm "${TRADITIONAL_LOG}" 2>/dev/null || true

    # Compress the rotated file
    gzip "${ROTATED_LOG}"
    log "Rotated and compressed: ${ROTATED_LOG}.gz"
else
    log "No traditional log to rotate or file is empty"
fi

# =============================================================================
# STEP 4: Delete old archives
# =============================================================================

log "Cleaning up old archives (older than ${ARCHIVE_RETENTION_DAYS} days)..."

# Find and delete old JSONL archives
OLD_ARCHIVES=$(find "${ARCHIVE_DIR}" -name "derby-*.jsonl.gz" -type f -mtime +${ARCHIVE_RETENTION_DAYS} 2>/dev/null || true)
if [ -n "${OLD_ARCHIVES}" ]; then
    echo "${OLD_ARCHIVES}" | while read archive; do
        rm -f "${archive}"
        log "Deleted old archive: ${archive}"
    done
fi

# Find and delete old traditional log archives
OLD_LOGS=$(find "${LOG_DIR}" -name "derby-*.log.gz" -type f -mtime +${RETENTION_DAYS} 2>/dev/null || true)
if [ -n "${OLD_LOGS}" ]; then
    echo "${OLD_LOGS}" | while read logfile; do
        rm -f "${logfile}"
        log "Deleted old log: ${logfile}"
    done
fi

# Update database to remove references to deleted archives
if [ -f "${DB_PATH}" ]; then
    ARCHIVE_CUTOFF=$(date -d "-${ARCHIVE_RETENTION_DAYS} days" +%Y-%m-%d 2>/dev/null || date -v-${ARCHIVE_RETENTION_DAYS}d +%Y-%m-%d)
    sqlite3 "${DB_PATH}" "DELETE FROM LogArchive WHERE archive_date < '${ARCHIVE_CUTOFF}';"
    log "Cleaned up old archive records from database"
fi

# =============================================================================
# STEP 5: Signal rsyslog to reopen files (if needed)
# =============================================================================

if systemctl is-active --quiet rsyslog; then
    log "Signaling rsyslog to reopen log files..."
    systemctl kill -s HUP rsyslog 2>/dev/null || true
fi

# =============================================================================
# DONE
# =============================================================================

log "=== Log Rotation Complete ==="

# Print summary
if [ -f "${DB_PATH}" ]; then
    TOTAL_ENTRIES=$(sqlite3 "${DB_PATH}" "SELECT COUNT(*) FROM LogEntries;" 2>/dev/null || echo "unknown")
    TOTAL_ARCHIVES=$(sqlite3 "${DB_PATH}" "SELECT COUNT(*) FROM LogArchive;" 2>/dev/null || echo "unknown")
    log "Summary: ${TOTAL_ENTRIES} active log entries, ${TOTAL_ARCHIVES} archives"
fi

exit 0

#!/bin/bash

# Cleanup script for HLS stream segment files
# Can be run manually or as a cron job

# Load configuration
CONFIG_FILE="/opt/hlsfeed/config.env"
if [ -f "$CONFIG_FILE" ]; then
  source "$CONFIG_FILE"
else
  echo "Error: Configuration file not found at $CONFIG_FILE"
  exit 1
fi

log() {
  echo "$(date +'%Y-%m-%d %H:%M:%S') [CLEANUP] $1" >> "$LOG_FILE"
  if [ "$2" = "console" ]; then
    echo "$1"
  fi
}

# Check if directory exists
if [ ! -d "$HLS_DIR" ]; then
  log "HLS directory $HLS_DIR does not exist" "console"
  exit 1
fi

# Count files before cleanup
FILES_BEFORE=$(find "$HLS_DIR" -name "*.ts" | wc -l)
SPACE_BEFORE=$(du -sh "$HLS_DIR" | awk '{print $1}')

log "Starting TS segment cleanup. Found $FILES_BEFORE files using $SPACE_BEFORE" "console"

# Delete old segment files
find "$HLS_DIR" -name "*.ts" -type f -mmin +$MAX_SEGMENT_AGE_MINUTES -delete

# Count files after cleanup
FILES_AFTER=$(find "$HLS_DIR" -name "*.ts" | wc -l)
SPACE_AFTER=$(du -sh "$HLS_DIR" | awk '{print $1}')
FILES_REMOVED=$((FILES_BEFORE - FILES_AFTER))

log "Cleanup complete. Removed $FILES_REMOVED files. Space now $SPACE_AFTER" "console"

# Clean up old log files if log rotation is enabled
if [ $LOG_RETENTION_DAYS -gt 0 ]; then
  LOG_DIR=$(dirname "$LOG_FILE")
  find "$LOG_DIR" -name "$(basename "$LOG_FILE")*" -type f -mtime +$LOG_RETENTION_DAYS -delete
  log "Removed log files older than $LOG_RETENTION_DAYS days" "console"
fi

exit 0
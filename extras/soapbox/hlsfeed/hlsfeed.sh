#!/bin/bash

# Load configuration
CONFIG_FILE="/opt/hlsfeed/config.env"
if [ -f "$CONFIG_FILE" ]; then
  source "$CONFIG_FILE"
else
  echo "Error: Configuration file not found at $CONFIG_FILE"
  exit 1
fi

# Create required directories
mkdir -p "$HLS_DIR"

# Ensure log file exists and has proper permissions
if [ ! -f "$LOG_FILE" ]; then
  touch "$LOG_FILE"
  chown www-data:www-data "$LOG_FILE"
fi

log() {
  echo "$(date +'%Y-%m-%d %H:%M:%S') [$LOG_LEVEL] $1" >> "$LOG_FILE"
}

cleanup_segments() {
  if [ -d "$HLS_DIR" ]; then
    log "Cleaning up TS segments older than $MAX_SEGMENT_AGE_MINUTES minutes"
    find "$HLS_DIR" -name "*.ts" -type f -mmin +$MAX_SEGMENT_AGE_MINUTES -delete
  fi
}

# Set up trap to handle exit
trap 'log "HLS feed service stopping"; exit 0' SIGTERM SIGINT

# Check disk space before starting
AVAILABLE_SPACE=$(df -h "$HLS_DIR" | awk 'NR==2 {print $4}')
log "Starting HLS stream service. Available space: $AVAILABLE_SPACE"
log "Using RTSP URL: ${RTSP_URL//:*@/:***@}" # Log URL but mask password

# Clean up any leftover segments from previous runs
cleanup_segments

# Start ffmpeg in a loop to handle crashes
while true; do
  log "Starting ffmpeg process"
  
  /usr/bin/ffmpeg -rtsp_transport tcp -i "$RTSP_URL" \
    -c:v libx264 -preset $VIDEO_PRESET -b:v $VIDEO_BITRATE -g $GOP_SIZE -sc_threshold 0 \
    -f hls -hls_time $HLS_SEGMENT_TIME -hls_list_size $HLS_LIST_SIZE -hls_flags delete_segments \
    "$HLS_DIR/stream.m3u8" >> "$LOG_FILE" 2>&1
  
  EXIT_CODE=$?
  
  if [ $EXIT_CODE -eq 0 ]; then
    log "FFmpeg exited normally"
  else
    log "FFmpeg exited with error code $EXIT_CODE. Restarting in 5 seconds..."
    sleep 5
  fi
  
  # Run cleanup routine
  cleanup_segments
  
  # Rotate log file if needed
  if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(du -m "$LOG_FILE" | cut -f1)
    if [ "$LOG_SIZE" -gt 50 ]; then
      mv "$LOG_FILE" "${LOG_FILE}.1"
      touch "$LOG_FILE"
      chown www-data:www-data "$LOG_FILE"
      log "Log file rotated due to size ($LOG_SIZE MB)"
    fi
  fi
done
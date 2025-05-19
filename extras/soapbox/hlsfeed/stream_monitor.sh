#!/bin/bash

# HLS Stream Health Monitor
# Checks the health of the stream and sends alerts when issues are detected

# Load configuration
CONFIG_FILE="/opt/hlsfeed/config.env"
if [ -f "$CONFIG_FILE" ]; then
  source "$CONFIG_FILE"
else
  echo "Error: Configuration file not found at $CONFIG_FILE"
  exit 1
fi

# Additional monitoring settings
METRICS_FILE="/var/log/hlsfeed_metrics.json"
ALERT_COUNT_FILE="/tmp/hlsfeed_alert_count"
MAX_ALERTS=3  # Maximum number of consecutive alerts before escalation
CHECK_INTERVAL=60  # Seconds between checks

log() {
  echo "$(date +'%Y-%m-%d %H:%M:%S') [MONITOR] $1" >> "$LOG_FILE"
  if [ "$2" = "console" ]; then
    echo "$1"
  fi
}

# Initialize metrics file if it doesn't exist
if [ ! -f "$METRICS_FILE" ]; then
  echo '{"last_update": "'$(date -Iseconds)'", "segments_count": 0, "stream_status": "unknown", "consecutive_failures": 0, "last_failure": null}' > "$METRICS_FILE"
fi

# Initialize alert count if it doesn't exist
if [ ! -f "$ALERT_COUNT_FILE" ]; then
  echo "0" > "$ALERT_COUNT_FILE"
fi

# Send alert message via MQTT
send_mqtt_alert() {
  local severity="$1"
  local message="$2"
  local timestamp=$(date -Iseconds)
  
  # Format JSON for MQTT
  local json="{\"timestamp\": \"$timestamp\", \"service\": \"hlsfeed\", \"severity\": \"$severity\", \"message\": \"$message\"}"
  
  # Send alert using mosquitto_pub if available
  if command -v mosquitto_pub &> /dev/null; then
    mosquitto_pub -h 192.168.100.10 -t "derbynet/alerts" -m "$json"
    log "Alert sent via MQTT: $message"
  else
    log "Could not send MQTT alert: mosquitto_pub not available"
  fi
}

check_process() {
  # Check if ffmpeg is running
  if pgrep -f "ffmpeg.*$RTSP_URL" > /dev/null; then
    echo "running"
  else
    echo "stopped"
  fi
}

check_segments() {
  # Check if new segments are being created
  local newest_segment=$(find "$HLS_DIR" -name "*.ts" -type f -printf '%T@ %p\n' | sort -nr | head -1)
  
  if [ -z "$newest_segment" ]; then
    echo "none"
    return
  fi
  
  # Extract timestamp from the result
  local segment_time=$(echo "$newest_segment" | cut -d' ' -f1 | cut -d'.' -f1)
  local current_time=$(date +%s)
  local age=$((current_time - segment_time))
  
  # Count segments
  local segments_count=$(find "$HLS_DIR" -name "*.ts" | wc -l)
  
  # Check if segments are being updated (should have new segments every few seconds)
  if [ $age -gt 30 ]; then
    echo "stale,$segments_count,$age"
  else
    echo "fresh,$segments_count,$age"
  fi
}

check_playlist() {
  # Check if playlist file exists and is valid
  local playlist="$HLS_DIR/stream.m3u8"
  
  if [ ! -f "$playlist" ]; then
    echo "missing"
    return
  fi
  
  # Check if playlist has entries
  local entries=$(grep -c "\.ts" "$playlist")
  if [ $entries -eq 0 ]; then
    echo "empty"
  else
    echo "valid,$entries"
  fi
}

update_metrics() {
  local process_status="$1"
  local segments_info="$2"
  local playlist_status="$3"
  
  # Parse segment info
  local segment_status=$(echo "$segments_info" | cut -d',' -f1)
  local segments_count=$(echo "$segments_info" | cut -d',' -f2 2>/dev/null || echo "0")
  local segment_age=$(echo "$segments_info" | cut -d',' -f3 2>/dev/null || echo "0")
  
  # Parse playlist info
  local playlist_valid=$(echo "$playlist_status" | cut -d',' -f1)
  local playlist_entries=$(echo "$playlist_status" | cut -d',' -f2 2>/dev/null || echo "0")
  
  # Determine overall status
  local stream_status="healthy"
  local failures=0
  
  if [ "$process_status" != "running" ]; then
    stream_status="error_process_not_running"
    failures=$((failures + 1))
  fi
  
  if [ "$segment_status" = "none" ] || [ "$segment_status" = "stale" ]; then
    stream_status="error_no_new_segments"
    failures=$((failures + 1))
  fi
  
  if [ "$playlist_valid" != "valid" ]; then
    stream_status="error_invalid_playlist"
    failures=$((failures + 1))
  fi
  
  # Read previous consecutive failures
  local prev_failures=$(jq '.consecutive_failures' "$METRICS_FILE" 2>/dev/null || echo "0")
  
  # Update consecutive failures counter
  if [ $failures -gt 0 ]; then
    consecutive_failures=$((prev_failures + 1))
    last_failure=$(date -Iseconds)
  else
    consecutive_failures=0
    last_failure=$(jq -r '.last_failure' "$METRICS_FILE" 2>/dev/null || echo "null")
    [ "$last_failure" = "null" ] && last_failure=null  # Ensure proper JSON null
  fi
  
  # Update metrics file
  cat > "$METRICS_FILE" << EOF
{
  "last_update": "$(date -Iseconds)",
  "process_status": "$process_status",
  "segments_count": $segments_count,
  "segment_status": "$segment_status",
  "segment_age": $segment_age,
  "playlist_status": "$playlist_valid",
  "playlist_entries": $playlist_entries,
  "stream_status": "$stream_status",
  "consecutive_failures": $consecutive_failures,
  "last_failure": $last_failure
}
EOF

  # Log the update
  log "Updated metrics: process=$process_status segments=$segment_status playlist=$playlist_valid status=$stream_status"
  
  return $failures
}

handle_alerts() {
  local failures=$1
  
  if [ $failures -gt 0 ]; then
    # Read alert count
    local alert_count=$(<"$ALERT_COUNT_FILE")
    alert_count=$((alert_count + 1))
    echo $alert_count > "$ALERT_COUNT_FILE"
    
    # Get stream status from metrics file
    local stream_status=$(jq -r '.stream_status' "$METRICS_FILE")
    
    # Send alert based on count
    if [ $alert_count -eq 1 ]; then
      # First alert - warning
      send_mqtt_alert "warning" "HLS stream issue detected: $stream_status"
      log "Warning: Stream issue detected: $stream_status" "console"
    elif [ $alert_count -ge $MAX_ALERTS ]; then
      # Critical alert and attempt recovery
      send_mqtt_alert "critical" "HLS stream failure: $stream_status - attempting recovery"
      log "Critical: Stream failure: $stream_status - attempting recovery" "console"
      
      # Try to restart the service
      systemctl restart hlsfeed.service
      
      # Reset alert count after recovery attempt
      echo "0" > "$ALERT_COUNT_FILE"
    else
      # Intermediate alerts
      log "Stream issue continues: $stream_status (Alert $alert_count/$MAX_ALERTS)" "console"
    fi
  else
    # Stream is healthy, reset alert count
    if [ -f "$ALERT_COUNT_FILE" ] && [ $(<"$ALERT_COUNT_FILE") -gt 0 ]; then
      # Send recovery alert if we were previously in alert state
      send_mqtt_alert "info" "HLS stream has recovered"
      log "Info: Stream has recovered" "console"
    fi
    
    echo "0" > "$ALERT_COUNT_FILE"
  fi
}

# Main monitoring loop
if [ "$1" = "--daemon" ]; then
  log "Starting stream monitor daemon" "console"
  
  while true; do
    process_status=$(check_process)
    segments_info=$(check_segments)
    playlist_status=$(check_playlist)
    
    update_metrics "$process_status" "$segments_info" "$playlist_status"
    failures=$?
    
    handle_alerts $failures
    
    sleep $CHECK_INTERVAL
  done
else
  # Single check mode
  process_status=$(check_process)
  segments_info=$(check_segments)
  playlist_status=$(check_playlist)
  
  update_metrics "$process_status" "$segments_info" "$playlist_status"
  failures=$?
  
  handle_alerts $failures
  
  # Output current status
  jq '.' "$METRICS_FILE"
fi

exit 0
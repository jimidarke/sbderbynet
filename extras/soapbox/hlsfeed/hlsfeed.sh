#!/bin/bash

LOG_FILE="/opt/hlsfeed/hls.log"
HLS_DIR="/opt/hlsfeed/hls"
RTSP_URL="rtsp://admin:all4theKids@192.168.100.20:554/21"

echo "$(date): Starting HLS stream from $RTSP_URL" >> "$LOG_FILE"

/usr/bin/ffmpeg -rtsp_transport tcp -i "$RTSP_URL" \
  -c:v libx264 -preset veryfast -g 25 -sc_threshold 0 \
  -f hls -hls_time 2 -hls_list_size 5 -hls_flags delete_segments \
  "$HLS_DIR/stream.m3u8" >> "$LOG_FILE" 2>&1

echo "$(date): FFmpeg exited" >> "$LOG_FILE"

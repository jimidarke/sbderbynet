#!/bin/bash
mkdir -p static/hls1 static/hls2

# Replace with your RTSP URLs
RTSP1="rtsp://admin:admin@192.168.100.20:554/11"
RTSP2="rtsp://admin:admin@192.168.100.20:554/22"

# First stream
ffmpeg -i "$RTSP1" -c:v copy -f hls -hls_time 2 -hls_list_size 3 -hls_flags delete_segments static/hls1/stream.m3u8 &

# Second stream
ffmpeg -i "$RTSP2" -c:v copy -f hls -hls_time 2 -hls_list_size 3 -hls_flags delete_segments static/hls2/stream.m3u8 &
 
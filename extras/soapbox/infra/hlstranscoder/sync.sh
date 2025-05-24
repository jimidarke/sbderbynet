#!/bin/bash
# HLS Transcoder Sync Script
# Version: 0.5.0
# This script synchronizes the HLS Transcoder files from the rsync server

# Default settings
SERVER_ADDRESS="${1:-192.168.100.10}"
RSYNC_MODULE="${2:-derbynet}"
INSTALL_DIR="/opt/hlstranscoder"

echo "Syncing HLS Transcoder files from $SERVER_ADDRESS..."
sudo /opt/hlstranscoder/setup.sh --update --server "$SERVER_ADDRESS" --rsync-module "$RSYNC_MODULE"

# Check result
if [ $? -eq 0 ]; then
    echo "Sync successful. HLS Transcoder service has been restarted."
else
    echo "Sync failed. Check server availability and network connectivity."
    exit 1
fi
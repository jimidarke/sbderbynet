#!/bin/bash
# HLS Transcoder Kiosk Script
# Version: 0.5.0
# This script sets up a kiosk mode browser for the HLS Transcoder status page

# Load configuration
CONFIG_FILE="/etc/hlstranscoder/config.env"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Default URL if not set in config
URL="${KIOSK_URL:-http://localhost/status.html}"

# Wait for network connectivity
for i in {1..30}; do
    if ping -c 1 derbynetpi.local &> /dev/null || ping -c 1 8.8.8.8 &> /dev/null; then
        break
    fi
    echo "Waiting for network..."
    sleep 2
done

# Wait a bit more for services to start
sleep 10

# Turn off screensaver and power management
xset s off
xset -dpms
xset s noblank

# Hide cursor
unclutter -idle 0.1 -root &

# Start Chromium in kiosk mode
chromium-browser --noerrdialogs --disable-infobars --kiosk "$URL" &

# Keep script running
while true; do
    # Check if chromium is running
    if ! pgrep -x "chromium" > /dev/null; then
        echo "Restarting Chromium..."
        chromium-browser --noerrdialogs --disable-infobars --kiosk "$URL" &
    fi
    
    # Check if URL has changed in config
    if [ -f "$CONFIG_FILE" ]; then
        NEW_URL=$(grep "KIOSK_URL" "$CONFIG_FILE" | cut -d= -f2 | tr -d '"')
        if [ ! -z "$NEW_URL" ] && [ "$NEW_URL" != "$URL" ]; then
            echo "URL changed, restarting Chromium with new URL: $NEW_URL"
            URL="$NEW_URL"
            pkill chromium
            sleep 2
            chromium-browser --noerrdialogs --disable-infobars --kiosk "$URL" &
        fi
    fi
    
    sleep 30
done
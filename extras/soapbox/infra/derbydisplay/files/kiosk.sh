#!/bin/bash

URL="http://192.168.100.10/derbynet/kiosk.php"
LOGFILE="/home/derby/derbykiosk.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Starting Midori kiosk..." >> $LOGFILE

sleep 60

# Start Midori in fullscreen and loop to restart it if it crashes
while true; do
    # Clear any previous Midori processes just in case
    pkill -f midori

    # Launch Midori in fullscreen mode
    midori -e Fullscreen "$URL" &>> $LOGFILE &

    MIDORI_PID=$!

    # Wait for the process to exit
    wait $MIDORI_PID

    DATE=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$DATE] Midori exited, restarting..." >> $LOGFILE

    # Wait a moment before restarting
    sleep 2
done

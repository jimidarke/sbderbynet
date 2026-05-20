#!/bin/bash
# DerbyDisplay kiosk xinitrc — launches Chromium and respawns it if it crashes.
# Baked into the derbydisplay image; runs as the kioskuser via getty autologin.

export DISPLAY=:0
LOADING=/opt/derbynet/loading.png
ERROR=/opt/derbynet/error.png
BASE_URL="http://192.168.100.10/derbynet/kiosk.php?address="
URL_FILE=/opt/derbynet/url.txt

# Allow operator override (drop a file into /opt/derbynet/url.txt to point elsewhere)
if [[ -f $URL_FILE ]]; then
    BASE_URL=$(< "$URL_FILE")
fi

# Hide cursor
unclutter-xfixes --timeout 0 --hide-on-touch &

# Splash while we wait for the server
feh --fullscreen --hide-pointer "$LOADING" 2>/dev/null &
FEH_PID=$!

# Wait up to 60s for the race server, show error splash if it never comes up
ready=false
for _ in $(seq 1 60); do
    if curl -sS -o /dev/null --max-time 1 "http://192.168.100.10/derbynet/" ; then
        ready=true
        break
    fi
    sleep 1
done

kill "$FEH_PID" 2>/dev/null || true

if [[ $ready != true ]]; then
    feh --fullscreen --hide-pointer "$ERROR" 2>/dev/null &
    sleep 30
fi

# MAC = our kiosk identity for the dispatcher
MAC=$(cat /sys/class/net/eth0/address 2>/dev/null || \
      cat /sys/class/net/wlan0/address 2>/dev/null || echo NOMAC)

CHROMIUM=$(command -v chromium-browser || command -v chromium)

# Respawn loop: if Chromium ever exits, restart it after 2s.
# Per audit P1 #8 — without this, a Chromium crash leaves a black screen
# until the next physical reboot.
while true; do
    "$CHROMIUM" \
        --noerrdialogs --kiosk --start-fullscreen \
        --window-size=1920,1080 --window-position=0,0 \
        --force-device-scale-factor=1.0 \
        --disable-gpu-sandbox --disable-software-rasterizer \
        --disable-background-timer-throttling \
        --disable-renderer-backgrounding \
        --disable-backgrounding-occluded-windows \
        --disable-features=TranslateUI --no-sandbox --incognito \
        "${BASE_URL}${MAC}" >> /var/log/derbynet/chromium.log 2>&1
    echo "[$(date -Iseconds)] chromium exited; restarting" >> /var/log/derbynet/chromium.log
    sleep 2
done

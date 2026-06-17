#!/bin/bash
# DerbyDisplay kiosk xinitrc — launches Chromium and respawns it if it crashes.
# Baked into the derbydisplay image; runs as the kioskuser via getty autologin.

export DISPLAY=:0
LOADING=/opt/derbynet/loading.png
ERROR=/opt/derbynet/error.png

# Server address is operator-editable on the FAT bootfs (Windows-friendly):
#   /boot/firmware/derby-server.txt -> host/IP (default 192.168.100.10)
#   /boot/firmware/derby-url.txt    -> optional FULL url, loaded verbatim
HOST=$(/usr/local/sbin/derby-server-host)

# Optional full-URL override: first non-comment, non-blank line of derby-url.txt
# (CR stripped, trimmed). When set it is used EXACTLY as written.
URL_OVERRIDE=$(awk '
    { sub(/\r$/, ""); gsub(/^[[:space:]]+|[[:space:]]+$/, "") }
    /^$/ || /^#/ { next }
    { print; exit }
' /boot/firmware/derby-url.txt 2>/dev/null)

# Hide cursor
unclutter-xfixes --timeout 0 --hide-on-touch &

# MAC = our kiosk identity for the dispatcher
MAC=$(cat /sys/class/net/eth0/address 2>/dev/null || \
      cat /sys/class/net/wlan0/address 2>/dev/null || echo NOMAC)

if [[ -n $URL_OVERRIDE ]]; then
    # Verbatim override (e.g. a remote/cloud server): no MAC appended, no probe.
    FINAL_URL="$URL_OVERRIDE"
    # Brief splash so the screen isn't black while Chromium starts.
    feh --fullscreen --hide-pointer "$LOADING" 2>/dev/null &
    FEH_PID=$!
    sleep 3
    kill "$FEH_PID" 2>/dev/null || true
else
    FINAL_URL="http://${HOST}/derbynet/kiosk.php?address=${MAC}"
    # Splash while we wait for the race server
    feh --fullscreen --hide-pointer "$LOADING" 2>/dev/null &
    FEH_PID=$!
    # Wait up to 60s for the race server, show error splash if it never comes up
    ready=false
    for _ in $(seq 1 60); do
        if curl -sS -o /dev/null --max-time 1 "http://${HOST}/derbynet/" ; then
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
fi

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
        "$FINAL_URL" >> /var/log/derbynet/chromium.log 2>&1
    echo "[$(date -Iseconds)] chromium exited; restarting" >> /var/log/derbynet/chromium.log
    sleep 2
done

#!/bin/bash
# derby-firstboot-finishtimer.sh — runs once on the first boot of a fresh
# finishtimer SD card. Reads DIP switches to determine lane number and
# writes it into /boot/firmware/derbyid.txt if the operator left it blank.
#
# The DIP-switch GPIOs (BCM 6/13/19/26 active-low) are read via /sys/class/gpio
# so we don't need RPi.GPIO at first-boot time.

set -uo pipefail
LOG=/var/log/derby-firstboot.log
log() { echo "[$(date -Iseconds)] [finishtimer] $*" | tee -a "$LOG"; }

# 1. Read DIP switches
read_dip() {
    local pin=$1
    if [[ ! -d /sys/class/gpio/gpio$pin ]]; then
        echo $pin > /sys/class/gpio/export 2>/dev/null || true
        echo in > /sys/class/gpio/gpio$pin/direction 2>/dev/null || true
        sleep 0.05
    fi
    # active-low: invert the read value
    local v
    v=$(< /sys/class/gpio/gpio$pin/value)
    if [[ $v == 0 ]]; then echo 1; else echo 0; fi
}

D1=$(read_dip 6)
D2=$(read_dip 13)
D3=$(read_dip 19)
D4=$(read_dip 26)
DIP="$D1$D2$D3$D4"
log "DIP read: $DIP"

# Map DIP to lane per derbynetPCBv1.py:get_Lane()
case "$DIP" in
    1000) LANE=1 ;;
    1001) LANE=2 ;;
    1010) LANE=3 ;;
    1011) LANE=4 ;;
    *)    LANE=0 ;;
esac
log "lane=$LANE"

# 2. If derbyid.txt is still the placeholder, generate FT00<lane>
ID_FILE=/boot/firmware/derbyid.txt
CURRENT=$(tr -d '[:space:]' < "$ID_FILE" 2>/dev/null || echo "")
if [[ $CURRENT == CHANGE-ME || $CURRENT == "" ]]; then
    if [[ $LANE -gt 0 ]]; then
        echo "FT00$LANE" > "$ID_FILE"
        log "derbyid auto-set to FT00$LANE"
    else
        log "WARN: DIP=$DIP not a valid lane code; derbyid left as placeholder"
    fi
else
    log "derbyid already operator-set to $CURRENT; leaving alone"
fi

log "finishtimer first-boot hook complete"

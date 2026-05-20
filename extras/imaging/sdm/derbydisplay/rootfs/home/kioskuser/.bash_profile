# Auto-launch X on tty1 for kiosk display.
if [[ -z $DISPLAY && $XDG_VTNR -eq 1 ]]; then
    exec startx -- -nocursor
fi

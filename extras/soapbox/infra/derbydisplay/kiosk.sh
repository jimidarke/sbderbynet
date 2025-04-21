#!/bin/bash
# Kiosk Setup Script - Console Autologin Version for Raspberry Pi OS Lite

### Configuration ###
WEB_URL="http://192.168.100.10/derbynet/kiosk.php?address="
LOADING_IMAGE="/opt/derbynet/loading.png"
ERROR_IMAGE="/opt/derbynet/error.png"
KIOSK_USER="kioskuser"
LOG_FILE="/var/log/kiosk-install.log"

### Initialization ###
exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== Starting Kiosk Installation $(date) ==="

### System Checks ###
[ "$(id -u)" -ne 0 ] && { echo "ERROR: Must be run as root" >&2; exit 1; }

### Verify Images ###
check_images() {
    [ -f "$LOADING_IMAGE" ] || { echo "ERROR: Missing $LOADING_IMAGE" >&2; exit 1; }
    [ -f "$ERROR_IMAGE" ] || { echo "ERROR: Missing $ERROR_IMAGE" >&2; exit 1; }
    echo "Found both splash screen images"
}

### System Configuration ###
setup_system() {
    echo "--- Configuring System ---"

    if ! id "$KIOSK_USER" &>/dev/null; then
        useradd -m -G video,input,render,tty "$KIOSK_USER" || {
            echo "ERROR: Failed to create user" >&2
            exit 1
        }
    fi

    echo "$KIOSK_USER ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/kioskuser
    chmod 440 /etc/sudoers.d/kioskuser

    mkdir -p /opt/kiosk/splash
    chown "$KIOSK_USER:$KIOSK_USER" /opt/kiosk

    # Fix X Server permissions
    echo -e "allowed_users=anybody\nneeds_root_rights=yes" > /etc/X11/Xwrapper.config
}

setup_kiosk_app_v2(){
    echo "--- Configuring Kiosk App ---"
    cat > /home/"$KIOSK_USER"/.xinitrc <<'EOL'
#!/bin/bash
# Set display
export DISPLAY=:0

# Paths
LOADING="/opt/derbynet/loading.png"
ERROR="/opt/derbynet/error.png"
URL_FILE="/opt/derbynet/url.txt"
BASE_URL="http://192.168.100.10/derbynet/kiosk.php?address="

# Determine final URL
if [[ -f "$URL_FILE" ]]; then
    CUSTOM_URL=$(cat "$URL_FILE")
    URL="${CUSTOM_URL:-$BASE_URL}"
else
    URL="$BASE_URL"
fi

# Detect Chromium binary
CHROMIUM=$(command -v chromium-browser || command -v chromium)
if [[ -z "$CHROMIUM" ]]; then
    echo "ERROR: Chromium not found"
    exit 1
fi

# Show loading screen
feh --fullscreen --hide-pointer "$LOADING" &
FEH_PID=$!
sleep 3  # shorter, tweak if you need more buffer

# Get MAC address (first available NIC)
MAC=$(cat /sys/class/net/eth0/address 2>/dev/null || \
      cat /sys/class/net/wlan0/address 2>/dev/null || \
      echo "NOMAC")

# Wait for network connection (ping gateway)
NETWORK_READY=false
for i in {1..30}; do
    if ping -c1 -W1 192.168.100.10 >/dev/null 2>&1; then
        NETWORK_READY=true
        break
    fi
    sleep 1
done

# Act based on network state
if $NETWORK_READY; then
    kill "$FEH_PID" 2>/dev/null
    sleep 0.5
    # Hide mouse cursor
    unclutter-xfixes --timeout 0 --hide-on-touch &
    # Launch browser in kiosk mode
    #exec "$CHROMIUM" --noerrdialogs --kiosk --incognito "${URL}${MAC}"
    exec "$CHROMIUM" --noerrdialogs --kiosk --start-fullscreen --window-size=1920,1080 --no-sandbox --incognito "${URL}${MAC}" >> ~/kiosk.log 2>&1

else
    kill "$FEH_PID" 2>/dev/null
    feh --fullscreen --hide-pointer "$ERROR" &
    echo "Network failed to connect after 30s" >> ~/kiosk.log
    sleep 30
    exit 1
fi

EOL
    chown "$KIOSK_USER:$KIOSK_USER" /home/"$KIOSK_USER"/.xinitrc
    chmod +x /home/"$KIOSK_USER"/.xinitrc
}

### Kiosk Application ###
setup_kiosk_app() {
    echo "--- Configuring Kiosk App ---"
    cat > /home/"$KIOSK_USER"/.xinitrc <<'EOL'
#!/bin/bash
# Set display environment
export DISPLAY=:0

# Configuration
LOADING="/opt/derbynet/loading.png"
ERROR="/opt/derbynet/error.png"
URL="http://192.168.100.10/derbynet/kiosk.php?address="

if [ ! -f /opt/derbynet/url.txt ]; then
    URL="http://192.168.100.10/derbynet/kiosk.php?address="
else
    URL=$(cat /opt/derbynet/url.txt)
fi

# Find Chromium
CHROMIUM=$(which chromium-browser || which chromium)
[ -z "$CHROMIUM" ] && { echo "ERROR: Chromium not found"; exit 1; }

# Show loading screen
feh --fullscreen --hide-pointer "$LOADING" &
sleep 10
FEH_PID=$!

# Get MAC address
MAC=$(cat /sys/class/net/eth0/address 2>/dev/null || cat /sys/class/net/wlan0/address 2>/dev/null)
[ -z "$MAC" ] && MAC="NOMAC"

# Network check (ping + HTTP)
SUCCESS=false #true
# Wait for network connection
count=0
while [ \$count -lt 30 ]; do
    ping -c1 192.168.100.10 >/dev/null 2>&1 && SUCCESS=true && break
    sleep 1
    count=\$((count+1))
done

if $SUCCESS; then
    kill $FEH_PID 2>/dev/null
    sleep 0.5
    unclutter-xfixes --timeout 0 --hide-on-touch &
    exec "$CHROMIUM" --noerrdialogs --kiosk --incognito "${URL}${MAC}"
else
    kill $FEH_PID 2>/dev/null
    feh --fullscreen --hide-pointer "$ERROR" &
    sleep 30
    exit 1
fi

EOL

    chown "$KIOSK_USER:$KIOSK_USER" /home/"$KIOSK_USER"/.xinitrc
    chmod +x /home/"$KIOSK_USER"/.xinitrc
}

### Console Autologin Configuration ###
setup_autologin() {
    echo "--- Configuring Console Autologin ---"
    
    # Configure autologin for tty1
    mkdir -p /etc/systemd/system/getty@tty1.service.d
    cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<'EOL'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin kioskuser --noclear %I $TERM
EOL

    # Create autostart script
    cat > /etc/profile.d/kiosk.sh <<'EOL'
#!/bin/sh
if [ "$(tty)" = "/dev/tty1" ] && [ "$USER" = "kioskuser" ]; then
    exec startx /home/kioskuser/.xinitrc -- -keeptty -verbose 3
fi
EOL

    chmod +x /etc/profile.d/kiosk.sh
}

setup_screensleep(){
    # Disable screen blanking and power management
    echo "Disabling screen blanking..."
    cat > /etc/X11/xorg.conf.d/10-disable-screensaver.conf <<EOL
Section "ServerFlags"
    Option "BlankTime" "0"
    Option "StandbyTime" "0"
    Option "SuspendTime" "0"
    Option "OffTime" "0"
EndSection
EOL

    # Disable sleep modes
    echo "Disabling system sleep modes..."
    systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
}

### Main Execution ###
{
    check_images
    setup_system
    setup_kiosk_app
    setup_autologin
    setup_screensleep
}

echo "=== Installation Complete ==="

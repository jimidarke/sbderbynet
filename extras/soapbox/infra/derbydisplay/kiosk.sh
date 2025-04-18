#!/bin/bash
# Kiosk Setup Script - Console Autologin Version for Raspberry Pi OS Lite

### Configuration ###
WEB_URL="http://192.168.100.10/derbynet/kiosk.php?address=MAC"
LOADING_IMAGE="/opt/kiosk/splash/image-loading.png"
ERROR_IMAGE="/opt/kiosk/splash/image-error.png"
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

### Install Dependencies ###
install_dependencies() {
    echo "--- Installing Packages ---"
    apt update || { echo "ERROR: Failed to update packages" >&2; exit 1; }
    apt install -y --no-install-recommends \
        chromium-browser \
        xserver-xorg \
        xinit \
        x11-xserver-utils \
        openbox \
        unclutter \
        feh \
        upower \
        dbus || {
            echo "ERROR: Package installation failed" >&2
            exit 1
        }
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

### Kiosk Application ###
setup_kiosk_app() {
    echo "--- Configuring Kiosk App ---"
    cat > /home/"$KIOSK_USER"/.xinitrc <<'EOL'
#!/bin/bash
# Set display environment
export DISPLAY=:0

# Configuration
LOADING="/opt/kiosk/splash/image-loading.png"
ERROR="/opt/kiosk/splash/image-error.png"
URL="http://192.168.100.10/derbynet/kiosk.php?address=MAC"
HOST="127.0.0.1"  # Adresse IP du serveur

# Find Chromium
CHROMIUM=$(which chromium-browser || which chromium)
[ -z "$CHROMIUM" ] && { echo "ERROR: Chromium not found"; exit 1; }

# Show loading screen
feh --fullscreen --hide-pointer "$LOADING" &
sleep 10
FEH_PID=$!

# Get MAC address
MAC=$(cat /sys/class/net/eth0/address 2>/dev/null || cat /sys/class/net/wlan0/address 2>/dev/null | tr -d ':')
[ -z "$MAC" ] && MAC="NOMAC"

# Network check (ping + HTTP)
SUCCESS=false
for ((i=1; i<=15; i++)); do
    if ping -c1 -W2 "$HOST" >/dev/null && \
       curl -s -I --connect-timeout 2 "http://$HOST" >/dev/null; then
        SUCCESS=true
        break
    fi
    sleep 1
done

if $SUCCESS; then
    kill $FEH_PID 2>/dev/null
    sleep 0.5
    exec "$CHROMIUM" --noerrdialogs --kiosk --incognito --disable-gpu "${URL/MAC/$MAC}"
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

### Main Execution ###
{
    check_images
    install_dependencies
    setup_system
    setup_kiosk_app
    setup_autologin
}

echo "=== Installation Complete ==="
echo "System will reboot to apply changes..."
sleep 3
reboot
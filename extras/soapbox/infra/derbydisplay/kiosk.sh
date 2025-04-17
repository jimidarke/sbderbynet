#!/bin/bash

# Kiosk Setup Script
# Configures a device to display a webpage with MAC address as URL parameter
# Includes splash screens and error handling

# Configuration variables
WEB_URL="http://192.168.100.10/derbynet/kiosk.php"  
LOADING_IMAGE="/opt/kiosk/splash/loading.png"
ERROR_IMAGE="/opt/kiosk/splash/error.png"
KIOSK_USER="kioskuser"
DESKTOP_ENV="xfce"  

# Check if script is run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root" >&2
    exit 1
fi

# Install required packages
echo "Installing required packages..."
apt-get update
apt-get install -y --no-install-recommends \
    xserver-xorg x11-xserver-utils xinit \
    unclutter chromium \
    lightdm xinit openbox \
    feh sudo

# Create kiosk user if not exists
if ! id "$KIOSK_USER" &>/dev/null; then
    echo "Creating kiosk user..."
    useradd -m -G audio,video,input "$KIOSK_USER"
    echo "$KIOSK_USER ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/010_kioskuser
fi

# Create splash screen directory
echo "Setting up splash screens..."
mkdir -p /opt/kiosk/splash
# You should place your loading.png and error.png in this directory
# For now we'll create simple placeholder images
wget http://192.168.100.10/derbynet/loading.png -O /opt/kiosk/splash/loading.png
wget http://192.168.100.10/derbynet/error.png -O /opt/kiosk/splash/error.png
#convert -size 800x480 xc:navy /opt/kiosk/splash/loading.png
#convert -size 800x480 xc:maroon /opt/kiosk/splash/error.png
chown -R "$KIOSK_USER:$KIOSK_USER" /opt/kiosk

# Configure lightdm to auto-login
echo "Configuring lightdm for auto-login..."
cat > /etc/lightdm/lightdm.conf <<EOL
[SeatDefaults]
autologin-user=$KIOSK_USER
autologin-user-timeout=0
user-session=$DESKTOP_ENV
EOL

# Create xinit script
echo "Creating xinit script..."
cat > /home/$KIOSK_USER/.xinitrc <<EOL
#!/bin/sh

# Display loading screen
feh --fullscreen --hide-pointer $LOADING_IMAGE &

# Get MAC address
MAC=\$(cat /sys/class/net/eth0/address 2>/dev/null || cat /sys/class/net/wlan0/address 2>/dev/null)
MAC=\${MAC//:/}

# Wait for network connection
count=0
while [ \$count -lt 30 ]; do
    ping -c1 example.com >/dev/null 2>&1 && break
    sleep 1
    count=\$((count+1))
done

# Launch browser or show error
if [ \$count -lt 30 ]; then
    # Network is up, launch browser
    pkill feh  # Close loading screen
    exec chromium-browser \\
        --noerrdialogs \\
        --disable-infobars \\
        --kiosk \\
        --incognito \\
        --disable-translate \\
        --disable-features=TranslateUI \\
        --disk-cache-dir=/dev/null \\
        --disable-pinch \\
        --overscroll-history-navigation=0 \\
        --disable-session-crashed-bubble \\
        --disable-component-update \\
        --check-for-update-interval=31536000 \\
        "$WEB_URL?mac=\$MAC"
else
    # Network failed, show error
    pkill feh
    feh --fullscreen --hide-pointer $ERROR_IMAGE
fi
EOL

chown "$KIOSK_USER:$KIOSK_USER" /home/$KIOSK_USER/.xinitrc
chmod +x /home/$KIOSK_USER/.xinitrc

# Configure autostart
echo "Configuring autostart..."
mkdir -p /home/$KIOSK_USER/.config/autostart
cat > /home/$KIOSK_USER/.config/autostart/kiosk.desktop <<EOL
[Desktop Entry]
Type=Application
Name=Kiosk
Exec=startx
EOL

chown -R "$KIOSK_USER:$KIOSK_USER" /home/$KIOSK_USER/.config

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

# Configure Chromium policies for better kiosk performance
echo "Configuring Chromium policies..."
mkdir -p /etc/chromium-browser/policies/managed
cat > /etc/chromium-browser/policies/managed/kiosk_policy.json <<EOL
{
    "AutoSelectCertificateForUrls": [{"pattern":"*","filter":{"ISSUER":{"CN":"*"}}}],
    "DefaultNotificationsSetting": 2,
    "DefaultPopupsSetting": 2,
    "DefaultGeolocationSetting": 2,
    "DefaultWebBluetoothGuardSetting": 2,
    "PasswordManagerEnabled": false,
    "TranslateEnabled": false,
    "ImportAutofillFormData": false,
    "ImportBrowserTheme": false,
    "ImportBookmarks": false,
    "ImportHistory": false,
    "ImportHomepage": false,
    "ImportSearchEngine": false,
    "ImportSavedPasswords": false,
    "ImportCookies": false,
    "RestoreOnStartup": 0,
    "RestoreOnStartupURLs": [],
    "HomepageLocation": "$WEB_URL",
    "HardwareAccelerationModeEnabled": true,
    "AllowDeletingBrowserHistory": false,
    "AllowDinosaurEasterEgg": false,
    "BrowserAddPersonEnabled": false,
    "BrowserGuestModeEnabled": false,
    "SpellcheckServiceEnabled": false
}
EOL

# Enable hardware acceleration for video playback
echo "Configuring hardware acceleration..."
cat > /etc/chromium-browser/customizations/01-accelerate <<EOL
CHROMIUM_FLAGS="\${CHROMIUM_FLAGS} --ignore-gpu-blocklist --enable-gpu-rasterization --enable-zero-copy --enable-native-gpu-memory-buffers --enable-accelerated-video-decode"
EOL

# Clean up
echo "Cleaning up..."
apt-get autoremove -y
apt-get clean

# Création du service système (nouveau)
echo "Creating systemd service..."
cat > /etc/systemd/system/kiosk.service <<EOL
[Unit]
Description=Kiosk Mode
After=lightdm.service
Wants=lightdm.service

[Service]
User=$KIOSK_USER
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/$KIOSK_USER/.Xauthority
ExecStart=/bin/bash /home/$KIOSK_USER/.xinitrc
Restart=on-abort
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOL

# Activation du service
systemctl daemon-reload
systemctl enable kiosk.service

echo "Setup complete!"
echo "The kiosk will start automatically on next boot."
echo "To start it now manually: sudo systemctl start kiosk"
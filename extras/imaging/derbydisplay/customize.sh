#!/bin/bash
# extras/imaging/derbydisplay/customize.sh
#
# Bakes the Pi 3 B+ kiosk image:
#   - Chromium kiosk on tty1 with auto-respawn wrapper (audit P1 #8)
#   - X server, openbox, unclutter, feh splash
#   - kioskuser auto-login on tty1
#   - derby-pull refresh from central on every boot
#   - derbydisplay.service for MQTT telemetry

set -euo pipefail
BUILD_CTX=${BUILD_CTX:-/build-context}
GIT_SHA=${GIT_SHA:-unknown}

echo "[derbydisplay] starting derbydisplay customize"

# ---------------------------------------------------------------------------
# 1. apt packages — kiosk stack
# ---------------------------------------------------------------------------
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    xserver-xorg xinit x11-xserver-utils \
    openbox unclutter-xfixes feh \
    chromium

# ---------------------------------------------------------------------------
# 2. Disable WiFi (Pi 3 B+ kiosk is wired only; BT already disabled by _common)
# ---------------------------------------------------------------------------
if ! grep -q '^dtoverlay=disable-wifi' /boot/firmware/config.txt; then
    echo 'dtoverlay=disable-wifi' >> /boot/firmware/config.txt
fi

# ---------------------------------------------------------------------------
# 3. Network: DHCP on eth0 via systemd-networkd
# ---------------------------------------------------------------------------
mkdir -p /etc/systemd/network
cat > /etc/systemd/network/10-eth0.network <<'EOF'
[Match]
Name=eth0

[Network]
DHCP=yes
IPForward=no
MulticastDNS=no
LinkLocalAddressing=no
EOF
systemctl enable systemd-networkd
systemctl disable dhcpcd 2>/dev/null || true

# ---------------------------------------------------------------------------
# 4. kioskuser
# ---------------------------------------------------------------------------
if ! id kioskuser >/dev/null 2>&1; then
    useradd -m -G video,input,render,tty,audio kioskuser
fi
# .xinitrc and .bash_profile copied via rootfs/; just fix ownership/mode
chown -R kioskuser:kioskuser /home/kioskuser
chmod 0755 /home/kioskuser/.xinitrc
chmod 0644 /home/kioskuser/.bash_profile

# ---------------------------------------------------------------------------
# 5. Snapshot the canonical derbydisplay files into /opt/derbynet/
# ---------------------------------------------------------------------------
mkdir -p /opt/derbynet /var/log/derbynet
rsync -a --delete \
    --exclude='.git' --exclude='*.md' --exclude='__pycache__' \
    "$BUILD_CTX/extras/soapbox/infra/derbydisplay/" /opt/derbynet/
chown -R kioskuser:kioskuser /opt/derbynet /var/log/derbynet

# Image provenance
echo "$GIT_SHA" > /etc/derby-image-sha
echo "$(date -Iseconds)" > /etc/derby-image-built-at

# ---------------------------------------------------------------------------
# 6. Service enables
# ---------------------------------------------------------------------------
systemctl enable derby-pull.service
systemctl enable derbydisplay.service
# Autologin drop-in already in rootfs/ — reload needed
systemctl daemon-reload || true

# ---------------------------------------------------------------------------
# 7. HDMI defaults (force 1080p for finicky TVs — see force-1080p.sh)
# ---------------------------------------------------------------------------
if ! grep -q '^hdmi_group=1' /boot/firmware/config.txt; then
    {
        echo ''
        echo '# DerbyDisplay HDMI defaults (force 1080p)'
        echo 'hdmi_group=1'
        echo 'hdmi_mode=16'
        echo 'hdmi_drive=2'
        echo 'disable_overscan=1'
    } >> /boot/firmware/config.txt
fi

echo "[derbydisplay] customize complete"

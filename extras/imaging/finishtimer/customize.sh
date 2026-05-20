#!/bin/bash
# extras/imaging/finishtimer/customize.sh
#
# Bakes the Pi Zero 2 W finishtimer image:
#   - WiFi-only (no Ethernet), wpa_supplicant rendered from CI secrets
#   - Snapshot of /opt/derbynet/ for first-boot offline operation
#   - derby-pull.service refreshes from central rsync on every boot
#   - finishtimer.service runs the Python finish detector
#   - DIP-switch reader writes derbyid.txt at first boot
#
# Required environment from CI:
#   WIFI_SSID, WIFI_PASSWORD  — race-day LAN WiFi credentials
#   BUILD_CTX                 — /build-context bind mount of the repo

set -euo pipefail
BUILD_CTX=${BUILD_CTX:-/build-context}
GIT_SHA=${GIT_SHA:-unknown}

echo "[finishtimer] starting finishtimer customize"

# ---------------------------------------------------------------------------
# 1. apt packages
# ---------------------------------------------------------------------------
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3-rpi.gpio \
    wpasupplicant \
    iw \
    wireless-tools

# ---------------------------------------------------------------------------
# 2. WiFi: render wpa_supplicant.conf from CI secrets
# ---------------------------------------------------------------------------
if [[ -z ${WIFI_SSID:-} || -z ${WIFI_PASSWORD:-} ]]; then
    echo "[finishtimer] FATAL: WIFI_SSID and WIFI_PASSWORD must be set"
    exit 1
fi
# wpa_passphrase produces the hashed PSK so plaintext never lands on disk
PSK=$(wpa_passphrase "$WIFI_SSID" "$WIFI_PASSWORD" \
      | awk -F= '/^[[:space:]]*psk=/ && !/#/ {print $2; exit}')
if [[ -z $PSK ]]; then
    echo "[finishtimer] FATAL: wpa_passphrase failed"
    exit 1
fi
TEMPLATE=/etc/wpa_supplicant/wpa_supplicant.conf.template
TARGET=/etc/wpa_supplicant/wpa_supplicant.conf
sed -e "s|{{SSID}}|$WIFI_SSID|g" -e "s|{{PSK}}|$PSK|g" "$TEMPLATE" > "$TARGET"
chmod 0600 "$TARGET"
rm -f "$TEMPLATE"

systemctl enable wpa_supplicant@wlan0.service
# DHCP via systemd-networkd
cat > /etc/systemd/network/20-wlan0.network <<'EOF'
[Match]
Name=wlan0

[Network]
DHCP=yes
IPForward=no
MulticastDNS=no
LinkLocalAddressing=no
EOF
systemctl enable systemd-networkd
systemctl disable dhcpcd 2>/dev/null || true

# Pi 0W2 raspi-config equivalent for WiFi country (else WiFi stays disabled)
echo 'country=CA' >> /etc/wpa_supplicant/wpa_supplicant.conf
# Some Pi OS images still gate WiFi on rfkill country
raspi-config nonint do_wifi_country CA 2>/dev/null || true

# ---------------------------------------------------------------------------
# 3. Snapshot the canonical finishtimer files into /opt/derbynet/
# ---------------------------------------------------------------------------
mkdir -p /opt/derbynet
rsync -a --delete \
    --exclude='.git' --exclude='*.md' --exclude='__pycache__' \
    "$BUILD_CTX/extras/soapbox/infra/finishtimer/files/" /opt/derbynet/
chown -R root:root /opt/derbynet

# Image provenance
echo "$GIT_SHA" > /etc/derby-image-sha
echo "$(date -Iseconds)" > /etc/derby-image-built-at

# ---------------------------------------------------------------------------
# 4. Service enables
# ---------------------------------------------------------------------------
systemctl enable derby-pull.service
systemctl enable finishtimer.service

# ---------------------------------------------------------------------------
# 5. Permissions
# ---------------------------------------------------------------------------
chmod 0755 /usr/local/sbin/derby-firstboot-finishtimer.sh

echo "[finishtimer] customize complete"

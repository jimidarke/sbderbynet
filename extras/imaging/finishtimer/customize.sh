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
# python3-smbus2, python3-zeroconf required by derbynetPCBv1.py / derbynet.py.
# Caught 2026-05-21 when FT001 came up but finishtimer.service crash-looped
# with ModuleNotFoundError after the path-mismatch fix.
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3-rpi.gpio \
    python3-smbus2 \
    python3-zeroconf \
    python3-pip \
    wpasupplicant \
    iw \
    wireless-tools

# tm1637 (7-segment LED driver) is not in Debian apt — PyPI package name is
# raspberrypi-tm1637. Pure-Python, no C extensions, so the chroot install
# works on both arm64 and armhf without per-arch wheels.
pip3 install --break-system-packages --no-cache-dir raspberrypi-tm1637

# Enable I2C bus — required for the MCP3421 ADC (battery monitoring) and any
# other I2C peripherals on the finishtimer PCB. Without this, /dev/i2c-1 is
# absent and derbynetPCBv1.py:getBatteryPercent() throws on every poll.
# Caught 2026-05-21 when FT001's getBatteryPercent crashed on `sum([None,…])`.
if ! grep -q '^dtparam=i2c_arm=on' /boot/firmware/config.txt; then
    echo 'dtparam=i2c_arm=on' >> /boot/firmware/config.txt
fi
echo 'i2c-dev' > /etc/modules-load.d/i2c.conf

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
# CRITICAL: this MUST be wpa_supplicant-wlan0.conf (with the interface
# suffix), not wpa_supplicant.conf, because we enable the
# `wpa_supplicant@wlan0.service` template unit below — which has:
#   ExecStart=/sbin/wpa_supplicant -c/etc/wpa_supplicant/wpa_supplicant-%I.conf -i%I
# The unsuffixed path is what the legacy non-template `wpa_supplicant.service`
# uses, and it conflicts with our systemd-networkd setup. Mismatched-path
# bug surfaced 2026-05-21 when FT002 never appeared on the LAN.
TARGET=/etc/wpa_supplicant/wpa_supplicant-wlan0.conf
sed -e "s|{{SSID}}|$WIFI_SSID|g" -e "s|{{PSK}}|$PSK|g" "$TEMPLATE" > "$TARGET"
chmod 0600 "$TARGET"
rm -f "$TEMPLATE"

systemctl enable wpa_supplicant@wlan0.service
# Pi OS Lite ships with `wpa_supplicant.service` (the non-template DBUS one)
# auto-enabled. It doesn't fight @wlan0 over the interface but it's wasted
# bytes and confuses diagnostics. Explicitly disable.
systemctl disable wpa_supplicant.service 2>/dev/null || true
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

# country=CA is already in the wpa_supplicant template, so no extra echo
# is needed here. `raspi-config nonint do_wifi_country` is also a no-op in
# the chroot (no kernel running) — drop it.

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

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
# 1. apt packages — kiosk stack + WiFi fallback
# ---------------------------------------------------------------------------
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    xserver-xorg xinit x11-xserver-utils \
    openbox unclutter-xfixes feh \
    chromium \
    fonts-noto-color-emoji \
    wpasupplicant iw wireless-tools rfkill

# ---------------------------------------------------------------------------
# 2. WiFi: render wpa_supplicant.conf from CI secrets. Same race-day LAN as
#    the finishtimer Pis. Ethernet stays primary via systemd-networkd
#    RouteMetric; wlan0 only takes over if eth0 is down.
# ---------------------------------------------------------------------------
if [[ -z ${WIFI_SSID:-} || -z ${WIFI_PASSWORD:-} ]]; then
    echo "[derbydisplay] FATAL: WIFI_SSID and WIFI_PASSWORD must be set"
    exit 1
fi
PSK=$(wpa_passphrase "$WIFI_SSID" "$WIFI_PASSWORD" \
      | awk -F= '/^[[:space:]]*psk=/ && !/#/ {print $2; exit}')
if [[ -z $PSK ]]; then
    echo "[derbydisplay] FATAL: wpa_passphrase failed"
    exit 1
fi
TEMPLATE=/etc/wpa_supplicant/wpa_supplicant.conf.template
# Path MUST include the interface suffix to match `wpa_supplicant@wlan0.service`
# (see finishtimer/customize.sh for the full explanation — same bug, same fix).
TARGET=/etc/wpa_supplicant/wpa_supplicant-wlan0.conf
sed -e "s|{{SSID}}|$WIFI_SSID|g" -e "s|{{PSK}}|$PSK|g" "$TEMPLATE" > "$TARGET"
chmod 0600 "$TARGET"
rm -f "$TEMPLATE"

systemctl enable wpa_supplicant@wlan0.service
# Pi OS Lite ships wpa_supplicant.service (DBUS) auto-enabled — disable it so
# only the @wlan0 template-instance runs (same fix as finishtimer/customize.sh).
systemctl disable wpa_supplicant.service 2>/dev/null || true
# country=CA is in the template; no extra echo needed. raspi-config no-op in chroot.

# ---------------------------------------------------------------------------
# 2b. WiFi regulatory domain + rfkill — REQUIRED or wlan0 stays soft-blocked.
# ---------------------------------------------------------------------------
# Ported from finishtimer/customize.sh: country=CA in wpa_supplicant.conf is NOT
# sufficient. On Pi OS wlan0 is rfkill soft-blocked until the kernel cfg80211
# regdomain is set, and NetworkManager + systemd-rfkill actively RE-block it from
# saved state on every boot. (Confirmed on a live kiosk 2026-06-17: phy0 soft=1,
# no cfg80211 on cmdline, NetworkManager active — the eth->wifi fallback was dead.)
CMDLINE=/boot/firmware/cmdline.txt
if ! grep -q 'cfg80211.ieee80211_regdom=' "$CMDLINE"; then
    sed -i '1 s/[[:space:]]*$/ cfg80211.ieee80211_regdom=CA/' "$CMDLINE"
    echo "[derbydisplay] added cfg80211.ieee80211_regdom=CA to cmdline.txt"
fi
echo 'REGDOMAIN=CA' > /etc/default/crda
# NetworkManager is shipped+enabled in base Pi OS; we run systemd-networkd +
# wpa_supplicant@wlan0, so NM is an unused, conflicting stack that re-soft-blocks
# wlan0 seconds after we unblock it. systemd-rfkill restores the saved blocked
# state. Disable/mask both; the wpa_supplicant@wlan0 10-rfkill-unblock.conf
# drop-in (rootfs/) clears the initial driver block right before wpa_supplicant.
systemctl disable NetworkManager.service 2>/dev/null || true
systemctl mask NetworkManager.service 2>/dev/null || true
systemctl mask systemd-rfkill.service systemd-rfkill.socket 2>/dev/null || true

# ---------------------------------------------------------------------------
# 3. Network: DHCP on eth0 (primary) + DHCP on wlan0 (high RouteMetric fallback)
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
cat > /etc/systemd/network/30-wlan0.network <<'EOF'
[Match]
Name=wlan0

[Network]
DHCP=yes
IPForward=no
MulticastDNS=no
LinkLocalAddressing=no

[DHCPv4]
RouteMetric=2000
EOF
systemctl enable systemd-networkd
systemctl disable dhcpcd 2>/dev/null || true

# ---------------------------------------------------------------------------
# 4. kioskuser
# ---------------------------------------------------------------------------
if ! id kioskuser >/dev/null 2>&1; then
    useradd -m -G video,input,render,tty,audio kioskuser
fi
# Lock the password — kioskuser only ever reaches a shell via tty1 autologin
# (no password prompt) or fleet-key SSH. No password path should exist.
passwd -l kioskuser
# .xinitrc and .bash_profile copied via rootfs/; just fix ownership/mode
chown -R kioskuser:kioskuser /home/kioskuser
chmod 0755 /home/kioskuser/.xinitrc
chmod 0644 /home/kioskuser/.bash_profile

# Fleet key for kioskuser — consistent with derbynet/root, so the operator
# can ssh kioskuser@<kiosk> for X-session debugging without sudo.
SRC_KEY="${BUILD_CTX:-/build-context}/extras/imaging/_common/authorized_keys"
if [[ -f "$SRC_KEY" ]]; then
    install -d -m 0700 -o kioskuser -g kioskuser /home/kioskuser/.ssh
    install -m 0600 -o kioskuser -g kioskuser "$SRC_KEY" /home/kioskuser/.ssh/authorized_keys
fi

# ---------------------------------------------------------------------------
# 5. Snapshot the canonical derbydisplay files into /opt/derbynet/
# ---------------------------------------------------------------------------
mkdir -p /opt/derbynet /var/log/derbynet
rsync -a --delete \
    --exclude='.git' --exclude='*.md' --exclude='__pycache__' \
    "$BUILD_CTX/extras/soapbox/infra/derbydisplay/" /opt/derbynet/
chown -R kioskuser:kioskuser /opt/derbynet /var/log/derbynet

# rootfs rsync (rsync -rltD, no -p) doesn't preserve the exec bit — set it on the
# shipped helper scripts in /usr/local/sbin.
chmod 0755 /usr/local/sbin/derby-server-host /usr/local/sbin/derbydisplay-run

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

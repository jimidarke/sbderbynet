#!/bin/bash
# extras/imaging/finishtimer/customize.sh
#
# Bakes the Pi Zero W V1.1 finishtimer image (armhf; BCM2835/ARMv6):
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
# raspberrypi-tm1637. Pure-Python, no C extensions, so the armhf chroot
# install needs no per-arch wheel.
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
# Build the conf directly from wpa_passphrase — NOT by sed-substituting a
# template. wpa_passphrase emits a complete `network={ ssid="..." #psk="<plain>"
# psk=<hash> }` block; we keep the hashed psk and STRIP the plaintext `#psk=`
# comment so the password never lands on disk. Generating it this way (vs sed)
# also means a special char in the SSID (& \ |) can't corrupt the file — the old
# sed approach even rewrote the comment lines (cosmetic, but symptomatic).
#
# CRITICAL: target MUST be wpa_supplicant-wlan0.conf (interface-suffixed) because
# we enable the template unit `wpa_supplicant@wlan0.service`:
#   ExecStart=/sbin/wpa_supplicant -c/etc/wpa_supplicant/wpa_supplicant-%I.conf -i%I
# The unsuffixed path is the legacy non-template service's path; a mismatch is a
# silent no-association (FT002, 2026-05-21).
TARGET=/etc/wpa_supplicant/wpa_supplicant-wlan0.conf
{
    echo "# Race-day WiFi, rendered at image-build time from CI secrets (PSK hashed)."
    echo "country=CA"
    echo "ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev"
    echo "update_config=1"
    echo ""
    wpa_passphrase "$WIFI_SSID" "$WIFI_PASSWORD" | grep -v '^[[:space:]]*#psk='
} > "$TARGET"
chmod 0600 "$TARGET"
rm -f /etc/wpa_supplicant/wpa_supplicant.conf.template

# Validation gate: assert a real network actually landed — a non-empty quoted
# SSID and a 64-hex PSK. Catches empty/placeholder/garbage creds at BUILD time
# (e.g. secrets that never reached the chroot) instead of on the bench.
if ! grep -qE '^[[:space:]]*ssid=".+"' "$TARGET" \
   || ! grep -qE '^[[:space:]]*psk=[0-9a-fA-F]{64}[[:space:]]*$' "$TARGET"; then
    echo "[finishtimer] FATAL: rendered $TARGET lacks a valid ssid/psk"
    exit 1
fi
echo "[finishtimer] wpa_supplicant-wlan0.conf rendered + validated"

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

# ---------------------------------------------------------------------------
# 2b. WiFi regulatory domain — REQUIRED or the radio stays rfkill-blocked.
# ---------------------------------------------------------------------------
# `country=CA` in wpa_supplicant.conf is NOT sufficient on its own: on Pi OS the
# wlan0 radio is soft-blocked by rfkill until the kernel cfg80211 regdomain is
# set. The known-good legacy finishtimer set it via the kernel cmdline
# (cfg80211.ieee80211_regdom=CA); the image-built card did NOT, so wlan0 never
# associated despite valid creds (confirmed 2026-05-29). Bake the regdomain into
# cmdline.txt (must stay a SINGLE line) and /etc/default/crda.
CMDLINE=/boot/firmware/cmdline.txt
if ! grep -q 'cfg80211.ieee80211_regdom=' "$CMDLINE"; then
    sed -i '1 s/[[:space:]]*$/ cfg80211.ieee80211_regdom=CA/' "$CMDLINE"
    echo "[finishtimer] added cfg80211.ieee80211_regdom=CA to cmdline.txt"
fi
echo 'REGDOMAIN=CA' > /etc/default/crda
# Regdomain sets the country but does NOT clear the rfkill soft-block, and two
# services actively RE-BLOCK the radio from saved state on every boot:
#   - NetworkManager: shipped AND enabled in the base Pi OS image. We run
#     systemd-networkd + wpa_supplicant@wlan0 instead, so NM is an unused,
#     conflicting stack — and it restores "Wi-Fi disabled by state file",
#     re-soft-blocking wlan0 a few seconds after we unblock it.
#   - systemd-rfkill: restores the saved /dev/rfkill blocked state.
# Confirmed 2026-05-30 by journal: every manual `rfkill unblock wifi` was
# re-blocked seconds later (first by systemd-rfkill, then by NetworkManager).
# Disabling NM + masking systemd-rfkill makes the unblock stick across reboots
# (validated on a live card). The shipped
# wpa_supplicant@wlan0.service.d/10-rfkill-unblock.conf drop-in clears the
# initial driver block right before wpa_supplicant starts.
systemctl disable NetworkManager.service 2>/dev/null || true
systemctl mask NetworkManager.service 2>/dev/null || true
systemctl mask systemd-rfkill.service systemd-rfkill.socket 2>/dev/null || true

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

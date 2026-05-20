#!/bin/bash
# extras/imaging/_common/customize.sh
#
# Universal customization layer applied to every image (derbypi, finishtimer,
# derbydisplay). Runs inside sdm's chroot.
#
# Usage (invoked by sdm via --plugin runscript):
#   _common/customize.sh <role>
#
# Environment provided by sdm:
#   $SDMPT          — mountpoint of the image rootfs (when not chrooted)
#   chroot mode     — script runs as root with /boot, /etc, /usr writable.

set -euo pipefail
ROLE=${1:?usage: customize.sh <role>}

echo "[derby-common] starting role=$ROLE"

# ---------------------------------------------------------------------------
# 1. Tag the image with its role
# ---------------------------------------------------------------------------
echo "$ROLE" > /etc/derby-role
chmod 0644 /etc/derby-role

# ---------------------------------------------------------------------------
# 2. Mask race-day-hostile timers (apt-daily*, fstrim, man-db, unattended)
# ---------------------------------------------------------------------------
for unit in apt-daily.timer apt-daily-upgrade.timer \
            apt-daily.service apt-daily-upgrade.service \
            fstrim.timer man-db.timer \
            unattended-upgrades.service; do
    systemctl mask "$unit" 2>/dev/null || true
done

# Belt-and-braces: also tell apt itself not to do periodic work
cat > /etc/apt/apt.conf.d/99-no-periodic <<'EOF'
APT::Periodic::Enable "0";
APT::Periodic::Update-Package-Lists "0";
APT::Periodic::Unattended-Upgrade "0";
EOF

# ---------------------------------------------------------------------------
# 3. Filesystem hardening (noatime + commit=600)
# ---------------------------------------------------------------------------
# fstab on a fresh image has the root entry with `defaults`. Replace the
# options string for the root partition while leaving the PARTUUID alone.
sed -i -E 's|^(PARTUUID=[^ ]+\s+/\s+ext4\s+)defaults\b|\1defaults,noatime,commit=600|' /etc/fstab || true
grep -q '/tmp ' /etc/fstab || \
    echo 'tmpfs /tmp tmpfs defaults,noatime,nosuid,nodev,size=64M 0 0' >> /etc/fstab

# ---------------------------------------------------------------------------
# 4. Hardware watchdog
# ---------------------------------------------------------------------------
# RuntimeWatchdogSec=15 is in _common/rootfs/etc/systemd/system.conf.d/.
# We also need dtparam=watchdog=on in config.txt. Idempotent append.
if ! grep -q '^dtparam=watchdog=on' /boot/firmware/config.txt; then
    echo '' >> /boot/firmware/config.txt
    echo '# DerbyNet hardening' >> /boot/firmware/config.txt
    echo 'dtparam=watchdog=on' >> /boot/firmware/config.txt
fi
# Also bake the common headless config (audio off, bt off, gpu memory min)
for line in 'dtoverlay=disable-bt' 'dtparam=audio=off' 'gpu_mem=16'; do
    grep -q "^${line}\b" /boot/firmware/config.txt || \
        echo "$line" >> /boot/firmware/config.txt
done

# ---------------------------------------------------------------------------
# 5. journald volatile + log2ram
# ---------------------------------------------------------------------------
# journald drop-in already copied via rootfs/.
#
# log2ram: azlux dropped pre-built .debs and install.sh assumes a live
# systemd. Inside systemd-nspawn, lay down the files manually and enable
# the units directly. Pinned to current latest 1.7.2 (2026-05).
LOG2RAM_VER=1.7.2
if [[ ! -f /usr/local/bin/log2ram ]]; then
    TMPDIR=$(mktemp -d)
    curl -fsSL "https://github.com/azlux/log2ram/archive/refs/tags/${LOG2RAM_VER}.tar.gz" \
        | tar -xzf - -C "$TMPDIR"
    SRC="$TMPDIR/log2ram-${LOG2RAM_VER}"
    install -m 0755 "$SRC/log2ram" /usr/local/bin/log2ram
    install -m 0644 "$SRC/log2ram.service"       /etc/systemd/system/log2ram.service
    install -m 0644 "$SRC/log2ram-daily.service" /etc/systemd/system/log2ram-daily.service
    install -m 0644 "$SRC/log2ram-daily.timer"   /etc/systemd/system/log2ram-daily.timer
    # Don't overwrite if user dropped a custom config via _common/rootfs/
    [[ -f /etc/log2ram.conf ]] || install -m 0644 "$SRC/log2ram.conf" /etc/log2ram.conf
    rm -rf "$TMPDIR"
fi
# Match SIZE in /etc/log2ram.conf to what _common/rootfs/log2ram.conf.d/ wants
sed -i 's/^SIZE=.*/SIZE=64M/' /etc/log2ram.conf || true
systemctl enable log2ram.service log2ram-daily.timer 2>/dev/null || true

# ---------------------------------------------------------------------------
# 6. Common apt packages
# ---------------------------------------------------------------------------
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    rsync git jq curl wget htop vim i2c-tools \
    python3 python3-pip python3-venv python3-paho-mqtt python3-psutil \
    python3-requests python3-tz python3-cryptography \
    sqlite3

# ---------------------------------------------------------------------------
# 7. Pinned Python venv for race-server / satellite Python code
# ---------------------------------------------------------------------------
# Apps that use it just call /var/lib/infra/.venv/bin/python3
python3 -m venv /var/lib/infra/.venv
/var/lib/infra/.venv/bin/pip install --no-cache-dir --upgrade pip
/var/lib/infra/.venv/bin/pip install --no-cache-dir \
    'paho-mqtt==2.1.0' \
    'psutil==6.1.0' \
    'requests==2.32.3' \
    'pytz==2024.2' \
    'cryptography==43.0.1'

# ---------------------------------------------------------------------------
# 8. Timezone
# ---------------------------------------------------------------------------
ln -sf /usr/share/zoneinfo/America/Edmonton /etc/localtime
echo 'America/Edmonton' > /etc/timezone

# ---------------------------------------------------------------------------
# 9. Permissions
# ---------------------------------------------------------------------------
chmod 0755 /usr/local/sbin/derby-firstboot.sh
chmod 0644 /etc/systemd/system/derby-firstboot.service
systemctl enable derby-firstboot.service

# ---------------------------------------------------------------------------
# 10. derbynet user (uid 1000, member of www-data + dialout for GPIO/I2C)
# ---------------------------------------------------------------------------
if ! id derbynet >/dev/null 2>&1; then
    groupadd -g 1000 derbynet 2>/dev/null || true
    useradd -u 1000 -g 1000 -G www-data,sudo,dialout,gpio,i2c \
        -s /bin/bash -m -d /home/derbynet derbynet
    # Passwordless sudo for the appliance user (race-day operations)
    echo 'derbynet ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/010_derbynet-nopasswd
    chmod 0440 /etc/sudoers.d/010_derbynet-nopasswd
fi

echo "[derby-common] done role=$ROLE"

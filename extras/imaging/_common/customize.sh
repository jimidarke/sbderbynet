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
# 0. Refresh apt cache (base image was frozen at build time; package
#    versions on Debian mirrors have moved on, so the cached index
#    points at .debs that 404).
# ---------------------------------------------------------------------------
DEBIAN_FRONTEND=noninteractive apt-get update

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
# 5. journald volatile (log2ram installed in step 6 via apt)
# ---------------------------------------------------------------------------
# journald drop-in already copied via rootfs/.

# ---------------------------------------------------------------------------
# 6. Common apt packages
# ---------------------------------------------------------------------------
# log2ram 1.7.2+ds-1 ships in Debian Trixie main as of Feb 2025 — no more
# GitHub tarball install. rsyslog ships by default on Pi OS Lite but pinning
# it here keeps the dependency visible.
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    rsync git jq curl wget htop vim i2c-tools \
    python3 python3-pip python3-venv python3-paho-mqtt python3-psutil \
    python3-requests python3-tz python3-cryptography \
    sqlite3 \
    rsyslog log2ram

# Match SIZE in /etc/log2ram.conf to what _common/rootfs/log2ram.conf.d/ wants
sed -i 's/^SIZE=.*/SIZE=64M/' /etc/log2ram.conf || true
systemctl enable log2ram.service log2ram-daily.timer 2>/dev/null || true

# ---------------------------------------------------------------------------
# 7. Python deps sanity check
# ---------------------------------------------------------------------------
# No venv: all five deps (paho-mqtt, psutil, requests, pytz, cryptography)
# are pinned by Debian Trixie's apt and live at /usr/lib/python3/dist-packages.
# The systemd service files all call /usr/bin/python3 directly. A venv was
# tried earlier but added no value over the apt packages on a frozen race-day
# image and was easy to break (rsync --delete on /var/lib/infra/ would wipe
# it). If you ever need pip-pinned packages, reintroduce a venv here.
/usr/bin/python3 -c 'import paho.mqtt.client, psutil, requests, pytz, cryptography' \
    && echo "[derby-common] python imports OK"

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
# 9b. SSH (Pi OS Lite ships openssh-server but with ssh.service disabled —
#     no Imager run-time customisation here to flip it on for us).
# ---------------------------------------------------------------------------
systemctl enable ssh

# Hardening drop-in: key-only auth, root key permitted (no password). Drop-in
# survives Pi OS upgrades that bump /etc/ssh/sshd_config.
mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/10-derby-hardening.conf <<'EOF'
PasswordAuthentication no
PermitRootLogin prohibit-password
ChallengeResponseAuthentication no
KbdInteractiveAuthentication no
UsePAM yes
EOF
chmod 0644 /etc/ssh/sshd_config.d/10-derby-hardening.conf

# Wipe baked-in host keys and let the shipped regenerate_ssh_host_keys.service
# create per-card unique keys on first boot. The unit self-disables.
rm -f /etc/ssh/ssh_host_*
systemctl enable regenerate_ssh_host_keys.service 2>/dev/null || true

# ---------------------------------------------------------------------------
# 10. derbynet user (uid 1000) — race-day appliance account
# ---------------------------------------------------------------------------
# RPi OS Lite Trixie ships a placeholder user at UID 1000 (set by Imager
# normally, here the chroot inherits an empty placeholder). Reconcile:
#   - if derbynet already exists, nothing to do
#   - else if another user has UID 1000, rename them in place
#   - else create from scratch
if ! id derbynet >/dev/null 2>&1; then
    existing=$(getent passwd 1000 | cut -d: -f1 || true)
    if [[ -n "$existing" && "$existing" != "derbynet" ]]; then
        echo "[derby-common] renaming UID-1000 user '$existing' -> derbynet"
        # Kill any processes still owned by the old user
        pkill -KILL -u "$existing" 2>/dev/null || true
        usermod -l derbynet "$existing"
        groupmod -n derbynet "$existing" 2>/dev/null || true
        # Move home dir to /home/derbynet if currently elsewhere
        if [[ -d "/home/$existing" && ! -d "/home/derbynet" ]]; then
            usermod -d /home/derbynet -m derbynet
        fi
    else
        groupadd -g 1000 derbynet 2>/dev/null || true
        useradd -u 1000 -g 1000 -m -d /home/derbynet -s /bin/bash derbynet
    fi
fi
# Pi OS Lite Trixie's UID-1000 placeholder ships with shell /usr/sbin/nologin.
# `usermod -l` doesn't touch the shell, so the rename path inherits nologin
# and SSH refuses connections with "This account is currently not available."
# Force shell unconditionally — idempotent.
usermod -s /bin/bash derbynet
# Add to the supplementary groups that exist on this image
for grp in www-data sudo dialout gpio i2c spi netdev video; do
    if getent group "$grp" >/dev/null 2>&1; then
        usermod -aG "$grp" derbynet 2>/dev/null || true
    fi
done
# Passwordless sudo for the appliance user (race-day operations)
echo 'derbynet ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/010_derbynet-nopasswd
chmod 0440 /etc/sudoers.d/010_derbynet-nopasswd

# Break-glass console password. SSH stays key-only (PasswordAuthentication no),
# so this password ONLY works at the physical console/serial — the fallback for
# when WiFi (and therefore the fleet SSH key) is unavailable. Sourced from the
# CONSOLE_PASSWORD CI secret; only the /etc/shadow hash lands on the card, never
# plaintext in git. Added 2026-05-29 after a finishtimer was completely
# unreachable: WiFi was down (no key login) and no console password existed.
if [[ -z "${CONSOLE_PASSWORD:-}" ]]; then
    echo "[derby-common] FATAL: CONSOLE_PASSWORD must be set (break-glass console login)"
    exit 1
fi
# Pre-hash and write directly with `chpasswd -e`. Plain `chpasswd` hashes via
# PAM (pam_chauthtok -> yescrypt), which fails under QEMU armhf emulation with
# "Authentication token manipulation error" (the finishtimer build runs armhf;
# arm64 roles were unaffected). openssl SHA-512-crypt + `-e` bypasses PAM.
DERBY_PW_HASH=$(openssl passwd -6 "$CONSOLE_PASSWORD")
if [[ "$DERBY_PW_HASH" != \$6\$* ]]; then
    echo "[derby-common] FATAL: could not hash CONSOLE_PASSWORD (openssl passwd -6)"
    exit 1
fi
echo "derbynet:${DERBY_PW_HASH}" | chpasswd -e
echo "[derby-common] set break-glass console password for derbynet"

# ---------------------------------------------------------------------------
# 10b. Disable the Pi OS first-boot user wizard (userconfig.service)
# ---------------------------------------------------------------------------
# Pi OS Lite Trixie ships userconfig.service enabled. On first boot it RENAMES
# the uid-1000 user to an operator-entered name and calls /bin/cancel-rename —
# which is what enables getty@tty1. On 2026-05-29 this silently renamed our
# baked `derbynet` account to `newname` and left it locked, killing BOTH console
# login (locked password) AND `ssh derbynet@` (no such user; the fleet key lives
# under /home/derbynet). Mask it so the baked appliance user is never clobbered,
# and enable getty@tty1 ourselves (the job userconfig normally did) so the
# console login prompt still appears.
systemctl mask userconfig.service 2>/dev/null || true
systemctl enable getty@tty1.service 2>/dev/null || true

# ---------------------------------------------------------------------------
# 11. Bake the derby-fleet authorized_keys so the image is reachable on first
#     boot without a userconf.txt dance. Private half lives in
#     SECURE/keys/derby/derby_fleet_ed25519 (gitignored).
# ---------------------------------------------------------------------------
SRC_KEY="${BUILD_CTX:-/build-context}/extras/imaging/_common/authorized_keys"
if [[ -f "$SRC_KEY" ]]; then
    install -d -m 0700 -o derbynet -g derbynet /home/derbynet/.ssh
    install -m 0600 -o derbynet -g derbynet "$SRC_KEY" /home/derbynet/.ssh/authorized_keys
    echo "[derby-common] installed authorized_keys for derbynet"
    # Emergency root override: services run as root on every role, so a
    # bricked /home/derbynet would otherwise lock us out. With sshd hardened
    # to prohibit-password + PasswordAuthentication=no, root is only
    # reachable with the fleet key.
    install -d -m 0700 -o root -g root /root/.ssh
    install -m 0600 -o root -g root "$SRC_KEY" /root/.ssh/authorized_keys
    echo "[derby-common] installed authorized_keys for root"
else
    echo "[derby-common] WARNING: $SRC_KEY missing — image will be unreachable until userconf.txt is supplied"
fi

echo "[derby-common] done role=$ROLE"

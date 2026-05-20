#!/bin/bash
# extras/imaging/derbypi/customize.sh
#
# Bakes the central race-server Pi image:
#   - nginx + php-fpm + sqlite serving DerbyNet
#   - mosquitto MQTT broker (bound to 192.168.100.10)
#   - rsync daemon serving /var/lib/infra/ to satellites
#   - rsyslog UDP 514 listener writing /var/log/derbynet.log
#   - derbyrace.service (enabled) + derbytime.service (disabled placeholder)
#   - Static IP 192.168.100.10/24 on eth0 via systemd-networkd
#   - DS3231 RTC overlay
#   - Skeleton SQLite DB seeded with WAL + synchronous=NORMAL
#   - 15-min backup timer + DB-restore-from-USB on first boot
#
# Inputs:
#   /build-context/  — bind-mounted (read-only) copy of the repo at $GIT_SHA
# Environment provided by build-images.yml:
#   GIT_SHA, BUILD_TIMESTAMP

set -euo pipefail
BUILD_CTX=${BUILD_CTX:-/build-context}
GIT_SHA=${GIT_SHA:-unknown}

echo "[derbypi] starting derbypi customize; git_sha=$GIT_SHA"

# ---------------------------------------------------------------------------
# 1. apt packages
# ---------------------------------------------------------------------------
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    nginx \
    php-fpm php-cli php-curl php-gd php-sqlite3 php-pdo php-mbstring \
    mosquitto mosquitto-clients \
    rsync rsyslog

# ---------------------------------------------------------------------------
# 2. Disable WiFi/BT (this is the wired central server)
# ---------------------------------------------------------------------------
if ! grep -q '^dtoverlay=disable-wifi' /boot/firmware/config.txt; then
    echo 'dtoverlay=disable-wifi' >> /boot/firmware/config.txt
fi

# ---------------------------------------------------------------------------
# 3. DS3231 RTC (Pi 3 B+ has the chip wired to I2C)
# ---------------------------------------------------------------------------
if ! grep -q '^dtparam=i2c_arm=on' /boot/firmware/config.txt; then
    echo 'dtparam=i2c_arm=on' >> /boot/firmware/config.txt
fi
if ! grep -q '^dtoverlay=i2c-rtc,ds3231' /boot/firmware/config.txt; then
    echo 'dtoverlay=i2c-rtc,ds3231' >> /boot/firmware/config.txt
fi
# Remove fake-hwclock (which fights the real RTC)
apt-get purge -y fake-hwclock 2>/dev/null || true
echo 'i2c-dev' > /etc/modules-load.d/i2c.conf

# ---------------------------------------------------------------------------
# 4. systemd-networkd for the static IP
# ---------------------------------------------------------------------------
systemctl enable systemd-networkd
systemctl disable dhcpcd 2>/dev/null || true
# The .network file is in rootfs/ — already copied.

# ---------------------------------------------------------------------------
# 5. nginx site
# ---------------------------------------------------------------------------
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/derbynet /etc/nginx/sites-enabled/derbynet

# Tune PHP via drop-ins so we don't have to know the PHP version at build time
PHP_VER=$(php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;')
PHP_FPM_CONF="/etc/php/${PHP_VER}/fpm/conf.d/99-derbynet.ini"
cat > "$PHP_FPM_CONF" <<'EOF'
upload_max_filesize = 16M
post_max_size = 16M
memory_limit = 256M
session.gc_maxlifetime = 28800
EOF
# php-fpm unit name varies; symlink to a stable name for our nginx config
mkdir -p /etc/tmpfiles.d
cat > /etc/tmpfiles.d/php-fpm-symlink.conf <<EOF
L /run/php/php-fpm.sock - - - - php${PHP_VER}-fpm.sock
EOF
systemctl enable "php${PHP_VER}-fpm"

# ---------------------------------------------------------------------------
# 6. Bake the application code
# ---------------------------------------------------------------------------
# website/ -> /var/www/html/derbynet
mkdir -p /var/www/html/derbynet
rsync -a --delete \
    --exclude='.git' --exclude='*.md' --exclude='node_modules' \
    "$BUILD_CTX/website/" /var/www/html/derbynet/
chown -R derbynet:www-data /var/www/html/derbynet
find /var/www/html/derbynet -type d -exec chmod 0775 {} +
find /var/www/html/derbynet -type f -exec chmod 0664 {} +

# Per-event local config dir, world-writable so PHP can drop config-database.inc
mkdir -p /var/www/html/derbynet/local
chmod 0777 /var/www/html/derbynet/local

# extras/soapbox/infra/ -> /var/lib/infra (this is what rsyncd serves)
mkdir -p /var/lib/infra
rsync -a --delete \
    --exclude='.git' --exclude='*.md' --exclude='__pycache__' \
    "$BUILD_CTX/extras/soapbox/infra/" /var/lib/infra/
chown -R derbynet:derbynet /var/lib/infra
# Compat symlink that several pre-existing scripts assume (derbyrace.service uses /var/lib/infra/app)
ln -sfn /var/lib/infra/server /var/lib/infra/app

# Stamp the image with its git SHA so we can verify provenance on a live Pi
echo "$GIT_SHA" > /etc/derby-image-sha
echo "$(date -Iseconds)" > /etc/derby-image-built-at

# ---------------------------------------------------------------------------
# 7. Data + key directories
# ---------------------------------------------------------------------------
mkdir -p /var/lib/derbynet/{imagery,slides,queue,keys,backups}
chown -R derbynet:derbynet /var/lib/derbynet
chmod 0777 /var/lib/derbynet /var/lib/derbynet/{imagery,slides,queue}
chmod 0700 /var/lib/derbynet/keys

# Logfiles the unified logging framework writes to
# (rsyslog → derbynet.log text format; derbylogger → derbynet.jsonl for derby-chronology)
touch /var/log/derbynet.log /var/log/derbynet.jsonl
chown derbynet:derbynet /var/log/derbynet.log /var/log/derbynet.jsonl
chmod 0644 /var/log/derbynet.log /var/log/derbynet.jsonl

# derby-chronology CLI wrapper (matches the install in
# extras/derbypi/ansible/roles/raceserver/tasks/main.yml so a fresh image
# behaves identically to an Ansible-bootstrapped Pi).
cat > /usr/local/bin/derby-chronology <<'EOF'
#!/bin/sh
exec python3 /var/lib/infra/app/derby-chronology.py "$@"
EOF
chmod 0755 /usr/local/bin/derby-chronology

# ---------------------------------------------------------------------------
# 8. Skeleton SQLite event DB (seeded with WAL + sync=NORMAL)
# ---------------------------------------------------------------------------
SKEL=/var/lib/derbynet/skeleton.sqlite3
rm -f "$SKEL"
sqlite3 "$SKEL" <<'SQL'
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;
PRAGMA temp_store=MEMORY;
CREATE TABLE IF NOT EXISTS _derbynet_image_marker (note TEXT);
INSERT INTO _derbynet_image_marker VALUES ('seeded by extras/imaging/derbypi/customize.sh');
SQL
chown derbynet:derbynet "$SKEL"
chmod 0664 "$SKEL"

# ---------------------------------------------------------------------------
# 9. Service enables
# ---------------------------------------------------------------------------
systemctl enable nginx mosquitto rsync rsyslog
systemctl enable derbyrace.service
systemctl enable derbynet-backup.timer
# derbytime stays DISABLED until a consumer of derbynet/race/time is confirmed
systemctl disable derbytime.service 2>/dev/null || true

# ---------------------------------------------------------------------------
# 10. Permissions on scripts
# ---------------------------------------------------------------------------
chmod 0755 /usr/local/sbin/derby-firstboot-derbypi.sh \
           /usr/local/sbin/derbynet-backup.sh

echo "[derbypi] customize complete"

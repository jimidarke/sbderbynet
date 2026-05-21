# DerbyNet Raspberry Pi Server Setup Guide

> **SUPERSEDED for race-day recovery.** The supported path to rebuild a derbypi is now the SD-card image pipeline — flash `sbderbynet-derbypi-<sha>.img.xz`, edit `derbyid.txt`, boot. See [`docs/SD_CARD_RECOVERY.md`](../../../../docs/SD_CARD_RECOVERY.md) and [`extras/imaging/INSTRUCTIONS.md`](../../../imaging/INSTRUCTIONS.md). The baked image already includes SSH key access, sshd hardening, static IP, RTC overlay, MQTT broker, nginx + PHP, derbynet-backup timer, log2ram, journald-volatile, and the watchdog — none of the manual steps below are required for a fresh install.
>
> This guide remains useful as a **reference for what's inside the image** and for one-off experimentation on a non-race Pi. It is no longer maintained as the source of truth; the image-pipeline scripts under [`extras/imaging/derbypi/`](../../../imaging/derbypi/) are.

Complete installation procedure for rebuilding the DerbyNet Raspberry Pi server from a fresh Raspberry Pi OS 64-bit installation.

**Target Configuration:**
- Raspberry Pi with fresh Raspberry Pi OS 64-bit (Lite)
- Ethernet wired (no WiFi)
- DS3231 battery-powered RTC attached
- Headless operation
- Static IP: 192.168.100.10
- HTTP only (no SSL)
- Services: MQTT broker, DerbyNet web interface, Soapbox server components
- Video streaming: Handled by separate Beelink PC (not this server)

---

## Phase 1: Initial Raspberry Pi OS Setup (Pre-Boot)

### 1.1 Flash SD Card
```bash
# Use Raspberry Pi Imager to flash Raspberry Pi OS 64-bit Lite
# During imaging, configure:
# - Enable SSH
# - Set username: derbynet (uid 1000, used for VS Code sync)
# - Set password
# - Set hostname: derbynetpi
# - Set locale/timezone: America/Edmonton
```

### 1.2 Configure Static IP (Pre-Boot)
Create/edit on the boot partition before first boot:

**`/boot/firmware/cmdline.txt`** - Add to end:
```
ip=192.168.100.10::192.168.100.1:255.255.255.0:derbynetpi:eth0:off
```

Or configure post-boot in `/etc/dhcpcd.conf`:
```
interface eth0
static ip_address=192.168.100.10/24
static routers=192.168.100.1
static domain_name_servers=192.168.100.1 8.8.8.8
```

### 1.3 Disable WiFi and Bluetooth
Add to `/boot/firmware/config.txt`:
```
# Disable WiFi and Bluetooth (not needed, ethernet only)
dtoverlay=disable-wifi
dtoverlay=disable-bt
```

### 1.4 Configure DS3231 RTC
Add to `/boot/firmware/config.txt`:
```
# Enable I2C for RTC
dtparam=i2c_arm=on

# Enable DS3231 RTC overlay
dtoverlay=i2c-rtc,ds3231
```

---

## Phase 2: First Boot & System Update

### 2.1 Connect and Update
```bash
# SSH into the Pi
ssh derbynet@192.168.100.10

# Update system
sudo apt update && sudo apt upgrade -y

# Set timezone
sudo timedatectl set-timezone America/Edmonton
```

### 2.2 Verify I2C and RTC Detection
```bash
# First, verify I2C is enabled and RTC is detected
sudo i2cdetect -y 1

# Expected output for DS3231 at address 0x68:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:                         -- -- -- -- -- -- -- --
# ...
# 60: -- -- -- -- -- -- -- -- 68 -- -- -- -- -- -- --
#                             ^^-- DS3231 detected here

# If you see "UU" at 0x68, the kernel driver has claimed it (good!)
# If you see "68", device detected but driver not loaded
# If you see "--" at 0x68, RTC not detected (check wiring/config)
```

### 2.3 Troubleshoot I2C Issues (if RTC not detected)
```bash
# Check if I2C modules are loaded
lsmod | grep i2c

# Check if RTC overlay is loaded
dmesg | grep -i rtc

# Verify config.txt settings took effect
cat /boot/firmware/config.txt | grep -E "i2c|rtc"

# If i2c-dev module not loaded:
sudo modprobe i2c-dev

# Check I2C device exists
ls -la /dev/i2c*

# If nothing at 0x68, check physical connections:
# - SDA to GPIO2 (pin 3)
# - SCL to GPIO3 (pin 5)
# - VCC to 3.3V (pin 1) or 5V (pin 2)
# - GND to Ground (pin 6)
```

### 2.4 Complete RTC Setup
```bash
# Remove fake hardware clock (replaced by real RTC)
sudo apt remove fake-hwclock -y
sudo update-rc.d -f fake-hwclock remove

# Disable the fake hwclock service
sudo systemctl disable fake-hwclock

# Edit hwclock-set to use RTC
sudo nano /lib/udev/hwclock-set
# Comment out these lines:
# if [ -e /run/systemd/system ] ; then
#     exit 0
# fi

# Verify RTC device exists
ls -la /dev/rtc*
# Should show: /dev/rtc0 -> rtc/rtc0

# Test reading RTC (requires util-linux package)
sudo hwclock -r
# Or use:
sudo hwclock --show --verbose

# If hwclock command not found:
sudo apt install util-linux

# If RTC time is wrong, sync from system time:
sudo hwclock -w
# Or:
sudo hwclock --systohc

# Verify time was written:
sudo hwclock -r
```

### 2.5 Test RTC Persistence
```bash
# To verify RTC keeps time during power loss:
# 1. Note the current time
date

# 2. Shut down (not reboot)
sudo shutdown -h now

# 3. Disconnect power for 30+ seconds
# 4. Reconnect power and boot
# 5. Check time before NTP sync (disconnect ethernet first to test)
date
sudo hwclock -r

# Times should match (within a few seconds)
```

---

## Phase 3: Install Core Dependencies

### 3.1 System Packages
```bash
sudo apt install -y \
    nginx \
    php-fpm \
    php-curl \
    php-gd \
    php-sqlite3 \
    php-pdo \
    mosquitto \
    mosquitto-clients \
    python3 \
    python3-pip \
    python3-venv \
    git \
    rsyslog \
    rsync \
    i2c-tools \
    jq 
```

### 3.2 Python Packages
```bash
# Install Python packages system-wide or in venv
sudo pip3 install --break-system-packages \
    paho-mqtt \
    requests \
    psutil \
    pytz

# Optional (for LCD display if attached):
# sudo pip3 install --break-system-packages pillow gpiozero spidev numpy
```

---

## Phase 4: Configure MQTT Broker (Mosquitto)

### 4.1 Configure Mosquitto
```bash
sudo nano /etc/mosquitto/conf.d/derbynet.conf
```
```
# DerbyNet MQTT Configuration
# Note: persistence_location is already set in main mosquitto.conf
# Only add settings that aren't in the main config

listener 1883
allow_anonymous true

# Logging
log_dest syslog
log_type error
log_type warning
log_type notice
```

**Troubleshooting:** If mosquitto fails to start with "Duplicate persistence_location":
```bash
# Check main config for existing settings
grep -E "persistence|listener" /etc/mosquitto/mosquitto.conf

# Remove any duplicate settings from derbynet.conf
# Only keep: listener, allow_anonymous, log_dest, log_type
```

### 4.2 Enable and Start Mosquitto
```bash
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# Test MQTT
mosquitto_sub -h localhost -t test &
mosquitto_pub -h localhost -t test -m "hello"
# Should see "hello" output
```

### 4.3 Configure Rsyslog for Remote Logging

The finish timers, start timer, and display nodes send logs to the central server via UDP syslog (port 514). Configure rsyslog to accept these:

```bash
sudo nano /etc/rsyslog.conf
```

Uncomment or add these lines to enable UDP syslog reception:
```
# Provides UDP syslog reception
module(load="imudp")
input(type="imudp" port="514")
```

Create a config to route DerbyNet logs to the shared log file:
```bash
sudo nano /etc/rsyslog.d/10-derbynet.conf
```
```
# Route all remote syslog to derbynet.log
:fromhost-ip, !isequal, "127.0.0.1" /var/log/derbynet.log
& stop
```

Restart rsyslog:
```bash
sudo systemctl restart rsyslog

# Verify rsyslog is listening on UDP 514
sudo ss -ulnp | grep 514
```

**Note:** Remote devices send logs to `192.168.100.10:514`:
- Finish timers (`nodelogger.py`) → UDP to 192.168.100.10:514
- Start timer (ESP32 `main.py`) → UDP to 192.168.100.10:514
- Display nodes → UDP to 192.168.100.10:514

### 4.4 Configure Rsync Daemon for Device Updates

The finish timers and display nodes use rsync to pull their scripts from the central server on boot. Configure the rsync daemon:

```bash
sudo apt install -y rsync
```

Create rsync daemon config:
```bash
sudo nano /etc/rsyncd.conf
```
```
# DerbyNet Rsync Daemon Configuration
uid = nobody
gid = nogroup
use chroot = yes
max connections = 10
timeout = 300
read only = yes

[derbynet]
    path = /var/lib/infra
    comment = DerbyNet Device Files
    read only = yes
    list = yes
```

Enable and start rsync daemon:
```bash
# Enable rsync daemon in defaults
sudo nano /etc/default/rsync
# Set: RSYNC_ENABLE=true

# Start the service
sudo systemctl enable rsync
sudo systemctl start rsync

# Verify it's running
sudo ss -tlnp | grep 873
```

**Rsync Module Structure:**
The finish timers pull from `rsync://192.168.100.10/derbynet/finishtimer/` which maps to `/var/lib/infra/finishtimer/` on the server.

After VS Code syncs `extras/soapbox/infra/` → `/var/lib/infra/`, the structure will be:
```
/var/lib/infra/
├── finishtimer/         # Pulled by finish timer nodes
│   ├── files/
│   │   ├── finishtimer.py
│   │   ├── finishtimer.service
│   │   ├── derbynet.py
│   │   ├── derbynetPCBv1.py
│   │   └── nodelogger.py
│   ├── setup.sh
│   └── sync.sh
├── derbydisplay/        # Pulled by display nodes
├── starttimer/          # ESP32 OTA files (served via HTTP)
└── server/              # Server components (not synced to nodes)
```

---

## Phase 5: Install DerbyNet Web Application

### 5.1 Create Directory Structure

Following the original DerbyNet installer pattern:

```bash
# Create data directory (stores database, photos, slides)
sudo mkdir -m 777 /var/lib/derbynet
sudo mkdir -m 777 /var/lib/derbynet/imagery
sudo mkdir -m 777 /var/lib/derbynet/slides

# Create web directory
sudo mkdir -p /var/www/html/derbynet

# Create local config directory inside web root
# This is where DerbyNet stores config-database.inc and config-roles.inc
sudo mkdir -m 777 /var/www/html/derbynet/local
```

### 5.2 Deploy DerbyNet Website Files

**Primary Method: VS Code Remote Sync**

The dev machine syncs files automatically via VS Code:
- `website/` → `derbynetpi:/var/www/html/derbynet/`
- `extras/soapbox/infra/` → `derbynetpi:/var/lib/infra/`

```bash
# Ensure target directories exist with correct permissions for VS Code sync
sudo mkdir -p /var/www/html/derbynet
sudo chown -R derbynet:www-data /var/www/html/derbynet
sudo chmod -R 775 /var/www/html/derbynet

# Ensure local directory is writable (for config files)
sudo chmod 777 /var/www/html/derbynet/local
```

### 5.3 Configure PHP-FPM

These settings match the original DerbyNet debian postinst script:

```bash
# Find PHP version
PHP_VERSION=$(php -r "echo PHP_MAJOR_VERSION.'.'.PHP_MINOR_VERSION;")

# Edit PHP configuration
sudo nano /etc/php/${PHP_VERSION}/fpm/php.ini
```
Set these values (matching installer/debian/server/postinst):
```ini
upload_max_filesize = 16M
post_max_size = 16M
memory_limit = 256M
session.gc_maxlifetime = 28800
```

```bash
# Restart PHP-FPM
sudo systemctl restart php${PHP_VERSION}-fpm
```

### 5.4 Configure Nginx

Create the DerbyNet log format config:
```bash
sudo nano /etc/nginx/conf.d/derbynet_log_format.conf
```
```nginx
# DerbyNet log format (includes request body for debugging)
log_format derbynet_log
    '$remote_addr - $remote_user [$time_local] '
    '"$request" $status '
    '$body_bytes_sent "$http_referer" '
    '"$http_user_agent" '
    '[$request_body]';
```

Create the main site config:
```bash
sudo nano /etc/nginx/sites-available/derbynet
```
```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name derbynetpi 192.168.100.10;

    root /var/www/html;
    index index.php index.html;

    # DerbyNet custom log format
    access_log /var/log/nginx/derbynet_access.log derbynet_log;

    # DerbyNet application
    location /derbynet {
        index index.php;
    }

    # PHP handler for DerbyNet
    location ~ derbynet/.*\.php(/.*)?$ {
        client_max_body_size 16M;
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php-fpm.sock;
        # CONFIG_DIR = local config files (config-database.inc, config-roles.inc)
        fastcgi_param DERBYNET_CONFIG_DIR /var/www/html/derbynet/local;
        # DATA_DIR = race data (database, photos, slides)
        fastcgi_param DERBYNET_DATA_DIR /var/lib/derbynet;
    }

    # Static files
    location ~ \.(css|js|png|jpg|gif|ico|svg|woff|woff2|ttf)$ {
        expires 1h;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
# Enable site
sudo ln -sf /etc/nginx/sites-available/derbynet /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and restart nginx
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## Phase 6: Install Soapbox Server Components

### 6.1 Create Infra Directory Structure

**VS Code syncs `extras/soapbox/infra/` → `derbynetpi:/var/lib/infra/`**

The directory structure on the Pi will be:
```
/var/lib/infra/
├── server/          # derbyRace.py, derbyTime.py, etc.
├── finishtimer/     # Finish timer components
├── starttimer/      # Start timer components
├── derbydisplay/    # Display kiosk components
└── deployment/      # Deployment scripts
```

```bash
# Create infra directory with correct permissions for VS Code sync
sudo mkdir -p /var/lib/infra
sudo chown -R derbynet:derbynet /var/lib/infra
sudo chmod -R 775 /var/lib/infra

# Create log file
sudo touch /var/log/derbynet.log
sudo chmod 666 /var/log/derbynet.log
```

### 6.2 Symlink for Service Compatibility
```bash
# Create symlink so services can find server files at expected location
# (Services expect /var/lib/infra/app/ but VS Code syncs to /var/lib/infra/server/)
sudo ln -sf /var/lib/infra/server /var/lib/infra/app
```

### 6.3 Create Message Queue Directory
```bash
sudo mkdir -p /var/lib/derbynet/queue
sudo chmod 777 /var/lib/derbynet/queue
```

### 6.4 Create Systemd Service Files

**Derby Race Service:**
```bash
sudo nano /etc/systemd/system/derbyrace.service
```
```ini
[Unit]
Description=Derby Race Server
After=network.target mosquitto.service nginx.service
Wants=mosquitto.service

[Service]
Type=simple
User=root
WorkingDirectory=/var/lib/infra/app
ExecStart=/usr/bin/python3 /var/lib/infra/app/derbyRace.py
Restart=always
RestartSec=10
Environment="DERBY_CONSOLE_LOG=false"
Environment="DERBY_DEBUG=false"
StandardOutput=journal
StandardError=journal
SyslogIdentifier=derbyrace

[Install]
WantedBy=multi-user.target
```

**Derby Time Service:**
```bash
sudo nano /etc/systemd/system/derbytime.service
```
```ini
[Unit]
Description=Derby Time Service
After=network.target mosquitto.service
Wants=mosquitto.service

[Service]
Type=simple
User=root
WorkingDirectory=/var/lib/infra/app
ExecStart=/usr/bin/python3 /var/lib/infra/app/derbyTime.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=derbytime

[Install]
WantedBy=multi-user.target
```

### 6.5 Enable and Start Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable derbyrace
sudo systemctl enable derbytime
sudo systemctl start derbyrace
sudo systemctl start derbytime
```

---

## Phase 7: Verify Installation

### 7.1 Check All Services
```bash
# Check service status
sudo systemctl status mosquitto
sudo systemctl status nginx
sudo systemctl status php*-fpm
sudo systemctl status derbyrace
sudo systemctl status derbytime

# Check logs
sudo journalctl -u derbyrace -f
sudo journalctl -u derbytime -f
```

### 7.2 Test MQTT
```bash
# Subscribe to race state
mosquitto_sub -h localhost -t "derbynet/race/state" &

# Subscribe to time broadcasts
mosquitto_sub -h localhost -t "derbynet/race/time"
```

### 7.3 Test Web Interface
```bash
# From another machine
curl http://192.168.100.10/derbynet/
# Or open in browser: http://192.168.100.10/derbynet/
```

### 7.4 Test API Connectivity
```bash
# From the Pi
curl "http://192.168.100.10/derbynet/action.php?query=poll.coordinator"
```

---

## Phase 8: Headless Optimization

If you installed the full desktop OS instead of Lite, follow these steps to convert to headless console-only operation.

### 8.1 Set Default Boot Target to Console
```bash
# Change default boot target from graphical to multi-user (console)
sudo systemctl set-default multi-user.target

# This is equivalent to raspi-config "Boot to Console" but more direct
```

### 8.2 Disable Desktop Environment & GUI Services
```bash
# Disable display manager (the GUI login screen)
sudo systemctl disable lightdm 2>/dev/null || true
sudo systemctl disable gdm3 2>/dev/null || true

# Disable compositor and desktop services
sudo systemctl disable plymouth 2>/dev/null || true

# Disable other unnecessary services
sudo systemctl disable avahi-daemon        # mDNS/Bonjour (not needed)
sudo systemctl disable triggerhappy        # Hotkey daemon
sudo systemctl disable hciuart             # Bluetooth UART
sudo systemctl disable bluetooth           # Bluetooth service
sudo systemctl disable ModemManager 2>/dev/null || true
sudo systemctl disable wpa_supplicant      # WiFi (using ethernet)

# Keep enabled: ssh, networking, our services
```

### 8.3 Remove Desktop Packages (Optional - Saves ~1GB+ RAM and disk)
```bash
# Remove desktop environment and related packages
sudo apt purge -y \
    'lxde*' 'lxpanel*' 'lxsession*' 'lxterminal*' \
    'pcmanfm*' 'openbox*' 'lightdm*' \
    'xserver-xorg*' 'x11-*' 'xarchiver' 'xdg-*' \
    'raspberrypi-ui-mods' 'rpd-*' 'pi-greeter' \
    'desktop-base' 'desktop-file-utils' \
    'gtk2-engines*' 'gtk3-*' 'libgtk*' \
    'pulseaudio*' 'pipewire*' \
    'chromium*' 'firefox*' \
    'vlc*' 'geany*' 'thonny*' \
    'scratch*' 'sonic-pi*' 'wolfram*' 'mathematica*' \
    'libreoffice*' 2>/dev/null || true

# Clean up orphaned packages
sudo apt autoremove -y
sudo apt autoclean
```

### 8.4 Reduce GPU Memory (Headless doesn't need graphics)
```bash
# Add to /boot/firmware/config.txt
echo "gpu_mem=16" | sudo tee -a /boot/firmware/config.txt
```

### 8.5 Reduce Logging
```bash
# Reduce journal size
sudo journalctl --vacuum-size=100M

# Configure journal limits
sudo mkdir -p /etc/systemd/journald.conf.d
cat << 'EOF' | sudo tee /etc/systemd/journald.conf.d/size.conf
[Journal]
SystemMaxUse=100M
RuntimeMaxUse=50M
EOF

sudo systemctl restart systemd-journald
```

### 8.6 Verify Headless Configuration
```bash
# Check default target (should be multi-user.target)
systemctl get-default

# Check no X/GUI processes running after reboot
ps aux | grep -E '[X]org|[l]xpanel|[o]penbox'

# Check memory usage (should be ~150-300MB without GUI)
free -h
```

### 8.7 Reboot and Verify
```bash
sudo reboot

# After reboot, SSH back in and verify:
# - Boots to console login prompt on HDMI
# - No GUI processes running
# - Lower memory usage
```

---

## Quick Reference - Key Files & Paths

| Component | Pi Path | Dev Machine Source |
|-----------|---------|-------------------|
| DerbyNet Website | `/var/www/html/derbynet/` | `website/` |
| DerbyNet Config | `/var/www/html/derbynet/local/` | (runtime config) |
| DerbyNet Data | `/var/lib/derbynet/` | (runtime data) |
| Racer Photos | `/var/lib/derbynet/imagery/` | (uploaded photos) |
| Slideshow Images | `/var/lib/derbynet/slides/` | (slideshow content) |
| Infra Components | `/var/lib/infra/` | `extras/soapbox/infra/` |
| Server Python Files | `/var/lib/infra/server/` | `extras/soapbox/infra/server/` |
| Server Log | `/var/log/derbynet.log` | - |
| MQTT Config | `/etc/mosquitto/conf.d/derbynet.conf` | - |
| Nginx Config | `/etc/nginx/sites-available/derbynet` | - |
| Nginx Log Format | `/etc/nginx/conf.d/derbynet_log_format.conf` | - |
| PHP Config | `/etc/php/*/fpm/php.ini` | - |

**VS Code Sync Mappings:**
```
website/                    → derbynetpi:/var/www/html/derbynet/
extras/soapbox/infra/       → derbynetpi:/var/lib/infra/
```

**DerbyNet Environment Variables (passed via nginx fastcgi_param):**
- `DERBYNET_CONFIG_DIR` = `/var/www/html/derbynet/local` (config-database.inc, config-roles.inc)
- `DERBYNET_DATA_DIR` = `/var/lib/derbynet` (database, photos, slides)

---

## Quick Reference - Key Services

| Service | Command |
|---------|---------|
| MQTT Broker | `sudo systemctl status mosquitto` |
| Web Server | `sudo systemctl status nginx` |
| PHP-FPM | `sudo systemctl status php*-fpm` |
| Race Server | `sudo systemctl status derbyrace` |
| Time Service | `sudo systemctl status derbytime` |

---

## Quick Reference - Network

| Hostname | IP Address | Purpose |
|----------|------------|---------|
| derbynetpi | 192.168.100.10 | Main server (this device) |
| - | 192.168.100.1 | Router/gateway |

---

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u <service-name> -e --no-pager
```

### MQTT connection issues
```bash
mosquitto_sub -h localhost -t "#" -v  # Monitor all topics
```

### Web interface 502 error
```bash
sudo systemctl restart php*-fpm
sudo systemctl restart nginx
```

### Python import errors
```bash
pip3 list | grep -E "paho|psutil|pytz|requests"
# Reinstall if missing
```

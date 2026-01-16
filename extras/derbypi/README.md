# DerbyPi Ansible Deployment

Automated deployment system for the DerbyNet Raspberry Pi server using Ansible.

## Overview

This Ansible deployment automates the manual setup documented in `extras/soapbox/infra/server/RASPBERRY_PI_SETUP.md`, providing:

- **One-command bootstrap** for fresh Raspberry Pi installations
- **Self-updating configuration** via `ansible-pull` (runs every 30 minutes)
- **RSA-2048 keypair generation** for SaaS integration
- **Native installation** without Docker for optimal Raspberry Pi performance

## Target Configuration

| Setting | Value |
|---------|-------|
| OS | Raspberry Pi OS Lite 64-bit (headless) |
| IP | 192.168.100.10 (static) |
| Hostname | derbynetpi |
| Timezone | America/Edmonton |

## Quick Start

### Prerequisites

1. Flash **Raspberry Pi OS Lite 64-bit** to SD card using Raspberry Pi Imager
2. During imaging, configure:
   - Enable SSH
   - Set username: `derbynet`
   - Set password
   - Set hostname: `derbynetpi`
   - Set locale/timezone: America/Edmonton

3. Configure static IP (optional, can be done post-boot):

   Add to `/boot/firmware/cmdline.txt`:
   ```
   ip=192.168.100.10::192.168.100.1:255.255.255.0:derbynetpi:eth0:off
   ```

### Bootstrap Installation

SSH into the Raspberry Pi and run:

```bash
curl -sSL https://raw.githubusercontent.com/jimidarke/sbderbynet/master/extras/derbypi/bootstrap.sh | sudo bash
```

Or download and run manually:

```bash
wget https://raw.githubusercontent.com/jimidarke/sbderbynet/master/extras/derbypi/bootstrap.sh
chmod +x bootstrap.sh
sudo ./bootstrap.sh
```

The bootstrap script will:
1. Install Ansible and Git
2. Clone the SBDerbyNet repository
3. Run the full Ansible playbook
4. Set up systemd timer for automatic updates
5. Display the public key for SaaS registration

### Reboot

After bootstrap completes, reboot to apply kernel/boot changes (RTC, WiFi/BT disable):

```bash
sudo reboot
```

## What Gets Installed

### System Services

| Service | Port | Description |
|---------|------|-------------|
| Mosquitto | 1883 | MQTT broker for device communication |
| Nginx | 80 | Web server for DerbyNet interface |
| PHP-FPM | socket | PHP FastCGI process manager |
| derbyrace | - | Race coordination service |
| derbytime | - | Time synchronization service |
| Chrony | 123 | NTP server for network devices |
| Rsyslog | 514/UDP | Centralized logging receiver |
| Rsync | 873 | Device update daemon |

### Directory Structure

```
/var/www/html/derbynet/     # DerbyNet web application
/var/www/html/derbynet/local/  # Local config (config-database.inc)
/var/lib/derbynet/          # Race data (database, photos, slides)
/var/lib/derbynet/keys/     # RSA keypair for SaaS auth
/var/lib/infra/             # Infrastructure components
/var/log/derbynet.log       # Unified log file
/opt/derbynet-repo/         # Git repository clone
```

## Ansible Roles

| Role | Purpose |
|------|---------|
| **common** | Hostname, timezone, directories, user, disable WiFi/BT |
| **rtc** | DS3231 RTC configuration, I2C overlay |
| **ntp** | Chrony NTP server for local network |
| **logging** | Rsyslog UDP receiver for remote devices |
| **mosquitto** | MQTT broker installation and config |
| **php** | PHP-FPM with DerbyNet settings |
| **nginx** | Web server with DerbyNet site config |
| **python** | Python 3 packages for race services |
| **derbynet** | Sync website and infra files from repo |
| **raceserver** | derbyrace and derbytime systemd services |
| **rsync** | Rsync daemon for device updates |
| **saasbox** | RSA-2048 keypair generation |

## Automatic Updates

The bootstrap script installs a systemd timer that runs `ansible-pull` every 30 minutes:

```bash
# Check timer status
systemctl status ansible-pull.timer

# View last run
journalctl -u ansible-pull.service

# Trigger manual update
sudo systemctl start ansible-pull.service
```

## Verification

After deployment, verify all services:

```bash
# All services running
systemctl status mosquitto nginx php*-fpm derbyrace derbytime rsync rsyslog chrony

# MQTT connectivity
mosquitto_pub -h localhost -t "derbynet/test" -m "hello"
mosquitto_sub -h localhost -t "derbynet/test" -C 1

# Web server responds
curl -I http://localhost/derbynet/

# API works
curl "http://localhost/derbynet/action.php?query=poll.coordinator"

# rsyslog listening
ss -ulnp | grep 514

# rsync daemon
rsync rsync://localhost/derbynet/

# RTC working
sudo hwclock --show

# NTP serving clients
chronyc clients

# ansible-pull timer active
systemctl status ansible-pull.timer

# SaaS public key generated
cat /var/lib/derbynet/keys/device.pub
```

## Manual Ansible Run

To run the playbook manually (without ansible-pull):

```bash
cd /opt/derbynet-repo
sudo ansible-playbook extras/derbypi/ansible/playbook.yml --connection=local -i localhost,
```

Run specific roles with tags:

```bash
# Only nginx configuration
ansible-playbook extras/derbypi/ansible/playbook.yml -t nginx

# All web-related roles
ansible-playbook extras/derbypi/ansible/playbook.yml -t web

# Only application deployment
ansible-playbook extras/derbypi/ansible/playbook.yml -t app
```

## Configuration Variables

All configuration is in `ansible/group_vars/all.yml`:

```yaml
# Network
derbypi_hostname: "derbynetpi"
derbypi_static_ip: "192.168.100.10"
derbypi_timezone: "America/Edmonton"

# Directories
derbynet_web_root: "/var/www/html/derbynet"
derbynet_data_dir: "/var/lib/derbynet"
derbynet_infra_dir: "/var/lib/infra"

# Services
mqtt_port: 1883
rsyslog_udp_port: 514
rsync_port: 873
```

## SaaS Integration

On first boot, the saasbox role generates an RSA-2048 keypair:

- **Private key**: `/var/lib/derbynet/keys/device.key` (mode 600)
- **Public key**: `/var/lib/derbynet/keys/device.pub` (mode 644)

The public key is displayed at the end of bootstrap. Register this key in the SaaS dashboard to enable cloud features.

View the public key anytime:
```bash
cat /var/lib/derbynet/keys/device.pub
```

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u <service-name> -e --no-pager
```

### MQTT issues
```bash
mosquitto_sub -h localhost -t "#" -v  # Monitor all topics
```

### Web 502 errors
```bash
sudo systemctl restart php*-fpm nginx
```

### ansible-pull failures
```bash
sudo journalctl -u ansible-pull.service -e
sudo systemctl start ansible-pull.service  # Retry
```

### RTC not detected
```bash
sudo i2cdetect -y 1  # Should show 68 or UU at 0x68
dmesg | grep -i rtc
cat /boot/firmware/config.txt | grep -E "i2c|rtc"
```

## File Inventory

```
extras/derbypi/
├── ansible/
│   ├── playbook.yml              # Main playbook
│   ├── ansible.cfg               # Ansible configuration
│   ├── inventory/
│   │   └── hosts.yml             # Localhost inventory
│   ├── group_vars/
│   │   └── all.yml               # Configuration variables
│   └── roles/
│       ├── common/               # Base system config
│       ├── rtc/                  # DS3231 RTC
│       ├── ntp/                  # Chrony NTP server
│       ├── logging/              # Rsyslog UDP
│       ├── mosquitto/            # MQTT broker
│       ├── php/                  # PHP-FPM
│       ├── nginx/                # Web server
│       ├── python/               # Python packages
│       ├── derbynet/             # Website sync
│       ├── raceserver/           # Race services
│       ├── rsync/                # Rsync daemon
│       └── saasbox/              # RSA keypair
├── bootstrap.sh                  # One-time setup script
└── README.md                     # This file
```

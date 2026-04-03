# DerbyPi Deployment

## Purpose

Automated one-command bootstrap for a fresh Raspberry Pi as a complete DerbyNet race server. Uses Ansible for reproducible, self-updating deployments with all services pre-configured.

## How It Fits

This is the deployment system for the race-day server Pi. It installs and configures the DerbyNet PHP app, Race Server, MQTT broker, and all supporting services on a single Raspberry Pi that serves as the central hub for the entire race network.

## Key Files

- `bootstrap.sh` — One-line curl install from GitHub (entry point)
- `ansible/playbook.yml` — Main playbook with 13 roles
- `README.md` — Complete deployment guide
- `DEPLOYMENT.md` — Detailed deployment procedures

## Ansible Roles

`common, rtc, ntp, logging, mosquitto, php, nginx, python, derbynet, raceserver, rsync, saasbox`

## Target Configuration

- **OS**: Raspberry Pi OS Lite 64-bit (headless)
- **IP**: `192.168.100.10` (static recommended)
- **Hostname**: `derbynetpi`
- **Timezone**: `America/Edmonton`

## Services Installed

- Mosquitto MQTT (port 1883)
- Nginx (port 80) + PHP-FPM
- derbyrace + derbytime (Python race services)
- Chrony NTP, Rsyslog (UDP 514), Rsync (873)

## Dependencies

- Fresh Raspberry Pi OS Lite 64-bit image
- Network connectivity for initial bootstrap
- DS3231 RTC module + I2C overlay

## Common Tasks

- **Bootstrap**: `curl -sSL https://raw.githubusercontent.com/.../bootstrap.sh | bash`
- **Self-update**: `ansible-pull` runs every 30 minutes automatically
- **Manual update**: `ansible-pull -U <repo-url>`

## Gotchas

- **SD card imaging**: Must be done before bootstrap — see `README.md`
- **RTC required**: DS3231 real-time clock needed for accurate timing without internet
- **WiFi/Bluetooth disabled**: Intentionally disabled for performance on race day
- **RSA keypair**: Auto-generated for SaaS authentication during bootstrap
- **Native Python**: No Docker on Pi — uses native Python for optimal performance

## Related Docs

- [README.md](README.md) — Complete deployment guide
- [DEPLOYMENT.md](DEPLOYMENT.md) — Detailed procedures and troubleshooting

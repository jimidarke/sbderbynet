# DerbyPi

The race-day Raspberry Pi. **Native install — no Docker** on the Pi (Docker is reserved for the cloud twin).

> **Race-day production deployment uses the SD-card image pipeline**, not the Ansible bootstrap documented below. Flash `sbderbynet-derbypi-<sha>.img.xz` from the latest CI build, edit `derbyid.txt`, boot — done in ~3 minutes. See the [SD-card recovery guide](https://github.com/jimidarke/sbderbynet/blob/master/docs/SD_CARD_RECOVERY.md) and [`extras/imaging/`](https://github.com/jimidarke/sbderbynet/tree/master/extras/imaging). The Ansible path below remains for developer use and one-off non-race deployments.

Lives at `extras/derbypi/`. Ansible + Bash.

---

## Target configuration

| Setting | Value |
|---|---|
| OS | Raspberry Pi OS Lite 64-bit (headless) |
| IP | `192.168.100.10` (static) |
| Hostname | `derbynetpi` |
| Timezone | `America/Edmonton` |
| RTC | DS3231 (required for accurate timing without internet) |
| WiFi/BT | **disabled** (race-day reliability) |

---

## Quick start

### 1. Image the SD card

Raspberry Pi Imager → **Raspberry Pi OS Lite 64-bit**. During imaging set:

- SSH enabled
- Username: `derbynet`
- Password (set one)
- Hostname: `derbynetpi`
- Locale/timezone: America/Edmonton

(Optional) static IP via `/boot/firmware/cmdline.txt`:

```
ip=192.168.100.10::192.168.100.1:255.255.255.0:derbynetpi:eth0:off
```

### 2. Bootstrap

SSH in and run:

```bash
curl -sSL https://raw.githubusercontent.com/jimidarke/sbderbynet/master/extras/derbypi/bootstrap.sh \
    | sudo bash
```

The bootstrap installs Ansible + Git, clones the repo, runs the full playbook, sets up a systemd timer for `ansible-pull`, and prints the SaaS public key.

### 3. Reboot

```bash
sudo reboot
```

Reboot is required to apply kernel/boot changes (RTC overlay, WiFi/BT disable).

---

## What gets installed

### Services

| Service | Port | Purpose |
|---|---|---|
| Mosquitto | 1883 | MQTT broker |
| Nginx | 80 | Web server |
| PHP-FPM | socket | PHP FastCGI |
| derbyrace | – | race coordination |
| derbytime | – | time sync |
| Chrony | 123 | NTP server for race subnet |
| Rsyslog | 514/UDP | centralised logging |
| Rsync | 873 | device update daemon |

### Filesystem layout

```
/var/www/html/derbynet/         # DerbyNet web app
/var/www/html/derbynet/local/   # local config (config-database.inc)
/var/lib/derbynet/              # race data (DB, photos, slides)
/var/lib/derbynet/keys/         # RSA keypair for SaaS auth
/var/lib/infra/                 # infrastructure components
/var/log/derbynet.log           # unified log
/opt/derbynet-repo/             # Git clone (used by ansible-pull)
```

### Ansible roles

`common, rtc, ntp, logging, mosquitto, php, nginx, python, derbynet, raceserver, rsync, saasbox` — defined under `ansible/roles/`.

---

## Auto-updates

A systemd timer runs `ansible-pull` every 30 minutes:

```bash
systemctl status ansible-pull.timer
journalctl -u ansible-pull.service
sudo systemctl start ansible-pull.service     # trigger now
```

---

## Verification

```bash
# All services up
systemctl status mosquitto nginx php*-fpm derbyrace derbytime rsync rsyslog chrony

# MQTT round-trip
mosquitto_pub -h localhost -t derbynet/test -m hello
mosquitto_sub -h localhost -t derbynet/test -C 1

# Web responds
curl -I http://localhost/derbynet/

# API
curl 'http://localhost/derbynet/action.php?query=poll.coordinator'

# Rsyslog UDP listening
ss -ulnp | grep 514

# Rsync daemon
rsync rsync://localhost/derbynet/

# RTC alive
sudo hwclock --show

# NTP serving
chronyc clients

# SaaS key
cat /var/lib/derbynet/keys/device.pub
```

---

## Manual playbook run

```bash
cd /opt/derbynet-repo
sudo ansible-playbook extras/derbypi/ansible/playbook.yml \
       --connection=local -i localhost,
```

Tag-scoped runs:

```bash
ansible-playbook extras/derbypi/ansible/playbook.yml -t nginx
ansible-playbook extras/derbypi/ansible/playbook.yml -t web
ansible-playbook extras/derbypi/ansible/playbook.yml -t app
```

---

## Configuration variables

`ansible/group_vars/all.yml`:

```yaml
derbypi_hostname: "derbynetpi"
derbypi_static_ip: "192.168.100.10"
derbypi_timezone: "America/Edmonton"

derbynet_web_root: "/var/www/html/derbynet"
derbynet_data_dir: "/var/lib/derbynet"
derbynet_infra_dir: "/var/lib/infra"

mqtt_port: 1883
rsyslog_udp_port: 514
rsync_port: 873
```

---

## SaaS key pair

On first boot, the `saasbox` role generates an RSA-2048 keypair at:

- Private: `/var/lib/derbynet/keys/device.key` (mode 600)
- Public: `/var/lib/derbynet/keys/device.pub` (mode 644)

The public key is printed at the end of bootstrap; register it in the SaaS dashboard to enable cloud features.

---

## Troubleshooting

```bash
# Service won't start
sudo journalctl -u <service-name> -e --no-pager

# MQTT issues
mosquitto_sub -h localhost -t '#' -v

# 502 from nginx
sudo systemctl restart php*-fpm nginx

# ansible-pull failure
sudo journalctl -u ansible-pull.service -e
sudo systemctl start ansible-pull.service

# RTC not detected
sudo i2cdetect -y 1                        # expect 68 or UU at 0x68
dmesg | grep -i rtc
cat /boot/firmware/config.txt | grep -E "i2c|rtc"
```

See also: [Network](../architecture/network.md), [Race Server](race-server.md), [VPS Procedures](../operations/vps-procedures.md) (the cloud-side counterpart).

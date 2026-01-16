# DerbyPi Deployment Guide

Step-by-step instructions for deploying a DerbyNet server on Raspberry Pi.

---

## Prerequisites

### Hardware Required
- Raspberry Pi 4 (2GB+ RAM recommended)
- MicroSD card (16GB+ recommended)
- DS3231 RTC module (connected via I2C)
- Ethernet cable (WiFi is disabled for reliability)
- Power supply (5V 3A USB-C)

### Software Required
- [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your computer
- SSH client (Terminal on Mac/Linux, PuTTY or Windows Terminal on Windows)

---

## Step 1: Flash the SD Card

1. Insert the MicroSD card into your computer

2. Open **Raspberry Pi Imager**

3. Click **Choose OS** → **Raspberry Pi OS (other)** → **Raspberry Pi OS Lite (64-bit)**

4. Click **Choose Storage** and select your MicroSD card

5. Click the **gear icon** (⚙️) or press `Ctrl+Shift+X` to open Advanced Options:

   | Setting | Value |
   |---------|-------|
   | Set hostname | `derbynetpi` |
   | Enable SSH | ✓ Use password authentication |
   | Set username | `derbynet` |
   | Set password | (your choice - remember this!) |
   | Set locale | `America/Edmonton` |
   | Set keyboard | `us` |

6. Click **Save**, then **Write**

7. Wait for imaging to complete

---

## Step 2: Configure Static IP (Pre-Boot)

Before inserting the SD card into the Pi, configure the static IP:

### Option A: Edit cmdline.txt (Recommended)

1. Open the `boot` partition on the SD card

2. Edit `cmdline.txt` and add to the **end of the existing line** (keep it all on one line):
   ```
   ip=192.168.100.10::192.168.100.1:255.255.255.0:derbynetpi:eth0:off
   ```

### Option B: Configure After Boot

Skip this step and configure via `/etc/dhcpcd.conf` after first boot (see Troubleshooting).

---

## Step 3: Connect Hardware

1. **Connect the DS3231 RTC module** to the Pi's GPIO header:
   | RTC Pin | Pi Pin | GPIO |
   |---------|--------|------|
   | VCC | Pin 1 | 3.3V |
   | GND | Pin 6 | Ground |
   | SDA | Pin 3 | GPIO2 |
   | SCL | Pin 5 | GPIO3 |

2. **Connect Ethernet cable** to your network

3. **Insert the SD card** into the Pi

4. **Connect power** - the Pi will boot automatically

---

## Step 4: First Boot & SSH Connection

1. Wait 1-2 minutes for the Pi to boot

2. Find the Pi on your network:
   - If you configured static IP: `192.168.100.10`
   - If using DHCP: Check your router's client list or use `ping derbynetpi.local`

3. SSH into the Pi:
   ```bash
   ssh derbynet@192.168.100.10
   ```
   Enter the password you set during imaging.

---

## Step 5: Run Bootstrap Script

Run the automated deployment:

```bash
curl -sSL https://raw.githubusercontent.com/jimidarke/sbderbynet/master/extras/derbypi/bootstrap.sh | sudo bash
```

Or if you prefer to review before running:

```bash
wget https://raw.githubusercontent.com/jimidarke/sbderbynet/master/extras/derbypi/bootstrap.sh
cat bootstrap.sh  # Review the script
chmod +x bootstrap.sh
sudo ./bootstrap.sh
```

The script will:
- Install Ansible and Git
- Clone the SBDerbyNet repository
- Run the full Ansible playbook (installs all services)
- Set up automatic updates via ansible-pull
- Generate RSA keypair for SaaS integration
- Display the public key at the end

**This takes 10-20 minutes** depending on your internet speed.

---

## Step 6: Reboot

After bootstrap completes, reboot to apply kernel changes (RTC, disable WiFi/BT):

```bash
sudo reboot
```

Wait 1 minute, then SSH back in:

```bash
ssh derbynet@192.168.100.10
```

---

## Step 7: Verify Installation

Run these checks to confirm everything is working:

### Check Services
```bash
# All services should show "active (running)"
sudo systemctl status mosquitto nginx php8.2-fpm derbyrace derbytime rsync rsyslog chrony --no-pager
```

### Check MQTT
```bash
# In one terminal, subscribe:
mosquitto_sub -h localhost -t "derbynet/test" &

# Publish a test message:
mosquitto_pub -h localhost -t "derbynet/test" -m "hello"
# Should see "hello" output

# Kill the subscriber
kill %1
```

### Check Web Interface
```bash
curl -I http://localhost/derbynet/
# Should return HTTP 200 OK
```

Open in a browser: `http://192.168.100.10/derbynet/`

### Check RTC
```bash
sudo hwclock --show
# Should display current date/time
```

### Check NTP
```bash
chronyc tracking
# Should show synchronized time source
```

### Check Rsyslog
```bash
ss -ulnp | grep 514
# Should show rsyslog listening on UDP 514
```

### Check Rsync
```bash
rsync rsync://localhost/derbynet/
# Should list available modules
```

### Check ansible-pull Timer
```bash
systemctl status ansible-pull.timer
# Should show "active (waiting)"
```

---

## Step 8: Save the Public Key

The bootstrap script displays the device's public key at the end. Save this for SaaS registration:

```bash
cat /var/lib/derbynet/keys/device.pub
```

Copy this entire key (including `-----BEGIN PUBLIC KEY-----` and `-----END PUBLIC KEY-----` lines) for registering this device with the SaaS dashboard.

---

## Post-Deployment

### Automatic Updates

The server automatically checks for updates every 30 minutes via `ansible-pull`. To manually trigger an update:

```bash
sudo systemctl start ansible-pull.service
```

Check update logs:
```bash
journalctl -u ansible-pull.service -e
```

### View Logs

```bash
# DerbyNet unified log (all components)
tail -f /var/log/derbynet.log

# Race server
journalctl -u derbyrace -f

# Time service
journalctl -u derbytime -f

# Web server
tail -f /var/log/nginx/derbynet_access.log
```

### Service Management

```bash
# Restart a service
sudo systemctl restart derbyrace

# Stop a service
sudo systemctl stop derbytime

# Check service status
sudo systemctl status mosquitto
```

---

## Network Reference

| Device | IP Address | Purpose |
|--------|------------|---------|
| DerbyPi Server | 192.168.100.10 | Central server |
| Gateway/Router | 192.168.100.1 | Network gateway |
| Finish Timers | 192.168.100.20-29 | Lane timing devices |
| Start Timer | 192.168.100.30 | Race start detection |
| Display Nodes | 192.168.100.40-49 | Information displays |

| Service | Port | Protocol |
|---------|------|----------|
| HTTP (DerbyNet) | 80 | TCP |
| MQTT | 1883 | TCP |
| NTP | 123 | UDP |
| Syslog | 514 | UDP |
| Rsync | 873 | TCP |

---

## Troubleshooting

### Can't SSH to the Pi

1. Verify the Pi is powered on (red LED solid, green LED flashing)
2. Check ethernet cable is connected
3. Try pinging: `ping 192.168.100.10`
4. If using DHCP, check your router for the Pi's IP address
5. Try: `ssh derbynet@derbynetpi.local`

### Static IP Not Working

Configure after boot via SSH (use DHCP IP first):

```bash
sudo nano /etc/dhcpcd.conf
```

Add at the end:
```
interface eth0
static ip_address=192.168.100.10/24
static routers=192.168.100.1
static domain_name_servers=192.168.100.1 8.8.8.8
```

Reboot: `sudo reboot`

### RTC Not Detected

Check I2C connection:
```bash
sudo i2cdetect -y 1
```

Should show `68` or `UU` at address 0x68. If not:
- Check wiring connections
- Verify `/boot/firmware/config.txt` contains:
  ```
  dtparam=i2c_arm=on
  dtoverlay=i2c-rtc,ds3231
  ```
- Reboot and try again

### Web Interface Shows 502 Error

Restart PHP and Nginx:
```bash
sudo systemctl restart php8.2-fpm nginx
```

Check PHP-FPM status:
```bash
sudo systemctl status php8.2-fpm
```

### MQTT Connection Refused

Check Mosquitto is running:
```bash
sudo systemctl status mosquitto
journalctl -u mosquitto -e
```

Common fix for "duplicate persistence_location" error:
```bash
sudo nano /etc/mosquitto/conf.d/derbynet.conf
# Remove any persistence_location line if present
sudo systemctl restart mosquitto
```

### Bootstrap Script Fails

Run Ansible manually with verbose output:
```bash
cd /opt/derbynet-repo
sudo ansible-playbook extras/derbypi/ansible/playbook.yml -v --connection=local -i localhost,
```

### Services Not Starting After Reboot

Check for errors:
```bash
journalctl -b -p err
```

Re-run Ansible:
```bash
sudo systemctl start ansible-pull.service
```

---

## Factory Reset

To completely reset and re-deploy:

```bash
# Stop services
sudo systemctl stop derbyrace derbytime

# Remove repo and re-bootstrap
sudo rm -rf /opt/derbynet-repo
curl -sSL https://raw.githubusercontent.com/jimidarke/sbderbynet/master/extras/derbypi/bootstrap.sh | sudo bash

# Reboot
sudo reboot
```

**Note:** This preserves race data in `/var/lib/derbynet/`. To also reset race data:
```bash
sudo rm -rf /var/lib/derbynet/*
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│  DerbyPi Quick Reference                                    │
├─────────────────────────────────────────────────────────────┤
│  SSH:        ssh derbynet@192.168.100.10                    │
│  Web UI:     http://192.168.100.10/derbynet/                │
│                                                             │
│  Services:   sudo systemctl status derbyrace derbytime      │
│  Logs:       tail -f /var/log/derbynet.log                  │
│  Update:     sudo systemctl start ansible-pull.service      │
│                                                             │
│  MQTT Test:  mosquitto_pub -t "test" -m "hello"             │
│  RTC Check:  sudo hwclock --show                            │
│  API Test:   curl "localhost/derbynet/action.php?query=     │
│              poll.coordinator"                              │
└─────────────────────────────────────────────────────────────┘
```

# Finish Timer Ansible Deployment

Ansible automation for deploying Raspberry Pi Zero finish timer devices.

## Overview

The finish timer system consists of Raspberry Pi Zero W/2W devices with custom PCBs that detect when cars cross the finish line. Each device:

- Reads a unique device ID from `/boot/firmware/derbyid.txt`
- Communicates via MQTT to the race server
- Uses I2C for battery monitoring (MCP3421 ADC)
- Drives a TM1637 7-segment display
- Reads GPIO inputs from toggle/DIP switches
- Syncs time via NTP to the race server

## Prerequisites

### Hardware
- Raspberry Pi Zero W or Zero 2W
- DerbyNet custom PCB v1
- MicroSD card (8GB+)

### Software
- Ansible 2.9+ on your control machine
- Pi OS Lite pre-imaged on SD cards

### Network

| Device | IP Address | Purpose |
|--------|------------|---------|
| Race Server | 192.168.100.10 | MQTT broker, NTP |
| Lane 1 Timer | 192.168.100.21 | Finish detection |
| Lane 2 Timer | 192.168.100.22 | Finish detection |
| Lane 3 Timer | 192.168.100.23 | Finish detection |

## Initial SD Card Setup

1. **Flash Pi OS Lite** using Raspberry Pi Imager

2. **Configure in Imager** (gear icon):
   - Enable SSH with password or public key
   - Username: `pi`
   - WiFi credentials for race network
   - Timezone: `America/Edmonton`

3. **Set static IP** after first boot in `/etc/dhcpcd.conf`:
   ```
   interface wlan0
   static ip_address=192.168.100.21/24
   static routers=192.168.100.1
   static domain_name_servers=192.168.100.1 8.8.8.8
   ```

4. **Verify SSH access**: `ssh pi@192.168.100.21`

## Deployment

### Bootstrap (Once per new device)

```bash
cd extras/soapbox/infra/finishtimer/ansible

# Single device
ansible-playbook bootstrap.yml -l lane1-timer

# All devices
ansible-playbook bootstrap.yml
```

This configures:
- Device ID in `/boot/firmware/derbyid.txt`
- Hostname
- I2C hardware
- Power optimizations
- Required packages
- Triggers reboot

### Deploy Application

```bash
# All timers
ansible-playbook deploy.yml

# Single timer
ansible-playbook deploy.yml -l lane2-timer

# Application only (faster)
ansible-playbook deploy.yml --tags application
```

### Verify

```bash
# Check service status
ansible finishtimers -m shell -a "systemctl status finishtimer"

# Check MQTT from race server
mosquitto_sub -h 192.168.100.10 -t 'derbynet/device/+/status'
```

## Inventory

Edit `inventory/hosts.yml` to add/modify timers:

```yaml
finishtimers:
  hosts:
    lane1-timer:
      ansible_host: 192.168.100.21
      finishtimer_derbyid: DT_54siv_0001
      finishtimer_lane: 1
    # Add more lanes as needed
```

## Available Tags

| Tag | Description |
|-----|-------------|
| `hardware` | I2C, GPIO, user/group |
| `power` | Power optimization |
| `packages` | System and pip packages |
| `application` | Files, service, NTP |
| `finishtimer` | All tasks |

## Dry Run

```bash
ansible-playbook deploy.yml --check --diff
```

## Troubleshooting

### Connection Issues
```bash
ping 192.168.100.21
ssh pi@192.168.100.21
```

### Service Won't Start
```bash
ssh pi@192.168.100.21 "journalctl -u finishtimer -n 50"
```

### I2C Not Working
```bash
ssh pi@192.168.100.21 "sudo i2cdetect -y 1"
```

### Time Not Syncing
```bash
ssh pi@192.168.100.21 "timedatectl show-timesync"
```

## File Locations

### On Timer Device
| Path | Description |
|------|-------------|
| `/opt/derbynet/files/` | Python application |
| `/boot/firmware/derbyid.txt` | Device ID |
| `/var/log/derbynet.log` | Application log |
| `/etc/systemd/system/finishtimer.service` | Service unit |

### Ansible Files
| Path | Description |
|------|-------------|
| `inventory/hosts.yml` | Device inventory |
| `group_vars/all.yml` | Global variables |
| `roles/finishtimer/` | Deployment role |
| `bootstrap.yml` | Initial setup |
| `deploy.yml` | Application deployment |

## Quick Reference

```bash
# Bootstrap new device
ansible-playbook bootstrap.yml -l lane1-timer

# Deploy all
ansible-playbook deploy.yml

# Deploy single
ansible-playbook deploy.yml -l lane2-timer

# App update only
ansible-playbook deploy.yml --tags application

# Dry run
ansible-playbook deploy.yml --check --diff

# Service status
ansible finishtimers -m shell -a "systemctl status finishtimer"

# Restart service
ansible finishtimers -m systemd -a "name=finishtimer state=restarted"

# Reboot all
ansible finishtimers -m reboot
```

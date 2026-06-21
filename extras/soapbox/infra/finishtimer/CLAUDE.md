# Finish Timer

## Purpose

Raspberry Pi-based lane finish detection. Uses physical toggle switches to detect when a car crosses the finish line, reports times via MQTT, and provides visual feedback through RGB LEDs and a 7-segment display.

## How It Fits

One finish timer per lane. Each publishes finish events to MQTT, which the Race Server consumes to record lane times. The timer also subscribes to race state to know when to arm for detection.

## Key Files

- `files/finishtimer.py` — Main service (v0.9.0). GPIO monitoring, MQTT pub/sub, LED/display control
- `setup.sh` — Service installation script
- `sync.sh` — File synchronization to Pi
- `board.txt` — DerbyNet PCB v1 hardware pinout specification

## Hardware

- **Platform**: Raspberry Pi with DerbyNet PCB v1
- **Detection**: Toggle switch on GPIO 24
- **Feedback**: RGB LED (connection/race status), 4-digit 7-segment display
- **Configuration**: DIP switches set lane number (1-4)
- **Power**: I2C ADC for battery monitoring

## Dependencies

- Python 3, paho-mqtt, RPi.GPIO
- MQTT broker on `192.168.100.10:1883`

## Common Tasks

- **Deploy**: `./sync.sh` to push files, `./setup.sh` on Pi to install service
- **Run**: `sudo systemctl start finishtimer`
- **Monitor**: Watch MQTT topic `derbynet/device/{hwid}/telemetry`

## Gotchas

- **Network resilience**: Exponential backoff on MQTT disconnect, local message queue during outages
- **LED color codes**: Red=disconnected, Blue=connecting, Green=ready, Purple=racing, Yellow=error
- **Hardware ID**: Derived from MAC address or `/boot/firmware/derbyid.txt`

## Related Docs

- [README.md](README.md) — Full hardware documentation and GPIO pinout
- [board.txt](board.txt) — PCB v1 specifications
- [ansible/README.md](ansible/README.md) — Ansible automation for timer setup

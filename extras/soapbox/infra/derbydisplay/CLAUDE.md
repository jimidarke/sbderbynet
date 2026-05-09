# Derby Display

## Purpose

Manages kiosk display screens on Raspberry Pi devices. Launches Chromium in kiosk mode pointing at DerbyNet kiosk pages, reports health telemetry via MQTT, and handles display configuration.

## How It Fits

Display Pis connect to the DerbyNet web app for content (kiosk pages) and to MQTT for real-time state updates. The coordinator page controls which scene/kiosk each display shows.

## Key Files

- `derbydisplay.py` — Main service. Chromium kiosk management, MQTT telemetry, display configuration
- `kiosk.sh` — Chromium kiosk mode launcher
- `setup.sh` — Service installation and Pi configuration
- `derbydisplay.service` — systemd service definition

## Hardware

- **Platform**: Raspberry Pi 3B+ or newer
- **Display**: HDMI monitor/TV
- **Power**: 5V 3A supply recommended

## Dependencies

- Python 3, paho-mqtt, Chromium browser
- DerbyNet web server for kiosk page content
- MQTT broker on `192.168.100.10:1883`

## Common Tasks

- **Deploy**: Run `setup.sh` on Pi
- **Run**: `sudo systemctl start derbydisplay`
- **Monitor**: MQTT topic `derbynet/device/{hwid}/telemetry` (every 5 seconds)

## Gotchas

- **HDMI negotiation**: Some TVs need `force-1080p.sh` for proper resolution
- **Hardware ID**: Read from `/boot/firmware/derbyid.txt` or derived from MAC address
- **Overscan**: May need adjustment in Pi config for certain displays

## Related Docs

- [README.md](README.md) — Full setup and troubleshooting guide

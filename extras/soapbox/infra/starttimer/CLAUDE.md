# Start Timer

## Purpose

ESP32-based race start signal detection. Detects gate opening via a start switch, broadcasts a timestamped start event over MQTT so all race components can synchronize timing.

## How It Fits

Publishes MQTT GO signal when the start gate opens. The Race Server uses this timestamp to calculate elapsed times. If this hardware is unavailable, the coordinator page provides a manual start button that publishes to `derbynet/device/manualstart/state`.

## Key Files

- `src/main.py` — Main application logic (MicroPython)
- `src/boot.py` — WiFi connection and startup
- `copytoweb.sh` — OTA firmware update helper

## Hardware

- **Platform**: ESP32 microcontroller (MicroPython)
- **Detection**: Start switch on GPIO 33
- **Sensors**: DHT22 temperature/humidity on GPIO 32
- **Feedback**: Built-in LED on GPIO 2
- **Power**: Battery-operated for portable start line positioning

## Dependencies

- MicroPython firmware on ESP32
- WiFi access to race network
- MQTT broker on `192.168.100.10:1883`

## Common Tasks

- **Flash firmware**: Upload MicroPython, then copy `src/` files
- **OTA update**: Use `copytoweb.sh` to serve firmware via HTTP

## Gotchas

- **WiFi credentials**: Hardcoded in firmware — update before flashing
- **Manual fallback**: Coordinator page shows green "Start" button when hardware timer is unavailable (requires `mosquitto_pub` on web server)
- **OTA**: Requires HTTP server hosting the firmware file

## Related Docs

- [README.md](README.md) — Setup and hardware documentation

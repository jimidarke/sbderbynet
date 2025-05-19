# Start Timer Component

This is the ESP32-based start timer for the Soapbox Derby race management system. It detects race start events and broadcasts them via MQTT to synchronize race timing across the system.

## Overview

The Start Timer:
- Detects when the starting gate opens using a hardware sensor
- Immediately broadcasts the start event with precise timestamps
- Reports telemetry data including temperature and humidity
- Supports over-the-air (OTA) updates for firmware maintenance

## Components

- **main.py**: MicroPython code that runs on the ESP32
- **boot.py**: Initial boot sequence and configuration
- **copytoweb.sh**: Script to copy firmware files to web server for OTA updates

## Hardware

The Start Timer uses the following hardware components:
- ESP32 microcontroller
- Start detection switch connected to GPIO 33
- DHT22 temperature and humidity sensor on GPIO 32
- LED indicator on GPIO 2 (built-in)

## Installation

1. Flash MicroPython to the ESP32:
   ```bash
   esptool.py --port /dev/ttyUSB0 erase_flash
   esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash --flash_size=detect 0 esp32-20220618-v1.19.1.bin
   ```

2. Upload code to the ESP32:
   ```bash
   ampy --port /dev/ttyUSB0 put main.py
   ampy --port /dev/ttyUSB0 put boot.py
   ```

3. Place the start timer at the starting gate with proper sensor connection

## Configuration

The Start Timer uses the following configuration:
- Wi-Fi network: DerbyNet
- MQTT broker: 192.168.100.10
- NTP server: 192.168.100.10
- OTA update URL: http://192.168.100.10/starttimer/main.py

## Operating Modes

The start timer operates in these modes:
1. **Normal Operation**: Monitoring start signal and sending telemetry
2. **OTA Update**: Receiving and applying firmware updates
3. **Failsafe Recovery**: Auto-reset if critical errors occur

## MQTT Topics

The Start Timer uses these MQTT topics:
- `derbynet/device/starttimer/status`: Online/offline status
- `derbynet/device/starttimer/state`: Start signal state (GO/STOP)
- `derbynet/device/starttimer/telemetry`: Device telemetry data
- `derbynet/device/starttimer/update`: OTA update trigger

## Telemetry Data

The device reports these telemetry metrics:
- Wi-Fi signal strength (RSSI)
- IP and MAC address
- Temperature and humidity (from DHT22)
- Device uptime
- Firmware version
- Current start signal state

## OTA Updates

To update the firmware remotely:
1. Copy the new firmware to the web server:
   ```bash
   ./copytoweb.sh
   ```
2. Trigger the update by publishing to the update topic:
   ```bash
   mosquitto_pub -h 192.168.100.10 -t derbynet/device/starttimer/update -m "update"
   ```

## Troubleshooting

### Common Issues

1. **Not connecting to Wi-Fi**
   - Check Wi-Fi credentials in main.py
   - Verify the ESP32 is within Wi-Fi range
   - Reboot the device to retry connection

2. **Start events not detected**
   - Check the physical connection to the start gate
   - Verify the switch is properly wired to GPIO 33
   - Check MQTT broker connectivity

3. **OTA update failing**
   - Verify the HTTP server is running and accessible
   - Check that the firmware file is correctly placed
   - Ensure the ESP32 has sufficient memory for the update
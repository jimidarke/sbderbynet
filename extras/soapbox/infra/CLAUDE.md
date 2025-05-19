# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a soapbox derby race management system that consists of several components:

1. **Server**: The central race management system that communicates with the DerbyNet software and coordinates with finish timers and displays
2. **Finish Timer**: Hardware timers installed at each lane that detect car finishes
3. **Start Timer**: ESP32-based device that detects race start signals
4. **Derby Display**: Display screen showing race status and results
5. **Streaming**: Camera streaming service for race viewing

The system primarily uses MQTT for communication between components, with a Python-based backend.

## Architecture

### Key Components

1. **Core Service (derbyRace.py)**: 
   - Central orchestration service that manages race state
   - Communicates with DerbyNet API
   - Coordinates start and finish timers via MQTT

2. **Finish Timer (finishtimer.py)**:
   - Monitors lane finish events using GPIO
   - Sends lane finish data to server via MQTT
   - Uses hardware PCB with toggle switches and LED indicators

3. **Start Timer (main.py on ESP32)**:
   - Detects race start signals
   - Broadcasts start events via MQTT

4. **Derby Display (derbydisplay.py)**:
   - Shows race information on displays
   - Updates in real-time via MQTT

5. **LCD Display (derbyLCD.py)**:
   - Controls small LCD displays for officials
   - Shows lane status and race information

6. **Stream Server (stream/app.py)**:
   - Handles video streaming for race viewing
   - Uses RTSP and HLS for streaming

### Communication Flow

1. Race initialization starts in derbyRace.py
2. Start signal is detected by ESP32 and sent via MQTT
3. Finish timers detect lane completions and send data via MQTT
4. derbyRace.py aggregates results and sends to DerbyNet API
5. Display components update with current race status
6. All components send telemetry for monitoring

## Configuration

The system expects a primary server with IP `192.168.100.10`. Devices like finish timers are identified by DIP switch settings that correspond to lane numbers.

## Deployment

The codebase includes deployment scripts for creating and deploying Raspberry Pi SD card images:

- `deployment/sdcard/createImage.sh`: Creates SD card images for deployment
- `deployment/sdcard/deployImage.sh`: Deploys images to SD cards with device-specific configuration

Device identification is managed through a `derbyid.txt` file on the boot partition.

## System Services

Components run as system services:

- **derbyRace**: Main server service
- **derbyTime**: Time synchronization service
- **finishtimer**: Lane finish detection service
- **derbydisplay**: Display management service

## Development Guidelines

1. **MQTT Topics**:
   - Device status: `derbynet/device/{id}/status`
   - Device telemetry: `derbynet/device/{id}/telemetry`
   - Device state: `derbynet/device/{id}/state`
   - Race state: `derbynet/race/state`
   - Lane LED control: `derbynet/lane/{lane}/led`
   - Lane pinny display: `derbynet/lane/{lane}/pinny`

2. **Telemetry Format**:
   Standard telemetry format across all devices includes:
   - hostname
   - hwid (hardware ID)
   - uptime
   - ip
   - mac
   - wifi_rssi
   - battery_level
   - cpu_temp
   - memory_usage
   - disk
   - cpu_usage

## Common Commands

### Starting Services

```bash
# Start the derby race management service
sudo systemctl start derbyrace

# Start the derby time service
sudo systemctl start derbyTime

# Start the finish timer service
sudo systemctl start finishtimer

# Start the derby display service
sudo systemctl start derbydisplay

# Start the streaming service
cd /path/to/stream && python app.py
```

### Deployment

```bash
# Create an SD card image from a source drive
./deployment/sdcard/createImage.sh /dev/sdX

# Deploy an image to an SD card with a specific device name
./deployment/sdcard/deployImage.sh /dev/sdX devicename
```

### Debug and Monitoring

The codebase uses standard Python logging through a `derbylogger` module. Logs are typically found in system journals:

```bash
# View logs for derby race service
sudo journalctl -u derbyrace

# View logs for finish timer
sudo journalctl -u finishtimer

# View logs for derby display 
sudo journalctl -u derbydisplay
```

## Hardware Interfaces

- **PCB Version 1 Finish Timer**:
  - `PIN_TOGGLE`: GPIO 24 - Finish detection toggle
  - `PIN_RED/GREEN/BLUE`: GPIO 8/7/1 - LED indicators
  - `PIN_DIP1-4`: GPIO 6/13/19/26 - DIP switches for lane configuration
  - `PIN_CLK/DIO`: GPIO 18/23 - 7-segment display control
  
- **ESP32 Start Timer**:
  - `START_PIN`: GPIO 33 - Start signal detection
  - `LED_PIN`: GPIO 2 - Status LED
  - `DHT_PIN`: GPIO 32 - Temperature/humidity sensor
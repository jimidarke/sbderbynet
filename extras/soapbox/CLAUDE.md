# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a comprehensive soapbox derby race management system built by extensively modifying the DerbyNet software. DerbyNet was originally created for Pinewood Derby racing events (small wooden cars racing down a gravity track), but has been extensively modified in this repository to support children's Soapbox Derby events (larger gravity-powered cars with children riding in them).

The system consists of several components:

1. **Server**: The central race management system that communicates with the modified DerbyNet software and coordinates with finish timers and displays
2. **Finish Timer**: Hardware timers installed at each lane that detect car finishes
3. **Start Timer**: ESP32-based device that detects race start signals
4. **Derby Display**: Display screen showing race status and results
5. **HLS Feed**: Camera streaming service for race viewing
6. **HLS Transcoder**: Dedicated component for transcoding video to HLS format and serving streams

This represents a significant overhaul of the original DerbyNet PHP code (found in the `/website` folder) with extensive new functionality in the `/extras/soapbox` folder to integrate hardware timing systems, lane detection, and video replay specifically for soapbox derby racing.

The system primarily uses MQTT for communication between components, with a Python-based backend deployed on Raspberry Pi devices.

## Architecture

### Key Components

1. **Core Service (derbyRace.py)**: 
   - Central orchestration service that manages race state
   - Communicates with DerbyNet API
   - Coordinates start and finish timers via MQTT

2. **Finish Timer (derbynetPCBv1.py)**:
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

6. **HLS Feed Service (hlsfeed)**:
   - Handles video streaming for race viewing
   - Uses RTSP and HLS for streaming
   - Integrates with DerbyNet's replay system

7. **HLS Transcoder Service (hlstranscoder)**:
   - Transcodes video input (RTSP) to HLS format
   - Provides adaptive streaming and replay capabilities
   - Runs on dedicated hardware for improved performance
   - Supports remote updates via MQTT and rsync
   - Includes web-based status and monitoring dashboard

### Communication Flow

1. Race initialization starts in derbyRace.py
2. Start signal is detected by ESP32 and sent via MQTT
3. Finish timers detect lane completions and send data via MQTT
4. derbyRace.py aggregates results and sends to DerbyNet API
5. Display components update with current race status
6. All components send telemetry for monitoring

## Original DerbyNet vs Soapbox Modifications

The original DerbyNet was designed for Pinewood Derby racing with:
- Simple timer interfaces (often just serial connections)
- Miniature wooden cars
- Typically shorter tracks with 3-6 lanes
- No video replay system

The soapbox derby modifications include significant enhancements:
- Hardware integration with custom PCBs for timing
- MQTT-based distributed architecture with multiple Raspberry Pi devices
- ESP32-based start detection
- HLS video streaming and replay system
- Enhanced real-time displays
- Network resilience features for outdoor operation
- Comprehensive telemetry system
- Modified race formats specific to soapbox derby

The `/website` folder contains the modified PHP code from the original DerbyNet, while the `/extras/soapbox` folder contains the new Python components developed specifically for soapbox derby racing.

## DerbyNet Integration

DerbyNet is a PHP-based web application that handles the front-end race management, which has been extensively modified for soapbox derby racing:

1. **Race Management**: Handles triple elimination format with preliminary, semi-final, and final rounds
2. **Timer Integration**: Communicates with our timing system via HTTP/AJAX with specific states (CONNECTED, STAGING, RUNNING, etc.)
3. **Kiosk System**: Supports various display types (now-racing, standings, ondeck, results-by-racer)
4. **HLS Replay System**: Integrates with our HLS feed for race replays with configurable options:
   - Replay length (default: 4000ms)
   - Replay count (default: 2)
   - Replay speed (default: 50%)
   - HLS stream URL: http://derbynetpi:8037/hls/stream.m3u8

## Configuration

The system expects a primary server with IP `192.168.100.10`. Devices like finish timers are identified by DIP switch settings that correspond to lane numbers.

## Common Commands

### Running Tests

The system provides comprehensive testing:

```bash
# Run all system tests
python3 tests/system_test.py

# Test specific component
python3 tests/system_test.py --test timers

# Verbose output
python3 tests/system_test.py --verbose

# Network resilience testing
python3 tests/network_resilience_test.py
python3 tests/network_resilience_test.py --scenario broker_restart --verbose
```

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

# Start the HLS feed service
sudo systemctl start hlsfeed

# Start the HLS transcoder service
sudo systemctl start hlstranscoder
```

### Deployment

```bash
# Create an SD card image from a source drive
./infra/deployment/sdcard/createImage.sh /dev/sdX

# Deploy an image to an SD card with a specific device name
./infra/deployment/sdcard/deployImage.sh /dev/sdX devicename
```

### Debug and Monitoring

```bash
# View logs for derby race service
sudo journalctl -u derbyrace

# View logs for finish timer
sudo journalctl -u finishtimer

# View logs for derby display 
sudo journalctl -u derbydisplay

# View logs for HLS feed
sudo journalctl -u hlsfeed

# View logs for HLS transcoder
sudo journalctl -u hlstranscoder
```

## MQTT Topic Structure

All MQTT topics use the prefix `derbynet/` followed by a category and specific identifiers:

- Race state: `derbynet/race/state`
- Device status: `derbynet/device/{id}/status`
- Device telemetry: `derbynet/device/{id}/telemetry`
- Lane LED control: `derbynet/lane/{lane}/led`
- Lane pinny display: `derbynet/lane/{lane}/pinny`

## Hardware Interfaces

- **PCB Version 1 Finish Timer**:
  - `PIN_TOGGLE`: GPIO 24 - Finish detection toggle
  - `PIN_RED/GREEN/BLUE`: GPIO 8/7/1 - LED indicators
  - `PIN_DIP1-4`: GPIO 6/13/19/26 - DIP switches for lane configuration
  - `PIN_CLK/DIO`: GPIO 18/23 - 7-segment display control
  
- **ESP32 Start Timer**:
  - `START_PIN`: GPIO 33 - Start signal detection
  - `LED_PIN`: GPIO 2 - Status LED

## Development Guidelines

### Versioning

The system uses semantic versioning (MAJOR.MINOR.PATCH). All components must:

1. Define a `VERSION` constant at the top of the file
2. Log the version on startup
3. Include version in telemetry data
4. Follow version update process documented in VERSION.md

### Telemetry Format

All device telemetry should include these standard fields:
- hostname
- hwid (hardware ID)
- version (firmware version)
- uptime
- ip
- mac
- wifi_rssi
- battery_level
- cpu_temp
- memory_usage
- disk
- cpu_usage

### Logging

The system uses a standardized logging library (derbylogger.py):
- Structured JSON logging
- Correlation IDs for cross-component tracking
- Centralized log aggregation

### Network Communication

All components should:
- Use service discovery via mDNS when possible
- Implement reconnection strategies
- Handle offline operation gracefully
- Use proper MQTT QoS levels
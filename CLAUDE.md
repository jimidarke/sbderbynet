# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This is a comprehensive soapbox derby race management system built by extensively modifying the DerbyNet software. DerbyNet was originally created for Pinewood Derby racing events (small wooden cars racing down a gravity track), but has been extensively modified to support children's Soapbox Derby events (larger gravity-powered cars with children riding in them).

**Current Version: 0.5.0**

## System Overview

This project is a comprehensive soapbox derby race management system built by extensively modifying the DerbyNet software. DerbyNet was originally created for Pinewood Derby racing events (small wooden cars racing down a gravity track), but has been extensively modified to support children's Soapbox Derby events (larger gravity-powered cars with children riding in them).

The system consists of several integrated components:

1. **DerbyNet PHP Core** (`/website/`): A PHP-based web application that handles race management, timing, results tracking, and award management
2. **Race Server** (`/extras/soapbox/infra/server/`): Central coordination server that manages race state and communicates with hardware components
3. **Finish Timer** (`/extras/soapbox/infra/finishtimer/`): Hardware-based finish line detection system using toggle switches on Raspberry Pi
4. **Start Timer** (`/extras/soapbox/infra/starttimer/`): ESP32-based device that detects race start signals 
5. **Derby Display** (`/extras/soapbox/infra/derbydisplay/`): Display screens showing race status and results
6. **HLS Feed** (`/extras/soapbox/hlsfeed/`): Camera streaming service for race viewing and replay

## License Information

This project is open source and released under the MIT License. The following license-related files are available in the repository:

1. `MIT-LICENSE.txt` - The main license file for the project
2. `LICENSE_HEADER.txt` - License header for PHP, JavaScript, CSS, and other files
3. `LICENSE_HEADER_PYTHON.txt` - License header for Python files
4. `extras/soapbox/LICENSE.txt` - License file for the Soapbox Derby extension
5. `LICENSE_UPDATE_INSTRUCTIONS.md` - Detailed instructions for updating license headers

### License Update Process

To ensure all files in the project have the proper license headers, we use the `update_licenses.sh` script. This script:

1. Reads license header templates from `LICENSE_HEADER.txt` and `LICENSE_HEADER_PYTHON.txt`
2. Finds files by extension (`.py`, `.php`, `.js`, `.css`, etc.)
3. Checks if files already have license headers
4. Adds the appropriate header to files that don't have them

Run the script with:
```bash
./update_licenses.sh
```

New files should always include the appropriate license header as described in `LICENSE_UPDATE_INSTRUCTIONS.md`.

## Architecture

### Key Components

1. **Core Service (derbyRace.py)**: 
   - Central orchestration service that manages race state
   - Communicates with DerbyNet API
   - Coordinates start and finish timers via MQTT
   - Located in `/extras/soapbox/infra/server/`

2. **Finish Timer (derbynetPCBv1.py)**:
   - Monitors lane finish events using GPIO
   - Sends lane finish data to server via MQTT
   - Uses hardware PCB with toggle switches and LED indicators
   - Located in `/extras/soapbox/infra/finishtimer/`

3. **Start Timer (main.py on ESP32)**:
   - Detects race start signals
   - Broadcasts start events via MQTT
   - Located in `/extras/soapbox/infra/starttimer/`

4. **Derby Display (derbydisplay.py)**:
   - Shows race information on displays
   - Updates in real-time via MQTT
   - Located in `/extras/soapbox/infra/derbydisplay/`

5. **LCD Display (derbyLCD.py)**:
   - Controls small LCD displays for officials
   - Shows lane status and race information
   - Located in `/extras/soapbox/infra/server/lcdscreen/`

6. **HLS Feed Service (hlsfeed)**:
   - Handles video streaming for race viewing
   - Uses RTSP and HLS for streaming
   - Integrates with DerbyNet's replay system
   - Located in `/extras/soapbox/hlsfeed/`

### Communication Flow

1. Race initialization starts in derbyRace.py
2. Start signal is detected by ESP32 and sent via MQTT
3. Finish timers detect lane completions and send data via MQTT
4. derbyRace.py aggregates results and sends to DerbyNet API
5. Display components update with current race status
6. All components send telemetry for monitoring

## DerbyNet Integration

The system integrates with DerbyNet, providing:

### Race Management
- Multi-device architecture with a central server
- Triple elimination format with preliminary, semi-final, and final rounds
- Real-time race management, timing, and results tracking
- Comprehensive racer registration and check-in

### Timer Integration 
- Communicates with timing hardware via HTTP/AJAX
- States: CONNECTED, STAGING, RUNNING, UNHEALTHY, NOT_CONNECTED
- 60-second heartbeat required to maintain connection

### Kiosk System
- Various display types (now-racing, standings, ondeck, results-by-racer)
- HTTP/AJAX polling with optional WebSocket support
- Intelligent display assignment for different race functions

### HLS Replay System
- HLS streaming integration for race viewing
- Configurable replay options (length, speed, repetitions)
- Video storage and race replay functionality
- Shows replays on kiosk displays

## MQTT Topic Structure

All MQTT topics use the prefix `derbynet/` followed by a category and specific identifiers:

### Core Categories

- `derbynet/race/`: Race-level events and state
- `derbynet/device/`: Device-level telemetry, status, and control
- `derbynet/lane/`: Lane-specific information and control

### Key Topics

- `derbynet/race/state`: Current race state (STOPPED, STAGING, RACING)
- `derbynet/device/{id}/status`: Device online/offline status
- `derbynet/device/{id}/telemetry`: Device health metrics
- `derbynet/device/{id}/state`: Device operational state
- `derbynet/lane/{lane}/led`: Controls LED indicators for each lane
- `derbynet/lane/{lane}/pinny`: Racer number for display on lanes

## Hardware Components

### Finish Timer Hardware
- Raspberry Pi-based controller
- Physical toggle switch for finish line detection
- RGB LED for status indication
- 4-digit 7-segment display
- DIP switches for lane configuration
- Battery monitoring circuitry

### Start Timer Hardware
- ESP32 microcontroller
- Start detection switch connected to GPIO 33
- DHT22 temperature and humidity sensor
- LED indicator for status

### Display Hardware
- Raspberry Pi (3B+ or newer)
- Display monitor with HDMI input
- Network connectivity (wired preferred)
- Chrome browser in kiosk mode

## Racing Format

The system implements a triple elimination format optimized for soapbox derby:

1. **Preliminary Round**
   - Each racer completes 3 runs (one in each lane)
   - Times from all 3 runs are averaged
   - Top 21 racers with best average times advance

2. **Semi-Final Round**
   - 21 qualified racers compete
   - Best time determines advancement
   - Top 3 racers advance to finals

3. **Final Round**
   - 3 qualified racers compete
   - Best time determines final standings (1st, 2nd, 3rd place)

## HLS Video Replay System

DerbyNet's replay functionality allows capturing video of races and playing them back immediately after a race completes. The system supports HLS (HTTP Live Streaming) as a video source.

### Replay Configuration
- Replay length: 4000ms (default)
- Replay count: 2 repetitions (default)
- Replay speed: 50% - slow motion (default)
- HLS stream URL: http://derbynetpi:8037/hls/stream.m3u8

### Trigger Methods
- Automatically on race completion
- Manually from coordinator interface
- Test replay mode for setup

### Video Storage
- Videos saved as MKV files when enabled
- Named by race details (class, round, heat)
- Example: ClassA_Round1_Heat01.mkv

## Network Requirements

The system expects a local network with:
- Primary server with IP `192.168.100.10`
- MQTT broker running on primary server
- All devices on same network (192.168.100.x)
- Finish timers identified by DIP switch settings

## Development Commands

### Build Commands

```bash
# Build the main DerbyNet distribution (uses Apache Ant)
ant dist

# Clean build artifacts
ant clean

# Build timer Java application
cd timer && ant dist

# Build timer Electron application
cd timer/derbynet-timer && npm run dist

# Package timer for distribution
cd timer/derbynet-timer && npm run pack
```

### License Management

```bash
# Update license headers in all source files
./update_licenses.sh
```

### JavaScript/PHP Code Quality

```bash
# Check JavaScript syntax (requires: npm install esprima-next)
./testing/js-syntax-check.sh

# Check specific JavaScript file
./testing/js-syntax-check.sh path/to/file.js
```

### DerbyNet Web Testing

```bash
# Setup basic test environment with photos
./testing/setup-basic.sh

# Setup test environment without photos
./testing/setup-basic-no-photos.sh

# Reset database for testing
./testing/reset-database.sh

# Run comprehensive web testing suite
./testing/suite-local-mac.sh

# Test specific functionality
./testing/test-basic-racing.sh
./testing/test-photo-upload.sh
./testing/test-awards.sh
./testing/test-balloting.sh

# Demo mode with sample data
./testing/demo.sh
```

### Service Management

```bash
# Start services
sudo systemctl start derbyrace
sudo systemctl start derbyTime
sudo systemctl start finishtimer
sudo systemctl start derbydisplay
sudo systemctl start hlsfeed

# View service logs
sudo journalctl -u derbyrace
sudo journalctl -u finishtimer
sudo journalctl -u derbydisplay
sudo journalctl -u hlsfeed
```

### Soapbox Derby System Testing

```bash
# Run all soapbox derby system tests
cd extras/soapbox/tests && python3 system_test.py

# Test specific component
cd extras/soapbox/tests && python3 system_test.py --test timers

# Verbose output
cd extras/soapbox/tests && python3 system_test.py --verbose

# Network resilience testing
cd extras/soapbox/tests && python3 network_resilience_test.py
cd extras/soapbox/tests && python3 network_resilience_test.py --scenario broker_restart --verbose
```

## Versioning and Telemetry

The system uses semantic versioning (MAJOR.MINOR.PATCH). All components include:

1. A `VERSION` constant at the top of the file
2. Logging of version on startup
3. Version in telemetry data

Telemetry data includes standardized fields:
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

## Development Guidelines

### Logging

The system uses a standardized logging library (derbylogger.py):
- Structured JSON logging
- Correlation IDs for cross-component tracking
- Centralized log aggregation

### Network Communication

All components follow these guidelines:
- Use service discovery via mDNS when possible
- Implement reconnection strategies
- Handle offline operation gracefully
- Use proper MQTT QoS levels

## Current Development Status

The system is currently at version 0.5.0 with the following completed features:

- HLS Feed Service Optimization
- Network Stability Improvements (service discovery, resilience)
- Unified Logging System
- Timer Protocol Enhancements
- HLS Replay Integration
- 2025-05-19: Fixed HLS stream URL handling in video-device-picker.js to prevent JavaScript errors

Current priorities include:
1. Create log search and analysis tools
2. Implement kiosk compatibility with DerbyNet
3. Consolidate redundant kiosk implementations
4. Create setup and deployment guides

## File Structure

- `/website/`: Core DerbyNet PHP web application
- `/extras/soapbox/infra/server/`: Central race server files
- `/extras/soapbox/infra/finishtimer/`: Finish line detection
- `/extras/soapbox/infra/starttimer/`: Start signal detection
- `/extras/soapbox/infra/derbydisplay/`: Display management
- `/extras/soapbox/hlsfeed/`: Video streaming service
- `/extras/soapbox/doc/`: Technical documentation
- `/extras/soapbox/tests/`: System test scripts

## Troubleshooting

### HLS Feed Issues
If the HLS replay functionality isn't working:
1. Verify HLS stream URL is correctly set
2. Check that video directory is properly configured
3. Test stream accessibility with VLC or browser
4. Examine logs for connection/encoding issues

### Timer Issues
If timers aren't reporting properly:
1. Check physical connections to switches
2. Verify LED indicators for status
3. Inspect MQTT connection status
4. Review DIP switch settings for lane configuration

### Display Issues
If displays aren't showing race information:
1. Verify browser is running in kiosk mode
2. Check network connectivity to MQTT broker
3. Inspect browser console for errors
4. Verify display assignment in coordinator

### Race Server Issues
If race coordination has problems:
1. Check connection to DerbyNet API
2. Verify MQTT broker is running
3. Inspect logs for timer communication issues
4. Review race state transitions
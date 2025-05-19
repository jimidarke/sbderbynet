# Soapbox Derby Race Management System

A comprehensive race management and timing system for soapbox derby events. This system provides accurate timing, display, and management functionality for races through a collection of networked components.

## System Components

### Race Server
Central coordination server that manages race state, communicates with DerbyNet race management software, and coordinates with timers and displays.

**Key Features:**
- Race state management (STOPPED, STAGING, RACING)
- Communication with DerbyNet API
- Timing coordination and results calculations
- Lane management

### Finish Timers
Hardware-based finish line detection using toggle switches with Raspberry Pi controllers.

**Key Features:**
- Lane-specific finish detection
- LED status indicators
- Numeric display
- Network resilience with message queuing
- DIP switch configuration for lane identification

### Start Timer
ESP32-based device that detects race start events and broadcasts them via MQTT.

**Key Features:**
- Start signal detection
- Telemetry monitoring
- OTA updates
- Configurable via WiFi

### Derby Display
Display screens showing race status and results.

**Key Features:**
- Full-screen kiosk mode operation
- Automatic startup and configuration
- Status monitoring
- Network resilience

### HLS Feed
Video streaming service for race viewing and replay.

**Key Features:**
- RTSP to HLS conversion via FFMPEG
- Nginx-based HLS delivery
- Responsive web player
- Automatic segment cleanup
- Integration with DerbyNet replay system

## DerbyNet Integration

The system integrates with [DerbyNet](doc/DERBYNET_REFERENCE.md), a PHP-based web application for derby race management that provides:

### Race Management
- Multi-device architecture with a central server
- Triple elimination format with precise advancement logic
- Comprehensive racer registration and check-in

### Timer Integration 
- Communicates with our timing hardware via HTTP/AJAX
- States: CONNECTED, STAGING, RUNNING, UNHEALTHY, NOT_CONNECTED
- 60-second heartbeat required to maintain connection

### Kiosk System
- Various display types (now-racing, standings, ondeck, results-by-racer)
- HTTP/AJAX polling or WebSocket support
- Intelligent display assignment for different race functions

### HLS Replay System
- [HLS streaming integration](doc/HLS_REPLAY_DOCUMENTATION.md) for race viewing
- Configurable replay options (length, speed, repetitions)
- Video storage and management
- Automatic race replay functionality

## Network Architecture

The system uses MQTT for reliable, real-time communication between components. A central MQTT broker (typically at 192.168.100.10) provides the message bus over which all components communicate.

**Key MQTT Topics:**
- `derbynet/device/{id}/status` - Device status information
- `derbynet/device/{id}/telemetry` - Device telemetry data
- `derbynet/race/state` - Current race state
- `derbynet/lane/{lane}/led` - Lane LED control
- `derbynet/lane/{lane}/pinny` - Lane pinny display

## Installation and Deployment

The system uses Raspberry Pi devices for most components, with SD card images for easy deployment.

### Server Deployment
1. Install the race server component on a central Raspberry Pi 
2. Configure network settings for the 192.168.100.x network
3. Start the derbyrace service

### Finish Timer Deployment
1. Create a Raspberry Pi SD card image using the deployment script
2. Deploy the image to SD cards with the deployImage.sh script
3. Configure lane number via DIP switches on the PCB
4. Connect physical toggle switches to the GPIO pins

### Display Deployment
1. Deploy a Raspberry Pi image with the display component
2. Configure automatic startup in kiosk mode
3. Connect to a display via HDMI

## System Services

Components run as system services for automatic startup and management:

- **derbyrace.service** - Main race management service
- **derbyTime.service** - Time synchronization service
- **finishtimer.service** - Finish timer lane detection
- **derbydisplay.service** - Display management
- **hlsfeed.service** - Video streaming

## Development

### Requirements
- Python 3.7+
- paho-mqtt library
- requests library
- psutil library
- TM1637 library (for finish timer displays)

### Testing
The `tests/system_test.py` script provides comprehensive testing of all system components.

```bash
# Run all tests
python3 tests/system_test.py

# Test specific component
python3 tests/system_test.py --test timers

# Verbose output
python3 tests/system_test.py --verbose
```

## Hardware Requirements

### Finish Timer
- Raspberry Pi (3B+ or later)
- Custom PCB v1 with:
  - Toggle switches for finish detection
  - RGB LEDs for status indication
  - DIP switches for configuration
  - 7-segment display (TM1637)

### Start Timer
- ESP32 microcontroller
- Start gate switch

### Display
- Raspberry Pi (3B+ or later)
- HDMI display

## Troubleshooting

System logs are available via standard systemd journal:

```bash
# View race server logs
sudo journalctl -u derbyrace

# View finish timer logs
sudo journalctl -u finishtimer

# View display logs
sudo journalctl -u derbydisplay

# View HLS feed logs
sudo journalctl -u hlsfeed
```

For HLS stream troubleshooting, refer to the [HLS Replay Documentation](doc/HLS_REPLAY_DOCUMENTATION.md#comprehensive-troubleshooting) which provides detailed steps for diagnosing and resolving stream issues.

## License

This project is proprietary and confidential.
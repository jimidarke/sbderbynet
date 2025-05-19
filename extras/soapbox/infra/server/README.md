# Derby Race Server Component

This is the central server component of the Soapbox Derby race management system. It coordinates race timing, communicates with the DerbyNet software, and serves as the hub for all race operations.

## Overview

The Derby Race Server:
- Manages the entire race lifecycle (staging, start, timing, finish)
- Communicates with DerbyNet API for race data and results
- Coordinates with finish timers and start timers via MQTT
- Controls lane LEDs and lane displays
- Reports device telemetry and status

## Components

- **derbyRace.py**: Main server application that orchestrates race operations
- **derbyApi.py**: API client for communicating with DerbyNet software
- **derbyTime.py**: Handles time synchronization for accurate race timing
- **derbyLCD.py**: Controls optional LCD displays for race officials

## Architecture

The system uses a central MQTT broker for communication between components:

1. **Race Management**:
   - Monitors race state from DerbyNet API
   - Controls race staging, start, timing, and finish
   - Handles abnormal situations like timeouts

2. **Device Communication**:
   - Receives finish signals from lane timers
   - Receives start signals from start timer
   - Monitors device health through heartbeats and telemetry
   - Controls lane indicators (LEDs)

3. **DerbyNet Integration**:
   - Authenticates with DerbyNet software
   - Reports race results back to DerbyNet
   - Pulls race configuration and heat data

## MQTT Topics

The server publishes and subscribes to these key topics:

- `derbynet/race/state`: Current race state (STOPPED, STAGING, RACING)
- `derbynet/race/event`: Race events like start signals
- `derbynet/device/+/state`: Device state changes
- `derbynet/device/+/telemetry`: Device telemetry data
- `derbynet/lane/{lane}/led`: LED state for each lane
- `derbynet/lane/{lane}/pinny`: Racer number display for each lane

## Installation

1. Install required dependencies:
   ```bash
   pip install paho-mqtt requests psutil
   ```

2. Set up the service:
   ```bash
   sudo cp derbyrace.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable derbyrace
   ```

3. Configure DerbyNet connection in config files

## Starting and Stopping

```bash
# Start the service
sudo systemctl start derbyrace

# Check status
sudo systemctl status derbyrace

# Stop the service
sudo systemctl stop derbyrace

# View logs
sudo journalctl -u derbyrace -f
```

## Configuration

- Default DerbyNet server IP: 192.168.100.10
- Default MQTT broker: localhost
- Default lane count: 3

## API Communication

The server uses DerbyNet's API for:
- Authentication with Timer role
- Sending race start events
- Sending lane finish times
- Receiving current heat information
- Reporting device status and telemetry

## Troubleshooting

### Common Issues

1. **Connection to DerbyNet fails**
   - Verify network connectivity
   - Check DerbyNet server is running
   - Verify correct credentials for Timer role

2. **Timers not reporting**
   - Check MQTT broker is running and accessible
   - Verify timer devices are powered and connected
   - Check for timer heartbeats in logs

3. **Race timing issues**
   - Verify time synchronization is working properly
   - Check for network delays in MQTT messages
   - Review logs for timing anomalies
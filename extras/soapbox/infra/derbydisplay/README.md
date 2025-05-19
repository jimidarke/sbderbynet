# Derby Display Component

This component manages and controls display screens for the Soapbox Derby race system, showing race information and status to racers and audience.

## Overview

The Derby Display component:
- Connects to the central race management system via MQTT
- Displays race information, results, and status
- Reports telemetry data back to the central server
- Runs in kiosk mode on Raspberry Pi devices

## Components

- **derbydisplay.py**: Main service that handles MQTT connectivity and telemetry reporting
- **derbydisplay.service**: Systemd service definition
- **kiosk.sh**: Script to launch the browser in kiosk mode
- **status.html**: Local status page for display when offline
- **loading.png/error.png**: Images for various display states
- **setup.sh**: Installation script for new display devices

## Configuration

The Derby Display uses the following configuration:
- MQTT connection to broker at 192.168.100.10
- Hardware ID read from `/boot/firmware/derbyid.txt` or generated from MAC address
- Telemetry reported every 5 seconds

## Installation

1. Run the setup script:
   ```bash
   sudo ./setup.sh
   ```

2. This will:
   - Install required dependencies
   - Configure the system for kiosk mode operation
   - Set up the service to start on boot
   - Configure hardware identification

## Starting and Stopping

```bash
# Start the service
sudo systemctl start derbydisplay

# Check status
sudo systemctl status derbydisplay

# Stop the service
sudo systemctl stop derbydisplay
```

## Troubleshooting

### Common Issues

1. **Screen shows loading but never connects**
   - Check network connectivity
   - Verify MQTT broker is running
   - Review logs with `journalctl -u derbydisplay`

2. **Screen shows error image**
   - Check system errors
   - Verify hardware ID configuration
   - Ensure display is properly configured in race manager

3. **Display freezes or goes blank**
   - Restart the service
   - Check for hardware issues (overheating, power)
   - Verify browser process is running

## Development

To modify the display content:
1. Edit the code to update how content is rendered
2. Update status.html for offline mode display
3. Restart the service to apply changes

## MQTT Topics

The component uses the following MQTT topics:

### Published
- `derbynet/device/{hwid}/state`: Current display state
- `derbynet/device/{hwid}/telemetry`: System telemetry data
- `derbynet/device/{hwid}/status`: Online/offline status

### Subscribed
- `derbynet/device/{hwid}/update`: Firmware update commands

## Hardware Requirements

- Raspberry Pi (3B+ or newer recommended)
- Display monitor with HDMI input
- Stable power supply
- Network connectivity (wired preferred)
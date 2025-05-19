# DerbyNet

![icon](https://raw.githubusercontent.com/jeffpiazza/derbynet/master/website/img/derbynet-300.png)

DerbyNet is a comprehensive race management system for derby racing events. Originally developed for Pinewood Derby races, it has been extended to support Soapbox Derby events as well.

Please visit us at [https://derbynet.org](https://derbynet.org).

## Features

### Core DerbyNet Features
- Web-based race management
- Multi-device architecture with central server and connected client displays
- Timer integration for automatic time capture
- Comprehensive racer registration and check-in
- Photo capture and management
- Results tracking and standings
- Award management and presentation
- Kiosk display system

### Soapbox Derby Extension
- **Current Version: 0.5.0**
- Custom hardware integration for soapbox racing
- Triple elimination racing format
- Start/finish line detection
- HLS video streaming and replay
- MQTT-based communication for real-time updates
- Enhanced display system for outdoor races
- Network resilience for outdoor environments

## Documentation

### Core Documentation
The `docs/` directory contains documentation for the main DerbyNet system in OpenDocument format.

### Soapbox Derby Documentation
The following documents provide details on the Soapbox Derby extension:

- [Soapbox Derby Overview](/extras/soapbox/README.md) - General overview of the Soapbox Derby system
- [DerbyNet Reference for Soapbox](/extras/soapbox/doc/DERBYNET_REFERENCE.md) - Technical reference for DerbyNet integration
- [MQTT API Documentation](/extras/soapbox/doc/MQTT_API.md) - Details of the MQTT communication protocol
- [HLS Replay Documentation](/extras/soapbox/doc/HLS_REPLAY_DOCUMENTATION.md) - Video streaming and replay implementation
- [Soapbox Test Guide](/extras/soapbox/doc/SoapboxDerby_Test_Guide.md) - Comprehensive testing guide
- [Version Information](/extras/soapbox/VERSION.md) - Version history and component versioning
- [Feature Enhancements](/extras/soapbox/FEATURE_ENHANCEMENTS.md) - Planned feature enhancements
- [Refactoring Plan](/extras/soapbox/REFACTORING_PLAN.md) - Current development and refactoring status

### Component Documentation
- [Race Server](/extras/soapbox/infra/server/README.md) - Core race management server
- [Finish Timer](/extras/soapbox/infra/finishtimer/README.md) - Finish line detection system
- [Start Timer](/extras/soapbox/infra/starttimer/README.md) - Start gate detection system
- [Derby Display](/extras/soapbox/infra/derbydisplay/README.md) - Display system
- [HLS Feed](/extras/soapbox/hlsfeed/README.md) - Video streaming service

## Architecture

The Soapbox Derby system extends DerbyNet with the following components:

1. **Race Server (derbyRace.py)**: Central orchestration service that manages race state, communicates with DerbyNet API, and coordinates start and finish timers via MQTT.
2. **Finish Timer (derbynetPCBv1.py)**: Monitors lane finish events using GPIO, sends lane finish data to server via MQTT.
3. **Start Timer (ESP32)**: Detects race start signals and broadcasts start events via MQTT.
4. **Derby Display (derbydisplay.py)**: Shows race information on displays, updates in real-time via MQTT.
5. **HLS Feed Service**: Handles video streaming for race viewing, uses RTSP and HLS for streaming.

## System Requirements

### Core DerbyNet
- PHP 7.0+ web server (Apache recommended)
- SQLite or Microsoft Access database
- Modern web browser for administration

### Soapbox Derby Components
- Raspberry Pi devices (3B+ or newer) for various components
- ESP32 for start timer
- MQTT broker (Mosquitto recommended)
- Customized hardware for finish line detection
- Network infrastructure (WiFi/Ethernet)
- Displays with HDMI input

## Installation

### Core DerbyNet Installation
See the installation guides in the `docs/` directory for platform-specific instructions:
- Debian/Ubuntu Linux
- Windows
- macOS
- Docker

### Developing Locally

To quickly get started on local development, the existing Docker image can be
used to provide the web server and PHP engine, even if you don't have these
installed natively on your machine.

1. Install [Apache Ant](https://ant.apache.org/). 
   1. You can [install WSL](https://learn.microsoft.com/en-us/windows/wsl/install) and run:

      ```bash
      sudo apt-get update
      sudo apt-get install ant
      ```

2. Execute `ant generated` from the root of the cloned repository.  (This build
target includes a step to generate PDF files from their ODF source files.  This
step will be silently skipped if the LibreOffice/OpenOffice `soffice`
application is not available.)

3. If desired, do one or both of the following.  (If you do neither, you won't
be able to connect to a hardware timer.)

   1. Execute `ant timer-in-brower` to build the in-browser timer interface.
   2. Execute `ant timer-jar` to build the derby-timer.jar timer interface.

4. Instantiate the docker container, but use your local sources rather than
those deployed in the container.  _**PATH_TO_YOUR_DATA**_ is a local directory
where you'd like databases, photos, and other data files to be stored.
_**PATH_TO_YOUR_REPOSITORY**_ is the path to your local cloned repository.

   ```powershell
   docker run --detach -p 80:80 -p 443:443 \
     --volume [** PATH TO YOUR DATA **]\lib\:/var/lib/derbynet \
     --mount type=bind,src=[** PATH TO YOUR REPOSITORY **]\website\,target=/var/www/html,readonly \
     jeffpiazza/derbynet_server   
   ```

### Soapbox Derby Installation

Refer to the [Soapbox Derby README](/extras/soapbox/README.md) for detailed installation instructions for the Soapbox Derby components. Key installation steps include:

1. Set up Raspberry Pi devices with the appropriate SD card images
2. Configure network for 192.168.100.x subnet
3. Install required dependencies (Python, MQTT, etc.)
4. Configure and start system services:
   - derbyrace.service
   - derbyTime.service
   - finishtimer.service
   - derbydisplay.service
   - hlsfeed.service

## Testing

### Core DerbyNet Testing
The `testing/` directory contains scripts for testing various aspects of DerbyNet operation.

### Soapbox Derby Testing
The Soapbox Derby system includes comprehensive testing tools:

```bash
# Run all system tests
python3 tests/system_test.py

# Test specific component
python3 tests/system_test.py --test timers

# Test network resilience
python3 tests/network_resilience_test.py
```

For detailed testing procedures, refer to the [Soapbox Test Guide](/extras/soapbox/doc/SoapboxDerby_Test_Guide.md).

## Troubleshooting

### Core DerbyNet
Check the error logs in your web server configuration. For standard installations, logs are in `/var/log/apache2/` on Linux or in the error logs of your web host application.

### Soapbox Derby Components
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

For HLS stream troubleshooting, refer to the [HLS Replay Documentation](/extras/soapbox/doc/HLS_REPLAY_DOCUMENTATION.md#comprehensive-troubleshooting).

## License

This project is released under the MIT License. See the LICENSE file for details.
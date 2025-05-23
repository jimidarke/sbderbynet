# HLS Transcoder

A dedicated component for the DerbyNet Soapbox Derby race management system that transcodes video input (like RTSP) to HLS format for efficient streaming and replay.

## Overview

The HLS Transcoder is designed to:

1. Accept video input from RTSP sources (like cameras)
2. Transcode the video stream to HLS format using FFmpeg
3. Serve the HLS stream via nginx
4. Integrate with DerbyNet's replay system
5. Provide status monitoring and telemetry via MQTT
6. Display a web-based status dashboard in kiosk mode

This component is designed to run on a dedicated Raspberry Pi 4B (or more powerful hardware) and acts as a centralized video transcoding service for the entire DerbyNet system.

## Hardware Requirements

- Raspberry Pi 4B or more powerful Linux machine
- 4GB RAM or more recommended
- 32GB or larger SD card
- Ethernet connection (recommended for stable video)
- HDMI display for kiosk mode (optional)

## Installation

1. Flash Raspberry Pi OS (Lite or Desktop) to an SD card
2. Create `/boot/derbyid.txt` with a unique identifier for this device
3. Boot the Raspberry Pi and connect it to your network
4. Clone the DerbyNet Soapbox repository
5. Run the installation script:

```bash
cd /path/to/sbderbynet/extras/soapbox/hlstranscoder
sudo chmod +x setup.sh
sudo ./setup.sh
```

## Configuration

The main configuration file is located at `/etc/hlstranscoder/config.env`. You can use the provided `config.template` as a reference.

Key configuration options:

- `RTSP_SOURCE`: URL of the RTSP stream to transcode
- `HLS_OUTPUT_DIR`: Directory to save HLS segments
- `RESOLUTION`: Output resolution (e.g., "1280x720")
- `BITRATE`: Output bitrate (e.g., "2M")
- `MQTT_BROKER`: Address of the MQTT broker for telemetry and control
- `KIOSK_URL`: URL to display in kiosk mode (defaults to status page)

For sensitive configuration values (like passwords), use the `secure_config.sh` script:

```bash
sudo ./secure_config.sh set MQTT_PASSWORD mysecretpassword
```

## Usage

The HLS Transcoder runs as a systemd service and starts automatically on boot.

### Service Management

```bash
# Check the status of the service
sudo systemctl status hlstranscoder

# Start the service
sudo systemctl start hlstranscoder

# Stop the service
sudo systemctl stop hlstranscoder

# Restart the service
sudo systemctl restart hlstranscoder

# View logs
sudo journalctl -u hlstranscoder -f
```

### Stream Access

The HLS stream is available at:

```
http://<transcoder-ip>:8037/hls/stream.m3u8
```

The status dashboard is available at:

```
http://<transcoder-ip>/status.html
```

## MQTT Integration

The HLS Transcoder integrates with the DerbyNet MQTT broker for status reporting and control.

### Published Topics

- `derbynet/device/hlstranscoder/status`: Online/offline status
- `derbynet/device/hlstranscoder/telemetry`: System telemetry data
- `derbynet/device/hlstranscoder/state`: Current transcoder state
- `derbynet/device/hlstranscoder/info`: Device information with version

### Subscribed Topics

- `derbynet/device/hlstranscoder/command`: Command channel
- `derbynet/device/<derby-id>/command`: Hardware ID specific command channel
- `derbynet/device/hlstranscoder/update`: Update channel
- `derbynet/device/<derby-id>/update`: Hardware ID specific update channel
- `derbynet/race/state`: Race state updates
- `derbynet/command/replay`: Replay commands

### Commands

You can control the transcoder by publishing to the command topic:

```bash
# Restart transcoding
mosquitto_pub -h <broker> -t derbynet/device/hlstranscoder/command -m "restart"

# Stop transcoding
mosquitto_pub -h <broker> -t derbynet/device/hlstranscoder/command -m "stop"

# Update configuration
mosquitto_pub -h <broker> -t derbynet/device/hlstranscoder/command -m "set:BITRATE:3M"

# Trigger remote update
mosquitto_pub -h <broker> -t derbynet/device/hlstranscoder/update -m "update"
```

## Remote Updates

The HLS Transcoder supports remote updates via rsync. This allows you to update the component's files without physical access to the device.

### Update Server Setup

1. Set up an rsync server on your central server (typically 192.168.100.10)
2. Create a module called `derbynet` in `/etc/rsyncd.conf`:

```
[derbynet]
path = /var/derbynet
comment = DerbyNet files
read only = yes
list = yes
```

3. Create a directory structure that includes hlstranscoder files:

```
/var/derbynet/
└── hlstranscoder/
    ├── hlstranscoder.py
    ├── hlstranscoder.service
    ├── setup.sh
    ├── sync.sh
    ├── kiosk.sh
    ├── config.template
    └── nginx/
        └── hls.conf
```

### Triggering Updates

Updates can be triggered in three ways:

1. **MQTT Command**: Send an update command via MQTT:
   ```bash
   mosquitto_pub -h <broker> -t derbynet/device/hlstranscoder/update -m "update"
   ```

2. **Manual Sync**: Run the sync script directly on the device:
   ```bash
   sudo /opt/hlstranscoder/sync.sh
   ```

3. **Remote SSH**: Execute the sync command via SSH:
   ```bash
   ssh pi@<transcoder-ip> "sudo /opt/hlstranscoder/sync.sh"
   ```

The update process will:
1. Download updated files from the rsync server
2. Apply configuration changes if needed
3. Restart the services automatically
4. Report status via MQTT

You can specify a different server address in the configuration:
```
UPDATE_SERVER="192.168.100.10"  # In config.env
```

Or pass it directly to the sync script:
```bash
sudo /opt/hlstranscoder/sync.sh 192.168.100.20
```

## Integration with DerbyNet Replay

To use the HLS Transcoder with DerbyNet's replay system, configure the replay URL in the DerbyNet coordinator interface:

1. Go to "Settings" > "Replay"
2. Set the replay URL to: `http://<transcoder-ip>:8037/hls/stream.m3u8`
3. Configure replay length, speed, and repetitions as desired

## Troubleshooting

### Stream Issues

If the HLS stream isn't working:

1. Check that the RTSP source is accessible:
   ```bash
   ffprobe <RTSP_URL>
   ```

2. Verify the HLS directory is writable:
   ```bash
   ls -la /var/www/html/hls/
   ```

3. Check the transcoder logs:
   ```bash
   sudo journalctl -u hlstranscoder -f
   ```

### MQTT Issues

If MQTT integration isn't working:

1. Verify the MQTT broker is reachable:
   ```bash
   mosquitto_sub -h <broker> -t derbynet/# -v
   ```

2. Check MQTT credentials if authentication is enabled

### Display Issues

If the kiosk display isn't showing:

1. Check X server logs:
   ```bash
   cat ~/.xsession-errors
   ```

2. Verify the service is running:
   ```bash
   ps aux | grep chromium
   ```

## Performance Tuning

For better performance on Raspberry Pi:

1. Consider using hardware acceleration:
   ```
   CODEC="h264_omx"  # In config.env
   ```

2. Adjust resolution and bitrate based on your hardware capabilities:
   ```
   RESOLUTION="854x480"
   BITRATE="1M"
   ```

3. For more powerful machines, increase quality:
   ```
   RESOLUTION="1920x1080"
   BITRATE="5M"
   FFMPEG_PRESET="fast"
   ```

## Advanced Features

### Stream Archiving

To enable archiving of the video stream:

1. Set `ENABLE_ARCHIVE="true"` in `config.env`
2. Configure `ARCHIVE_DIR` and `ARCHIVE_RETENTION_DAYS`

### Multiple Streams

To transcode multiple input streams, you can run multiple instances of the transcoder:

1. Create separate configuration files for each stream
2. Start the service with the different configuration file:
   ```bash
   sudo systemctl start hlstranscoder@stream2
   ```

## Development

The HLS Transcoder follows the same development patterns as other components in the DerbyNet Soapbox system:

- Version tracking at the top of each source file
- Structured logging with DerbyLogger
- MQTT communication with standard topics
- Standard telemetry format
- Common error handling strategies

For development, you can run the transcoder manually:

```bash
cd /opt/hlstranscoder
sudo python3 hlstranscoder.py --config /path/to/config.env --debug
```
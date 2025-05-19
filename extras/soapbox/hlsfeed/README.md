# HLS Feed Service

This component provides video streaming capabilities for the Soapbox Derby race system using HLS (HTTP Live Streaming) protocol.

## Overview

The HLS Feed service:
- Captures RTSP video stream from cameras
- Converts to HLS format using FFmpeg
- Serves the video stream using Nginx
- Manages video segments and performs cleanup

## Components

- **hlsfeed.sh**: Main service script that handles RTSP to HLS conversion using FFmpeg
- **cleanup_ts.sh**: Handles automatic cleanup of old video segments
- **config.env**: Configuration file for stream settings, cleanup policies, etc.
- **nginx/hls.conf**: Nginx configuration for serving HLS streams
- **hlsfeed.service**: Systemd service definition

## Configuration

Edit the `config.env` file to modify:
- RTSP source URL and credentials
- Video quality settings
- Segment retention policy
- Log settings

## Installation

1. Place files in `/opt/hlsfeed/`
2. Copy `hlsfeed.service` to `/etc/systemd/system/`
3. Copy `nginx/hls.conf` to `/etc/nginx/`
4. Enable services:
   ```bash
   sudo systemctl enable hlsfeed.service
   sudo systemctl enable nginx-hls.service
   ```

## Starting and Stopping

```bash
# Start the service
sudo systemctl start hlsfeed

# Check status
sudo systemctl status hlsfeed

# Stop the service
sudo systemctl stop hlsfeed
```

## Monitoring

Monitor the HLS feed:
- Check logs at `/var/log/hlsfeed.log`
- Access health endpoint at `http://<server-ip>:8037/health`
- View the stream at `http://<server-ip>:8037/`

## Troubleshooting

### Common Issues

1. **Stream not available**
   - Check camera connectivity
   - Verify RTSP URL is correct
   - Check logs for FFmpeg errors

2. **High disk usage**
   - Adjust `MAX_SEGMENT_AGE_MINUTES` in config.env
   - Ensure cleanup_ts.sh is running as scheduled
   - Check available disk space with `df -h`

3. **Playback issues**
   - Verify network connectivity to server
   - Check browser console for CORS errors
   - Test stream with VLC player for comparison
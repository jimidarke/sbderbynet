# DerbyNet Multi-Camera HLS Setup Guide

**Version**: 0.5.0  
**Date**: May 30, 2025

This guide provides comprehensive instructions for setting up multi-camera HLS streaming with the DerbyNet soapbox derby system. The framework supports both RTSP (POE cameras) and USB webcams with optimized FFmpeg transcoding profiles.

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Quick Start](#quick-start)
3. [Camera Configuration](#camera-configuration)
4. [Quality Profiles](#quality-profiles)
5. [RTSP Camera Setup](#rtsp-camera-setup)
6. [USB Webcam Setup](#usb-webcam-setup)
7. [Service Management](#service-management)
8. [Troubleshooting](#troubleshooting)
9. [Performance Optimization](#performance-optimization)

## System Requirements

### Hardware Requirements
- **CPU**: Intel i5/AMD Ryzen 5 or better (hardware acceleration recommended)
- **RAM**: 8GB minimum, 16GB recommended for multiple 1080p streams
- **Storage**: 50GB+ available space for video segments and recordings
- **Network**: Gigabit Ethernet recommended for multiple cameras

### Software Requirements
- Ubuntu 20.04+ or Debian 11+
- FFmpeg 4.4+ with hardware acceleration support
- Nginx with lua module
- Python 3.8+
- Required Python packages: `psutil`, `paho-mqtt`

### Camera Requirements
- **RTSP Cameras**: POE cameras supporting H.264 encoding
- **USB Cameras**: UVC-compatible webcams (USB 3.0 recommended)

## Quick Start

### 1. Download and Setup
```bash
# Navigate to the HLS feed directory
cd /path/to/derbynet/extras/soapbox/hlsfeed

# Run the setup wizard
sudo chmod +x camera-manager.sh
./camera-manager.sh setup
```

### 2. Configure Cameras
```bash
# Edit the configuration file
sudo nano /opt/hlsfeed/multicam-config.env

# Discover available cameras
./camera-manager.sh discover

# Test camera configuration
./camera-manager.sh validate
```

### 3. Start Service
```bash
# Start the multi-camera service
sudo systemctl start multicam-service

# Check status
./camera-manager.sh status
```

## Camera Configuration

### Configuration File Structure

The main configuration file is located at `/opt/hlsfeed/multicam-config.env`. Each camera is defined with the following pattern:

```bash
# Camera enabled flag
CAMERA_{ID}_ENABLED=true

# Camera type (RTSP or USB)
CAMERA_{ID}_TYPE="RTSP"

# Camera source (URL for RTSP, device path for USB)
CAMERA_{ID}_SOURCE="rtsp://user:pass@192.168.100.20:554/21"

# Display name
CAMERA_{ID}_NAME="Finish Line Camera"

# Position identifier
CAMERA_{ID}_POSITION="finish"

# Primary camera flag (used for legacy compatibility)
CAMERA_{ID}_PRIMARY=true
```

### Example Multi-Camera Configuration

```bash
# Finish line camera (mandatory)
CAMERA_FINISH_ENABLED=true
CAMERA_FINISH_TYPE="RTSP"
CAMERA_FINISH_SOURCE="rtsp://admin:password@192.168.100.20:554/21"
CAMERA_FINISH_NAME="Finish Line"
CAMERA_FINISH_POSITION="finish"
CAMERA_FINISH_PRIMARY=true

# Start line camera
CAMERA_START_ENABLED=true
CAMERA_START_TYPE="RTSP"
CAMERA_START_SOURCE="rtsp://admin:password@192.168.100.21:554/21"
CAMERA_START_NAME="Start Line"
CAMERA_START_POSITION="start"
CAMERA_START_PRIMARY=false

# Overhead track view
CAMERA_OVERHEAD_ENABLED=true
CAMERA_OVERHEAD_TYPE="USB"
CAMERA_OVERHEAD_SOURCE="/dev/video0"
CAMERA_OVERHEAD_NAME="Track Overview"
CAMERA_OVERHEAD_POSITION="overhead"
CAMERA_OVERHEAD_PRIMARY=false
```

## Quality Profiles

The system supports three quality profiles with automatic fallback:

### HIGH_QUALITY (1080p)
- **Resolution**: 1920x1080
- **Bitrate**: 4000k
- **Preset**: medium
- **Use Case**: High-end systems with sufficient CPU/bandwidth

### MEDIUM_QUALITY (720p)
- **Resolution**: 1280x720
- **Bitrate**: 2500k
- **Preset**: fast
- **Use Case**: Standard systems with moderate resources

### LOW_QUALITY (480p)
- **Resolution**: 854x480
- **Bitrate**: 1200k
- **Preset**: veryfast
- **Use Case**: Resource-constrained systems

### Changing Quality Profile

```bash
# Set quality profile
./camera-manager.sh quality HIGH_QUALITY

# Test system performance with different profiles
./camera-manager.sh benchmark
```

## RTSP Camera Setup

### Supported Camera Types
- Axis cameras
- Hikvision cameras
- Dahua cameras
- Generic POE cameras with RTSP support

### Finding Camera RTSP URLs

Most POE cameras use standard RTSP URL formats:

```bash
# Generic format
rtsp://username:password@camera_ip:port/path

# Common examples
rtsp://admin:password@192.168.100.20:554/1          # Stream 1
rtsp://admin:password@192.168.100.20:554/h264       # H.264 stream
rtsp://admin:password@192.168.100.20:554/live       # Live stream
```

### Camera Discovery

```bash
# Discover RTSP cameras on network
./camera-manager.sh discover

# Test specific camera
ffprobe -rtsp_transport tcp rtsp://admin:password@192.168.100.20:554/1
```

### RTSP Configuration Best Practices

1. **Use TCP Transport**: More reliable than UDP
   ```bash
   RTSP_TRANSPORT="tcp"
   ```

2. **Set Appropriate Timeouts**: Handle network issues
   ```bash
   RTSP_TIMEOUT="30"
   RTSP_RECONNECT_DELAY="5"
   ```

3. **Camera Settings**: Configure cameras for optimal streaming
   - Set frame rate to 30fps or lower
   - Use H.264 encoding
   - Set GOP size to 2x frame rate
   - Disable audio if not needed

## USB Webcam Setup

### Compatible Webcams
- Logitech C920/C930e
- Microsoft LifeCam
- Any UVC-compatible USB camera

### USB Device Discovery

```bash
# List video devices
ls /dev/video*

# Get device information
v4l2-ctl --device=/dev/video0 --info

# List supported formats
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

### USB Camera Configuration

```bash
# Basic USB camera setup
CAMERA_SIDE_ENABLED=true
CAMERA_SIDE_TYPE="USB"
CAMERA_SIDE_SOURCE="/dev/video0"
CAMERA_SIDE_NAME="Side View Camera"

# USB-specific settings
USB_CAMERA_FORMAT="v4l2"
USB_CAMERA_FRAMERATE="30"
USB_CAMERA_INPUT_FORMAT="mjpeg"  # or yuyv422
```

### USB Camera Optimization

1. **Use MJPEG Format**: Reduces CPU load
   ```bash
   USB_CAMERA_INPUT_FORMAT="mjpeg"
   ```

2. **Set Appropriate Resolution**: Match quality profile
   ```bash
   v4l2-ctl --device=/dev/video0 --set-fmt-video=width=1920,height=1080,pixelformat=MJPG
   ```

3. **USB 3.0 Ports**: Use USB 3.0 for high-resolution cameras

## Service Management

### Systemd Service

The multi-camera service runs as a systemd service:

```bash
# Service management
sudo systemctl start multicam-service
sudo systemctl stop multicam-service
sudo systemctl restart multicam-service
sudo systemctl enable multicam-service

# Check service status
sudo systemctl status multicam-service

# View logs
journalctl -u multicam-service -f
```

### Camera Manager Tool

Use the camera manager for operational tasks:

```bash
# Check overall status
./camera-manager.sh status

# Test specific camera
./camera-manager.sh test finish

# Change quality profile
./camera-manager.sh quality MEDIUM_QUALITY

# View logs for specific camera
./camera-manager.sh logs finish
```

### MQTT Monitoring

The service publishes status to MQTT:

```bash
# Topic: derbynet/camera/status
# Payload includes:
{
  "timestamp": "2025-05-30T10:30:00",
  "version": "0.5.0",
  "cameras": {
    "finish": {
      "name": "Finish Line",
      "enabled": true,
      "healthy": true,
      "stream_url": "http://derbynetpi:8037/hls/camera_finish/stream.m3u8"
    }
  },
  "system": {
    "cpu_percent": 45.2,
    "memory_percent": 62.1
  }
}
```

## Troubleshooting

### Common Issues

#### 1. Camera Not Streaming
```bash
# Check camera configuration
./camera-manager.sh validate

# Test camera directly
./camera-manager.sh test camera_id

# Check FFmpeg logs
journalctl -u multicam-service | grep camera_id
```

#### 2. High CPU Usage
```bash
# Check system resources
./camera-manager.sh status

# Run benchmark to find optimal profile
./camera-manager.sh benchmark

# Lower quality profile
./camera-manager.sh quality MEDIUM_QUALITY
```

#### 3. Network Issues with RTSP
```bash
# Test RTSP connectivity
ffprobe -rtsp_transport tcp -timeout 10 rtsp://camera_url

# Check network latency
ping camera_ip

# Verify camera settings in web interface
```

#### 4. USB Camera Not Detected
```bash
# Check USB devices
lsusb

# Check video devices
ls -la /dev/video*

# Test with FFmpeg
ffmpeg -f v4l2 -list_formats all -i /dev/video0

# Check permissions
sudo usermod -a -G video hlsfeed
```

### Log Analysis

```bash
# Service logs
journalctl -u multicam-service -f

# Camera-specific logs
./camera-manager.sh logs camera_id

# System logs
tail -f /var/log/hlsfeed/multicam-service.log
```

### Performance Monitoring

```bash
# Real-time monitoring
htop

# Check GPU usage (if hardware acceleration enabled)
nvidia-smi  # For NVIDIA
vainfo      # For Intel/AMD

# Network usage
iftop
```

## Performance Optimization

### Hardware Acceleration

Enable hardware acceleration for better performance:

```bash
# Intel Quick Sync (QSV)
ENABLE_HARDWARE_ACCEL=true
HARDWARE_ACCEL_TYPE="qsv"

# NVIDIA NVENC
ENABLE_HARDWARE_ACCEL=true
HARDWARE_ACCEL_TYPE="nvenc"

# Intel/AMD VAAPI
ENABLE_HARDWARE_ACCEL=true
HARDWARE_ACCEL_TYPE="vaapi"
```

### System Tuning

1. **CPU Governor**: Set to performance mode
   ```bash
   sudo cpupower frequency-set -g performance
   ```

2. **Network Buffers**: Increase for high bitrate streams
   ```bash
   echo 'net.core.rmem_max = 134217728' >> /etc/sysctl.conf
   echo 'net.core.wmem_max = 134217728' >> /etc/sysctl.conf
   ```

3. **File Descriptors**: Increase limits
   ```bash
   echo 'hlsfeed soft nofile 4096' >> /etc/security/limits.conf
   echo 'hlsfeed hard nofile 8192' >> /etc/security/limits.conf
   ```

### Quality vs Performance Guidelines

| Camera Count | Recommended Profile | CPU Usage | Bandwidth |
|--------------|-------------------|-----------|-----------|
| 1-2 cameras  | HIGH_QUALITY      | 40-60%    | 8-10 Mbps |
| 3-4 cameras  | MEDIUM_QUALITY    | 50-70%    | 10-15 Mbps |
| 5+ cameras   | LOW_QUALITY       | 60-80%    | 6-10 Mbps |

### Automatic Quality Fallback

The system automatically falls back to lower quality profiles if:
- Camera restart count exceeds 3 attempts
- System CPU usage exceeds 80%
- Network timeouts occur frequently

Monitor fallback events in the logs:
```bash
journalctl -u multicam-service | grep "falling back"
```

## Integration with DerbyNet

### Stream URLs
Each camera is accessible via unique URLs:
```
Primary camera: http://derbynetpi:8037/hls/stream.m3u8 (legacy)
Finish camera:  http://derbynetpi:8037/hls/camera_finish/stream.m3u8
Start camera:   http://derbynetpi:8037/hls/camera_start/stream.m3u8
```

### DerbyNet Configuration
Update DerbyNet's HLS settings to use the primary camera URL or implement camera selection in the coordinator interface.

### Replay Integration
The replay system works with all configured cameras. Recordings are saved with camera-specific naming:
```
/opt/hlsfeed/videos/finish_ClassA_Round1_Heat01.mkv
/opt/hlsfeed/videos/start_ClassA_Round1_Heat01.mkv
```

For additional support or advanced configurations, refer to the main DerbyNet documentation or submit issues to the project repository.
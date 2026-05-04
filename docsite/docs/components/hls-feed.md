# HLS Feed

Captures RTSP streams (POE cameras, USB webcams), transcodes via FFmpeg, serves HLS segments through Nginx for browser playback. Multi-camera with quality profiles and automatic fallback.

Lives at `extras/soapbox/hlsfeed/`. Bash + Python + FFmpeg + Nginx. Runs as `multicam-service` (preferred) or legacy `hlsfeed.service`.

**Current version**: 0.8.0.

---

## System requirements

- **CPU**: Intel i5 / AMD Ryzen 5 or better; hardware acceleration recommended.
- **RAM**: 8 GB minimum, 16 GB for multiple 1080p streams.
- **Storage**: 50 GB+ for segments and recordings.
- **Network**: gigabit Ethernet for multiple cameras.
- **OS**: Ubuntu 20.04+ or Debian 11+.
- **FFmpeg 4.4+** with hwaccel; Nginx with lua module; Python 3.8+ with `psutil`, `paho-mqtt`.

Cameras: RTSP-capable POE (H.264), and/or UVC USB webcams.

---

## Quick start

```bash
cd /path/to/derbynet/extras/soapbox/hlsfeed
sudo chmod +x camera-manager.sh
./camera-manager.sh setup            # wizard
sudo $EDITOR /opt/hlsfeed/multicam-config.env
./camera-manager.sh discover
./camera-manager.sh validate
sudo systemctl start multicam-service
./camera-manager.sh status
```

---

## Configuration

`/opt/hlsfeed/multicam-config.env`. Each camera follows a pattern:

```bash
CAMERA_{ID}_ENABLED=true
CAMERA_{ID}_TYPE="RTSP"            # or USB
CAMERA_{ID}_SOURCE="rtsp://user:pass@192.168.100.20:554/21"
CAMERA_{ID}_NAME="Finish Line Camera"
CAMERA_{ID}_POSITION="finish"
CAMERA_{ID}_PRIMARY=true            # legacy compatibility
```

Example multi-cam:

```bash
CAMERA_FINISH_ENABLED=true
CAMERA_FINISH_TYPE="RTSP"
CAMERA_FINISH_SOURCE="rtsp://admin:password@192.168.100.20:554/21"
CAMERA_FINISH_NAME="Finish Line"
CAMERA_FINISH_POSITION="finish"
CAMERA_FINISH_PRIMARY=true

CAMERA_START_ENABLED=true
CAMERA_START_TYPE="RTSP"
CAMERA_START_SOURCE="rtsp://admin:password@192.168.100.21:554/21"
CAMERA_START_NAME="Start Line"
CAMERA_START_POSITION="start"

CAMERA_OVERHEAD_ENABLED=true
CAMERA_OVERHEAD_TYPE="USB"
CAMERA_OVERHEAD_SOURCE="/dev/video0"
CAMERA_OVERHEAD_NAME="Track Overview"
CAMERA_OVERHEAD_POSITION="overhead"
```

---

## Quality profiles

Three with automatic fallback:

| Profile | Resolution | Bitrate | Preset | Use case |
|---|---|---|---|---|
| `HIGH_QUALITY` | 1920×1080 | 4000 k | medium | sufficient CPU/bandwidth |
| `MEDIUM_QUALITY` | 1280×720 | 2500 k | fast | standard systems |
| `LOW_QUALITY` | 854×480 | 1200 k | veryfast | resource-constrained |

```bash
./camera-manager.sh quality HIGH_QUALITY
./camera-manager.sh benchmark
```

Automatic fallback triggers when: camera restarts > 3, CPU > 80 %, frequent network timeouts. Watch for it: `journalctl -u multicam-service | grep "falling back"`.

---

## RTSP & USB

### RTSP

- Use TCP transport (`RTSP_TRANSPORT=tcp`) — more reliable than UDP.
- 30 fps or lower, H.264, GOP = 2 × frame rate, audio off.
- Find URL: `ffprobe -rtsp_transport tcp rtsp://admin:password@192.168.100.20:554/1`.

### USB

- MJPEG input (`USB_CAMERA_INPUT_FORMAT=mjpeg`) — much lower CPU than yuyv422.
- Match resolution to profile: `v4l2-ctl --device=/dev/video0 --set-fmt-video=width=1920,height=1080,pixelformat=MJPG`.
- USB 3.0 ports for high-resolution cameras.
- User in `video` group: `sudo usermod -a -G video hlsfeed`.

---

## Service management

```bash
sudo systemctl {start,stop,restart,status,enable} multicam-service
journalctl -u multicam-service -f

./camera-manager.sh status
./camera-manager.sh test finish
./camera-manager.sh logs finish
```

### MQTT status

```
Topic: derbynet/camera/status
{
  "timestamp": "2025-05-30T10:30:00",
  "version": "0.8.0",
  "cameras": { "finish": { "name": "Finish Line", "healthy": true,
    "stream_url": "http://derbynetpi:8037/hls/camera_finish/stream.m3u8" } },
  "system": { "cpu_percent": 45.2, "memory_percent": 62.1 }
}
```

---

## Stream URLs

```
Primary (legacy):   http://derbynetpi:8037/hls/stream.m3u8
Per-camera:         http://derbynetpi:8037/hls/camera_{position}/stream.m3u8
Health endpoint:    http://derbynetpi:8037/health
```

Replay recordings: `/opt/hlsfeed/videos/{position}_{class}_{round}_{heat}.mkv`.

---

## Performance guidelines

| Camera count | Recommended profile | CPU | Bandwidth |
|---|---|---|---|
| 1–2 | HIGH | 40–60 % | 8–10 Mbps |
| 3–4 | MEDIUM | 50–70 % | 10–15 Mbps |
| 5+ | LOW | 60–80 % | 6–10 Mbps |

Hardware acceleration: `qsv` (Intel), `nvenc` (NVIDIA), `vaapi` (Intel/AMD). Set `ENABLE_HARDWARE_ACCEL=true` and `HARDWARE_ACCEL_TYPE`.

System tuning: CPU governor → performance, increase `net.core.{r,w}mem_max`, raise file-descriptor limits.

---

## Troubleshooting

| Symptom | Check |
|---|---|
| Stream not available | camera connectivity, RTSP URL, FFmpeg logs |
| High disk usage | `MAX_SEGMENT_AGE_MINUTES` in config; `cleanup_ts.sh` running; `df -h` |
| Playback issues | network connectivity; browser console (CORS); test in VLC |
| High CPU | `./camera-manager.sh benchmark`; lower profile; enable hwaccel |
| RTSP intermittent | TCP transport; ping camera; verify camera web settings |
| USB not detected | `lsusb`, `ls /dev/video*`, `ffmpeg -f v4l2 -list_formats all -i /dev/video0`, `video` group |

---

## Disk hygiene

HLS segments accumulate fast. `cleanup_ts.sh` runs automatically; monitor anyway during race day. The disk-usage watchdog is what keeps a long event from filling `/`.

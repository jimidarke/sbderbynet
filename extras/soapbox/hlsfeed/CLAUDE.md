# HLS Video Feed

## Purpose

Converts RTSP camera streams to HLS (HTTP Live Streaming) for browser-based race viewing. Supports multiple cameras, segment management, and replay recording.

## How It Fits

Cameras at the race track stream RTSP. This service converts to HLS segments served via Nginx, viewable in any browser. The replay handler integrates with race events for recording specific races.

## Key Files

- `hlsfeed.sh` — Main streaming script (RTSP-to-HLS via FFmpeg)
- `multicam-service.py` — Multi-camera stream management
- `cleanup_ts.sh` — Automatic HLS segment cleanup (prevents disk fill)
- `config.env` — RTSP source URLs and stream configuration
- `nginx/hls.conf` — Nginx configuration for serving HLS segments

## Dependencies

- FFmpeg (RTSP input, HLS output)
- Nginx (segment serving)
- Python 3 (multicam service)
- RTSP-capable cameras on the race network

## Common Tasks

- **Start streaming**: `sudo systemctl start hlsfeed`
- **Add cameras**: Edit `config.env` with RTSP URLs
- **Check disk**: `cleanup_ts.sh` runs automatically, but monitor disk usage on race day

## Gotchas

- **Disk usage**: HLS segments accumulate fast — cleanup script is essential
- **Network bandwidth**: Multiple HD streams need sufficient network capacity
- **Camera compatibility**: Test RTSP URLs with `ffplay` before configuring

## Related Docs

- [README.md](README.md) — Setup and configuration guide
- [MULTICAM_SETUP.md](MULTICAM_SETUP.md) — Multi-camera configuration

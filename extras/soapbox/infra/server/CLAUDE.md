# Race Server

## Purpose

Central orchestration service for soapbox derby races. Manages race lifecycle (staging, start, timing, finish), coordinates hardware devices via MQTT, bridges to the DerbyNet PHP app via HTTP API and direct SQLite writes for low-latency result recording.

## How It Fits

This is the hub of the hardware layer. Finish timers and start timers publish events via MQTT; this server consumes them, manages race state, and writes results to the DerbyNet database. Kiosk displays and LED signs subscribe to race state updates published by this server.

## Key Files

- `derbyRace.py` — Main entry point (v0.9.3). Race state machine, lane time management with thread locks, MQTT message routing
- `derbyapi.py` — DerbyNet HTTP API client for schedule queries and result submission
- `derbydb.py` — Direct SQLite database access (bypasses HTTP for race-critical writes)
- `derbyTime.py` — Time synchronization service
- `derbynet.py` — Standardized MQTT networking library with retry logic and message queuing
- `serverlogger.py` — Unified logging framework (v2.0.0)
- `ledsign_content.py` — LED sign content generation based on race state
- `simulate_racing.py` — End-to-end race simulation for testing

## Dependencies

- Python 3, paho-mqtt, requests, psutil, RPi.GPIO (on Pi)
- MQTT broker (Mosquitto) on `192.168.100.10:1883`
- DerbyNet PHP app on `192.168.100.10:80`
- SQLite database at `/var/lib/derbynet/{year}/{event}/derbynet.sqlite3`

## Common Tasks

- **Run**: `python3 derbyRace.py` (as systemd service: `sudo systemctl start derbyrace`)
- **Simulate**: `python3 simulate_racing.py` (no hardware needed)
- **View logs**: Check serverlogger output or `journalctl -u derbyrace`
- **Test plan**: See `tests/DERBYRACE_TEST_PLAN.md`

## Gotchas

- **Thread safety**: Lane time updates use thread locks (added v0.8.1) to prevent race conditions between MQTT callbacks
- **Dual write path**: Results go via direct SQLite (fast) with HTTP API fallback if DB unavailable
- **State machine**: States are `UNCONFIGURED → STOPPED → STAGING → RACING → FINISHED`. See [docs/RACINGSTATEENGINE.md](../../../../docs/RACINGSTATEENGINE.md)
- **Version history**: Extensive changelog in `derbyRace.py` header comments (30+ versions)

## Related Docs

- [README.md](README.md) — Component overview and installation
- [LOGGING.md](LOGGING.md) — Logging framework configuration
- [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md) — Pi server setup guide
- [docs/RACINGSTATEENGINE.md](../../../../docs/RACINGSTATEENGINE.md) — Cross-layer state machine documentation

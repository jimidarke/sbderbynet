# Soapbox Derby Infrastructure

## Purpose

Complete hardware and software infrastructure for running soapbox derby events. This layer sits on top of the DerbyNet PHP core (`/website/`) and adds real-time hardware coordination, video streaming, display management, and audio via MQTT messaging.

## How It Fits

The DerbyNet PHP app manages race data (schedules, results, rosters). This infrastructure layer handles the physical event — detecting race starts/finishes, coordinating timers, driving displays, and streaming video. The Race Server (`infra/server/`) is the central hub that bridges hardware devices to the DerbyNet database.

## Component Map

| Component | Directory | Tech | Purpose |
|-----------|-----------|------|---------|
| Race Server | `infra/server/` | Python/MQTT | Central orchestration, state machine, API bridge |
| Finish Timer | `infra/finishtimer/` | Python/GPIO | Lane finish detection on Raspberry Pi |
| Start Timer | `infra/starttimer/` | MicroPython/ESP32 | Race start signal detection |
| Derby Display | `infra/derbydisplay/` | Python/Chromium | Kiosk display management |
| HLS Feed | `hlsfeed/` | FFmpeg/Nginx | RTSP-to-HLS video streaming |
| Audio Pi | `audiopi/` | Audio | Event audio/sound system |
| Deployment | `infra/deployment/` | Bash | SD card imaging scripts |

Each component has its own `CLAUDE.md` with detailed guidance.

## Network Architecture

- **Subnet**: `192.168.100.x` (isolated race network)
- **MQTT Broker**: Mosquitto on `192.168.100.10:1883`
- **DerbyNet Server**: `192.168.100.10:80` (PHP/Nginx)
- **All devices**: Static IPs on the race subnet

## MQTT Topic Hierarchy

```
derbynet/
├── race/state          — Race state changes (STAGING, RACING, FINISHED)
├── race/events         — Race events (start, finish, results)
├── device/{hwid}/state — Device state reports
├── device/{hwid}/telemetry — Device health/metrics (1s interval)
└── broadcast/          — Emergency and general announcements
```

See [doc/MQTT_API.md](doc/MQTT_API.md) for full protocol specification.

## Communication Patterns

1. **Real-time**: MQTT pub/sub for device state, race events, telemetry
2. **Setup/Config**: HTTP polling to DerbyNet for configuration discovery
3. **Race-critical**: Direct SQLite writes for sub-second result recording (Race Server)
4. **Resilience**: Local message queuing during network outages, exponential backoff reconnection

## Related Docs

- [doc/MQTT_API.md](doc/MQTT_API.md) — MQTT topic and message format specification
- [doc/DERBYNET_REFERENCE.md](doc/DERBYNET_REFERENCE.md) — DerbyNet system technical reference
- [doc/HLS_REPLAY_DOCUMENTATION.md](doc/HLS_REPLAY_DOCUMENTATION.md) — Video replay system
- [doc/SoapboxDerby_Test_Guide.md](doc/SoapboxDerby_Test_Guide.md) — Hardware testing procedures
- [../../docs/LOGGING.md](../../docs/LOGGING.md) — Race-day on-Pi logging map (rsyslog topology, time discipline, chronology tool)
- [infra/server/LOGGING.md](infra/server/LOGGING.md) — Unified logging framework, heat correlation IDs, error code catalog

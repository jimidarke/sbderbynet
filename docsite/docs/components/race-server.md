# Race Server

Central orchestration daemon for soapbox derby races. Manages race lifecycle (staging, start, timing, finish), coordinates hardware via MQTT, and bridges to the DerbyNet PHP app via HTTP API + direct SQLite writes for low-latency result recording.

Lives at `extras/soapbox/infra/server/`. Python 3, paho-mqtt, requests, psutil, RPi.GPIO. Runs as `derbyrace.service`.

---

## What it does

- Race state machine: `UNCONFIGURED → STOPPED → STAGING → RACING → FINISHED`.
- Consumes finish/start events from MQTT and writes lane times to the DB.
- Publishes lane LED commands and per-lane "pinny" (racer-number) displays.
- Reports device telemetry; monitors timer health via heartbeats.
- Drives LED sign content based on race state.

See [Race State Engine](../architecture/race-state-engine.md) for the state machine; [MQTT API](../reference/mqtt-api.md) for topic definitions.

---

## Key files

| File | Role |
|---|---|
| `derbyRace.py` | Main entry. State machine, lane time management with thread locks, MQTT routing |
| `derbyapi.py` | DerbyNet HTTP API client (schedule queries, result submission) |
| `derbydb.py` | Direct SQLite access (bypasses HTTP for race-critical writes) |
| `derbyTime.py` | Time sync service |
| `derbynet.py` | Standardised MQTT networking library (retry logic, message queuing) |
| `serverlogger.py` | Unified logging framework (v2.0.0) |
| `ledsign_content.py` | LED sign content generation |
| `simulate_racing.py` | End-to-end simulation (no hardware needed) |

## Dependencies

- Python 3, `paho-mqtt`, `requests`, `psutil`, `RPi.GPIO` (on Pi).
- MQTT broker (Mosquitto) on `192.168.100.10:1883`.
- DerbyNet PHP app on `192.168.100.10:80`.
- SQLite at `/var/lib/derbynet/{year}/{event}/derbynet.sqlite3`.

## MQTT topics

Publishes / subscribes to:

- `derbynet/race/state` — current race state.
- `derbynet/race/event` — race events (start signals, finish events).
- `derbynet/device/+/state` — device state changes.
- `derbynet/device/+/telemetry` — device health.
- `derbynet/lane/{lane}/led` — LED state per lane.
- `derbynet/lane/{lane}/pinny` — racer-number display per lane.

Full reference: [MQTT API](../reference/mqtt-api.md).

---

## Common tasks

```bash
# Run as service
sudo systemctl {start,stop,status} derbyrace
sudo journalctl -u derbyrace -f

# Run directly
python3 derbyRace.py

# Simulate without hardware
python3 simulate_racing.py
```

Test plan: `extras/soapbox/infra/server/tests/DERBYRACE_TEST_PLAN.md`.

---

## Gotchas

- **Thread safety**: lane time updates use thread locks (added v0.8.1) to prevent race conditions between MQTT callbacks. Don't remove them.
- **Dual write path**: results go via direct SQLite (fast) with HTTP API fallback if the DB is unavailable.
- **Authentication**: race server logs into DerbyNet with the `Timer` role.
- **Default DerbyNet server IP**: `192.168.100.10`. Default MQTT broker: same host (the README's "localhost" is the broker as seen from the same machine).

## Troubleshooting

| Symptom | Where to look |
|---|---|
| Connection to DerbyNet fails | Pi network up, DerbyNet running, `Timer` role credentials |
| Timers not reporting | broker running, devices powered, heartbeats in logs |
| Timing drift / odd values | NTP healthy, MQTT latency on the wifi bridge ([Network](../architecture/network.md)) |

See also: [Logging](../operations/logging.md), [DerbyPi](derbypi.md).

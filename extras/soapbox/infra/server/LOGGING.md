# DerbyNet Unified Logging Framework

**Version: 3.0.0** | **Date: 2026-01-14**

## Overview

Centralized logging for all Derby infrastructure components with:
- Dual output: human-readable text + parseable JSON (JSONL)
- Standardized error codes across Python and PHP
- MQTT alerting for critical errors
- Unified timezone handling

## Time Synchronization Architecture

**CRITICAL: All devices MUST sync time from the DerbyPi server.**

```
┌─────────────────────────────────────────────────────────────┐
│                     TIME SYNC HIERARCHY                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Internet NTP ─────┐                                        │
│         OR          ├──► DerbyPi (NTP Server)               │
│   Battery RTC ──────┘         │                              │
│                               │                              │
│                    ┌──────────┼──────────┐                   │
│                    ▼          ▼          ▼                   │
│              FinishTimer  StartTimer  Display                │
│              (sync from   (sync from  (sync from             │
│               DerbyPi)     DerbyPi)    DerbyPi)              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### DerbyPi Server (NTP Host)
- Primary: Syncs via internet NTP when available
- Offline fallback: Battery-backed RTC maintains time
- Serves NTP to all other infrastructure devices
- IP: `192.168.100.10` (default)

### Remote Devices (NTP Clients)
All finish timers, start timers, and displays MUST:
1. Configure NTP client to sync from DerbyPi: `192.168.100.10`
2. Disable other NTP sources when on derby network
3. Verify sync before race operations

### Why Local Timezone (Not UTC)
- Race times displayed to coordinators/spectators in local time
- Log analysis more intuitive during live events
- JSON logs include ISO 8601 timestamps with timezone offset for unambiguous parsing
- Configured timezone: `America/Edmonton` (adjust per deployment)

## Log Files

| File | Format | Purpose |
|------|--------|---------|
| `/var/log/derbynet.log` | Text | Human-readable, console, rsyslog |
| `/var/log/derbynet.jsonl` | JSONL | Machine-parseable, alerting, analysis |

## Output Formats

### Text Format
```
2025-12-08 14:35:22.123 FINISH1:ERROR [finishtimer.py:234] [ERR-HW-201] Sensor timeout
```

| Part | Description |
|------|-------------|
| Timestamp | `YYYY-MM-DD HH:MM:SS.mmm` (local timezone) |
| Device:Level | Hostname uppercase, level: DEBUG/INFO/WARNING/ERROR/CRITICAL |
| Location | `[filename:line]` |
| Error Code | `[ERR-XXX-NNN]` (optional) |

### JSON Format (JSONL)
```json
{"ts":"2025-12-08T14:35:22.123-07:00","level":"ERROR","device":"FINISH1","component":"finishtimer","file":"finishtimer.py","line":234,"msg":"Sensor timeout","code":"ERR-HW-201","ctx":{"lane":2,"timeout_ms":5000}}
```

| Field | Description |
|-------|-------------|
| `ts` | ISO 8601 timestamp with timezone offset |
| `level` | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `device` | Device identifier (uppercase hostname) |
| `component` | Module/service name |
| `file` | Source filename |
| `line` | Line number |
| `msg` | Log message |
| `code` | Error code (optional) |
| `ctx` | Context data (optional) |

## Error Code Format

`ERR-{CATEGORY}-{NUMBER}`

### Categories
| Code | Category | Description |
|------|----------|-------------|
| AUTH | Authentication | Logins, permissions, sessions |
| VAL | Validation | Input validation, data format |
| DB | Database | SQL, connections, queries |
| HW | Hardware | Timers, sensors, devices |
| NET | Network | MQTT, HTTP, connectivity |
| RACE | Race | State, timing, results |
| SYS | System | Memory, disk, processes |
| CFG | Configuration | Settings, files, initialization |

### Severity by Number
| Range | Severity | Alert |
|-------|----------|-------|
| 1xx | WARNING | No |
| 2xx | ERROR | No |
| 3xx | CRITICAL | Yes (MQTT) |

### Common Error Codes
```
ERR-HW-101  Low battery warning
ERR-HW-201  Sensor timeout
ERR-HW-301  Device offline (ALERT)

ERR-NET-201  MQTT publish failed
ERR-NET-301  MQTT broker disconnected (ALERT)

ERR-DB-201   SQL query failed
ERR-DB-301   Database connection lost (ALERT)

ERR-RACE-201 Invalid state transition
ERR-RACE-301 Timing system failure (ALERT)
```

## Usage

### Python (Server)
```python
from derbylogger import setup_logger

logger = setup_logger('derbyrace')
logger.info("Heat started")
logger.error("Sensor timeout", extra={
    'error_code': 'ERR-HW-201',
    'context': {'lane': 2, 'timeout_ms': 5000}
})
```

### Python (Remote Device)
```python
from nodelogger import NodeLogger

logger = NodeLogger(name='finishtimer').get_logger()
logger.info("Lane triggered")
logger.warning("Low battery", extra={'error_code': 'ERR-HW-101'})
```

### PHP
```php
require_once('inc/error-logging.inc');

derby_log_info("Heat started");
derby_log_error("Database failed", 'ERR-DB-201', ['query' => 'SELECT...']);
```

## Alerting

Critical errors (3xx codes) are published to MQTT for real-time alerting.

### MQTT Topics
| Topic | Description |
|-------|-------------|
| `derbynet/alerts` | All critical alerts |
| `derbynet/alerts/hw` | Hardware alerts |
| `derbynet/alerts/net` | Network alerts |
| `derbynet/alerts/db` | Database alerts |
| `derbynet/alerts/race` | Race state alerts |

### Alert Message Format
```json
{
  "ts": "2025-12-08T14:35:22.123-07:00",
  "alert_id": "uuid",
  "code": "ERR-HW-301",
  "level": "CRITICAL",
  "device": "FINISH2",
  "msg": "Device offline - Lane 2 timer not responding",
  "ctx": {"lane": 2, "timeout_seconds": 3}
}
```

### Subscribe to Alerts
```bash
mosquitto_sub -h 192.168.100.10 -t 'derbynet/alerts/#'
```

## Heat Correlation IDs

The race server mints a per-heat correlation ID on every heat change and
broadcasts it (retained) on MQTT so device firmware can stamp it into every
event payload. This is what lets `derby-chronology` filter and join all
component events for a single heat.

| Item | Value |
|------|-------|
| Topic | `derbynet/race/heat/correlation` |
| QoS | 1 |
| Retain | true |
| Payload | `heat-{round}-{heat}-{epoch_ms}` (plain string) |
| Publisher | `derbyRace.updateFromDerbyAPI` on `(roundid, heatid)` change |
| Subscribers | `finishtimer.py`, `starttimer/main.py`, derby-chronology |

Device payloads stamp `correlation_id` on:
- `derbynet/device/{hwid}/state` (toggle + start events)
- `derbynet/device/{hwid}/telemetry`

Server-side, the same id is also passed through `derbylogger.set_correlation_id()`
so every JSONL line written during the heat carries it in the `corr_id` field.
A correlation id that starts with `heat-{round}-{heat}-` is sufficient to
filter the entire heat — the epoch_ms suffix only disambiguates re-runs of
the same heat number.

## Chronology Tool

`derby-chronology` (installed at `/usr/local/bin/derby-chronology` on the
race-server Pi via the `raceserver` Ansible role) merges all sources into
one timeline.

```sh
derby-chronology --heat 3/7              # round 3, heat 7
derby-chronology --heat heat-3-7-...     # exact correlation_id
derby-chronology --since "2026-05-20 09:00" --until "2026-05-20 09:30"
derby-chronology --include-archives --heat 3/7    # also reads gz archives
derby-chronology --heat 3/7 --mqtt-log            # add broker connect events
derby-chronology --heat 3/7 --format md > heat-3-7.md
```

The header block shows: total entries and window, device counts, NTP-sync
anchors, START-event device/server clock offset (logged by derbyRace as
`START event: device_ts=... server_recv_ts=... offset_ms=...`), and the
finishtimer GPIO-edge→publish latency distribution per lane.

## Configuration

### Timezone
**IMPORTANT:** All components MUST use the same timezone.

Edit constant in each logger:
- Python: `DERBY_TIMEZONE = 'America/Edmonton'` in `derbylogger.py`
- PHP: `define('DERBY_TIMEZONE', 'America/Edmonton');` in `error-logging.inc`
- System: `sudo timedatectl set-timezone America/Edmonton`

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `DERBY_TIMEZONE` | America/Edmonton | Timestamp timezone |
| `DERBY_DEBUG` | false | Enable DEBUG level |
| `DERBY_CONSOLE_LOG` | false | Output to console |
| `DERBY_JSON_LOG` | true | Write JSON log file |
| `DERBY_DEVICE_ID` | hostname | Override device ID |
| `RSYSLOG_IP` | 192.168.100.10 | rsyslog server IP |
| `RSYSLOG_PORT` | 514 | rsyslog server port |

### Debug Mode
```bash
export DERBY_DEBUG=true        # Python DEBUG level
export DERBY_PHP_DEBUG=true    # PHP DEBUG level
export DERBY_CONSOLE_LOG=true  # Python console output
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LOGGING ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Server Components          Remote Devices                   │
│  ┌─────────────────┐        ┌─────────────────┐             │
│  │ derbyRace.py    │        │ finishtimer.py  │             │
│  │ derbydb.py      │        │ starttimer.py   │             │
│  │ PHP (action.php)│        │ display.py      │             │
│  └────────┬────────┘        └────────┬────────┘             │
│           │                          │                       │
│           ▼                          ▼                       │
│  ┌─────────────────┐        ┌─────────────────┐             │
│  │ derbylogger.py  │        │ nodelogger.py   │             │
│  │ error-logging   │        │ (wraps derby-   │             │
│  │    .inc         │        │  logger)        │             │
│  └────────┬────────┘        └────────┬────────┘             │
│           │                          │                       │
│           ▼                          ▼                       │
│  ┌─────────────────┐        ┌─────────────────┐             │
│  │ /var/log/       │        │   rsyslog UDP   │             │
│  │ derbynet.log    │◄───────│   port 514      │             │
│  │ derbynet.jsonl  │        └─────────────────┘             │
│  └────────┬────────┘                                        │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │ alerthandler.py │──────► MQTT derbynet/alerts            │
│  └─────────────────┘                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `server/derbylogger.py` | Unified Python logger (v3.0.0) |
| `server/error_codes.py` | Python error code registry |
| `server/alerthandler.py` | MQTT alerting handler |
| `finishtimer/files/nodelogger.py` | Remote device logger wrapper |
| `derbydisplay/derbylogger.py` | Display logger wrapper |
| `website/inc/error-logging.inc` | PHP logger (v3.0.0) |
| `website/inc/error-codes.inc` | PHP error code registry |
| `server/rsyslog/10-derbynet.conf` | rsyslog config |

## Viewing Logs

### Text Log
```bash
tail -f /var/log/derbynet.log           # Live tail
grep ':ERROR \[' /var/log/derbynet.log  # By level
grep 'FINISH1:' /var/log/derbynet.log   # By device
grep 'ERR-HW-' /var/log/derbynet.log    # By error category
```

### JSON Log
```bash
# Pretty print last entry
tail -1 /var/log/derbynet.jsonl | python3 -m json.tool

# Filter by error code
cat /var/log/derbynet.jsonl | jq 'select(.code | startswith("ERR-HW-"))'

# Count errors by code
cat /var/log/derbynet.jsonl | jq -r '.code // empty' | sort | uniq -c

# Extract CRITICAL entries
cat /var/log/derbynet.jsonl | jq 'select(.level == "CRITICAL")'
```

## Troubleshooting

### Check Files/Permissions
```bash
ls -la /var/log/derbynet.log /var/log/derbynet.jsonl
```

### Test Python Logger
```bash
cd /var/lib/infra/app
python3 derbylogger.py
```

### Test Alert Handler
```bash
python3 alerthandler.py
```

### Check rsyslog
```bash
sudo systemctl status rsyslog
journalctl -u rsyslog -f
```

### Verify NTP Sync
```bash
# On DerbyPi server
timedatectl status
chronyc sources  # or ntpq -p

# On remote devices
timedatectl status
chronyc sources -v
```

### Common Issues

| Issue | Solution |
|-------|----------|
| JSON file not created | Check `DERBY_JSON_LOG=true` env var |
| Wrong timezone in logs | Verify `DERBY_TIMEZONE` constant matches system |
| Alerts not publishing | Check MQTT broker connection |
| Remote logs missing | Verify rsyslog UDP 514 connectivity |
| Time drift on devices | Ensure NTP client points to DerbyPi |

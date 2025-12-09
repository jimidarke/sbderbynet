# Racing State Engine

This document describes the race state management system that maintains state integrity across multiple devices and services in the SoapBox Derby race management system.

## Problem Statement

The race state management system had potential edge cases where the system could believe a race is running (`TIMER_RUNNING`) but the physical start hadn't been given. This occurred during:
- Manual adjustments on the coordinator page
- Network latency causing stale state propagation
- Manual start button pressed without proper staging
- Heartbeat arrival during state transitions

The system must maintain **integral state** across:
1. PHP/DerbyNet backend (source of truth)
2. Python race server (hardware coordinator)
3. Start and finish timers (hardware devices)

## Architecture Overview

### State Layers

| Layer | States | Storage | Communication |
|-------|--------|---------|---------------|
| **PHP/Web** | `NowRacingState` (0/1) + Timer State (7 states) | RaceInfo table | AJAX polling (1 sec) |
| **Python Server** | `STOPPED/STAGING/RACING` | Memory (derived from API) | MQTT + HTTP |
| **Hardware Timers** | Ready/Toggle | MQTT topics | MQTT telemetry (1 sec) |

### Timer State Constants (PHP)

```
TIMER_NOT_CONNECTED (1) - No recent contact from authenticated timer
TIMER_SEARCHING (6)     - Timer connection in progress
TIMER_UNCONFIRMED (7)   - Timer identified but not verified
TIMER_CONNECTED (2)     - Timer connected and idle
TIMER_STAGING (3)       - Heat ready, waiting for start
TIMER_RUNNING (4)       - Race in progress
TIMER_UNHEALTHY (5)     - Persistent malfunction detected
```

### State Flow Diagram

```
                                ┌─────────────────────┐
                                │     NOT_RACING      │
                                │  NowRacingState=0   │
                                │  timer=CONNECTED    │
                                │  Python=STOPPED     │
                                └──────────┬──────────┘
                                           │
                                           │ Coordinator sets now_racing=1
                                           ▼
                                ┌─────────────────────┐
                                │      STAGING        │
                                │  NowRacingState=1   │
                                │  timer=STAGING      │
                                │  Python=STAGING     │
                                │  physical_start=0   │
                                └──────────┬──────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    │ Start Timer GO       │ Manual Start         │ Timeout/Cancel
                    │ (MQTT)               │ (API)                │
                    ▼                      ▼                      ▼
          ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
          │ RUNNING         │   │ RUNNING         │   │ NOT_RACING      │
          │ (CONFIRMED)     │   │ (UNCONFIRMED)   │   │ (cancelled)     │
          │ physical_start  │   │ physical_start  │   │                 │
          │   = timestamp   │   │   = 0           │   │                 │
          │ integrity=OK    │   │ integrity=WARN  │   │                 │
          └────────┬────────┘   └────────┬────────┘   └─────────────────┘
                   │                     │
                   │ All lanes finish    │ Lanes finish
                   ▼                     ▼
          ┌─────────────────────────────────────┐
          │            FINISHED                 │
          │  Results written to RaceChart       │
          │  Auto-advance to next heat          │
          └─────────────────────────────────────┘
```

## Centralized Configuration

All timeout thresholds are defined in `/website/inc/heartbeat-config.inc`:

| Constant | Value | Purpose |
|----------|-------|---------|
| `HEARTBEAT_INTERVAL` | 5s | How often heartbeats are sent |
| `TIMER_RECENT_THRESHOLD` | 5s | Max age for timer to be "recent" |
| `TIMER_STALE_THRESHOLD` | 8s | When to mark timer stale in DB |
| `TIMER_DISCONNECT_THRESHOLD` | 15s | When PHP considers timer disconnected |
| `DEVICE_INACTIVE_THRESHOLD` | 30s | When to mark device inactive |
| `FRONTEND_OFFLINE_THRESHOLD` | 8s | When UI shows timer as offline |
| `MIN_TIMERS_FOR_RACE` | 3 | Minimum finish timers required |
| `INTEGRITY_GRACE_PERIOD` | 5s | Grace period before flagging issues |
| `ORPHAN_START_TIMEOUT` | 120s | Time to keep orphan start records |

### Timeout Cascade

Timeouts are designed to cascade upward:
```
HEARTBEAT_INTERVAL (5s)
  ≤ TIMER_RECENT_THRESHOLD (5s)
    < TIMER_STALE_THRESHOLD (8s)
      < TIMER_DISCONNECT_THRESHOLD (15s)
        < DEVICE_INACTIVE_THRESHOLD (30s)
```

## Physical Start Tracking

The system now tracks physical start events to detect state integrity issues.

### RaceInfo Keys

| Key | Description |
|-----|-------------|
| `physical_start_time` | Unix timestamp when start signal received |
| `physical_start_source` | `'start_timer'` or `'manual'` |
| `race_integrity` | `'OK'`, `'WARN:reason'`, or `'ERROR:reason'` |

### Recording Physical Start

When a `STARTED` message is received (`/website/ajax/action.timer-message.inc`):
```php
$start_source = isset($_POST['manual']) ? 'manual' : 'start_timer';
write_raceinfo('physical_start_time', time());
write_raceinfo('physical_start_source', $start_source);
write_raceinfo('race_integrity', 'OK');
```

### Clearing Physical Start

Physical start tracking is cleared when:
- Race finishes (FINISHED message with successful results)
- Racing is aborted (ABORT sent)
- Orphan timeout expires (120 seconds)

## State Integrity Validation

### PHP Integrity Check

The `check_race_integrity()` function in `/website/inc/racing-state.inc` detects:

| Condition | Status | Description |
|-----------|--------|-------------|
| `TIMER_RUNNING` but `physical_start_time = 0` | WARN | Running without confirmed start |
| `!now_racing` but recent `physical_start_time` | WARN | Orphaned physical start |
| `TIMER_RUNNING` with `manual` source | OK | Manual start (acceptable) |
| All checks pass | OK | Normal operation |

### Python Integrity Check

The `check_race_integrity()` method in `/extras/soapbox/infra/server/derbyRace.py` detects:

- Python racing but PHP `NowRacingState` is OFF
- PHP timer shows running but Python not racing
- Racing state without valid start time
- Round/heat mismatch during active race

### Integrity Response Format

```json
{
  "status": "ok|warn|error",
  "code": "no_physical_start|orphan_start|manual_start|ok",
  "message": "Human-readable description"
}
```

## Health Status Display

### Health Status Levels

| Status | Condition | Display |
|--------|-----------|---------|
| `healthy` | All timers online and ready | No warning |
| `degraded` | Timer(s) offline, not racing | Yellow warning |
| `warning` | Timer(s) not ready during staging | Yellow warning |
| `critical` | Timer(s) offline during active race | Red pulsing warning |

### JSON Timer State Response

The `/website/inc/json-timer-state.inc` returns:

```json
{
  "lanes": 3,
  "state": 4,
  "message": "Race running",
  "timers": [...],
  "server_time": 1733654321,
  "timers_online": 3,
  "timers_ready": 3,
  "timers_required": 3,
  "health_status": "healthy",
  "health_message": ""
}
```

### Frontend Warning Display

The coordinator page (`/website/js/coordinator-poll.js`) displays health warnings:

```javascript
// Show warning when health is degraded/critical or integrity issues exist
if ((nowRacing && (healthStatus === 'critical' || healthStatus === 'warning')) ||
    raceIntegrity.status === 'warn' || raceIntegrity.status === 'error') {
  showTimerHealthWarning(healthStatus, healthMessage, raceIntegrity);
}
```

## Files Modified

### PHP Files

| File | Purpose |
|------|---------|
| `/website/inc/heartbeat-config.inc` | Centralized timeout constants |
| `/website/inc/timer-state.inc` | Timer state machine with configurable timeout |
| `/website/inc/racing-state.inc` | Added `check_race_integrity()` function |
| `/website/inc/json-timer-state.inc` | Health status calculation |
| `/website/ajax/action.timer-message.inc` | Physical start tracking |
| `/website/ajax/query.poll.coordinator.inc` | Integrity in poll response |

### Python Files

| File | Purpose |
|------|---------|
| `/extras/soapbox/infra/server/derbyRace.py` | Aligned timeout, integrity validation |
| `/extras/soapbox/infra/server/derbyapi.py` | Aligned recency threshold |

### Frontend Files

| File | Purpose |
|------|---------|
| `/website/js/coordinator-poll.js` | Health warning display functions |
| `/website/css/coordinator.css` | Health warning styles |

## Design Decisions

### Source of Truth

**PHP backend is the single source of truth.** The Python server derives its state from DerbyNet API responses and reports to PHP. This ensures:
- Consistent state across all web clients
- Database-backed persistence
- Existing coordinator workflow unchanged

### Physical Start Cannot Be Blocked

When the physical start actuator releases the carts, it cannot be stopped. Therefore:
- System logs warnings but proceeds with race
- Manual starts are allowed with warning indication
- Integrity issues are displayed but don't block operation

### Sync Latency

Near real-time synchronization (1-3 seconds) is acceptable:
- Coordinator polls every 1 second
- Heartbeats sent every 5 seconds
- State changes propagate within 1-2 poll cycles

## Testing Scenarios

1. **Normal race flow**: Staging → Physical Start → Running → Finish → Results
2. **Manual start without timer**: Shows warning but proceeds
3. **Start timer fire when not racing**: Logged, state unchanged
4. **Timer goes offline during race**: Critical warning displayed
5. **Network latency**: Python re-sends start confirmation if mismatch detected

## Troubleshooting

### Timer Shows Offline

1. Check physical timer device power and network
2. Verify MQTT broker is running
3. Check `TIMER_STALE_THRESHOLD` hasn't been exceeded
4. Review `/var/log/derbynet.log` for heartbeat errors

### Integrity Warning: "Running without physical start"

This indicates `TIMER_RUNNING` state without a recorded start signal:
1. May occur with legacy timer setups
2. Manual start button can be used
3. Check start timer MQTT connectivity

### State Mismatch Between PHP and Python

1. Check network connectivity between race server and web server
2. Verify API authentication is working
3. Review Python logs for API errors
4. Force heartbeat by restarting derbyRace service

## Version History

- **v0.6.3** (2025-12) - Initial race state engine integrity implementation
  - Centralized timeout configuration
  - Physical start tracking
  - State integrity validation
  - Health status display

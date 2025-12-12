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
| **Python Server** | `UNCONFIGURED/STOPPED/STAGING/RACING/FINISHED` | Memory (derived from API) | MQTT + HTTP |
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

### Python Race Server States

```
RACE_STATE_UNCONFIGURED - API unavailable / no database configured (LED: yellow)
RACE_STATE_STOPPED      - Race not active (LED: red)
RACE_STATE_STAGING      - Race active, waiting for start (LED: blue)
RACE_STATE_RACING       - Race in progress (LED: green)
RACE_STATE_FINISHED     - All lanes complete (transient, returns to STOPPED)
```

**Note:** "FINISHED" is a transient state - after processing results, state automatically transitions to STOPPED.

### LED Color Reference

| Color | RGB Pins (H/L) | State(s) | Description |
|-------|----------------|----------|-------------|
| Red | R:H G:L B:L | STOPPED, DNF, Lane Finished | Race not active, lane did not finish, or lane crossed finish line |
| Blue | R:L G:L B:H | STAGING (ready) | Heat ready, toggle flipped, waiting for start signal |
| Green | R:L G:H B:L | RACING | Race in progress |
| Purple (flicker) | R:H G:L B:H | STAGING (not ready) | Heat staged but toggle not flipped (display shows "flip"); flickers to grab attention |
| Yellow | R:H G:H B:L | UNCONFIGURED, Error | API unavailable or system error |
| White | R:H G:H B:H | Boot/Diagnostic | Power-on sequence or test mode |

### State Flow Diagram

```
          ┌─────────────────────┐
          │    UNCONFIGURED     │
          │  API unavailable    │
          │  LED=YELLOW         │
          └──────────┬──────────┘
                     │ API becomes available
                     ▼
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

### Lane Completion Guard

Once a race is started (RACING state with valid start_time), the Python race server **will not transition away from RACING** until:
1. All lanes have finished (either crossed finish line or marked DNF)
2. Race timeout (70s) expires and remaining lanes are auto-marked DNF

This prevents the bug where PHP reporting "Staging" (e.g., for next heat prep) would cause Python to prematurely end the current race.

**Implementation in `setLEDFromRaceStat()`:**
```python
# GUARD: If we're racing and not all lanes finished, stay in RACING
if (self.race_state == RACE_STATE_RACING and
    self.start_time > 0 and
    self.lanesFinished < self.lane_count):
    return  # Don't change state
```

**Per-Lane DNF Support:**
The coordinator can mark individual lanes as DNF (99.999s):
- Clicking DNF button for an unfinished lane triggers lane completion
- Clicking DNF for an already-finished lane updates that lane's time to DNF
- If DNF is clicked on the last unfinished lane, the race completes

**DNF Data Flow:**
1. User clicks DNF button on coordinator page (`coordinator-poll.js:handleRacerDNF()`)
2. AJAX request to `action.php` with `action: 'racer.dnf'`
3. PHP backend (`action.racer.dnf.inc`) sets `finishtime = 99.999` in RaceChart table
4. Python race server polls API every second via `updateFromDerbyAPI()`
5. API (`derbyapi.py:get_race_status()`) includes `finishtime` in lanes data
6. Detection code in `derbyRace.py` finds `finishtime >= 99.999` and calls `laneDNF()`
7. Race server updates lane state, LED (red), and completes race if all lanes finished

### State Transition Reset

When transitioning between race states, the system performs cleanup to prevent stale data:

**STAGING Transition** (from FINISHED/STOPPED/UNCONFIGURED):
- Clears `lane_times`, `lanesFinished`, `start_time`
- Forces LED update to all lanes (blue)
- Logs warning if stale data was present

**STOPPED Transition** (from any other state):
- Clears `lane_times`, `lanesFinished`, `start_time`
- Forces LED update to all lanes (red)
- Logs warning if stale data was present

This prevents issues where:
1. Incomplete/aborted races leave stale timing data
2. Individual lane LEDs (purple for finish) don't reset after race completion

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

- **v0.7.3** (2025-12) - DNF button integration fix
  - **Fixed DNF button not being picked up by race server** - `derbyapi.py` now passes `finishtime` field from PHP API response
  - Added `finishtime` to lanes data in `get_race_status()` enabling Python race server to detect coordinator DNF clicks
  - DNF detection now works within 1 second polling cycle
  - Race completes properly when DNF is clicked on the last unfinished lane
  - Documented complete DNF data flow in "Per-Lane DNF Support" section

- **v0.7.2** (2025-12) - LED color scheme update and state reset
  - **Changed lane finish color from purple to red** - Red now indicates lane stopped/finished
  - **Purple now indicates "flip" state** - Staging but toggle not ready (needs flip)
  - Force LED update to all lanes when transitioning between states
  - Fixed lane LEDs not resetting after race completion

- **v0.7.1** (2025-12) - Stale race data cleanup
  - **Fixed stale race data causing incorrect finish times** - Race tracking now resets on state transitions
  - Added reset of `lane_times`, `lanesFinished`, and `start_time` when entering STAGING or STOPPED
  - Prevents data from aborted/incomplete races from affecting subsequent races
  - Added warning logs when clearing stale race data

- **v0.7.0** (2025-12) - Lane completion guard and DNF support
  - **Fixed premature race finish bug** - Race no longer transitions from RACING to STAGING until all lanes complete
  - Added lane completion guard in `setLEDFromRaceStat()` to prevent state transitions while race in progress
  - Dynamic lane count - Now updates from actual racers in each heat instead of hardcoded value
  - Added `laneDNF()` method for per-lane DNF support
  - DNF detection via polling - Detects coordinator DNF button clicks within 1 second
  - See "Lane Completion Guard" section for implementation details

- **v0.6.3** (2025-12) - Race state alignment and UNCONFIGURED state
  - Added UNCONFIGURED state for pre-setup scenarios (yellow LED)
  - Aligned state constants across Python race server and API client
  - Added LED color reference documentation
  - Fixed state persistence bug when API unavailable

- **v0.6.2** (2025-12) - Initial race state engine integrity implementation
  - Centralized timeout configuration
  - Physical start tracking
  - State integrity validation
  - Health status display

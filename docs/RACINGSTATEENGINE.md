# Racing State Engine

Race state management across PHP backend, Python race server, and hardware timers.

## State Layers

| Layer | States | Storage | Communication |
|-------|--------|---------|---------------|
| **PHP/Web** | `NowRacingState` (0/1) + Timer State (7 states) | RaceInfo table | AJAX polling (1 sec) |
| **Python Server** | `UNCONFIGURED/STOPPED/STAGING/RACING/FINISHED` | Memory | MQTT + HTTP |
| **Hardware Timers** | Ready/Toggle | MQTT topics | MQTT telemetry (1 sec) |

---

## Timer States (PHP)

```
TIMER_NOT_CONNECTED (1) - No recent contact from timer
TIMER_CONNECTED (2)     - Timer connected and idle
TIMER_STAGING (3)       - Heat ready, waiting for start
TIMER_RUNNING (4)       - Race in progress
TIMER_UNHEALTHY (5)     - Persistent malfunction
TIMER_SEARCHING (6)     - Connection in progress
TIMER_UNCONFIRMED (7)   - Timer identified but not verified
```

## Python Race Server States

```
RACE_STATE_UNCONFIGURED - API unavailable (LED: yellow)
RACE_STATE_STOPPED      - Race not active (LED: red)
RACE_STATE_STAGING      - Waiting for start (LED: blue)
RACE_STATE_RACING       - Race in progress (LED: green)
RACE_STATE_FINISHED     - All lanes complete (transient → STOPPED)
```

---

## LED Color Reference

| Color | State | Description |
|-------|-------|-------------|
| Red | STOPPED, Lane Finished | Race not active or lane crossed finish |
| Blue | STAGING (ready) | Toggle flipped, waiting for start |
| Green | RACING | Race in progress |
| Purple (flicker) | STAGING (not ready) | Toggle not flipped |
| Yellow | UNCONFIGURED | API unavailable or error |

---

## Timeout Configuration

Defined in `/website/inc/heartbeat-config.inc`:

| Constant | Value | Purpose |
|----------|-------|---------|
| `HEARTBEAT_INTERVAL` | 5s | Heartbeat send frequency |
| `TIMER_RECENT_THRESHOLD` | 5s | Max age for "recent" timer |
| `TIMER_STALE_THRESHOLD` | 8s | When to mark timer stale |
| `TIMER_DISCONNECT_THRESHOLD` | 15s | When PHP considers disconnected |
| `DEVICE_INACTIVE_THRESHOLD` | 30s | When to mark device inactive |
| `MIN_TIMERS_FOR_RACE` | 3 | Minimum finish timers required |

---

## State Flow

```
UNCONFIGURED (yellow LED)
      │ API available
      ▼
NOT_RACING (timer=CONNECTED, python=STOPPED)
      │ Coordinator sets now_racing=1
      ▼
STAGING (timer=STAGING, python=STAGING, blue LED)
      │
      ├─ Start Timer GO (MQTT) ──► RACING (confirmed, green LED)
      ├─ Manual Start (API) ─────► RACING (unconfirmed)
      └─ Timeout/Cancel ─────────► NOT_RACING
      │
      ▼
RACING ─► All lanes finish ─► FINISHED ─► Results written ─► NOT_RACING
```

---

## Lane Completion Guard

Once racing starts, the Python server **will not transition away from RACING** until:
1. All lanes finish (crossed line or marked DNF)
2. Race timeout (70s) with remaining lanes auto-DNF

**DNF Data Flow:**
1. Coordinator clicks DNF button
2. PHP sets `finishtime = 99.999` in RaceChart
3. Python polls API every second
4. Detects `finishtime >= 99.999`, calls `laneDNF()`
5. Race completes when all lanes finished

---

## Health Status

| Status | Condition |
|--------|-----------|
| `healthy` | All timers online and ready |
| `degraded` | Timer(s) offline, not racing |
| `warning` | Timer(s) not ready during staging |
| `critical` | Timer(s) offline during active race |

---

## Files Modified

### PHP
| File | Purpose |
|------|---------|
| `inc/heartbeat-config.inc` | Timeout constants |
| `inc/timer-state.inc` | Timer state machine |
| `inc/racing-state.inc` | Race integrity check |
| `inc/json-timer-state.inc` | Health status |
| `ajax/action.timer-message.inc` | Physical start tracking |

### Python
| File | Purpose |
|------|---------|
| `extras/soapbox/infra/server/derbyRace.py` | Race server, integrity |
| `extras/soapbox/infra/server/derbyapi.py` | API client |

### Frontend
| File | Purpose |
|------|---------|
| `js/coordinator-poll.js` | Health warning display |
| `css/coordinator.css` | Warning styles |

---

## Version History

- **v0.7.3** - DNF button integration (finishtime field in API)
- **v0.7.2** - LED color scheme (red=finished, purple=flip)
- **v0.7.1** - Stale race data cleanup on state transitions
- **v0.7.0** - Lane completion guard, dynamic lane count
- **v0.6.3** - UNCONFIGURED state, yellow LED
- **v0.6.2** - Initial race state integrity implementation

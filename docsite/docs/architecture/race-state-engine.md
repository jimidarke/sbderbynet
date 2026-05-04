# Race State Engine

State is tracked in three layers. The database is authoritative; the others cache.

| Layer | States | Storage | How it's read |
|---|---|---|---|
| PHP / Web | `NowRacingState` (0/1) plus 7-state Timer State | `RaceInfo` table | AJAX poll (≈1s) |
| Python race server | `UNCONFIGURED / STOPPED / STAGING / RACING / FINISHED` | in-memory | MQTT + HTTP |
| Hardware timers | `Ready / Toggle` per lane | MQTT topics | telemetry every 1s |

---

## Timer states (PHP)

```
TIMER_NOT_CONNECTED (1) — no recent contact
TIMER_CONNECTED     (2) — connected and idle
TIMER_STAGING       (3) — heat ready, waiting for start
TIMER_RUNNING       (4) — race in progress
TIMER_UNHEALTHY     (5) — persistent malfunction
TIMER_SEARCHING     (6) — connection in progress
TIMER_UNCONFIRMED   (7) — identified but not verified
```

## Race-server states (Python)

```
RACE_STATE_UNCONFIGURED  — API unavailable      (LED: yellow)
RACE_STATE_STOPPED       — race not active      (LED: red)
RACE_STATE_STAGING       — waiting for start    (LED: blue)
RACE_STATE_RACING        — race in progress     (LED: green)
RACE_STATE_FINISHED      — all lanes complete   (transient → STOPPED)
```

---

## LED colour key

| Colour | State | Meaning |
|---|---|---|
| Red | STOPPED / lane finished | race not running, or this lane has crossed |
| Blue | STAGING (ready) | toggle flipped, waiting for go |
| Green | RACING | race in progress |
| Purple (flicker) | STAGING (not ready) | toggle not flipped |
| Yellow | UNCONFIGURED | API down or error |

---

## Timeouts

!!! info "Source of truth"
    All timeout constants live in [`website/inc/heartbeat-config.inc`](https://github.com/anthropics/SBDerbyNet/blob/master/website/inc/heartbeat-config.inc). Update them there; everything else reads from that file.

| Constant | Value | What it does |
|---|---|---|
| `HEARTBEAT_INTERVAL` | 2s | how often Python sends heartbeats |
| `TIMER_RECENT_THRESHOLD` | 3s | max heartbeat age to count as recent (for `confirmed` flag) |
| `TIMER_STALE_THRESHOLD` | 5s | DB marks timer stale/not-ready |
| `TIMER_DISCONNECT_THRESHOLD` | 10s | PHP transitions timer to `NOT_CONNECTED` |
| `DEVICE_INACTIVE_THRESHOLD` | 20s | DeviceStatus marks device inactive |
| `FRONTEND_OFFLINE_THRESHOLD` | 5s | UI shows timer as offline |
| `MIN_TIMERS_FOR_RACE` | 3 | minimum finish timers required to start |
| `INTEGRITY_GRACE_PERIOD` | 3s | grace before flagging state-integrity issues |
| `ORPHAN_START_TIMEOUT` | 120s | retain orphan physical-start records this long |

The cascade should always read low → high: `HEARTBEAT_INTERVAL ≤ TIMER_RECENT_THRESHOLD < TIMER_STALE_THRESHOLD < TIMER_DISCONNECT_THRESHOLD < DEVICE_INACTIVE_THRESHOLD`.

---

## State flow

```
UNCONFIGURED (yellow)
   │ API available
   ▼
NOT_RACING (timer=CONNECTED, python=STOPPED)
   │ coordinator sets now_racing=1
   ▼
STAGING (timer=STAGING, python=STAGING, blue)
   │
   ├─ Start Timer GO (MQTT) ──► RACING (confirmed, green)
   ├─ Manual Start (API) ─────► RACING (unconfirmed)
   └─ Timeout / Cancel ───────► NOT_RACING
   │
   ▼
RACING  ──► all lanes finish ──► FINISHED ──► results written ──► NOT_RACING
```

---

## Lane-completion guard

Once `RACING` starts, the Python server will not transition away until **either**:

1. All lanes finish (crossed line or marked DNF), or
2. The race timeout (70s) elapses; remaining lanes auto-DNF.

### DNF data flow

1. Coordinator clicks DNF.
2. PHP sets `finishtime = 99.999` in `RaceChart`.
3. Python polls the API every second.
4. On `finishtime >= 99.999` it calls `laneDNF()`.
5. Race completes when all lanes have finished.

---

## Health status

`query=poll.coordinator` reports a `health_status` value used by the coordinator UI (see [Coordinator Poll API](../reference/coordinator-poll-api.md)):

| Status | Condition |
|---|---|
| `healthy` | all timers online and ready |
| `degraded` | timer(s) offline, not racing |
| `warning` | timer(s) not ready during staging |
| `critical` | timer(s) offline during active race |

---

## Files involved

**PHP**

- `website/inc/heartbeat-config.inc` — timeout constants
- `website/inc/timer-state.inc` — timer state machine
- `website/inc/racing-state.inc` — race integrity
- `website/inc/json-timer-state.inc` — health status
- `website/ajax/action.timer-message.inc` — physical-start tracking

**Python**

- `extras/soapbox/infra/server/derbyRace.py` — race server, integrity
- `extras/soapbox/infra/server/derbyapi.py` — API client

**Frontend**

- `website/js/coordinator-poll.js` — health warning display
- `website/css/coordinator.css` — warning styles

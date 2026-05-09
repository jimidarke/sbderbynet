# Start Timer — Recommended Hardware/Firmware Changes

Companion doc to commit `a97aa685` (`fix(starter): wire start-timer telemetry
into coordinator status panel`). That fix was **server-side only** —
deliberately so, to avoid an OTA round-trip on race-day hardware. The
ESP32 firmware in `src/main.py` keeps publishing the same MQTT payloads
it always has, and the Race Server now adapts on receive.

This list captures firmware changes that would be **nice to have** but
are not required for the coordinator status panel to work.

## Status: nothing required

The current firmware works. The Race Server identifies the start timer
by `hwid == "START"` (or the `starttimer` substring in the topic),
extracts the latched switch level from `payload_data["state"]` (1 = HIGH
= Active, 0 = LOW = Standby), and forwards it as a starter heartbeat to
PHP. No firmware change is needed for the coordinator to display
Online / Active / Standby with a live heartbeat age.

## Optional improvements (firmware-side)

If/when an OTA window opens, consider these:

### 1. Tighten telemetry interval (10 s → 1 s)

**File:** `src/main.py:364` — `telemetry_interval = 10`

Finish timers heartbeat every 1 s. The 10 s start-timer interval forced
a separate, more lenient `STARTER_FRONTEND_OFFLINE_THRESHOLD` (25 s) in
`website/inc/heartbeat-config.inc`. If the start timer matched the 1 s
cadence, the starter could share `FRONTEND_OFFLINE_THRESHOLD` and the
UI would react faster to power loss / WiFi drop. **Battery impact:**
publishes more often → shorter battery life. Measure before committing.

### 2. Publish `readyToRace` alongside `state`

**File:** `src/main.py:311-328` — `collect_telemetry()` payload

Add `'readyToRace': bool(start_signal.value())` to the telemetry dict.
This would let the Race Server use the same `payload_data.get("readyToRace", False)`
extraction path as the finish timers, removing the special-case branch
in `derbyRace._handle_message`. Keep `state` too — other consumers may
depend on it. Pure additive change, no breakage risk.

### 3. Tenant-scoped MQTT topics for cloud deployments

**File:** `src/main.py:69` — `MQTT_TOPIC = 'derbynet/device/starttimer'`

Commit `426d2bea` introduced tenant-scoped topics
(`derbynet/t/<slug>/device/...`) for cloud / multi-tenant deployments.
The start timer firmware was not updated. On Pi-mode / single-tenant
race-day hardware this is fine — `derbyRace.on_connect` still subscribes
to the unprefixed legacy topics. But a cloud-attached real start timer
would not be heard by the right tenant. Resolution path: add a tenant
slug to `/config.json` and prefix `MQTT_TOPIC` with `t/<slug>/` when set.

### 4. Replace the latched switch with a momentary one (mechanical)

The user noted: *"is-ready should show Standby (if LOW) and Active (if
HIGH) because it's latched which is dumb."* Software now labels the two
states meaningfully, but a momentary push-button (auto-resets after the
gate opens) would let the start timer behave like a normal arming
signal: ready/not-ready, then a brief HIGH pulse on activation. That
would obsolete the Active/Standby distinction and let the start timer
share the finish-timer ready-flag semantics end-to-end.

This is the only item on the list that requires touching the **physical
gate hardware**, not just the ESP32 firmware. Defer until off-season.

## Verification after any of the above

- `mosquitto_sub -h 192.168.100.10 -t 'derbynet/device/starttimer/#' -v` — confirm new payload shape / cadence
- Coordinator page Start Timer row — heartbeat age should tick at the new cadence
- `sqlite3 .../derbynet.sqlite3 "SELECT * FROM TimerStatus WHERE is_starter=1;"` — `last_heartbeat` should match the new cadence

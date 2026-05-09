# MQTT API

All race-day devices speak MQTT to the broker on `192.168.100.10:1883`. Topics are prefixed `derbynet/` followed by a category and identifiers.

Categories:

- `derbynet/race/...` — race-level events and state
- `derbynet/device/{id}/...` — device telemetry, status, control
- `derbynet/lane/{lane}/...` — lane-specific control
- `derbynet/ledsign/{zone}/...` — LED-sign content (see [LED Signs](../components/led-signs.md))
- `derbynet/alerts` — system-wide alerts

`{id}` is the device's hardware ID (`hwid`) — see [Hardware IDs](../architecture/hardware-ids.md). The start timer's `hwid` is hardcoded to `starttimer`; everything else is MAC-derived or read from `derbyid.txt`.

---

## Race topics

### `derbynet/race/state`

Current race state. **Publisher**: race server. **Subscribers**: all devices. **Format**: string (`STOPPED` / `STAGING` / `RACING`).

```
derbynet/race/state RACING
```

### `derbynet/race/event`

Race events (start, finish). **Publisher**: race server. **Subscribers**: timers, displays. **Format**: JSON.

```json
{
  "event": "race_start",
  "timestamp": 1715432587,
  "roundid": 3,
  "heatid": 12
}
```

---

## Device topics

### `derbynet/device/{id}/status`

Online/offline. **Publisher**: device. **Subscriber**: race server. **Format**: string. **Values**: `online` / `offline` / `updating`. **Flags**: retained, QoS 1, used as LWT (Last Will and Testament).

```
derbynet/device/L1/status online
```

### `derbynet/device/{id}/telemetry`

Health metrics. JSON. QoS 1, retained. Standard fields:

```json
{
  "hostname": "finishtimerL1",
  "hwid": "L1",
  "uptime": 3645,
  "ip": "192.168.100.101",
  "mac": "b8:27:eb:c3:d4:e5",
  "wifi_rssi": -67,
  "battery_level": 100,
  "cpu_temp": 42.3,
  "memory_usage": 14.7,
  "disk": 23.5,
  "cpu_usage": 1.2,
  "time": 1715432587,
  "pcbVersion": "1.0.0"
}
```

Devices may add their own fields (e.g. start timer adds DHT22 temp/humidity).

### `derbynet/device/{id}/state`

Device operational state. JSON.

Start timer:

```json
{ "state": "GO", "timestamp": 1715432587 }
```

Finish timer:

```json
{ "toggle": false, "timestamp": 1715432589, "dip": "1000" }
```

### `derbynet/device/{id}/update`

Trigger firmware update. **Publisher**: race server. Value: `update`.

```
derbynet/device/L1/update update
```

---

## Lane topics

### `derbynet/lane/{lane}/led`

LED control. **Publisher**: race server. **Subscriber**: finish timers. String. Values: `red`, `green`, `blue`, `purple`. QoS 2, retained.

```
derbynet/lane/1/led green
```

### `derbynet/lane/{lane}/pinny`

Racer-number display. **Publisher**: race server. **Subscriber**: displays + finish timers. String (4-digit). QoS 2, retained.

```
derbynet/lane/1/pinny 0042
```

---

## LED-sign topics

```
derbynet/ledsign/{zone}/message            # zone-specific content
derbynet/ledsign/broadcast                 # priority override
derbynet/ledsign/device/{mac}/update       # OTA trigger
```

Zones: `starter`, `usher-lane1..N`, `finish`, `registration`, `audience`. Payload is JSON with a `message` and a `display_config`. Full BetaBrite display options: [BetaBrite Protocol](betabrite-protocol.md).

---

## Alerts

### `derbynet/alerts`

System-wide alerts. **Publisher**: any component. **Subscriber**: race server, monitoring. JSON.

```json
{
  "timestamp": "2025-04-22T15:32:10Z",
  "service": "hlsfeed",
  "severity": "warning",
  "message": "HLS stream issue detected: error_no_new_segments"
}
```

---

## Conventions

- **Timestamps**: UTC Unix seconds. High-precision events include milliseconds as decimal.
- **Device identification**: every payload includes `hwid` and `hostname`.
- **QoS**: `0` for telemetry/status (acceptable to lose), `1` for state, `2` for race-critical (LED commands, finish events).
- **Retention**: status, LED, pinny topics are retained so a late-joining device sees current state immediately.

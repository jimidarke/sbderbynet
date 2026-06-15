# Derby Race System MQTT API

This document describes the MQTT topic structure and message formats used throughout the Soapbox Derby race management system.

## Two topic shapes: Pi (legacy) vs cloud (tenant-prefixed)

The topic shape depends on where the broker runs:

- **Pi / race-day stack** — topics are unprefixed: `derbynet/<category>/...`. Real
  timer firmware, the Pi race-server, and every existing kiosk talk on this
  shape. Nothing in this document changes for Pi deployments.
- **Cloud twin (uisp.darketech.ca)** — topics are tenant-prefixed:
  `derbynet/t/<slug>/<category>/...`. The `<slug>` is the per-session sandbox
  identifier (`$_SESSION['tenant_slug']`), validated against
  `^[a-z0-9][a-z0-9-]{0,31}$`. The cloud broker is shared by every sandbox;
  the prefix is what keeps one sandbox's race state from leaking into
  another's.

The body of this document describes the **legacy / Pi** shape. To translate to
the cloud shape, prepend `t/<slug>/` after the leading `derbynet/`. The race-server
selects shape at boot via `DERBYNET_TENANT_MODE` — `multi` for cloud,
unset/`single` for Pi.

For the design rationale (why three components must agree: browser bridge,
broker ACL, race-server router), see
[`docs/CLOUD_MULTI_TENANT.md`](../../../docs/CLOUD_MULTI_TENANT.md).

## Topic Structure

All topics use the prefix `derbynet/` (Pi) or `derbynet/t/<slug>/` (cloud)
followed by a category and specific identifiers.

### Core Categories

- `derbynet/race/`: Race-level events and state
- `derbynet/device/`: Device-level telemetry, status, and control
- `derbynet/lane/`: Lane-specific information and control

## Race Topics

### Race State

**Topic**: `derbynet/race/state`  
**Description**: Current race state  
**Publisher**: Derby Race server  
**Subscribers**: All devices  
**Format**: String  
**Values**: 
- `STOPPED` - No active race
- `STAGING` - Race is staged and ready for start
- `RACING` - Race is in progress

**Example**:
```
derbynet/race/state RACING
```

### Race Events

**Topic**: `derbynet/race/event`  
**Description**: Race events like start signals  
**Publisher**: Derby Race server  
**Subscribers**: Timers, displays  
**Format**: JSON  

**Example**:
```json
{
  "event": "race_start",
  "timestamp": 1715432587,
  "roundid": 3,
  "heatid": 12
}
```

## Device Topics

### Device Status

**Topic**: `derbynet/device/{id}/status`  
**Description**: Device online/offline status  
**Publisher**: Individual devices  
**Subscribers**: Derby Race server  
**Format**: String  
**Values**: `online`, `offline`, `updating`  
**Flags**: Retained, QoS 1, LWT (Last Will and Testament)  

**Example**:
```
derbynet/device/L1/status online
```

### Device Telemetry

**Topic**: `derbynet/device/{id}/telemetry`  
**Description**: Device health and status metrics  
**Publisher**: Individual devices  
**Subscribers**: Derby Race server  
**Format**: JSON  
**Flags**: QoS 1, Retained  

**Example**:
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

### Device State

**Topic**: `derbynet/device/{id}/state`  
**Description**: Device operational state  
**Publisher**: Individual devices  
**Subscribers**: Derby Race server  
**Format**: JSON  

**Examples**:

Start Timer:
```json
{
  "state": "GO",
  "timestamp": 1715432587
}
```

Finish Timer:
```json
{
  "toggle": false,
  "timestamp": 1715432589,
  "dip": "1000"
}
```

### Device Update

**Topic**: `derbynet/device/{id}/update`  
**Description**: Trigger device firmware update  
**Publisher**: Derby Race server  
**Subscribers**: Individual devices  
**Format**: String  
**Value**: `update`  

**Example**:
```
derbynet/device/L1/update update
```

## Lane Topics

### Lane LED Control

**Topic**: `derbynet/lane/{lane}/led`  
**Description**: Controls LED indicators for each lane  
**Publisher**: Derby Race server  
**Subscribers**: Finish timers  
**Format**: String  
**Values**: `red`, `green`, `blue`, `purple`  
**Flags**: QoS 2, Retained  

**Example**:
```
derbynet/lane/1/led green
```

### Lane Pinny Display

**Topic**: `derbynet/lane/{lane}/pinny`  
**Description**: Racer number for display  
**Publisher**: Derby Race server  
**Subscribers**: Displays, finish timers  
**Format**: String — 4-digit zero-padded racer number, or `"----"` for an empty
(bye) lane  
**Flags**: QoS 2, Retained  

**Example**:
```
derbynet/lane/1/pinny 0042
derbynet/lane/3/pinny ----      # bye lane (no racer this heat)
```

> The server refreshes **every physical lane** each heat (not just populated
> ones). A lane with no racer — a "bye" from a pull-forward withdrawal or an odd
> racer count — is published as `"----"` so the retained topic never leaves a
> stale number on the display. (Race server v0.9.3+.)

## Alert Topics

### System Alerts

**Topic**: `derbynet/alerts`  
**Description**: System-wide alerts and notifications  
**Publisher**: Any component detecting issues  
**Subscribers**: Derby Race server, monitoring systems  
**Format**: JSON  

**Example**:
```json
{
  "timestamp": "2025-04-22T15:32:10Z",
  "service": "hlsfeed",
  "severity": "warning",
  "message": "HLS stream issue detected: error_no_new_segments"
}
```

## Cloud worked example

Pi publish on the legacy topic:

```
derbynet/device/B_FINISH_1/state
{"toggle": false, "timestamp": 1715432589, "hwid": "B_FINISH_1", "dip": "1000", "lane": 1}
```

Same publish from a browser virtual finish-timer in the `acme` sandbox:

```
derbynet/t/acme/device/B_FINISH_1/state
{"toggle": false, "timestamp": 1715432589, "hwid": "B_FINISH_1", "dip": "1000", "lane": 1}
```

The **payload** is unchanged across shapes. Only the topic carries tenancy.
That keeps the race-server's per-message logic identical: in cloud mode the
router strips `derbynet/t/<slug>/` before dispatching to a per-tenant
`derbyRace` context; in Pi mode the legacy topic falls through directly.

## Cloud-specific topics

| Topic                                     | Direction | Notes                                              |
| ----------------------------------------- | --------- | -------------------------------------------------- |
| `derbynet/t/<slug>/race/state`            | server→all | Same payload as Pi `derbynet/race/state`           |
| `derbynet/t/<slug>/race/time`             | derbyTime→all | Fanned out per-tenant in multi mode             |
| `derbynet/t/<slug>/status`                | server | Per-tenant online/offline (server-level LWT remains on unscoped `derbynet/status`) |
| `derbynet/t/<slug>/alerts/<category>`     | server | Tenant-scoped alerts; payload identical to Pi     |
| `derbynet/t/<slug>/device/B_*/...`        | browser→server | Browser virtual hardware. ACL constrains the `virtual-device` user to the `B_`-prefixed hwid namespace under any slug. |

Real-hardware hwids (no `B_` prefix) are not permitted on the cloud broker —
the ACL rejects the publish, defending against a leaked browser cred
impersonating a Pi-side timer.

## Message Format Standards

### Device Identification

All devices should include:
- `hwid`: Hardware ID matching device registration
- `hostname`: Human-readable device name

### Timestamps

All timestamps should be:
- UTC Unix epoch time (seconds since Jan 1, 1970)
- For high-precision events, include milliseconds as decimal

### Telemetry Format

Standard telemetry includes:
- `hostname`: Device name
- `hwid`: Hardware ID
- `uptime`: Seconds since boot
- `ip`: IP address
- `mac`: MAC address
- `wifi_rssi`: Wi-Fi signal strength in dBm
- `battery_level`: Battery percentage (0-100)
- `cpu_temp`: CPU temperature in Celsius
- `memory_usage`: Memory utilization percentage
- `disk`: Disk utilization percentage
- `cpu_usage`: CPU utilization percentage
- `time`: UTC timestamp
- Device-specific metrics as needed
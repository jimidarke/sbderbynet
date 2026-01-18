# LED Sign Integration Plan for SBDerbyNet

**Version**: 1.3.0
**Date**: 2026-01-16
**Status**: Phase 1-3 Implemented - HTTP Discovery + MQTT Content Delivery

> **Changelog v1.3.0**: Implemented HTTP-based device discovery and configuration (mirrors kiosk pattern), MQTT now used only for content delivery after zone assignment. Added PHP admin dashboard, database schema, and updated ESP32 firmware.
>
> **Changelog v1.2.0**: Added single agnostic firmware architecture with MAC-based device discovery, server-side zone configuration via MQTT, and kiosk-like device mapping pattern.

---

## Executive Summary

This document outlines a comprehensive plan to integrate BetaBrite LED signs into the SBDerbyNet race management system. The integration leverages the existing MQTT infrastructure, ESP32 microcontrollers as WiFi-to-serial bridges, and the well-documented Alpha Protocol for BetaBrite sign communication.

### Goals

1. Provide real-time race status to race officials at key positions
2. Display racer information (pinny, name) at usher stations per lane
3. Show race results at the finish line
4. Enable emergency broadcast capability across all signs
5. Support sponsor advertising during idle periods
6. Integrate with existing alert and error notification system

---

## Decisions Made (2026-01-15)

The following decisions have been finalized based on stakeholder input:

| Decision Area | Choice | Rationale |
|---------------|--------|-----------|
| **Sign Hardware** | All signs identical model, standard one-line (7-8 LED high) | Consistent protocol, simplified development |
| **Lane Count** | Fixed at 3 lanes | Safety constraints, unlikely to change |
| **Name Format** | First name + Last initial (e.g., "JohnS") | Child-friendly, privacy-conscious |
| **Time Format** | `mm:ss.nnn` (e.g., "00:30.134") | No lane label needed - one sign per lane |
| **Expected Race Times** | ~30 seconds (±12s depending on track) | Informs display sizing |
| **Sponsor Config** | JSON file with: name, tagline, url (all optional) | Simple, no database UI needed initially |
| **Emergency Broadcast Authority** | Race Coordinator only | Single authority during race events |
| **Offline Sign Handling** | Local "connection lost" display + heartbeat monitoring with non-blocking warnings | Graceful degradation, no race interruption |
| **ESP32 Firmware** | Single agnostic firmware for all devices, MAC as unique ID | Flash once, configure via HTTP, no per-device customization |
| **Device Configuration** | Server-side via HTTP polling; unconfigured devices display MAC and await mapping | Identical to kiosk pattern, minimal on-device state |
| **WiFi Credentials** | Hardcoded in firmware (same as finish timers) | Consistent with existing edge devices |
| **Device Mapping UI** | PHP admin dashboard (`ledsign-dashboard.php`) with zone dropdowns | Implemented - mirrors kiosk dashboard |
| **Discovery Protocol** | HTTP polling (not MQTT) for device registration and configuration | Simpler, follows kiosk pattern, MQTT only for content |

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Sign Roles and Deployment Zones](#2-sign-roles-and-deployment-zones)
3. [MQTT Topic Design](#3-mqtt-topic-design)
4. [Message Formats](#4-message-formats)
5. [ESP32 Controller Design](#5-esp32-controller-design)
6. [Content Management](#6-content-management)
7. [Priority and Emergency System](#7-priority-and-emergency-system)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [Hardware Requirements](#9-hardware-requirements)
10. [Questions and Decisions Needed](#10-questions-and-decisions-needed)
11. [References](#11-references)

---

## 1. System Architecture

### 1.1 High-Level Architecture (HTTP Discovery + MQTT Content)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LED SIGN LIFECYCLE                                    │
│                                                                             │
│  1. DISCOVERY (HTTP)              2. CONFIGURATION (HTTP)                   │
│  ┌─────────┐                      ┌─────────────────────┐                   │
│  │  ESP32  │ ──GET /ledsign.php───►│   DerbyNet PHP      │                   │
│  │         │ ◄──{status:identify}─│   (192.168.100.10)  │                   │
│  └─────────┘                      └─────────────────────┘                   │
│       │                                    │                                │
│       │ Poll every 5s                      │ Admin assigns zone via         │
│       │                                    │ ledsign-dashboard.php          │
│       ▼                                    ▼                                │
│  ┌─────────┐                      ┌─────────────────────┐                   │
│  │  ESP32  │ ──GET poll.ledsign───►│   DerbyNet PHP      │                   │
│  │         │ ◄──{zone:"starter"}──│   (action.php)      │                   │
│  └─────────┘                      └─────────────────────┘                   │
│       │                                                                     │
│       │ 3. CONTENT DELIVERY (MQTT) - only after zone assigned               │
│       ▼                                                                     │
│  ┌─────────┐    subscribe: derbynet/ledsign/{zone}/message                  │
│  │  ESP32  │ ◄────────────────────────────────────────── MQTT Broker        │
│  │         │    subscribe: derbynet/ledsign/broadcast                       │
│  └─────────┘                                                                │
└─────────────────────────────────────────────────────────────────────────────┘

Key Components:
┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  DerbyNet PHP │  │  Admin Page   │  │  MQTT Broker  │  │  Race Server  │
│  (ledsign.php)│  │  (dashboard)  │  │  (mosquitto)  │  │  (Python)     │
│               │  │               │  │               │  │               │
│ Registration  │  │ Zone mapping  │  │ Content only  │  │ Race events   │
│ Config poll   │  │ Device list   │  │ (post-config) │  │ to LED signs  │
└───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘
```

**Key Principle:** HTTP for discovery/config (identical to kiosk pattern), MQTT only for real-time content delivery after zone assignment.

### 1.2 Integration Points

| Component | Direction | Integration Method |
|-----------|-----------|-------------------|
| Race Server | Outbound | Publishes race state, lane data, alerts |
| LED Sign Controller | Inbound | Subscribes to zone-specific topics |
| Alert Handler | Outbound | Routes critical alerts to LED pathway |
| PHP Backend | Outbound | New API endpoint for sponsor content |
| Coordinator UI | Outbound | Manual broadcast message interface |

### 1.3 Data Flow

```
Race Event Occurs (e.g., race staged)
         │
         ▼
DerbyRace Server (derbyRace.py)
         │
         ├─► Publishes to existing topics (derbynet/race/state)
         │
         └─► NEW: LED Sign Pathway in AlertHandler
                   │
                   ▼
             Determines relevant signs based on event type
                   │
                   ▼
             Publishes to: derbynet/ledsign/{zone}/message
                   │
                   ▼
             ESP32 Controller receives JSON message
                   │
                   ▼
             Translates to BetaBrite Alpha Protocol
                   │
                   ▼
             Serial TX to BetaBrite Sign
```

---

## 2. Sign Roles and Deployment Zones

### 2.1 Zone Definitions

| Zone ID | Role | Location | Primary Content |
|---------|------|----------|-----------------|
| `starter` | Race Official | Start Line | System status, GO/STOP readiness |
| `usher-lane1` | Lane 1 Usher | Lane 1 staging | Upcoming racer pinny + name |
| `usher-lane2` | Lane 2 Usher | Lane 2 staging | Upcoming racer pinny + name |
| `usher-lane3` | Lane 3 Usher | Lane 3 staging | Upcoming racer pinny + name |
| `finish-lane1` | Lane 1 Results | Finish Line Lane 1 | Race time (mm:ss.nnn) |
| `finish-lane2` | Lane 2 Results | Finish Line Lane 2 | Race time (mm:ss.nnn) |
| `finish-lane3` | Lane 3 Results | Finish Line Lane 3 | Race time (mm:ss.nnn) |
| `registration` | Public Info | Registration Booth | Sponsor ads, instructions |
| `audience` | General Audience | Viewing Area | Announcements, standings |
| `broadcast` | Emergency | All Signs | Emergency messages (reserved) |

**Note**: Total of 10 sign zones (1 starter + 3 usher + 3 finish + 1 registration + 1 audience + 1 broadcast virtual zone)

### 2.2 Zone Behavior Matrix

| Zone | Race Idle | Race Staging | Race Active | Race Finished | Emergency |
|------|-----------|--------------|-------------|---------------|-----------|
| `starter` | "SYSTEM READY" | "RACE STAGED - READY" | "RACE IN PROGRESS" | "RACE COMPLETE" | Override |
| `usher-laneN` | Sponsor ads | "#42 JohnS" | Current racer | Next racer | Override |
| `finish-laneN` | Sponsor ads | "LANE N READY" | Live time on finish | "00:30.134" (hold) | Override |
| `registration` | Sponsor rotation | Sponsor rotation | Sponsor rotation | Sponsor rotation | Override |
| `audience` | Standings/sponsors | Heat info | Race status | Results | Override |

### 2.3 Content Priority Levels

| Priority | Level | Duration | Override Behavior |
|----------|-------|----------|-------------------|
| 0 | Emergency | Until cleared | Overrides ALL zones immediately |
| 1 | Critical Alert | 60 seconds | Overrides current, returns to normal |
| 2 | Race Event | Event duration | Normal race operations |
| 3 | Sponsor/Idle | Configurable | Lowest priority, interrupted by higher |

---

## 3. MQTT Topic Design

### 3.1 New Topic Structure

Building on existing `derbynet/` prefix:

```
# Device-level topics (MAC address as identifier)
derbynet/ledsign/device/{MAC}/status      # Device online/offline (LWT)
derbynet/ledsign/device/{MAC}/identity    # Device self-identification
derbynet/ledsign/device/{MAC}/config      # Zone assignment from server
derbynet/ledsign/device/{MAC}/message     # Direct message to specific device
derbynet/ledsign/device/{MAC}/telemetry   # Device health metrics
derbynet/ledsign/device/{MAC}/update      # OTA update trigger

# Zone-level topics (after device is configured)
derbynet/ledsign/{zone}/message           # Content for all devices in zone

# Global topics
derbynet/ledsign/broadcast                # Emergency broadcast to ALL signs
derbynet/ledsign/sponsors/rotation        # Sponsor content rotation
```

### 3.2 Topic Specifications

#### Device Identity Topic

**Topic**: `derbynet/ledsign/device/{MAC}/identity`
**Description**: Device broadcasts its identity for discovery
**Publisher**: ESP32 LED Sign Controller
**Subscriber**: Race Server, Web Interface (for device mapping)
**Format**: JSON
**QoS**: 1
**Retained**: Yes (allows web interface to see devices on page load)

#### Device Config Topic

**Topic**: `derbynet/ledsign/device/{MAC}/config`
**Description**: Server assigns zone to device
**Publisher**: Race Server, Web Interface
**Subscriber**: ESP32 LED Sign Controller
**Format**: JSON
**QoS**: 1
**Retained**: Yes (device receives assignment on reconnect)

#### Device Status Topic

**Topic**: `derbynet/ledsign/device/{MAC}/status`
**Description**: Device online/offline status
**Publisher**: ESP32 LED Sign Controller
**Subscriber**: Race Server, Monitoring
**Format**: String (`online`, `offline`)
**QoS**: 1
**Retained**: Yes
**LWT**: Configured for `offline` on disconnect

#### Zone Message Topic

**Topic**: `derbynet/ledsign/{zone}/message`
**Description**: Delivers display messages to specific zone
**Publisher**: Race Server, LED Sign Pathway, Coordinator UI
**Subscriber**: ESP32 LED Sign Controller
**Format**: JSON
**QoS**: 1 (at least once)
**Retained**: Yes (ensures sign gets last message on reconnect)

#### Zone Status Topic

**Topic**: `derbynet/ledsign/{zone}/status`
**Description**: Sign controller online/offline status
**Publisher**: ESP32 LED Sign Controller
**Subscriber**: Race Server, Monitoring
**Format**: String (`online`, `offline`, `updating`)
**QoS**: 1
**Retained**: Yes
**LWT**: Configured for `offline` on disconnect

#### Broadcast Topic

**Topic**: `derbynet/ledsign/broadcast`
**Description**: Emergency messages to ALL signs simultaneously
**Publisher**: Race Server, Coordinator UI (authorized users only)
**Subscriber**: ALL ESP32 LED Sign Controllers
**Format**: JSON
**QoS**: 2 (exactly once - critical messages)
**Retained**: Yes

#### Sponsor Rotation Topic

**Topic**: `derbynet/ledsign/sponsors/rotation`
**Description**: Sponsor content for idle periods
**Publisher**: PHP Backend content manager
**Subscriber**: ESP32 controllers in applicable zones
**Format**: JSON array
**QoS**: 1
**Retained**: Yes

### 3.3 Topic Subscription Patterns

**All devices subscribe to these topics on boot (before zone assignment):**

| Topic | Purpose |
|-------|---------|
| `derbynet/ledsign/device/{MAC}/config` | Receive zone assignment |
| `derbynet/ledsign/device/{MAC}/message` | Direct messages to this device |
| `derbynet/ledsign/device/{MAC}/update` | OTA update trigger |
| `derbynet/ledsign/broadcast` | Emergency broadcasts |

**After zone assignment, device additionally subscribes to:**

| Assigned Zone | Additional Subscriptions |
|---------------|-------------------------|
| `starter` | `derbynet/ledsign/starter/message` |
| `usher-lane1` | `derbynet/ledsign/usher-lane1/message`, `derbynet/lane/1/pinny` |
| `usher-lane2` | `derbynet/ledsign/usher-lane2/message`, `derbynet/lane/2/pinny` |
| `usher-lane3` | `derbynet/ledsign/usher-lane3/message`, `derbynet/lane/3/pinny` |
| `finish-lane1` | `derbynet/ledsign/finish-lane1/message` |
| `finish-lane2` | `derbynet/ledsign/finish-lane2/message` |
| `finish-lane3` | `derbynet/ledsign/finish-lane3/message` |
| `registration` | `derbynet/ledsign/registration/message`, `derbynet/ledsign/sponsors/rotation` |
| `audience` | `derbynet/ledsign/audience/message`, `derbynet/ledsign/sponsors/rotation` |

---

## 4. Message Formats

### 4.1 Standard Message Format

All messages to LED signs follow this JSON structure:

```json
{
  "timestamp": 1705344000,
  "priority": 2,
  "title": "RACE STAGED",
  "message": "Heat 12 - Ready to start",
  "display_config": {
    "mode": "flash",
    "mode_code": "c",
    "color": "green",
    "color_code": "2",
    "character_set": "7high",
    "charset_code": "3",
    "position": "fill",
    "position_code": "0",
    "speed": 3,
    "speed_code": "\\027",
    "special_effect": null,
    "effect_code": null,
    "priority": false,
    "duration": 0
  },
  "zone": "starter",
  "source": "derbyrace-server"
}
```

### 4.2 Zone-Specific Message Examples

#### Starter Zone - System Ready

```json
{
  "timestamp": 1705344000,
  "priority": 2,
  "title": "SYSTEM READY",
  "message": "All timers online - Ready to race",
  "display_config": {
    "mode": "hold",
    "mode_code": "b",
    "color": "green",
    "color_code": "2",
    "character_set": "10high",
    "charset_code": "6",
    "position": "fill",
    "position_code": "0",
    "speed": 2,
    "speed_code": "\\026"
  },
  "zone": "starter"
}
```

#### Starter Zone - NOT Ready (Timer Offline)

```json
{
  "timestamp": 1705344000,
  "priority": 1,
  "title": "NOT READY",
  "message": "Lane 2 timer OFFLINE",
  "display_config": {
    "mode": "flash",
    "mode_code": "c",
    "color": "red",
    "color_code": "1",
    "character_set": "10high",
    "charset_code": "6",
    "position": "fill",
    "position_code": "0",
    "speed": 4,
    "speed_code": "\\030",
    "special_effect": "starburst",
    "effect_code": "7"
  },
  "zone": "starter"
}
```

#### Usher Zone - Racer Assignment

```json
{
  "timestamp": 1705344000,
  "priority": 2,
  "title": "NEXT",
  "message": "#42 JohnS",
  "display_config": {
    "mode": "hold",
    "mode_code": "b",
    "color": "green",
    "color_code": "2",
    "character_set": "7high",
    "charset_code": "3",
    "position": "fill",
    "position_code": "0",
    "speed": 2,
    "speed_code": "\\026"
  },
  "zone": "usher-lane1",
  "metadata": {
    "pinny": "42",
    "firstname": "John",
    "lastname": "Smith",
    "formatted_name": "JohnS",
    "class": "Ages 9-11"
  }
}
```

#### Finish Zone - Race Times (Per-Lane Signs)

Since each lane has its own dedicated finish sign, times are displayed individually:

```json
{
  "timestamp": 1705344000,
  "priority": 2,
  "title": "",
  "message": "00:30.134",
  "display_config": {
    "mode": "hold",
    "mode_code": "b",
    "color": "green",
    "color_code": "2",
    "character_set": "10high",
    "charset_code": "6",
    "position": "fill",
    "position_code": "0",
    "speed": 2,
    "speed_code": "\\026"
  },
  "zone": "finish-lane1",
  "metadata": {
    "lane": 1,
    "time_seconds": 30.134,
    "time_formatted": "00:30.134",
    "place": 2
  }
}
```

#### Registration Zone - Sponsor Ad

```json
{
  "timestamp": 1705344000,
  "priority": 3,
  "title": "",
  "message": "Thanks to our sponsor: ACME Racing - acme-racing.com",
  "display_config": {
    "mode": "scroll",
    "mode_code": "m",
    "color": "rainbow1",
    "color_code": "9",
    "character_set": "7highfancy",
    "charset_code": "5",
    "position": "midline",
    "position_code": " ",
    "speed": 2,
    "speed_code": "\\026"
  },
  "zone": "registration",
  "metadata": {
    "sponsor_id": "acme-001",
    "rotation_interval": 15
  }
}
```

#### Emergency Broadcast

```json
{
  "timestamp": 1705344000,
  "priority": 0,
  "title": "EMERGENCY",
  "message": "MISSING CHILD: BLUE SHIRT AGE 6 - Report to registration",
  "display_config": {
    "mode": "flash",
    "mode_code": "c",
    "color": "red",
    "color_code": "1",
    "character_set": "10high",
    "charset_code": "6",
    "position": "fill",
    "position_code": "0",
    "speed": 5,
    "speed_code": "\\031",
    "special_effect": "bomb",
    "effect_code": "Z",
    "priority": true
  },
  "zone": "broadcast",
  "source": "coordinator-emergency"
}
```

### 4.3 Sponsor Rotation Message Format

```json
{
  "timestamp": 1705344000,
  "sponsors": [
    {
      "id": "sponsor-001",
      "message": "Thanks to ACME Racing - acme-racing.com",
      "duration": 15,
      "display_config": {
        "mode": "scroll",
        "mode_code": "m",
        "color": "rainbow1",
        "color_code": "9"
      }
    },
    {
      "id": "sponsor-002",
      "message": "Local Pizza Co - Best pizza in town!",
      "duration": 12,
      "display_config": {
        "mode": "scroll",
        "mode_code": "m",
        "color": "amber",
        "color_code": "3"
      }
    }
  ],
  "default_duration": 15,
  "loop": true
}
```

---

## 5. ESP32 Controller Design

### 5.1 Design Philosophy

**Single Agnostic Firmware**: All LED sign controllers run identical firmware (v1.1.0+). The MAC address serves as the unique identifier. Zone assignment and configuration are managed server-side via HTTP polling, identical to kiosk device mapping.

**HTTP Discovery + MQTT Content**:
- ESP32 polls HTTP endpoints for registration and configuration (every 5 seconds)
- Once zone is assigned, ESP32 connects to MQTT for real-time content delivery
- This mirrors the kiosk pattern exactly

**Minimal On-Device State**: The ESP32 retains only:
- Hardcoded WiFi credentials (same as finish timers)
- Its own MAC address (read from hardware)
- Current assigned zone (received via HTTP, not persisted to flash)

**Server-Side Configuration**: DerbyNet PHP maintains:
- MAC address → Zone name mappings (in SQLite database `LedSigns` table)
- Zone-specific content and behavior
- Sponsor rotation content

### 5.2 Hardware Configuration

| Component | Purpose | GPIO/Connection |
|-----------|---------|-----------------|
| ESP32 DevKit | WiFi controller | N/A |
| Serial TX | BetaBrite data out | GPIO17 (TX2) |
| Serial RX | BetaBrite data in (optional) | GPIO16 (RX2) |
| Status LED | Connection status | GPIO2 (onboard) |
| MAX3232 | TTL to RS-232 level shifter | Between ESP32 and BetaBrite |

### 5.3 Serial Configuration

```cpp
#define BETABRITE_SERIAL Serial2
#define BETABRITE_BAUD 9600
#define BETABRITE_RX 16
#define BETABRITE_TX 17

void setup() {
  BETABRITE_SERIAL.begin(BETABRITE_BAUD, SERIAL_8N1, BETABRITE_RX, BETABRITE_TX);
}
```

### 5.4 Software Architecture (MicroPython)

Single firmware for all devices:

```
/
├── main.py           # Main application (identical on all devices)
├── betabrite.py      # BetaBrite protocol library
├── config.py         # Hardcoded WiFi credentials only
└── boot.py           # Boot configuration
```

### 5.5 Hardcoded Configuration (config.py v1.1.0)

```python
# WiFi credentials - same as other edge devices
WIFI_SSID = "DerbyNet"
WIFI_PASSWORD = "all4theKids"

# DerbyNet server for HTTP discovery/configuration
DERBYNET_SERVER = "192.168.100.10"
DERBYNET_PORT = 80
HTTP_REGISTER_ENDPOINT = "/ledsign.php"    # Registration and config
HTTP_POLL_ENDPOINT = "/action.php"          # Polling for updates
HTTP_POLL_INTERVAL = 5                      # Poll every 5 seconds

# MQTT broker (for content delivery after zone assignment)
DEFAULT_MQTT_BROKER = "192.168.100.10"
MQTT_PORT = 1883

# OTA update endpoint
OTA_BASE_URL = "http://192.168.100.10/ledsign"
```

**Note**: No zone-specific configuration on device. Zone assignment comes from HTTP polling, MQTT topics come from HTTP response.

### 5.6 Device States

| State | LED Sign Display | HTTP/MQTT Behavior |
|-------|------------------|-------------------|
| **UNCONFIGURED** | Shows MAC address (e.g., "SETUP:AABBCCDD") | Polls HTTP every 5s, awaits zone assignment |
| **CONFIGURED** | Shows zone content | MQTT connected, subscribed to zone topics |
| **OFFLINE** | "CONNECTION LOST" | WiFi disconnected, attempting reconnect |

### 5.7 ESP32 Firmware Flow (v1.1.0 - HTTP Discovery)

```
Boot
  │
  ├─► Connect WiFi (hardcoded credentials, exponential backoff)
  │
  ├─► Show "SETUP:XXXXXXXX" on sign (last 8 chars of MAC)
  │
  └─► Main Loop
        │
        ├─► HTTP POLLING (every 5 seconds)
        │     │
        │     ├─► If UNCONFIGURED:
        │     │     └─► GET /ledsign.php?mac={MAC}&ip={IP}&version={VER}
        │     │         └─► Response: {zone: null, status: "identify"}
        │     │             └─► Continue polling...
        │     │         └─► Response: {zone: "starter", mqtt_topics: {...}}
        │     │             └─► Zone assigned! → Connect to MQTT
        │     │
        │     └─► If CONFIGURED:
        │           └─► GET /action.php?query=poll.ledsign&mac={MAC}
        │               └─► Check for zone changes, update if needed
        │
        ├─► MQTT (only when zone assigned)
        │     │
        │     ├─► Connect to MQTT broker (from HTTP response)
        │     ├─► Subscribe: derbynet/ledsign/{zone}/message
        │     ├─► Subscribe: derbynet/ledsign/broadcast
        │     ├─► Subscribe: derbynet/ledsign/device/{MAC}/update (OTA)
        │     │
        │     ├─► On zone message received
        │     │     └─► Process and display on sign
        │     │
        │     ├─► On broadcast received (priority 0)
        │     │     └─► Override display immediately
        │     │
        │     └─► On update command received
        │           └─► Trigger OTA update
        │
        ├─► Check priority timeout
        │     └─► Return to normal display if expired
        │
        ├─► Send MQTT telemetry (every 30s, when connected)
        │
        ├─► Check WiFi connection
        │     └─► If lost: Display "CONNECTION LOST", attempt reconnect
        │
        └─► Feed watchdog
```

### 5.8 Identity Broadcasting

On connect (and periodically), each device publishes its identity:

**Topic**: `derbynet/ledsign/device/{MAC}/identity`

```json
{
  "mac": "AA:BB:CC:DD:EE:FF",
  "ip": "192.168.100.150",
  "version": "1.0.0",
  "uptime": 0,
  "configured": false,
  "zone": null,
  "timestamp": 1705344000
}
```

The web interface monitors this topic (wildcard subscribe to `derbynet/ledsign/device/+/identity`) to discover available devices for mapping.

### 5.9 Zone Assignment Flow (HTTP-Based)

```
Admin Dashboard                  DerbyNet PHP                ESP32 Device
(ledsign-dashboard.php)          (action.php)                (main.py)
     │                               │                            │
     │                               │      GET /ledsign.php      │
     │                               │◄────────────────────────────┤ Poll every 5s
     │                               │      {zone: null}          │
     │                               ├───────────────────────────►│ Device appears in dashboard
     │                               │                            │
     │  Admin selects zone dropdown  │                            │
     │  POST action=ledsign.assign   │                            │
     ├──────────────────────────────►│                            │
     │  mac=AA:BB:..., zone=starter  │                            │
     │                               │  (Zone saved to database)  │
     │                               │                            │
     │                               │      GET /ledsign.php      │
     │                               │◄────────────────────────────┤ Next poll (within 5s)
     │                               │      {zone: "starter",     │
     │                               │       mqtt_topics: {...}}  │
     │                               ├───────────────────────────►│
     │                               │                            │
     │                               │                            ├─► Store zone
     │                               │                            ├─► Connect to MQTT
     │                               │                            ├─► Subscribe to zone topic
     │                               │                            ├─► Display "ZONE: Start Line"
     │                               │                            │
```

### 5.10 Server-Side Device Registry (IMPLEMENTED)

DerbyNet PHP maintains device mappings in the SQLite database:

**Database Table**: `LedSigns`

```sql
CREATE TABLE LedSigns (
  mac VARCHAR(17) PRIMARY KEY,        -- 'AA:BB:CC:DD:EE:FF' format
  zone VARCHAR(50),                    -- Assigned zone (NULL = unassigned)
  ip_address VARCHAR(45),              -- Last known IP
  firmware_version VARCHAR(20),        -- Reported version
  last_contact INTEGER NOT NULL        -- Unix timestamp
);
```

**Zone Definitions**: Fixed zones defined in `website/inc/ledsign-zones.inc`

**PHP Files Implemented**:

| File | Purpose |
|------|---------|
| `website/ledsign.php` | ESP32 registration endpoint |
| `website/ajax/query.poll.ledsign.inc` | Individual sign polling |
| `website/ajax/query.poll.ledsign.all.inc` | Admin dashboard polling |
| `website/ajax/action.ledsign.assign.inc` | Zone assignment |
| `website/ledsign-dashboard.php` | Admin UI |
| `website/js/ledsign-dashboard.js` | Dashboard JavaScript |
| `website/inc/ledsigns.inc` | Core LED sign functions |
| `website/inc/ledsign-zones.inc` | Zone definitions |

**Admin Dashboard**: `http://derbynet-server/ledsign-dashboard.php`
- Shows all discovered signs with zone dropdowns
- Real-time polling (every 2 seconds)
- Zone assignment summary table

### 5.11 BetaBrite Protocol Library (betabrite.py)

Key functions needed:

```python
class BetaBrite:
    def __init__(self, serial, address='Z'):
        self.serial = serial
        self.address = address

    def send_command(self, command):
        """Send raw Alpha Protocol command"""
        pass

    def write_text(self, file_label, text, mode, color, charset, position, speed, effect=None):
        """Write text to a file label with display configuration"""
        pass

    def write_priority(self, text, mode, color, charset, position, speed, effect=None):
        """Write priority message (interrupts rotation)"""
        pass

    def cancel_priority(self):
        """Cancel priority message and return to rotation"""
        pass

    def set_run_sequence(self, sequence):
        """Set file playback sequence"""
        pass

    def clear_memory(self):
        """Clear sign memory"""
        pass
```

---

## 6. Content Management

### 6.1 Content Sources

| Content Type | Source | Update Frequency |
|--------------|--------|------------------|
| Race Status | Race Server | Real-time |
| Lane Assignments | Race Server | Per heat |
| Race Results | Race Server | Per race |
| System Alerts | Alert Handler | Real-time |
| Sponsor Ads | JSON config file (`sponsors.json`) | On boot / manual reload |
| Emergency Broadcasts | Coordinator UI (Race Coordinator only) | Manual trigger |

### 6.2 Sponsor Content Management (JSON Config)

Sponsors are managed via the `sponsors.json` configuration file located at `extras/ledsign/sponsors.json`.

> **Future Enhancement**: Move sponsor management to the web interface under Settings UI, near the folder selection parameters. This will provide a proper UX for adding/editing/removing sponsors without manual JSON editing. For initial implementation, JSON config is sufficient to validate core functionality.

#### Sponsor JSON Structure

```json
{
  "settings": {
    "default_duration": 15,
    "default_mode": "scroll",
    "default_color": "rainbow1",
    "loop": true,
    "shuffle": false
  },
  "sponsors": [
    {
      "id": "sponsor-001",
      "name": "ACME Racing Supplies",
      "tagline": "Everything you need to win!",
      "url": "acme-racing.com",
      "duration": 15,
      "enabled": true
    }
  ]
}
```

#### Sponsor Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier |
| `name` | string | No* | Sponsor name |
| `tagline` | string | No* | Short slogan or message |
| `url` | string | No* | Website URL (displayed without http://) |
| `duration` | integer | No | Display time in seconds (default: 15) |
| `enabled` | boolean | No | Set to `false` to hide without deleting |

*At least one of `name`, `tagline`, or `url` should be provided.

#### Generated Display Message

The ESP32 constructs the display message from available fields:

| Fields Present | Display Format |
|----------------|----------------|
| name only | "Thanks to ACME Racing Supplies" |
| name + tagline | "ACME Racing Supplies - Everything you need to win!" |
| name + url | "ACME Racing Supplies - acme-racing.com" |
| all three | "ACME Racing Supplies - Everything you need to win! - acme-racing.com" |
| tagline only | "Everything you need to win!" |
| url only | "Visit acme-racing.com" |

#### Loading Sponsors to ESP32

Option A: **Embedded in firmware** - Copy `sponsors.json` to ESP32 SPIFFS during deployment
Option B: **MQTT delivery** - Race server publishes to `derbynet/ledsign/sponsors/rotation` topic
Option C: **HTTP fetch** - ESP32 fetches from `http://192.168.100.10/ledsign/sponsors.json` on boot

### 6.3 Audience Wrangling Messages

Predefined messages for common announcements:

| Message ID | Display Text | Use Case |
|------------|--------------|----------|
| `register-here` | "REGISTRATION --> Follow signs to tent" | Direct to registration |
| `race-starting` | "Racing begins in 10 minutes!" | Race start warning |
| `food-available` | "Concessions open - Food & drinks available" | Food announcement |
| `restrooms` | "Restrooms located behind main tent" | Facility directions |
| `photos-available` | "Race photos available at photo booth" | Photo service |
| `lost-found` | "Lost & Found at registration desk" | Lost items |

### 6.4 Content Rotation Logic

For zones with idle content (registration, audience):

```
1. Check for active priority message (level 0-1)
   └─► If active and not expired, display it

2. Check for race-related content (level 2)
   └─► If race active, display race-appropriate content

3. Fall through to sponsor rotation (level 3)
   └─► Cycle through sponsor messages
   └─► Respect individual duration settings
   └─► Loop continuously
```

---

## 7. Priority and Emergency System

### 7.1 Priority Levels

| Level | Name | Behavior | Example |
|-------|------|----------|---------|
| 0 | EMERGENCY | Immediate override ALL signs, until manually cleared | Missing child |
| 1 | CRITICAL | Override zone, auto-expire after duration | Timer offline |
| 2 | RACE_EVENT | Normal race operations | Heat staged |
| 3 | IDLE | Lowest priority, background content | Sponsors |

### 7.2 Emergency Broadcast Flow

```
Emergency Trigger (Coordinator UI)
         │
         ▼
Publish to: derbynet/ledsign/broadcast
    │
    ├─► QoS 2 ensures delivery
    ├─► Retained message ensures late-connecting signs receive it
    │
    ▼
ALL ESP32 Controllers receive message
    │
    ├─► Immediately interrupt current display
    ├─► Display emergency message with flash/red
    ├─► Continue displaying until cleared
    │
    ▼
Clear Emergency (Coordinator UI)
    │
    ├─► Publish empty/clear message to broadcast topic
    └─► Signs return to normal zone content
```

### 7.3 Emergency UI in Coordinator Page (IMPLEMENTED)

**Status:** Complete - implemented in `website/coordinator.php`

The emergency broadcast UI replaces the old broadcast message section:

```
┌─────────────────────────────────────────────────────┐
│ ⚠️ No Active Emergency                              │  ← Status banner (green when safe)
├─────────────────────────────────────────────────────┤
│ 🚨 Emergency Broadcast:                 0/255 chars │
│ [Enter EMERGENCY message for all kiosks...]         │  ← Red-bordered input
│                                                      │
│        [🚨 BROADCAST EMERGENCY]                      │  ← Confirmation required
└─────────────────────────────────────────────────────┘

When emergency is active:
┌─────────────────────────────────────────────────────┐
│ ⚠️ EMERGENCY ACTIVE: Fire drill - evacuate building │  ← Pulsing red banner
├─────────────────────────────────────────────────────┤
│                                                      │
│        [✓ Clear Emergency]                          │  ← Requires confirmation
└─────────────────────────────────────────────────────┘
```

**Key Features:**
- Confirmation dialog before broadcasting (prevents accidents)
- 255 character limit with live counter
- Persists until explicitly cleared (no auto-expiry)
- Displays on ALL web kiosks immediately
- RED flashing banner on kiosks (20% height, persists until cleared)
- Synchronized with FCM push notifications (when SaaS API is connected)

**API Endpoints:**
- `POST action.php?action=emergency.broadcast` - Activate (requires CONTROL_RACE_PERMISSION)
- `POST action.php?action=emergency.clear` - Deactivate (requires CONTROL_RACE_PERMISSION)

**Storage:** `RaceInfo` table, key `emergency-broadcast`, JSON format

### 7.4 Alert Handler Integration

Modify `alerthandler.py` to include LED sign pathway:

```python
class AlertHandler:
    def __init__(self, mqtt_client):
        self.client = mqtt_client
        self.led_zones = ['starter']  # Zones that receive alerts

    def send_alert(self, code, message, context=None):
        # Existing alert logic...

        # NEW: Check if alert should go to LED signs
        if self._should_display_on_led(code):
            self._publish_to_led_signs(code, message, context)

    def _should_display_on_led(self, code):
        """Determine if error code warrants LED display"""
        # Hardware errors (3xx) go to starter sign
        return code.startswith('ERR-HW-3') or code.startswith('ERR-NET-3')

    def _publish_to_led_signs(self, code, message, context):
        """Publish alert to appropriate LED zones"""
        led_message = {
            "timestamp": int(time.time()),
            "priority": 1,
            "title": "ALERT",
            "message": message,
            "display_config": {
                "mode": "flash",
                "mode_code": "c",
                "color": "red",
                "color_code": "1",
                "character_set": "7high",
                "charset_code": "3",
                "position": "fill",
                "position_code": "0",
                "speed": 4,
                "speed_code": "\\030",
                "priority": True,
                "duration": 30
            },
            "zone": "starter",
            "source": "alerthandler"
        }
        self.client.publish(
            "derbynet/ledsign/starter/message",
            json.dumps(led_message),
            qos=1,
            retain=True
        )
```

---

## 8. Implementation Roadmap

### Phase 1: Foundation ✅ COMPLETE

**Objective**: Basic ESP32 to BetaBrite communication

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Create MicroPython BetaBrite library | ✅ `betabrite.py` implemented |
| 1.2 | Port starttimer ESP32 pattern for LED sign | ✅ `main.py` implemented |
| 1.3 | Test basic text display over serial | ✅ Working |
| 1.4 | Implement all display modes/colors/effects | ✅ Full library |
| 1.5 | Hardware assembly (ESP32 + MAX3232 + BetaBrite) | ✅ Test units built |

### Phase 2: HTTP Discovery + MQTT Content ✅ COMPLETE (v1.1.0)

**Objective**: HTTP-based device discovery (kiosk pattern), MQTT for content

| Task | Description | Status |
|------|-------------|--------|
| 2.1 | Implement HTTP registration endpoint | ✅ `ledsign.php` |
| 2.2 | Implement HTTP polling for config | ✅ `action.php?query=poll.ledsign` |
| 2.3 | Create SQLite database schema | ✅ `LedSigns` table |
| 2.4 | ESP32 HTTP polling for registration | ✅ `main.py` v1.1.0 |
| 2.5 | ESP32 MQTT connection after zone assignment | ✅ Content delivery only |
| 2.6 | Implement priority message handling | ✅ Priority queue with timeout |
| 2.7 | Add OTA update support | ✅ Remote firmware updates |
| 2.8 | Implement "CONNECTION LOST" display | ✅ Local error on WiFi disconnect |

### Phase 3: Admin Dashboard ✅ COMPLETE

**Objective**: Web UI for device discovery and zone mapping

| Task | Description | Status |
|------|-------------|--------|
| 3.1 | Create admin dashboard page | ✅ `ledsign-dashboard.php` |
| 3.2 | Implement zone dropdown assignment | ✅ Real-time zone selection |
| 3.3 | Add zone summary table | ✅ Shows all zones with assignments |
| 3.4 | Real-time polling (2s intervals) | ✅ `ledsign-dashboard.js` |
| 3.5 | Add navigation link from index.php | ✅ "LED Signs" button |
| 3.6 | Backend test script | ✅ `website/tests/test-ledsign-backend.sh` |

### Phase 4: Race Server Integration (NEXT)

**Objective**: Integrate LED signs into race event flow

| Task | Description | Status |
|------|-------------|--------|
| 4.1 | Add LED pathway to `derbyRace.py` | ⏳ Pending |
| 4.2 | Implement starter sign race state updates | ⏳ Pending |
| 4.3 | Implement usher sign lane assignments | ⏳ Pending |
| 4.4 | Implement finish sign race results | ⏳ Pending |
| 4.5 | Integrate with AlertHandler for errors | ⏳ Pending |
| 4.6 | Add telemetry/heartbeat monitoring | ⏳ Pending |

**Success Criteria**: Signs update automatically during race flow

### Phase 5: Content Management

**Objective**: Sponsor ads and audience content

| Task | Description | Status |
|------|-------------|--------|
| 5.1 | Implement sponsor JSON config loading | ⏳ Pending |
| 5.2 | Publish sponsors to MQTT on startup | ⏳ Pending |
| 5.3 | Implement sponsor rotation on ESP32 | ⏳ Pending |
| 5.4 | Build coordinator emergency broadcast UI | ✅ Complete (see 7.3) |

### Phase 6: Production Deployment

**Objective**: Field deployment and refinement

| Task | Description | Status |
|------|-------------|--------|
| 6.1 | Build production ESP32 units | ⏳ Pending |
| 6.2 | Create deployment documentation | ⏳ Pending |
| 6.3 | Field test at practice race event | ⏳ Pending |
| 6.4 | Refine timing and display parameters | ⏳ Pending |

---

## 9. Hardware Requirements

### 9.1 Per Sign Unit

| Component | Quantity | Purpose | Est. Cost |
|-----------|----------|---------|-----------|
| ESP32 DevKit V1 | 1 | WiFi controller | $8 |
| MAX3232 module | 1 | TTL to RS-232 converter | $3 |
| RJ12 cable/adapter | 1 | BetaBrite connection | $5 |
| 5V USB power supply | 1 | ESP32 power | $5 |
| Project enclosure | 1 | Weather protection | $10 |
| **Total per unit** | | | **~$31** |

### 9.2 System-Wide

| Component | Quantity | Purpose |
|-----------|----------|---------|
| BetaBrite LED signs | 9 | Display devices (1 starter + 3 usher + 3 finish + 1 registration + 1 audience) |
| ESP32 controller units | 9 | One per sign |
| WiFi network | 1 | DerbyNet race network |
| MQTT broker | 1 | Existing (192.168.100.10) |

**Total Hardware Cost Estimate**: ~$279 (9 units × $31 per unit)

### 9.3 Wiring Diagram

```
ESP32 DevKit          MAX3232 Module         BetaBrite Sign
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│             │      │             │      │             │
│  GPIO17 TX ─┼──────┼─► T1IN      │      │             │
│             │      │             │      │             │
│             │      │   T1OUT ────┼──────┼─► RX (Pin 4)│
│             │      │             │      │             │
│  GPIO16 RX ◄┼──────┼── R1OUT    │      │             │
│             │      │             │      │             │
│             │      │   R1IN  ◄───┼──────┼── TX (Pin 5)│
│             │      │             │      │             │
│  GND ───────┼──────┼── GND ──────┼──────┼── GND      │
│             │      │             │      │             │
│  5V/VIN ────┼──────┼── VCC      │      │             │
│             │      │             │      │             │
└─────────────┘      └─────────────┘      └─────────────┘
```

### 9.4 BetaBrite RJ12 Pinout

| Pin | Signal | Direction |
|-----|--------|-----------|
| 1 | GND | - |
| 2 | Not used | - |
| 3 | Not used | - |
| 4 | RX (data to sign) | Input |
| 5 | TX (data from sign) | Output |
| 6 | GND | - |

---

## 10. Questions and Decisions (RESOLVED)

All questions have been resolved. See **Decisions Made** section at the top of this document.

### 10.1 Technical Decisions (Resolved)

| Question | Decision |
|----------|----------|
| Sign Model Variations | All signs identical - consistent protocol |
| Display Size | Standard one-line (7-8 LED high) - testing to confirm exact capacity |
| Number of Lanes | Fixed at 3 lanes (safety constraints) |

### 10.2 Content Decisions (Resolved)

| Question | Decision |
|----------|----------|
| Sponsor Management | JSON config file (`sponsors.json`) |
| Racer Name Format | First name + Last initial: "JohnS" |
| Time Format | mm:ss.nnn format: "00:30.134" (one sign per lane, no lane label needed) |
| Idle Content | Sponsor rotation |

### 10.3 Operational Decisions (Resolved)

| Question | Decision |
|----------|----------|
| Emergency Access | Race Coordinator only (single authority) |
| Sign Failure Handling | Local "connection lost" display + heartbeat monitoring with non-blocking warnings (race continues) |
| Content Update | On boot + manual reload |

### 10.4 Remaining Items for Implementation

1. **Character Capacity Testing**: Determine exact character width of signs during Phase 1
2. **Power/Boot Strategy**: Decide if signs stay powered continuously or need fast boot
3. **Enclosure Design**: Determine outdoor exposure requirements for ESP32 units

---

## 11. References

### 11.1 Internal Documentation

- [BETABRITE.md](./BETABRITE.md) - Complete BetaBrite protocol reference
- [ESP32_BETABRITE_IMPLEMENTATION.md](./ESP32_BETABRITE_IMPLEMENTATION.md) - ESP32 implementation guide
- [MQTT_API.md](../soapbox/doc/MQTT_API.md) - Existing MQTT topic structure
- [derbyRace.py](../soapbox/infra/server/derbyRace.py) - Race server reference
- [starttimer main.py](../soapbox/infra/starttimer/src/main.py) - ESP32 MicroPython reference

### 11.2 External Resources

- [Alpha Sign Communications Protocol](https://www.alpha-american.com/support) - Official protocol documentation
- [tastewar/BetaBrite](https://github.com/tastewar/BetaBrite) - Arduino BetaBrite library
- [depili/betabrite](https://github.com/depili/betabrite) - Python BetaBrite implementation
- [ESP8266 BetaBrite WiFi](https://www.hackster.io/daveazcarate/my-old-betabrite-controlled-with-esp8266-4f8726) - WiFi integration example

### 11.3 Related SBDerbyNet Components

| Component | Relevance |
|-----------|-----------|
| `alerthandler.py` | Error notification integration |
| `derbynet.py` | MQTT client pattern, telemetry format |
| `error_codes.py` | Standardized error codes |
| `finishtimer.py` | Lane topic subscription pattern |

---

## Appendices

### Appendix A: Display Configuration Quick Reference

| Setting | Values | Notes |
|---------|--------|-------|
| mode | rotate, hold, flash, scroll, explode, etc. | See BETABRITE.md |
| color | red, green, amber, yellow, rainbow1, etc. | See BETABRITE.md |
| character_set | 5high, 7high, 10high, etc. | Size affects visibility |
| position | fill, topline, midline, botline | Fill for max visibility |
| speed | 1-5 | 1=slowest, 5=fastest |
| special_effect | twinkle, sparkle, snow, bomb, etc. | Optional enhancement |

### Appendix B: Race State to LED Display Mapping

| Race State | Starter Sign | Usher Signs | Finish Signs (per lane) |
|------------|--------------|-------------|-------------------------|
| UNCONFIGURED | "SYSTEM NOT READY" (red flash) | Sponsor rotation | Sponsor rotation |
| STOPPED | "READY FOR RACE" (green hold) | Sponsor rotation | Last results or sponsors |
| STAGING | "RACE STAGED - READY" (green flash) | "#42 JohnS" (green hold) | "LANE N READY" |
| RACING | "RACE IN PROGRESS" (amber scroll) | Current racer | Live time on finish trigger |
| FINISHED | "RACE COMPLETE" (green hold) | Next racer or sponsors | "00:30.134" (hold until next race) |

### Appendix C: Error Code to LED Alert Mapping

| Error Code | Alert Message | Display Style |
|------------|---------------|---------------|
| ERR-HW-301 | "LANE X TIMER OFFLINE" | Red flash, 30s |
| ERR-HW-302 | "START TIMER OFFLINE" | Red flash, 30s |
| ERR-NET-301 | "NETWORK ERROR" | Red flash, 60s |
| ERR-RACE-301 | "TIMING SYSTEM ERROR" | Red flash, 60s |

### Appendix D: Name and Time Formatting Functions

#### Name Formatting (FirstnameL format)

```python
def format_racer_name(firstname: str, lastname: str) -> str:
    """Format racer name as 'JohnS' (firstname + last initial)"""
    if not firstname:
        return lastname[0].upper() if lastname else "?"
    if not lastname:
        return firstname.capitalize()
    return f"{firstname.capitalize()}{lastname[0].upper()}"

# Examples:
# format_racer_name("john", "smith") -> "JohnS"
# format_racer_name("MARY", "JONES") -> "MaryJ"
# format_racer_name("billy-bob", "thornton") -> "Billy-bobT"
```

#### Time Formatting (mm:ss.nnn format)

```python
def format_race_time(seconds: float) -> str:
    """Format race time as 'mm:ss.nnn' (e.g., '00:30.134')"""
    if seconds >= 99.999:  # DNF marker
        return "DNF"
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes:02d}:{remaining_seconds:06.3f}"

# Examples:
# format_race_time(30.134) -> "00:30.134"
# format_race_time(65.789) -> "01:05.789"
# format_race_time(5.5)    -> "00:05.500"
# format_race_time(99.999) -> "DNF"
```

---

**Document Status**: Phases 1-3 Complete - HTTP Discovery + Admin Dashboard Implemented
**Next Steps**: Phase 4 - Race Server Integration (connect LED signs to race event flow)

# Architecture Overview

SBDerbyNet is three things stacked on top of each other:

1. A **PHP web application** (forked from DerbyNet) that owns the SQLite race database, schedules heats, runs registration, and serves coordinator/kiosk/admin UI.
2. A **race server** (Python) that coordinates hardware via MQTT and writes results back to the database.
3. A fleet of **embedded devices** — finish timers (Pi Zeros), a start timer (ESP32), display kiosks (Raspberry Pis), and LED signs (ESP32 + BetaBrite serial drivers).

A **cloud twin** mirrors the Pi for rehearsal and audience-facing replay.

![Architecture diagram — TODO screenshot](../images/placeholder-architecture.png)

---

## Component map

| Component | Hardware | Lives at | Talks |
|---|---|---|---|
| Web App | Pi 4/5 | `192.168.100.10:80` | HTTP (browser), SQLite (local), MQTT (subscribe) |
| Race Server | Pi 4/5 (same box) | localhost daemon | MQTT (broker), HTTP→PHP, direct SQLite |
| MQTT Broker | Mosquitto on race Pi | `192.168.100.10:1883` | — |
| Finish Timers (×3) | Pi Zero W V1.1 | `192.168.100.21–23` | MQTT |
| Start Timer | ESP32 | DHCP on race subnet | MQTT (over WiFi) |
| Derby Display kiosks | Pi 4 + HDMI | DHCP | MQTT, HTTP (browser to PHP) |
| LED Signs | ESP32 + BetaBrite | DHCP | MQTT (config), HTTP (discovery) |
| HLS Feed | Pi or NUC | DHCP | RTSP (cameras) → HLS over HTTP |
| Cloud Twin | VPS (`uisp.darketech.ca`) | external | HTTPS only, snapshot pull |
| Flutter App | phones | external | HTTPS to cloud twin |

---

## Three sources of state, one source of truth

The SQLite database on the race Pi is the **single source of truth**. Hardware reports state by writing to it (directly, for performance) or via the PHP HTTP API (fallback).

But state is also cached in memory in the Python race server (for MQTT coordination) and reflected in PHP session/AJAX polling (for the coordinator UI). When these disagree, the database wins. Drift between layers is the most common class of bug — see [Race State Engine](race-state-engine.md).

---

## Why this shape

- **Local-first**: Race-day operates on the Pi alone, no internet required. The cloud twin never touches the race Pi during operations.
- **MQTT for hardware**: cheap, low-latency, lossy-tolerant. Devices reconnect automatically and queue locally on disconnect.
- **SQLite, not Postgres**: race-day infrastructure is a single Pi. SQLite (in WAL mode) handles the load; one fewer service to fail.
- **Per-device firmware identical**: all finish timers run the same image; lane is set by physical DIP switches. Same with LED signs and zone.

---

## Where to go next

- [Race State Engine](race-state-engine.md) — how PHP, Python, and hardware agree (or disagree)
- [Network](network.md) — the `192.168.100.0/24` subnet and the wifi bridge
- [Hardware IDs](hardware-ids.md) — MAC-derived, file-based, and the one hardcoded exception
- [MQTT API](../reference/mqtt-api.md) — topic patterns and payloads

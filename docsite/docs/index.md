# SBDerbyNet

Soapbox-derby race-management system. A heavily-modified fork of [DerbyNet](https://derbynet.org) with hardware infrastructure (MQTT-coordinated timers, kiosk displays, LED signs), elimination tournaments, broadcast messaging, and a cloud twin for rehearsal.

---

## What's where

| If you want to... | Start here |
|---|---|
| Understand the system end-to-end | [Architecture → Overview](architecture/overview.md) |
| Run race-day, deploy, or recover | [Operations](operations/dress-rehearsal.md) |
| Look up a specific feature (pull-forward, eliminations) | [Features](features/pull-forward.md) |
| Set up a piece of hardware | [Components](components/race-server.md) |
| Find an MQTT topic or API endpoint | [Reference → MQTT API](reference/mqtt-api.md) |
| Understand the test plan | [Development → Testing](development/testing.md) |

![System overview — TODO screenshot](images/placeholder-system-overview.png)

---

## The 60-second mental model

- **One race-day Pi** (`192.168.100.10`) runs everything: PHP web app, SQLite database, MQTT broker, race server.
- **Devices** (finish timers, start timer, displays, LED signs) talk MQTT to the broker over an isolated `192.168.100.0/24` subnet. A WiFi extender bridge spans the start line and the finish line — see [Network](architecture/network.md).
- **Cloud twin** at `uisp.darketech.ca` mirrors the Pi for dress rehearsals and audience-facing replay. Pi pushes a SQLite snapshot upstream on a cron.
- **State** lives in three layers (PHP / Python / hardware) that have to agree. See [Race State Engine](architecture/race-state-engine.md).

---

## Conventions

- Round names start with a number (sorts correctly).
- All hardware uses MAC-derived IDs unless explicitly hardcoded — see [Hardware IDs](architecture/hardware-ids.md).
- MQTT topics follow `derbynet/{category}/{id}/{type}`.
- The race subnet is real; the cloud lives separately and never touches race-day operations.

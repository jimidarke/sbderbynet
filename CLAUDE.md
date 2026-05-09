# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project Overview

SBDerbyNet is a soapbox derby race management system built by extensively modifying DerbyNet (originally for Pinewood Derby). It adds hardware infrastructure (MQTT-coordinated timers, displays, LED signs), elimination tournaments, broadcast messaging, and professional kiosk displays while maintaining full backward compatibility with the original DerbyNet.

**Version**: 1.0.0 | **License**: MIT | **Original**: [DerbyNet](https://derbynet.org)

## Component Map

| Component | Directory | Tech | CLAUDE.md |
|-----------|-----------|------|-----------|
| Web Application | `website/` | PHP, SQLite, jQuery | [website/CLAUDE.md](website/CLAUDE.md) |
| Soapbox Infrastructure | `extras/soapbox/` | Python, MQTT | [extras/soapbox/CLAUDE.md](extras/soapbox/CLAUDE.md) |
| Race Server | `extras/soapbox/infra/server/` | Python, MQTT | [extras/soapbox/infra/server/CLAUDE.md](extras/soapbox/infra/server/CLAUDE.md) |
| Finish Timer | `extras/soapbox/infra/finishtimer/` | Python, GPIO | [extras/soapbox/infra/finishtimer/CLAUDE.md](extras/soapbox/infra/finishtimer/CLAUDE.md) |
| Start Timer | `extras/soapbox/infra/starttimer/` | MicroPython, ESP32 | [extras/soapbox/infra/starttimer/CLAUDE.md](extras/soapbox/infra/starttimer/CLAUDE.md) |
| Derby Display | `extras/soapbox/infra/derbydisplay/` | Python, Chromium | [extras/soapbox/infra/derbydisplay/CLAUDE.md](extras/soapbox/infra/derbydisplay/CLAUDE.md) |
| HLS Video Feed | `extras/soapbox/hlsfeed/` | FFmpeg, Nginx | [extras/soapbox/hlsfeed/CLAUDE.md](extras/soapbox/hlsfeed/CLAUDE.md) |
| LED Signs | `extras/ledsign/` | MicroPython, ESP32 | [extras/ledsign/CLAUDE.md](extras/ledsign/CLAUDE.md) |
| Flutter App | `extras/flutterapp/` | Flutter/Dart | [extras/flutterapp/CLAUDE.md](extras/flutterapp/CLAUDE.md) |
| SaaS Backend | `extras/saasbox/` | FastAPI, Docker | [extras/saasbox/CLAUDE.md](extras/saasbox/CLAUDE.md) |
| Pi Deployment | `extras/derbypi/` | Ansible, Bash | [extras/derbypi/CLAUDE.md](extras/derbypi/CLAUDE.md) |
| Test Suite | `testing/` | Bash, Puppeteer | [testing/CLAUDE.md](testing/CLAUDE.md) |
| Timer (Legacy Java) | `timer/` | Java, Ant | [timer/CLAUDE.md](timer/CLAUDE.md) |

## Architecture

- **Database**: SQLite (single source of truth, WAL mode in production)
- **Messaging**: MQTT via Mosquitto broker (`192.168.100.10:1883`) for all device coordination
- **State Engine**: Race state spans PHP (NowRacingState), Python (Race Server states), and hardware (timer states). See [docs/RACINGSTATEENGINE.md](docs/RACINGSTATEENGINE.md)
- **Network**: Isolated `192.168.100.x` subnet for race-day operations

## Global Conventions

- Round names must start with a number for proper sequencing
- Tournament configurations use JSON files in `website/inc/elimination-configs/`
- All hardware devices use MAC-derived hardware IDs
- MQTT topics follow `derbynet/{category}/{id}/{type}` pattern

## Development

- **Build**: `ant generated` (generates version info)
- **Test**: `cd testing/ && ./test-basic-racing.sh`
- **Docker**: `docker run -p 80:80 -v /data:/var/lib/derbynet jeffpiazza/derbynet_server`
- **Production DB access**: See [docs/PRODUCTION_ACCESS.md](docs/PRODUCTION_ACCESS.md)

## Key Cross-Cutting Docs

- [docs/RACINGSTATEENGINE.md](docs/RACINGSTATEENGINE.md) — State machine across PHP, Python, and hardware
- [docs/COORDINATOR_POLL_API.md](docs/COORDINATOR_POLL_API.md) — Coordinator polling API specification
- [docs/ROUNDSETUP.md](docs/ROUNDSETUP.md) — Round system and database schema
- [docs/CICD.md](docs/CICD.md) — CI/CD pipeline and deployment strategy
- [docs/PULL_FORWARD.md](docs/PULL_FORWARD.md) — Mid-event schedule adjustment system
- [docs/PULL_FORWARD_OPERATOR.md](docs/PULL_FORWARD_OPERATOR.md) — Race-day operator card for pull-forward
- [docs/DRESS_REHEARSAL.md](docs/DRESS_REHEARSAL.md) — Cloud + Pi rehearsal runbook and race-day go/no-go
- [docs/PHONE_USAGE.md](docs/PHONE_USAGE.md) — Phone scope: standard pages only, never a control surface
- [docs/VPS_OPERATIONS.md](docs/VPS_OPERATIONS.md) — Cloud VPS interaction protocol via `scripts/derbyvps.sh`
- [docs/LOGGING.md](docs/LOGGING.md) — Where every server-side log lands; `derbyvps.sh logs --where` prints the live map
- [docs/TESTING.md](docs/TESTING.md) — Test-case proposal: priorities, what each one would catch, where to start

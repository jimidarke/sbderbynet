# SBDerbyNet: Soapbox Derby Race Management System

![SBDerbyNet](https://raw.githubusercontent.com/jeffpiazza/derbynet/master/website/img/derbynet-300.png)

SBDerbyNet is a race management system for children's soapbox derby events, built by extensively modifying the original [DerbyNet](https://derbynet.org) software. It adds MQTT-coordinated hardware infrastructure, elimination tournaments, broadcast messaging, professional kiosk displays, and live video streaming while maintaining full backward compatibility.

**Version: 1.0.0** | **License: MIT** | **Original: [DerbyNet](https://github.com/jeffpiazza/derbynet)**

---

## Key Enhancements Over DerbyNet

- **~40 new files** in hardware infrastructure (`extras/soapbox/`) — race server, finish/start timers, displays, video streaming
- **Critical scheduling engine fix** — corrected `n_times_per_lane` parameter interpretation that generated wrong race counts
- **Elimination tournament system** — JSON-configured formats with 3 new database tables, automatic progression, professional kiosk displays
- **MQTT messaging architecture** — real-time coordination between all hardware components
- **Broadcast messaging** — instant announcements and emergency alerts across all displays and LED signs
- **LED sign integration** — BetaBrite signs controlled via ESP32, zone-based architecture, priority messaging

---

## System Architecture

| Component | Directory | Description |
|-----------|-----------|-------------|
| Web Application | [`website/`](website/CLAUDE.md) | PHP/SQLite race management UI |
| Race Server | [`extras/soapbox/infra/server/`](extras/soapbox/infra/server/CLAUDE.md) | Python MQTT orchestration hub |
| Finish Timer | [`extras/soapbox/infra/finishtimer/`](extras/soapbox/infra/finishtimer/CLAUDE.md) | Raspberry Pi lane detection |
| Start Timer | [`extras/soapbox/infra/starttimer/`](extras/soapbox/infra/starttimer/CLAUDE.md) | ESP32 gate-open detection |
| Derby Display | [`extras/soapbox/infra/derbydisplay/`](extras/soapbox/infra/derbydisplay/CLAUDE.md) | Pi kiosk display service |
| HLS Video Feed | [`extras/soapbox/hlsfeed/`](extras/soapbox/hlsfeed/CLAUDE.md) | RTSP-to-HLS streaming |
| LED Signs | [`extras/ledsign/`](extras/ledsign/CLAUDE.md) | BetaBrite sign control |
| Flutter App | [`extras/flutterapp/`](extras/flutterapp/CLAUDE.md) | Mobile app (Phase 1) |
| SaaS Backend | [`extras/saasbox/`](extras/saasbox/CLAUDE.md) | Cloud features (pre-launch) |
| Pi Deployment | [`extras/derbypi/`](extras/derbypi/CLAUDE.md) | Ansible-based Pi bootstrap |
| Timer (Legacy) | [`timer/`](timer/CLAUDE.md) | Java timer bridge |
| Test Suite | [`testing/`](testing/CLAUDE.md) | Bash + Puppeteer tests |

---

## Quick Start

### Docker (Recommended)

```bash
# Build
sudo apt-get install ant && ant generated

# Run
docker run --detach -p 80:80 -p 443:443 \
  --volume /path/to/data:/var/lib/derbynet \
  --mount type=bind,src=$(pwd)/website,target=/var/www/html,readonly \
  jeffpiazza/derbynet_server
```

### Cloud Deployment (Docker Compose + SSL)

```bash
cd installer/docker-cloud
cp .env.example .env   # Edit with your domain
docker-compose up -d --build
```

See [installer/docker-cloud/README.md](installer/docker-cloud/README.md) for details.

### Raspberry Pi (Full Hardware Stack)

See [extras/derbypi/CLAUDE.md](extras/derbypi/CLAUDE.md) for one-command bootstrap.

### Initial Configuration

1. Navigate to `http://your-server-ip/setup.php`
2. Create or select database
3. Import racers or generate fake roster for testing
4. Configure timer connections and display assignments

---

## System Requirements

**Core**: PHP 7.0+, SQLite, modern web browser

**Hardware** (optional): Raspberry Pi 3B+, ESP32, Mosquitto MQTT broker, HDMI displays, RTSP cameras

**Network**: Isolated `192.168.100.x` subnet recommended, MQTT broker at `192.168.100.10`

---

## Documentation Index

### Technical References
- [docs/RACINGSTATEENGINE.md](docs/RACINGSTATEENGINE.md) — State machine across PHP, Python, and hardware
- [docs/COORDINATOR_POLL_API.md](docs/COORDINATOR_POLL_API.md) — Coordinator polling API
- [docs/ROUNDSETUP.md](docs/ROUNDSETUP.md) — Round system and database schema
- [docs/DATABASE_SCHEMA_VALIDATION.md](docs/DATABASE_SCHEMA_VALIDATION.md) — Elimination tournament schema
- [docs/ELIMINATION_CONFIG_VALIDATION.md](docs/ELIMINATION_CONFIG_VALIDATION.md) — Config editor field mappings
- [docs/PULL_FORWARD.md](docs/PULL_FORWARD.md) — Mid-event schedule adjustment
- [docs/CICD.md](docs/CICD.md) — CI/CD pipeline and deployment

### Infrastructure
- [extras/soapbox/doc/MQTT_API.md](extras/soapbox/doc/MQTT_API.md) — MQTT message protocol
- [extras/soapbox/doc/DERBYNET_REFERENCE.md](extras/soapbox/doc/DERBYNET_REFERENCE.md) — System technical reference
- [extras/soapbox/doc/HLS_REPLAY_DOCUMENTATION.md](extras/soapbox/doc/HLS_REPLAY_DOCUMENTATION.md) — Video replay system

### Setup Guides
- [extras/soapbox/infra/server/RASPBERRY_PI_SETUP.md](extras/soapbox/infra/server/RASPBERRY_PI_SETUP.md) — Pi server setup
- [extras/soapbox/hlsfeed/MULTICAM_SETUP.md](extras/soapbox/hlsfeed/MULTICAM_SETUP.md) — Multi-camera streaming
- [docs/PRODUCTION_ACCESS.md](docs/PRODUCTION_ACCESS.md) — Production database access via SFTP

### Business
- [docs/business/COMMERCIALIZATION.md](docs/business/COMMERCIALIZATION.md) — SaaSBox business model
- [docs/business/ENTERPRISE_ROADMAP.md](docs/business/ENTERPRISE_ROADMAP.md) — Enterprise readiness roadmap

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. Run `cd testing/ && ./test-basic-racing.sh` before submitting changes.

---

## Credits

Built on [DerbyNet](https://derbynet.org) by Jeff Piazza. Released under the MIT License — see `MIT-LICENSE.txt`.

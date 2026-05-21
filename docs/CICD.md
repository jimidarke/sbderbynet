# CI/CD Strategy

Development and testing infrastructure on a cloud VPS, separate from the race-day Raspberry Pi.

**Architecture principle:** The Pi is the race-day master. The cloud VPS is for development, testing, and CI/CD only. It has no race-day role.

## Architecture Overview

```
═══════════════════════════════════════════════════════════════
  RACE DAY (Raspberry Pi - 192.168.100.x)    AUTHORITATIVE
═══════════════════════════════════════════════════════════════
  DerbyNet PHP + SQLite, Race Server, Mosquitto MQTT
  All hardware (timers, displays, LED signs)
  Deployed via Ansible auto-pull from GitHub (extras/derbypi/)
  
═══════════════════════════════════════════════════════════════
  DEVELOPMENT (Cloud VPS)                    DEV / TEST ONLY
═══════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────┐
│                     LOCAL DEVELOPMENT                        │
│  Docker Compose with build context                          │
│  cd installer/docker-cloud && docker compose up -d --build  │
│  Access at http://localhost/derbynet/                        │
└─────────────────────────────────────────────────────────────┘
                             │
                      git push develop / master
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     GITHUB ACTIONS                           │
│                                                              │
│  .github/workflows/test.yml (all PRs + pushes):             │
│    → Build Docker images                                    │
│    → Start full stack in CI                                 │
│    → Run test suite + race simulation                       │
│                                                              │
│  .github/workflows/deploy.yml (develop + master):           │
│    → Build Docker images                                    │
│    → Push to ghcr.io                                        │
│    → SSH deploy to VPS                                      │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    VULTR VPS                                 │
│                                                              │
│  ┌─────────────────────┐    ┌─────────────────────┐        │
│  │  STAGING            │    │  PRODUCTION         │        │
│  │  :8080 or subdomain │    │  :80 / :443         │        │
│  │  Image tag: develop │    │  Image tag: latest  │        │
│  └─────────────────────┘    └─────────────────────┘        │
│                                                              │
│  Caddy reverse proxy (automatic HTTPS via Let's Encrypt)    │
│  Mosquitto MQTT (internal only, not exposed)                │
│  Docker volumes persist test data across deploys            │
└─────────────────────────────────────────────────────────────┘
```

## Workflow Summary

| Scenario | Action | Result |
|----------|--------|--------|
| Quick testing | `docker compose up -d --build` locally | Instant local stack |
| Ready for review | `git push origin develop` | Auto-deploys to staging |
| Ready for production | Merge develop → master | Auto-deploys to VPS production |
| Emergency hotfix | Push directly to master | Auto-deploys (use sparingly) |
| Run tests | Open a PR | Tests run automatically in CI |
| Race day Pi update | Ansible auto-pull (every 30 min) | Pi pulls from master |

## Local Development

```bash
cd installer/docker-cloud

# First time: set up MQTT auth and env
cp .env.example .env
./scripts/setup-mqtt-auth.sh derbynet yourpassword

# Start local stack
docker compose up -d --build

# Access at http://localhost/derbynet/
# Run simulation: docker exec derbynet-race-server python3 /var/lib/infra/app/simulate_racing.py
```

## Deployment Pipeline

### Test Pipeline (`.github/workflows/test.yml`)

Runs on all PRs and pushes to develop/master:
1. Builds Docker images
2. Starts full stack (Caddy + PHP + Race Server + Mosquitto)
3. Runs `testing/test-basic-racing.sh`
4. Runs `simulate_racing.py` smoke test
5. Reports results

### Deploy Pipeline (`.github/workflows/deploy.yml`)

**Staging** (develop branch):
1. Build images, tag as `develop`
2. Push to `ghcr.io/<owner>/sbderbynet-web:develop` and `sbderbynet-server:develop`
3. SSH to VPS → `docker compose pull && docker compose up -d`

**Production** (master branch):
1. Build images, tag as `latest` + git SHA
2. Push to ghcr.io
3. SSH to VPS → deploy to production

**Note:** Docker volumes persist across deploys — test data and database survive redeploys. The workflow uses `docker compose up -d` (not `down -v`) to preserve volumes.

### Manual deploy (when CI is unavailable)

For situations where the GitHub Actions path is blocked (PAT scopes,
network outage, deploying a feature branch that hasn't merged), the
`scripts/derbyvps.sh` wrapper provides the same end-to-end flow:

```sh
./scripts/derbyvps.sh deploy --dry-run      # preview the rsync diff
./scripts/derbyvps.sh deploy                # backup → rsync → up → validate
```

It rsyncs the local working tree to the VPS, builds images locally on the
host, and runs the same pre/postflight gates (port collisions, /health,
ERROR scan). On postflight failure it auto-rolls back to the just-made
backup. Full reference: `docs/VPS_OPERATIONS.md`.

The wrapper and the GitHub Actions deploy are interchangeable on the
target side — both bring up the same compose stack at
`/opt/sbderbynet/installer/docker-cloud/` with the production override
that bind-mounts data at `/opt/derbynet/production/data`.

## VPS Directory Structure

```
/opt/derbynet/
├── staging/
│   ├── docker-compose.yml          # Base compose
│   ├── docker-compose.staging.yml  # Image tag override (:develop)
│   ├── Caddyfile
│   └── .env
│
├── production/
│   ├── docker-compose.yml          # Base compose
│   ├── docker-compose.production.yml  # Image tag override (:latest)
│   ├── Caddyfile
│   └── .env
│
└── mosquitto/
    ├── mosquitto.conf
    └── passwd
```

## Docker Stack

| Service | Image | Purpose |
|---------|-------|---------|
| `caddy` | `caddy:2-alpine` | Reverse proxy, automatic HTTPS, plus `/mqtt` WebSocket route to the broker. Also serves the obfuscated-token spectator pages at `live.soapboxderbynet.com` (see `docs/PUBLIC_STATS.md`) |
| `mqtt` | `eclipse-mosquitto:2` | MQTT broker. Listens on 1883 (TCP, internal) and 9001 (WebSockets, fronted by Caddy at `/mqtt`) |
| `derbynet-web` | `ghcr.io/.../sbderbynet-web` | PHP/Nginx web application; serves `website/virtual/*` browser virtual hardware in cloud mode |
| `race-server` | `ghcr.io/.../sbderbynet-server` | Python race server + simulator (extended with `SimulatedDisplay`/`SimulatedLEDSign` for headless CI) |
| `derbynet-stats-gen` | local build (alpine + sqlite + qrencode) | Prerenders the public spectator pages (schedule + recent results) from the Pi-synced SQLite every 30 s. Not in CI image matrix — built fresh on each `derbyvps.sh deploy --build` |

### Browser virtual hardware (cloud-only)

When `DERBYNET_CLOUD_MODE` is set, the cloud stack also serves a set of
desktop-only browser pages under `/derbynet/virtual/` that mimic the real
finish/start timers, displays, and LED signs over MQTT-WS. Their hwids are
prefixed `B_` and they are explicitly excluded from race-day code paths
on the Pi via `_guard.inc` and the `B_*` filter in `device-status-api.php`.
Credentials are served through `action.virtual-mqtt-creds`. The local Pi
never exposes these pages and never connects to the cloud broker.

See `docs/DRESS_REHEARSAL.md` for how to drive a full event from the
control panel at `/derbynet/virtual/index.php`.

## GitHub Secrets Required

| Secret | Purpose |
|--------|---------|
| `SERVER_HOST` | VPS IP address |
| `SERVER_USER` | SSH username (e.g., `deploy`) |
| `SERVER_SSH_KEY` | Private SSH key for deployment |

## Key Files

| File | Purpose |
|------|---------|
| `installer/docker-cloud/docker-compose.yml` | Base Docker stack |
| `installer/docker-cloud/Caddyfile` | Reverse proxy config |
| `installer/docker-cloud/docker-compose.staging.yml` | Staging image overrides |
| `installer/docker-cloud/docker-compose.production.yml` | Production image overrides |
| `.github/workflows/deploy.yml` | CI/CD deploy pipeline |
| `.github/workflows/test.yml` | CI/CD test pipeline |

## Two Deployment Paths

| Target | Method | Trigger |
|--------|--------|---------|
| Cloud VPS | GitHub Actions → Docker | Push to develop/master |
| Race-day Pi | Ansible auto-pull | Every 30 min from master (`extras/derbypi/`) |

Both pull from the same GitHub repo but use different deployment mechanisms. Code merged to master reaches both targets.

## Rollback

```bash
# Cloud VPS: rollback to previous image by SHA
cd /opt/derbynet/production
# Edit docker-compose.production.yml to pin a specific SHA tag
docker compose -f docker-compose.yml -f docker-compose.production.yml pull
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d

# Or via git revert
git revert HEAD
git push origin master  # Triggers new deploy with reverted code
```

## Future: Mobile App Backend

When the Flutter app is ready for cloud integration:
- SaaSBox API (`extras/saasbox/`) runs on the VPS alongside the dev stack
- Pi pushes race data to SaaSBox via `POST /v1/orgs/{org_id}/events/{event_id}/sync`
- Mobile app connects to SaaSBox for live results, predictions, push notifications
- This is a separate concern from the dev/CI pipeline

## Future Enhancements

- [ ] Database migration automation
- [ ] Blue-green deployments for zero-downtime
- [ ] Slack/Discord deploy notifications
- [ ] Automated version bumping on release
- [ ] Race-day database backup (rsync SQLite to VPS)
- [ ] SaaSBox API deployment alongside dev stack

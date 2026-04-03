# CI/CD Strategy

A three-tier deployment strategy: **Local → Staging → Production** with automated GitHub Actions pipelines.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     LOCAL DEVELOPMENT                            │
│  Docker Compose with build context for hot-reload               │
│  cd installer/docker-cloud && docker compose up -d --build      │
│  Access at http://localhost/derbynet/                            │
└─────────────────────────────────────────────────────────────────┘
                             │
                      git push develop / master
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GITHUB ACTIONS                               │
│                                                                  │
│  .github/workflows/test.yml (all PRs + pushes):                 │
│    → Build Docker images                                        │
│    → Start full stack in CI                                     │
│    → Run test suite + race simulation                           │
│                                                                  │
│  .github/workflows/deploy.yml (develop + master):               │
│    → Build Docker images                                        │
│    → Push to ghcr.io                                            │
│    → SSH deploy to VPS                                          │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VULTR VPS                                     │
│                                                                  │
│  ┌─────────────────────┐    ┌─────────────────────┐            │
│  │  STAGING            │    │  PRODUCTION         │            │
│  │  :8080 or subdomain │    │  :80 / :443         │            │
│  │                     │    │                     │            │
│  │  Image tag: develop │    │  Image tag: latest  │            │
│  └─────────────────────┘    └─────────────────────┘            │
│                                                                  │
│  Caddy reverse proxy (automatic HTTPS when domain configured)   │
│  Mosquitto MQTT (authenticated, port 1883)                      │
└─────────────────────────────────────────────────────────────────┘
                             │
                      MQTT Bridge
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  LOCAL GATEWAY (Race Day)                         │
│                                                                  │
│  Mosquitto bridge on 192.168.100.10:1883                        │
│  Relays derbynet/# topics bidirectionally to cloud              │
│  Zero firmware changes on devices                                │
│                                                                  │
│  Fallback: switch-to-local.sh for cloud-independent operation   │
└─────────────────────────────────────────────────────────────────┘
```

## Workflow Summary

| Scenario | Action | Result |
|----------|--------|--------|
| Quick testing | `docker compose up -d --build` locally | Instant local stack |
| Ready for review | `git push origin develop` | Auto-deploys to staging |
| Ready for production | Merge develop → master | Auto-deploys to production |
| Emergency hotfix | Push directly to master | Auto-deploys (use sparingly) |
| Run tests | Open a PR | Tests run automatically in CI |

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
| `caddy` | `caddy:2-alpine` | Reverse proxy, automatic HTTPS |
| `mqtt` | `eclipse-mosquitto:2` | MQTT broker (authenticated) |
| `derbynet-web` | `ghcr.io/.../sbderbynet-web` | PHP/Nginx web application |
| `race-server` | `ghcr.io/.../sbderbynet-server` | Python race server |

## GitHub Secrets Required

| Secret | Purpose |
|--------|---------|
| `SERVER_HOST` | VPS IP address |
| `SERVER_USER` | SSH username (e.g., `deploy`) |
| `SERVER_SSH_KEY` | Private SSH key for deployment |

## Local Gateway

For connecting race-day hardware to the cloud:

```bash
cd installer/gateway

# Configure bridge credentials
# Edit mosquitto-bridge.conf with cloud host and MQTT credentials

# Start bridge
docker compose up -d

# Emergency failover to local-only
./switch-to-local.sh

# Resume cloud operation
./switch-to-cloud.sh
```

See [installer/gateway/README.md](../installer/gateway/README.md) for details.

## Key Files

| File | Purpose |
|------|---------|
| `installer/docker-cloud/docker-compose.yml` | Base Docker stack |
| `installer/docker-cloud/Caddyfile` | Reverse proxy config |
| `installer/docker-cloud/docker-compose.staging.yml` | Staging image overrides |
| `installer/docker-cloud/docker-compose.production.yml` | Production image overrides |
| `.github/workflows/deploy.yml` | CI/CD deploy pipeline |
| `.github/workflows/test.yml` | CI/CD test pipeline |
| `installer/gateway/mosquitto-bridge.conf` | Local-to-cloud MQTT bridge |
| `installer/gateway/docker-compose.fallback.yml` | Local fallback stack |

## Rollback

```bash
# On VPS: rollback to previous image by SHA
cd /opt/derbynet/production
# Edit docker-compose.production.yml to pin a specific SHA tag
docker compose -f docker-compose.yml -f docker-compose.production.yml pull
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d

# Or via git revert
git revert HEAD
git push origin master  # Triggers new deploy with reverted code
```

## Future Enhancements

- [ ] Database migration automation
- [ ] Blue-green deployments for zero-downtime
- [ ] Slack/Discord deploy notifications
- [ ] Automated version bumping on release
- [ ] Device-side timestamps for cloud race timing accuracy
- [ ] TLS on MQTT broker (port 8883) for encrypted bridge traffic

# CI/CD

Two deployment paths to two targets. Race-day Pi pulls via Ansible; cloud twin updates via the `derbyvps.sh` wrapper.

**Architecture principle**: the Pi is the race-day master. The cloud VPS is for development, testing, dress rehearsal. It has no race-day role.

---

## The picture

```
═══════════════════════════════════════════════════════════════
  RACE DAY (Raspberry Pi — 192.168.100.x)        AUTHORITATIVE
═══════════════════════════════════════════════════════════════
  DerbyNet PHP + SQLite, Race Server, Mosquitto MQTT
  All hardware (timers, displays, LED signs)
  Deployed via Ansible auto-pull from GitHub (extras/derbypi/)

═══════════════════════════════════════════════════════════════
  CLOUD TWIN (uisp.darketech.ca)                  DEV / TEST
═══════════════════════════════════════════════════════════════
  Same image as the Pi, in Docker.
  Updated by `scripts/derbyvps.sh deploy` from a developer machine.
```

---

## Two paths, same repo

| Target | Method | Trigger |
|---|---|---|
| Race-day Pi | Ansible auto-pull (`ansible-pull`) | every 30 min from `master` |
| Cloud twin | `scripts/derbyvps.sh deploy` | manual, from a developer's working tree |

Both pull from the same GitHub repository. Code merged to `master` reaches both.

---

## Cloud-twin deploy (current canonical path)

```bash
./scripts/derbyvps.sh deploy --dry-run    # preview rsync diff
./scripts/derbyvps.sh deploy              # backup → rsync → up → validate
```

The wrapper rsyncs the local working tree, builds images on the VPS, runs pre/post-flight gates (port collisions, `/health`, ERROR scan). Postflight failure auto-rolls back to the just-made backup.

Full reference: [VPS Procedures](../operations/vps-procedures.md).

---

## Race-day Pi deploy

DerbyPi installs an `ansible-pull` systemd timer at bootstrap. Every 30 minutes it pulls the repo and runs the playbook against `master`. Manual trigger:

```bash
sudo systemctl start ansible-pull.service
```

See [DerbyPi](../components/derbypi.md).

---

## GitHub Actions

!!! warning "Future / not yet implemented"
    The `.github/workflows/test.yml` and `.github/workflows/deploy.yml` workflows referenced by previous design docs **do not currently exist**. The repo's `.github/workflows/` ships only the desktop-installer builders (`electron.yml`, `jpackage-macos.yml`, `jpackage-win.yaml`).

    Until those are added, treat the manual `derbyvps.sh deploy` path as canonical.

When the workflows do land, the planned shape is:

- `test.yml` (all PRs and pushes): build images, start full stack, run `testing/test-basic-racing.sh` + `simulate_racing.py`, report.
- `deploy.yml` (`develop` and `master` branches): build → push to `ghcr.io` → SSH deploy to VPS.

The cloud-twin target side will accept either the wrapper or a future workflow — both bring up the same compose stack at `/opt/sbderbynet/installer/docker-cloud/` with the production override that bind-mounts data at `/opt/derbynet/production/data`.

---

## Local development

```bash
cd installer/docker-cloud

# first time only
cp .env.example .env
./scripts/setup-mqtt-auth.sh derbynet yourpassword

# bring up the stack
docker compose up -d --build

# visit http://localhost/derbynet/
# run a simulation
docker exec derbynet-race-server python3 /var/lib/infra/app/simulate_racing.py
```

---

## VPS layout

```
/opt/derbynet/
├── staging/
│   ├── docker-compose.yml
│   ├── docker-compose.staging.yml      # image tag override
│   ├── Caddyfile
│   └── .env
├── production/
│   ├── docker-compose.yml
│   ├── docker-compose.production.yml   # bind mount + image tag override
│   ├── Caddyfile
│   └── .env
└── mosquitto/
    ├── mosquitto.conf
    └── passwd
```

## Docker stack

| Service | Image | Purpose |
|---|---|---|
| `caddy` | `caddy:2-alpine` | reverse proxy, automatic HTTPS, `/mqtt` WebSocket route |
| `mqtt` | `eclipse-mosquitto:2` | MQTT broker (1883 TCP internal, 9001 WS via Caddy) |
| `derbynet-web` | `ghcr.io/.../sbderbynet-web` | PHP/Nginx web app; serves `website/virtual/*` in cloud mode |
| `race-server` | `ghcr.io/.../sbderbynet-server` | Python race server + simulator (with `Simulated*` for headless CI) |

### Browser virtual hardware (cloud only)

When `DERBYNET_CLOUD_MODE` is set, the cloud stack also serves desktop-only browser pages under `/derbynet/virtual/` that mimic real finish/start timers, displays, and LED signs over MQTT-WS. Their `hwid`s are prefixed `B_` and they are explicitly excluded from race-day code paths on the Pi via `_guard.inc` and the `B_*` filter in `device-status-api.php`. Credentials are served through `action.virtual-mqtt-creds`. The Pi never exposes these pages and never connects to the cloud broker.

See [Dress Rehearsal](../operations/dress-rehearsal.md).

---

## Rollback

```bash
# Cloud: roll back to the last snapshot
ssh ... 'sudo ls -1t /opt/sbderbynet-backups | head'
./scripts/derbyvps.sh rollback deploy-20260503-201500

# Or via git revert
git revert HEAD && git push origin master
# Pi will pick it up at the next ansible-pull (≤30 min).
```

---

## Future enhancements

- GitHub Actions for `test.yml` + `deploy.yml`
- Database migration automation
- Blue-green deployments (zero-downtime)
- Deploy notifications (Slack / Discord)
- Race-day database backup (`rsync` SQLite to VPS)
- SaaSBox API deployment alongside the dev stack

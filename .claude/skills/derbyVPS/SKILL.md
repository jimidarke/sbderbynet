---
name: derbyVPS
description: |
  Operational reference for the SBDerbyNet cloud VPS at uisp.darketech.ca.
  Use when the user asks to check, deploy to, troubleshoot, or restart the
  cloud twin. Routes routine work through scripts/derbyvps.sh; this skill
  documents what + why (connection details, host state, design decisions).
---

# derbyVPS — Cloud Twin Operations

## TL;DR — use the wrapper

Every routine VPS interaction goes through `scripts/derbyvps.sh`:

```sh
./scripts/derbyvps.sh audit                 # read-only state report
./scripts/derbyvps.sh bootstrap             # first-time setup
./scripts/derbyvps.sh deploy [--dry-run]    # backup → rsync → up → validate
./scripts/derbyvps.sh status                # containers + /health
./scripts/derbyvps.sh logs [service]        # tail logs
./scripts/derbyvps.sh backup [tag]          # manual snapshot
./scripts/derbyvps.sh rollback <tag>        # restore from snapshot
./scripts/derbyvps.sh shutdown              # clean down (data preserved)
./scripts/derbyvps.sh restore-uisp          # tear down sbderby, bring UISP back
./scripts/derbyvps.sh stats-token {show|rotate|qr}  # spectator-page token control
```

Full command reference and walkthroughs: `docs/VPS_OPERATIONS.md`.

For "where do logs live?" run `./scripts/derbyvps.sh logs --where`.
The full log map (container stdouts, persistent volumes, the wrapper deploy
trail, host journal) is in `docs/LOGGING.md`. Container logs are size-capped
(json-file `max-size: 10m, max-file: 3` per service) so disk-fill won't
sneak up on race day.

The script handles preflight gates (SSH, disk, ports, UISP siloed),
backup-first rotation (last 10 snapshots), postflight checks (`/health`,
ERROR log scan), and automatic rollback on postflight failure. Every SSH
call is logged to `scripts/.derbyvps-deploy.log` locally and
`/var/log/sbderbynet-deploy.log` on the VPS.

## Connection (what the script defaults to)

| | |
|---|---|
| **Host** | `uisp.darketech.ca` |
| **Port** | `22` |
| **User** | `claude` (passwordless sudo via `/etc/sudoers.d/claude-validation`) |
| **Key** | `~/.ssh/sbderby_vps_ed25519` (fingerprint `SHA256:7IVpRtmYcmmHs5B8lGY4NhAbnSMYKF/dzaFHSQJa5ZM`) |
| **Repo dir** | `/opt/sbderbynet/` |
| **Data dir** | `/opt/derbynet/production/data/` (bind-mounted to `/var/lib/derbynet` in containers) |
| **Backups** | `/opt/sbderbynet-backups/<tag>/` |

To override any of these: `cp scripts/derbyvps.config.example scripts/derbyvps.config`.

## What's on the host

### UISP — siloed (don't disturb)

UISP installation at `/home/unms/app/`, project name `unms`. As of
2026-05-03 all 9 containers are stopped with `restart=no` and the
auto-update cron at `/etc/cron.d/unms-update` was renamed to
`unms-update.disabled-by-claude-20260503` (it was running every minute).
Volumes and networks preserved.

To restart UISP later, use `./scripts/derbyvps.sh restore-uisp` — it does
the inverse of the silo (re-enables cron, restores `restart=always`,
starts containers in dependency order).

### SBDerbyNet — managed by the wrapper

- Compose project at `/opt/sbderbynet/installer/docker-cloud/`
- Production override (`docker-compose.production.yml`) bind-mounts
  `/opt/derbynet/production/data` into both `derbynet-web` and
  `race-server` so cloud-sync.sh's scp target lines up with the
  `/var/lib/derbynet` path the containers read from
- Stack: Caddy (80/443) + Mosquitto (1883 internal, 9001 WS via Caddy
  `/mqtt`) + derbynet-web (PHP) + race-server (Python) +
  derbynet-stats-gen (Alpine sidecar, prerenders public spectator HTML
  every 30 s — see `docs/PUBLIC_STATS.md`)
- Postflight expects **5** running services (`EXPECTED_SERVICES_MIN=5`).
- Caddy serves a second site at `live.soapboxderbynet.com` (separate
  block) for the obfuscated-token spectator pages — does not interfere
  with the main control surface on `uisp.darketech.ca`.

## Design decisions worth remembering

- **Why rsync instead of git pull on the VPS?** The GitHub Actions
  deploy at `.github/workflows/deploy.yml` was removed (2026-05-03) —
  rsync via `derbyvps.sh deploy` is now the only path to the VPS. We
  chose this because the cloud twin is a test environment, the wrapper
  already handles backup-rotate-deploy-rollback safely, and CI auto-deploy
  on master push was an over-engineered fit. If you ever want CI deploy
  back, see git history (commit 8de623ca added the original) — but
  prefer keeping the path explicit.
- **Why is `/etc/cron.d/unms-update` renamed instead of deleted?** UISP
  needs it back when we decommission. The dot-in-filename rule in cron's
  `cron.d/` parser disables it without removing data.
- **Why does the wrapper auto-rollback on postflight failure?** A bad
  `.env` change or a syntax error in a virtual page would otherwise
  leave the stack down with no easy recovery. The just-made backup is
  the one we restore from — guaranteed to be the last known good state.
- **Why `B_*` MQTT ACL is enumerated, not wildcarded?** MQTT spec § 4.7.1.2
  forbids `+` combined with literal characters. `derbynet/device/B_+/state`
  is invalid; we list each hwid explicitly in
  `installer/docker-cloud/mosquitto/acl`. Add a line when introducing a
  new virtual device.
- **Why not zero-downtime?** The cloud twin is a *test* environment.
  A 10-second blip during `compose up` is acceptable. Don't over-engineer.

## Cleanup when work is finished

The `claude` user is intended ephemeral:

```sh
sudo rm /etc/sudoers.d/claude-validation
sudo userdel -r claude
```

The private key at `~/.ssh/sbderby_vps_ed25519` lives in the dev
workspace; treat as session-scoped.

## Things outside this skill's scope

- **Pi side** — `extras/soapbox/CLAUDE.md`, `docs/CICD.md`.
- **Race-day operations** — `docs/PULL_FORWARD_OPERATOR.md`, `docs/DRESS_REHEARSAL.md`.
- **(Removed) GitHub Actions deploy** — `.github/workflows/deploy.yml` was deleted; `docs/CICD.md` is now historical.

## Quick safety reminders

- Never share the contents of `/opt/sbderbynet/installer/docker-cloud/.env` (broker passwords).
- The Pi remains source of truth for race data. The cloud twin's DB is a
  one-way replica — local edits there will be overwritten on the next
  Pi sync.
- Ports 80/443 conflict between UISP and SBDerbyNet. Only one stack runs
  at a time. The wrapper enforces this in preflight.

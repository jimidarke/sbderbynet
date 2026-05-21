# VPS Operations

Standard procedure for interacting with the SBDerbyNet cloud twin VPS.

The `scripts/derbyvps.sh` wrapper does everything routine. This doc explains
**when** to use each command and walks through the common scenarios. For
the underlying VPS state (which user, what's siloed, where things live),
see the `derbyVPS` skill at `.claude/skills/derbyVPS/SKILL.md`.

## Quick reference

```sh
./scripts/derbyvps.sh audit                 # read-only state report
./scripts/derbyvps.sh bootstrap             # first-time setup (one-time)
./scripts/derbyvps.sh deploy [--dry-run]    # update from local working tree
./scripts/derbyvps.sh status                # containers + /health + recent errors
./scripts/derbyvps.sh logs [service]        # tail logs (all services or one)
./scripts/derbyvps.sh backup [tag]          # manual snapshot
./scripts/derbyvps.sh rollback <tag>        # restore from snapshot
./scripts/derbyvps.sh shutdown              # clean down (data preserved)
./scripts/derbyvps.sh restore-uisp          # tear down sbderby, bring UISP back
./scripts/derbyvps.sh stats-token show      # spectator token + URL + QR location
./scripts/derbyvps.sh stats-token rotate    # mint new spectator token (race-day morning)
./scripts/derbyvps.sh stats-token qr        # scp the QR PNG down to ./derby-qr.png
```

Common flags: `--dry-run`, `--yes`, `--quiet`, `--verbose`.

## Setup (once per dev machine)

The script ships with sensible defaults. To override host/port/paths:

```sh
cp scripts/derbyvps.config.example scripts/derbyvps.config
$EDITOR scripts/derbyvps.config
```

`derbyvps.config` is gitignored — safe to put deployer-specific paths
there. If you need a different SSH key:

```bash
echo 'VPS_KEY="$HOME/.ssh/my-other-key"' > scripts/derbyvps.config
```

## Scenario walkthroughs

### First-ever deploy to a clean VPS

```sh
./scripts/derbyvps.sh audit
# Verify host healthy, UISP siloed, ports 80/443/1883 free.

./scripts/derbyvps.sh bootstrap
# Creates /opt/sbderbynet, bind-mount data dir, .env with random passwords,
# provisions broker users, builds + brings the stack up, runs postflight.

./scripts/derbyvps.sh status
# Sanity check. /health should return 200; 5 services Up
# (Caddy + MQTT + derbynet-web + race-server + derbynet-stats-gen).
```

Then in a browser: `http://<vps>/derbynet/virtual/index.php` should render
the device control panel.

### Routine update from your dev branch

```sh
./scripts/derbyvps.sh deploy --dry-run
# Shows the rsync diff so you know exactly what's about to ship.

./scripts/derbyvps.sh deploy
# Backup first, then rsync, validate, build, up, postflight.
# If postflight fails the script auto-rolls back to the just-made snapshot.
```

If your working tree is dirty the script will prompt; `--yes` to skip.

### Something broke after deploy

```sh
./scripts/derbyvps.sh status
./scripts/derbyvps.sh logs derbynet-web    # one-service tail
```

If you need to roll back to before the bad deploy:

```sh
ssh ... 'sudo ls -1t /opt/sbderbynet-backups | head'
# Pick the right tag (e.g. deploy-20260503-201500)

./scripts/derbyvps.sh rollback deploy-20260503-201500
```

Rollback is interactive by default. Pass `--yes` to skip the confirmation.

### Manual checkpoint before something risky

```sh
./scripts/derbyvps.sh backup pre-pull-forward-experiment
```

Backups not tagged `deploy-*` are still subject to the rotation cap; if you
want one to live forever, copy it off-host:

```sh
scp -i ~/.ssh/sbderby_vps_ed25519 -r \
    claude@uisp.darketech.ca:/opt/sbderbynet-backups/<tag> ./
```

### Putting UISP back when the race is over

```sh
./scripts/derbyvps.sh restore-uisp
```

Stops the SBDerbyNet stack (preserves volumes + backups), re-enables the
UISP `unms-update` cron, restores `restart=always` on each UISP container,
starts them in dependency order, prints the post-state.

To wake SBDerbyNet back up later: `./scripts/derbyvps.sh shutdown`
on UISP first (manually), then `./scripts/derbyvps.sh deploy`.

## Validation gates explained

### Pre-deploy aborts (deploy command)

| Trigger | Why | Fix |
|---|---|---|
| SSH connect fails | host unreachable, key missing, user removed | check `VPS_*` config; verify your key is in `authorized_keys` |
| Disk free < 4 GB | not enough headroom for backup + new images | `ssh ... sudo apt autoremove`, prune old backups, `docker image prune` |
| Non-docker process bound to 80/443/1883 | port collision | identify with `ssh ... sudo ss -tlnp`; stop the rogue process |
| UISP containers running | UISP would fight us for ports | run `restore-uisp` was wrong path — `ssh ... sudo docker stop <unms-*>` |
| `docker compose config` fails | bad YAML or env after rsync | fix locally, deploy again |

### Post-deploy aborts → automatic rollback

| Trigger | Likely cause |
|---|---|
| Fewer than `EXPECTED_SERVICES_MIN` containers Up after 60s | container exited (build error, image fault); check logs |
| `/health` doesn't return 200 in ~15s | Caddy not routing or web container unhealthy |
| More than 1 ERROR line in last 60s of logs | application-level failure |

When a postflight fails the script restores the just-made backup, retries
postflight, and if rollback also fails leaves the stack stopped with both
log files intact. The deploy log is at `scripts/.derbyvps-deploy.log`
locally and `/var/log/sbderbynet-deploy.log` on the VPS.

## What the script does *not* do

- **Push to GitHub.** Use `git push` yourself when the PAT allows it.
- **Run tests.** Run them locally with `./testing/test-pull-forward.sh` etc.
- **Off-host backup.** The Pi's `cloud-sync.sh` covers DB-to-cloud direction.
  For full off-host history of `.env` + backups, copy them down via `scp`.
- **Schema migrations.** SBDerbyNet's PHP setup handles its own schema; the
  deploy just brings new code online.

## Logs

- **Local**: `scripts/.derbyvps-deploy.log` (gitignored; one line per ssh
  call with timestamp).
- **Remote**: `/var/log/sbderbynet-deploy.log` (mirrored output of every
  remote command, accumulating).

If a deploy goes sideways, attach both files to the post-mortem.

## Adjusting defaults

- More frequent rotation? Set `BACKUP_RETENTION=20` in your config.
- Different bind-mount path? Set `VPS_DATA_DIR=...`. Make sure the
  `installer/docker-cloud/docker-compose.production.yml` agrees.
- Want to skip the production override and use the named volume instead?
  `COMPOSE_FILES="-f docker-compose.yml"` (note: drops the bind mount).

### Race-day: mint and print the spectator QR

```sh
./scripts/derbyvps.sh stats-token rotate    # generates new token, recreates stats-gen + caddy
./scripts/derbyvps.sh stats-token qr        # downloads the QR PNG
./scripts/derbyvps.sh stats-token show      # prints URLs + QR location anytime
```

The token gates a per-event `https://live.soapboxderbynet.com/<TOKEN>/{schedule,recent}.html`
URL. Full runbook: `docs/PUBLIC_STATS.md`.

## See also

- `.claude/skills/derbyVPS/SKILL.md` — connection details, what's running, what's siloed.
- `docs/LOGGING.md` — full server-side logging map. `derbyvps.sh logs --where` prints the live cheat sheet.
- `docs/CICD.md` — eventual GitHub-Actions-driven deploy path (when the
  feature branch lands on master).
- `docs/DRESS_REHEARSAL.md` — race-day go/no-go gates that depend on the
  cloud twin being up.
- `docs/PUBLIC_STATS.md` — public spectator pages: deployment, token rotation, troubleshooting.

# VPS Procedures

Standard procedure for the SBDerbyNet cloud twin. The `scripts/derbyvps.sh` wrapper handles routine operations; this page explains **when** to use each command and walks through common scenarios.

For underlying VPS state (which user, what's siloed, where things live), see `.claude/skills/derbyVPS/SKILL.md`.

---

## Quick reference

```sh
./scripts/derbyvps.sh audit                 # read-only state report
./scripts/derbyvps.sh bootstrap             # first-time setup (one-time)
./scripts/derbyvps.sh deploy [--dry-run]    # update from local working tree
./scripts/derbyvps.sh status                # containers + /health + recent errors
./scripts/derbyvps.sh logs [service]        # tail logs
./scripts/derbyvps.sh backup [tag]          # manual snapshot
./scripts/derbyvps.sh rollback <tag>        # restore from snapshot
./scripts/derbyvps.sh shutdown              # clean down (data preserved)
./scripts/derbyvps.sh restore-uisp          # tear down sbderby, bring UISP back
```

Common flags: `--dry-run`, `--yes`, `--quiet`, `--verbose`.

---

## Setup (once per dev machine)

```sh
cp scripts/derbyvps.config.example scripts/derbyvps.config
$EDITOR scripts/derbyvps.config
```

`derbyvps.config` is gitignored — safe for deployer-specific paths. Override the SSH key:

```bash
echo 'VPS_KEY="$HOME/.ssh/my-other-key"' > scripts/derbyvps.config
```

---

## Scenario walkthroughs

### First-ever deploy to a clean VPS

```sh
./scripts/derbyvps.sh audit          # host healthy, UISP siloed, ports 80/443/1883 free
./scripts/derbyvps.sh bootstrap      # creates /opt/sbderbynet, .env, broker users, builds, brings up
./scripts/derbyvps.sh status         # /health = 200, 5 services Up
```

Then in a browser: `http://<vps>/derbynet/virtual/index.php` should render the device control panel.

### Routine update from your dev branch

```sh
./scripts/derbyvps.sh deploy --dry-run   # shows the rsync diff
./scripts/derbyvps.sh deploy             # backup → rsync → validate → build → up → postflight
```

If postflight fails, the script auto-rolls back to the just-made snapshot. Dirty working tree prompts; `--yes` to skip.

### Something broke after deploy

```sh
./scripts/derbyvps.sh status
./scripts/derbyvps.sh logs derbynet-web
```

To roll back to before the bad deploy:

```sh
ssh ... 'sudo ls -1t /opt/sbderbynet-backups | head'
./scripts/derbyvps.sh rollback deploy-20260503-201500
```

Rollback is interactive by default; `--yes` to skip.

### Manual checkpoint before something risky

```sh
./scripts/derbyvps.sh backup pre-pull-forward-experiment
```

Backups not tagged `deploy-*` are still subject to rotation. To preserve permanently, copy off-host:

```sh
scp -i ~/.ssh/sbderby_vps_ed25519 -r \
    claude@uisp.darketech.ca:/opt/sbderbynet-backups/<tag> ./
```

### Putting UISP back when the race is over

```sh
./scripts/derbyvps.sh restore-uisp
```

Stops the SBDerbyNet stack (preserves volumes and backups), re-enables the UISP `unms-update` cron, restores `restart=always` on each UISP container, starts them in dependency order, prints final state.

To wake SBDerbyNet back up later: shut down UISP first manually, then `./scripts/derbyvps.sh deploy`.

---

## Validation gates

### Pre-deploy aborts

| Trigger | Why | Fix |
|---|---|---|
| SSH connect fails | host unreachable, key missing | check `VPS_*` config; verify key in `authorized_keys` |
| Disk free < 4 GB | not enough headroom | `apt autoremove`, prune backups, `docker image prune` |
| Non-docker process on 80/443/1883 | port collision | `ss -tlnp`, stop the rogue process |
| UISP containers running | port fight | `docker stop <unms-*>` (don't run `restore-uisp` here) |
| `docker compose config` fails | bad YAML / env after rsync | fix locally, deploy again |

### Post-deploy aborts → automatic rollback

| Trigger | Likely cause |
|---|---|
| Fewer than `EXPECTED_SERVICES_MIN` containers Up after 60s | container exited (build error, image fault) |
| `/health` doesn't return 200 in ~15s | Caddy not routing or web container unhealthy |
| > 1 ERROR line in last 60s of logs | application-level failure |

When postflight fails the script restores the just-made backup, retries postflight, and if rollback also fails leaves the stack stopped with both log files intact. Deploy logs at `scripts/.derbyvps-deploy.log` (local) and `/var/log/sbderbynet-deploy.log` (VPS).

---

## What the script does *not* do

- **Push to GitHub.** Use `git push` yourself.
- **Run tests.** Run them locally with `./testing/test-pull-forward.sh` etc.
- **Off-host backup.** The Pi's `cloud-sync.sh` covers DB-to-cloud direction. For full off-host history, `scp` backups down.
- **Schema migrations.** The PHP setup handles schema; deploy just brings new code online.

---

## Adjusting defaults

- More frequent rotation: `BACKUP_RETENTION=20` in your config.
- Different bind-mount path: `VPS_DATA_DIR=...`. Make sure `installer/docker-cloud/docker-compose.production.yml` agrees.
- Skip the production override (use the named volume instead): `COMPOSE_FILES="-f docker-compose.yml"` (drops the bind mount).

See also: [Logging](logging.md), [Dress Rehearsal](dress-rehearsal.md), [CI/CD](../reference/cicd.md).

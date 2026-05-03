---
name: derbyVPS
description: |
  Operational reference for the SBDerbyNet cloud VPS at uisp.darketech.ca.
  Use when the user asks to check, deploy to, troubleshoot, or restart the
  cloud twin. Covers SSH access, host inventory, UISP silo state, deployment
  procedure for the SBDerbyNet stack, and clean teardown / UISP restoration.
---

# derbyVPS — SBDerbyNet Cloud Twin Operations

The cloud twin runs on a Vultr Ubuntu 24.04 VPS shared (currently siloed) with
a UISP installation. This skill documents how to reach it, what's installed,
and how to drive the SBDerbyNet stack on it.

## Connection

| | |
|---|---|
| **Host** | `uisp.darketech.ca` (also serves as the cloud twin URL) |
| **Port** | `22` |
| **User** | `claude` (passwordless sudo via `/etc/sudoers.d/claude-validation`) |
| **Key** | `~/.ssh/sbderby_vps_ed25519` (key fingerprint `SHA256:7IVpRtmYcmmHs5B8lGY4NhAbnSMYKF/dzaFHSQJa5ZM`) |
| **Public key comment** | `claude-sbderbynet-vps-validation-20260503` |

Standard SSH invocation:

```sh
ssh -i ~/.ssh/sbderby_vps_ed25519 -p 22 claude@uisp.darketech.ca
```

For one-shot commands, prefer a single SSH session that runs everything in a
heredoc/single quoted block — minimizes connection overhead and keeps audit
output linear.

### Key cleanup (when work is done)

The `claude` user is intended to be ephemeral. To remove:

```sh
sudo rm /etc/sudoers.d/claude-validation
sudo userdel -r claude
```

## Host inventory (snapshot 2026-05-03)

- **OS:** Ubuntu 24.04.4 LTS · 2 vCPU · 3.8 GB RAM · 75 GB disk
- **Kernel running:** `6.8.0-101` (newer kernels installed but reboot pending)
- **Docker:** `29.2.1` (server + client). Storage `overlay2`, cgroups v2 systemd.
- **Docker Compose:** plugin v5.x at `/usr/libexec/docker/cli-plugins/docker-compose`. Use `docker compose ...` (the standard Docker CLI plugin form).
- **UFW:** active, default deny inbound, only port 22 allowed.
  - ⚠️ Docker `docker-proxy` bypasses UFW. When SBDerbyNet binds 80/443, those become reachable from the internet without a UFW rule. Standard Docker behavior.
- **Other shell users:** `ubuntu`, `linuxuser`, `unms`. The `unms` user owns the UISP install at `/home/unms/app/`.

The inventory above will drift; use the **Audit** recipe below to refresh.

## What's running (and not)

### UISP — siloed (stopped, won't auto-start)

UISP compose project lives at `/home/unms/app/docker-compose.yml`, project
name `unms`. As of 2026-05-03 all 9 containers are stopped with
`restart=no`. The cron at `/etc/cron.d/unms-update` (which ran every minute,
not daily) was renamed to `unms-update.disabled-by-claude-20260503` to
prevent UISP self-update from reviving the stack.

Containers (siloed):
```
unms-device-ws-1, unms-api, ucrm, unms-netflow, unms-rabbitmq,
unms-siridb, unms-nginx, unms-postgres, unms-fluentd
```

Volumes preserved (do NOT delete):
```
0bc0a51e..., 03c712a7..., 67508beb..., 965063f8..., fd301589...
```

Networks preserved: `unms_internal`, `unms_public`.

### SBDerbyNet — to be deployed

Target layout:
- Repo at `/opt/sbderbynet/` (clone of github.com/jimidarke/sbderbynet)
- Data at `/opt/derbynet/production/data/` (bind-mounted into containers per
  `installer/docker-cloud/docker-compose.production.yml`, owner `33:33` for
  www-data)
- Containers: `derbynet-caddy`, `derbynet-mqtt`, `derbynet-web`, `derbynet-race-server`

## Common recipes

### Audit (read-only, refresh state)

Single SSH session, prints host info, ports, docker, disk, RAM:

```sh
ssh -i ~/.ssh/sbderby_vps_ed25519 -p 22 claude@uisp.darketech.ca '
echo "=== HOST ==="; hostname; uptime; uname -srm
echo; echo "=== RESOURCES ==="; free -h; df -h /
echo; echo "=== PORTS ==="; sudo ss -tlnp 2>/dev/null
echo; echo "=== DOCKER ==="; sudo docker ps -a --format "table {{.Names}}\t{{.Status}}"
echo; echo "=== UISP STATE ==="
sudo docker inspect $(sudo docker ps -aq --filter label=com.docker.compose.project=unms) \
  --format "{{.Name}}: state={{.State.Status}} restart={{.HostConfig.RestartPolicy.Name}}" 2>/dev/null
'
```

### Bootstrap SBDerbyNet (first-time)

Replace `<TAG>` with the desired tag (e.g. `v0.9.1`).

```sh
# 1. Data directory (bind-mount target — referenced by docker-compose.production.yml)
sudo mkdir -p /opt/derbynet/production/data
sudo chown 33:33 /opt/derbynet/production/data

# 2. Clone repo
sudo mkdir -p /opt/sbderbynet && sudo chown $(id -u):$(id -g) /opt/sbderbynet
git clone https://github.com/jimidarke/sbderbynet /opt/sbderbynet
cd /opt/sbderbynet
git checkout <TAG>

# 3. Configure environment
cd installer/docker-cloud
cp .env.example .env
$EDITOR .env   # set DERBYNET_CLOUD_MODE=public, MQTT_PASS, VIRTUAL_MQTT_PASS

# 4. Provision broker users (creates derbynet + virtual-device, password file)
./scripts/setup-mqtt-auth.sh

# 5. Create production data directory permissions, then bring stack up
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d

# 6. Verify
curl -fsS http://localhost/health
docker compose ps
```

### Update SBDerbyNet to a new tag

```sh
cd /opt/sbderbynet
git fetch --tags && git checkout <NEW_TAG>
cd installer/docker-cloud
docker compose -f docker-compose.yml -f docker-compose.production.yml pull
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d
```

### Tail logs

```sh
ssh ... 'cd /opt/sbderbynet/installer/docker-cloud && \
  docker compose -f docker-compose.yml -f docker-compose.production.yml logs -f --tail=100'
```

### Sync DB from Pi

The Pi's `extras/soapbox/infra/server/cloud-sync.sh` writes to
`/opt/derbynet/production/data/derbynet.sqlite3` over SCP — that path is
bind-mounted into the containers at `/var/lib/derbynet`, so the synced DB
appears immediately. Same path for the `.cloud_readonly` sentinel.

To verify a recent sync from the cloud side:
```sh
ssh ... 'cat /opt/derbynet/production/data/.cloud_readonly'
```

## Restoring UISP (when SBDerbyNet is decommissioned)

```sh
ssh ... '
# 1. Stop SBDerbyNet
cd /opt/sbderbynet/installer/docker-cloud
sudo docker compose -f docker-compose.yml -f docker-compose.production.yml down

# 2. Re-enable UISP self-update cron
sudo mv /etc/cron.d/unms-update.disabled-by-claude-* /etc/cron.d/unms-update

# 3. Restore restart policies
for c in unms-postgres unms-rabbitmq unms-fluentd unms-siridb \
         unms-api unms-nginx unms-netflow unms-device-ws-1 ucrm; do
  sudo docker update --restart=always "$c"
done

# 4. Start in dependency order
sudo docker start unms-postgres unms-rabbitmq unms-fluentd
sleep 5
sudo docker start unms-siridb unms-api unms-nginx unms-netflow ucrm unms-device-ws-1

# 5. Verify
sudo docker ps --filter label=com.docker.compose.project=unms
'
```

## Coexistence notes

- **Port collision**: UISP nginx and SBDerbyNet Caddy both want 80/443. They
  cannot both run. Always silo one before bringing the other up.
- **RAM**: with UISP off, ~3.0 GB available. SBDerbyNet uses ~700 MB. Headroom is plenty.
- **Disk**: `/var/lib/docker` ~3.9 GB before SBDerbyNet (UISP images + volumes).
  Adding SBDerbyNet images ≈ +1 GB. Plenty of free disk (46 GB+) regardless.

## Maintenance

- Apt updates accumulate on `noble-updates` (regular updates) — `unattended-upgrades` only auto-installs `*-security` by default. Run `sudo apt-get upgrade && sudo apt autoremove && sudo reboot` periodically; the autoremove will clean up the stack of old kernels.
- Don't enable Docker auto-pull / Watchtower without coordination — the
  cloud-sync sentinel relies on the bind-mount path being stable.
- Ubuntu Pro is available but not attached. Free for personal use up to 5 machines; would extend security-update coverage. Optional.

## Things this skill does NOT cover

- **Pi side** (race-day master). See `extras/soapbox/CLAUDE.md` and `docs/CICD.md`.
- **Race-day operations**. See `docs/PULL_FORWARD_OPERATOR.md` and `docs/DRESS_REHEARSAL.md`.
- **GitHub Actions deployment.** The CI deploys to staging+production VPS targets;
  see `.github/workflows/deploy.yml` and `docs/CICD.md`. This skill is for direct VPS access.

## Security reminders

- The `claude` user has passwordless sudo. It exists only for ad-hoc validation. **Remove when not actively used** (see "Key cleanup" above).
- The `~/.ssh/sbderby_vps_ed25519` private key lives in this Claude Code workspace; treat as session-scoped.
- Never share the contents of `installer/docker-cloud/.env` (contains MQTT passwords) in chat or commits — the `.env` file is in `.gitignore`.
- The Mosquitto ACL at `installer/docker-cloud/mosquitto/acl` enumerates `B_*` topics explicitly; if a new virtual device hwid is introduced, add corresponding lines or it won't authorize.

# Server-Side Logging Map

Where every log line ends up on the SBDerbyNet cloud twin, and how to find
it fast. For the Pi side see `extras/soapbox/CLAUDE.md` and
`extras/soapbox/infra/server/LOGGING.md`.

## TL;DR

```sh
./scripts/derbyvps.sh logs --where        # prints the live map
./scripts/derbyvps.sh logs                # tail all services
./scripts/derbyvps.sh logs derbynet-web   # tail one service
```

## The map

### Container stdout (rotated automatically)

Every service writes its main log stream to the container's stdout. Docker's
json-file driver captures it. We've configured rotation in
`installer/docker-cloud/docker-compose.yml`: **max 10 MB × 3 files per
service** (so up to ~30 MB per container, no disk-fill risk).

| Service | What's in stdout | How to read |
|---|---|---|
| `derbynet-caddy` | HTTP access log + LE cert events + redirect/proxy decisions | `derbyvps.sh logs caddy` |
| `derbynet-mqtt` | broker startup + connect/disconnect events + ACL denials | `derbyvps.sh logs mqtt` |
| `derbynet-web` | nginx access log + PHP-FPM startup + PHP application errors | `derbyvps.sh logs derbynet-web` |
| `derbynet-race-server` | derbylogger.py output (set `DERBY_CONSOLE_LOG=true` in `.env`) | `derbyvps.sh logs race-server` |

Direct access without the wrapper:

```sh
ssh ... 'sudo docker logs derbynet-caddy --tail=200'
ssh ... 'sudo docker logs -f derbynet-mqtt'
```

### Persistent volume-backed files

Volumes survive container recreates (deploys, restarts, image updates).
None of these are size-capped at the volume level — keep an eye via
`sudo du -sh /var/lib/docker/volumes/*/_data`. They're typically tiny.

| File (inside container) | Volume name | What's in it |
|---|---|---|
| `/var/log/nginx/access.log` | `derbynet_web_nginx_logs` | request-by-request access log with timing |
| `/var/log/nginx/error.log`  | `derbynet_web_nginx_logs` | nginx-level errors (502s, timeouts, syntax) |
| `/var/log/php83/error.log`  | `derbynet_web_php_logs` | PHP application errors and warnings (`error_log = /var/log/php83/error.log` set in `99-sbderbynet-logging.ini`) |
| `/var/log/derbynet.log`     | `derbynet_logs` | derbylogger.py text format (only when `DERBY_CONSOLE_LOG=false`) |
| `/var/log/derbynet.jsonl`   | `derbynet_logs` | derbylogger.py JSON format |
| `/mosquitto/log/mosquitto.log` | `mqtt_log` | broker file log (in addition to stdout) |

Quick way to peek a volume without exec'ing into the container:

```sh
ssh ... 'sudo docker run --rm -v derbynet_web_nginx_logs:/v alpine \
         tail -50 /v/access.log'
```

### Wrapper deploy trail

Every SSH call `derbyvps.sh` makes is logged to two places, with timestamps:

| Path | Lifetime |
|---|---|
| `scripts/.derbyvps-deploy.log` (dev box) | unbounded; gitignored |
| `/var/log/sbderbynet-deploy.log` (VPS) | rotated weekly, keep 4 (`/etc/logrotate.d/sbderbynet`) |

Tail the remote one in real time during a deploy:

```sh
ssh ... 'sudo tail -f /var/log/sbderbynet-deploy.log'
```

### Host-level systemd journal

`journalctl` captures system-level events (kernel, sshd, docker daemon
itself, cloud-init). Useful for:

- `sudo journalctl -u docker` — docker daemon issues
- `sudo journalctl -u ssh -p err` — SSH errors and brute-force attempts
- `sudo journalctl --since "1 hour ago"` — recent everything

Default systemd retention applies (`/var/log/journal/` is currently around
4 GB on this VPS — normal for 67 days of uptime).

## What goes where for common questions

> **"Did Caddy serve my request?"** → `derbyvps.sh logs caddy` (every request
> appears with status code, response time, and which backend served it)

> **"Why is `/derbynet/foo.php` 500-ing?"** → first look at
> `derbyvps.sh logs derbynet-web` for the PHP error; for persistent records
> read `/var/log/php83/error.log` from the `derbynet_web_php_logs` volume

> **"Did a virtual device connect to the broker?"** → `derbyvps.sh logs mqtt`
> shows connect/disconnect events; `/mosquitto/log/mosquitto.log` has the
> same content but persists across container recreates

> **"What did the race server do during heat 5?"** → currently `docker logs
> derbynet-race-server` (we have `DERBY_CONSOLE_LOG=true`). To get the file
> form with correlation IDs, flip `DERBY_CONSOLE_LOG=false` in `.env` and
> deploy; the race-server then writes `/var/log/derbynet.log` and
> `/var/log/derbynet.jsonl` (visible via `derbynet_logs` volume).

> **"What changed on the VPS in the last week?"** →
> `sudo less /var/log/sbderbynet-deploy.log`. Every deploy lists tag,
> timestamp, deployer, and full SSH commands.

## Things this map deliberately does NOT cover

- **Off-host log shipping.** No Loki, no Splunk, no journald-remote. If you
  ever scale beyond one VPS, this is where to add it. For one cloud twin,
  `docker logs` + the volume files are enough.
- **Audit logs for race-server actions.** The race-server writes results
  directly to SQLite — to reconstruct race history use the `RaceChart` and
  `Events` tables, not log files.
- **HTTP access log shipping.** Nginx access log stays on the VPS. If you
  ever want analytics, point a tool at `derbynet_web_nginx_logs` volume.

## Disk usage sanity check

Run `derbyvps.sh audit` at any time. The "RESOURCES" section reports
`df -h /`. As a rough budget for race day:

- Containers: ≤ 120 MB total log (4 services × 30 MB cap)
- Volumes: typically < 50 MB total unless something's wrong
- Race DB: small (few MB even for a full event)

If `df` shows < 4 GB free, the wrapper's preflight will refuse to deploy.

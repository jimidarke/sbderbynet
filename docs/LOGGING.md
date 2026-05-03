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

## Findings & lessons (real bugs caught by this map)

### The `json_failure()` self-crash (caught 2026-05-03, fixed in v0.9.6)

**Symptom**: every action that called `json_failure()` returned a stack
trace fragment like `Call to undefined function derby_get_error_details()`.
In the UI this looked like generic "save failed" or worse — completely
silent failures, since some AJAX call sites swallowed non-JSON responses.

**Root cause**: `website/action.php:51` called `derby_get_error_details()`
with a `derby_` prefix that doesn't exist. The actual helper in
`website/inc/error-codes.inc:476` is named `get_error_details()`. A
one-character typo masked **every error message in the entire app**.

**How we found it**: posted the failing request from inside the web
container (`docker exec derbynet-web curl ... action.php`) and read the
raw PHP exception from the response body. Without the volume-mounted
`/var/log/php83/error.log` (added in v0.9.4), this would have been
visible only as a ~200-byte JSON `outcome.summary: failure` with no
context — exactly what a frustrated operator would see.

**Lesson**: if a `json_failure()` call site reports a strange error,
*reproduce the request from inside the container with curl* and look at
the raw response. The AJAX layer in the browser swallows much of what
the server actually sent.

### Setup creates dirs under the document root

**Symptom**: clean DB initialization through `setup.php` failed with
`Unable to create test subdirectory: /var/www/html/Data/test/<year>/...`

**Root cause**: legacy DerbyNet behavior — `setup.nodata` creates
per-event scratch dirs (racers, cars, videos, etc.) under
`$docroot/Data/test/<year>/<event>/` in addition to the real database
under `default_database_directory()`. In a container, `$docroot` is
`/var/www/html` and isn't writable by the unprivileged Alpine PHP-FPM
`nobody` user.

**Fix (v0.9.6)**: `Dockerfile.web` now `mkdir -p -m 777 ${WWW_ROOT}/Data`
during build. *Caveat*: contents under that dir live in the container's
writable layer, not a volume — they don't survive deploys. Acceptable
since the actual SQLite file is under `/var/lib/derbynet` (bind-mounted,
persistent).

**Lesson**: when running upstream PHP apps in containers, audit anywhere
the app calls `mkdir` against the document root or the install path. The
Pi build (Ansible-managed) doesn't see this issue because there the
docroot IS the install dir and is writable.

### Resetting the cloud twin to a clean setup state

If you ever need to wipe a created event and return the cloud twin to
the fresh-setup wizard:

```sh
ssh -i ~/.ssh/sbderby_vps_ed25519 -p 22 claude@uisp.darketech.ca '
  sudo rm -fv /opt/derbynet/production/data/config-database.inc \
              /opt/derbynet/production/data/config-roles.inc
  sudo rm -rfv /opt/derbynet/production/data/<year>
  sudo docker exec derbynet-web sh -c "rm -rf /var/www/html/Data/test"
'
```

`config-database.inc` is the pointer PHP uses to skip setup. Removing it
*and* the year subdir(s) is enough; PHP regenerates both during the
next setup run.

### Recurring pattern: bugs hidden until real bootstrap

The cloud stack accumulated a backlog of unsurfaced bugs because nobody
had previously brought it up end-to-end with auth on. We hit them in
order during the first live bootstrap:

1. Mosquitto ACL syntax (illegal `B_+` wildcard) — *v0.9.1*
2. MQTT.js fetched at runtime from a CDN — *v0.9.1*
3. Production volume bind path didn't match cloud-sync.sh — *v0.9.1*
4. psutil source build needs gcc on Alpine — *v0.9.2*
5. CRLF line endings on installer shell scripts — *v0.9.2*
6. Mosquitto healthcheck used unauth `$SYS/#` topic — *v0.9.2*
7. `setup-mqtt-auth.sh` wrote `passwd` mode 600 root-only — *v0.9.2*
8. nginx serves at `/`, website hard-codes `/derbynet/` — *v0.9.2*
9. Bind-mount uid mismatch (Alpine `nobody` vs Debian `www-data`) — *v0.9.2*
10. `rsync` without `--inplace` confused docker bind mounts — *v0.9.2*
11. Caddy bound only `:80`, browsers default to HTTPS — *v0.9.3*
12. `json_failure()` self-crash (this doc) — *v0.9.6*
13. `setup.nodata` creates dirs under read-only docroot — *v0.9.6*

**Lesson**: a "test environment" that isn't actually exercised every
release accumulates these silently. Track 1–2 commits worth of headroom
for similar surprises during any future first-run on a new host.

## Disk usage sanity check

Run `derbyvps.sh audit` at any time. The "RESOURCES" section reports
`df -h /`. As a rough budget for race day:

- Containers: ≤ 120 MB total log (4 services × 30 MB cap)
- Volumes: typically < 50 MB total unless something's wrong
- Race DB: small (few MB even for a full event)

If `df` shows < 4 GB free, the wrapper's preflight will refuse to deploy.

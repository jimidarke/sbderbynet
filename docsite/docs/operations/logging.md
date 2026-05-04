# Logging

Where every server-side log line lands on the SBDerbyNet cloud twin, and how to find it fast. For the Pi side see `extras/soapbox/CLAUDE.md` and `extras/soapbox/infra/server/LOGGING.md`.

## TL;DR

```sh
./scripts/derbyvps.sh logs --where        # prints the live map
./scripts/derbyvps.sh logs                # tail all services
./scripts/derbyvps.sh logs derbynet-web   # tail one service
```

---

## Container stdout (rotated automatically)

Every service writes its main log to stdout. Docker's json-file driver captures it; rotation is set in `installer/docker-cloud/docker-compose.yml` to **10 MB × 3 files per service** (≤ 30 MB per container).

| Service | What's in stdout | Read with |
|---|---|---|
| `derbynet-caddy` | HTTP access log + LE cert events + redirect/proxy decisions | `derbyvps.sh logs caddy` |
| `derbynet-mqtt` | broker startup + connect/disconnect events + ACL denials | `derbyvps.sh logs mqtt` |
| `derbynet-web` | nginx access log + PHP-FPM startup + PHP application errors | `derbyvps.sh logs derbynet-web` |
| `derbynet-race-server` | derbylogger.py output (when `DERBY_CONSOLE_LOG=true` in `.env`) | `derbyvps.sh logs race-server` |

Direct access without the wrapper:

```sh
ssh ... 'sudo docker logs derbynet-caddy --tail=200'
ssh ... 'sudo docker logs -f derbynet-mqtt'
```

---

## Persistent volume-backed files

Volumes survive container recreates. None are size-capped at the volume level — keep an eye via `sudo du -sh /var/lib/docker/volumes/*/_data`. They're typically tiny.

| File (in container) | Volume | What's in it |
|---|---|---|
| `/var/log/nginx/access.log` | `derbynet_web_nginx_logs` | request-by-request access log with timing |
| `/var/log/nginx/error.log`  | `derbynet_web_nginx_logs` | nginx-level errors (502s, timeouts, syntax) |
| `/var/log/php83/error.log`  | `derbynet_web_php_logs` | PHP errors and warnings (`error_log` set in `99-sbderbynet-logging.ini`) |
| `/var/log/derbynet.log`     | `derbynet_logs` | derbylogger.py text format (when `DERBY_CONSOLE_LOG=false`) |
| `/var/log/derbynet.jsonl`   | `derbynet_logs` | derbylogger.py JSON format |
| `/mosquitto/log/mosquitto.log` | `mqtt_log` | broker file log |

Peek a volume without exec'ing into the container:

```sh
ssh ... 'sudo docker run --rm -v derbynet_web_nginx_logs:/v alpine \
         tail -50 /v/access.log'
```

---

## Wrapper deploy trail

Every SSH call `derbyvps.sh` makes is logged to two places, with timestamps:

| Path | Lifetime |
|---|---|
| `scripts/.derbyvps-deploy.log` (dev box) | unbounded; gitignored |
| `/var/log/sbderbynet-deploy.log` (VPS) | rotated weekly, keep 4 (`/etc/logrotate.d/sbderbynet`) |

Tail the remote one in real time:

```sh
ssh ... 'sudo tail -f /var/log/sbderbynet-deploy.log'
```

---

## Host systemd journal

`journalctl` for system-level events (kernel, sshd, docker daemon, cloud-init):

- `sudo journalctl -u docker`
- `sudo journalctl -u ssh -p err`
- `sudo journalctl --since "1 hour ago"`

---

## Common questions

> **"Did Caddy serve my request?"** → `derbyvps.sh logs caddy` (every request appears with status, response time, backend).

> **"Why is `/derbynet/foo.php` 500-ing?"** → `derbyvps.sh logs derbynet-web` first; for persistent records read `/var/log/php83/error.log` from the `derbynet_web_php_logs` volume.

> **"Did a virtual device connect to the broker?"** → `derbyvps.sh logs mqtt`; `/mosquitto/log/mosquitto.log` persists across container recreates.

> **"What did the race server do during heat 5?"** → currently `docker logs derbynet-race-server` (`DERBY_CONSOLE_LOG=true`). For file form with correlation IDs, flip `DERBY_CONSOLE_LOG=false` in `.env` and deploy.

> **"What changed on the VPS in the last week?"** → `sudo less /var/log/sbderbynet-deploy.log`. Every deploy lists tag, timestamp, deployer, and full SSH commands.

---

## What this map does not cover

- **Off-host log shipping.** No Loki / Splunk / journald-remote. For one cloud twin, `docker logs` + volume files are enough.
- **Audit logs for race-server actions.** The race-server writes results directly to SQLite — to reconstruct race history use the `RaceChart` and `Events` tables.
- **HTTP access log shipping.** Stays on the VPS. Point a tool at `derbynet_web_nginx_logs` volume for analytics.

---

## Findings & lessons (real bugs caught by this map)

### `json_failure()` self-crash (caught 2026-05-03, fixed in v0.9.6)

**Symptom**: every action calling `json_failure()` returned a stack-trace fragment like `Call to undefined function derby_get_error_details()`. UI surface: generic "save failed" or silent failures.

**Root cause**: `website/action.php:51` called `derby_get_error_details()` with a `derby_` prefix that doesn't exist. Actual helper in `website/inc/error-codes.inc:476` is `get_error_details()`. One-character typo masked **every** error message in the app.

**How we found it**: posted the failing request from inside the web container (`docker exec derbynet-web curl ... action.php`) and read the raw PHP exception. Without the volume-mounted `/var/log/php83/error.log` (added v0.9.4) this would have been a ~200-byte JSON `outcome.summary: failure` with no context.

**Lesson**: when `json_failure()` reports a strange error, *reproduce the request from inside the container with curl* and look at the raw response. The AJAX layer in the browser swallows much of what the server sent.

### Setup creates dirs under the document root

**Symptom**: clean DB initialization through `setup.php` failed with `Unable to create test subdirectory: /var/www/html/Data/test/<year>/...`

**Root cause**: legacy DerbyNet — `setup.nodata` creates per-event scratch dirs under `$docroot/Data/test/...` in addition to the real database under `default_database_directory()`. In a container, `$docroot` is `/var/www/html`, not writable by Alpine PHP-FPM `nobody`.

**Fix (v0.9.6)**: `Dockerfile.web` now `mkdir -p -m 777 ${WWW_ROOT}/Data` during build. *Caveat*: contents under that dir live in the container's writable layer, not a volume — they don't survive deploys. Acceptable since the actual SQLite file is bind-mounted at `/var/lib/derbynet`.

**Lesson**: when running upstream PHP apps in containers, audit anywhere the app calls `mkdir` against the document root. The Pi build doesn't see this because docroot IS the install dir there.

### Resetting the cloud twin to a clean setup state

```sh
ssh -i ~/.ssh/sbderby_vps_ed25519 -p 22 claude@uisp.darketech.ca '
  sudo rm -fv /opt/derbynet/production/data/config-database.inc \
              /opt/derbynet/production/data/config-roles.inc
  sudo rm -rfv /opt/derbynet/production/data/<year>
  sudo docker exec derbynet-web sh -c "rm -rf /var/www/html/Data/test"
'
```

`config-database.inc` is the pointer PHP uses to skip setup. Removing it *and* the year subdir(s) is enough; PHP regenerates both during the next setup run.

---

## Recurring pattern: bugs hidden until real bootstrap

The cloud stack accumulated a backlog of unsurfaced bugs because nobody had brought it up end-to-end with auth on. We hit them in order during the first live bootstrap:

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
12. `json_failure()` self-crash (above) — *v0.9.6*
13. `setup.nodata` creates dirs under read-only docroot — *v0.9.6*
14. PHP-FPM `clear_env=yes` strips `DERBYNET_CLOUD_MODE` — *v0.9.8*
15. `paho-mqtt==1.6.1` pinned but code uses v2 `CallbackAPIVersion` — *v0.9.8*
16. `result.error_string` (paho v1) vs `mqtt.error_string(rc)` (v2) — *v0.9.8*
17. Pi-only `hostname -I` / `vcgencmd` crash on Alpine — *v0.9.8*
18. `derbyapi.py` hardcoded `/derbynet/` API path — *v0.9.8*
19. `derbyTime.py` missing `username_pw_set` + `loop_start` — *v0.9.9*
20. `virtual/_guard.inc` missing `session_start()` — *v0.9.10*
21. JS sent `GET ?action=...` against POST-only dispatcher — *v0.9.11*
22. Browser cache held stale virtual JS after deploy — *v0.9.14*

**Lesson**: a "test environment" that isn't actually exercised every release accumulates these silently. Track 1–2 commits of headroom for similar surprises during any future first-run on a new host.

---

## Patterns worth automating

Looking back at the 22 fixes above, several share a shape that would be caught by a CI smoke test against a real cloud-twin deploy:

- **Auth-required endpoints surfaced as 5xx/cryptic errors** (#12, #20, #21). A "log in as RaceCoordinator, hit every action.* endpoint, expect a valid JSON `outcome`" pass would catch all three.
- **Container-runtime drift from the Pi** (#9, #14, #17, #18). Each surfaced because cloud and Pi runtimes diverge subtly. A cloud-only env probe asserting `is_cloud_mode() === true && DERBYNET_CLOUD_MODE === 'public'` inside PHP-FPM would catch #14.
- **Library version drift** (#15, #16, #19). `paho-mqtt` 1→2 is a real API break. Pin Python deps + smoke-test that imports race-server modules.
- **Browser caching across deploys** (#22). Mitigated by `virtual_asset_v()` cache-busting; an HTTP-level test asserting every `<script src>` includes `?v=` would prevent regressions.

See [Testing](../development/testing.md) for the structured proposal.

---

## Disk usage sanity check

Run `derbyvps.sh audit` any time. The "RESOURCES" section reports `df -h /`. As a rough budget for race day:

- Containers: ≤ 120 MB total log (4 services × 30 MB cap)
- Volumes: typically < 50 MB total unless something's wrong
- Race DB: small (few MB even for a full event)

If `df` shows < 4 GB free, the wrapper's preflight refuses to deploy.

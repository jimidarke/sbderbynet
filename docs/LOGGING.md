# Server-Side Logging Map

Where every log line ends up on the SBDerbyNet cloud twin, and how to find
it fast. For the on-track (race-day) side jump to
[Race-day (on-Pi) logging map](#race-day-on-pi-logging-map) below; for the
unified framework itself see `extras/soapbox/infra/server/LOGGING.md`.

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
14. PHP-FPM `clear_env=yes` strips `DERBYNET_CLOUD_MODE` — *v0.9.8*
15. `paho-mqtt==1.6.1` pinned but code uses v2 `CallbackAPIVersion` — *v0.9.8*
16. `result.error_string` (paho v1) vs `mqtt.error_string(rc)` (v2) — *v0.9.8*
17. Pi-only `hostname -I` / `vcgencmd` crash on Alpine — *v0.9.8*
18. `derbyapi.py` hardcoded `/derbynet/` API path — *v0.9.8*
19. `derbyTime.py` missing `username_pw_set` + `loop_start` — *v0.9.9*
20. `virtual/_guard.inc` missing `session_start()` — *v0.9.10*
21. JS sent `GET ?action=...` against POST-only dispatcher — *v0.9.11*
22. Browser cache held stale virtual JS after deploy — *v0.9.14*

**Lesson**: a "test environment" that isn't actually exercised every
release accumulates these silently. Track 1–2 commits worth of headroom
for similar surprises during any future first-run on a new host.

### Patterns worth automating

Looking back at the 22 fixes above, several share a shape that would be
caught by a CI smoke test against a real cloud-twin deploy:

- **Auth-required endpoints surfaced as 5xx/cryptic errors**
  (#12 json_failure, #20 session_start, #21 GET vs POST). A simple
  "log in as RaceCoordinator, hit every action.* endpoint, expect a
  valid JSON `outcome`" pass would have caught all three.
- **Container-runtime drift from the Pi**
  (#9 uid mismatch, #14 clear_env, #17 hostname/vcgencmd, #18 path).
  Each surfaced because the cloud and Pi runtimes diverge in subtle
  ways. A cloud-only "env probe" test that asserts
  `is_cloud_mode() === true && DERBYNET_CLOUD_MODE === 'public'`
  inside PHP-FPM would have caught #14 alone.
- **Library version drift** (#15, #16, #19). `paho-mqtt` 1→2 is a real
  API break. Pinning Python deps in `requirements.txt` plus a smoke
  test that imports race-server modules would make this loud.
- **Browser caching across deploys** (#22). Now mitigated by
  `virtual_asset_v()` cache-busting; an HTTP-level test that asserts
  every script src includes `?v=` would prevent regressions.

See `docs/TESTING.md` for a structured proposal of test categories,
priorities, and which of these fix patterns each one would have caught.

## Disk usage sanity check

Run `derbyvps.sh audit` at any time. The "RESOURCES" section reports
`df -h /`. As a rough budget for race day:

- Containers: ≤ 120 MB total log (4 services × 30 MB cap)
- Volumes: typically < 50 MB total unless something's wrong
- Race DB: small (few MB even for a full event)

If `df` shows < 4 GB free, the wrapper's preflight will refuse to deploy.

## Race-day (on-Pi) logging map

The on-track stack is more distributed than the cloud twin: there's no
Docker, the network is isolated (`192.168.100.0/24`), and four classes of
device write logs (race-server Pi, finishtimer Pis, ESP32 start timer,
derby displays). All of them converge on **one file on the race-server Pi**
via rsyslog UDP.

### One file to rule them all

`/var/log/derbynet.jsonl` on the race-server Pi (192.168.100.10) is the
single canonical timeline. Every component — local Python, PHP, finishtimer
Pis over rsyslog UDP 514, ESP32 over rsyslog UDP 514 — ends up in this file
with a consistent JSONL schema:

```json
{"ts":"2026-05-20T09:00:01.523-06:00","level":"INFO","device":"FINISH2",
 "component":"finishtimer","msg":"Toggle Changed to: False",
 "corr_id":"heat-3-7-1716230400123","seq":42}
```

The `corr_id` field is the heat correlation_id (see
`extras/soapbox/infra/server/LOGGING.md#heat-correlation-ids`); it lets you
filter every component's events for a single heat with one tool.

### Per-component map

| Component | Local file | Forwarded? | Persistence | NTP source |
|---|---|---|---|---|
| Race-server Pi | `/var/log/derbynet.{log,jsonl}` | n/a (this *is* the destination) | DS3231 RTC + chrony; daily gz archives under `/var/lib/derbynet/logs/archive/` | chrony with public NTP + RTC fallback |
| Finishtimer Pi (each lane) | `/var/log/derbynet.log` + systemd-journald (20 MB ring) | rsyslog UDP → race-server | journald survives reboot; rsyslog forwarding is the primary durable path | systemd-timesyncd → `192.168.100.10` |
| ESP32 start timer | — (no persistent storage) | UDP syslog → race-server:514 | ephemeral on device; race-server file is the only record | `ntptime.settime()` against `192.168.100.10`; publishes a retained `ntp-synced` anchor event after sync |
| Derby display | journald + rsyslog UDP → race-server | yes | journald local; race-server canonical | systemd-timesyncd → `192.168.100.10` |
| Mosquitto broker | `/mosquitto/log/mosquitto.log` + syslog | yes | broker keeps connects/disconnects | n/a |

### Time discipline

- **Race-server Pi**: DS3231 hardware RTC (Ansible role `extras/derbypi/ansible/roles/rtc/`) plus chrony with `refclock PHC /dev/ptp0` as fallback. Serves NTP to `192.168.100.0/24`.
- **Finishtimer Pis**: `systemd-timesyncd` with `NTP=192.168.100.10` set by `extras/soapbox/infra/finishtimer/setup.sh`.
- **ESP32**: blocking `ntptime.settime()` against `192.168.100.10` at boot; emits a retained `ntp-synced` MQTT event after success so the chronology tool knows when its clock became trustworthy.
- **Race-day go/no-go check** (cross-reference `docs/DRESS_REHEARSAL.md`): `chronyc tracking` on race-server and `timedatectl show-timesync` on each finishtimer Pi should show offsets under 10 ms after 5 minutes of network uptime. Expected chronology resolution: ±100 ms.

### Event payload precision

Race events carry timestamps captured at the **GPIO edge**, not at MQTT publish time, with **0.1 s** precision:

| Source | Topic | Fields |
|---|---|---|
| Finishtimer toggle | `derbynet/device/{hwid}/state` | `timestamp` (GPIO edge), `publish_ts`, `seq`, `correlation_id` |
| Start timer | `derbynet/device/starttimer/state` | `timestamp` (GPIO edge), `publish_ts`, `ntp_sync_ts`, `correlation_id` |
| Start timer NTP anchor | `derbynet/device/starttimer/status` | retained `{"status":"ntp-synced","timestamp":...}` |

The race server (`derbyRace.py`) uses the device-supplied start timestamp as the canonical race start, *not* its own wall-clock at receipt, and logs both so the offset is auditable.

### Reconstructing a heat

```sh
# Round 3, heat 7 — full timeline, all components
derby-chronology --heat 3/7

# Same but pull rotated archives if the live file has been rolled
derby-chronology --heat 3/7 --include-archives

# Include broker connect/disconnect anchors
derby-chronology --heat 3/7 --mqtt-log

# Markdown report for an incident write-up
derby-chronology --heat 3/7 --format md > incident-heat-3-7.md
```

The header block reports per-device entry counts, NTP-sync anchors, the start-event device/server offset, and the per-lane GPIO-edge→publish latency distribution.

### Things on-Pi logging deliberately does NOT do

- **No off-host shipping for race-day operations.** All ingest happens locally so the race is independent of internet. The separate `logsync.py` ships `/var/log/derbynet.jsonl` to the cloud only after the race (or in background on a 5-minute timer) — see `extras/saasbox/CLAUDE.md`.
- **No live log query UI on race day.** `derby-chronology` is the post-hoc tool. If you want live, tail `/var/log/derbynet.log`.

# Test Plan — What to Consider

Race day in ~30 days. The cloud twin works end-to-end now, but the path
there exposed 22 latent bugs that nothing automated caught. This doc
proposes test categories worth investing in, in priority order.

It's not a spec — it's a **conversation about coverage**. Implement what
matches the time you have. The first three categories alone would have
caught the majority of what we hit.

## Existing test surface (what we already have)

| Suite | Lives in | Runs against |
|---|---|---|
| Pull-forward backend | `testing/test-pull-forward.sh` | curl against running stack — 9 scenarios |
| Pull-forward UI | `testing/puppeteer/pull-forward-test.js` | Puppeteer with mocked AJAX — 11 scenarios |
| Cloud stack smoke | `testing/puppeteer/virtual-device-test.js` | Live cloud stack — opens virtual pages, asserts MQTT-WS connect |
| MQTT replay | `testing/replay-real-race.py` | Captured Pi session against any broker |
| Race-server unit | `extras/soapbox/infra/server/tests/` (pytest) | Mocked MQTT — heartbeat tests pass |

What's missing: **anything that would have caught the 22 cloud-bringup bugs.**

## Priority A — must-have before race day

### A1. Cloud-twin smoke test (post-deploy gate)

A scripted dry-run of the full coordinator workflow against a live cloud
stack, run after every deploy. The `derbyvps.sh deploy` postflight already
checks containers + `/health`; this extends it to user-flow validation.

**Concrete checks** (pseudo-shell, all curl + cookie jar):

```
1. POST role.login as RaceCoordinator        → outcome.success
2. POST role.login as Timer (no password)    → outcome.success, role=Timer
3. GET  /derbynet/index.php                  → 200, contains "Race Dashboard"
4. GET  /derbynet/coordinator.php            → 200
5. GET  /derbynet/virtual/index.php (auth)   → 200, contains "vd-index-card"
6. POST action=virtual-mqtt-creds (auth)     → outcome.success, has user+pass
7. POST action=virtual-mqtt-creds (no auth)  → outcome.failure, code=notauthorized
8. GET  every <link>/<script> in index.php returns 200
9. Subscribe derbynet/race/time for 3s       → ≥2 messages received
10. Probe action.php for empty post          → no PHP exception in body
```

**Catches**: items 12, 14, 19, 20, 21 from the recurring-bugs list, plus
any future "endpoint exists but crashes on hit".

**Effort**: ~1 day to write as a Bash script in `testing/test-cloud-smoke.sh`.

### A2. Permission boundary matrix

For every interactive endpoint, assert it returns the right outcome for
each role. The matrix is small (≈4 roles × ~20 endpoints) and most cells
are "denied".

| Endpoint | '' (anon) | Timer | Photo | RaceCrew | RaceCoordinator |
|---|---|---|---|---|---|
| action=role.login | ok | ok | ok | ok | ok |
| action=racer.dropout | denied | denied | denied | ok? | ok |
| action=schedule.pullforward | denied | denied | denied | denied | ok |
| action=virtual-mqtt-creds | denied | denied | denied | denied | ok |
| action=heat.select | denied | denied | denied | ok? | ok |
| query=poll.coordinator | denied | denied | denied | ok | ok |
| GET /coordinator.php | redirect | denied | denied | ok | ok |
| GET /virtual/index.php | redirect | 403 | 403 | 403 | ok |

**Catches**: privilege escalation regressions, accidental loosening of
the cloud-mode + coordinator gate on virtual pages, and the "every error
looks identical" symptom from json_failure().

**Effort**: ~half a day. Best as a parameterized shell script that loops
the matrix and reports the first cell that disagrees.

### A3. Pull-forward Pi rehearsal (live hardware)

Already documented in `docs/DRESS_REHEARSAL.md` Part B. Currently a
manual checklist; no automation. For race-day confidence:

- Capture the MQTT session once (G3 from the plan)
- Replay against the cloud broker (G6) and assert the resulting RaceChart
  matches the original byte-for-byte
- Bonus: assert the **broadcast text** ("Justin (#17) please report to
  staging — moved to Heat 5") appears verbatim on a kiosk page during
  the replay

**Catches**: any future regression in the schedule-adjuster, kiosk
broadcast plumbing, or the now-fixed json_failure / session_start chain.

**Effort**: ~1 day to capture + write the assertions. Replay script
already exists.

## Priority B — high value, lower urgency

### B1. Container-runtime probes

A small set of assertions that would catch Alpine-vs-Pi divergences:

- PHP-FPM env: `is_cloud_mode()` returns true; `$_SERVER['DERBYNET_CLOUD_MODE']` is `public`; `MQTT_USER` reachable
- Race-server import: `python3 -c "import paho.mqtt.client as m; m.CallbackAPIVersion.VERSION2"` (catches paho version pin drift)
- nginx: `curl http://derbynet-web/` returns 200 or 302 (NOT 404 — catches docroot path issues)
- Caddy: `curl -k https://localhost/.well-known/acme-challenge/test` returns 404 (route exists), `wss://localhost/mqtt` upgrades

**Catches**: items 14–18 from the recurring-bugs list.

**Effort**: ~half a day. Add as a `derbyvps.sh probe` subcommand or a
script under `testing/probe-runtime.sh`.

### B2. Browser-virtual hardware E2E (cloud only)

Extend `testing/puppeteer/virtual-device-test.js` from "all pages reach
'connected'" to "drive a 4-heat round end-to-end and assert finish times
land in the DB":

```
For each heat 1..4:
  set all 3 finish-timer "ready" toggles
  click GO on start-timer
  click finish on each finish-timer at staggered intervals
  poll RaceChart for finishtime values
  assert all 3 lanes have a time in [1.0, 5.0] range
After:
  GET /derbynet/results.php → assert 12 rows of results, no DNFs
```

**Catches**: race-server result-recording regressions, MQTT topic-ACL
mismatches (would 401 the publish), and any future drift in the virtual
finish-timer payload format.

**Effort**: ~2 days because Puppeteer + multi-tab MQTT-WS is finicky.

### B3. Cloud-sync round-trip

Pi → cloud DB sync currently has no test. Capture a Pi DB snapshot,
compute its checksum, run `cloud-sync.sh`, fetch the cloud-side DB,
compute its checksum, assert they match within a few seconds of sync.

**Catches**: silent sync failures, bind-mount path mismatches (#3 was
this exact class of bug), and any future cron breakage on the Pi side.

**Effort**: ~half a day. Run from a Pi-side cron that emails on diff.

## Priority C — nice to have, low urgency

### C1. Schema migration regression

Run setup.php DB-creation, dump schema, diff against a committed
baseline schema. Detects unintentional table/column drift between
releases.

### C2. Soak / memory growth

Run the cloud stack for 24 hours under simulated load. Track per-container
RSS and disk-usage growth. Catches log-file blow-up risks (we capped
docker logs at 30 MB per container, but volumes are uncapped).

### C3. Disconnect / reconnect chaos

Kill the broker for 10 seconds; assert race-server reconnects, virtual
pages reconnect (LWT fires, then rejoin). Currently untested — we know
the LWT/reconnect path works in normal operation but haven't exercised
the disruption path.

### C4. Deploy → rollback → redeploy churn

Run `derbyvps.sh deploy` → introduce a deliberate breakage (e.g. invalid
docker-compose.yml) → assert auto-rollback kicks in → recover. The
wrapper has the code path; never tested in anger.

## Priority D — research / explore

### D1. Replay-as-fuzz

Take a known-good captured Pi session, mutate one MQTT message at a time
(swap two finish times, drop a heartbeat, send junk JSON to a topic),
replay, and assert the race-server doesn't crash. Cheap fuzzing that
exercises real shapes.

### D2. Static analysis

Run `phpstan` or `psalm` against the website/ tree. Catches things like
`derby_get_error_details` being called but never defined (#12). The
fix landed by accident; static analysis would have flagged it on commit.

## Where each priority would have helped

Mapping bugs to tests that would have caught them:

| # | Bug | Caught by |
|---|---|---|
| 1 | ACL `B_+` wildcard | A1 (publish probe), B1 (broker probe) |
| 2 | MQTT.js CDN dep | B2 (E2E loads JS) |
| 3 | Bind-mount path | B3 (sync round-trip), B1 (volume probe) |
| 4 | psutil source build | B1 (race-server import probe) |
| 5 | CRLF on installer scripts | A1 (deploy = build = catches) |
| 6 | Mosquitto unauth healthcheck | A1 (`docker compose ps` shows healthy=no) |
| 7 | passwd 600 root-only | A1 (broker fails to start = unhealthy) |
| 8 | nginx serves at `/` | A1 (curl /derbynet/ ≠ 404) |
| 9 | uid mismatch | B1 (write probe as PHP-FPM user) |
| 10 | rsync without `--inplace` | A1 (after deploy, assert config inside container matches host) |
| 11 | Caddy 80-only | A1 (HTTPS probe) |
| 12 | json_failure self-crash | A1 (any json_failure path), A2 (denied paths return clean json) |
| 13 | setup.nodata Data/test | A1 (run setup) |
| 14 | clear_env=yes | A1 (fetch creds), B1 (env probe) |
| 15 | paho-mqtt 1.6 pin | B1 (import probe) |
| 16 | error_string v1 vs v2 | C1 race-server smoke under load |
| 17 | hostname/vcgencmd | A1 (race-server starts cleanly) |
| 18 | hardcoded /derbynet/ | A1 (race-server reaches web app) |
| 19 | derbyTime auth+loop | A1 (subscribe race/time) |
| 20 | session_start | A1 (virtual page after login) |
| 21 | GET vs POST cred | A1 (cred endpoint), A2 (auth matrix) |
| 22 | browser cache | B2 (puppeteer doesn't cache by default) |

**13 of 22** would have been caught by **A1 alone** (cloud-twin smoke).
That's the highest-leverage investment.

## Suggested order of implementation

1. **A1** — cloud-twin smoke (1 day). Catches the most.
2. **A3** — Pi-rehearsal capture/replay (1 day). Locks in race-day baseline.
3. **A2** — permission matrix (½ day). Cheap insurance.
4. **B1** — runtime probes (½ day). Fast feedback for env drift.
5. Everything else is post-race-day polish.

Total Priority-A effort: ~2.5 days. Priority A+B: ~5 days. The full
list is roughly 2 weeks of test-engineering work; the 30-day runway has
room if there's appetite.

## What's NOT in scope

- **Hardware-in-the-loop** (real ESP32 finish timers) — covered by the
  Pi rehearsal manually.
- **Visual regression / screenshot diff** — overkill for a kids' race.
- **Mocking the MQTT broker** — the existing pytest fixtures are fine
  for unit tests; integration tests should hit a real Mosquitto
  (Docker container), not a mock.
- **Browser compat** — Chrome/Firefox/Safari testing. Cloud twin is
  for testing, not public-facing.

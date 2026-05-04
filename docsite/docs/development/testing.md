# Testing

Race day is on a tight runway. The cloud twin works end-to-end now, but reaching that state surfaced 22 latent bugs that no automation caught. This page proposes test categories worth investing in, in priority order.

It's a **conversation about coverage**, not a spec. The first three categories alone would have caught most of what we hit during cloud bringup.

---

## What we already have

| Suite | Lives in | Runs against |
|---|---|---|
| Pull-forward backend | `testing/test-pull-forward.sh` | curl against running stack — 10 scenarios; Test 10 asserts dry-run JSON == execute JSON |
| Pull-forward UI | `testing/puppeteer/pull-forward-test.js` | Puppeteer with mocked AJAX — 20 scenarios |
| Cloud-stack smoke | `testing/puppeteer/virtual-device-test.js` | live cloud stack — opens virtual pages, asserts MQTT-WS connect |
| MQTT replay | `testing/replay-real-race.py` | captured Pi session against any broker |
| Race-server unit | `extras/soapbox/infra/server/tests/` (pytest) | mocked MQTT — heartbeat tests pass |

What's missing: anything that would have caught the 22 cloud-bringup bugs (see [Logging — recurring patterns](../operations/logging.md#recurring-pattern-bugs-hidden-until-real-bootstrap)).

---

## Priority A — must-have before race day

### A1. Cloud-twin smoke test (post-deploy gate)

Scripted dry-run of the full coordinator workflow against a live cloud stack, run after every deploy. The `derbyvps.sh deploy` postflight already checks containers and `/health`; this extends it to user-flow validation.

Concrete checks (curl + cookie jar):

```
1.  POST role.login as RaceCoordinator        → outcome.success
2.  POST role.login as Timer (no password)    → outcome.success, role=Timer
3.  GET  /derbynet/index.php                  → 200, contains "Race Dashboard"
4.  GET  /derbynet/coordinator.php            → 200
5.  GET  /derbynet/virtual/index.php (auth)   → 200, contains "vd-index-card"
6.  POST action=virtual-mqtt-creds (auth)     → outcome.success, has user+pass
7.  POST action=virtual-mqtt-creds (no auth)  → outcome.failure, code=notauthorized
8.  GET  every <link>/<script> in index.php   → 200
9.  Subscribe derbynet/race/time for 3s       → ≥ 2 messages received
10. Probe action.php for empty post           → no PHP exception in body
```

**Catches**: 13 of the 22 recurring-bugs items, plus any future "endpoint exists but crashes on hit". Highest-leverage single investment.

**Effort**: ~1 day (`testing/test-cloud-smoke.sh`).

### A2. Permission boundary matrix

For every interactive endpoint, assert it returns the right outcome for each role. Matrix is small (~4 roles × ~20 endpoints) and most cells are "denied".

| Endpoint | anon | Timer | Photo | RaceCrew | RaceCoordinator |
|---|---|---|---|---|---|
| `action=role.login` | ok | ok | ok | ok | ok |
| `action=racer.dropout` | denied | denied | denied | ok? | ok |
| `action=schedule.pullforward` | denied | denied | denied | denied | ok |
| `action=virtual-mqtt-creds` | denied | denied | denied | denied | ok |
| `action=heat.select` | denied | denied | denied | ok? | ok |
| `query=poll.coordinator` | denied | denied | denied | ok | ok |
| `GET /coordinator.php` | redirect | denied | denied | ok | ok |
| `GET /virtual/index.php` | redirect | 403 | 403 | 403 | ok |

**Catches**: privilege escalation, accidental loosening of cloud-mode + coordinator gate, and "every error looks identical" symptoms.

**Effort**: ~½ day. Parameterised shell script.

### A3. Pull-forward Pi rehearsal (live hardware)

Already documented in [Dress Rehearsal](../operations/dress-rehearsal.md) Part B. Currently manual; for race-day confidence:

- Capture the MQTT session once.
- Replay against the cloud broker; assert resulting `RaceChart` matches the original byte-for-byte.
- Bonus: assert the broadcast text appears verbatim on a kiosk page during replay.

**Effort**: ~1 day. Replay script already exists.

---

## Priority B — high value, lower urgency

### B1. Container-runtime probes

Catch Alpine-vs-Pi divergences:

- PHP-FPM: `is_cloud_mode()` true; `$_SERVER['DERBYNET_CLOUD_MODE']` is `public`; `MQTT_USER` reachable.
- Race-server import: `python3 -c "import paho.mqtt.client as m; m.CallbackAPIVersion.VERSION2"`.
- nginx: `curl http://derbynet-web/` returns 200 or 302 (not 404).
- Caddy: `curl -k https://localhost/.well-known/acme-challenge/test` returns 404, `wss://localhost/mqtt` upgrades.

**Effort**: ~½ day. New `derbyvps.sh probe` subcommand, or `testing/probe-runtime.sh`.

### B2. Browser-virtual-hardware E2E (cloud only)

Extend `virtual-device-test.js` from "all pages reach connected" to "drive a 4-heat round end-to-end":

```
For each heat 1..4:
  set all 3 finish-timer "ready" toggles
  click GO on start-timer
  click finish on each finish-timer at staggered intervals
  poll RaceChart for finishtime values
  assert all 3 lanes have a time in [1.0, 5.0] range
After:
  GET /derbynet/results.php → 12 rows, no DNFs
```

**Effort**: ~2 days (Puppeteer + multi-tab MQTT-WS is finicky).

### B3. Cloud-sync round-trip

Pi → cloud DB sync currently has no test. Capture Pi DB snapshot + checksum, run `cloud-sync.sh`, fetch cloud-side DB + checksum, assert match within seconds of sync.

**Effort**: ~½ day; Pi-side cron that emails on diff.

---

## Priority C — nice to have

- **C1. Schema migration regression** — diff `setup.php` schema dump against committed baseline.
- **C2. Soak / memory growth** — 24-hour run under simulated load; track per-container RSS and disk usage.
- **C3. Disconnect / reconnect chaos** — kill broker for 10s; assert race-server and virtual pages reconnect (LWT fires, then rejoin).
- **C4. Deploy → rollback → redeploy churn** — deliberately break a deploy; assert auto-rollback kicks in.

---

## Priority D — research

- **D1. Replay-as-fuzz** — mutate one MQTT message at a time in a known-good capture; assert race server doesn't crash. Cheap fuzzing on real shapes.
- **D2. Static analysis** — phpstan / psalm against `website/`. Would have caught `derby_get_error_details` (#12 in the bug list).

---

## Bugs → tests that would have caught them

| # | Bug | Caught by |
|---|---|---|
| 1 | ACL `B_+` wildcard | A1 (publish probe), B1 |
| 2 | MQTT.js CDN dep | B2 |
| 3 | Bind-mount path | B3, B1 |
| 4 | psutil source build | B1 |
| 5 | CRLF on installer scripts | A1 |
| 6 | Mosquitto unauth healthcheck | A1 |
| 7 | passwd 600 root-only | A1 |
| 8 | nginx serves at `/` | A1 |
| 9 | uid mismatch | B1 |
| 10 | rsync without `--inplace` | A1 |
| 11 | Caddy 80-only | A1 |
| 12 | json_failure self-crash | A1, A2 |
| 13 | setup.nodata Data/test | A1 |
| 14 | `clear_env=yes` | A1, B1 |
| 15 | paho-mqtt 1.6 pin | B1 |
| 16 | error_string v1 vs v2 | C2 |
| 17 | hostname/vcgencmd | A1 |
| 18 | hardcoded `/derbynet/` | A1 |
| 19 | derbyTime auth+loop | A1 |
| 20 | `session_start` | A1 |
| 21 | GET vs POST cred | A1, A2 |
| 22 | browser cache | B2 |

**13 of 22** would have been caught by **A1 alone**. That's the highest-leverage single investment.

---

## Suggested order

1. **A1** cloud-twin smoke (1 day).
2. **A3** Pi-rehearsal capture/replay (1 day).
3. **A2** permission matrix (½ day).
4. **B1** runtime probes (½ day).
5. Everything else is post-race-day polish.

Total Priority-A: ~2.5 days. A+B: ~5 days. The full list is roughly two weeks of test-engineering work.

---

## Out of scope

- **Hardware-in-the-loop** — covered by Pi rehearsal manually.
- **Visual regression / screenshot diff** — overkill for a kids' race.
- **Mocked MQTT brokers** in integration tests — use a real Mosquitto in Docker.
- **Browser-compat suite** — cloud twin is for testing, not public-facing.

# Test Suite

## Purpose

Comprehensive testing for the DerbyNet system — shell-based integration tests using curl against a running instance, plus Puppeteer browser automation for E2E testing.

## How It Fits

Tests exercise the DerbyNet PHP web application by making HTTP requests (curl) and verifying responses. They cover registration, scheduling, racing, awards, permissions, and elimination tournaments. The test suite is designed to run against a local or Docker instance.

## Key Files

- `common.sh` — Shared utilities (curl helpers, assertions, logging, environment setup)
- `test-basic-racing.sh` — Core racing workflow test
- `test-master-schedule.sh` — Scheduling engine tests
- `test-awards.sh` — Awards system tests
- `test-permissions.sh` — Permission boundary tests
- `data/` — Test fixtures and sample data (CSV rosters, photos)
- `test-pull-forward.sh` — Pull-forward backend (10 scenarios; Test 4 asserts the broadcast surfaces on the kiosk poll, Test 10 asserts dry-run JSON is byte-identical to execute JSON — the simulation-fidelity check that backs the operator UI)
- `test-cloud-sync-trigger.sh` — Offline unit test for the event-driven cloud-sync safety (`extras/soapbox/infra/server/cloud-sync.sh`): single-flight `flock` + coalesce-to-one-catch-up retry. Stubs scp/ssh/sqlite3 onto PATH, so no Pi/cloud/DB needed. Run directly (no `BASE_URL`). See `docs/PUBLIC_STATS.md`.
- `test-stats-render.sh` — Offline test for the spectator-page render contract (`installer/docker-cloud/stats-gen/render.sh`): builds a small real SQLite event DB and asserts `version.txt` equals the DB mtime, stays stable when the DB is idle (no needless reloads) and bumps on change, `{{VERSION}}` substitution, and content sanity (zero-padded pinny, current-heat marker, finish time, per-racer page polling `../version.txt`). Needs local `sqlite3`.
- `test-stats-render-loop.sh` — Offline test for the stats-gen render loop (`installer/docker-cloud/stats-gen/entrypoint.sh`, via the `RENDER_BIN` override): renders on startup, on DB-mtime change, and NOT while idle. Timing-based but with generous windows.
- `test-cloud-push-integration.sh` — End-to-end integration test for the PHP event-driven push hooks against a REAL DerbyNet instance in Docker. Builds the stock `installer/docker/Dockerfile` from the current tree (Alpine 3.20 pin), drives a real roster/schedule/heat/result flow, and asserts: with the trigger file absent the hooks are a no-op and never break racing; with it present `write_chart`/`set_current_heat`/`write_heat_results` each fire it. Skips cleanly if Docker is unavailable. (`KEEP=1` leaves the container up to poke.)
- `test-derbydb-cloud-push.py` — Unit test for the real `derbydb.DerbyDatabase.request_cloud_push`: no-op when absent, fires `os.utime` when present, swallows `OSError`. No DB/server needed.
- `test-adhoc-mode.php` — Offline functional test for ad-hoc racing mode (`docs/ADHOC.md`). Builds a throwaway "official" DB from the real schema and exercises the real `inc/db-marker.inc`, `inc/adhoc.inc` (`adhoc_build`, pinny resolution), and `inc/adhoc-standings.inc` (best-of scoring, DNF exclusion, per-age-group top-N, PII-free render), plus marker round-trip and official-DB isolation. Run directly: `php testing/test-adhoc-mode.php` (needs PHP CLI with `pdo_sqlite`; no server/Docker). Exit 0 = pass, 2 = skipped (no driver).
- `puppeteer/` — Browser automation tests (JavaScript)
  - `pull-forward-test.js` — Pull-forward UI tests (20 scenarios). Tests 1–11 cover the deprecated modal fallback; Tests 12–20 cover the dedicated `pull-forward.php` page (entry button, roster render, selection→dry-run, preview, Apply/Apply+Announce/Discard, no_gaps inline, `?pf_committed=1` undo pulse).
  - `virtual-device-test.js` — Smoke test for cloud-twin browser virtual hardware (requires a live cloud stack)
- `captures/` — JSONL captures of real-hardware MQTT sessions, replayed by the script below
- `replay-real-race.py` — Paho replayer that drives a captured MQTT timeline against a target broker for deterministic regression

For a structured test-case proposal (categories, priorities, mapping to
real bugs caught), see `docs/TESTING.md`.

## Test Naming Patterns

- `test-*.sh` — Feature/integration tests
- `setup-*.sh` — Environment initialization scripts
- `demo-*.sh` — Demo/showcase scripts

## Dependencies

- Bash, curl
- Running DerbyNet instance (local or Docker)
- Node.js + Puppeteer (for E2E tests)

## Common Tasks

- **Run a test**: `./test-basic-racing.sh`
- **Run with custom server**: `BASE_URL=http://localhost:8080 ./test-basic-racing.sh`
- **Reset database**: Uses `drop-all-tables.sql` for clean state

## Environment Variables

- `BASE_URL` — DerbyNet server URL
- `PASSWORDS_FILE` — Path to passwords configuration

## Gotchas

- **Stateful tests**: Most tests modify database state — run `setup-*.sh` first or use database reset between tests
- **No test runner**: Tests are individual shell scripts, not part of a framework
- **Order matters**: Some tests depend on data created by setup scripts

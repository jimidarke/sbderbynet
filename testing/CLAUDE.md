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
- `test-pull-forward.sh` — Pull-forward backend (9 scenarios; Test 4 also asserts the broadcast surfaces on the kiosk poll)
- `puppeteer/` — Browser automation tests (JavaScript)
  - `pull-forward-test.js` — Pull-forward modal UI tests (11 scenarios)
  - `virtual-device-test.js` — Smoke test for cloud-twin browser virtual hardware (requires a live cloud stack)
- `captures/` — JSONL captures of real-hardware MQTT sessions, replayed by the script below
- `replay-real-race.py` — Paho replayer that drives a captured MQTT timeline against a target broker for deterministic regression

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

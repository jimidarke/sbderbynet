# Race Simulation & Validation System (`simctl`)

Validates the full results pipeline end-to-end before race day: MQTT timer
hardware → race-server → tenant DB → elimination advancement → standings →
awards.  Runs dozens–hundreds of seeded full-tournament variants against the
cloud multi-tenant stack, mocking the start/finish timers at the MQTT layer,
and cross-checks every outcome against an independent pure-Python oracle.

## How a variant runs

1. A `sim-NN` tenant is reset from a sanitized snapshot of the official
   tenant (`st-albert-2026-official`) — same roster, pinnies, classes, and
   tournament rows; results stripped, everyone checked in.
2. Mock hardware connects to the broker on the tenant's topic namespace
   (`derbynet/t/sim-NN/...`): three finish timers + a start timer publishing
   the same payloads as the real firmware.  On the cloud stack the
   race-server submits results via HTTP `timer-message FINISHED` (no derbydb
   module in the image), and that request drives PHP heat auto-advance and
   round advancement.  A mock **kiosk** also polls `query=poll.results` to
   reproduce race-day read load.
3. The orchestrator drives each round: `schedule.generate`, `heat.select
   now_racing=1`, then per heat: wait for STAGING → ready telemetry → GO →
   finish messages.  **Fast mode** backdates device timestamps (GO at T₀ in
   the recent past, finishes at T₀+plan) so recorded times are exact without
   wall-clock waits — this relies on derbyRace ≥ 0.9.1 honoring finish
   device timestamps.  **Realtime mode** actually waits.
4. DNFs go through the coordinator path (`action=racer.dnf`), picked up by
   the race-server's 1 s API tick — the real race-day DNF mechanism (the 70 s
   auto-timeout is disabled in production).
5. Pull-forward withdrawals call `schedule.pullforward` (dry-run → apply,
   optional undo/re-apply) between heats.
6. Round completion should auto-advance the elimination tournament; the
   orchestrator falls back to `elimination.tournament.advance` and logs an
   anomaly if it doesn't.
7. The **oracle** recomputes scores/advancement/finals/awards from the
   injected results; the **verifier** diffs against the tenant DB.

## Oracle semantics (the agreed truth)

* DNF = 99.999 exactly, included in every aggregate.
* `drop_slowest` = single time when n=1, else (Σ−max)/(n−1).  One DNF gets
  *erased* by the drop — surfaced in the report as a policy effect.
* Ties at SCORE_EPSILON (0.0005); competition ranking (1,2,2,4).
* Advancement = top N **plus everyone tied with the N-th score**.
* Pull-forward dropouts are ineligible to advance (the verifier separately
  detects PHP advancing a dropout on a partial-run aggregate).

## Quick start

```bash
# local twin (once docker compose is up in installer/docker-cloud):
deploy/run-local.sh doctor
deploy/run-local.sh template build
deploy/run-local.sh pool init --count 2
deploy/run-local.sh run --seed 1 --scenario happy_path --tenant sim-01

# VPS:
deploy/run-on-vps.sh doctor
deploy/run-on-vps.sh template build
deploy/run-on-vps.sh pool init --count 4
deploy/run-on-vps.sh campaign run --plan /sim/campaigns/smoke.json
NOHUP=1 deploy/run-on-vps.sh campaign run --plan /sim/campaigns/full-matrix.json
```

Artifacts land in `artifacts/<campaign>/vNNNNN-…/{artifact,verdict}.json`
plus an aggregate `REPORT.md` (pass/fail matrix, failure taxonomy,
std-vs-dropslowest advancement diffs).

## Offline self-test (no stack needed)

```bash
python3 selftest.py
```

Checks the oracle against the hand-computed `fixtures/micro6` fixture (tie
at the cutoff, DNF totals, drop-slowest forgiveness, withdrawn exclusion,
finals placement) and planner determinism.  `expected.json` was computed by
hand — never regenerate it from the oracle.

## Guardrails

* Pool tooling refuses any tenant slug not matching `^sim-\d+$`.
* The official DB is only ever opened read-only (SQLite backup API / mode=ro).
* `simctl doctor` records the official DB sha256; compare before/after
  campaigns.
* stats-gen reads the compose-pinned single DB path; sim tenants cannot leak
  to the spectator pages.

## Scenarios & campaigns

`scenarios/*.json` — happy_path, dnf_edge (3% DNFs + all-DNF heat +
all-DNF racer + forced cutoff ties), pullforward, tie_rich (0.05 s
resolution → natural ties everywhere).
`campaigns/*.json` — smoke (2 variants), full-matrix (50 seeds × both
scoring configs = 100 variants), dress-rehearsal (1 realtime variant).

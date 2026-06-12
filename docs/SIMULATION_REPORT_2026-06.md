# Race Simulation Validation Report — June 2026

**Goal:** validate the full results pipeline (MQTT timers → race-server →
DB → elimination advancement → standings → awards) before the live-broadcast
race day on 2026-06-22, across hundreds of simulated tournament variants,
and assess drop-slowest-then-average as an alternative scoring method.

**System:** `testing/simulator/` (`simctl`) — seeded, reproducible
full-tournament variants against cloud-twin tenants cloned from
`st-albert-2026-official`, mock timer hardware at the MQTT layer, every
outcome cross-checked against an independent pure-Python oracle.
See `testing/simulator/README.md`.

---

## 1. Bugs found and fixed (all would have surfaced on broadcast day)

| # | Bug | Impact on race day | Fix |
|---|-----|--------------------|-----|
| 1 | Three queries compared integer `Rounds.round` against the round NAME string | **Tournament could not advance past prelims at all** ("Next round not found"); elimination standings page and results kiosk rendered **empty** | Compare `roundname` (5 sites) |
| 2 | `advance_round()` read its round row without `PDO::FETCH_ASSOC` | The auto round-advance path has been a **silent no-op since it was written** | Pass `FETCH_ASSOC`; entry logging added |
| 3 | THREE divergent advancement engines (playlist StandingsOracle bucket path, inline `advance_round` copy, explicit action) | Roster of the next round = additive union of two differently-scored top-N lists, **duplicate Roster rows** (extra lanes), `EliminationTournaments.current_round` never updated | Single shared engine `inc/elimination-advancement.inc`; all paths delegate |
| 4 | Advancement cut used `ORDER BY score LIMIT n` with no tiebreak | A racer tied for the last advancing spot was **dropped nondeterministically** | Full ranking, tie-inclusive cut, competition ranks (1,2,2,4) |
| 5 | DNF (99.999) included in advancement but excluded from displayed standings | Displayed order could **disagree with who actually advances** | DNF counts as 99.999 everywhere (user decision) |
| 6 | Pull-forward dropouts advanced: a withdrawn racer's 1-run `total_time` beat every 3-run total | **A kid who left the event would be announced into the quarter-finals** (simulator caught this live in scenario testing) | Advancement + standings filter `passedinspection = 1 AND exclude = 0` (pull-forward clears `passedinspection` on dropout) |
| 7 | Race-server finish path used MQTT receipt wall-clock | Lane times absorbed network jitter | derbyRace 0.9.1: device GPIO-edge timestamps (mirrors START), receipt-clock fallback |

Also added: `drop_slowest` scoring method end-to-end (advancement engine,
standings oracle, config validator, editor UI) + variant config
`soapbox-derby-elimination-dropslowest.json`.

## 2. Validation results

### Local gate (docker-cloud twin, full-size official-shaped roster)
* `selftest.py`: 36/36 oracle checks vs hand-computed fixture (micro6).
* `testing/test-elimination-scoring.sh`: PASS — roundname fix, tie-inclusive
  cut, DNF-inclusive scoring, drop_slowest, kiosk rendering, all via HTTP.
* Full happy-path tournament (173 racers, ~200 heats, 4 classes → finals):
  PASS in 3m45s fast-MQTT; every injected time recorded exactly (3 d.p.).
* Reproducibility: same seed on two tenants → 612/612 identical results.
* `dnf_edge` (3% DNFs + all-DNF heat + all-DNF racer + forced cutoff ties),
  both scoring configs: PASS, zero anomalies.
* `tie_rich` (0.05s resolution): cuts widened naturally (27→29 etc.),
  scheduler handled odd roster sizes: PASS.
* `pullforward` (3 dropouts incl. dry-run/undo/re-apply cycle): PASS after
  fix #6 — and it was this scenario that exposed #6.
* Realtime micro run (VIP class, real wall-clock, coordinator DNF loop):
  PASS — 48/48 recorded times within 0.15s of plan.

### VPS (production stack, tenants cloned from st-albert-2026-official)
* Real 2026 registration shape: Ages 9-11 = 57, Ages 6-8 = 55,
  Ages 12-14 = 14 racers.
* Smoke campaign: **2/2 PASS**.
* Full matrix (100 variants: 50 seeds × std + dropslowest across all
  scenario families): **IN PROGRESS** — launched 2026-06-11 ~18:24 MDT,
  detached on the VPS (survives local shutdown). 8/8 PASS at last check.
  Log: `/opt/sbderbynet/testing/simulator/artifacts/run-20260612-002410.log`
  Status check:
  `ssh claude@uisp.darketech.ca "sudo find /opt/sbderbynet/testing/simulator/artifacts/campaign-full-matrix -name verdict.json | wc -l"`
  (done when the log tail says "campaign done: N/100"); aggregate report at
  `artifacts/campaign-full-matrix/REPORT.md` on the VPS.
* Realtime dress rehearsal: **TBD — queued after the matrix**:
  `NOHUP=1 testing/simulator/deploy/run-on-vps.sh campaign run --plan /sim/campaigns/dress-rehearsal.json`
* After campaigns: re-verify official DB hash against
  `testing/simulator/artifacts/official-db-baseline.sha256`
  (d18882526e350c18…).
* Official tenant isolation: DB sha256 verified unchanged before/after
  campaigns (`artifacts/official-db-baseline.sha256`).

## 3. Scoring method assessment (std total_time vs drop_slowest)

Preliminary (paired seed 11, ~3% DNF rate): the methods disagree
substantially — e.g. 5 of 27 Ages 6-8 prelim advancers differ and the
finals field changes. The dominant driver is DNF policy:

* **total_time**: one DNF ≈ +100s — effectively eliminates the racer.
* **drop_slowest**: the DNF *is* the dropped run — one DNF is fully
  forgiven; only a second DNF hurts.

Full-matrix comparison tables: **TBD**.

**Decision needed before race day:** which DNF philosophy do you want on
the track? (A mechanical failure costing a kid the event argues for
drop_slowest; "you must finish your runs" argues for total_time.)

## 4. Race-day notes

* **Timer resolution:** finish/start firmware records GPIO edges at 0.1s
  resolution. With derbyRace 0.9.1 both ends of `race_time` quantize to
  0.1s, so **exact ties will be common** — the tie-inclusive advancement
  fix is load-bearing. Optional improvement before race day: bump firmware
  timestamps to millisecond resolution (flash via the SD imaging pipeline).
* **Cloud vs Pi write path:** the cloud race-server image carries no
  `derbydb` module, so results flow via HTTP `timer-message` — which is
  also what drives heat auto-advance and round advancement. **Verify the
  same on the Pi before race day**: if the Pi race-server writes directly
  to SQLite, nothing advances the heat pointer automatically (the
  coordinator would advance manually — confirm that's the intended Pi
  operating mode).
* **Pull-forward pauses racing** when it squeezes out an emptied heat —
  operator must press Start Racing again (matches the operator card).
* The VIP age-group config (`races_per_racer: 2`) isn't honored by the
  scheduler (only 1 or 3 handled; falls back to once-per-lane = 3 runs).
  No VIP class exists in the official event; fix only if one is added.

## 5. Repro / operations

```bash
# local twin
testing/simulator/deploy/run-local.sh doctor
# VPS campaign
testing/simulator/deploy/run-on-vps.sh campaign run --plan /sim/campaigns/smoke.json
NOHUP=1 testing/simulator/deploy/run-on-vps.sh campaign run --plan /sim/campaigns/full-matrix.json
# any failure is reproducible from its seed:
testing/simulator/deploy/run-on-vps.sh run --seed N --scenario S --config C --tenant sim-01
```

Deploy backup tag for this change set: `deploy-20260611-181744`.

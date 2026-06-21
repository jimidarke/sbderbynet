# Race Simulation Validation Report — June 2026

**Goal:** validate the full results pipeline (MQTT timers → race-server →
DB → elimination advancement → standings → awards) ahead of the scheduled
race day on 2026-06-21, across hundreds of simulated tournament variants,
and assess drop-slowest-then-average as an alternative scoring method.

> **Outcome (2026-06-21):** race day was rain-cancelled; only Friday practice
> (2026-06-20) ran, so the elimination pipeline was not exercised in live
> competition. The 7 fixes below remain validated by simulation and are in
> `master`, ready for the next event.

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
* Stock-suite regression A/B (2026-06-12): `setup-basic-no-photos.sh` +
  `test-basic-racing.sh` run against side-by-side containers built from
  the pre-change baseline (061de2ad) and the current tree. Result: **all
  92 executed steps and every failure point byte-identical** between the
  two builds. The failures themselves are pre-existing fork rot /
  environment gaps (`note_from` custom-field assertions, replay-client
  expectations with no replay attached, and the fork's own
  check-in-gates-scheduling behavior) — none introduced by this change
  set. Note: the `FETCH_ASSOC` fix re-awakened `advance_round()`'s legacy
  non-elimination branch, which only fires for rounds named exactly
  "Preliminary"/"Semi-Final"; SBDerbyNet rounds are always number-prefixed
  ("1 Preliminary"), so it remains unreachable in this fork.

### VPS (production stack, tenants cloned from st-albert-2026-official)
* Real 2026 registration shape: Ages 9-11 = 57, Ages 6-8 = 55,
  Ages 12-14 = 14 racers.
* Smoke campaign: **2/2 PASS**.
* Full matrix (100 variants: 50 seeds × std + dropslowest across
  happy_path / dnf_edge / pullforward / tie_rich): **100/100 PASS.**
  First pass was 91/100; all 9 failures were one latent race-server bug
  (lane count not adapting when a partial heat staged inside the one-tick
  FINISHED→RACING bounce after a DNF-completed heat — possible only at
  simulator pacing, near-zero race-day exposure). Fixed in derbyRace
  0.9.2; the 9 seeds re-ran 9/9 PASS. The 91 original passes are
  unaffected by the fix (it changes a hang path, not any scoring path).
* Realtime dress rehearsal: **PASS** — the full event at real wall-clock
  (157 heats, 469 results, 70 minutes, zero anomalies), coordinator-DNF
  loop and heartbeat cadence under true timing. One adjudication nuance:
  realtime jitter (~0.1s/run) legitimately broke a scenario-planted exact
  tie at the 27th cut, so the verifier now judges realtime runs against
  the RECORDED times (the engine's actual inputs) rather than the plan —
  with that, engine and oracle agree completely.
* Official tenant isolation: hash unchanged across all campaigns. (It DID
  change once mid-evening — coordinator settings edits `weight-units=kg`
  + `scoring=1` at 19:19 MDT, human action, no race data touched.)
* Official tenant isolation: DB sha256 verified unchanged before/after
  campaigns (`artifacts/official-db-baseline.sha256`).

## 3. Scoring method assessment (std total_time vs drop_slowest)

50 paired seeds, identical injected times under both methods:

| Effect | Result |
|---|---|
| Prelim advancers changed | mean ~10-12% of each cut (3.3/27 Ages 9-11, 3.1/29 Ages 6-8, 1.0/10 Ages 12-14); max 6-7 |
| Finals field differs | **46 / 50 seeds (92%)** |
| A podium differs | **46 / 50 seeds (92%)** |
| Why drop-only advancers got in | 278 pure peak-vs-consistency vs 92 DNF-forgiveness (**3:1**) |

The headline: the scoring choice changes a podium in 92% of simulated
events — and the dominant mechanism is NOT DNF forgiveness. Dropping the
slowest run fundamentally rewards *peak pace* (your best 2 runs) where
total_time rewards *consistency* (all 3 runs count). DNF policy rides on
top of that:

* **total_time**: one DNF ≈ +100s — effectively eliminates the racer.
* **drop_slowest**: the DNF *is* the dropped run — one DNF fully forgiven.

Both methods are validated end-to-end (50 full tournaments each). The
detailed who-changed tables are in the campaign report on the VPS
(`artifacts/campaign-full-matrix/REPORT.md`, 308 difference rows).

**DECIDED 2026-06-12: the event races DROP-SLOWEST.** The Settings
toggle (RaceInfo `scoring`) is now authoritative end-to-end: for
multi-run rounds it overrides the config's scoring method in both
advancement and the elimination standings display
(`elimination_effective_scoring_method()`), so the coordinator's switch
governs everything — validated by `test-elimination-scoring.sh` class C
(std config + scoring=1 → drop-slowest advancement) run three times
green against the production stack, plus a cross-tenant probe proving
the setting is tenant-scoped (Pi: the single event DB — same code).
The official tenant's existing `scoring=1` is therefore live and
consistent: drop-slowest display AND drop-slowest advancement.

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

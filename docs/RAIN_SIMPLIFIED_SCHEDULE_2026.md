# Rain-Day Simplified Schedule — 2026 (PENDING CONFIRMATION)

**Status:** 🟡 Proposed — pending coordinator sign-off. **No config or code changes made yet.**
**Created:** 2026-06-17
**Driver:** Rain forecast for race day; coordinator wants a simpler schedule with the
same elimination structure to reduce time on the hill.

This is a planning tracker, not an implemented change. When confirmed, the only
build artifact is **one new elimination config file** (see "Implementation path").

---

## Source documents

- Coordinator email thread 1 — proposed simplified schedule (3 runs → top 9 semi → top 3 final;
  remove the 27-racer elimination round for 6-8 and 9-11; "top 9 with best 2 times").
- Coordinator email thread 2 — 12-14 only has 10 racers; advancing top 9 singles out one
  "loser." Coordinator agreed: **12-14 goes straight to a top-3 final (no semi).**
- `2026 Race Schedule- 106 racers, 14 VIP Simplified.xlsx` (repo root) — side-by-side
  2025 (current) vs 2026 (proposed) schedule with documented heat counts + timing.

---

## Agreed format (all four groups, race-day order)

| # | Group | Racers* | Bracket | Prelim scoring |
|---|---|---|---|---|
| 1 | **12-14** | ~10 | Prelim (3 runs) → **Final, top 3** *(no semi)* | best-2-of-3 |
| 2 | **9-11** | ~48 | Prelim (3 runs, top 9) → Semi (top 3) → Final | best-2-of-3 |
| 3 | **VIP** | ~14 | 2 prelim runs (top 3) → Final | combined-2 *(unchanged)* |
| 4 | **6-8** | ~48 | Prelim (3 runs, top 9) → Semi (top 3) → Final | best-2-of-3 |

\* Documented planning numbers (xlsx). Actual counts come from check-in on the day;
rain may reduce turnout — `advance_count` is a max, so low turnout degrades gracefully.

### Changes vs. today's production format

- **12-14:** drop the semi entirely → 2-round Prelim→Final (top 3); prelim scoring → best-2.
- **9-11 & 6-8:** delete the **Quarter-Finals** round (27→9 collapses into the prelim);
  prelim scoring → best-2 ("drop slowest" of 3).
- **VIP:** untouched.

Net: all three age groups end on the same Prelim→(Semi)→Final shape; VIP unchanged.

---

## Heat counts (updated schedule)

Prelim heats = racers (each races 3×, once per lane, 3 lanes → heats = racers).
Single-run rounds = racers ÷ 3. VIP prelim = 2 runs → 14×2÷3 ≈ 10.

| Group | Racers | Prelim | Semi | Final | **Heats** |
|---|---|---|---|---|---|
| 12-14 | 10 | 10 | — | 1 | **11** |
| 9-11 | 48 | 48 | 3 | 1 | **52** |
| VIP | 14 | 10 | — | 1 | **11** |
| 6-8 | 48 | 48 | 3 | 1 | **52** |
| **Total** | **120** | 116 | 6 | 4 | **126** |

## Timing estimates

Racing time = heats × per-heat, +10% for resets/transitions (per the xlsx method).
Prelims dominate (116 of 126 heats).

| Per-heat | Total racing time (126 heats, +10%) |
|---|---|
| 1 min | ~2 hr 19 min |
| 2 min | ~4 hr 37 min |

- 1 min/heat is the **optimistic floor** — achievable only if the next 3 carts are
  pre-staged at the line while the prior heat clears.
- The xlsx note says "release / reload / second release takes 3 minutes." The
  `min_heat_gap = 6` rest design exists because racers walk carts back up the hill;
  that gap means no racer is in back-to-back heats, so heat *cadence* can beat any one
  racer's turnaround.
- **Recommended planning number: 2 min/heat** for the parent-facing start times
  (≈4½ hr racing + lunch), leaving rain slack; operators can beat it on the day.

---

## Open items (confirm before sending parent start times)

1. **Confirm "best 2 times" = `drop_slowest`** (best 2 of 3, slowest dropped). This is
   how it would be implemented and is already validated.
2. **9-11 prelim scoring wording** in the xlsx omitted "top two" (6-8 and 12-14 say it
   explicitly) — confirm all three age groups use best-2 uniformly.
3. **Per-heat time** for the parent email: 1 vs 2 min. Recommend 2 min for margin.
4. **VIP** confirmed unchanged (2 prelim runs → top-3 final).
5. **Turnout** — 10/48/48/14 are planning figures; rain may reduce them. No structural
   impact (advance_count is a max).
6. **xlsx 12-14 figure is stale** — it still shows the semi (14 races / ~80 min);
   with top-3 straight to final it's 11 heats (~60 min @5min, ~22 min @2min). Does not
   cascade (9-11 has a fixed later start).

---

## Implementation path (when confirmed — NOT done yet)

1. Clone `website/inc/elimination-configs/soapbox-derby-elimination-dropslowest.json`
   to a new rain-day config file.
2. **12-14:** reduce to 2 rounds — Prelim (`races_per_racer: 3`, `scoring_method:
   drop_slowest`, `advance_count: 3`) → Finals (placement). Remove the semi.
3. **6-8 & 9-11:** flatten to 3 rounds — Prelim (`drop_slowest`, `advance_count: 9`) →
   Semi (`best_time`, `advance_count: 3`) → Finals (placement). Remove the Quarter-Finals round.
4. **VIP:** leave as-is.
5. Update `expected_racers` to the planning numbers (informational only).
6. Validate: simulator (`testing/simulator/`) + cloud-twin sandbox tenant
   `st-albert-2026-official` → import to Pi before race day.

No engine changes required — every primitive (3-round bracket, `drop_slowest`,
`top_count`, `placement`) already exists and is validated.

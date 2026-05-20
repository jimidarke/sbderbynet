# Round Setup Guide

## Database Schema

### Key Tables

```
RegistrationInfo (racers)
    └── racerid (PK)
    └── classid (FK) → Classes.classid
    └── passedinspection (boolean)
    └── registered (boolean)

Classes (age groups)
    └── classid (PK)
    └── class (name, e.g., "Ages 6-8")

Rounds (racing rounds)
    └── roundid (PK)
    └── classid (FK) → Classes.classid
    └── round (INTEGER) ← Must be numeric!
    └── roundname (VARCHAR) ← Display name

Roster (racer enrollment)
    └── roundid (FK) → Rounds.roundid
    └── racerid (FK) → RegistrationInfo.racerid
    └── classid (FK) → Classes.classid

RaceChart (scheduled heats)
    └── roundid (FK) → Rounds.roundid
    └── heat (INTEGER)
    └── lane (INTEGER)
    └── racerid (FK)
    └── finishtime (result)
```

### Data Flow

```
RegistrationInfo → Roster → RaceChart → Results
     (racers)      (enrollment)  (heats)   (times)
```

---

## Critical: The `round` Column

The `Rounds.round` column **must contain integers** (1, 2, 3...), not string names.

**Correct:**
```sql
roundid | round | roundname        | classid
1       | 1     | 1 Preliminary    | 1
2       | 2     | 2 Quarter Finals | 1
3       | 3     | 3 Semi-Finals    | 1
4       | 4     | 4 Finals         | 1
```

**Why it matters:** The `fill_in_missing_roster_entries()` function uses `WHERE round = 1`. If `round` contains a string, no racers will be enrolled in the Roster table.

---

## Setup Sequence

### Standard Racing

1. Create Classes (Round 1 auto-created with `round = 1`)
2. Register Racers (auto-enrolled in Round 1)
3. Pass Inspection (`passedinspection = 1`)
4. Generate Schedule (creates RaceChart entries)
5. Start Racing

### Elimination Tournament

1. Create Classes (Round 1 auto-created)
2. Register Racers (auto-enrolled in Round 1)
3. Initialize Elimination Tournament (creates additional rounds)
4. Pass Inspection
5. Generate Schedule for Round 1
6. Race → Advance top racers → Generate next round → Repeat

---

## Per-Class Minimum Heat Gap

`Classes.min_heat_gap` (added in schema 17) controls how many heats of rest the
scheduler tries to give each racer between appearances. Soapbox racers need
time to walk their cart back to the top of the hill; the legacy
`avoid-consecutive` weight only penalised heat N vs N+1, so racers could still
end up racing every 3rd or 4th heat.

The scheduler now applies a **windowed soft penalty** inside `min_heat_gap`:
full `avoid-consecutive` weight at gap = 1, tapering linearly to ~1/window at
the window edge, zero beyond. The penalty is soft (algorithm never refuses to
schedule), so small rosters that physically can't honour the window degrade
gracefully — exactly the behaviour required for late-event pull-forward.

Defaults:

- New classes default to `min_heat_gap = 6` — empirically the sweet spot
  for 3-lane soapbox.
- Set to `0` to opt out and restore the legacy "only penalise N vs N+1" behaviour.
- A small charity / VIP class with 12 racers might want `min_heat_gap = 3` so the
  algorithm doesn't dump unnecessary penalty mass into a roster that physically
  can't satisfy a larger window.

Edit on the Racing Groups page (`racing-groups.php`) inside the per-class
edit modal.

### Why 6 instead of 8?

The user-facing target was "8 races of rest." Empirically, on real
production tenant data (26–31 racers × 3 lanes × 3 runs each), the
windowed penalty performs best in the 4–6 range:

| `min_heat_gap` | Observed `min` gap | Racers with tightest gap < 4 |
|---|---|---|
| 0 (legacy) | 2 | 17–58% |
| **4** | **4** | **0%** |
| **6** | **5–6** | **0%** |
| 8 | 3 | 4–8% |
| 12 | 3 | 4–15% |

The intuition: at larger windows, the linearly-decaying penalty spreads
weight over many heats. The d=1 (back-to-back) cost stays fixed at the
full `avoid-consecutive` weight, but the integrated cost of *also*
penalising d=2..7 dilutes the marginal value of fixing one specific
violation. The greedy occasionally accepts a tighter gap in one place to
score better elsewhere.

For typical soapbox sizes, **6 reliably achieves min-gap of 5–6** without
this dilution. Operators who want a guaranteed minimum of 8+ should
instead increase `avoid-consecutive` to maximum and use `min_heat_gap = 6`;
nothing prevents setting `min_heat_gap = 8`, it just may not behave
better than 6 in practice.

---

## Troubleshooting

### "Can't start race" / No heats scheduled
- Check `Rounds.round` contains integers, not strings
- Verify racers have `passedinspection = 1`
- Confirm Roster has entries: `SELECT COUNT(*) FROM Roster`

### Racers not appearing in rounds
- Verify Round 1 exists with `round = 1`: `SELECT * FROM Rounds WHERE round = 1`
- Re-trigger roster population by adding/editing a racer

### Elimination tournament won't start
- Verify round numbers are sequential integers (1, 2, 3, 4)
- Check `EliminationTournaments` table has active tournament

---

## Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `create_class()` | `inc/class_add_or_delete.inc` | Creates class + Round 1 |
| `insert_new_racer()` | `inc/newracer.inc` | Adds racer, triggers roster |
| `fill_in_missing_roster_entries()` | `inc/newracer.inc` | Enrolls racers in Round 1 |
| `initialize_elimination_tournament()` | `inc/elimination-config.inc` | Sets up elimination format |
| `schedule_one_round()` | `inc/schedule_one_round.inc` | Generates heat schedule |

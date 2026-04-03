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

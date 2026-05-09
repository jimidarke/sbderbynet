# Round Setup

How rounds, the roster, and the race chart relate, and the gotcha that makes "racers not appearing" the most common new-event bug.

---

## Schema

```
RegistrationInfo  (racers)
    racerid (PK)
    classid → Classes.classid
    passedinspection (bool)
    registered (bool)

Classes  (age groups)
    classid (PK)
    class (e.g. "Ages 6-8")

Rounds  (racing rounds)
    roundid (PK)
    classid → Classes.classid
    round (INTEGER)         ← MUST be numeric
    roundname (VARCHAR)     ← display name

Roster  (racer enrollment)
    roundid → Rounds.roundid
    racerid → RegistrationInfo.racerid
    classid → Classes.classid

RaceChart  (scheduled heats)
    roundid → Rounds.roundid
    heat (INTEGER)
    lane (INTEGER)
    racerid
    finishtime (result)
```

### Data flow

```
RegistrationInfo  →  Roster  →  RaceChart  →  Results
   (racers)        (enrolment)   (heats)      (times)
```

---

## The `round` column gotcha

`Rounds.round` **must** contain integers (`1, 2, 3, …`), not display names.

**Correct:**

| roundid | round | roundname | classid |
|---|---|---|---|
| 1 | 1 | 1 Preliminary | 1 |
| 2 | 2 | 2 Quarter Finals | 1 |
| 3 | 3 | 3 Semi-Finals | 1 |
| 4 | 4 | 4 Finals | 1 |

**Why it matters**: `fill_in_missing_roster_entries()` queries `WHERE round = 1`. If `round` contains a string, no racers get enrolled in `Roster` and you'll see "Can't start race" with no heats scheduled.

(All round *names* must also start with a digit so they sort correctly — that's enforced by config validation.)

---

## Setup sequence

### Standard racing

1. Create Classes (Round 1 auto-created with `round = 1`).
2. Register racers (auto-enrolled in Round 1).
3. Pass inspection (`passedinspection = 1`).
4. Generate schedule (creates `RaceChart` entries).
5. Start racing.

### Elimination tournament

1. Create Classes (Round 1 auto-created).
2. Register racers (auto-enrolled).
3. Initialize elimination tournament (creates additional rounds).
4. Pass inspection.
5. Generate schedule for Round 1.
6. Race → advance top racers → generate next round → repeat.

---

## Troubleshooting

### "Can't start race" / no heats scheduled

- Check `Rounds.round` contains integers, not strings.
- Verify racers have `passedinspection = 1`.
- Confirm `Roster` has entries: `SELECT COUNT(*) FROM Roster`.

### Racers not appearing in rounds

- Verify Round 1 exists with `round = 1`: `SELECT * FROM Rounds WHERE round = 1`.
- Re-trigger roster population by adding/editing a racer.

### Elimination tournament won't start

- Verify round numbers are sequential integers (`1, 2, 3, 4`).
- Confirm `EliminationTournaments` has an active tournament.

---

## Key functions

| Function | File | Purpose |
|---|---|---|
| `create_class()` | `website/inc/class_add_or_delete.inc` | Creates class + Round 1 |
| `insert_new_racer()` | `website/inc/newracer.inc` | Adds racer, triggers roster fill |
| `fill_in_missing_roster_entries()` | `website/inc/newracer.inc` | Enrols racers in Round 1 |
| `initialize_elimination_tournament()` | `website/inc/elimination-config.inc` | Sets up elimination format |
| `schedule_one_round()` | `website/inc/schedule_one_round.inc` | Generates heat schedule |

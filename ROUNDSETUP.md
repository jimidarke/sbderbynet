# Round Setup Guide

This document outlines how the DerbyNet round system works, the correct setup sequence, and how elimination tournaments integrate with the base system.

## Table of Contents
1. [Database Schema Overview](#database-schema-overview)
2. [The Round Column: Critical Understanding](#the-round-column-critical-understanding)
3. [Setup Sequence: Step by Step](#setup-sequence-step-by-step)
4. [Fake Roster Function Analysis](#fake-roster-function-analysis)
5. [Elimination Tournament Integration](#elimination-tournament-integration)
6. [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)

---

## Database Schema Overview

### Key Tables and Their Relationships

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
    └── round (INTEGER) ← CRITICAL: Must be numeric!
    └── roundname (VARCHAR) ← Display name

Roster (racer enrollment in rounds)
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

### Data Flow for Racing

```
RegistrationInfo → Roster → RaceChart → Results
     (racers)      (enrollment)  (heats)   (times)
```

---

## The Round Column: Critical Understanding

### The `round` Column Must Be Numeric

The `Rounds.round` column is **INTEGER** and must contain numeric values (1, 2, 3, etc.), NOT string names.

**Correct:**
```sql
roundid | round | roundname           | classid
1       | 1     | 1 Preliminary       | 1
2       | 2     | 2 Quarter Finals    | 1
3       | 3     | 3 Semi-Finals       | 1
4       | 4     | 4 Finals            | 1
```

**Incorrect (causes roster population failure):**
```sql
roundid | round              | roundname           | classid
1       | 2 Quarter Finals   | 2 Quarter Finals    | 1  ← WRONG!
2       | 3 Semi-Finals      | 3 Semi-Finals       | 1  ← WRONG!
```

### Why This Matters

The `fill_in_missing_roster_entries()` function in `inc/newracer.inc` uses:

```php
WHERE round = 1
```

If `round` contains a string like "2 Quarter Finals" instead of the integer `1`, **no racers will be enrolled in the Roster table**, which means:
- No racers appear in rounds
- Cannot generate heat schedules
- Cannot start racing

---

## Setup Sequence: Step by Step

### Standard Setup (Without Elimination Tournament)

1. **Create Classes** (via setup or partition creation)
   - When a class is created, Round 1 is automatically created with `round = 1`
   - See `inc/class_add_or_delete.inc:36-45`

2. **Register Racers** (via check-in or fake roster)
   - Racers are inserted into `RegistrationInfo`
   - `fill_in_missing_roster_entries()` is called
   - Racers are automatically enrolled in Round 1 of their class

3. **Pass Inspection**
   - Set `passedinspection = 1` for racers
   - Only inspected racers appear in scheduling

4. **Generate Schedule**
   - Click "Schedule" on coordinator page
   - Creates entries in `RaceChart`

5. **Start Racing**
   - Select round and click "Race"

### Setup with Elimination Tournament

1. **Create Classes** (same as above)
   - Classes created with Round 1 (`round = 1`)

2. **Register Racers** (same as above)
   - Racers enrolled in Round 1 via `fill_in_missing_roster_entries()`

3. **Initialize Elimination Tournament**
   - Call `initialize_elimination_tournament($classid, $config_file)`
   - This should:
     - Update Round 1's `roundname` (NOT `round`!)
     - Create additional rounds with sequential `round` values (2, 3, 4)
     - Record tournament in `EliminationTournaments` table

4. **Generate Schedule** (same as above)

5. **Race and Advance**
   - After completing a round, advance top racers to next round

---

## Fake Roster Function Analysis

### How Fake Roster Works

**File:** `ajax/action.racer.fake.inc`

```php
// 1. Create fake racers for each group
for ($g = 1; $g <= $_POST['ngroups']; ++$g) {
    $group_name = fake_partition_name($g);  // "Fake Lions", "Fake Tigers", etc.

    for ($r = 0; $r < $group_size; ++$r) {
        // 2. Insert racer with partition name
        $racerid = insert_new_racer(array(
            'firstname' => $racer['firstname'],
            'lastname' => $racer['lastname'],
            'partition' => $group_name,  // ← Creates class if doesn't exist
            ...
        ));
    }
}

// 3. Pass inspection if checkbox selected
if ($_POST['check_in']) {
    $db->exec('UPDATE RegistrationInfo SET passedinspection = 1');
}
```

### The Chain of Events

1. `insert_new_racer()` is called with `partition` name
2. `find_or_create_partition()` is called
3. If partition doesn't exist, `find_or_create_class()` is called
4. `create_class()` creates:
   - New entry in `Classes` table
   - New entry in `Rounds` table with **`round = 1`** (correct!)
5. After racer insert, `fill_in_missing_roster_entries()` enrolls racer in Round 1

### Fake Roster Compliance Status: COMPLIANT

The fake roster function correctly:
- Creates classes with Round 1 (`round = 1`)
- Enrolls racers in Round 1 via `fill_in_missing_roster_entries()`
- Sets `passedinspection = 1` when checkbox is checked

**The fake roster itself is NOT the problem.**

---

## Elimination Tournament Integration

### The Bug in `elimination-config.inc`

The bug occurs in two functions that incorrectly set `round` to the round name instead of the sequence number:

#### Bug 1: `update_existing_round_for_elimination()`

**Current (BUGGY):**
```php
function update_existing_round_for_elimination($classid, $round_config) {
    $round_name = $round_config['round_name'];

    $stmt = $db->prepare('UPDATE Rounds
                         SET round = :round, roundname = :roundname
                         WHERE classid = :classid AND round = \'1\'...');

    $stmt->execute(array(
        ':round' => $round_name,      // BUG: Should be round_sequence!
        ':roundname' => $round_name
    ));
}
```

**Correct:**
```php
function update_existing_round_for_elimination($classid, $round_config) {
    $round_sequence = $round_config['round_sequence'];  // Use sequence!
    $round_name = $round_config['round_name'];

    $stmt = $db->prepare('UPDATE Rounds
                         SET round = :round, roundname = :roundname
                         WHERE classid = :classid AND round = 1...');

    $stmt->execute(array(
        ':round' => $round_sequence,  // CORRECT: Use numeric sequence
        ':roundname' => $round_name
    ));
}
```

#### Bug 2: `create_elimination_round()`

**Current (BUGGY):**
```php
function create_elimination_round($classid, $tournament_id, $round_config) {
    $round_name = $round_config['round_name'];

    $stmt = $db->prepare('INSERT INTO Rounds (classid, round, roundname)
                         VALUES (:classid, :round, :roundname)');

    $stmt->execute(array(
        ':round' => $round_name,      // BUG: Should be round_sequence!
        ':roundname' => $round_name
    ));
}
```

**Correct:**
```php
function create_elimination_round($classid, $tournament_id, $round_config) {
    $round_sequence = $round_config['round_sequence'];  // Use sequence!
    $round_name = $round_config['round_name'];

    $stmt = $db->prepare('INSERT INTO Rounds (classid, round, roundname)
                         VALUES (:classid, :round, :roundname)');

    $stmt->execute(array(
        ':round' => $round_sequence,  // CORRECT: Use numeric sequence
        ':roundname' => $round_name
    ));
}
```

### JSON Configuration Structure

The JSON config file (`soapbox-derby-elimination.json`) has both values:

```json
{
    "round_sequence": 1,        // ← For Rounds.round (INTEGER)
    "round_name": "1 Preliminary"  // ← For Rounds.roundname (VARCHAR)
}
```

---

## Common Issues and Troubleshooting

### Issue: "Can't start race" / No heats scheduled

**Symptoms:**
- Coordinator shows 0 heats scheduled
- Schedule button doesn't work or shows "too few racers"
- Rounds appear but no racers listed

**Diagnosis:**
```sql
-- Check if Roster has entries
SELECT COUNT(*) FROM Roster;  -- Should be > 0

-- Check round values
SELECT roundid, round, roundname FROM Rounds;  -- round should be numeric

-- Check if racers are passed inspection
SELECT COUNT(*) FROM RegistrationInfo WHERE passedinspection = 1;
```

**Common Causes:**
1. `Rounds.round` contains string instead of integer
2. No racers passed inspection
3. Roster not populated

### Issue: Racers not appearing in rounds

**Diagnosis:**
```sql
-- Check roster enrollment
SELECT r.roundid, rd.roundname, COUNT(r.racerid)
FROM Roster r
JOIN Rounds rd ON r.roundid = rd.roundid
GROUP BY r.roundid;

-- Check if Round 1 exists with correct round value
SELECT * FROM Rounds WHERE round = 1;
```

**Fix:** If Round 1 doesn't have `round = 1`:
```sql
UPDATE Rounds SET round = 1 WHERE roundid = (SELECT MIN(roundid) FROM Rounds WHERE classid = X);
```

Then trigger roster population by adding/editing a racer.

### Issue: Elimination tournament initialized but racing won't start

**Diagnosis:**
```sql
-- Check elimination tournament state
SELECT * FROM EliminationTournaments;

-- Verify round numbers are sequential integers
SELECT roundid, round, roundname, classid FROM Rounds ORDER BY classid, round;
```

**Fix:** Ensure `round` column has sequential integers (1, 2, 3, 4), not string names.

---

## Correct Setup Sequence Summary

### For Standard Racing:
1. Setup database
2. Create classes (partitions)
3. Register/import racers
4. Check-in racers (pass inspection)
5. Generate schedule for Round 1
6. Race!

### For Elimination Tournament:
1. Setup database
2. Create classes (partitions) → Round 1 auto-created with `round = 1`
3. Register/import racers → Roster auto-populated
4. Check-in racers (pass inspection)
5. Initialize elimination tournament → Updates roundname, creates additional rounds
6. Generate schedule for first round
7. Race!
8. After round complete, advance racers
9. Generate schedule for next round
10. Repeat until finals

---

## Technical Reference

### Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `create_class()` | `inc/class_add_or_delete.inc` | Creates class and Round 1 |
| `insert_new_racer()` | `inc/newracer.inc` | Adds racer and triggers roster population |
| `fill_in_missing_roster_entries()` | `inc/newracer.inc` | Enrolls racers in Round 1 |
| `initialize_elimination_tournament()` | `inc/elimination-config.inc` | Sets up elimination format |
| `schedule_one_round()` | `inc/schedule_one_round.inc` | Generates heat schedule |

### Critical SQL Queries

**Roster population (must have `round = 1`):**
```sql
INSERT INTO Roster(roundid, classid, racerid)
SELECT roundid, RegistrationInfo.classid, racerid
FROM Rounds
INNER JOIN RegistrationInfo ON Rounds.classid = RegistrationInfo.classid
WHERE round = 1  -- ← MUST match integer 1
AND NOT EXISTS(SELECT 1 FROM Roster
               WHERE Roster.roundid = Rounds.roundid
               AND Roster.racerid = RegistrationInfo.racerid)
```

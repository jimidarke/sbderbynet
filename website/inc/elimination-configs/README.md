# Elimination Tournament Configuration

This directory contains JSON configuration files for elimination tournament formats.

## Configuration Schema

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `format_name` | string | Display name for the tournament format |
| `description` | string | Brief description of the format |
| `version` | string | Configuration version |
| `age_groups` | object | Map of age group configurations (keyed by identifier) |
| `scheduling_rules` | object | Global scheduling parameters |

### Age Group Configuration

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Display name (e.g., "Ages 6-8") |
| `class_name_pattern` | regex | Pattern to match class names for auto-detection |
| `expected_racers` | number | Expected number of racers (informational only) |
| `lanes` | number | Number of racing lanes |
| `rounds` | array | Array of round configurations |

### Round Configuration

| Field | Type | Description |
|-------|------|-------------|
| `round_sequence` | number | Round order (1, 2, 3, ...) |
| `round_name` | string | Display name - **MUST start with sequence number** (e.g., "1 Preliminary") |
| `races_per_racer` | number | Number of races each racer runs in this round |
| `advancement_rule` | string | How racers advance: `top_count`, `percentage`, or `placement` |
| `advance_count` | number | Maximum number of racers to advance (see behavior notes below) |
| `scoring_method` | string | How to rank racers: `total_time`, `best_time`, `average_time`, or `placement` |
| `description` | string | Human-readable description of the round |

### Scheduling Rules

| Field | Type | Description |
|-------|------|-------------|
| `heat_ordering.heat_counts` | number | Weight for heat count optimization |
| `heat_ordering.group_weighted_cars` | number | Weight for grouping cars by weight |
| `heat_ordering.avoid_consecutive` | number | Weight for avoiding consecutive races |
| `heat_ordering.avoid_same_lane` | number | Weight for avoiding same lane assignments |
| `dnf_time` | number | Time assigned for DNF (Did Not Finish) results |
| `auto_advancement` | boolean | Whether to auto-advance when rounds complete |
| `bracket_seeding` | string | Seeding method: `time_based` or `random` |

## Important Behavior Notes

### Advancement Count Behavior

**`advance_count` acts as a MAXIMUM, not a requirement.**

If fewer racers exist than `advance_count`, all racers advance to the next round. For example:

- Config says `advance_count: 27`
- Only 20 racers in the round
- Result: All 20 racers advance (no error)

This allows the same configuration to work for tournaments of varying sizes. The `expected_racers` field is purely informational and does not enforce any minimum.

### Round Name Requirements

Round names **MUST start with a sequence number** to ensure proper ordering in the UI:
- "1 Preliminary"
- "2 Quarter Finals"
- "3 Semi-Finals"
- "4 Finals"

### Races Per Racer

- `races_per_racer: 3` - Racer runs once in each lane (standard preliminary)
- `races_per_racer: 1` - Racer runs exactly once (elimination rounds)
- `races_per_racer: 2` - Racer runs twice (used for smaller brackets like VIP)

### Scoring Methods

| Method | Description |
|--------|-------------|
| `total_time` | Sum of all race times (best for multi-race rounds) |
| `best_time` | Fastest single time (best for single-race elimination) |
| `average_time` | Average of all race times |
| `placement` | Final round only - determines 1st/2nd/3rd by finish position |

## Example: Small Tournament Handling

For a tournament with only 15 racers in Ages 6-8 (config expects 73):

1. **Preliminary** (15 racers): All 15 advance (config says 27, but only 15 exist)
2. **Quarter Finals** (15 racers): Top 9 advance
3. **Semi-Finals** (9 racers): Top 3 advance
4. **Finals** (3 racers): Race for 1st/2nd/3rd

The tournament completes successfully despite having fewer racers than designed for.

## Creating Custom Configurations

1. Copy an existing configuration file
2. Modify age groups and rounds as needed
3. Ensure round names start with sequence numbers
4. Test with a small dataset before production use

## File Naming Convention

Use descriptive names with hyphens:
- `soapbox-derby-elimination.json` - Standard soapbox format
- `pinewood-derby-double.json` - Double elimination format
- `custom-event-2025.json` - Event-specific configuration

---

## Production Validation (2025-12-12)

The elimination tournament system has been validated against production data (test2 database) with the following results:

### Validated Tournament Flow

```
Ages 6-8 Tournament (34 racers):
┌─────────────────────────────────────────────────────────────────────────┐
│ Round 1: Preliminary                                                     │
│ • 34 racers × 3 races each = 102 race entries                           │
│ • Each racer races once per lane (lanes 1, 2, 3)                        │
│ • Scoring: total_time (sum of all 3 race times)                         │
│ • Top 27 by total time advance                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ Round 2: Quarter Finals                                                  │
│ • 27 racers × 1 race each = 27 race entries                             │
│ • 9 heats of 3 racers                                                   │
│ • Scoring: best_time (single race time)                                 │
│ • Top 9 by best time advance                                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ Round 3: Semi-Finals                                                     │
│ • 9 racers × 1 race each = 9 race entries                               │
│ • 3 heats of 3 racers                                                   │
│ • Scoring: best_time                                                    │
│ • Top 3 by best time advance                                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ Round 4: Finals                                                          │
│ • 3 racers × 1 race = 3 race entries                                    │
│ • 1 heat of 3 racers                                                    │
│ • Scoring: placement (finish position determines 1st/2nd/3rd)           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Validated Scoring Methods

| Method | Round Used | Validation |
|--------|------------|------------|
| `total_time` | Preliminary | ✅ Sum of 3 race times correctly calculated |
| `best_time` | QF, Semi-Finals | ✅ Single race time used for ranking |
| `placement` | Finals | ✅ Finish position determines standings |

### Validated Advancement Logic

| Transition | Config | Validated Behavior |
|------------|--------|-------------------|
| Preliminary → QF | `advance_count: 27` | ✅ Top 27 by total_time advanced |
| QF → Semi-Finals | `advance_count: 9` | ✅ Top 9 by best_time advanced |
| Semi-Finals → Finals | `advance_count: 3` | ✅ Top 3 by best_time advanced |

### Sample Production Results

**Ages 6-8 Finals (test2):**
| Place | Racer | Time | Lane |
|-------|-------|------|------|
| 🥇 1st | Octavio Hayden | 4.769s | 2 |
| 🥈 2nd | Emilia Everett | 5.913s | 3 |
| 🥉 3rd | Stephen Johnson | 6.603s | 1 |

### Key Insights from Production

1. **Lane Distribution Works**: Every racer in Preliminary raced exactly once in each lane (1, 2, 3)
2. **Partial Heats Handled**: System correctly handles when racers don't divide evenly into heats
3. **Advancement Maximum**: `advance_count` acts as maximum - if fewer racers exist, all advance
4. **Heat Generation**: 34 heats generated for 34 racers in Preliminary (one racer per heat for 3-race rounds)

### Database Structure Reference

**EliminationTournaments:** Links classes to configuration files and tracks tournament state
**Rounds:** Stores round metadata including `roundname`, `is_triple_elim`, `elim_type`
**Roster:** Tracks which racers are in each round
**RaceChart:** Stores race results with `finishtime`, `finishplace`, `lane`

For complete validation details, see `/docs/ELIMINATION_CONFIG_VALIDATION.md`

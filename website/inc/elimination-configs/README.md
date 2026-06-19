# Elimination Tournament Configuration

This directory contains JSON configuration files for elimination tournament formats.

## Configuration Schema

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `format_name` | string | **Yes** | Display name for the tournament format |
| `age_groups` | object | **Yes** | Map of age group configurations (keyed by identifier) |
| `description` | string | No | Brief description of the format (display only) |
| `version` | string | No | Configuration version (defaults to `1.0`) |
| `scheduling_rules` | object | No | Global scheduling parameters — only `heat_ordering.*` is read by the engine (see below) |

### Age Group Configuration

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | **Yes** | Display name (e.g., "Ages 6-8") |
| `class_name_pattern` | regex | **Yes** | Case-insensitive pattern to match class names for auto-detection |
| `rounds` | array | **Yes** | Non-empty array of round configurations |
| `expected_racers` | number | No | Informational only — enforces nothing |
| `lanes` | number | No | **Informational only.** The actual racing lane count comes from the global timer/race setting (`RaceInfo.lane_count`), not this field |

### Round Configuration

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `round_sequence` | number | **Yes** | Round order (1, 2, 3, ...). Stored as the numeric round key |
| `round_name` | string | **Yes** | Display name — **MUST start with the sequence number** (e.g., "1 Preliminary") and be **unique within the age group** (the engine matches rounds by this string) |
| `races_per_racer` | number | **Yes** | Races each racer runs this round. **Only `1` and `3` are supported** (see notes) |
| `advancement_rule` | string | **Yes** | `top_count` or `placement`. (`percentage` validates but is **not implemented** — see notes) |
| `scoring_method` | string | **Yes** | `total_time`, `best_time`, `average_time`, `drop_slowest`, or `placement` |
| `advance_count` | number | For cut rounds | Maximum racers to advance. **Optional in the schema (defaults to `0`), but `0`/absent means nobody advances** — required for every non-final round. See behavior notes |
| `description` | string | No | Human-readable description (display only) |

### Scheduling Rules

Only the four `heat_ordering.*` weights are read by the engine — `apply_elimination_scheduling_rules()` writes them into `RaceInfo` at tournament init to tune heat-order optimization. **Every other key under `scheduling_rules` is currently decorative** (parsed by nothing).

| Field | Type | Read by engine? | Description |
|-------|------|-----------------|-------------|
| `heat_ordering.heat_counts` | number | ✅ Yes | Weight for heat count optimization (→ `RaceInfo heat-counts`) |
| `heat_ordering.group_weighted_cars` | number | ✅ Yes | Weight for grouping cars by weight (→ `RaceInfo group-weighted-cars`) |
| `heat_ordering.avoid_consecutive` | number | ✅ Yes | Weight for avoiding consecutive races (→ `RaceInfo avoid-consecutive`) |
| `heat_ordering.avoid_same_lane` | number | ✅ Yes | Weight for avoiding same-lane assignments (→ `RaceInfo avoid-same-lane`) |
| `dnf_time` | number | ❌ No | **Ignored.** The DNF sentinel (`99.999`) is hardcoded in the engine, not read from here |
| `auto_advancement` | boolean | ❌ No | **Ignored.** Round advancement is driven by the coordinator, not this flag |
| `bracket_seeding` | string | ❌ No | **Ignored.** No seeding logic reads this |
| `preliminary_requirements.*` | object | ❌ No | **Ignored.** Documentary only (`races_per_racer`, `allow_partial_heats`, `minimum_racers_per_heat`, `comment`) |

## Important Behavior Notes

### Advancement Count Behavior

**`advance_count` acts as a MAXIMUM, not a requirement.**

If fewer racers exist than `advance_count`, all racers advance to the next round. For example:

- Config says `advance_count: 27`
- Only 20 racers in the round
- Result: All 20 racers advance (no error)

This allows the same configuration to work for tournaments of varying sizes. The `expected_racers` field is purely informational and does not enforce any minimum.

**Tie handling:** racers whose score ties the last advancing score also advance (compared within `ELIMINATION_SCORE_EPSILON` = `0.0005`s), so a boundary tie is never split arbitrarily.

**`advance_count: 0` (or absent) advances nobody** — this is how the terminal/final round is marked, alongside `advancement_rule: placement`.

### Advancement Rule

- `top_count` — cut to the top `advance_count` racers by `scoring_method`.
- `placement` — marks the terminal (final) round; nobody advances.
- `percentage` — **passes validation but is not implemented.** No engine reads `advance_percentage`, so a `percentage` round will not actually cut by percent. Use `top_count` with an explicit `advance_count`.

### Round Name Requirements

Round names **MUST start with a sequence number** to ensure proper ordering in the UI:
- "1 Preliminary"
- "2 Quarter Finals"
- "3 Semi-Finals"
- "4 Finals"

### Races Per Racer

**Only `1` and `3` are supported by the scheduler.**

- `races_per_racer: 3` — Racer runs once in each lane (standard multi-run preliminary; sets `n_times_per_lane = 1`)
- `races_per_racer: 1` — Racer runs exactly once (single-race elimination rounds)

Any other value matches no dedicated branch in the scheduler and is logged as `Unsupported races_per_racer value`. ⚠️ The bundled VIP age group uses `races_per_racer: 2`, which is **not** honored — it does not produce two scheduled runs per racer. Use `1` or `3`.

### Scoring Methods

| Method | Aggregate | Description |
|--------|-----------|-------------|
| `total_time` | `SUM(finishtime)` | Sum of all race times (best for multi-run rounds) |
| `best_time` | `MIN(finishtime)` | Fastest single time (best for single-race elimination) |
| `average_time` | `AVG(finishtime)` | Average of all race times |
| `drop_slowest` | drop max, average the rest | Drops each racer's slowest run and averages the remainder; a single-run racer keeps that time (used by the drop-slowest prelim variant) |
| `placement` | `MIN(finishplace)` | **Final round only** — ranks by finish position (1st/2nd/3rd). Drives standings, not advancement |

DNF runs carry the `99.999` sentinel and participate in every time aggregate by design (a DNF is a heavy penalty, not a discarded run).

#### Scoring-Method Override (coordinator toggle)

For **multi-run rounds** (`races_per_racer > 1`, non-`placement`), the coordinator's Settings *scoring* toggle (`RaceInfo.scoring`) **overrides** the file's `scoring_method` for both displayed standings and who advances (`elimination_effective_scoring_method()`):

| `RaceInfo.scoring` | Effective method |
|--------------------|------------------|
| `0` (default) | Keeps the config's authored method |
| `1` | Forces `drop_slowest` |
| `2` | Forces `best_time` |

Single-run rounds (`best_time` QF/SF) and `placement` finals are unaffected. This is why the two bundled configs differ only in the preliminary `scoring_method` — at race time the toggle can reproduce either.

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

---

## Engine Reconciliation (2026-06-19)

This README was reconciled against the actual engine (`inc/elimination-config.inc`, `inc/elimination-standings.inc`, `inc/elimination-advancement.inc`, `ajax/action.schedule.generate.inc`, `inc/schedule_one_round.inc`). Corrections made:

1. **Added `drop_slowest`** to the scoring methods — it is fully implemented (standings + advancement) and used by `soapbox-derby-elimination-dropslowest.json`, but was previously undocumented.
2. **`races_per_racer` supports only `1` and `3`.** The bundled VIP group's `races_per_racer: 2` is logged as unsupported and does not schedule two runs.
3. **`advancement_rule: percentage` is a stub** — it validates but no engine reads `advance_percentage`, so it does not cut by percent.
4. **`dnf_time`, `auto_advancement`, `bracket_seeding`, and `preliminary_requirements` are decorative** — read by no code. Only `heat_ordering.*` is consumed from `scheduling_rules`.
5. **Per-age-group `lanes` is informational** — the real lane count is the global `RaceInfo.lane_count`.
6. **`advance_count` is schema-optional (defaults to `0`)** but required for any non-final round; `0`/absent advances nobody, and boundary ties advance together (epsilon `0.0005`s).
7. **Documented the coordinator scoring-toggle override** of the preliminary `scoring_method` for multi-run rounds.

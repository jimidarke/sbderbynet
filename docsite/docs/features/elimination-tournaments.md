# Elimination Tournaments

JSON-defined tournament formats with multi-round advancement. Configs live in `website/inc/elimination-configs/*.json` (hardcoded — not runtime-editable). The editor at `elimination-config-editor.php` is for offline tweaking.

---

## Database schema

### `EliminationTournaments`

| Field | Type | Description |
|---|---|---|
| `tournament_id` | INTEGER PRIMARY KEY | Auto-increment |
| `classid` | INTEGER NOT NULL | FK → `Classes.classid` |
| `config_file` | VARCHAR(100) NOT NULL | JSON config filename |
| `age_group_key` | VARCHAR(50) NOT NULL | Age group key from config |
| `current_round` | INTEGER NOT NULL DEFAULT 1 | Current round number |
| `total_rounds` | INTEGER NOT NULL | Total rounds |
| `active` | BOOLEAN NOT NULL DEFAULT 1 | Active flag |
| `created_at` | TIMESTAMP | Creation time |
| `completed_at` | TIMESTAMP NULL | Completion time |

Indexes: `classid`, `active`.

### `EliminationRoundState`

| Field | Type | Description |
|---|---|---|
| `state_id` | INTEGER PRIMARY KEY | Auto-increment |
| `tournament_id` | INTEGER NOT NULL | FK |
| `roundid` | INTEGER NOT NULL | FK → `Rounds.roundid` |
| `round_sequence` | INTEGER NOT NULL | 1, 2, 3, … |
| `status` | VARCHAR(20) DEFAULT 'pending' | pending / active / completed |
| `races_per_racer` | INTEGER NOT NULL | This round |
| `advancement_rule` | VARCHAR(20) NOT NULL | top_count / percentage / placement |
| `advance_count` | INTEGER DEFAULT 0 | Number to advance |
| `scoring_method` | VARCHAR(20) NOT NULL | total_time / best_time / placement |
| `started_at` | TIMESTAMP NULL | |
| `completed_at` | TIMESTAMP NULL | |

Indexes: `tournament_id`, `roundid`, `round_sequence`.

### `EliminationAdvancement`

| Field | Type | Description |
|---|---|---|
| `advancement_id` | INTEGER PRIMARY KEY | Auto-increment |
| `tournament_id` | INTEGER NOT NULL | FK |
| `from_round` | INTEGER NOT NULL | FK → `Rounds.roundid` |
| `to_round` | INTEGER NOT NULL | FK → `Rounds.roundid` |
| `racerid` | INTEGER NOT NULL | FK → `RegistrationInfo.racerid` |
| `rank_in_round` | INTEGER NOT NULL | Racer's rank in the round |
| `score` | DOUBLE NULL | Time or points |
| `advanced` | BOOLEAN DEFAULT 0 | Did they advance |
| `advanced_at` | TIMESTAMP NULL | |

Indexes: `tournament_id`, `from_round`, `to_round`, `racerid`.

### Foreign-key relationships

```
EliminationTournaments.classid → Classes.classid
EliminationRoundState.tournament_id → EliminationTournaments.tournament_id
EliminationRoundState.roundid → Rounds.roundid
EliminationAdvancement.tournament_id → EliminationTournaments.tournament_id
EliminationAdvancement.from_round → Rounds.roundid
EliminationAdvancement.to_round → Rounds.roundid
EliminationAdvancement.racerid → RegistrationInfo.racerid
```

### Schema files

- SQLite: `website/sql/sqlite/elimination-tables.inc`
- MS Access: `website/sql/access/elimination-tables.inc`
- Schema update: `website/sql/sqlite/update-schema.inc` (version 16)

---

## Config-editor field mapping

### Top-level

| JSON | UI | Notes |
|---|---|---|
| `format_name` | `#format-name` | required |
| `description` | `#description` | optional |
| `version` | `#version` | defaults to "1.0" |
| `age_groups` | dynamic panels | object with age group keys |
| `scheduling_rules` | multiple fields | see below |

### Age group

| JSON | UI |
|---|---|
| `name` | `.group-name` |
| `class_name_pattern` | `.class-pattern` (regex) |
| `expected_racers` | `.expected-racers` |
| `lanes` | `.lanes` (1–20) |
| `rounds` | round panels |

### Round

| JSON | UI | Notes |
|---|---|---|
| `round_sequence` | auto-generated | from order |
| `round_name` | `.round-name` | **must start with a number** |
| `races_per_racer` | `.races-per-racer` | 1–6 |
| `advancement_rule` | `.advancement-rule` | top_count / percentage / placement |
| `advance_count` | `.advance-count` | shown when rule = top_count |
| `advance_percentage` | `.advance-percentage` | shown when rule = percentage |
| `scoring_method` | `.scoring-method` | total_time / best_time / average_time / placement |
| `description` | `.round-description` | optional |

### Scheduling rules

| JSON | UI | Allowed |
|---|---|---|
| `heat_ordering.heat_counts` | `#heat-counts` | 0/50/300/1000/10 |
| `heat_ordering.group_weighted_cars` | `#group-weighted-cars` | 0/50/300/1000/100 |
| `heat_ordering.avoid_consecutive` | `#avoid-consecutive` | 0/50/300/5000 |
| `heat_ordering.avoid_same_lane` | `#avoid-same-lane` | 0/50/300/1000/200 |
| `dnf_time` | `#dnf-time` | default 99.000 |
| `auto_advancement` | `#auto-advancement` | boolean |
| `bracket_seeding` | `#bracket-seeding` | time_based / random |

`preliminary_requirements.*` round-trips but isn't shown in the UI.

### Conditional fields

| Advancement rule | Visible field | Serialised |
|---|---|---|
| `top_count` | `advance_count` | `advance_count` only |
| `percentage` | `advance_percentage` | `advance_percentage` only |
| `placement` | none | `advance_count: 0` |

### Validation

**Client-side**:

- Format name: required, non-empty.
- Age groups: ≥ 1.
- Age group key: matches `/^[a-z0-9_]+$/`.
- Rounds: ≥ 1 per age group.
- Round name: matches `/^\d+/` (starts with a digit).

**Server-side**:

- Structure: `format_name`, `age_groups` required.
- Age group: `name`, `class_name_pattern`, `rounds` required.
- Round: `round_sequence`, `round_name`, `races_per_racer`, `advancement_rule`, `scoring_method` required.
- Active-tournament check: configs with active tournaments are read-only.

---

## Files

- Editor: `website/elimination-config-editor.php`
- JS: `website/js/elimination-config-editor.js`
- PHP validation: `website/inc/elimination-config.inc`
- Configs: `website/inc/elimination-configs/*.json`

See also: [Round Setup](round-setup.md).

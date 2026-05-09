# Elimination Tournament Database Schema

## Table Definitions

### EliminationTournaments

| Field | Type | Description |
|-------|------|-------------|
| `tournament_id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `classid` | INTEGER NOT NULL | FK → Classes.classid |
| `config_file` | VARCHAR(100) NOT NULL | JSON config filename |
| `age_group_key` | VARCHAR(50) NOT NULL | Age group key from config |
| `current_round` | INTEGER NOT NULL DEFAULT 1 | Current round number |
| `total_rounds` | INTEGER NOT NULL | Total rounds in tournament |
| `active` | BOOLEAN NOT NULL DEFAULT 1 | Tournament active flag |
| `created_at` | TIMESTAMP | Tournament creation time |
| `completed_at` | TIMESTAMP NULL | Tournament completion time |

**Indexes:** `classid`, `active`

### EliminationRoundState

| Field | Type | Description |
|-------|------|-------------|
| `state_id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `tournament_id` | INTEGER NOT NULL | FK → EliminationTournaments |
| `roundid` | INTEGER NOT NULL | FK → Rounds.roundid |
| `round_sequence` | INTEGER NOT NULL | Round number (1, 2, 3...) |
| `status` | VARCHAR(20) DEFAULT 'pending' | pending/active/completed |
| `races_per_racer` | INTEGER NOT NULL | Races per racer this round |
| `advancement_rule` | VARCHAR(20) NOT NULL | top_count/percentage/placement |
| `advance_count` | INTEGER DEFAULT 0 | Number to advance |
| `scoring_method` | VARCHAR(20) NOT NULL | total_time/best_time/placement |
| `started_at` | TIMESTAMP NULL | Round start time |
| `completed_at` | TIMESTAMP NULL | Round completion time |

**Indexes:** `tournament_id`, `roundid`, `round_sequence`

### EliminationAdvancement

| Field | Type | Description |
|-------|------|-------------|
| `advancement_id` | INTEGER PRIMARY KEY | Auto-increment ID |
| `tournament_id` | INTEGER NOT NULL | FK → EliminationTournaments |
| `from_round` | INTEGER NOT NULL | FK → Rounds.roundid |
| `to_round` | INTEGER NOT NULL | FK → Rounds.roundid |
| `racerid` | INTEGER NOT NULL | FK → RegistrationInfo.racerid |
| `rank_in_round` | INTEGER NOT NULL | Racer's rank in the round |
| `score` | DOUBLE NULL | Time or points |
| `advanced` | BOOLEAN DEFAULT 0 | Whether racer advanced |
| `advanced_at` | TIMESTAMP NULL | Advancement timestamp |

**Indexes:** `tournament_id`, `from_round`, `to_round`, `racerid`

---

## Field Mapping Reference

### PHP → Database

| PHP Variable | Database Column | Table |
|--------------|-----------------|-------|
| `$classid` | `classid` | EliminationTournaments |
| `$config_file` | `config_file` | EliminationTournaments |
| `$age_group['group_key']` | `age_group_key` | EliminationTournaments |
| `count($age_group['rounds'])` | `total_rounds` | EliminationTournaments |

### JSON Config → Database

| JSON Field | Database Column | Notes |
|------------|-----------------|-------|
| Object key (e.g., "ages_6_8") | `age_group_key` | From `age_groups` object |
| `rounds[]` array length | `total_rounds` | Count of rounds |
| `advancement_rule` | `advancement_rule` | top_count/percentage/placement |
| `scoring_method` | `scoring_method` | total_time/best_time/placement |

---

## Foreign Key Relationships

```
EliminationTournaments.classid → Classes.classid
EliminationRoundState.tournament_id → EliminationTournaments.tournament_id
EliminationRoundState.roundid → Rounds.roundid
EliminationAdvancement.tournament_id → EliminationTournaments.tournament_id
EliminationAdvancement.from_round → Rounds.roundid
EliminationAdvancement.to_round → Rounds.roundid
EliminationAdvancement.racerid → RegistrationInfo.racerid
```

---

## Schema Files

- **SQLite:** `website/sql/sqlite/elimination-tables.inc`
- **MS Access:** `website/sql/access/elimination-tables.inc`
- **Schema Update:** `website/sql/sqlite/update-schema.inc` (version 16)

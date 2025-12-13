# Elimination Configuration Editor - Field Reference

## JSON to UI Field Mapping

### Top-Level Fields

| JSON Field | UI Element | Notes |
|------------|------------|-------|
| `format_name` | `#format-name` input | Required |
| `description` | `#description` textarea | Optional |
| `version` | `#version` input | Defaults to "1.0" |
| `age_groups` | Dynamic panels | Object with age group keys |
| `scheduling_rules` | Multiple fields | See scheduling section |

### Age Group Fields

| JSON Field | UI Element | Notes |
|------------|------------|-------|
| `name` | `.group-name` input | Display name |
| `class_name_pattern` | `.class-pattern` input | Regex pattern |
| `expected_racers` | `.expected-racers` input | Number |
| `lanes` | `.lanes` input | 1-20 |
| `rounds` | Round panels | Array of round configs |

### Round Fields

| JSON Field | UI Element | Notes |
|------------|------------|-------|
| `round_sequence` | Auto-generated | Based on order (1, 2, 3...) |
| `round_name` | `.round-name` input | Must start with number |
| `races_per_racer` | `.races-per-racer` select | 1-6 |
| `advancement_rule` | `.advancement-rule` select | top_count/percentage/placement |
| `advance_count` | `.advance-count` input | Shown when rule = top_count |
| `advance_percentage` | `.advance-percentage` input | Shown when rule = percentage |
| `scoring_method` | `.scoring-method` select | total_time/best_time/average_time/placement |
| `description` | `.round-description` textarea | Optional |

### Scheduling Rules

| JSON Field | UI Element | Notes |
|------------|------------|-------|
| `heat_ordering.heat_counts` | `#heat-counts` select | 0/50/300/1000/10 |
| `heat_ordering.group_weighted_cars` | `#group-weighted-cars` select | 0/50/300/1000/100 |
| `heat_ordering.avoid_consecutive` | `#avoid-consecutive` select | 0/50/300/5000 |
| `heat_ordering.avoid_same_lane` | `#avoid-same-lane` select | 0/50/300/1000/200 |
| `dnf_time` | `#dnf-time` input | Default 99.000 |
| `auto_advancement` | `#auto-advancement` checkbox | Boolean |
| `bracket_seeding` | `#bracket-seeding` select | time_based/random |

**Note:** `preliminary_requirements.*` fields are preserved during round-trip but not shown in UI.

---

## Conditional Field Handling

| Advancement Rule | Visible Field | Serialized Field |
|-----------------|---------------|------------------|
| `top_count` | `advance_count` | `advance_count` only |
| `percentage` | `advance_percentage` | `advance_percentage` only |
| `placement` | Neither | `advance_count: 0` |

---

## Validation Rules

### Client-Side (JavaScript)
- Format name: Required, non-empty
- Age groups: At least 1 required
- Age group key: Must match `/^[a-z0-9_]+$/`
- Rounds: At least 1 per age group
- Round name: Must start with digit `/^\d+/`

### Server-Side (PHP)
- Structure: `format_name`, `age_groups` required
- Age group: `name`, `class_name_pattern`, `rounds` required
- Round: `round_sequence`, `round_name`, `races_per_racer`, `advancement_rule`, `scoring_method` required
- Active tournament check: Configs with active tournaments are read-only

---

## Files

- **Editor:** `website/elimination-config-editor.php`
- **JavaScript:** `website/js/elimination-config-editor.js`
- **PHP Validation:** `website/inc/elimination-config.inc`
- **Config Files:** `website/inc/elimination-configs/*.json`

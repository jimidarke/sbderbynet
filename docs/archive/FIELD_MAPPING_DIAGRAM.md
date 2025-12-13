# Elimination Configuration Editor - Complete Field Mapping

## Visual Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  EXISTING JSON FILE (soapbox-derby-elimination.json)            │
├─────────────────────────────────────────────────────────────────┤
│  {                                                               │
│    "format_name": "Soapbox Derby Triple Elimination",    ✓ UI   │
│    "description": "Standard soapbox derby...",           ✓ UI   │
│    "version": "1.0",                                     ✓ UI   │
│                                                                  │
│    "age_groups": {                                              │
│      "ages_6_8": {                                              │
│        "name": "Ages 6-8",                               ✓ UI   │
│        "class_name_pattern": "^(Ages 6-8|6-8).*$",      ✓ UI   │
│        "expected_racers": 73,                            ✓ UI   │
│        "lanes": 3,                                       ✓ UI   │
│        "rounds": [                                              │
│          {                                                       │
│            "round_sequence": 1,                      ✓ AUTO    │
│            "round_name": "1 Preliminary",            ✓ UI   │
│            "races_per_racer": 3,                     ✓ UI   │
│            "advancement_rule": "top_count",          ✓ UI   │
│            "advance_count": 27,                      ✓ UI   │
│            "scoring_method": "total_time",           ✓ UI   │
│            "description": "Each racer runs..."       ✓ UI   │
│          }                                                       │
│        ]                                                         │
│      }                                                           │
│    },                                                            │
│                                                                  │
│    "scheduling_rules": {                                        │
│      "heat_ordering": {                                         │
│        "heat_counts": 10,                            ✓ UI   │
│        "group_weighted_cars": 100,                   ✓ UI   │
│        "avoid_consecutive": 5000,                    ✓ UI   │
│        "avoid_same_lane": 200                        ✓ UI   │
│      },                                                          │
│      "preliminary_requirements": {               ⚠ PRESERVED  │
│        "races_per_racer": 3,                     ⚠ NOT IN UI │
│        "allow_partial_heats": true,              ⚠ NOT IN UI │
│        "minimum_racers_per_heat": 1,             ⚠ NOT IN UI │
│        "comment": "Each racer must..."           ⚠ NOT IN UI │
│      },                                                          │
│      "dnf_time": 99.000,                             ✓ UI   │
│      "auto_advancement": true,                       ✓ UI   │
│      "bracket_seeding": "time_based"                 ✓ UI   │
│    }                                                             │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  AJAX QUERY: query.elimination.config.detail                    │
│  GET filename=soapbox-derby-elimination.json                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  JAVASCRIPT: renderConfigForm(config)                           │
│  • Store originalSchedulingRules (includes preliminary_req)     │
│  • Populate all UI fields from config                           │
│  • Enable/disable based on lock status                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  UI FORM (elimination-config-editor.php)                        │
├─────────────────────────────────────────────────────────────────┤
│  Configuration Details                                          │
│  ┌──────────────────────────────────────────────────┐          │
│  │ Format Name: [Soapbox Derby Triple Elimination] │ ← USER   │
│  │ Description: [Standard soapbox derby format...] │ ← USER   │
│  │ Version:     [1.0]                               │ ← USER   │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
│  Age Groups                      [Add Age Group]                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ Ages 6-8                                    [Remove]   │    │
│  │ ┌────────────────────────────────────────────────────┐ │    │
│  │ │ Age Group Key:      [ages_6_8]             │ ← USER│ │    │
│  │ │ Display Name:       [Ages 6-8]             │ ← USER│ │    │
│  │ │ Class Pattern:      [^(Ages 6-8|6-8).*$]  │ ← USER│ │    │
│  │ │ Expected Racers:    [73]                   │ ← USER│ │    │
│  │ │ Lanes:              [3]                    │ ← USER│ │    │
│  │ │                                                     │ │    │
│  │ │ Rounds                            [Add Round]      │ │    │
│  │ │ ┌──────────────────────────────────────────────┐  │ │    │
│  │ │ │ ☰ Round 1: 1 Preliminary              [×]   │  │ │    │
│  │ │ │ Round Name:        [1 Preliminary]  ← USER  │  │ │    │
│  │ │ │ Races Per Racer:   [3 ▼]           ← USER  │  │ │    │
│  │ │ │ Advancement Rule:  [Top Count ▼]   ← USER  │  │ │    │
│  │ │ │ Advance Count:     [27]             ← USER  │  │ │    │
│  │ │ │ Scoring Method:    [Total Time ▼]  ← USER  │  │ │    │
│  │ │ │ Description:       [Each racer...] ← USER  │  │ │    │
│  │ │ └──────────────────────────────────────────────┘  │ │    │
│  │ └────────────────────────────────────────────────────┘ │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Scheduling Rules                                               │
│  ┌──────────────────────────────────────────────────┐          │
│  │ Heat Counts:         [Custom (10) ▼]     │ ← USER│          │
│  │ Group Weighted Cars: [Custom (100) ▼]    │ ← USER│          │
│  │ Avoid Consecutive:   [Heavy (5000) ▼]    │ ← USER│          │
│  │ Avoid Same Lane:     [Custom (200) ▼]    │ ← USER│          │
│  │ DNF Time:            [99.000]             │ ← USER│          │
│  │ ☑ Auto Advancement                        │ ← USER│          │
│  │ Bracket Seeding:     [Time Based ▼]      │ ← USER│          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
│  ⚠ preliminary_requirements NOT SHOWN BUT PRESERVED             │
│                                                                  │
│            [Save Configuration]  [Cancel]                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  JAVASCRIPT: serializeFormToConfig()                            │
│  1. Start with originalSchedulingRules (has preliminary_req)    │
│  2. Update only UI fields                                       │
│  3. Preserve preliminary_requirements untouched                 │
│  4. Return complete config object                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  AJAX POST: action.elimination.config.save                      │
│  operation=update                                               │
│  filename=soapbox-derby-elimination.json                        │
│  config_json={...complete config with preliminary_req...}       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHP: validate_elimination_config($config)                      │
│  • Check format_name exists                                     │
│  • Check age_groups exists                                      │
│  • Validate each age group                                      │
│  • Validate each round                                          │
│  • Check advancement_rule values                                │
│  • Check scoring_method values                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHP: get_classes_using_config($filename)                       │
│  SELECT class FROM EliminationTournaments                       │
│  WHERE config_file = 'soapbox-derby-elimination.json'           │
│    AND active = 1                                               │
│  → Returns [] (no active tournaments) → OK to save              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHP: save_elimination_config_file($filename, $config)          │
│  1. Create backup: soapbox-derby...json.2025-12-08-143022.backup│
│  2. Acquire file lock: flock(LOCK_EX)                          │
│  3. Write JSON: JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES     │
│  4. Release lock: flock(LOCK_UN)                               │
│  5. Verify JSON: json_decode(file_get_contents(...))           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  SAVED JSON FILE (soapbox-derby-elimination.json)              │
├─────────────────────────────────────────────────────────────────┤
│  {                                                               │
│    "format_name": "...",              ← FROM UI                 │
│    "description": "...",              ← FROM UI                 │
│    "version": "1.0",                  ← FROM UI                 │
│    "age_groups": {...},               ← FROM UI                 │
│    "scheduling_rules": {                                        │
│      "heat_ordering": {...},         ← FROM UI                 │
│      "preliminary_requirements": {   ← PRESERVED! ✓           │
│        "races_per_racer": 3,          ← ORIGINAL                │
│        "allow_partial_heats": true,   ← ORIGINAL                │
│        "minimum_racers_per_heat": 1,  ← ORIGINAL                │
│        "comment": "..."               ← ORIGINAL                │
│      },                                                          │
│      "dnf_time": 99.000,             ← FROM UI                 │
│      "auto_advancement": true,        ← FROM UI                 │
│      "bracket_seeding": "time_based"  ← FROM UI                 │
│    }                                                             │
│  }                                                               │
│                                                                  │
│  ✅ ALL UI FIELDS UPDATED                                       │
│  ✅ PRELIMINARY_REQUIREMENTS PRESERVED                          │
│  ✅ VALID JSON FORMAT                                           │
│  ✅ READY FOR CROSS-SYSTEM SHARING                              │
└─────────────────────────────────────────────────────────────────┘
```

## Key Points

### ✅ Complete Round-Trip Preservation

1. **Load Phase**: Store original `scheduling_rules` including `preliminary_requirements`
2. **Edit Phase**: User modifies only visible UI fields
3. **Save Phase**: Merge UI changes with preserved fields
4. **Result**: Output JSON is identical to input except for user changes

### ✅ Field Categories

| Category | Count | Handling |
|----------|-------|----------|
| UI-Visible Fields | 19 | Direct two-way binding |
| Auto-Generated Fields | 1 | `round_sequence` computed from order |
| Preserved Fields | 4 | Stored and merged during save |
| **Total Fields** | **24** | **All handled correctly** |

### ✅ Validation Layers

1. **Client-Side (JavaScript)**
   - Immediate feedback
   - Format validation
   - Required field checks

2. **Server-Side (PHP)**
   - Schema validation
   - Business rule checks
   - Active tournament prevention

3. **File System**
   - Lock-based concurrency control
   - Backup before overwrite
   - JSON verification after write

## Examples

### Example 1: Modify Round Name Only

**Input JSON:**
```json
{
  "format_name": "My Config",
  "scheduling_rules": {
    "preliminary_requirements": {"races_per_racer": 3}
  }
}
```

**User Action:** Change format name to "My Updated Config"

**Output JSON:**
```json
{
  "format_name": "My Updated Config",      ← CHANGED
  "scheduling_rules": {
    "preliminary_requirements": {"races_per_racer": 3}  ← PRESERVED ✓
  }
}
```

### Example 2: Add New Age Group

**User Action:** Click "Add Age Group", fill fields, save

**Result:**
- New age group added to `age_groups` object
- All existing age groups unchanged
- `preliminary_requirements` still present ✓

### Example 3: Change Advancement Rule

**User Action:** Change "top_count" → "percentage"

**Input Round:**
```json
{
  "advancement_rule": "top_count",
  "advance_count": 27
}
```

**Output Round:**
```json
{
  "advancement_rule": "percentage",
  "advance_percentage": 50
}
```

**Note:** Field changes from `advance_count` to `advance_percentage` automatically!

## Cross-System Compatibility Guarantee

✅ **Files created by UI editor are 100% compatible with:**
- Tournament initialization system
- Standings calculator
- Kiosk displays
- MQTT messaging system
- External systems sharing the same JSON schema

✅ **Future-proof:**
- Unknown fields are preserved during round-trip
- New fields can be added without breaking editor
- Validation only checks required fields

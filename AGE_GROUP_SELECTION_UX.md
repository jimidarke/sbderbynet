# Age Group Selection UX - Pattern Matching vs Explicit Selection

## Problem with Original Design

### ❌ Automatic Pattern Matching (Fragile)

```
User Flow:
1. Select Class: "Ages 6-8 Boys"
2. Select Config: "soapbox-derby-elimination.json"
3. Click "Initialize Tournament"

Backend (Hidden):
4. Get class name from database → "Ages 6-8 Boys"
5. Try pattern match: "^(Ages 6-8|6-8|6 to 8).*$"
6. Match? ✓ (lucky!)
7. Initialize tournament with ages_6_8 age group

Problems:
- ❌ User has no visibility into age group selection
- ❌ Silent failure if pattern doesn't match
- ❌ No way to override automatic selection
- ❌ Requires perfect regex patterns in config
- ❌ Fails with slight naming variations:
  • "Six to Eight Year Olds" → NO MATCH
  • "6-8 age group" → NO MATCH (case-sensitive)
  • "Ages 6 through 8" → NO MATCH
  • "Ages 6,7,8" → NO MATCH
```

## ✅ New Design: Explicit Selection with Auto-Suggest

### Improved User Flow

```
1. Select Class: "Ages 6-8 Boys"
2. Select Config: "soapbox-derby-elimination.json"

   → System loads age groups from config
   → Shows dropdown with ALL available age groups

3. Age Group Dropdown appears:
   ┌────────────────────────────────────────────────────┐
   │ Age Group for this Class:                          │
   │ ┌────────────────────────────────────────────────┐ │
   │ │ Ages 6-8 (4 rounds, ~73 racers) ⭐ Suggested  │ │ ← Auto-selected
   │ │ Ages 9-11 (4 rounds, ~62 racers)              │ │
   │ │ Ages 12-14 (3 rounds, ~23 racers)             │ │
   │ │ VIPs (2 rounds, ~15 racers)                   │ │
   │ └────────────────────────────────────────────────┘ │
   └────────────────────────────────────────────────────┘

   ✓ Auto-detected "Ages 6-8" based on class name pattern

4. User can:
   - Accept suggestion (already selected)
   - Override and pick different age group

5. Click "Initialize Tournament"
6. Confirmation dialog shows selected age group
7. Tournament initialized with explicit choice
```

### Benefits

✅ **Visible**: User sees all available options
✅ **Flexible**: Can override pattern matching
✅ **Forgiving**: Works with any class naming
✅ **Informative**: Shows rounds count and expected racers
✅ **Safe**: Explicit confirmation before initialization
✅ **Backward Compatible**: Pattern matching still works as auto-suggest

## Technical Implementation

### New AJAX Endpoint

**File:** `website/ajax/query.elimination.config.age-groups.inc`

```php
GET parameters:
  - config_file: Configuration to load
  - classid: (Optional) Class for pattern matching

Returns:
{
  "outcome": {"summary": "success"},
  "age_groups": [
    {
      "key": "ages_6_8",
      "name": "Ages 6-8",
      "pattern": "^(Ages 6-8|6-8|6 to 8).*$",
      "expected_racers": 73,
      "lanes": 3,
      "rounds_count": 4,
      "rounds_summary": [
        {"name": "1 Preliminary", "races_per_racer": 3},
        {"name": "2 Quarter Finals", "races_per_racer": 1},
        ...
      ],
      "pattern_match": true  // This age group matched the class name
    },
    ...
  ],
  "suggested_key": "ages_6_8",
  "class_name": "Ages 6-8 Boys",
  "format_name": "Soapbox Derby Triple Elimination"
}
```

### Updated Initialization

**File:** `website/ajax/action.elimination.tournament.initialize.inc`

```php
POST parameters:
  - classid: Class ID
  - config_file: Configuration file
  - age_group_key: Explicit age group selection (NEW!)

Backend logic:
  if (age_group_key) {
    // Use explicit selection (PREFERRED)
    $age_group = $config['age_groups'][$age_group_key];
  } else {
    // Fall back to pattern matching
    $age_group = find_age_group_for_class($config, $classid);
  }
```

### Frontend JavaScript

**File:** `website/js/elimination-tournament.js`

New functions:
- `load_age_groups_for_config()` - Loads age groups when config selected
- `populate_age_group_selector()` - Builds dropdown with suggestions
- `show_age_group_selector()` - Displays the selector
- `hide_age_group_selector()` - Hides when not needed

Event flow:
```javascript
$('#elimination_config_select').on('change', function() {
  var config_file = $(this).val();
  if (config_file) {
    // Load age groups and show selector
    load_age_groups_for_config(config_file, current_class_id);
  }
});
```

## UI Examples

### Example 1: Pattern Match Found (Auto-Suggest)

```
Class Name: "Ages 6-8 Boys"
Config: "soapbox-derby-elimination.json"

Age Group Dropdown:
┌─────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Ages 6-8 (4 rounds, ~73 racers) ⭐ Suggested        │ │ ← Pre-selected
│ │ Ages 9-11 (4 rounds, ~62 racers)                   │ │
│ │ Ages 12-14 (3 rounds, ~23 racers)                  │ │
│ │ VIPs (2 rounds, ~15 racers)                        │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘

✓ Auto-detected "Ages 6-8" based on class name pattern

User: Can click Initialize immediately (suggestion accepted)
```

### Example 2: No Pattern Match (Manual Selection Required)

```
Class Name: "Six to Eight Year Olds"
Config: "soapbox-derby-elimination.json"

Age Group Dropdown:
┌─────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Select age group for this class...                  │ │ ← Nothing selected
│ │ Ages 6-8 (4 rounds, ~73 racers)                    │ │
│ │ Ages 9-11 (4 rounds, ~62 racers)                   │ │
│ │ Ages 12-14 (3 rounds, ~23 racers)                  │ │
│ │ VIPs (2 rounds, ~15 racers)                        │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘

⚠ No pattern match found for class "Six to Eight Year Olds".
  Please select manually.

User: Must manually select appropriate age group
```

### Example 3: User Override (Manual Selection)

```
Class Name: "Ages 6-8 VIP Racers"
Config: "soapbox-derby-elimination.json"

Age Group Dropdown:
┌─────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Ages 6-8 (4 rounds, ~73 racers) ⭐ Suggested        │ │ ← Auto-suggested
│ │ Ages 9-11 (4 rounds, ~62 racers)                   │ │
│ │ Ages 12-14 (3 rounds, ~23 racers)                  │ │
│ │ VIPs (2 rounds, ~15 racers)                        │ │ ← User selects this
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘

✓ Auto-detected "Ages 6-8" based on class name pattern

User: Ignores suggestion and manually selects "VIPs" instead
```

## Confirmation Dialog

```
Initialize elimination tournament for this class?

Age Group: Ages 6-8 (4 rounds, ~73 racers) ⭐ Suggested

This will create tournament rounds and cannot be easily undone.

[Cancel] [OK]
```

## Pattern Matching as Helper (Not Blocker)

### Old Way: Pattern = Required

```
if (pattern_matches) {
  ✓ Initialize tournament
} else {
  ❌ FAIL - No match found
}
```

### New Way: Pattern = Suggestion

```
suggested = try_pattern_match(class_name)

if (suggested) {
  → Pre-select suggested age group
  → Show green checkmark: "✓ Auto-detected"
} else {
  → No pre-selection
  → Show orange warning: "⚠ Please select manually"
}

user_selection = await user_picks_from_dropdown()
✓ Initialize tournament with user_selection
```

## Edge Cases Handled

### 1. Multiple Configs with Different Age Groups

```
Config A: Ages 6-8, Ages 9-11, Ages 12-14
Config B: Under 10, Over 10

User switches from Config A to Config B:
→ Age group dropdown updates automatically
→ Shows new options from Config B
```

### 2. Config with Single Age Group

```
Config: "Single Age Group Elimination"
Age Groups: [All Ages]

Age Group Dropdown:
┌─────────────────────────────────────────────────┐
│ All Ages (3 rounds, ~100 racers) ⭐ Suggested   │ ← Only option
└─────────────────────────────────────────────────┘

User: Single option auto-selected, can proceed immediately
```

### 3. Class Name Changes After Tournament Init

```
Scenario: Class renamed after tournament started

Tournament already active:
→ Age group selector not shown (tournament info shown instead)
→ No pattern matching needed (age group stored in database)
→ Class can be renamed without affecting tournament
```

## Database Storage

Age group selection is stored in `EliminationTournaments` table:

```sql
CREATE TABLE EliminationTournaments (
  tournament_id INTEGER PRIMARY KEY,
  classid INTEGER,
  config_file VARCHAR(100),
  age_group_key VARCHAR(50),  -- Explicit selection stored here
  ...
);
```

**Benefits:**
- Tournament remembers which age group was selected
- Class can be renamed without breaking tournament
- No dependency on pattern matching after initialization

## Migration Path

### Existing Tournaments

Existing tournaments continue to work:
```sql
-- Old tournaments (before this feature)
SELECT age_group_key FROM EliminationTournaments WHERE tournament_id = 1;
-- Result: "ages_6_8" (from pattern matching during init)

-- New tournaments (after this feature)
SELECT age_group_key FROM EliminationTournaments WHERE tournament_id = 2;
-- Result: "ages_6_8" (from explicit user selection)

-- Both work identically!
```

### Backward Compatibility

✅ Old tournaments continue working
✅ Pattern matching still available (as fallback)
✅ Configs don't need to be updated
✅ UI shows age group selector for new inits
✅ Existing initialization code path preserved

## Summary

### Before (Pattern Matching Only)

❌ Fragile - breaks with naming variations
❌ Hidden - user doesn't see age group selection
❌ Inflexible - no override capability
❌ Error-prone - regex patterns must be perfect

### After (Explicit Selection with Auto-Suggest)

✅ Robust - works with any class naming
✅ Visible - user sees all available options
✅ Flexible - can override suggestions
✅ Informative - shows rounds and expected racers
✅ Safe - confirmation dialog shows selection
✅ Backward compatible - patterns still work as suggestions

## Pattern Matching: From Requirement to Enhancement

**Philosophy Change:**

**Old:** "If pattern doesn't match, fail"
**New:** "If pattern matches, suggest; if not, let user choose"

This transforms pattern matching from a **blocker** into a **helper**, making the system much more user-friendly and robust!

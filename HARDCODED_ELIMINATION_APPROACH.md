# Hardcoded Elimination Configuration Approach

## Overview

This document analyzes a simpler approach to implementing the triple elimination race format using hardcoded JSON configurations instead of complex UI management. This approach prioritizes predictability and reliability over dynamic configuration.

## Race Format Requirements

### Ages 6-8 (4 Rounds)
- Round 1: Preliminary (~73 racers) - 3 races each = 73 heats, top 27 advance
- Round 2: Quarter Finals (27 racers) - 1 race each = 9 heats, top 9 advance  
- Round 3: Semi-Finals (9 racers) - 1 race each = 3 heats, top 3 advance
- Round 4: Finals (3 racers) - 1 race = 1 heat

### Ages 9-11 (4 Rounds)
- Round 1: Preliminary (~62 racers) - 3 races each = 62 heats, top 27 advance
- Round 2: Quarter Finals (27 racers) - 1 race each = 9 heats, top 9 advance
- Round 3: Semi-Finals (9 racers) - 1 race each = 3 heats, top 3 advance  
- Round 4: Finals (3 racers) - 1 race = 1 heat

### Ages 12-14 (3 Rounds)
- Round 1: Preliminary (~23 racers) - 3 races each = 23 heats, top 9 advance
- Round 2: Semi-Finals (9 racers) - 1 race each = 3 heats, top 3 advance
- Round 3: Finals (3 racers) - 1 race = 1 heat

## Proposed JSON Configuration Approach

### Configuration Structure

```json
{
  "elimination_formats": {
    "ages_6_8": {
      "name": "Ages 6-8 Triple Elimination",
      "expected_racers": 73,
      "rounds": [
        {
          "round_id": 1,
          "name": "Preliminary",
          "races_per_racer": 3,
          "advancement_rule": "top_count",
          "advance_count": 27,
          "scoring": "total_time"
        },
        {
          "round_id": 2, 
          "name": "Quarter Finals",
          "races_per_racer": 1,
          "advancement_rule": "top_count",
          "advance_count": 9,
          "scoring": "best_time"
        },
        {
          "round_id": 3,
          "name": "Semi-Finals", 
          "races_per_racer": 1,
          "advancement_rule": "top_count",
          "advance_count": 3,
          "scoring": "best_time"
        },
        {
          "round_id": 4,
          "name": "Finals",
          "races_per_racer": 1,
          "advancement_rule": "placement",
          "advance_count": 0,
          "scoring": "placement"
        }
      ]
    },
    "ages_9_11": { /* similar structure */ },
    "ages_12_14": { /* similar structure */ }
  }
}
```

NOTE: the age groups are known as race Classes in derbynet and are established when the data is entered. Reference the Import Fake Roster functionality on the setup.php page for example they use Fake Lions, etc. but our races will be age bracketed. Perhaps the JSON structure needs to reference the class id number or something else key to relations other than just a string text of the age bracket. 

### Implementation Strategy

1. **Configuration Loading**: Load JSON config at race initialization
2. **Round Management**: Use config to determine round progression automatically
3. **Schedule Generation**: Generate heats based on round requirements
4. **Advancement Logic**: Apply advancement rules after each round completion
5. **State Persistence**: Save current round/stage in database

## Data Flow Analysis

### Race Initialization
1. Load appropriate age group configuration from JSON
2. Validate actual racer count against expected count
3. Create database entries for all rounds
4. Generate preliminary round schedule

### Round Progression
1. Monitor round completion via existing heat completion logic
2. When round complete, apply advancement rules from config
3. Generate next round schedule automatically
4. Update race state and notify displays

### Advancement Processing
1. Calculate scores based on round scoring rule (total_time vs best_time)
2. Sort racers according to advancement rule
3. Select advancing racers based on advance_count
4. Create next round entries in database

## Key Questions & Assumptions

### Configuration Management
**Q**: Where should JSON configurations be stored?
**A**: Consider `/website/inc/elimination-configs/` directory with separate files per format

**Q**: How should configurations be selected/applied?
**A**: Coordinator selects format during race setup, config applied to racing group

**Q**: What happens if actual racer count differs from expected?
**A**: Need flexible advancement rules (percentages vs fixed counts)
NOTE: no, if someone comes late too bad, if someone doesn't show up then two racers go in the heat instead of three and the missing person is given a DNF (i.e., 99second race time). Partial heats with 1-2 racers are perfectly acceptable - the system prioritizes avoiding consecutive races for the same racer over maintaining 3 racers per heat.

### Round Transitions
**Q**: Should round advancement be automatic or require coordinator approval?
**A**: Assume automatic with coordinator override capability

**Q**: How to handle ties in advancement decisions?
**A**: Need tiebreaker rules in configuration (secondary time, manual selection)
NOTE: timing is precise to 0.001 seconds, tiebreakers will never occur

**Q**: What if a racer drops out mid-tournament?
**A**: Need dropout handling that doesn't break advancement math
NOTE: nope, that racer will simply leave an empty spot and two racers will go down the hill instead of three (or only one racer if the other two drop out). since everything is progressed by timing, it doesn't matter if all lanes are occupied, and its easier to simply assign a DNF than shifting around the schedules last minute. The heat ordering algorithm prioritizes avoiding consecutive races (weight: 1000) over maintaining full heats (weight: 50). 

### Integration with Existing System
**Q**: How does this integrate with DerbyNet's existing round/heat system?
**A**: Leverage existing RacingRound table, add elimination metadata

**Q**: Can we reuse existing scheduling algorithms?
**A**: Preliminary rounds can use rotation scheduling, elimination rounds need bracket-style

**Q**: How to handle lane assignments in elimination rounds?
**A**: Random assignment or seeded by ranking from previous round
NOTE: Reference the Heat Ordering Options in the settings.php page and follow the same algorithms to determine the schedule. Elimination tournaments apply custom weights: avoid_consecutive=1000 (highest priority), group_weighted_cars=300, avoid_same_lane=300, heat_counts=50 (lowest priority). This ensures racers get adequate rest between races even if it means some heats have fewer than 3 racers.

### State Management
**Q**: How to track tournament state across system restarts?
**A**: Store current round, advancement status in database tables

**Q**: What if coordinator needs to modify advancement mid-tournament?
**A**: Need override mechanisms while preserving audit trail
NOTE: coodinator.php page has a button for manual time entry and redoing the heat but are not likely to be used so this won't be a use case to support

**Q**: How to handle manual race reruns or adjustments?
**A**: Recalculate advancement when race results change
NOTE: coodinator can adjust the times of recent races manually

## Likely Change Scenarios

### Configuration Changes
- **Racer count variations**: Actual turnout differs from expected
- **Format modifications**: Race directors want different advancement numbers
- **New age groups**: Additional categories added to event
- **Scoring adjustments**: Different time calculation methods

### Operational Changes  
- **Manual overrides**: Coordinator needs to advance/eliminate specific racers
- **Round reruns**: Technical issues require repeating heats
- **Schedule adjustments**: Time constraints require format compression
- **Dropout handling**: Racers leave mid-tournament

### System Integration Changes
- **Display updates**: Elimination brackets on kiosk displays
- **Award integration**: Final placement feeding into award system
- **Timing integration**: Special timing rules for elimination rounds
- **Reporting needs**: Tournament bracket reports and statistics

## Technical Implementation Considerations

### Database Schema Changes
- Add `elimination_config` table to store active tournament config
- Add `elimination_state` table to track tournament progression
- Extend `RegistrationInfo` with elimination status fields
- Add advancement audit trail table

### PHP Backend Changes
- Create elimination config management functions
- Add round advancement processing logic
- Extend scheduling to handle elimination formats
- Add advancement calculation functions

### Frontend Changes
- Minimal UI for format selection during setup
- Display current tournament state on coordinator page
- Show elimination brackets on appropriate kiosks
- Add manual override controls for edge cases

### API Considerations
- Endpoints for tournament state queries
- Round advancement trigger endpoints
- Configuration validation endpoints
- Tournament bracket data for displays

### DerbyNet Permission System
The elimination tournament features integrate with DerbyNet's existing permission system:

**Available Permissions:**
- `VIEW_RACE_RESULTS_PERMISSION` (1) - View race results by racer
- `VIEW_AWARDS_PERMISSION` (2) - View awards summary  
- `CHECK_IN_RACERS_PERMISSION` (4) - Check in racers
- `REVERT_CHECK_IN_PERMISSION` (8) - Revert check-ins
- `REGISTER_NEW_RACER_PERMISSION` (32) - Register new racers
- `EDIT_RACER_PERMISSION` (64) - Edit racer details, change class/rank
- `ASSIGN_RACER_IMAGE_PERMISSION` (128) - Assign racer photos
- `JUDGING_PERMISSION` (256) - Record judging, assign ad-hoc awards
- `CONTROL_RACE_PERMISSION` (512) - Record heat results, advance heats, assign kiosks
- `PRESENT_AWARDS_PERMISSION` (1024) - Present awards ceremony
- `VIEW_DEVICE_STATUS` (1024) - View device status (shared with awards)
- `EDIT_AWARDS_PERMISSION` (2048) - Edit award configurations
- `TIMER_MESSAGE_PERMISSION` (4096) - Send timer messages
- `PHOTO_UPLOAD_PERMISSION` (8192) - Upload photos
- `SET_UP_PERMISSION` (32768) - Database setup, configuration changes
- `ADMINISTRATION_PERMISSION` (65536) - System administration

**Elimination Tournament Permission Usage:**
- Tournament initialization: `SET_UP_PERMISSION` - Same as racing group setup
- Tournament status queries: `CHECK_IN_RACERS_PERMISSION` - Basic race viewing
- Tournament advancement: `CONTROL_RACE_PERMISSION` - Same as advancing heats
- Configuration management: `SET_UP_PERMISSION` - System configuration level

## Benefits of Hardcoded Approach

1. **Predictability**: Known, tested configurations reduce surprises
2. **Reliability**: Less complex UI means fewer failure points  
3. **Performance**: No dynamic calculation overhead during races
4. **Maintainability**: Configuration changes don't require code changes
5. **Testing**: Easier to validate known tournament formats
6. **Documentation**: JSON serves as clear format specification

## Potential Drawbacks

1. **Flexibility**: Harder to accommodate one-off format changes
2. **Discovery**: New formats require developer intervention
3. **Validation**: Need robust config validation to prevent errors
4. **Migration**: Existing race data may need conversion

## Recommended Next Steps

1. Create detailed JSON schema for elimination configurations
2. Implement configuration loading and validation
3. Create database schema extensions for elimination state
4. Build basic advancement processing logic
5. Test with simulated tournament data
6. Add coordinator interface for format selection
7. Integrate with existing race management workflows
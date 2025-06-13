# DNF (Did Not Finish) Functionality

This document describes the DNF (Did Not Finish) feature added to the DerbyNet race coordinator interface, allowing race coordinators to mark racers as DNF when they cannot complete their race due to equipment failure, injury, or other circumstances.

## Overview

The DNF feature provides a one-click solution for race coordinators to mark racers as "Did Not Finish" during active races. When a racer is marked as DNF, they receive a time of 99.999 seconds, which effectively gives them the maximum possible time while keeping them in the race schedule for proper scoring and progression calculations.

## Implementation Details

### Files Created/Modified

1. **Backend Action Handler**: `website/ajax/action.racer.dnf.inc` (NEW)
   - Handles POST requests to mark racers as DNF
   - Sets racer's time to 99.999 seconds for the specific heat
   - Requires `CONTROL_RACE_PERMISSION` (race coordinator only)
   - Records DNF events for audit trail

2. **Frontend Display**: `website/js/coordinator-poll.js` (MODIFIED)
   - Added "Action" column to current heat racers table
   - DNF buttons appear only for racers without results
   - Added `handleRacerDNF()` JavaScript function
   - Styled DNF buttons with orange color (#ff6b35)

### Database Integration

The DNF functionality integrates seamlessly with DerbyNet's existing database structure:

- **RaceChart Table**: Updates `finishtime` to 99.999 and `finishplace` to 0
- **Event Logging**: Records DNF actions using existing event system
- **Race Progression**: DNF times are treated as valid results for advancement calculations

### Permission Requirements

- **Required Permission**: `CONTROL_RACE_PERMISSION` (512)
- **Default Roles**: Only RaceCoordinator role has this permission
- **Security**: All DNF actions are logged and require explicit confirmation

## User Interface

### Coordinator Page Display

During active races, the coordinator page shows the current heat racers in a table format:

| Lane | Car | Racer | Time | Action |
|------|-----|-------|------|--------|
| 1 | 123 | John Smith | 3.456 | |
| 2 | 456 | Jane Doe | | **[DNF]** |
| 3 | 789 | Bob Wilson | 4.123 | |

### DNF Button Behavior

- **Visibility**: DNF buttons only appear for racers who haven't finished yet (no time recorded)
- **Styling**: Orange background (#ff6b35) with white text for visibility
- **Confirmation**: Clicking DNF shows a confirmation dialog: "Mark this racer as DNF (Did Not Finish)? This will give them a time of 99.999 seconds."
- **Immediate Update**: After confirmation, the display refreshes automatically to show the DNF time

### Visual Feedback

1. **Before DNF**: Button shows "DNF" in orange
2. **After DNF**: Time column shows "99.999" and button disappears
3. **Confirmation**: Clear dialog explaining the 99.999 second assignment
4. **Real-time Update**: Page refreshes via existing polling system

## Technical Specifications

### API Endpoint

**URL**: `POST /action.php`

**Parameters**:
- `action`: `racer.dnf`
- `racerid`: Database ID of the racer to mark as DNF
- `roundid`: Database ID of the current round
- `heat`: Heat number where DNF occurred

**Response**: Standard DerbyNet JSON response with success/failure status

### JavaScript Integration

```javascript
function handleRacerDNF(racerid, roundid, heat) {
  if (confirm('Mark this racer as DNF (Did Not Finish)? This will give them a time of 99.999 seconds.')) {
    $.ajax('action.php', {
      type: 'POST',
      data: {
        action: 'racer.dnf',
        racerid: racerid,
        roundid: roundid,
        heat: heat
      },
      success: function (data) {
        if (data.outcome && data.outcome.code == 'success') {
          coordinator_poll(); // Refresh display
        } else {
          alert('Failed to mark racer as DNF: ' + (data.outcome ? data.outcome.description : 'Unknown error'));
        }
      }
    });
  }
}
```

### Time Value Selection

The DNF time of **99.999 seconds** was chosen because:
- It's clearly distinguishable from normal race times (typically 1-10 seconds)
- It's within the database's time field constraints
- It sorts correctly as the slowest time for standings calculations
- It's easily recognizable by race officials and spectators
- It matches existing DerbyNet conventions (the existing dropout function uses 999.999)

## Usage Scenarios

### Common Use Cases

1. **Equipment Failure**: Car breaks down during race
2. **Safety Issues**: Racer injury or unsafe conditions
3. **Last-Minute Withdrawal**: Racer decides not to participate after staging
4. **Technical Issues**: Lane malfunction affecting specific racer
5. **Rule Violations**: Disqualification during race

### Workflow Integration

1. **Race Start**: Coordinator starts heat normally
2. **Issue Occurs**: Racer cannot complete race for any reason
3. **Mark DNF**: Coordinator clicks DNF button for affected racer
4. **Confirm Action**: System prompts for confirmation with clear explanation
5. **Automatic Update**: Race results show DNF time immediately
6. **Continue Racing**: Heat completion and advancement proceed normally

## Race Progression Impact

### Standings Calculation
- DNF racers receive 99.999 seconds for that heat
- They remain in standings with their DNF time
- Normal advancement rules apply based on overall performance
- DNF times sort as slowest for that heat

### Elimination Tournaments
- DNF racers are automatically eliminated in elimination formats
- Their position is determined by when they received the DNF
- Other racers advance normally based on their actual times

### Multi-Round Races
- DNF only affects the specific heat where it occurred
- Racer can still participate in future heats if scheduled
- Overall standings reflect both completed and DNF heats

## Event Logging and Audit Trail

All DNF actions are logged in DerbyNet's event system:

```
Event Type: EVENT_HEAT_MANUALLY_ENTERED
Details: {
  "roundid": 123,
  "heat": 2,
  "racerid": 456,
  "action": "DNF"
}
```

This provides:
- **Accountability**: Who marked the DNF and when
- **Audit Trail**: Complete record of all race modifications
- **Debugging**: Helps troubleshoot race issues
- **Reporting**: Can be included in race reports

## Error Handling

### Frontend Validation
- Buttons only appear for valid racers
- Confirmation prevents accidental clicks
- Clear error messages for failed operations
- Graceful handling of network issues

### Backend Validation
- Verifies all required parameters present
- Checks user permissions before action
- Validates racer exists in specified heat
- Database transaction ensures data consistency

### Edge Cases
- **Already Finished**: Button doesn't appear if racer already has time
- **Invalid Racer**: Backend validates racer exists in heat
- **Network Issues**: Frontend shows error message and allows retry
- **Permission Denied**: Clear error message for unauthorized users

## Testing and Validation

### Functionality Testing
1. Verify DNF buttons appear only for unfinished racers
2. Confirm permission checking works correctly
3. Test confirmation dialog and cancellation
4. Validate 99.999 time assignment
5. Check real-time display updates

### Integration Testing
1. Verify standings calculations with DNF times
2. Test advancement logic with mixed results
3. Confirm event logging works correctly
4. Validate database consistency after DNF
5. Test with various race formats

### Edge Case Testing
1. Multiple DNFs in same heat
2. DNF in final heat of round
3. Network interruption during DNF
4. Simultaneous coordinator actions
5. DNF with different user permissions

## Future Enhancements

### Potential Improvements
1. **Custom DNF Times**: Allow coordinators to set specific DNF times
2. **DNF Reasons**: Add dropdown for common DNF reasons (equipment, injury, etc.)
3. **Bulk DNF**: Mark multiple racers as DNF simultaneously
4. **DNF Reversal**: Allow coordinators to undo accidental DNF markings
5. **DNF Statistics**: Track and report DNF rates by category/round

### Integration Opportunities
1. **Timer Integration**: Automatic DNF detection from timing hardware
2. **Kiosk Display**: Show DNF status on public displays
3. **Mobile Interface**: DNF functionality for mobile coordinator apps
4. **Reporting**: Include DNF analysis in race reports
5. **Export Functions**: Include DNF data in results exports

## Conclusion

The DNF functionality provides race coordinators with an essential tool for managing unexpected situations during derby races. By integrating seamlessly with DerbyNet's existing architecture and maintaining data consistency, it ensures that races can continue smoothly even when individual racers cannot complete their runs.

The implementation prioritizes:
- **Ease of Use**: One-click operation with clear confirmation
- **Data Integrity**: Proper database updates and event logging
- **Race Continuity**: Minimal disruption to ongoing race operations
- **Flexibility**: Works with all race formats and advancement rules
- **Accountability**: Complete audit trail of all DNF actions

This feature enhances DerbyNet's capability to handle real-world racing scenarios while maintaining the system's reliability and user-friendly design.
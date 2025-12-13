# Heartbeat System Fixes (v0.6.2)

## Issues Fixed

### 1. **Stale Heartbeat Confirmation**
**Problem**: The `confirmed` flag was being set based on whether timers were present in the dictionary, not whether they had recently checked in.

**Fix**: Now only confirms when ALL timers have checked in within the last 5 seconds:
```python
# Only confirm if ALL timers have checked in within the last 5 seconds
all_recent = all(
    (current_time - timer_heartbeats[lane]['time']) <= 5.0 
    for lane in expected_timers
)
```

### 2. **Race Condition in Timer Cleanup**
**Problem**: Timer cleanup was happening inside the heartbeat function, potentially causing race conditions.

**Fix**: Separated cleanup into its own function called at the right time:
```python
def cleanup_offline_timers(self, current_time):
    """Remove timers that haven't sent heartbeats within timeout period"""
    for lane_num in list(self.timer_heartbeats.keys()):
        if (current_time - self.timer_heartbeats[lane_num]['time']) > HEARTBEAT_TIMEOUT:
            logger.warning(f"Timer for lane {lane_num} is offline")
            del self.timer_heartbeats[lane_num]
```

### 3. **Delayed State Transitions**
**Problem**: Race state changes weren't immediately reflected in heartbeats to DerbyNet.

**Fix**: Added force immediate heartbeat on state changes:
```python
if prev_race_state != self.race_state:
    logger.info(f"Race state changed: {prev_race_state} -> {self.race_state}")
    # Force immediate heartbeat when race state changes
    self.force_heartbeat_update()
```

### 4. **Inconsistent Race State Logic**
**Problem**: Race state transitions weren't properly handling transitions back to active after being stopped.

**Fix**: Clearer state logic with proper transition handling:
```python
if raceActive == True:
    if timer_state_string == "Race running":
        self.race_state = "RACING"
    else:
        self.race_state = "STAGING"
        # Only call set_staging if transitioning from a different state
        if prev_race_state in ["FINISHED", "STOPPED", ""]:
            self.api.set_staging()
else:
    self.race_state = "STOPPED"
```

## Timing Improvements

### Heartbeat Frequency
- **From derbyRace**: Every 1 second (responsive)
- **To DerbyNet API**: Every 5 seconds (balanced - not overwhelming)
- **Force immediate**: When timer state changes or reconnects

### Confirmation Logic
- **Confirmed = 1**: All 3 timers present, recent (≤5s), and ready
- **Confirmed = 0**: Any timer missing, stale (>5s), or not ready

## Debug Improvements

### Enhanced Logging
```python
logger.debug(f"Heartbeat: Online={online_timers}, Ready={ready_timers}")
logger.debug(f"Heartbeat confirmation: confirmed={confirmed}, timers={len(timer_heartbeats)}")
logger.info(f"Race state changed: {prev_race_state} -> {self.race_state}")
```

### Better Error Messages
- Timer offline notifications include time since last heartbeat
- Clear distinction between missing vs stale timers
- State transition logging for debugging

## Testing with Debug Mode

To test these fixes with debug console logging:

```bash
# Method 1: Use debug runner
./debug-run.sh derbyRace.py

# Method 2: Set environment variables
export DERBY_CONSOLE_LOG=true DERBY_DEBUG=true
python3 derbyRace.py
```

Debug output will show:
- Heartbeat confirmation decisions
- Timer state changes
- Race state transitions
- API communication results

## Expected Behavior

### Normal Operation
1. Timers send telemetry every ~1 second
2. derbyRace sends heartbeat to DerbyNet every 5 seconds
3. `confirmed=1` only when all timers recent and ready
4. State changes trigger immediate heartbeat updates

### Recovery Scenarios
1. **Timer goes offline**: Removed from heartbeats after 5s, `confirmed=0`
2. **Timer comes back**: Immediate heartbeat sent, logged as "reconnected"
3. **Race inactive -> active**: Proper transition to STAGING, immediate update
4. **Network issues**: Graceful handling with retry logic

This should resolve the "stuck offline status" and "stopped racing" issues by ensuring timely and accurate heartbeat confirmation based on current timer status.
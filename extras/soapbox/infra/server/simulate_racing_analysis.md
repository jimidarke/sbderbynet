# Simulate Racing Script Analysis and Planning

## Objective
Create a Python script `simulate_racing.py` that simulates a complete racing event for testing purposes. The script should mimic the normal race flow as managed by the derbyRace.py system.

## Analysis of Existing Code

### Available Imports from Server Folder
1. **derbyapi.py (DerbyNetClient class)**
   - `login()` - Authenticates with DerbyNet 
   - `get_race_status()` - Gets current race state and heat info
   - `send_start()` - Sends race start signal to DerbyNet
   - `send_finish(roundid, heatid, lane_times)` - Sends finish results
   - `set_staging()` - Sets race state to staging
   - `send_timer_heartbeat(timer_heartbeats)` - Sends heartbeat data

2. **derbynet.py (MQTTClient and other networking)**
   - Enhanced MQTT client with resilient connections
   - DeviceTelemetry class for standardized telemetry

3. **serverlogger.py (ServerLogger class)**
   - Standardized logging with file and syslog handlers
   - Format: `'%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s'`

### derbyRace.py Key Functions to Reference
1. **Race state validation**: 
   - `race_state` property indicates STOPPED, STAGING, RACING, FINISHED
   - LED colors: red=STOPPED, blue=STAGING, green=RACING, purple=finished lane

2. **Key racing functions**:
   - `startRace(timer=None)` - Initializes race, sets state to RACING, green LED
   - `laneFinish(lane, timer=None)` - Records lane finish time, purple LED for that lane
   - `stopRace(timer=None)` - Ends race, sends results to DerbyNet API

3. **Race flow validation**:
   - Must be in STAGING (blue LED) state before starting race
   - Each lane (1, 2, 3) must finish exactly once per heat
   - Race automatically stops when all lanes finish

## Script Requirements Analysis

### Prerequisites
- DerbyNet system must be in STAGING state (blue LED)
- Must validate race status before each startRace call
- Exit script if not in proper state

### Race Simulation Flow
1. **Validate STAGING state** → quit if not ready
2. **Start race** → `startRace()` function
3. **Wait 5-10 seconds** (random)
4. **Lane finish 1** → random lane (1, 2, or 3), `laneFinish(lane)`
5. **Wait 1-5 seconds** (random)
6. **Lane finish 2** → different random lane, `laneFinish(lane)`
7. **Wait 1-5 seconds** (random)
8. **Lane finish 3** → remaining lane, `laneFinish(lane)`
9. **Race auto-stops** when all 3 lanes finish
10. **Wait 5-10 seconds** (random)
11. **Repeat from step 1**

### Technical Implementation Plan

#### Core Classes Needed
- `DerbyNetClient` from derbyapi.py for API communication
- `ServerLogger` from serverlogger.py for consistent logging

#### Key Variables to Track
- `race_state` - Current race state (STAGING, RACING, etc.)
- `lanes_used` - Track which lanes have finished in current heat
- `lane_times` - Dictionary of lane finish times
- `start_time` - Race start timestamp

#### Random Timing Implementation
```python
import random
import time

# Race start delay: 5-10 seconds
start_delay = random.uniform(5, 10)

# Lane finish delays: 1-5 seconds between finishes
finish_delay = random.uniform(1, 5)

# Between-race delay: 5-10 seconds
between_race_delay = random.uniform(5, 10)
```

#### Lane Selection Logic
```python
# Ensure no lane repeats within same heat
available_lanes = [1, 2, 3]
for finish_position in range(3):
    selected_lane = random.choice(available_lanes)
    available_lanes.remove(selected_lane)
    # Call laneFinish(selected_lane)
```

## Questions and Considerations

### 1. State Validation Method
**Question**: How should we validate STAGING state?
**Options**: 
- A) Use `derbyapi.get_race_status()` and check state
- B) Create instance of derbyRace class and check `race_state`
**Recommendation**: Option A - Use API to get race status for independence

### 2. Race Execution Method
**Question**: Should we call derbyRace methods directly or simulate MQTT messages?
**Options**:
- A) Call derbyRace.startRace() and derbyRace.laneFinish() directly
- B) Simulate MQTT messages that would trigger these functions
**Recommendation**: Option A - Direct function calls for simplicity and reliability

### 3. Timing Precision
**Question**: What precision should we use for race times?
**Analysis**: derbyRace.py uses `round(timer - self.start_time, 3)` (3 decimal places)
**Recommendation**: Use time.time() for consistent precision

### 4. Error Handling
**Question**: How should we handle API failures or race state errors?
**Recommendation**: 
- Log errors clearly
- Exit gracefully on critical failures
- Retry API calls with timeout

### 5. Loop Control
**Question**: How should the simulation loop be controlled?
**Options**:
- A) Infinite loop with keyboard interrupt handling
- B) Fixed number of races with parameter
- C) Time-based duration
**Recommendation**: Option A - Infinite loop with proper interrupt handling

## Implementation Dependencies

### Required Imports
```python
import random
import time
import logging
import sys
from derbyapi import DerbyNetClient
from serverlogger import ServerLogger
```

### Required Functions
1. `validate_staging_state()` - Check if system is ready to race
2. `simulate_single_race()` - Execute one complete race simulation
3. `main()` - Main execution loop with error handling

## Risk Assessment

### Low Risk
- Random timing generation
- Lane selection logic
- Basic logging

### Medium Risk
- API communication failures
- Race state synchronization
- Timing precision issues

### High Risk
- Concurrent access to derbyRace instance
- Database/API state corruption during simulation
- Network connectivity issues

## Success Criteria

1. Script successfully validates STAGING state before racing
2. Each simulated race follows proper sequence: start → 3 lane finishes → stop
3. No lane repeats within a single heat
4. Script handles API failures gracefully
5. Logging provides clear race progression visibility
6. Script can be interrupted cleanly with Ctrl+C

## Next Steps

1. Create basic script structure with imports and logging
2. Implement state validation function
3. Create single race simulation function
4. Add main loop with error handling
5. Test with actual DerbyNet system
6. Add command-line parameters for configuration

## File Dependencies Confirmed

All required files are present in `/extras/soapbox/infra/server/`:
- ✅ derbyapi.py - DerbyNetClient class
- ✅ derbynet.py - Network utilities (if needed)
- ✅ serverlogger.py - ServerLogger class
- ✅ derbyRace.py - Reference for function signatures and flow

The script can be created independently and will integrate with the existing system architecture.
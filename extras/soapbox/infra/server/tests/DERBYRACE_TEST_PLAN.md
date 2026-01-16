# derbyRace.py Comprehensive Test Plan

**Version:** 1.0.0
**Date:** 2026-01-15
**Status:** Draft
**Author:** Claude Code Analysis

---

## Executive Summary

`derbyRace.py` is the **crown jewel** of the soapbox derby infrastructure - the central race coordination server that orchestrates all race-day operations. This document provides a comprehensive test plan to ensure enterprise-grade reliability for this mission-critical component.

### Why This Matters

On race day, `derbyRace.py` is responsible for:
- **Timing accuracy**: Sub-millisecond race result recording
- **Hardware coordination**: Managing 3+ finish timers via MQTT
- **State consistency**: Maintaining race state across distributed systems
- **Fault tolerance**: Handling hardware failures, network issues, and edge cases

A failure in `derbyRace.py` during a live event could result in:
- Lost race results (unrecoverable)
- Incorrect standings calculations
- Hardware desynchronization
- Event delays affecting hundreds of participants

### Recent Changes Requiring Validation

Since commit `7d90953f` (cloud testing v1), the following changes have been made but not fully tested:

| Change | Version | Risk Level | Test Priority |
|--------|---------|------------|---------------|
| Direct SQLite DB access | 0.8.2 | HIGH | Critical |
| Thread synchronization locks | 0.8.1 | HIGH | Critical |
| Alert handler integration | 0.8.3 | MEDIUM | High |
| State machine refactoring | 0.8.1 | HIGH | Critical |
| Fallback logic (DB → HTTP) | 0.8.2 | HIGH | Critical |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        derbyRace.py                                  │
│                   (Central Race Coordinator)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │ State Machine│    │ Race Timing  │    │ Alert Handler│           │
│  │              │    │              │    │              │           │
│  │ UNCONFIGURED │    │ start_time   │    │ check_and_   │           │
│  │ STOPPED      │    │ lane_times   │    │ alert()      │           │
│  │ STAGING      │    │ lanesFinished│    │              │           │
│  │ RACING       │    │ lane_count   │    │ derbynet/    │           │
│  │ FINISHED     │    │              │    │ alerts       │           │
│  └──────────────┘    └──────────────┘    └──────────────┘           │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Thread Locks                                │   │
│  │  _race_lock: race_state, lane_times, lanesFinished, start_time│   │
│  │  _heartbeat_lock: timer_heartbeats dictionary                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ MQTT Broker │      │  DerbyDB    │      │  DerbyAPI   │
│             │      │ (SQLite)    │      │ (HTTP)      │
│ telemetry   │      │             │      │             │
│ state       │      │ write_race_ │      │ send_finish │
│ led         │      │ results()   │      │ get_status  │
│ alerts      │      │             │      │ heartbeat   │
└─────────────┘      └─────────────┘      └─────────────┘
         ▲                                       ▲
         │                                       │
┌─────────────┐                         ┌─────────────┐
│ Finish Timer│ ──── ESP32 Devices ──── │ Start Timer │
│ (per lane)  │                         │ (gate)      │
└─────────────┘                         └─────────────┘
```

### Key Interactions

| Component | Protocol | Direction | Purpose |
|-----------|----------|-----------|---------|
| Finish Timers | MQTT | IN | Lane finish events, telemetry |
| Start Timer | MQTT | IN | Race start trigger |
| LEDs | MQTT | OUT | Visual status indicators |
| DerbyDB | SQLite | OUT | Race result persistence |
| DerbyAPI | HTTP | IN/OUT | PHP backend sync |
| AlertHandler | MQTT | OUT | Critical error notifications |

---

## Test Categories

### 1. State Machine Transitions (CRITICAL)

The race state machine has 5 states with specific valid transitions:

```
                    ┌───────────────┐
                    │ UNCONFIGURED  │ (API unavailable)
                    └───────┬───────┘
                            │ API responds
                            ▼
┌─────────┐  NowRacing=ON  ┌─────────┐
│ STOPPED │◄──────────────►│ STAGING │
└─────────┘  NowRacing=OFF └────┬────┘
     ▲                          │ start signal
     │                          ▼
     │                    ┌─────────┐
     │                    │ RACING  │
     │                    └────┬────┘
     │                         │ all lanes finish
     │                         ▼
     │                    ┌─────────┐
     └────────────────────│FINISHED │
                          └─────────┘
```

#### Test Cases: State Transitions

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| SM-001 | UNCONFIGURED → STOPPED | API returns valid response | state=STOPPED, led=red | P0 |
| SM-002 | STOPPED → STAGING | racestats.active=True | state=STAGING, led=blue | P0 |
| SM-003 | STAGING → RACING | startRace() called | state=RACING, led=green | P0 |
| SM-004 | RACING → FINISHED | lanesFinished==lane_count | state=FINISHED, results submitted | P0 |
| SM-005 | FINISHED → STOPPED | racestats.active=False | state=STOPPED, lane data cleared | P0 |
| SM-006 | Race guard active | PHP reports STAGING during race | state stays RACING | P0 |
| SM-007 | State data cleared on STAGING | Stale lane data exists | lanesFinished=0, lane_times={} | P0 |
| SM-008 | State data cleared on STOPPED | Previous race data exists | All race tracking reset | P0 |
| SM-009 | Invalid transition rejected | STOPPED → RACING (skip STAGING) | No state change | P1 |
| SM-010 | API unavailable during race | API timeout | Race continues, results queued | P1 |

### 2. Race Lifecycle (CRITICAL)

Complete race execution from start to finish.

#### Test Cases: Race Start

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| RL-001 | Normal race start | startRace() with staging state | start_time set, state=RACING | P0 |
| RL-002 | Start clears stale data | Previous lane_times exist | lane_times={}, lanesFinished=0 | P0 |
| RL-003 | Start ignored if racing | startRace() while RACING | No state change, warning logged | P0 |
| RL-004 | Start with custom timer | startRace(timer=1234567890.123) | start_time=1234567890.123 | P1 |
| RL-005 | Start publishes MQTT | startRace() | MQTT publish to race/state | P0 |
| RL-006 | Start notifies PHP | startRace() | api.send_start() called | P0 |

#### Test Cases: Lane Finish

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| RL-010 | Single lane finish | laneFinish(1) | lane_times[1] set, lanesFinished=1 | P0 |
| RL-011 | All lanes finish | laneFinish(1,2,3) in sequence | stopRace() called | P0 |
| RL-012 | Duplicate finish ignored | laneFinish(1) twice | Second call returns False | P0 |
| RL-013 | Finish time calculation | laneFinish(1) at start_time+3.456 | lane_times[1]=3.456 | P0 |
| RL-014 | Finish without start_time | laneFinish(1) with start_time=0 | race_time=0.0, warning logged | P1 |
| RL-015 | Concurrent lane finishes | laneFinish(1,2,3) simultaneously | All recorded, no corruption | P0 |
| RL-016 | Lane LED updated on finish | laneFinish(1) | LED for lane 1 → red | P1 |

#### Test Cases: Race Stop

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| RL-020 | Normal race stop | stopRace() with all lanes finished | Results written, state=FINISHED | P0 |
| RL-021 | Stop writes to DB (primary) | stopRace() with db available | db.write_race_results() called | P0 |
| RL-022 | Stop falls back to HTTP | stopRace() with db=None | api.send_finish() called | P0 |
| RL-023 | Stop falls back on DB error | db.write_race_results() throws | api.send_finish() called | P0 |
| RL-024 | Stop resets race state | stopRace() | lanesFinished=0, lane_times={}, start_time=0 | P0 |
| RL-025 | Stop publishes MQTT | stopRace() | MQTT publish to race/state | P0 |

#### Test Cases: DNF Handling

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| RL-030 | Mark lane DNF | laneDNF(1) during racing | lane_times[1]=99.999 | P0 |
| RL-031 | DNF ignored if not racing | laneDNF(1) while STOPPED | Returns False, warning logged | P0 |
| RL-032 | DNF overwrites finish time | laneFinish(1), then laneDNF(1) | lane_times[1]=99.999 | P1 |
| RL-033 | DNF completes race | DNF last unfinished lane | stopRace() called | P0 |
| RL-034 | DNF increments count | laneDNF(1) for new lane | lanesFinished++ | P0 |
| RL-035 | DNF doesn't double-count | laneDNF(1) for finished lane | lanesFinished unchanged | P1 |

#### Test Cases: Race Timeout

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| RL-040 | Timeout marks DNF | Race exceeds RACE_TIMEOUT | Unfinished lanes get DNF | P1 |
| RL-041 | Timeout sends alert | Race timeout occurs | Alert with ERR-RACE-301 | P1 |
| RL-042 | Timeout completes race | All lanes timed out | stopRace() called | P1 |
| RL-043 | No timeout if not racing | checkRaceTimeout() while STOPPED | Returns False | P2 |

### 3. Hardware Integration (HIGH)

MQTT message handling and device coordination.

#### Test Cases: MQTT Message Parsing

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| HW-001 | Parse state message GO | {"state": "GO", "dip": "1000"} | startRace() called | P0 |
| HW-002 | Parse finish toggle | {"toggle": false, "dip": "1000"} | laneFinish(1) called | P0 |
| HW-003 | Parse telemetry | {"hostname": "...", "hwid": "..."} | timerHeartbeat() called | P0 |
| HW-004 | Ignore finish if not racing | Toggle message while STOPPED | No laneFinish() call | P0 |
| HW-005 | Invalid JSON rejected | Malformed payload | Error logged, no crash | P1 |
| HW-006 | Missing required fields | {"hostname": "..."} only | Warning logged | P2 |

#### Test Cases: DIP Switch Mapping

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| HW-010 | DIP 1000 → Lane 1 | getDIPName("1000") | Returns 1 | P0 |
| HW-011 | DIP 1001 → Lane 2 | getDIPName("1001") | Returns 2 | P0 |
| HW-012 | DIP 1010 → Lane 3 | getDIPName("1010") | Returns 3 | P0 |
| HW-013 | DIP 1011 → Lane 4 | getDIPName("1011") | Returns 4 | P0 |
| HW-014 | Unknown DIP → 0 | getDIPName("0000") | Returns 0 | P1 |

#### Test Cases: LED Control

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| HW-020 | Update all LEDs | updateLED("green", "all") | MQTT to all lane topics | P0 |
| HW-021 | Update single LED | updateLED("red", 1) | MQTT to lane/1/led only | P0 |
| HW-022 | LED color on staging | setLEDFromRaceStat() with staging | All LEDs → blue | P0 |
| HW-023 | LED color on racing | setLEDFromRaceStat() with racing | All LEDs → green | P0 |
| HW-024 | LED color on stopped | setLEDFromRaceStat() with stopped | All LEDs → red | P0 |

#### Test Cases: Timer Heartbeat

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| HW-030 | Heartbeat updates timestamp | timerHeartbeat(1, True) | timer_heartbeats[1] updated | P0 |
| HW-031 | First heartbeat logs online | timerHeartbeat(1) first time | "Timer online" logged | P1 |
| HW-032 | Ready state change logged | timerHeartbeat(1, True→False) | Ready state change logged | P1 |
| HW-033 | Offline timer cleanup | No heartbeat for 3+ seconds | Timer removed from dict | P0 |
| HW-034 | Offline timer alert | Timer goes offline | Alert with ERR-HW-301 | P0 |
| HW-035 | Heartbeat sent to API | timerHeartbeat() | api.send_timer_heartbeat() | P0 |

### 4. Thread Safety (CRITICAL)

Concurrent access protection.

#### Test Cases: Race Lock

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| TS-001 | Concurrent laneFinish() | 3 threads calling laneFinish() | Each lane recorded once | P0 |
| TS-002 | laneFinish() during stopRace() | Concurrent finish and stop | No data corruption | P0 |
| TS-003 | startRace() clears atomically | Observer thread watching state | Never sees partial clear | P0 |
| TS-004 | stopRace() collects atomically | Observer thread during stop | Gets complete lane_times | P0 |
| TS-005 | State transition atomic | Multiple threads transitioning | Valid state at all times | P0 |

#### Test Cases: Heartbeat Lock

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| TS-010 | Concurrent heartbeat updates | 4 timers updating simultaneously | All heartbeats recorded | P0 |
| TS-011 | Cleanup during update | Cleanup and update concurrent | No KeyError exceptions | P0 |
| TS-012 | Heartbeat copy for API | send_heartbeat_to_api() | Safe copy, no mutation | P1 |

### 5. Error Handling & Alerts (HIGH)

Fault tolerance and alerting.

#### Test Cases: Alert Handler

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| AL-001 | Alert on MQTT disconnect | on_disconnect() with rc!=0 | ERR-NET-301 alert sent | P0 |
| AL-002 | Alert on timer offline | Timer heartbeat timeout | ERR-HW-301 alert sent | P0 |
| AL-003 | Alert on race timeout | Race exceeds RACE_TIMEOUT | ERR-RACE-301 alert sent | P1 |
| AL-004 | No alert if handler unavailable | send_alert() with handler=None | No crash, warning logged | P1 |
| AL-005 | Alert handler exception caught | AlertHandler.check_and_alert() throws | Warning logged, continues | P2 |

#### Test Cases: Database Fallback

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| DB-001 | DB unavailable at init | DERBYNET_DB_PATH not set | db=None, HTTP fallback | P0 |
| DB-002 | DB file not found | DERBYNET_DB_PATH invalid | db=None, warning logged | P0 |
| DB-003 | DB write success | db.write_race_results() returns True | No HTTP call | P0 |
| DB-004 | DB write failure | db.write_race_results() returns False | HTTP fallback called | P0 |
| DB-005 | DB write exception | db.write_race_results() throws | HTTP fallback called | P0 |

#### Test Cases: API Polling

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| AP-001 | API returns None | get_race_status() returns None | State → UNCONFIGURED | P0 |
| AP-002 | API returns non-dict | get_race_status() returns string | State → UNCONFIGURED | P0 |
| AP-003 | DNF detected from API | API shows finishtime=99.999 | laneDNF() called | P0 |
| AP-004 | Lane count updated | lanes array has 4 entries | lane_count = 4 | P1 |

### 6. Edge Cases & Regression Tests

| ID | Test Case | Input | Expected | Priority |
|----|-----------|-------|----------|----------|
| EC-001 | Race integrity: Python racing, PHP not | race_state=RACING, api.active=False | Warning logged, race continues | P1 |
| EC-002 | Race integrity: Heat mismatch | roundid mismatch during race | Warning logged | P2 |
| EC-003 | Reconnection after MQTT disconnect | on_disconnect() then reconnect | connect_with_retry() scheduled | P1 |
| EC-004 | Stale data cleanup on staging | Old race data, enter staging | All tracking state cleared | P0 |
| EC-005 | Stale data cleanup on stopped | Old race data, enter stopped | All tracking state cleared | P0 |
| EC-006 | Version reporting | sendServerTelemetry() | VERSION in payload | P2 |

---

## Test Implementation Files

### File Structure

```
tests/
├── test_derbyRace_threading.py     # Existing - Thread safety (532 lines)
├── test_derbyRace_statemachine.py  # NEW - State transitions
├── test_derbyRace_lifecycle.py     # NEW - Race start/finish/DNF
├── test_derbyRace_hardware.py      # NEW - MQTT, DIP, LED, heartbeat
├── test_derbyRace_alerts.py        # NEW - Alert handler integration
└── test_derbyRace_integration.py   # NEW - End-to-end scenarios
```

### Test Dependencies

```python
# Required mocks for isolation
- MockMQTTClient         # MQTT broker simulation
- MockDerbyNetClient     # HTTP API simulation
- MockDerbyDatabase      # SQLite simulation
- MockAlertHandler       # Alert system simulation
- MockServerLogger       # Logging simulation

# Required fixtures
- derby_race_instance    # Fully mocked derbyRace instance
- populated_db           # Database with test data
- mock_mqtt              # MQTT client patch
- mock_api               # API client patch
```

---

## Test Metrics & Coverage Goals

### Coverage Targets

| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| Line coverage | ~30% | 85% | P0 |
| Branch coverage | ~25% | 75% | P1 |
| Method coverage | ~40% | 95% | P0 |
| State transitions | 20% | 100% | P0 |

### Critical Paths (Must Have 100% Coverage)

1. `startRace()` → `laneFinish()` → `stopRace()` flow
2. State machine transitions
3. Database write with fallback
4. Thread lock acquisition and release
5. Alert triggering conditions

### Test Execution Time Targets

| Test Suite | Max Duration | Notes |
|------------|--------------|-------|
| State machine | 2s | Fast unit tests |
| Lifecycle | 5s | Some timing tests |
| Hardware | 3s | MQTT mocking |
| Threading | 10s | Concurrent stress tests |
| Integration | 30s | Full scenarios |

---

## Implementation Priority

### Phase 1: Critical Path (Week 1)
1. `test_derbyRace_statemachine.py` - All SM-* tests
2. `test_derbyRace_lifecycle.py` - RL-001 through RL-035
3. DB fallback tests (DB-001 through DB-005)

### Phase 2: Hardware Integration (Week 2)
1. `test_derbyRace_hardware.py` - All HW-* tests
2. Alert handler tests (AL-001 through AL-005)

### Phase 3: Edge Cases & Integration (Week 3)
1. `test_derbyRace_integration.py` - Full race scenarios
2. Edge case tests (EC-001 through EC-006)
3. Performance/stress tests

---

## Verification Checklist

Before marking complete, verify:

- [ ] All P0 tests passing
- [ ] Line coverage > 85%
- [ ] No race conditions in threading tests
- [ ] All state transitions covered
- [ ] Database fallback logic verified
- [ ] Alert triggering verified
- [ ] Integration with existing 216 tests maintained

---

## Appendix: Code Diff Analysis

### Changes Since Last Commit (7d90953f)

**New Imports:**
- `derbydb.DerbyDatabase` (conditional)
- `alerthandler.AlertHandler` (conditional)

**New Instance Variables:**
- `self._race_lock` - threading.Lock
- `self._heartbeat_lock` - threading.Lock
- `self.db` - DerbyDatabase or None
- `self.alert_handler` - AlertHandler or None

**Modified Methods:**
- `__init__()` - Added lock initialization, DB init, alert handler init
- `on_disconnect()` - Added alert sending
- `setLEDFromRaceStat()` - Refactored with lock, flag-based external calls
- `startRace()` - Added lock, atomic state clearing
- `stopRace()` - Added lock, DB write with fallback
- `laneFinish()` - Added lock, atomic check-and-modify
- `laneDNF()` - Added lock, atomic state updates
- `checkRaceTimeout()` - Added alert sending
- `timerHeartbeat()` - Added lock, refactored
- `cleanup_offline_timers()` - Added lock, alert sending
- `send_heartbeat_to_api()` - Added lock for safe copy

**New Methods:**
- `send_alert()` - Alert handler wrapper

---

*Document generated by Claude Code analysis of derbyRace.py v0.8.3*

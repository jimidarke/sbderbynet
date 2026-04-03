# SBDerbyNet Enterprise Roadmap

**Version:** 1.0 | **Assessment Date:** 2026-01-14 | **Current Version:** 1.0.0

**Domain:** `soapboxderbynet.com` (acquired)

This document provides a comprehensive enterprise readiness assessment and commercialization roadmap for SBDerbyNet, a soapbox derby race management system supporting ~200 racers annually with plans to scale as a cloud service.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Target Architecture](#2-target-architecture)
3. [Current State Assessment](#3-current-state-assessment)
4. [Dead Code & Cleanup Items](#4-dead-code--cleanup-items)
5. [Documentation Status](#5-documentation-status)
6. [Test Coverage Analysis](#6-test-coverage-analysis)
7. [Validated Functionality Matrix](#7-validated-functionality-matrix)
8. [Critical Abstraction Gaps](#8-critical-abstraction-gaps)
9. [Prioritized Implementation Roadmap](#9-prioritized-implementation-roadmap)
10. [White-Label Architecture](#10-white-label-architecture)
11. [Two-System Architecture: Registration vs Users](#11-two-system-architecture-registration-vs-users)
12. [Hybrid Deployment Model](#12-hybrid-deployment-model)

---

## 1. Executive Summary

### Assessment Results

| Category | Score | Status |
|----------|-------|--------|
| Overall Maturity | 2.5/5 | Functional single-site, needs work for multi-tenant |
| Code Quality | 3/5 | Good structure, some cleanup needed |
| Test Coverage | 3/5 | Strong integration tests, Python unit tests in progress |
| Documentation | 4/5 | Comprehensive, minor gaps |
| API Abstraction | 2/5 | Significant work needed |
| Production Readiness | 3/5 | Stable for current use case |

### Key Findings

**Strengths:**
- Robust elimination tournament system with JSON configuration
- Comprehensive PHP integration test suite (36 tests)
- Well-documented MQTT messaging architecture
- Professional kiosk display system
- Solid hardware abstraction for timers

**Critical Issues:**
- Hardcoded IP addresses prevent multi-site deployment (RESOLVED - env vars added)
- ~~Python services have zero unit test coverage~~ (RESOLVED - 72 tests passing)
- PHP/Python state synchronization risks (RESOLVED - threading locks, integrity checks)
- Inconsistent error handling patterns
- ~~Race conditions in lane finish timing~~ (RESOLVED - `_race_lock` protection)

### Priority Order (Per Stakeholder Direction)

1. **Stability** - Cleanup and state synchronization
2. **Testing** - Comprehensive test coverage
3. **Scalability** - API abstraction and configuration

---

## 2. Target Architecture

### Deployment Model: Hybrid Cloud + On-Premise

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLOUD LAYER                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │ Mobile App  │  │ Parent/     │  │   Admin     │               │
│  │   (iOS/     │  │ Public      │  │   Portal    │               │
│  │  Android)   │  │ Portal      │  │             │               │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │
│         │                │                │                       │
│         └────────────────┼────────────────┘                       │
│                          ▼                                        │
│              ┌───────────────────────┐                           │
│              │     API Gateway       │                           │
│              │   (Authentication,    │                           │
│              │    Rate Limiting)     │                           │
│              └───────────┬───────────┘                           │
│                          ▼                                        │
│              ┌───────────────────────┐                           │
│              │   Cloud Database      │                           │
│              │   (Multi-tenant)      │                           │
│              └───────────────────────┘                           │
└──────────────────────────┬───────────────────────────────────────┘
                           │ Sync (when online)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    ON-PREMISE LAYER (Raspberry Pi)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │   DerbyNet  │  │  Race       │  │   MQTT      │               │
│  │   Web App   │  │  Server     │  │   Broker    │               │
│  │   (PHP)     │  │  (Python)   │  │ (Mosquitto) │               │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │
│         │                │                │                       │
│         └────────────────┼────────────────┘                       │
│                          │ MQTT                                   │
│         ┌────────────────┼────────────────┐                       │
│         ▼                ▼                ▼                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │   Finish    │  │   Start     │  │   Display   │               │
│  │   Timer     │  │   Timer     │  │   Kiosks    │               │
│  └─────────────┘  └─────────────┘  └─────────────┘               │
└──────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Offline-First**: On-premise system must operate independently
2. **Sync-When-Available**: Cloud sync for mobile app and analytics
3. **White-Label Ready**: Runtime-configurable branding and content
4. **Single Source of Truth**: Event sourcing for state management

---

## 3. Current State Assessment

### System Components

| Component | Technology | Location | Lines of Code | Status |
|-----------|------------|----------|---------------|--------|
| Web Application | PHP 7.4+ | `/website/` | ~50,000 | Production |
| Action Endpoints | PHP | `/website/ajax/` | 133 files | Production |
| Include Libraries | PHP | `/website/inc/` | 119 files | Production |
| Race Server | Python 3.7+ | `/extras/soapbox/infra/server/` | ~3,500 | Production |
| Finish Timer | Python/RPi | `/extras/soapbox/infra/finishtimer/` | ~1,500 | Production |
| Start Timer | MicroPython | `/extras/soapbox/infra/starttimer/` | ~300 | Production |
| Display Client | Python | `/extras/soapbox/infra/derbydisplay/` | ~500 | Production |
| Video Streaming | FFmpeg/Nginx | `/extras/soapbox/hlsfeed/` | ~800 | Production |
| LED Sign Controller | MicroPython/ESP32 | `/extras/ledsign/` | ~2,500 | Development |

### Communication Protocols

| Interface | Protocol | Format | QoS |
|-----------|----------|--------|-----|
| Browser ↔ PHP | HTTP/AJAX | JSON/XML | N/A |
| PHP ↔ Database | PDO | SQL | N/A |
| Python ↔ MQTT | MQTT 3.1.1 | JSON | 0-2 |
| Timer ↔ Server | MQTT | JSON | 2 |
| PHP ↔ Hardware | HTTP | JSON | N/A |

**Issue:** PHP communicates with hardware via HTTP while Python uses MQTT, creating dual pathways.

---

## 4. Dead Code & Cleanup Items

### Status: CLEANUP COMPLETED (2026-01-14)

All identified dead code has been removed. See Phase 1.1 in Section 9 for details.

### ~~Priority 1: Safe to Remove (74KB)~~ - DONE

~~These files are dated backups with no references in the codebase:~~

| File | Size | Status |
|------|------|--------|
| ~~`website/inc/form_groups_by_rule-backup-18-04-2025.inc`~~ | 3.4KB | **DELETED** |
| ~~`website/inc/rounds-backup-18-04-2025.inc`~~ | 8.4KB | **DELETED** |
| ~~`website/inc/racing-state-backup-(tripple-elimination)).inc`~~ | 16KB | **DELETED** |
| ~~`website/inc/racing-state-backup-(tripple-elimination)-18-04-2025-06-53-PM.inc`~~ | 17KB | **DELETED** |
| ~~`website/ajax/action.schedule.generate-backup-16-04-2025.inc`~~ | 4.8KB | **DELETED** |

### ~~Priority 2: Consolidate or Remove~~ - DONE

| File | Issue | Status |
|------|-------|--------|
| ~~`website/inc/schedule_orderedddd.inc`~~ | 134 lines commented code, duplicate | **DELETED** (orphaned) |
| `website/inc/data-backup-copy.inc` | 19KB backup functionality | Deferred - may be needed |

### ~~Priority 3: Review Before Removing~~ - DONE

| File | Issue | Status |
|------|-------|--------|
| ~~`website/inc/util.inc`~~ | Never included anywhere | **DELETED** |
| ~~`website/inc/current-racers.inc`~~ | Replaced by `json-current-racers.inc` | **DELETED** |

### Priority 4: TODO Comments (Backlog)

Remaining TODO comments are documentation notes, not dead code. Retained as tech debt backlog:

| File | TODO Description | Priority |
|------|-----------------|----------|
| `website/js/awards-editor.js` | "Ordering in the face of speed trophies?" | Low |
| `website/js/awards-editor.js` | "Poll on this, not just this one time" | Low |
| `website/js/coordinator-controls.js` | "Show place instead of time" | Low |
| `website/js/coordinator-controls.js` | "Risk of form conflicts" | Medium |
| `website/js/coordinator-poll.js` | "Single roundid master scheduling" | Low |
| `website/js/checkin.js` | Finding racer logic | Low |
| `website/js/circular-frame-buffer.js` | `offscreen_video.remove()` | Low |
| `website/js/award-presentations-kiosk.js` | "Literal 10 vaguely accounts for margins" | Low |

**Note:** Commented-out code lines with TODO markers were removed during cleanup.

---

## 5. Documentation Status

### Active Documentation (23 files)

| Document | Location | Status | Quality |
|----------|----------|--------|---------|
| README.md | `/` | Current | Excellent |
| CLAUDE.md | `/` | Current | Good |
| CONTRIBUTING.md | `/` | Current | Good |
| RACINGSTATEENGINE.md | `/` | Current | Excellent |
| ROUNDSETUP.md | `/` | Current | Good |
| DATABASE_SCHEMA_VALIDATION.md | `/` | Current | Good |
| ELIMINATION_CONFIG_VALIDATION.md | `/` | Current | Good |
| SFTP_ACCESS.md | `/SECURE/` | Current | Good |
| COORDINATOR_POLL_API.md | `/docs/` | Current | Excellent |
| Server README | `/extras/soapbox/infra/server/` | Current | Good |
| RASPBERRY_PI_SETUP.md | `/extras/soapbox/infra/server/` | Current | Excellent |
| Finish Timer README | `/extras/soapbox/infra/finishtimer/` | Current | Good |
| Start Timer README | `/extras/soapbox/infra/starttimer/` | Current | Good |
| Display README | `/extras/soapbox/infra/derbydisplay/` | Current | Good |
| HLS Feed README | `/extras/soapbox/hlsfeed/` | Current | Good |
| DERBYNET_REFERENCE.md | `/extras/soapbox/doc/` | Current | Excellent |
| MQTT_API.md | `/extras/soapbox/doc/` | Current | Good |
| Elimination Config README | `/website/inc/elimination-configs/` | Current | Excellent |

### Archived Documentation (6 files - Consider Cleanup)

| Document | Location | Status |
|----------|----------|--------|
| AGE_GROUP_SELECTION_UX.md | `/docs/archive/` | Superseded |
| FIELD_MAPPING_DIAGRAM.md | `/docs/archive/` | Superseded |
| HEARTBEAT_FIXES.md | `/docs/archive/` | Superseded |
| SCHEMA_UPDATE_STATUS.md | `/docs/archive/` | Superseded |
| SCHEMA_VALIDATION_SUMMARY.md | `/docs/archive/` | Superseded |
| simulate_racing_analysis.md | `/docs/archive/` | Superseded |

**Action:** Add `ARCHIVE_README.md` explaining these are historical and which current docs supersede them.

### Documentation Gaps

1. **Missing:** API versioning strategy
2. **Missing:** Multi-tenant architecture guide
3. **Missing:** Cloud deployment runbook
4. **Missing:** White-label configuration guide
5. **Missing:** Disaster recovery procedures

---

## 6. Test Coverage Analysis

### Current Test Infrastructure

| Test Type | Count | Coverage | Location |
|-----------|-------|----------|----------|
| Shell Integration Tests | 36 | 70-80% PHP | `/testing/test-*.sh` |
| Puppeteer Browser Tests | 6 | Coordinator UI | `/testing/puppeteer/` |
| Python Tournament Tests | 1 | Elimination only | `/website/test_elimination_tournaments.py` |
| Python Unit Tests | 386 | derbydb, derbyRace (state machine, lifecycle, hardware), threading, schema, config, logging, error_codes, derbyapi, derbynet, device protocols, finishtimer resilience, correlation IDs, log sync, performance timing | `/extras/soapbox/infra/server/tests/` |
| Security Tests | 0 | **None** | N/A |
| Load/Performance Tests | 10 | Race timing latency | `/extras/soapbox/infra/server/tests/test_performance_timing.py` |

### Test Utilities Available

| File | Purpose |
|------|---------|
| `/testing/common.sh` | Shared test functions (curl, assertions) |
| `/testing/action` | POST action helper |
| `/testing/query` | GET query helper |
| `/testing/actionj`, `/testing/queryj` | JSON API testing |
| `/testing/setup-basic.sh` | Demo environment setup |
| `/testing/reset-database.sh` | Test data cleanup |

### Test Data Fixtures

| Type | Count | Location |
|------|-------|----------|
| Roster CSVs | 11 | `/testing/data/` |
| Headshot Images | 65+ | `/testing/data/headshots/` |
| Car Photos | 100+ | `/testing/data/carphotos/` |
| Awards Data | Various | `/testing/data/` |

### Critical Test Gaps

| Component | Risk Level | Estimated Effort | Status |
|-----------|------------|------------------|--------|
| `derbyRace.py` (34KB) | LOW | - | **Complete** (84 tests) - state machine, lifecycle, hardware, threading, DB fallback |
| `derbydb.py` (10KB) | LOW | - | **Complete** (31 tests) |
| `derbyapi.py` (21KB) | LOW | - | **Complete** (31 tests) |
| `derbynet.py` (16KB) | LOW | - | **Complete** (27 tests) |
| Device protocols | LOW | - | **Complete** (32 tests) - finish timer, start timer, display |
| Device error logging | LOW | - | **Complete** (32 tests) - battery, WiFi, CPU temp, offline |
| `finishtimer.py` | LOW | - | **Complete** (27 resilience tests) - MessageQueue persistence, offline operation, recovery scenarios, concurrent operations |
| Security/penetration | HIGH | 30-40 hours | No tests |
| Load testing (500+ racers) | MEDIUM | 20-30 hours | No tests |

---

## 7. Validated Functionality Matrix

### Core Race Management

| ID | Function | Endpoint | Test Script | Status |
|----|----------|----------|-------------|--------|
| RM-01 | Racer Registration | `action.racer.add` | `test-basic-checkins.sh` | Validated |
| RM-02 | Racer Check-in | `action.racer.checkin` | `test-basic-checkins.sh` | Validated |
| RM-03 | Heat Scheduling | `action.schedule.generate` | `test-extended-scheduling.sh` | Validated |
| RM-04 | Result Recording | `action.result.write` | `test-basic-racing.sh` | Validated |
| RM-05 | Manual Result Entry | `action.result.write` | `test-basic-racing.sh` | Validated |
| RM-06 | Heat Rerun | `action.heat.rerun` | `test-basic-racing.sh` | Validated |
| RM-07 | Timer Communication | `action.timer-message` | `test-basic-racing.sh` | Validated |
| RM-08 | Device Status API | `/device-status-api.php` | Manual | Partial |

### Elimination Tournament System

| ID | Function | Endpoint | Test Script | Status |
|----|----------|----------|-------------|--------|
| ET-01 | Tournament Initialize | `action.elimination.tournament.initialize` | `test_elimination_tournaments.py` | Validated |
| ET-02 | Round Advancement | `action.elimination.tournament.advance` | `test_elimination_tournaments.py` | Validated |
| ET-03 | Config List | `query.elimination.config.list` | `test_elimination_tournaments.py` | Validated |
| ET-04 | Config Detail | `query.elimination.config.detail` | `test_elimination_tournaments.py` | Validated |
| ET-05 | Tournament Status | `query.elimination.tournament.status` | `test_elimination_tournaments.py` | Validated |
| ET-06 | Batch Status | `query.elimination.tournament.all-status` | `test_elimination_tournaments.py` | Validated |
| ET-07 | Config Editor | `/elimination-config-editor.php` | Puppeteer | Validated |

### Award Management

| ID | Function | Endpoint | Test Script | Status |
|----|----------|----------|-------------|--------|
| AW-01 | Award Creation | `action.award.add` | `test-awards.sh` | Validated |
| AW-02 | Award Editing | `action.award.edit` | `test-awards.sh` | Validated |
| AW-03 | Winner Assignment | `action.award.winner` | `test-awards.sh` | Validated |
| AW-04 | Award Presentation | `action.award.present` | `test-awards.sh` | Validated |
| AW-05 | Award Import | `action.award.import` | `test-awards.sh` | Validated |

### Kiosk Display System

| ID | Function | Kiosk File | Test Script | Status |
|----|----------|------------|-------------|--------|
| KS-01 | Now Racing | `now-racing.kiosk` | `test-visit-each-page.sh` | Validated |
| KS-02 | On Deck | `ondeck.kiosk` | `test-visit-each-page.sh` | Validated |
| KS-03 | Standings | `standings.kiosk` | `test-visit-each-page.sh` | Validated |
| KS-04 | Elimination Standings | `elimination-standings.kiosk` | Manual | Validated |
| KS-05 | Elimination Results | `elimination-results.kiosk` | Manual | Validated |
| KS-06 | Video Stream | `hls-video-stream.kiosk` | Manual | Partial |
| KS-07 | Broadcast Messages | `action.broadcast.message` | `test-messaging.sh` | Validated |

### Hardware Integration

| ID | Function | Component | Test Method | Status |
|----|----------|-----------|-------------|--------|
| HW-01 | Finish Detection | `finishtimer.py` | Manual/Simulation | Validated |
| HW-02 | Start Detection | `starttimer/main.py` | Manual | Validated |
| HW-03 | LED Control | MQTT `derbynet/lane/*/led` | Manual | Validated |
| HW-04 | Pinny Display | MQTT `derbynet/lane/*/pinny` | Manual | Validated |
| HW-05 | Device Telemetry | MQTT `derbynet/device/*/telemetry` | Manual | Validated |
| HW-06 | OTA Updates | MQTT `derbynet/device/*/update` | Manual | Partial |
| HW-07 | LED Sign Display | MQTT `derbynet/ledsign/*/message` | Unit Tests (176) | Development |
| HW-08 | LED Sign Broadcast | MQTT `derbynet/ledsign/broadcast` | Unit Tests | Development |
| HW-09 | LED Sign Discovery | MQTT `derbynet/ledsign/device/*/identity` | Unit Tests | Development |

### User Authentication & Authorization

| ID | Function | Endpoint | Test Script | Status |
|----|----------|----------|-------------|--------|
| UA-01 | Role Login | `action.role.login` | `test-permissions.sh` | Validated |
| UA-02 | Permission Check | Multiple | `test-permissions.sh` | Validated |
| UA-03 | Coordinator Role | Multiple | `test-each-role.sh` | Validated |
| UA-04 | Timer Role | `action.timer-message` | `test-each-role.sh` | Validated |

---

## 8. Critical Abstraction Gaps

### Gap 1: Hardcoded IP Addresses (BLOCKING for Multi-Site)

| File | Line | Hardcoded Value |
|------|------|-----------------|
| `extras/soapbox/infra/server/derbyapi.py` | 5 | `192.168.100.10` |
| `extras/soapbox/infra/finishtimer/files/finishtimer.py` | 52 | `192.168.100.10:1883` |
| `extras/soapbox/infra/finishtimer/files/derbynet.py` | 41 | `192.168.100.10` |
| `extras/soapbox/infra/derbydisplay/derbydisplay.py` | 39 | `192.168.100.10` |
| `extras/soapbox/infra/server/derbylogger.py` | 63 | `192.168.100.10` |
| `extras/soapbox/infra/starttimer/src/main.py` | 37, 109 | `192.168.100.10` |
| `extras/soapbox/infra/server/derbyTime.py` | 29 | `127.0.0.1` |
| `extras/soapbox/infra/server/derbyRace.py` | 49 | `localhost` |

**Resolution:**
1. Create `config.yaml` schema for all network configuration
2. Environment variable fallbacks: `MQTT_BROKER`, `DERBYNET_HOST`, `RSYSLOG_IP`
3. Service discovery via mDNS (`_derbynet._tcp.local.`)
4. Docker Compose environment profiles

### Gap 2: Dual Communication Protocols

**Current State:**
- PHP → Hardware: Direct HTTP calls
- Python → Hardware: MQTT pub/sub

**Impact:** Cannot guarantee message delivery consistency, race conditions possible.

**Resolution:**
1. PHP publishes to MQTT for hardware commands
2. PHP subscribes to MQTT for hardware status (or polls via Python API)
3. Single message bus for all hardware communication

### Gap 3: Split State Management

**PHP State:**
- `RaceInfo` database table
- Session variables
- Action response data

**Python State:**
- `derbyRace.py` in-memory variables
- MQTT topic `derbynet/race/state`
- No persistence

**Impact:** PHP and Python can have different views of race state.

**Resolution:**
1. Implement event sourcing pattern
2. Race state changes as events stored in database
3. Both PHP and Python read from same event stream
4. MQTT for real-time notifications only (not source of truth)

### Gap 4: Inconsistent Error Handling

| Pattern | Location | Format |
|---------|----------|--------|
| JSON success/failure | `action.php`, most actions | `{"outcome": {"summary": "success"}}` |
| XML response | Timer protocol | `<success/>` or `<failure code="">` |
| HTTP status codes | `device-status-api.php` | 401, 405, 500 |
| Silent failures | `data.inc` | Returns default value |

**Resolution:**
1. Standardize on JSON for all responses
2. Implement RFC 7807 Problem Details format
3. Consistent HTTP status codes
4. Remove XML response format (breaking change acceptable)

### Gap 5: Race Conditions in Python

**Location:** `extras/soapbox/infra/server/derbyRace.py:142-160`

```python
if lane not in self.lane_times:  # Check
    self.lane_times[lane] = race_time  # Then set
```

**Impact:** Concurrent MQTT messages could corrupt lane timing data.

**Resolution:**
1. Add `threading.Lock()` for all shared state
2. Use atomic operations where possible
3. Implement proper transaction handling

---

## 9. Prioritized Implementation Roadmap

### Phase 1: Stability (Priority: HIGHEST)

**Goal:** Ensure reliable operation for June race event

**Duration:** 2-3 weeks

**Status:** 1.1, 1.2, 1.4 Complete, 1.3 Pending

#### 1.1 Dead Code Cleanup - COMPLETED (2026-01-14)

- [x] Delete 5 dated backup files (74KB)
- [x] Consolidate `schedule_ordered*.inc` files (deleted orphaned `schedule_orderedddd.inc`)
- [x] Review and resolve `util.inc` and `current-racers.inc` (both deleted - orphaned)
- [x] Add `ARCHIVE_README.md` to `/docs/archive/`
- [x] Clean ~120 lines of commented legacy code from `schedule_ordered.inc`
- [x] Clean commented-out code from 6 JavaScript files

**Files Removed:**
| File | Size | Reason |
|------|------|--------|
| `website/inc/form_groups_by_rule-backup-18-04-2025.inc` | 3.4KB | Dated backup |
| `website/inc/rounds-backup-18-04-2025.inc` | 8.4KB | Dated backup |
| `website/inc/racing-state-backup-(tripple-elimination)).inc` | 16KB | Dated backup |
| `website/inc/racing-state-backup-(tripple-elimination)-18-04-2025-06-53-PM.inc` | 17KB | Dated backup |
| `website/ajax/action.schedule.generate-backup-16-04-2025.inc` | 4.8KB | Dated backup |
| `website/inc/schedule_orderedddd.inc` | 5.5KB | Orphaned duplicate |
| `website/inc/util.inc` | 2.8KB | Never included |
| `website/inc/current-racers.inc` | 1.5KB | Replaced by JSON version |

**JavaScript Files Cleaned:**
- `awards-editor.js` - Removed 3 commented-out lines
- `checkin.js` - Removed 1 commented-out line
- `photo-capture-modal.js` - Removed 3 commented-out lines
- `common-update.js` - Removed 1 commented-out line
- `coordinator-controls.js` - Removed 1 debug console.log
- `photo-thumbs.js` - Removed 1 debug console.log

#### 1.2 State Synchronization - COMPLETED (2026-01-14)

- [x] Add `threading.Lock()` to `derbyRace.py` shared state
  - Added `_race_lock` for `race_state`, `lane_times`, `lanesFinished`, `start_time`
  - Added `_heartbeat_lock` for `timer_heartbeats` dictionary
  - Protected all critical methods: `laneFinish()`, `laneDNF()`, `startRace()`, `stopRace()`, `setLEDFromRaceStat()`
  - Protected heartbeat methods: `timerHeartbeat()`, `cleanup_offline_timers()`, `send_heartbeat_to_api()`
  - Version bumped to 0.8.1 with detailed changelog
- [x] Implement atomic lane timing updates
  - `laneFinish()` uses atomic check-and-modify pattern with `_race_lock`
  - Prevents race conditions from concurrent MQTT message handling
- [x] Transaction handling for database operations
  - PHP already uses `beginTransaction()`/`commit()` for critical operations
  - Verified in: elimination advancement, racing-state, DNF handling, playlist, replay
- [x] State reconciliation mechanism between PHP and Python
  - PHP: `check_race_integrity()` in `racing-state.inc` detects timer/start mismatches
  - Python: `check_race_integrity()` in `derbyRace.py` detects PHP/Python state divergence
  - Both log warnings for operator visibility (no auto-correction for safety)
  - Race integrity status exposed via `poll.coordinator` API

#### 1.3 Error Handling Standardization - COMPLETED (2026-01-15)

- [x] Define standard error code enum - `error_codes.py` (Python), `error-codes.inc` (PHP)
- [x] Update critical action endpoints to use consistent format - JSON log entries with ERR-* codes
- [x] Add logging correlation IDs - Thread-local `CorrelationContext` in derbylogger.py v3.1.0

**New Files Created:**
- `extras/soapbox/infra/server/logsync.py` - Cloud log sync service (background, low priority)
- `extras/soapbox/infra/server/systemd/derbynet-logsync.service` - Systemd service config
- `extras/soapbox/infra/server/tests/test_correlation_ids.py` - 27 correlation ID tests
- `extras/soapbox/infra/server/tests/test_logsync.py` - 22 log sync tests

**Updated Files:**
- `extras/soapbox/infra/server/derbylogger.py` v3.1.0 - Correlation IDs, sequence numbers, sync metadata
- `website/inc/error-logging.inc` v3.1.0 - PHP correlation ID functions
- `extras/soapbox/infra/finishtimer/files/nodelogger.py` v3.1.0 - Re-exports correlation functions

**Architecture:**
- Correlation IDs trace requests across PHP → Python → MQTT → Timer
- JSON logs include: `corr_id`, `session_id`, `source`, `seq`, `sync_status`
- Log sync runs as background service (doesn't block race operations)
- Syncs to cloud for support/troubleshooting regardless of subscription tier

#### 1.4 Configuration Externalization - COMPLETED (2026-01-14)

- [x] Replace hardcoded IPs with environment variables

**Server-side files (already had env var support):**
- `server/derbyRace.py` - `MQTT_BROKER`, `MQTT_PORT`, `DERBYNET_API_HOST`
- `server/derbyapi.py` - `DERBYNET_API_HOST`
- `server/derbynet.py` - `MQTT_BROKER`, `MQTT_PORT`
- `server/derbylogger.py` - `RSYSLOG_IP`, `RSYSLOG_PORT`, `DERBY_DEBUG`
- `server/derbyTime.py` - `MQTT_BROKER`, `MQTT_PORT`
- `server/simulate_racing.py` - `MQTT_BROKER`, `MQTT_PORT`, `DERBYNET_API_HOST`

**Updated Python files for env var support:**
- `derbydisplay/derbydisplay.py` - Added `MQTT_BROKER`, `MQTT_PORT`
- `derbydisplay/derbylogger.py` - Added `RSYSLOG_IP`, `RSYSLOG_PORT`
- `finishtimer/files/finishtimer.py` - Added `MQTT_BROKER`, `MQTT_PORT`
- `finishtimer/files/derbynet.py` - Added `MQTT_BROKER`, `MQTT_PORT`
- `finishtimer/files/nodelogger.py` - Added `RSYSLOG_IP`, `RSYSLOG_PORT`, `DERBY_TIMEZONE`
- `server/lcdscreen/derbyLCD.py` - Added `MQTT_BROKER`, `MQTT_PORT`, `DERBYNET_API_HOST`

**MicroPython (starttimer) - file-based config:**
- `starttimer/src/main.py` - Added `/config.json` file support with defaults
- Config keys: `wifi_ssid`, `wifi_password`, `mqtt_broker`, `mqtt_port`, `ota_url`

**Design Note:** The on-premise Raspberry Pi server uses static IP `192.168.100.10` intentionally for race-day reliability (DNS is unreliable for critical timing). All defaults preserve this. Environment variables are for development, testing, Docker, and future multi-site deployments - not needed for production.

**Configuration Priority:**
1. mDNS service discovery (automatic, for supported devices)
2. Environment variables (for overrides/Docker)
3. Static default `192.168.100.10` (production fallback)

**Environment Variables Reference:**
| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_BROKER` | `192.168.100.10` or `localhost` | MQTT broker address |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `DERBYNET_API_HOST` | `192.168.100.10` or `localhost` | DerbyNet PHP API host |
| `RSYSLOG_IP` | `192.168.100.10` | Central rsyslog server |
| `RSYSLOG_PORT` | `514` | Rsyslog UDP port |
| `DERBY_TIMEZONE` | `America/Edmonton` | Timezone for logs |
| `DERBY_DEBUG` | `false` | Enable debug logging |

- [ ] Create `config.yaml` template (deferred - env vars sufficient for now)
- [ ] Update Docker Compose for environment profiles (deferred - not using Docker yet)

#### 1.5 Unified MQTT + Direct Database Access - COMPLETED (2026-01-14)

**Goal:** Eliminate HTTP latency in race-critical path, enable future cloud sync architecture.

**Two-Tier Architecture:**
```
┌─────────────────────────────────────────────────────────────────┐
│                ON-PREMISE (Free, Works Offline)                  │
│                                                                  │
│   Hardware ──MQTT──► derbyRace.py ──SQLite──► PHP (reads)       │
│                           │                                      │
│                     Direct DB writes                             │
│                     (WAL mode for                                │
│                      concurrent access)                          │
└──────────────────────────┬───────────────────────────────────────┘
                           │ Sync (when online, future)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                CLOUD (Subscription Extension)                    │
│                                                                  │
│   Mobile App ◄── API Gateway ◄── PostgreSQL (replica)           │
│   Public Portal                                                  │
│   Parent Features                                                │
└─────────────────────────────────────────────────────────────────┘
```

**Files Modified/Created:**
- [x] `website/inc/data.inc` - Added `PRAGMA journal_mode=WAL` and `busy_timeout=5000`
- [x] `extras/soapbox/infra/server/derbydb.py` - NEW: Direct SQLite database module
  - Thread-safe with internal locking
  - `write_race_results()` for sub-millisecond result persistence
  - `read_raceinfo()` / `write_raceinfo()` for config access
  - Falls back gracefully if unavailable
- [x] `extras/soapbox/infra/server/derbyRace.py` - Updated to v0.8.2
  - Uses direct DB when `DERBYNET_DB_PATH` environment variable set
  - Falls back to HTTP API if direct DB unavailable
  - Race results written directly to SQLite, eliminating HTTP latency

**New Environment Variable:**
| Variable | Default | Description |
|----------|---------|-------------|
| `DERBYNET_DB_PATH` | (none) | Path to SQLite database for direct access |

**Benefits:**
- Sub-millisecond race result persistence (was ~100-500ms via HTTP)
- PHP and Python can access database concurrently (WAL mode)
- No HTTP dependency in race-critical timing path
- Graceful fallback to HTTP if direct DB unavailable

**Future Cloud Sync (Phase 2+):**
- Sync service will poll local SQLite for changes
- Push to cloud API (1-5 second latency acceptable for public view)
- PII protection: Public sees only pinny + class + times (no names)
- Premium features: Interactive voting, parent notifications, analytics

### Phase 2: Testing (Priority: HIGH)

**Goal:** Comprehensive test coverage before commercialization

**Status:** Core Infrastructure Complete, 386 Tests Passing

#### 2.1 Python Unit Tests - 386 TESTS PASSING (2026-01-15)

**Test Infrastructure Created:**
- `extras/soapbox/infra/server/pytest.ini` - pytest configuration
- `extras/soapbox/infra/server/requirements-dev.txt` - test dependencies
- `extras/soapbox/infra/server/tests/` - test directory with:
  - `conftest.py` - fixtures with tiered database states (empty, registered, scheduled, completed)
  - `test_data.py` - normalized test data: 107 racers, 3 classes, 11 rounds, 102 results
  - `schema.sql` - real DerbyNet schema for testing
  - `test_derbydb.py` - database module tests (30 tests)
  - `test_derbyRace_threading.py` - thread safety tests (8 tests)
  - `test_schema.py` - schema validation tests (12 tests)
  - `test_config.py` - environment variable tests (21 tests)
  - `test_logging.py` - unified logging framework tests (22 tests)
  - `test_derbyapi.py` - API client tests (31 tests)
  - `test_derbynet.py` - MQTT/network library tests (27 tests)
  - `test_device_protocols.py` - device protocol validation (32 tests)
  - `test_device_errors.py` - device health monitoring tests (32 tests)
  - `test_finishtimer_resilience.py` - offline operation, recovery scenarios (27 tests)
  - `test_correlation_ids.py` - request tracing across components (27 tests)
  - `test_logsync.py` - cloud log sync service (22 tests)
  - `test_performance_timing.py` - race timing latency benchmarks (10 tests)

**Test Data Fixtures (from real event data):**
| Fixture | Contents | Use Case |
|---------|----------|----------|
| `empty_db` | Schema only | Initial setup testing |
| `registered_db` | 107 racers, 3 classes | Pre-race workflows |
| `scheduled_db` | + 11 rounds, 34 heats | Race execution |
| `completed_db` | + 102 race results | Results/standings |

**Run Tests:**
```bash
cd extras/soapbox/infra/server
pip install -r requirements-dev.txt
pytest -v
```

**Coverage Status:**
- [x] Set up pytest infrastructure
- [x] Unit tests for `derbydb.py` (31 tests) - **COMPLETE**
- [x] Thread safety tests for race state management (8 tests) - **COMPLETE**
- [x] Schema validation tests (sync with PHP schema) (12 tests) - **COMPLETE**
- [x] Environment variable configuration tests (21 tests) - **COMPLETE**
- [x] Unified logging framework tests (22 tests) - **COMPLETE**
- [x] Unit tests for `derbyapi.py` (31 tests) - **COMPLETE**
- [x] Unit tests for `derbynet.py` (27 tests) - **COMPLETE**
- [x] Device protocol validation (32 tests) - **COMPLETE** (finish timer, start timer, display)
- [x] Device error logging tests (32 tests) - **COMPLETE** (battery, WiFi, CPU temp, offline detection)
- [x] Finishtimer resilience tests (27 tests) - **COMPLETE** (MessageQueue persistence, MQTTClient offline, recovery scenarios)
- [x] Unit tests for `derbyRace.py` race logic (84 tests) - **COMPLETE** (state machine, lifecycle, hardware, threading)
- [ ] Hardware simulation tests for finishtimer.py (requires GPIO mocking - lower priority now that resilience is covered)

#### 2.2 Integration Test Expansion

- [ ] MQTT end-to-end message flow tests
- [ ] Hardware simulation test suite
- [ ] Multi-lane concurrent timing tests

#### 2.3 Security Testing

- [ ] SQL injection audit (all action endpoints)
- [ ] XSS vulnerability scan
- [ ] Authentication bypass testing
- [ ] CSRF protection verification

#### 2.4 Performance Testing - STARTED (2026-01-15)

- [x] Load testing framework setup - `performance.py` instrumentation module
- [x] Race timing latency tests - 10 tests measuring critical path
- [ ] 500+ racer scenario testing
- [ ] Concurrent user stress testing
- [ ] Database query optimization

**New Files Created:**
- `extras/soapbox/infra/server/performance.py` - Production instrumentation module
- `extras/soapbox/infra/server/tests/test_performance_timing.py` - 10 performance tests

**SLA Targets Defined:**
| Metric | P95 Target | Actual |
|--------|------------|--------|
| MQTT round-trip | 20ms | 1.4ms |
| Single lane finish | 50ms | 1.3ms |
| All lanes simultaneous | 100ms | 2.9ms |
| DB write | 10ms | 2.5ms |
| Sustained racing (degradation) | <20% | +1% |

**Test Results (2026-01-15):**
- All SLA targets met with significant headroom
- No performance degradation over 100 heats
- Timestamp precision: sub-microsecond

**⚠️ Hardware Note:** Baselines measured on development laptop (x86_64). Production runs on Raspberry Pi 4 (ARM64, 1.5GHz). Expect ~3-5x slower on Pi, but SLA targets set with this headroom in mind (laptop 2ms → Pi ~10ms → SLA 50ms).

#### 2.5 CI/CD Pipeline

- [ ] GitHub Actions workflow for tests
- [ ] Automated test execution on PR
- [ ] Code coverage reporting
- [ ] Static analysis integration

### Phase 3: Scalability (Priority: LOW)

**Goal:** API abstraction and multi-tenant foundation for DerbyNet PHP core

**Duration:** 6-8 weeks

**Scope Clarification:** This phase applies to the **DerbyNet PHP core** (`/website/`), NOT the SaaS API. The SaaS API (`/extras/saasbox/api/`) already has these capabilities built-in:

| Capability | SaaS API Status | DerbyNet PHP Status |
|------------|-----------------|---------------------|
| Multi-tenant middleware | ✅ `middleware/tenant.py` | 🔲 Not started |
| PostgreSQL + Row-Level Security | ✅ Complete | N/A (uses SQLite) |
| Rate limiting | ✅ `app/redis_client.py` | 🔲 Not started |
| Repository pattern | ✅ SQLAlchemy ORM | 🔲 Not started |
| API versioning | ✅ `/v1/` prefix | 🔲 Not started |
| Request validation | ✅ Pydantic schemas | 🔲 Not started |

**Priority Note:** Since the SaaS API handles all premium/cloud features, this phase is lower priority. Only needed if DerbyNet PHP core requires similar scalability for on-premise multi-org deployments.

#### 3.1 API Gateway (DerbyNet PHP)

- [ ] Create `/api/v1/` unified gateway
- [ ] OpenAPI 3.0 specification
- [ ] Request/response validation middleware
- [ ] Rate limiting implementation
- [ ] API versioning strategy

#### 3.2 Database Abstraction (DerbyNet PHP)

- [ ] Create `Repository` pattern interfaces
- [ ] Implement for SQLite (current)
- [ ] Add MySQL/PostgreSQL support
- [ ] Query caching layer
- [ ] Connection pooling

#### 3.3 Service Discovery

- [ ] mDNS implementation for local network
- [ ] DNS-SD for cloud discovery
- [ ] Health check endpoints
- [ ] Service registry

#### 3.4 Multi-Tenancy Foundation (DerbyNet PHP)

- [ ] Tenant isolation middleware
- [ ] Database-per-tenant schema
- [ ] Tenant configuration management
- [ ] Usage metrics collection

### Phase 4: LED Sign Integration (Priority: MEDIUM)

**Goal:** Production-ready LED signage system for race-day communication

**Status:** Firmware v1.1.0 + Admin Dashboard complete, 176 tests passing

#### 4.1 LED Sign Discovery & Assignment Architecture

**Key Design Decision:** HTTP for discovery/config (mirrors kiosk pattern), MQTT only for content delivery.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LED SIGN LIFECYCLE                                │
│                                                                         │
│  1. DISCOVERY (HTTP)           2. CONFIGURATION (HTTP)                  │
│  ┌─────────┐                   ┌─────────┐                              │
│  │  ESP32  │ ──GET /ledsign.php?mac=AA:BB:CC:DD:EE:FF──► │  DerbyNet │  │
│  │         │ ◄──── JSON: {zone: null, status: "identify"} │  Server  │  │
│  └─────────┘                   └─────────┘                              │
│       │                             │                                   │
│       │ Poll every 5s               │ Admin assigns zone via dashboard  │
│       ▼                             ▼                                   │
│  ┌─────────┐                   ┌─────────┐                              │
│  │  ESP32  │ ──GET poll.ledsign&mac=...──────────────────► │  DerbyNet │ │
│  │         │ ◄──── JSON: {zone: "starter", mqtt_topics: {...}} │ Server│ │
│  └─────────┘                   └─────────┘                              │
│       │                                                                 │
│       │ 3. CONTENT DELIVERY (MQTT) - only after zone assigned           │
│       ▼                                                                 │
│  ┌─────────┐    subscribe: derbynet/ledsign/starter/message            │
│  │  ESP32  │ ◄─────────────────────────────────────────── MQTT Broker  │
│  │         │    subscribe: derbynet/ledsign/broadcast                   │
│  └─────────┘                                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

**Zone Assignment Flow:**
1. ESP32 boots → connects to WiFi → polls `GET /ledsign.php?mac=...` every 5s
2. Sign appears in Admin Dashboard (`ledsign-dashboard.php`) as "unassigned"
3. Admin selects zone from dropdown → PHP writes to `LedSigns` table
4. Next poll returns zone + MQTT topics → ESP32 connects to MQTT for content
5. Race server publishes messages to zone topics during race

**Completed:**
- [x] BetaBrite Alpha Protocol library (`betabrite.py`) - all display modes, colors, effects
- [x] ESP32 MicroPython firmware v1.1.0 (`main.py`) - HTTP discovery, MQTT content
- [x] Single agnostic firmware pattern - MAC-based identity, HTTP configuration
- [x] HTTP-based device discovery - polls `/ledsign.php`, appears in admin dashboard
- [x] Admin dashboard (`ledsign-dashboard.php`) - zone assignment UI
- [x] PHP backend - `ledsigns.inc`, `ledsign-zones.inc`, action/query handlers
- [x] Database schema - `LedSigns` table (SQLite + MySQL)
- [x] Priority message system - emergency broadcasts override all content
- [x] Sponsor rotation support - JSON-configured sponsor messages
- [x] Comprehensive test suite - 176 tests covering protocol, messages, firmware logic

**Remaining:**
- [ ] Race server integration - publish to LED sign topics from derbyRace.py
- [ ] Sponsor management UI - configure sponsor messages in web interface
- [x] Emergency broadcast UI - coordinator page integration for alerts (**COMPLETE** - see 4.2)
- [ ] Hardware procurement and assembly (ESP32 + MAX3232 + BetaBrite)
- [ ] Field testing at race event

#### 4.2 Emergency Broadcast System (COMPLETE)

**Purpose:** Event-wide emergency notifications that persist until explicitly cleared.

**Coordinator Page UI:**
- Red-themed emergency input replacing the old broadcast message field
- 255 character limit with live counter
- Confirmation dialog before broadcasting
- Status banner showing active/inactive state
- "Clear Emergency" button (visible only during active emergency)

**Kiosk Display:**
- Red flashing banner covering top 20% of screen
- Shows "⚠️ EMERGENCY ⚠️" header with message text
- Persists until coordinator explicitly clears the emergency
- Takes priority over any regular broadcasts

**API Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `action.php?action=emergency.broadcast` | POST | Activate emergency (requires CONTROL_RACE_PERMISSION) |
| `action.php?action=emergency.clear` | POST | Clear emergency (requires CONTROL_RACE_PERMISSION) |

**Storage:** Emergency state stored in `RaceInfo` table as `emergency-broadcast` JSON with no auto-expiry.

**Files Created/Modified:**
- `website/ajax/action.emergency.broadcast.inc` - Set emergency
- `website/ajax/action.emergency.clear.inc` - Clear emergency
- `website/coordinator.php` - Emergency UI HTML
- `website/css/coordinator.css` - Emergency styling
- `website/js/coordinator-controls.js` - Emergency handlers
- `website/js/kiosk-poller.js` - Persistent emergency banner

**Zone Definitions:**
| Zone | Content | Format | Priority |
|------|---------|--------|----------|
| `starter` | READY / GO / STOP | Large, centered | 2 |
| `usher-lane{1-3}` | #42 JohnS | Pinny + FirstnameL | 2 |
| `finish-lane{1-3}` | 00:30.134 | mm:ss.nnn time | 2 |
| `registration` | Sponsor rotation | Scrolling | 3 |
| `audience` | Announcements | Various | 2-3 |
| `broadcast` | EMERGENCY | Flash red, all signs | 0 |

**HTTP Endpoints (Discovery/Configuration):**
| Endpoint | Direction | Purpose |
|----------|-----------|---------|
| `GET /ledsign.php?mac={MAC}` | Device→Server | Registration, receive zone |
| `GET /action.php?query=poll.ledsign&mac={MAC}` | Device→Server | Poll for config changes |
| `GET /action.php?query=poll.ledsign.all` | Dashboard→Server | Get all signs + zones |
| `POST /action.php action=ledsign.assign` | Dashboard→Server | Assign zone to sign |

**MQTT Topics (Content Delivery Only):**
| Topic | Direction | Purpose |
|-------|-----------|---------|
| `derbynet/ledsign/{zone}/message` | Server→Device | Zone content |
| `derbynet/ledsign/broadcast` | Server→All | Emergency override |
| `derbynet/ledsign/sponsors/rotation` | Server→Device | Sponsor content |

**PHP Files Created:**
| File | Purpose |
|------|---------|
| `website/ledsign.php` | ESP32 entry point (registration) |
| `website/ledsign-dashboard.php` | Admin UI for zone assignment |
| `website/inc/ledsigns.inc` | Core functions |
| `website/inc/ledsign-zones.inc` | Zone definitions |
| `website/ajax/query.poll.ledsign.inc` | Individual sign polling |
| `website/ajax/query.poll.ledsign.all.inc` | Dashboard polling |
| `website/ajax/action.ledsign.assign.inc` | Zone assignment |
| `website/js/ledsign-dashboard.js` | Dashboard JavaScript |
| `website/sql/sqlite/ledsign-table.inc` | SQLite schema |
| `website/sql/mysql/ledsign-table.inc` | MySQL schema |

**Documentation:** See `extras/ledsign/LED_SIGN_INTEGRATION_PLAN.md` for complete specification.

### Phase 5: FCM Push Notifications (Priority: MEDIUM)

**Goal:** Real-time mobile push notifications for premium SaaS users

**Status:** Phase 5.1, 5.2, 5.3 Complete - Ready for Flutter Integration (Phase 5.4)

**Documentation:** See `extras/saasbox/FCM_NOTIFICATION_PLAN.md` for complete specification.

#### 5.1 Notification Categories

| Category | Trigger | Priority | Opt-out |
|----------|---------|----------|---------|
| Favorite Staging | Racer within 5 heats | HIGH | Yes |
| Favorite Result | Heat completes | NORMAL | Yes |
| Poll Announcements | Poll activated/closed | NORMAL | Yes |
| Prediction Results | Heat resolves | NORMAL | Yes |
| Emergency Broadcast | Coordinator action | HIGH | No |
| Purchase Confirmation | Payment succeeds | HIGH | No |

#### 5.2 Implementation Tasks

**Phase 5.1: Foundation - COMPLETE**
- [x] Create database models (PushToken, NotificationPreference, NotificationLog) - `models/notification.py`
- [x] Create SQL migration (push_tokens, notification_preferences, notification_log) - `migrations/002_fcm_notifications.sql`
- [x] Update UserFavorite with last_staging_notified_at, last_result_notified_at
- [x] Add FCM config settings to app/config.py (fcm_enabled, staging_lookahead, dedup_window, batch_size)
- [x] Implement FCMService class with firebase-admin SDK - `services/notifications/fcm_service.py`
- [ ] Write unit tests for FCM service

**Phase 5.2: Triggers & Templates - COMPLETE**
- [x] Implement NotificationTriggers class - `services/notifications/triggers.py`
- [x] Create message templates (PII-safe, character limits) - embedded in triggers.py
- [x] Integrate with sync handler for staging/result notifications - `modules/events/routes.py`
- [x] Write integration tests - `tests/test_notifications.py`

**Phase 5.3: API & Preferences - COMPLETE**
- [x] Push token registration endpoint (POST /v1/me/notifications/push-token)
- [x] Push token listing endpoint (GET /v1/me/notifications/push-tokens)
- [x] Push token deletion endpoint (DELETE /v1/me/notifications/push-token/{deviceId})
- [x] Preferences management endpoints (GET/PATCH /v1/me/notifications/preferences)
- [x] Notification history endpoint (GET /v1/me/notifications/history)
- [x] Emergency broadcast endpoint (POST /v1/orgs/{orgId}/events/{eventId}/emergency/broadcast)
- [x] Emergency clear endpoint (DELETE /v1/orgs/{orgId}/events/{eventId}/emergency/broadcast)
- [x] Alert Manager integration (errors only)

**Files Created:**
```
extras/saasbox/api/
├── services/notifications/
│   ├── __init__.py             # Exports FCMService, NotificationTriggers
│   ├── fcm_service.py          # Full FCMService implementation
│   └── triggers.py             # NotificationTriggers + message templates
├── modules/notifications/
│   ├── __init__.py
│   ├── schemas.py              # Request/response Pydantic models
│   └── routes.py               # All notification endpoints
├── modules/events/
│   └── routes.py               # Updated: _trigger_sync_notifications()
└── app/main.py                 # Updated: registered notification routes
```

**Phase 5.4: Flutter Client**
- [ ] Configure firebase_messaging package
- [ ] Create Android notification channels (5 channels)
- [ ] Implement deep link routing for all notification types
- [ ] Handle foreground/background/terminated states

#### 5.3 Key Design Decisions

| Decision | Choice |
|----------|--------|
| Staging timing | Notify when racer within 5 heats |
| Emergency authority | Race Coordinator only |
| Notification scope | Favorites only (reduces noise) |
| Alert Manager | Errors only (not every send) |
| Platform | Android Phase 1, iOS Phase 2 (next year) |

#### 5.4 Emergency Broadcast Alignment

Emergency broadcasts are synchronized with LED sign system:
- Same message content to both channels
- Coordinator-only authorization
- Cannot be opted out of
- High priority / wake device from Doze

---

## 10. White-Label Architecture

### Runtime Configuration Model

```
/var/lib/derbynet/
├── config/
│   └── tenant.yaml           # Tenant-specific configuration
├── branding/
│   ├── logo.png              # Custom logo (max 500x200)
│   ├── logo-dark.png         # Dark mode variant
│   └── colors.yaml           # Color scheme
├── content/
│   ├── ads/                  # Advertisement images/videos
│   ├── sponsors/             # Sponsor content
│   └── signage/              # Custom signage
└── templates/                # Optional template overrides
```

### Branding Configuration Schema

```yaml
# /var/lib/derbynet/branding/colors.yaml
branding:
  name: "Example Derby"
  tagline: "Racing for Glory"

colors:
  primary: "#1a73e8"          # Main brand color
  secondary: "#34a853"        # Accent color
  background: "#ffffff"       # Page background
  text: "#202124"             # Primary text
  highlight: "#fbbc04"        # Highlight/attention

fonts:
  heading: "Roboto"
  body: "Open Sans"
  display: "Racing Sans One"  # For large displays

features:
  show_sponsors: true
  show_ads: true
  custom_css: false           # Enable custom CSS injection
```

### Content Loading at Runtime

PHP will check for tenant-specific content in order:
1. `/var/lib/derbynet/content/{type}/` (tenant override)
2. `/var/www/derbynet/content/{type}/` (default)

Python services use same pattern via environment variable:
```bash
DERBYNET_CONTENT_PATH=/var/lib/derbynet/content
```

### White-Label Feature Tiers

| Feature | Basic | Standard | Premium |
|---------|-------|----------|---------|
| Logo replacement | Yes | Yes | Yes |
| Color scheme | Yes | Yes | Yes |
| Custom fonts | No | Yes | Yes |
| Sponsor content | No | Yes | Yes |
| Advertisement slots | No | Yes | Yes |
| Custom CSS | No | No | Yes |
| Template overrides | No | No | Yes |
| Custom domain | No | No | Yes |

**Primary Domain:** `soapboxderbynet.com`
- Main cloud service: `app.soapboxderbynet.com`
- API endpoint: `api.soapboxderbynet.com`
- Parent portal: `portal.soapboxderbynet.com` (or `soapboxderbynet.com`)
- Documentation: `docs.soapboxderbynet.com`

---

## 11. Two-System Architecture: Registration vs Users

### Terminology Clarification

This system has **two completely separate identity domains** that must not be confused:

| Term | System | Who Controls | Contains PII | Description |
|------|--------|--------------|--------------|-------------|
| **Registration** (Racers) | On-Premise Only | Local Staff | Yes (children) | Racer entry, check-in, car weighing, race results |
| **Users** (Premium) | Cloud Only | Self-service | Yes (parents) | Mobile app accounts, notifications, social features |
| **Local Users** (Staff) | On-Premise Only | Admin | Minimal | Fixed staff accounts (coordinator, timer, check-in) |

### System Separation

```
┌─────────────────────────────────────┐     ┌─────────────────────────────────────┐
│     ON-PREMISE (Local Staff)        │     │      CLOUD (Premium Subscription)   │
│                                     │     │                                     │
│  REGISTRATION = Racers (Children)   │     │  USERS = Parents/Public             │
│  ├─ Names, ages (PII)               │     │  ├─ Email, profile (PII)            │
│  ├─ Check-in status                 │     │  ├─ Notification preferences        │
│  ├─ Car weight, inspection          │     │  ├─ Favourites (pinny numbers)      │
│  ├─ Race times, places              │     │  ├─ Votes, predictions              │
│  └─ Awards earned                   │     │  └─ Social features                 │
│                                     │     │                                     │
│  LOCAL USERS = Staff (handful)      │     │                                     │
│  ├─ coordinator                     │     │                                     │
│  ├─ timer                           │ ──► │  SYNCED DATA (PII-stripped):        │
│  ├─ check-in                        │     │  ├─ Pinny number                    │
│  └─ (fixed accounts)                │     │  ├─ Age group/class                 │
│                                     │     │  ├─ Race times, places              │
│  SQLite (source of truth)           │     │  └─ Schedule, standings             │
└─────────────────────────────────────┘     └─────────────────────────────────────┘
                                                           │
                                                           ▼
                                               "Favourite Pinny #1234"
                                               (only bridge between systems)
```

### The "Favourite Pinny" Bridge

The **ONLY connection** between Registration (racers) and Users (premium accounts) is the pinny number:

- A User (parent) can "favourite" a pinny number in the mobile app
- This triggers push notifications when that pinny's racer is scheduled
- **No PII crosses this boundary** - just an integer identifier
- On-premise system is unaware of who favourited what

### PII Protection Requirements (CRITICAL)

**Racers are children. Strict data protection is mandatory.**

| Data Field | Public API | Staff Interface | Synced to Cloud |
|------------|------------|-----------------|-----------------|
| Pinny Number | Yes | Yes | Yes |
| Age Group/Class | Yes | Yes | Yes |
| Race Times | Yes | Yes | Yes |
| Finish Place | Yes | Yes | Yes |
| Schedule/Heat | Yes | Yes | Yes |
| **First Name** | **NO** | Yes | **NO** |
| **Last Name** | **NO** | Yes | **NO** |
| **Photos** | **NO** | Yes | **NO** (unless explicit opt-in) |
| **Contact Info** | **NO** | Yes | **NO** |

**Cloud API Enforcement:**
- Public endpoints return ONLY: `pinny`, `class`, `finishtime`, `place`
- No joins to name fields in public queries
- Photo access requires explicit parent consent flag (future feature)

### Premium Features (Subscription)

| Feature | Free (On-Premise) | Premium (Cloud) |
|---------|-------------------|-----------------|
| Race Management | Yes | N/A |
| Staff Tablets/Kiosks | Yes | N/A |
| Hardware Integration | Yes | N/A |
| Live Public Standings | No | Yes (pinny + class only) |
| Mobile App | No | Yes |
| Push Notifications | No | Yes |
| Favourite a Racer | No | Yes (by pinny) |
| Audience Voting | No | Yes |
| Predictions Game | No | Yes |
| Analytics Dashboard | No | Yes |

---

## 12. Hybrid Deployment Model

### On-Premise Requirements (Raspberry Pi)

**Hardware:**
- Raspberry Pi 4 (4GB+ RAM recommended)
- 32GB+ SD card
- Ethernet connection (primary)
- WiFi (backup/devices)
- DS3231 RTC module (for offline time sync)

**Software Stack:**
- Raspberry Pi OS Lite (64-bit)
- Nginx + PHP-FPM
- SQLite database
- Python 3.9+
- Eclipse Mosquitto MQTT broker
- systemd service management

**Network Configuration:**
- Static IP: `192.168.100.10` (configurable)
- MQTT: port 1883
- HTTP: port 80
- mDNS: `derbynet.local`

### Cloud Requirements

**Infrastructure:**
- Container orchestration (Docker Compose / Kubernetes)
- PostgreSQL database (multi-tenant)
- Redis cache
- Load balancer with SSL termination
- Object storage (S3-compatible) for media

**Services:**
- API Gateway (authentication, rate limiting)
- Sync Receiver (on-premise → cloud, one-way)
- Mobile Backend (push notifications, real-time updates)
- Admin Portal (tenant management)
- Analytics Service (usage tracking)

### Sync Protocol (One-Way: Local → Cloud)

**CRITICAL:** Sync is strictly one-way. On-premise is the source of truth for all race data.

```
On-Premise (Source of Truth)    Cloud (Read Replica + Premium)
    │                             │
    │  1. Connect (when online)   │
    ├────────────────────────────►│
    │                             │
    │  2. Push race data          │
    │     (PII-stripped)          │
    │     - pinny, class, times   │
    │     - NO names, NO photos   │
    ├────────────────────────────►│
    │                             │
    │  3. Acknowledge receipt     │
    │◄────────────────────────────┤
    │                             │
    │  4. Continue offline        │
    │     (if connection lost)    │
    │                             │
```

**Data Flow Rules:**
- On-premise race results are authoritative (hardware truth)
- Cloud NEVER writes back to on-premise
- Cloud stores its own premium data (Users, votes, favourites) independently
- No conflict resolution needed - on-premise always wins

### Offline Capabilities

When cloud connection is unavailable, on-premise system:

| Function | Availability |
|----------|--------------|
| Race timing | Full |
| Heat scheduling | Full |
| Result recording | Full |
| Kiosk displays | Full |
| Award management | Full |
| New registrations | Full (local only) |
| Mobile app access | Limited (cached data) |
| Parent portal | Unavailable |
| Analytics | Queued for sync |

---

## Appendix A: File Reference

### ~~Files to Remove~~ - COMPLETED

All files have been removed (2026-01-14):

```
# DELETED:
website/inc/form_groups_by_rule-backup-18-04-2025.inc
website/inc/rounds-backup-18-04-2025.inc
website/inc/racing-state-backup-(tripple-elimination)).inc
website/inc/racing-state-backup-(tripple-elimination)-18-04-2025-06-53-PM.inc
website/ajax/action.schedule.generate-backup-16-04-2025.inc
website/inc/schedule_orderedddd.inc
website/inc/util.inc
website/inc/current-racers.inc
```

### ~~Files to Consolidate~~ - COMPLETED

```
website/inc/schedule_ordered.inc      # Kept (active)
# schedule_orderedddd.inc deleted - was orphaned
```

### Files Requiring IP Address Updates

```
extras/soapbox/infra/server/derbyapi.py
extras/soapbox/infra/server/derbyRace.py
extras/soapbox/infra/server/derbyTime.py
extras/soapbox/infra/server/derbylogger.py
extras/soapbox/infra/finishtimer/files/finishtimer.py
extras/soapbox/infra/finishtimer/files/derbynet.py
extras/soapbox/infra/derbydisplay/derbydisplay.py
extras/soapbox/infra/starttimer/src/main.py
```

---

## Appendix B: Test Script Reference

### Integration Tests

| Script | Tests |
|--------|-------|
| `test-ab-initio-setup.sh` | Initial database setup |
| `test-basic-checkins.sh` | Racer registration and check-in |
| `test-basic-racing.sh` | Heat execution and results |
| `test-extended-scheduling.sh` | Complex scheduling scenarios |
| `test-partitions.sh` | Heat partitioning |
| `test-awards.sh` | Award management |
| `test-permissions.sh` | Role-based access |
| `test-messaging.sh` | Broadcast messages |
| `test-each-role.sh` | Multi-role workflows |
| `test-visit-each-page.sh` | UI completeness |

### Browser Tests

| Script | Tests |
|--------|-------|
| `puppeteer/coordinator-test.js` | Coordinator dashboard |
| `puppeteer/checkin-empty-test.js` | Empty check-in state |
| `puppeteer/ondeck-columns-test.js` | On-deck display |
| `puppeteer/all-pages-test.js` | Page navigation |

---

## Appendix C: MQTT Topic Reference

| Topic | Publisher | Subscriber | QoS |
|-------|-----------|------------|-----|
| `derbynet/race/state` | Race Server | Displays, Timers | 1 |
| `derbynet/device/{hwid}/status` | Devices | Race Server | 1 |
| `derbynet/device/{hwid}/telemetry` | Devices | Race Server | 1 |
| `derbynet/device/{hwid}/state` | Finish Timer | Race Server | 2 |
| `derbynet/device/{hwid}/update` | Race Server | Devices | 1 |
| `derbynet/lane/{n}/led` | Race Server | Finish Timer | 1 |
| `derbynet/lane/{n}/pinny` | Race Server | Finish Timer | 1 |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-14 | Claude Code Assessment | Initial enterprise readiness assessment |
| 1.1 | 2026-01-14 | Claude Code | Phase 1.1 Complete: Dead code cleanup - removed 8 files (~55KB), cleaned commented code from 7 files |
| 1.2 | 2026-01-14 | Claude Code | Phase 1.2 Complete: State synchronization - added thread locks to derbyRace.py v0.8.1, verified PHP transactions, integrity checks in place |
| 1.3 | 2026-01-14 | Claude Code | Phase 1.4 Complete: Configuration externalization - added env var support to 7 Python files, file-based config for MicroPython starttimer |
| 1.4 | 2026-01-14 | Claude Code | Architecture: Unified MQTT + Direct DB - SQLite WAL mode, derbydb.py for direct DB writes, derbyRace.py v0.8.2 with direct DB integration |
| 1.5 | 2026-01-14 | Claude Code | Architecture clarification: Added Section 11 (Two-System Architecture), fixed sync to one-way (Local→Cloud), documented PII protection, clarified Registration vs Users terminology |
| 1.6 | 2026-01-14 | Claude Code | Testing: Created pytest infrastructure with real DerbyNet schema, 26+ unit tests for derbydb.py, schema validation tests, fixed RLock deadlock bug in derbydb.py v0.1.1 |
| 1.7 | 2026-01-14 | Claude Code | Testing: Fixed threading tests for paho-mqtt 2.0 - added MockMQTTPublishResult with `rc` attribute, added `send_timer_heartbeat()` to MockDerbyNetClient. All 72 tests now passing. |
| 1.8 | 2026-01-14 | Claude Code | Phase 1.3 Started: Unified logging framework - Created error_codes.py (Python) and error-codes.inc (PHP) registries with ERR-{CAT}-{NUM} format. Updated derbylogger.py v3.0.0 with dual text+JSON output. Fixed derbydb.py v0.1.2 to use unified logger. Created test_logging.py with 22 test cases. All 94 tests passing. |
| 1.9 | 2026-01-15 | Claude Code | Phase 2.1 Major Expansion: Added 122 new tests covering derbyapi.py (31 tests), derbynet.py (27 tests), device protocols (32 tests), and device error logging (32 tests). Tests validate finish timer, start timer, display protocols, battery monitoring, WiFi signal, CPU temp, device offline detection. Added ERR-HW-104 for CPU temperature warnings. All 216 tests passing. |
| 1.10 | 2026-01-15 | Claude Code | Test Data Infrastructure: Created test_data.py with normalized data from real event (107 racers, 3 classes, 11 rounds, 102 results). Updated conftest.py with tiered fixtures (empty_db, registered_db, scheduled_db, completed_db) for different test scenarios. Schema-independent approach survives future schema changes. All 216 tests passing. |
| 1.11 | 2026-01-15 | Claude Code | **derbyRace.py Comprehensive Test Coverage**: Created DERBYRACE_TEST_PLAN.md documenting 84 test cases. Implemented test_derbyRace_statemachine.py (20 tests), test_derbyRace_lifecycle.py (37 tests), test_derbyRace_hardware.py (27 tests). Coverage includes: state machine transitions, race lifecycle (start/finish/DNF), DB fallback logic, MQTT message parsing, DIP switch mapping, LED control, timer heartbeats, thread safety. All 300 tests passing. |
| 1.12 | 2026-01-15 | Claude Code | **Finishtimer Resilience Tests**: Created test_finishtimer_resilience.py (27 tests) covering production failure scenarios from race day. Tests validate: MessageQueue disk persistence, MQTTClient offline operation with exponential backoff, toggle event survival across timer/server restarts, concurrent queue access, recovery scenarios (timer battery disconnect, server power loss, intermittent network). All 327 tests passing. |
| 1.13 | 2026-01-15 | Claude Code | **Phase 1.3 Complete - Error Handling Standardization**: Added correlation IDs for request tracing across PHP→Python→MQTT→Timer. Created logsync.py service for cloud log transmission (background sync regardless of premium status). Updated derbylogger.py v3.1.0 with thread-local correlation context, sequence numbers for ordering, sync metadata. Updated error-logging.inc v3.1.0 with PHP correlation functions. Created systemd service for log sync. Added test_correlation_ids.py (27 tests), test_logsync.py (22 tests). All 376 tests passing. |
| 1.14 | 2026-01-15 | Claude Code | **Phase 2.4 Started - Performance Testing**: Created performance.py production instrumentation module with thread-safe metrics collection, SLA checking, and slow operation logging. Created test_performance_timing.py with 10 benchmark tests covering MQTT latency, DB writes, single/multi-lane finishes, sustained racing, and timing precision. All SLA targets exceeded with significant headroom (single lane: 1.3ms vs 50ms target, all lanes: 2.9ms vs 100ms target). No degradation over 100 heats. All 386 tests passing. |
| 1.15 | 2026-01-15 | Claude Code | **Phase 4 Added - LED Sign Integration**: Added LED Sign Controller to system components table. Added HW-07/08/09 to Hardware Integration validation matrix. Created Phase 4 roadmap section with architecture diagram, zone definitions, MQTT topics, completion status (firmware + 176 tests complete), and remaining integration work. |
| 1.16 | 2026-01-16 | Claude Code | **Phase 5 Added - FCM Push Notifications**: Created comprehensive FCM notification plan (`extras/saasbox/FCM_NOTIFICATION_PLAN.md`). Covers: 7 notification types (staging, results, polls, predictions, emergency, purchases), FCMService with firebase-admin SDK, NotificationTriggers for event-based dispatch, user preferences, Flutter client integration, emergency broadcast alignment with LED signs. Key decisions: notify within 5 heats, Coordinator-only emergencies, favorites-only scope, Alert Manager for errors only. Android Phase 1, iOS Phase 2 (next year). |
| 1.17 | 2026-01-16 | Claude Code | **Phase 5.1 Database Models**: Created `models/notification.py` with PushToken, NotificationPreference, NotificationLog SQLAlchemy models. Created `migrations/002_fcm_notifications.sql` with full schema including indexes, constraints, and cleanup function. Updated UserFavorite with last_staging_notified_at, last_result_notified_at. Updated User model with push_tokens and notification_preferences relationships. Added FCM config settings (fcm_enabled, staging_lookahead, dedup_window, batch_size) to app/config.py. |
| 1.18 | 2026-01-16 | Claude Code | **Phase 5.1 & 5.3 Complete - FCM Service + API Endpoints**: Created `services/notifications/fcm_service.py` with full FCMService implementation (token management, multicast batching up to 500, deduplication, preference filtering, emergency broadcasts, invalid token cleanup). Created `modules/notifications/` with schemas.py (Pydantic request/response models) and routes.py (8 endpoints: push token CRUD, preferences GET/PATCH, notification history, emergency broadcast/clear). Registered routes in main.py at `/v1/me/notifications` and `/v1/orgs/{orgId}/events/{eventId}/emergency`. |
| 1.19 | 2026-01-16 | Claude Code | **Phase 4 HTTP Discovery Architecture**: Implemented HTTP-based LED sign discovery mirroring kiosk pattern. ESP32 firmware v1.1.0 uses HTTP polling for registration/config (`/ledsign.php`), MQTT only for content delivery after zone assignment. Created admin dashboard (`ledsign-dashboard.php`), PHP backend (ledsigns.inc, ledsign-zones.inc, action/query handlers), database schema (LedSigns table for SQLite/MySQL). Updated LED_SIGN_INTEGRATION_PLAN.md to v1.3.0 and ESP32 README with new architecture. |
| 1.20 | 2026-01-16 | Claude Code | **Phase 4.2 Emergency Broadcast System**: Implemented event-wide emergency notifications. Repurposed coordinator broadcast input for emergencies with red-themed UI, 255 char limit, confirmation dialog. Emergency broadcasts persist until explicitly cleared (no auto-expiry). Kiosks display red flashing banner that persists until cleared. Created `action.emergency.broadcast.inc` and `action.emergency.clear.inc`. Updated coordinator.php, coordinator.css (200+ lines), coordinator-controls.js, coordinator-poll.js, kiosk-poller.js, query.poll.kiosk.inc, query.poll.coordinator.inc. Added emergency tests to test-ledsign-backend.sh. |

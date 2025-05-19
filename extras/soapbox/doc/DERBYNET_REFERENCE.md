# DerbyNet Soapbox Derby Reference

This reference document provides a comprehensive technical summary of the DerbyNet soapbox derby system for AI-based integration. It covers the core architecture, operation workflow, race management logic, and device integration specifications needed for system integration and compatibility.

## 1. System Overview

DerbyNet is a PHP-based web application for managing soapbox derby races with these key capabilities:

- Multi-device architecture with central server and connected client displays
- Support for triple elimination race format optimized for soapbox derby
- Real-time race management, timing, and results tracking
- Integrated photo/video capture and HLS replay system
- Comprehensive racer registration and check-in workflow
- Award management and presentation capabilities

## 2. System Architecture

### 2.1 Core Components

#### Database Layer
- File: `inc/data.inc`
- Abstraction over SQLite or ODBC (Access)
- Key tables: RaceInfo, RaceChart, Roster, Rounds, Classes, Racer
- Configuration stored as key-value pairs in RaceInfo table

#### Race Management
- File: `inc/racing-state.inc`
- "NowRacingState" controls automatic or manual race progression
- Triple elimination format with preliminary, semi-final, and final rounds
- Enforces validation rules like round completion requirements

#### Scheduling Engine
- Files: `inc/schedule_*.inc`, `inc/form_groups_by_rule.inc`
- Optimized heat generation with fairness algorithms
- Lane assignment with rotation to equalize race opportunity
- Handles racer dropouts and inconsistent heat counts

#### Timer Integration
- File: `inc/timer-state.inc`
- States: CONNECTED, STAGING, RUNNING, UNHEALTHY, NOT_CONNECTED
- 60-second heartbeat required to maintain connection
- Malfunction detection and automatic recovery

#### Kiosk System
- Files: `kiosk.php` and files in `kiosks/` directory
- Displays for various race functions (results, check-in, standings)
- Registration via HTTP/AJAX with polling mechanism
- Intelligent display assignment from coordinator

### 2.2 Communication Protocols

#### Primary Communication
- HTTP/AJAX polling for most interfaces
- Optional WebSocket support for improved responsiveness
- JSON format for structured data exchange

#### Message System
- Queue-based messaging in database or filesystem
- Messages expire after configurable timeframes
- Used for race control, timer state, and kiosk updates

#### Timer Protocol
- Plain text commands with JSON status responses
- Periodic heartbeat required (every 60 seconds)
- Explicit state transitions (STAGING → RUNNING → CONNECTED)

#### Video/Replay System
- WebRTC for camera feeds, HTTP for control
- HLS (HTTP Live Streaming) support for video replay
- Circular buffer mechanism for instant replay

## 3. Race Management Workflow

### 3.1 Setup Phase

- **Database Selection**: Create or select SQLite/Access database
- **Lane Configuration**: Set number of lanes for track (typically 3-6)
- **Timer Settings**: Configure timer connection and operation mode
- **Class Definition**: Create racing groups and classes
- **Award Setup**: Define award types and criteria

### 3.2 Registration Phase

- **Roster Import**: Import racers from CSV/Excel or enter manually
- **Class Assignment**: Assign racers to appropriate groups/classes
- **Check-in Process**: Mark racers present, capture racer/car photos
- **Car Numbering**: Assign unique identifiers to cars

### 3.3 Racing Phase

- **Schedule Generation**: Create optimized heat schedules
- **Heat Management**: Control race progression through heats
- **Timer Integration**: Capture race times automatically or manually
- **Result Recording**: Store and validate all race results
- **Round Advancement**: Promote qualifying racers to next round
- **Video Replay**: Capture and display race replays

### 3.4 Results Phase

- **Standings Calculation**: Determine rankings based on results
- **Results Display**: Show standings and detailed racer results
- **Award Management**: Track and present award recipients
- **Export Options**: Generate CSV, JSON exports of results

## 4. Racing Format Details

### 4.1 Triple Elimination Format

1. **Preliminary Round**
   - Each racer completes 3 runs (one in each lane)
   - Times from all 3 runs are averaged
   - Top 21 racers with best average times advance

2. **Semi-Final Round**
   - 21 qualified racers compete
   - Best time determines advancement
   - Top 3 racers advance to finals

3. **Final Round**
   - 3 qualified racers compete
   - Best time determines final standings (1st, 2nd, 3rd place)

### 4.2 Scheduling Logic

1. **Schedule Generation**
   - Roster retrieved and organized by class/group
   - Optimized heat assignments with fairness algorithms
   - BYEs added to balance lanes if needed

2. **Lane Assignment Logic**
   - Configurable priorities with weights:
     - Even race distribution (`rate_race_counts`)
     - Avoid consecutive races (`rate_consecutive`)
     - Avoid same lane repetition (`avoid-same-lane`)

3. **Fairness Mechanisms**
   - Weight-based car grouping for similar competition
   - Lane bias detection and compensation
   - Equal lane distribution for each racer

### 4.3 Results Processing

1. **Time Collection**
   - Times retrieved from timer or entered manually
   - Validation to ensure all lanes have times/places
   - DNF handling for incomplete races

2. **Place Calculation**
   - Automatic place determination from times
   - Tie handling for identical finish times
   - Results stored in RaceChart table

3. **Advancement Logic**
   - Preliminary → Semi-Finals: Best average time from 3 runs
   - Semi-Finals → Finals: Best time in semi-final round
   - Final standings based on final round performance

## 5. Device Integration Reference

### 5.1 Timer Integration

- **Protocol**: HTTP/AJAX polling with plain text/JSON
- **States**: CONNECTED, STAGING, RUNNING, UNHEALTHY, NOT_CONNECTED
- **Connection**: 60-second heartbeat requirement
- **Commands**:
  - START: Begin timing a heat
  - STAGING: Prepare timer for race start
  - UNHEALTHY: Report malfunction
- **Time Format**: Decimal seconds to precision of 0.001

### 5.2 Kiosk System

- **Protocol**: HTTP/AJAX polling
- **Identification**: IP+port or custom identifier
- **Assignment**: Coordinator selects display type for each kiosk
- **Kiosk Types**:
  - now-racing: Shows current race status
  - standings: Shows race standings
  - ondeck: Shows upcoming races
  - results-by-racer: Shows individual racer results
  - others defined in kiosks/*.kiosk files

### 5.3 Video/Replay System

- **Protocols**: 
  - WebRTC for direct camera integration
  - HLS (HTTP Live Streaming) for video feeds
  - HTTP/AJAX for control messages

- **Replay Commands**:
  - START: Begin recording new heat
  - REPLAY: Trigger playback of recorded content
  - RACE_STARTS: Set delayed replay after race
  - CANCEL: Cancel pending replay

- **Configuration**:
  - replay-skipback: Buffer duration (default: 4000ms)
  - replay-num-showings: Repeat count (default: 2)
  - replay-rate: Playback speed percentage (default: 50%)
  - hls-stream-url: URL to HLS stream (http://derbynetpi:8037/hls/stream.m3u8)

- **Storage**: 
  - Videos saved to configured directory as MKV files
  - Naming convention: ClassA_Round1_Heat01.mkv

### 5.4 Device Status API

- **Protocol**: RESTful API (GET/POST)
- **Authentication**: Session-based
- **Data Structure**: JSON with required device metrics
- **Timeout**: 60-second update window
- **Fields**: device_name, serial, status, uptime, battery, memory, etc.

## 6. Database Schema Details

### 6.1 Core Tables

- **RaceInfo**: Key-value configuration storage
- **RaceChart**: Race results with heat, lane, time, place
- **Rounds**: Competition structure and advancement rules
- **Classes**: Racer grouping and organization
- **Racer**: Participant information including status
- **Roster**: Maps racers to rounds they're eligible for

### 6.2 Auxiliary Tables

- **SettingsMessage**: Stores and routes messages between components
- **Awards**: Award definitions and criteria
- **PhotoInfo**: Links to racer/car photos
- **RaceChart**: Individual race results
- **Timer**: Timer settings and configuration

## 7. Integration Requirements

### 7.1 Timer Hardware Requirements

- Must make periodic HTTP contact (heartbeat)
- Must report state transitions properly
- Must provide lane-by-lane finish times in correct format
- Must respond to START/STAGING commands

### 7.2 Display Client Requirements

- Must support HTTP/AJAX polling
- Must interpret standard JSON data structures
- Must handle RELOAD signals
- Must render appropriate content for assigned kiosk type

### 7.3 Video System Requirements

- Must support WebRTC or HLS video streaming
- Must implement circular buffer concept for replay
- Must respond to replay control messages
- Must handle appropriate video encoding/decoding

### 7.4 External System Requirements

- Must authenticate via PHP sessions
- Must conform to expected data formats
- Must handle connection timeouts appropriately
- Must respect data validation requirements

## 8. Security Considerations

- Session-based authentication for all interfaces
- Role-based permissions for different functions
- No explicit encryption beyond HTTPS if configured
- Limited API security with basic session validation

## 9. HLS Replay Specific Integration

The system supports HLS (HTTP Live Streaming) for video replay with these features:

- **HLS Stream URL**: Configured as `http://derbynetpi:8037/hls/stream.m3u8`
- **HLS.js Library**: Used for stream handling in browser
- **Circular Buffer**: Records from stream for instant replay
- **Replay Triggers**:
  - Automatic on race completion
  - Manual from coordinator interface
  - Test mode for setup
- **Replay Options**:
  - Buffer length: 4000ms default
  - Playback speed: 50% default (slow motion)
  - Repeat count: 2 times default
- **Video Storage**:
  - Saved as MKV files when enabled
  - Named by race details (class, round, heat)
  - Stored in configured video directory

---

This reference document provides the technical foundation for integrating with and understanding the DerbyNet soapbox derby race management system. It is structured for AI consumption and provides comprehensive details on architecture, functionality, and integration points.
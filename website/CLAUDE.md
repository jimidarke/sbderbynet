# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## DerbyNet Overview

DerbyNet is an open-source race management system for Pinewood Derby and Soapbox Derby events. It's built as a PHP web application that manages all aspects of derby racing: racer registration, scheduling, timing, results tracking, and award management.

The current branch (soapbox-derby) appears to be customized for soapbox derby racing.

## System Architecture

- **PHP Web Application**: The system runs as a web server that multiple devices can connect to during a race.
- **Database**: Uses SQLite by default, but can also use ODBC connections (e.g., for Microsoft Access).
- **Multi-device System**: Designed for a central server with various devices/screens connecting as kiosks showing different views (race results, standings, etc.).
- **Timer Integration**: Can connect to physical timing hardware for tracking race results.

## Key Components

1. **Database Layer** (`inc/data.inc`): Handles database connections and core operations.
2. **Racing Logic** (`inc/racing-state.inc`, `inc/schedule_*.inc`): Manages race scheduling and state.
3. **Web Interface**: PHP-based pages for various race management functions.
4. **Kiosk System**: Different displays can be configured for various purposes (results display, check-in, etc).
5. **Settings & Configuration**: Centralized settings management.

## Schedule Generation Logic

The race scheduling system is managed through several key files:

### **Core Files**
- `coordinator.php:238-256` - Schedule modal interface with user input for "times each racer appears in each lane"
- `js/coordinator-controls.js:215-290` - Frontend logic handling schedule modal and AJAX submission
- `ajax/action.schedule.generate.inc` - Backend processing of schedule generation requests
- `inc/schedule_one_round.inc` - Core scheduling algorithms and race chart generation

### **Data Flow**
1. User clicks "Schedule" button on coordinator page
2. Modal displays with dropdown for runs per lane (default: 1)
3. User selection sent via AJAX to `action.schedule.generate.inc`
4. Backend processes triple elimination logic and user preferences
5. Calls `schedule_one_round()` with final parameters
6. Race chart written to database and coordinator page updates

### **Triple Elimination Integration**
- **Preliminary rounds**: Default to 3 runs per lane (each racer runs in each lane 3 times)
- **Semifinal/Final rounds**: Default to 1 run per lane  
- **User override**: Any explicit selection (2,3,4,5,6) overrides triple elimination defaults
- **Logic location**: `action.schedule.generate.inc:125` and `schedule_one_round.inc:265`

### **Recent Fixes (2025-05-26)**
Fixed issue where triple elimination logic completely overrode user input:
- Modified logic to only apply defaults when user hasn't explicitly chosen a different value
- Set explicit default to 1 in coordinator modal
- Maintained automatic behavior while preserving user control

## Running and Development

### Setup

To set up a new DerbyNet instance:

1. Ensure PHP is available with necessary extensions (PDO, SQLite).
2. Access the setup page at `/setup.php` to configure the database and other settings.

### Development Tools

DerbyNet doesn't use modern build tools or a package manager. Its development mode is:

- Direct PHP editing
- JavaScript for frontend functionality (using jQuery)
- CSS for styling

### Testing

There's no dedicated test framework. Testing is primarily done by:

1. Setting up a test database (can use the "Fake Roster" feature)
2. Running through race management workflows manually

### Common Commands

When developing for DerbyNet:

- **Local Development**: Use a PHP server with `php -S localhost:8000` to serve the website directory
- **Database Management**: Database operations are managed through the web interface at `setup.php`
- **Debugging**: PHP errors appear in the web server logs or in `error_log.php`

## Data Structure

The core entities in the system are:

- **Racers**: Participants in the derby
- **Racing Groups/Classes**: Categories for organizing racers
- **Rounds**: Race organization units
- **Heats**: Individual race instances
- **Awards**: Recognition for various achievements

## Workflow

The typical race management workflow is:

1. **Setup**: Configure database and system settings
2. **Registration**: Import or enter racers
3. **Racing Groups**: Set up classes and groups for racers
4. **Check-in**: Record participants as they arrive
5. **Racing**: Schedule and run races, collect results
6. **Standings**: Display race results and overall standings
7. **Awards**: Present awards to participants

## Common Files and Directories

- `/inc/`: Core functionality and helper code
- `/js/`: JavaScript files for frontend functionality
- `/css/`: Styling and layout
- `/ajax/`: Backend handlers for AJAX requests
- `/sql/`: Database schema and management
- `/kiosks/`: Kiosk configurations for various displays
- `/Images/`: Assets for the different derby types

### Slideshow System

DerbyNet includes a comprehensive slideshow system for displaying sponsor images, intermission content, and general announcements:

- **Shared Slideshow Template** (`shared-slideshow.php`): Common slideshow implementation used by all slideshow kiosks
- **Slideshow Configuration** (`inc/slideshow-config.inc`): Central configuration for slideshow timing and directory settings
- **Slideshow JavaScript** (`js/shared-slideshow.js`): Handles image cycling and timing logic

**Available Slideshow Kiosk Types:**
- `slideshow.kiosk`: General slideshow from main directory
- `sponsors.kiosk`: Sponsor advertisements from sponsors/ subdirectory  
- `intermission.kiosk`: Intermission content from intermission/ subdirectory

**Settings:**
- `slideshow-directory`: Base directory path for slideshow images (configured in Settings page)
- `slideshow-duration`: Duration in seconds each image displays (default: 30 seconds)
- `slideshow-duration-sponsors`: Optional custom timing for sponsor slides
- `slideshow-duration-intermission`: Optional custom timing for intermission slides

### Broadcast Messaging System

DerbyNet includes a broadcast messaging system for sending urgent announcements to all active kiosk displays:

- **AJAX Endpoints** (`ajax/action.broadcast.message.inc`, `ajax/action.broadcast.clear.inc`): API for sending and clearing broadcast messages
- **Kiosk Integration** (`ajax/query.poll.kiosk.inc`, `js/kiosk-poller.js`): Automatic message display on all kiosk types
- **Message Display**: White text on black background overlay covering top 20% of screen

**Key Features:**
- 255 character message limit with configurable duration (1-300 seconds)
- Automatic expiration and cleanup of old messages
- Permission-based access (requires CONTROL_RACE_PERMISSION)
- Works on all kiosk types including slideshow variations
- Uses existing 5-second polling cycle for near real-time delivery

**Database Storage:**
- `broadcast-message`: JSON data stored in RaceInfo table containing message, duration, timestamp, and expiration

### Scene Management and Coordinator Integration

DerbyNet's scene system allows coordinated control of multiple kiosk displays through predefined configurations:

- **Scene Management** (`scenes.php`): Create and edit scene configurations that define which page each named kiosk should display
- **Kiosk Dashboard** (`kiosk-dashboard.php`): Primary interface for scene selection and individual kiosk management
- **Coordinator Integration** (`coordinator.php`): Scene selector dropdown added to coordinator page for centralized scene control during races

**Key Features:**
- **Centralized Control**: Change scenes from both the kiosk dashboard and coordinator page
- **Real-time Updates**: Scene changes are immediately reflected across all connected kiosks via polling
- **Database-driven**: Scene configurations stored in `Scenes` and `SceneKiosk` tables
- **Coordinator Integration**: Scene selector positioned above playlist controls in the coordinator interface

**Implementation Details:**
- **JavaScript Functions**: `setup_scenes_select_control_coordinator()` and `on_scene_change_coordinator()` in `coordinator-controls.js`
- **Polling Integration**: Scene updates included in `query.poll.coordinator.inc` for automatic synchronization
- **Styling**: Scene selector uses consistent styling with kiosk dashboard (`coordinator.css`)
- **Backend API**: Leverages existing `action.scene.apply.inc` endpoint for scene changes

## Troubleshooting Elimination Tournaments

### Schedule Modal Issues
If the schedule modal doesn't adapt for elimination tournaments:
1. Open browser console (F12) to check for JavaScript errors
2. Look for console messages: "show_schedule_modal called for roundid: X"
3. Verify AJAX responses for elimination tournament detection
4. Check that coordinator-controls.js is loaded properly

### Kiosk Display Issues  
If elimination kiosks show PHP errors:
1. Verify database schema is version 16 (includes elimination tables)
2. Check that elimination tournament is properly initialized for the class
3. Ensure classid parameter is passed correctly to kiosk URL
4. Look for "Undefined array key" errors in server logs

### Common Error Patterns
- `"Undefined array key 'name'"`: Indicates JSON key mismatch - age groups use `'name'`, rounds use `'round_name'`
- `"Creating triple elimination rounds"`: Old legacy system still active - check form_groups_by_rule.inc
- `"No active tournament"`: Tournament not initialized or classid mismatch

### Debugging Commands
```bash
# Check current schema version
php -r "chdir('website'); require_once('inc/data.inc'); echo 'Schema: ' . schema_version() . '\n';"

# View elimination tournament tables
sqlite3 database.db ".tables" | grep -i elimination

# Check for legacy triple elimination functions
grep -r "create_triple_elimination_rounds" website/inc/
```

## DerbyNet Permission System

DerbyNet uses a bitmask permission system where each permission is a power of 2:

**Core Permissions:**
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

**Default Role Permissions:**
- **Anonymous**: `VIEW_RACE_RESULTS_PERMISSION` only
- **Timer**: `TIMER_MESSAGE_PERMISSION` only (non-interactive)
- **Photo**: `PHOTO_UPLOAD_PERMISSION` only (non-interactive)
- **RaceCrew**: Includes `CHECK_IN_RACERS_PERMISSION`, `JUDGING_PERMISSION`, `EDIT_RACER_PERMISSION`, etc.
- **RaceCoordinator**: All permissions (value `-1`)

**Permission Usage in Features:**
- Racing group setup: `SET_UP_PERMISSION` (RaceCoordinator only)
- Heat advancement: `CONTROL_RACE_PERMISSION` (RaceCoordinator only)
- Basic race viewing: `VIEW_RACE_RESULTS_PERMISSION` (All roles)

## Elimination Tournament System

The soapbox derby system includes a hardcoded elimination tournament format to replace complex UI configuration with reliable, pre-tested race structures.

### **Core Components**

**Configuration System:**
- JSON-based tournament definitions in `/inc/elimination-configs/`
- Age group patterns match DerbyNet classes via regex (e.g., "Ages 6-8", "6-8", "6 to 8")
- Hardcoded race parameters: rounds, advancement counts, scoring methods

**Tournament Formats:**
- **Ages 6-8**: 4 rounds (Preliminary → Quarter Finals → Semi-Finals → Finals)
- **Ages 9-11**: 4 rounds (Preliminary → Quarter Finals → Semi-Finals → Finals)  
- **Ages 12-14**: 3 rounds (Preliminary → Semi-Finals → Finals)

**Database Integration:**
- `EliminationTournaments` - Tournament state tracking
- `EliminationRoundState` - Round progression management
- `EliminationAdvancement` - Advancement audit trail
- Extends existing `Rounds` table with elimination metadata

**API Endpoints:**
- `query.elimination.config.list.inc` - List available configurations
- `action.elimination.tournament.initialize.inc` - Initialize tournaments  
- `query.elimination.tournament.status.inc` - Tournament status
- `action.elimination.tournament.advance.inc` - Advance to next round

### **Key Design Decisions**

**Operational Simplicity:**
- No rescheduling for dropouts - empty lanes get DNF (99.000s) times
- No tiebreaker logic needed (0.001s timing precision)
- Automatic advancement based on time rankings
- Leverages existing heat ordering algorithms with elimination-specific weighting
- Partial heats allowed (1-2 racers per heat) to accommodate dropouts/equipment failures
- Coordinator scheduling modal automatically bypassed for elimination tournaments (uses hardcoded parameters)

**Heat Ordering Priority (Elimination Tournaments):**
- `avoid_consecutive`: 1000 (highest priority - prevent back-to-back races for same racer)
- `group_weighted_cars`: 300 (medium priority - group similar weight cars)
- `avoid_same_lane`: 300 (medium priority - lane variation)
- `heat_counts`: 50 (lowest priority - even heat distribution)

**Reliability Focus:**
- Predetermined tournament structures eliminate configuration errors
- JSON validation ensures consistent race parameters  
- State persistence handles system restarts gracefully
- Integration with existing DerbyNet scheduling and timing systems

### **Implementation Files**

**Core Logic:** `inc/elimination-config.inc` - Configuration loading, validation, tournament management
**Database Schema:** `sql/*/elimination-tables.inc` - Tournament state tables
**Configuration:** `inc/elimination-configs/soapbox-derby-elimination.json` - Tournament definitions
**API Layer:** `ajax/action.elimination.*` and `ajax/query.elimination.*` - AJAX endpoints

### **Permission Requirements**

**Elimination Tournament Operations:**
- Tournament initialization: `SET_UP_PERMISSION` - RaceCoordinator only (same as racing group setup)
- Tournament status queries: `VIEW_RACE_RESULTS_PERMISSION` - All roles can view tournament status
- Tournament advancement: `CONTROL_RACE_PERMISSION` - RaceCoordinator only (same as advancing heats)  
- Configuration management: `SET_UP_PERMISSION` - RaceCoordinator only (system configuration level)

## Recent Updates and Fixes (2025-06-11)

### Schedule Modal Enhancement
The coordinator schedule modal now intelligently detects elimination tournaments:
- **Smart Detection**: Automatically identifies elimination tournament rounds via AJAX
- **Visual Feedback**: Orange border and styling when elimination tournament detected
- **Disabled Controls**: Dropdown becomes disabled with explanatory text
- **Preserved Functionality**: Both "Schedule" and "Schedule + Race" buttons remain functional
- **Robust Fallback**: Modal always works even if tournament detection fails

### Legacy System Removal
- **Conflict Resolution**: Removed old automatic triple elimination system that conflicted with new JSON-based approach
- **Clean Separation**: No more automatic round creation during racing group formation
- **User Control**: Rounds now created only when elimination tournaments are explicitly initialized

### PHP Error Fixes
- **Kiosk Display Issues**: Fixed "Undefined array key 'name'" errors in both elimination kiosk displays
- **Correct Key Usage**: Age groups use `'name'` key, rounds use `'round_name'` key per JSON structure
- **Error-Free Operation**: Elimination kiosks now render without PHP warnings

### Database Schema Compatibility
- **Schema Version 16**: Elimination tournament tables properly integrated
- **Column Mapping**: Fixed database insertion to use existing schema columns
- **Backward Compatibility**: Standard DerbyNet functionality preserved

## Specific Configuration

When working in the soapbox-derby branch:
- The UI elements and images are tailored specifically for soapbox derby rather than pinewood derby
- Some racing logic may be customized for this specific derby type
- Elimination tournaments use hardcoded JSON configurations for predictable race management
- Schedule modal automatically adapts behavior based on tournament type
- Dedicated elimination kiosk displays for tournament-specific information
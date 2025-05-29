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

## Specific Configuration

When working in the soapbox-derby branch:
- The UI elements and images are tailored specifically for soapbox derby rather than pinewood derby
- Some racing logic may be customized for this specific derby type
# Kiosk Functionality Improvements Analysis

## Current Kiosk System Overview

### Architecture
- **Central kiosk management**: Controlled through `kiosk-dashboard.php` and `coordinator.php`
- **Scene-based system**: Uses `scenes.php` to manage different display configurations
- **Database-driven**: Kiosk assignments stored in `Kiosks` table with scene configurations in `Scenes` and `SceneKiosk` tables
- **Polling-based updates**: Kiosks poll server every 2 seconds via AJAX (`query.poll.kiosk.inc`, `query.poll.kiosk.all.inc`)

### Current Features
1. **Kiosk Assignment**: Individual kiosks can be assigned specific pages (e.g., now-racing, standings, ondeck)
2. **Scene Management**: Pre-defined scenes that set multiple kiosk displays simultaneously
3. **Messaging System**: Basic message passing for WebRTC signaling (`inc/messages.inc`, `action.message.send.inc`)
4. **Slideshow Configuration**: Custom slideshow parameters including title, subdirectory, and class filtering

## Proposed Improvements Analysis

### 1. Scene Switching on Coordinator Page

**Current State:**
- Scene switching is only available on `kiosk-dashboard.php` (line 52-58)
- Uses dropdown with `scenes-select` ID and `on_scene_change()` handler
- Coordinator page has no scene switching capability

**Implementation Requirements:**
- **Files to modify:**
  - `coordinator.php`: Add scene dropdown similar to kiosk-dashboard
  - `js/coordinator-controls.js`: Add scene change handler
  - CSS styling to match coordinator page layout

**Technical Details:**
- Reuse existing scene management functions from `inc/scenes.inc`
- Leverage existing `action.scene.apply.inc` AJAX endpoint
- JavaScript variables `g_all_scenes` and `g_current_scene` already available in kiosk-dashboard

**Implementation Approach:**
```javascript
// Add to coordinator.php similar to kiosk-dashboard.php:52-58
<div id="scenes-control">
  <label for="scenes-select">Current scene:</label>
  <select id="scenes-select"></select>
</div>

// Reuse setup_scenes_select_control() and on_scene_change() from kiosk-dashboard.js
```

**Confidence Level: HIGH** - Well-defined existing patterns to follow

### 2. Text-based Notification Broadcasting ✅ **COMPLETED**

**Implementation Status: COMPLETED (January 2025)**

**Features Implemented:**
- **New AJAX Endpoints:**
  - `action.broadcast.message.inc` - Send broadcast messages
  - `action.broadcast.clear.inc` - Clear active messages
- **Kiosk Integration:**
  - Updated `query.poll.kiosk.inc` to include broadcast message data
  - Modified `kiosk-poller.js` to display messages on all kiosk types
- **Message Display:**
  - White text on black background overlay (top 20% of screen)
  - Configurable duration (1-300 seconds, default 20)
  - Auto-expiration and cleanup
  - Duplicate message prevention
- **Permission Control:**
  - Requires `CONTROL_RACE_PERMISSION`
  - Proper authentication via session cookies

**Technical Implementation:**
- Uses `RaceInfo` table for message storage (key: `broadcast-message`)
- JSON data structure with message, duration, timestamp, and expiration
- Integrates with existing 5-second kiosk polling cycle
- Automatic cleanup of expired messages

**API Usage:**
```bash
# Send broadcast message
curl -X POST http://localhost/action.php \
  -H "Cookie: PHPSESSID=YOUR_SESSION_COOKIE" \
  -d "action=broadcast.message" \
  -d "message=Emergency: Track delay" \
  -d "duration=30"

# Clear active message
curl -X POST http://localhost/action.php \
  -H "Cookie: PHPSESSID=YOUR_SESSION_COOKIE" \
  -d "action=broadcast.clear"
```

**Works On All Kiosk Types:**
- now-racing, standings, ondeck, slideshow, sponsors, intermission
- All slideshow variations using shared-slideshow.php
- Any kiosk page that includes kiosk-poller.inc

**Production Ready:** Clean operation with no debug artifacts

### 3. Slideshow Image Folder Path Management ✅ **COMPLETED**

**Implementation Status: COMPLETED (January 2025)**

**Features Implemented:**
- **Settings Page Integration:**
  - Added "Slideshow Directory" field in Settings → Photos section
  - Added "Slideshow Duration (seconds)" field for timing control
  - Proper validation and error handling for both settings
- **Database Integration:**
  - Added `slideshow-directory` and `slideshow-duration` to RaceInfo table
  - Settings persist across sessions and server restarts
- **Slideshow System Enhancements:**
  - Unified slideshow functionality via `shared-slideshow.php`
  - Support for multiple slideshow types: general, sponsors, intermission
  - Centralized configuration via `inc/slideshow-config.inc`

**Settings Added:**
- `slideshow-directory`: Base path for slideshow images
- `slideshow-duration`: Default duration in seconds (range 1-300)
- `slideshow-duration-sponsors`: Optional custom timing for sponsor slides
- `slideshow-duration-intermission`: Optional custom timing for intermission

**Kiosk Types Implemented:**
- `slideshow.kiosk`: General slideshow content
- `sponsors.kiosk`: Sponsor advertisements from sponsors/ subdirectory
- `intermission.kiosk`: Intermission content from intermission/ subdirectory

**Technical Implementation:**
- Updated `action.settings.write.inc` to handle new settings
- Modified `slideshow-config.inc` to read database settings
- Enhanced `shared-slideshow.js` and `slideshow.js` to use configurable timing
- Proper kiosk polling integration for all slideshow types

**Directory Structure:**
```
/slideshow-base-path/
├── sponsors/          # Sponsor advertisements
├── intermission/      # Intermission content  
└── general/          # General slideshow images
```

**Production Ready:** All slideshow functionality fully integrated and configurable

## Implementation Status

### ✅ Phase 1: Slideshow Directory Management - **COMPLETED**
- **Status**: Fully implemented and production ready
- **Files Modified**: settings.php, action.settings.write.inc, slideshow-config.inc, shared-slideshow.php
- **Features Added**: Directory configuration, duration settings, unified slideshow system

### ✅ Phase 2: Notification Broadcasting System - **COMPLETED**  
- **Status**: Fully implemented and production ready
- **Files Modified**: action.broadcast.message.inc, action.broadcast.clear.inc, query.poll.kiosk.inc, kiosk-poller.js, shared-slideshow.php
- **Features Added**: Broadcast messaging API, kiosk display overlay, automatic expiration

### 🔄 Phase 3: Scene Switching on Coordinator - **PENDING**
- **Effort**: Low
- **Risk**: Low  
- **Dependencies**: None
- Reuses existing scene management infrastructure
- **Implementation**: Add scene dropdown to coordinator.php similar to kiosk-dashboard

## Technical Questions & Considerations

### Notification System Design Questions:
1. **Persistence**: Should notifications survive browser refresh or kiosk reconnection?
2. **Queue Management**: How many notifications can be active simultaneously?
3. **Priority System**: Should there be different notification levels (info, warning, critical)?
4. **Access Control**: Should only certain user roles be able to send notifications?
5. **Integration**: How should notifications interact with existing modal dialogs and overlays?

### Implementation Assumptions:
1. Notification system will use existing message infrastructure with new message types
2. All kiosk pages will need notification display capability added
3. Slideshow directory setting will default to current behavior for backwards compatibility
4. Scene switching on coordinator will use identical UI patterns to kiosk-dashboard

### Files Requiring Modification Summary:

**Slideshow Directory Management:**
- `settings.php` (add form field)
- `inc/slideshow-config.inc` (update path resolution)
- Database schema (add RaceInfo entry)

**Coordinator Scene Switching:**
- `coordinator.php` (add scene dropdown)
- `js/coordinator-controls.js` (add scene change handler)
- CSS updates for styling

**Notification Broadcasting:**
- `coordinator.php` (add notification input)
- `action.message.send.inc` (extend for notifications)
- All kiosk template files (add notification display)
- `js/kiosk-poller.js` (check for notification messages)
- CSS for notification styling

**Confidence Assessment:**
- **Slideshow Management**: 95% confidence - clear existing patterns
- **Scene Switching**: 90% confidence - well-defined reusable components  
- **Notification System**: 70% confidence - significant new UI/UX work required, integration complexity

## Recommended Implementation Order:
1. Slideshow directory management (quick win, low risk)
2. Coordinator scene switching (moderate effort, clear requirements)
3. Notification broadcasting (complex, requires design decisions)
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

### 2. Text-based Notification Broadcasting

**Current State:**
- Message system exists but limited to WebRTC signaling
- `inc/messages.inc` provides `send_message()` and `retrieve_messages()` functions
- Messages have recipient targeting and automatic expiration (1s broadcast, 15s targeted)
- No UI for sending general notifications

**Implementation Requirements:**
- **Backend:**
  - Extend `action.message.send.inc` to handle general notifications
  - Create new message type for coordinator alerts
  - Modify polling mechanisms to check for notification messages

- **Frontend:**
  - Add notification input field to coordinator page
  - Implement alert modal display system on all kiosk pages
  - 20-second timeout with red background as specified

**Technical Details:**
- Leverage existing message infrastructure with new message type:
```json
{
  "type": "coordinator-notification",
  "message": "Emergency: Track delay - 15 minutes",
  "duration": 20000,
  "recipient": "" // Empty for broadcast
}
```

- Modify kiosk polling to check for notification messages
- Add notification display to all kiosk templates

**Questions/Assumptions:**
- Should notifications persist across kiosk page changes?
- Should there be notification history/logging?
- How should notifications interact with existing modal dialogs?

**Confidence Level: MEDIUM** - Message system exists but significant UI work required

### 3. Slideshow Image Folder Path Management

**Current State:**
- Settings page has photo directory configuration for racers, cars, and videos (lines 312-319)
- Slideshow uses subdirectory selection but no base path setting
- `find_alternate_slides_directories()` function searches for slideshow subdirectories
- Slideshow configuration handled in `inc/slideshow-config.inc`

**Implementation Requirements:**
- **Files to modify:**
  - `settings.php`: Add slideshow directory field similar to photo-dir fields
  - `inc/slideshow-config.inc`: Update to use configurable base path
  - Database: Add `slideshow-directory` to RaceInfo table

**Technical Details:**
- Follow existing pattern from `photo_settings()` function (settings.php:256-274)
- Add new settings field:
```php
<?php photo_settings('slideshow images', 'slideshow-dir', read_raceinfo('slideshow-directory')); ?>
```

- Update slideshow path resolution to use configured directory
- Ensure backwards compatibility with existing relative path structure

**Database Changes:**
- Add `slideshow-directory` key to RaceInfo table
- Default value should maintain current behavior (data directory relative)

**Confidence Level: HIGH** - Clear pattern exists, straightforward implementation

## Implementation Priority and Dependencies

### Phase 1: Slideshow Directory Management
- **Effort**: Low-Medium
- **Risk**: Low
- **Dependencies**: None
- Most straightforward implementation following existing patterns

### Phase 2: Scene Switching on Coordinator
- **Effort**: Low
- **Risk**: Low  
- **Dependencies**: None
- Reuses existing scene management infrastructure

### Phase 3: Notification Broadcasting System
- **Effort**: Medium-High
- **Risk**: Medium
- **Dependencies**: UI/UX design decisions needed
- Requires coordination across multiple kiosk types and polling systems

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
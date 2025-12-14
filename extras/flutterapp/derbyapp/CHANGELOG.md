# Changelog

All notable changes to the SBDerbyNet Mobile App will be documented in this file.

## [0.1.1] - 2025-12-14

### Added
- **Racing Schedule Screen**: New feature to view upcoming heats that haven't been run yet
  - Shows heat number, round name, and racer lineup
  - Lane badges with color coding
  - Pull-to-refresh functionality
  - Sorted by heat order (next up first)
- **Heat History Screen**: Enhanced history view for completed heats
  - Expandable/collapsible heat cards with ExpansionTile
  - Shows round names (e.g., "Ages 6-8, 1 Preliminary")
  - Medal emojis (🥇🥈🥉) for top 3 finishers in completed heats
  - Pinny number chips in collapsed state
  - Race times rounded to 1 decimal place (5.4s format)
  - Filters out incomplete heats (only shows race history)

### Changed
- Replaced "View Recent Results" button with "View Racing Schedule" on dashboard
- Improved heat history UI to be more compact and informative
- Updated Quick Actions card on dashboard

### Fixed
- Type mismatch errors in data models:
  - Changed `speed` field from `int` to `double` in HeatResultModel
  - Changed `current-scene` field from `String` to `int` in CoordinatorPollResponse
- Added missing `OnDeckEntryModel` import in heat_history_screen.dart
- Fixed heat history to only show completed heats

### Technical Improvements
- Created `racingScheduleProvider` for fetching upcoming heats
- Enhanced `HeatGroup` class with `roundName` field
- Improved data fetching to include round information from coordinator poll
- Better separation of completed vs. upcoming heats

## [0.1.0] - 2025-12-13

### Added
- Initial release
- Dashboard with current heat information
- Real-time race status updates
- Racer lineup display
- Connection status indicator
- Server configuration screen
- Authentication screens (login/splash)
- Timer state monitoring
- Basic navigation with go_router
- Riverpod state management
- Clean architecture with repository pattern

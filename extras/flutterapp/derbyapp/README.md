# SBDerbyNet Mobile App

Mobile application for soapbox derby race management built with Flutter.

## Current Version: 0.1.1

**Status**: Active Development - Core features implemented and functional

## Features

### Dashboard & Live Race Status
- ✅ Real-time race status polling (1-second intervals)
- ✅ Current heat information display
- ✅ Racer lineup with lane assignments
- ✅ Timer status and health monitoring
- ✅ Connection status indicator
- ✅ Quick action buttons for navigation

### Racing Schedule
- ✅ View upcoming heats that haven't been run yet
- ✅ Heat lineup with racer names and car numbers
- ✅ Color-coded lane badges
- ✅ Round information (e.g., "Ages 6-8, 1 Preliminary")
- ✅ Pull-to-refresh functionality

### Heat History
- ✅ View completed heats with race results
- ✅ Expandable/collapsible heat cards
- ✅ Medal emojis (🥇🥈🥉) for top 3 finishers
- ✅ Race times displayed to nearest 10th of second
- ✅ Pinny number chips for quick reference
- ✅ Filtered to show only completed races

### Server Configuration
- ✅ Server URL configuration screen
- ✅ Connection validation
- ✅ Settings persistence

## Architecture

- **Pattern**: Clean Architecture with Repository Pattern
- **State Management**: Riverpod
- **Navigation**: GoRouter
- **HTTP Client**: Dio
- **Storage**: Flutter Secure Storage + SharedPreferences

## Project Structure

```
lib/
├── core/                  # Core utilities and constants
├── data/                  # Data layer (API, models, repositories)
├── domain/                # Business logic
└── presentation/          # UI layer (screens, providers, widgets)
```

## Getting Started

### Prerequisites

- Flutter SDK 3.38.5+ (installed at `/home/jimi/flutter`)
- Android SDK with accepted licenses
- Android device or emulator

### Setup

```bash
# Navigate to project directory
cd /home/jimi/Documents/SBDerbyNet/extras/flutterapp/derbyapp

# Get dependencies
/home/jimi/flutter/bin/flutter pub get

# Run the app
/home/jimi/flutter/bin/flutter run
```

### Build APK

```bash
# Debug build
/home/jimi/flutter/bin/flutter build apk --debug

# Release build
/home/jimi/flutter/bin/flutter build apk --release
```

## Configuration

The app requires configuration of the DerbyNet server URL on first launch. The server should be accessible on the local WiFi network (e.g., `http://192.168.100.10`).

## Documentation

- [CHANGELOG](CHANGELOG.md) - Version history and release notes
- [SBDerbyNet Main Project](../../../) - Main project repository
- [API Test Script](test_endpoints.sh) - Endpoint validation script

## API Integration

The app connects to the DerbyNet server REST API:
- **Coordinator Poll**: `/action.php?query=poll.coordinator` - Real-time race status
- **OnDeck Chart**: `/action.php?query=poll&values=ondeck` - Heat history and schedule
- **Heat Details**: `/action.php?query=poll.coordinator&roundid={id}&heat={num}` - Specific heat results

See `test_endpoints.sh` for endpoint validation and testing.

## Development Roadmap

### Completed (v0.1.1)
- ✅ Real-time race dashboard
- ✅ Racing schedule viewer
- ✅ Heat history with results
- ✅ Server configuration
- ✅ Connection monitoring

### Planned Future Enhancements
- Individual racer profiles and tracking
- Push notifications for racer's upcoming heats
- Offline mode with local caching
- Photo display for racers and cars
- Advanced filtering and search
- Export results to PDF/CSV

## License

Part of the SBDerbyNet project.

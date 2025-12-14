# SBDerbyNet Mobile App

Mobile application for soapbox derby race management built with Flutter.

## Project Status

**Phase 1 - In Development**: Offline race status dashboard with authentication

## Features (Phase 1)

- ✅ Clean architecture setup
- ✅ Dependencies configured
- 🚧 Offline authentication against DerbyNet server
- 🚧 Real-time race status polling (1-second intervals)
- 🚧 Dashboard displaying:
  - Current heat information
  - Racer lineup
  - Timer status
  - Race integrity warnings

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

- [Implementation Plan](IMPLEMENTATION_PLAN.md) - Complete development roadmap
- [SBDerbyNet Main Project](../../website/) - PHP backend

## Phase Roadmap

- **Phase 1** (Current): Offline race dashboard
- **Phase 2** (Future): Cloud deployment with Firebase and SSO
- **Phase 3** (Future): Race results and upcoming heats
- **Phase 4** (Future): Individual racer tracking with push notifications

## License

Part of the SBDerbyNet project.

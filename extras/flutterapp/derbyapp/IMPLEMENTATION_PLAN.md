# SBDerbyNet Flutter Mobile App - Implementation Plan

## Executive Summary

This plan details the development of an Android Flutter mobile app for soapbox derby race management, with a phased rollout from offline-only local deployment to cloud-based multi-user functionality.

**Target Platform:** Android only (Phase 1)
**User Scale:** 100-500 users (Phase 2+)
**Cloud Backend:** Firebase (Phase 2+)
**State Management:** Riverpod
**Architecture:** Clean Architecture with Repository Pattern

---

## Prerequisites: Flutter SDK Installation

Before starting development, you need to install the Flutter SDK on your development system (Linux).

### 0.1 Install Flutter SDK

**Step 1: Download Flutter**
```bash
# Navigate to your home directory or preferred installation location
cd ~

# Download Flutter SDK (stable channel)
wget https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.27.1-stable.tar.xz

# Extract the archive
tar xf flutter_linux_3.27.1-stable.tar.xz

# Optional: Remove the archive to save space
rm flutter_linux_3.27.1-stable.tar.xz
```

**Step 2: Add Flutter to PATH**
```bash
# Add Flutter to your PATH permanently
echo 'export PATH="$HOME/flutter/bin:$PATH"' >> ~/.bashrc

# Reload your shell configuration
source ~/.bashrc

# Verify Flutter is in PATH
flutter --version
```

**Step 3: Run Flutter Doctor**
```bash
# Check for missing dependencies
flutter doctor

# This will show you what needs to be installed:
# - Android toolchain (Android SDK, Platform Tools)
# - Chrome (for web development - optional)
# - Linux toolchain (optional)
```

### 0.2 Install Android Development Tools

**Step 1: Install Android Studio (Recommended)**
```bash
# Download Android Studio from:
# https://developer.android.com/studio

# Or use snap (Ubuntu/Debian):
sudo snap install android-studio --classic

# Launch Android Studio
android-studio
```

**Step 2: Install Android SDK via Android Studio**
1. Open Android Studio
2. Go to **Tools → SDK Manager**
3. Install the following:
   - **Android SDK Platform-Tools** (latest)
   - **Android SDK Build-Tools** (latest)
   - **Android SDK Platform** (API 34 or latest)
   - **Android SDK Command-line Tools**

**Step 3: Accept Android Licenses**
```bash
# Accept all Android SDK licenses
flutter doctor --android-licenses

# Type 'y' to accept all licenses when prompted
```

### 0.3 Alternative: Command-Line Only Setup (No Android Studio)

If you prefer command-line tools only:

```bash
# Install Java (required for Android SDK)
sudo apt-get update
sudo apt-get install openjdk-17-jdk

# Download Android command-line tools
mkdir -p ~/Android/Sdk/cmdline-tools
cd ~/Android/Sdk/cmdline-tools
wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip commandlinetools-linux-11076708_latest.zip
mv cmdline-tools latest

# Add to PATH
echo 'export ANDROID_HOME="$HOME/Android/Sdk"' >> ~/.bashrc
echo 'export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"' >> ~/.bashrc
echo 'export PATH="$ANDROID_HOME/platform-tools:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Install required SDK components
sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"

# Accept licenses
flutter doctor --android-licenses
```

### 0.4 Verify Installation

```bash
# Run Flutter doctor to verify everything is set up
flutter doctor -v

# You should see checkmarks for:
# ✓ Flutter (Channel stable)
# ✓ Android toolchain - develop for Android devices
# ✓ Linux toolchain (optional)

# Create a test project to verify
flutter create test_app
cd test_app
flutter run -d linux  # Test on Linux desktop

# Or connect Android device and run:
flutter devices  # Should list your Android device
flutter run      # Runs on connected device
```

### 0.5 Install Additional Tools (Optional)

**VS Code with Flutter Extension (Recommended IDE):**
```bash
# Install VS Code
sudo snap install code --classic

# Install Flutter extension
code --install-extension Dart-Code.flutter
code --install-extension Dart-Code.dart-code
```

**Android Device Setup:**
1. Enable **Developer Options** on your Android device:
   - Go to Settings → About Phone
   - Tap "Build Number" 7 times
2. Enable **USB Debugging**:
   - Go to Settings → Developer Options
   - Enable "USB Debugging"
3. Connect device via USB
4. Authorize the computer when prompted on device

**ADB (Android Debug Bridge) Verification:**
```bash
# Check if ADB can see your device
adb devices

# You should see your device listed
# If not, try:
adb kill-server
adb start-server
```

### 0.6 Troubleshooting

**Issue: "flutter: command not found"**
- Solution: Verify PATH is set correctly in `~/.bashrc` and reload with `source ~/.bashrc`

**Issue: "Android licenses not accepted"**
- Solution: Run `flutter doctor --android-licenses` and accept all

**Issue: "No devices found"**
- Solution: Enable USB debugging on Android device, reconnect, and authorize computer

**Issue: "Unable to locate Android SDK"**
- Solution: Set `ANDROID_HOME` environment variable to SDK location

### 0.7 System Requirements

**Minimum Requirements:**
- **OS:** Linux (Ubuntu 18.04+, Debian 10+, or similar)
- **Disk Space:** 2.8 GB (Flutter SDK + Android SDK)
- **RAM:** 8 GB minimum (16 GB recommended)
- **Git:** Required for Flutter SDK

**Install Git if needed:**
```bash
sudo apt-get install git
```

---

## Phase 1: Offline Race Status Dashboard (Initial Implementation)

### 1.1 Core Objectives

- ✅ Read-only race status dashboard using existing `query.poll.coordinator.inc` API
- ✅ Simple offline authentication (admin/staff/guest roles - all same experience)
- ✅ Live updates via 1-second polling (matching web interface)
- ✅ WiFi connection to DerbyNet server (air-gapped from internet)
- ✅ **NO changes to existing PHP codebase**
- ✅ Deliverable: Operational APK for testing

### 1.2 Architecture Pattern

**Clean Architecture with Repository Pattern:**
```
Presentation Layer (UI/Widgets)
    ↓
Application Layer (Riverpod State Management)
    ↓
Domain Layer (Models/Entities)
    ↓
Data Layer (Repositories/API Clients)
```

### 1.3 Project Structure

```
lib/
├── core/                          # Core utilities
│   ├── constants/api_endpoints.dart
│   ├── network/dio_client.dart
│   └── errors/failures.dart
│
├── data/                          # Data layer
│   ├── datasources/
│   │   ├── local/secure_storage_source.dart
│   │   └── remote/
│   │       ├── auth_api_source.dart
│   │       └── race_api_source.dart
│   ├── models/race/               # JSON models
│   │   ├── coordinator_poll_response.dart
│   │   ├── current_heat_model.dart
│   │   ├── racer_model.dart
│   │   ├── timer_state_model.dart
│   │   └── race_integrity_model.dart
│   └── repositories/
│       └── race_repository_impl.dart
│
├── domain/                        # Business logic
│   ├── entities/
│   └── repositories/race_repository.dart
│
└── presentation/                  # UI layer
    ├── providers/                 # Riverpod providers
    │   ├── auth/auth_provider.dart
    │   └── race/race_poll_provider.dart
    ├── screens/
    │   ├── auth/
    │   │   ├── server_config_screen.dart
    │   │   └── login_screen.dart
    │   └── dashboard/
    │       ├── dashboard_screen.dart
    │       └── widgets/
    │           ├── current_heat_card.dart
    │           ├── racer_lineup_card.dart
    │           ├── timer_status_card.dart
    │           └── connection_indicator.dart
    └── routes/app_router.dart
```

### 1.4 Key Dependencies

```yaml
dependencies:
  flutter_riverpod: ^2.5.1          # State management
  riverpod_annotation: ^2.3.5
  go_router: ^14.0.2                # Navigation
  dio: ^5.4.3+1                     # HTTP client
  flutter_secure_storage: ^9.0.0    # Secure credential storage
  shared_preferences: ^2.2.3        # App preferences
  connectivity_plus: ^6.0.1         # Network checking
  json_annotation: ^4.9.0           # JSON serialization
  freezed_annotation: ^2.4.1        # Immutable models
  logger: ^2.2.0                    # Logging
```

### 1.5 Authentication Strategy (Offline-First)

**Authentication Flow:**
1. User enters DerbyNet server URL (e.g., `http://192.168.100.10`)
2. Server URL stored in `SharedPreferences`
3. User enters credentials (username/password)
4. POST to `{server-url}/action.php?action=role.login`
5. Extract `PHPSESSID` cookie from response
6. Store credentials in `flutter_secure_storage` (encrypted)
7. Store session cookie in secure storage
8. All subsequent API calls include session cookie in headers

**Security Implementation:**
- Credentials encrypted at rest using platform keychains (Android Keystore)
- Session tokens stored in `flutter_secure_storage` (not SharedPreferences)
- No cloud services or internet connectivity required
- Dio interceptor adds session cookie to all requests automatically

**Reference:** [Flutter Security Best Practices](https://www.dectac.com/blog/flutter-security-best-practices-protecting-your-app-in-2025)

### 1.6 Data Models - Coordinator Poll Response

The app polls `/action.php?query=poll.coordinator&roundid=X&heat=Y` every 1 second.

**Response Structure (based on `/website/ajax/query.poll.coordinator.inc`):**

```json
{
  "current-heat": {
    "now_racing": bool,
    "classid": int,
    "roundid": int,
    "heat": int,
    "number-of-heats": int,
    "class": string
  },
  "racers": [{
    "lane": int,
    "racerid": int,
    "name": string,
    "carname": string,
    "carnumber": string,
    "finishtime": string,
    "finishplace": int
  }],
  "timer-state": {
    "lanes": int,
    "state": string,
    "timers": [{...}],
    "health_status": string,
    "health_message": string
  },
  "heat-results": [{...}],
  "classes": [{...}],
  "rounds": [{...}],
  "race-integrity": {
    "status": "ok" | "warn" | "error",
    "code": string,
    "message": string
  }
}
```

All models use `freezed` for immutability and `json_serializable` for JSON parsing.

### 1.7 State Management - Polling Architecture

**Race Polling Provider (Riverpod):**
```dart
@riverpod
class RacePoll extends _$RacePoll {
  Timer? _pollTimer;

  @override
  RaceState build() {
    _startPolling(); // Auto-start on creation
    return const RaceState.loading();
  }

  void _startPolling() {
    _pollTimer = Timer.periodic(
      const Duration(seconds: 1),
      (_) => _poll(),
    );
  }

  Future<void> _poll() async {
    final result = await repository.pollCoordinator();
    result.fold(
      (failure) => state = RaceState.error(failure.message),
      (data) => state = RaceState.loaded(data),
    );
  }
}
```

**Benefits:**
- Automatic polling on screen load
- Lifecycle management (stops when disposed)
- Error handling with fallback to cached state
- Connection status indicators

**Reference:** [Flutter Offline-First Architecture](https://docs.flutter.dev/app-architecture/design-patterns/offline-first)

### 1.8 Dashboard UI Components

**Main Dashboard Screen:**
- App bar with connection status indicator
- Scrollable content with refresh indicator
- Race integrity warning banner (if issues detected)
- Current heat card (heat number, round, racing status)
- Racer lineup card (lane assignments, car numbers, finish times)
- Timer status card (health status, online timers, individual timer states)
- Heat results card (times, speeds, placements)

**Visual Design Priorities:**
- Clear status indicators (green/orange/red for connection, timer health)
- Lane color coding for easy identification
- Prominent display of racing/paused state
- Real-time updates without flickering

### 1.9 Critical Implementation Files

**Files to Create (in priority order):**

1. **Core Infrastructure:**
   - `lib/main.dart` - App entry point
   - `lib/core/network/dio_client.dart` - HTTP client with interceptors
   - `lib/data/datasources/local/secure_storage_source.dart` - Credential storage

2. **Data Models:**
   - `lib/data/models/race/coordinator_poll_response.dart`
   - `lib/data/models/race/current_heat_model.dart`
   - `lib/data/models/race/racer_model.dart`
   - `lib/data/models/race/timer_state_model.dart`

3. **Repositories:**
   - `lib/domain/repositories/race_repository.dart` (interface)
   - `lib/data/repositories/race_repository_impl.dart`
   - `lib/data/datasources/remote/race_api_source.dart`

4. **State Management:**
   - `lib/presentation/providers/race/race_poll_provider.dart`
   - `lib/presentation/providers/auth/auth_provider.dart`

5. **UI Screens:**
   - `lib/presentation/screens/auth/server_config_screen.dart`
   - `lib/presentation/screens/auth/login_screen.dart`
   - `lib/presentation/screens/dashboard/dashboard_screen.dart`
   - Dashboard widget components (heat card, lineup card, timer card)

**Critical PHP Files to Reference (DO NOT MODIFY):**
- `/website/ajax/query.poll.coordinator.inc` - API endpoint structure
- `/website/ajax/action.role.login.inc` - Authentication endpoint
- `/website/inc/json-timer-state.inc` - Timer state logic
- `/website/inc/json-current-racers.inc` - Racer data structure

### 1.10 Build and Deployment

**Development Setup:**
```bash
flutter create soapbox_derby_app
cd soapbox_derby_app
flutter pub add flutter_riverpod dio flutter_secure_storage go_router
flutter pub add --dev build_runner json_serializable freezed
flutter pub run build_runner build
flutter run
```

**Build APK:**
```bash
# Debug build for testing
flutter build apk --debug

# Release build for production
flutter build apk --release
```

**Testing Strategy:**
- Unit tests for repositories and API sources
- Widget tests for UI components
- Integration tests for full authentication and polling flow

---

## Phase 2: Cloud Migration (Future)

### 2.1 Migration Overview

**Objective:** Add cloud-based deployment for online audience access while maintaining backward compatibility with local mode.

**Key Changes:**
- Add Firebase backend (Authentication, Realtime Database, Cloud Functions)
- Implement SSO (Google, Facebook) via Firebase Auth
- Create cloud sync service (DerbyNet server → Firebase)
- Support dual-mode operation (local vs cloud)

### 2.2 Architecture Strategy

**Environment-Based Configuration:**
```dart
enum AppEnvironment {
  local,   // Phase 1: Direct server connection
  cloud,   // Phase 2+: Firebase backend
}
```

**Dual Repository Pattern:**
- Abstract `RaceRepository` interface remains unchanged
- `LocalRaceRepository` - Direct DerbyNet API calls (Phase 1)
- `CloudRaceRepository` - Firebase Realtime Database (Phase 2+)
- Provider switches based on environment configuration

### 2.3 Firebase Implementation

**Backend Components:**
1. **Firebase Authentication:** SSO with Google/Facebook
2. **Realtime Database:** Live race data synced from DerbyNet
3. **Cloud Functions:** Sync service polling DerbyNet server and pushing to Firebase
4. **Cloud Messaging:** Foundation for push notifications (Phase 4)

**Database Schema:**
```
/races/{raceId}/
  - currentHeat (coordinator poll data)
  - racers
  - results

/users/{userId}/
  - profile
  - preferences
```

**Migration Path:**
- All Phase 1 code remains functional
- New cloud providers added alongside local providers
- Feature flags control which mode is active
- Users can switch between local (on-site) and cloud (remote viewing)

**Reference:** [Firebase Authentication Flutter Guide](https://firebase.flutter.dev/docs/auth/social/)

### 2.4 SSO Implementation

**Google Sign-In:**
```dart
Future<void> loginWithGoogle() async {
  final googleUser = await GoogleSignIn().signIn();
  final googleAuth = await googleUser!.authentication;
  final credential = GoogleAuthProvider.credential(
    accessToken: googleAuth.accessToken,
    idToken: googleAuth.idToken,
  );
  await FirebaseAuth.instance.signInWithCredential(credential);
}
```

**Facebook Sign-In:**
- Install `flutter_facebook_auth` package
- Configure Facebook SDK for Android
- Integrate with Firebase Auth

**Additional Dependencies:**
```yaml
dependencies:
  firebase_core: ^2.24.0
  firebase_auth: ^4.15.0
  google_sign_in: ^6.1.6
  flutter_facebook_auth: ^6.0.3
  firebase_database: ^10.4.0
```

**Reference:** [Federated Identity & Social Sign-In](https://firebase.google.com/docs/auth/flutter/federated-auth)

---

## Phase 3: Race Results & Upcoming Heats (Future)

### 3.1 Objectives

- Display race outcomes and times for each racer and heat
- Show scheduled racers coming up in next heats
- Historical results browsing

### 3.2 New API Endpoints to Integrate

**Existing DerbyNet Endpoints:**
- `query.poll.ondeck` - Upcoming racers in next heats
- `query.racer.results` - Individual racer's historical results
- `query.award.list` - Award standings

### 3.3 UI Enhancements

**New Screens:**
- Results browser (by class, round, racer)
- Upcoming heats preview
- Award standings

---

## Phase 4: Individual Racer Tracking & Push Notifications (Future)

### 4.1 Objectives

- Link app users to specific racers
- Track individual racer's heat position and results
- Push notifications when cart should be in position

### 4.2 Implementation Strategy

**User-Racer Mapping:**
```dart
class RacerMapping {
  final String userId;
  final int racerid;

  Future<List<Heat>> getUpcomingHeats();
  Future<List<RaceResult>> getResults();
}
```

**Push Notification Types:**
1. **Heat Reminder:** "Your heat is coming up in 3 heats"
2. **Position Alert:** "Your cart should be in position now"
3. **Results Posted:** "Your race results are available"

**Implementation:**
- Firebase Cloud Messaging (FCM)
- Cloud Functions monitor race progression
- Schedule notifications based on heat advancement
- Topic subscriptions per racer (`racer_{racerid}`)

**Additional Dependencies:**
```yaml
dependencies:
  firebase_messaging: ^14.7.6
  flutter_local_notifications: ^16.3.0
```

**Reference:** [Mastering Push Notifications in Flutter (2025)](https://medium.com/@AlexCodeX/mastering-push-notifications-in-flutter-a-complete-2025-guide-to-firebase-cloud-messaging-fcm-589e1e16e144)

---

## Development Timeline Estimate

### Phase 1 (Immediate):
- **Week 1-2:** Project setup, core infrastructure, data models
- **Week 2-3:** Authentication, repository implementation
- **Week 3-4:** Dashboard UI, polling integration
- **Week 4:** Testing, bug fixes, APK build
- **Deliverable:** Working Android APK with offline authentication and live race dashboard

### Phase 2 (Future):
- **Week 1-2:** Firebase setup, cloud functions, database schema
- **Week 2-3:** SSO implementation (Google, Facebook)
- **Week 3-4:** Cloud repository, environment switching
- **Week 4:** Testing, deployment
- **Deliverable:** Cloud-hosted app with SSO, supporting 100-500 users

### Phase 3 (Future):
- **Week 1-2:** Results browser, upcoming heats UI
- **Deliverable:** Enhanced dashboard with historical data

### Phase 4 (Future):
- **Week 1-2:** User-racer mapping, FCM integration
- **Week 2-3:** Notification scheduling logic
- **Deliverable:** Personalized racer tracking with push notifications

---

## Success Criteria

### Phase 1:
- ✅ APK installs and runs on Android devices
- ✅ Successfully authenticates against DerbyNet server on local network
- ✅ Displays real-time race status with 1-second polling
- ✅ Shows current heat, racer lineup, timer status
- ✅ No modifications to existing PHP codebase
- ✅ Works offline (air-gapped from internet)

### Phase 2:
- ✅ Users can sign in with Google/Facebook accounts
- ✅ App supports 100-500 concurrent users
- ✅ Cloud deployment accessible via internet
- ✅ Maintains backward compatibility with local mode

### Phase 3:
- ✅ Users can browse race results
- ✅ Upcoming heats preview displayed

### Phase 4:
- ✅ Users can link to their racers
- ✅ Personalized race tracking dashboard
- ✅ Push notifications delivered reliably

---

## Risk Mitigation

### Technical Risks:

1. **Session Cookie Compatibility:** DerbyNet PHP sessions may have quirks
   - **Mitigation:** Thorough testing with actual server, capture network traffic to debug

2. **Polling Performance:** 1-second polling may drain battery
   - **Mitigation:** Implement adaptive polling (slow down when backgrounded), battery optimization

3. **JSON Model Mismatches:** API response structure may vary
   - **Mitigation:** Comprehensive error handling, fallback to safe defaults

4. **Firebase Costs:** Cloud hosting may exceed budget at scale
   - **Mitigation:** Implement rate limiting, caching, monitor usage closely

### Deployment Risks:

1. **Network Configuration:** Users may struggle with server URL setup
   - **Mitigation:** Auto-discovery via mDNS/Bonjour, QR code scanning for server config

2. **APK Distribution:** No Google Play Store initially
   - **Mitigation:** Direct APK download, consider F-Droid for open-source distribution

---

## References & Resources

### Official Documentation:
- [Flutter App Architecture Guide](https://docs.flutter.dev/app-architecture/guide)
- [Offline-First Support in Flutter](https://docs.flutter.dev/app-architecture/design-patterns/offline-first)
- [Firebase Flutter Documentation](https://firebase.flutter.dev/)

### Security Best Practices:
- [Flutter Security Best Practices 2025](https://www.dectac.com/blog/flutter-security-best-practices-protecting-your-app-in-2025)
- [Securely Storing JWTs in Flutter](https://carmine.dev/posts/flutterwebjwt/)
- [OWASP Top 10 for Flutter](https://docs.talsec.app/appsec-articles/articles/owasp-top-10-for-flutter-m3-insecure-authentication-and-authorization-in-flutter)

### State Management:
- [Riverpod Documentation](https://riverpod.dev/)

### Push Notifications:
- [Firebase Cloud Messaging for Flutter](https://firebase.google.com/docs/cloud-messaging/flutter/client)
- [Complete FCM Guide 2025](https://medium.com/@AlexCodeX/mastering-push-notifications-in-flutter-a-complete-2025-guide-to-firebase-cloud-messaging-fcm-589e1e16e144)

### Authentication:
- [Firebase Social Authentication](https://firebase.flutter.dev/docs/auth/social/)
- [Federated Identity Guide](https://firebase.google.com/docs/auth/flutter/federated-auth)

---

## Next Steps

1. **Create Flutter project** with initial dependencies
2. **Set up project structure** following clean architecture
3. **Implement core infrastructure** (Dio client, secure storage)
4. **Build data models** for coordinator poll response
5. **Create repository layer** with API integration
6. **Implement authentication flow** (server config → login → dashboard)
7. **Build dashboard UI** with polling integration
8. **Test on physical Android device** connected to DerbyNet server
9. **Build release APK** for field testing

**First Milestone:** Working Phase 1 APK ready for testing at next race event.

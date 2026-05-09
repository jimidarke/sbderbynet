# Flutter Mobile App

## Purpose

Android mobile application for soapbox derby event management. Currently in Phase 1 (infrastructure foundation) — architecture skeleton, dependencies, and project structure are in place but no feature implementation yet.

## How It Fits

Will connect to the DerbyNet PHP app via REST API for race data, schedules, and results. Intended as a companion app for race-day participants and officials.

## Key Files

- `derbyapp/` — Flutter project root
- `STATUS.md` — Development status (Phase 1 complete as of Dec 2025)
- `PROGRESS.md` — Detailed progress tracking with file structure

## Tech Stack

- **Framework**: Flutter (Android-only target)
- **State Management**: Riverpod
- **Navigation**: Go Router
- **HTTP**: Dio with interceptors
- **Models**: Freezed (code generation)
- **Package**: `com.sbderbynet.soapbox_derby_app`

## Dependencies

- Flutter SDK
- Android SDK
- Dependencies declared in `derbyapp/pubspec.yaml`

## Common Tasks

- **Run**: `cd derbyapp && flutter run`
- **Build**: `flutter build apk`
- **Generate models**: `flutter pub run build_runner build`

## Gotchas

- **Phase 1 only**: Infrastructure skeleton — no working features yet
- **Next steps**: Failure handling, API endpoints, HTTP client interceptors, data models
- **Clean architecture**: Folder structure follows layered architecture pattern

## Related Docs

- [STATUS.md](STATUS.md) — Current development status
- [PROGRESS.md](PROGRESS.md) — Detailed progress and file inventory

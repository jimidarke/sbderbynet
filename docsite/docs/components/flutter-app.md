# Flutter App

Mobile companion app for the cloud twin (audience-facing results, schedules, optionally push notifications). Phase 1 (foundation) complete as of 2025-12-14. **Pre-launch**: not yet user-facing.

Lives at `extras/flutterapp/derbyapp/`. Flutter / Dart.

!!! note "Status snapshot"
    The contents of this page reflect the project state at end-of-Phase-1. Phase 2 (live API integration, screens beyond skeleton) has not started; refresh this page when it does.

---

## Architecture

Clean architecture with three layers under `lib/`:

```
lib/
├── core/                # cross-cutting: config, error handling, network base
├── data/                # API clients, DTOs, repository implementations
├── domain/              # entities, repository interfaces, use-cases
└── presentation/        # screens, widgets, Riverpod providers, routing
```

### Stack

- **State**: Riverpod
- **Navigation**: Go Router
- **HTTP**: Dio (interceptors planned for auth/retry/logging)
- **Models**: Freezed + `json_serializable` (codegen via `build_runner`)
- **Package**: `com.sbderbynet.soapbox_derby_app`

---

## Phase 1 — completed

| Area | Status |
|---|---|
| Project scaffolding, pubspec, build_runner | done |
| Core config / failure types / network base | done |
| Models with Freezed + JSON | done |
| Riverpod provider plumbing | done |
| 3 screens, 4 custom widgets | done |
| 55 Dart files, 3500+ LoC, 0 build errors | done |

---

## Phase 2 — next

- Concrete failure handling (currently scaffolded, not propagated end-to-end)
- API endpoint coverage (results, standings, schedule, racer detail)
- Dio interceptors (auth, retry, observability)
- Real data models matched to cloud-twin endpoints
- Live screens replacing the skeleton placeholders

---

## Common tasks

```bash
flutter pub get
flutter pub run build_runner watch --delete-conflicting-outputs
flutter run -d <device>
flutter test
```

---

## Files of note

- `extras/flutterapp/derbyapp/README.md` — project setup
- `extras/flutterapp/derbyapp/IMPLEMENTATION_PLAN.md` — detailed phase plan
- `extras/flutterapp/PROGRESS.md` — task-level tracking
- `extras/flutterapp/STATUS.md` — high-level snapshot

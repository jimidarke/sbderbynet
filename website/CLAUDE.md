# DerbyNet PHP Web Application

## Purpose

Central web UI for race management — registration, scheduling, race operations, results, awards, and kiosk displays. This is the original DerbyNet PHP application, extensively modified for soapbox derby support with elimination tournaments, broadcast messaging, and enhanced coordinator controls.

## How It Fits

This is the core of the system. The Race Server (`extras/soapbox/infra/server/`) bridges hardware to this app via HTTP API and direct SQLite writes. All kiosk displays, coordinator pages, and admin tools are served from here. The database (SQLite) is the single source of truth for race state.

## Key Files

- `action.php` — AJAX dispatcher. Routes `action=X` to `ajax/action.X.inc`, enforces permissions, returns JSON
- `coordinator.php` — Race coordinator interface (heat management, timer status, broadcast messaging)
- `index.php` — Main dashboard entry point
- `elimination-config-editor.php` — Tournament format configuration UI
- `inc/elimination-config.inc` — JSON-based tournament format management
- `inc/schedule_one_round.inc` — Core scheduling algorithms (rotation, ordered, elimination)
- `inc/racing-state.inc` — Race state management (NowRacingState)
- `inc/heartbeat-config.inc` — Centralized timeout constants (cross-component alignment)
- `inc/error-codes.inc` — Standardized error code registry

## File Naming Conventions

- **Actions**: `ajax/action.{entity}.{operation}.inc` (e.g., `action.award.edit.inc`)
- **Queries**: `ajax/query.{entity}.{operation}.inc` (e.g., `query.poll.coordinator.inc`)
- **Includes**: `inc/{feature}.inc` — shared PHP libraries
- **JavaScript**: `js/{feature}.js` — client-side behavior
- **CSS**: `css/{feature}.css` — stylesheets
- **Kiosks**: `kiosks/{name}.kiosk` — kiosk display templates

## Dependencies

- PHP 7.0+ with PDO/SQLite3
- jQuery, jQuery UI, Dropzone (file upload), Jcrop (image cropping)
- No composer — all dependencies vendored

## Common Tasks

- **Run tests**: `cd testing/ && ./test-basic-racing.sh`
- **Add an action**: Create `ajax/action.{name}.inc`, handle via `action.php` dispatch
- **Add a query**: Create `ajax/query.{name}.inc`, returns JSON
- **Build**: `ant generated` (generates version info, aggregated files)

## Gotchas

- **Scheduling engine parameter fix**: `n_times_per_lane` was misinterpreted — `races_per_racer: 3` means `n_times_per_lane = 1` (1 per lane x 3 lanes). See `action.schedule.generate.inc`
- **Database-required actions**: Most actions need a database connection. Files with `.nodata` suffix bypass this
- **Round naming**: All round names MUST start with a number for proper sequencing
- **Tournament configs**: JSON files in `inc/elimination-configs/` — hardcoded formats, not UI-editable at runtime
- **Heat generation weights**: `avoid_consecutive=5000, group_weighted_cars=100, avoid_same_lane=200, heat_counts=10`

## Related Docs

- [docs/ROUNDSETUP.md](../docs/ROUNDSETUP.md) — Round system and database schema
- [docs/DATABASE_SCHEMA_VALIDATION.md](../docs/DATABASE_SCHEMA_VALIDATION.md) — Elimination tournament schema
- [docs/ELIMINATION_CONFIG_VALIDATION.md](../docs/ELIMINATION_CONFIG_VALIDATION.md) — Config editor field mappings
- [docs/COORDINATOR_POLL_API.md](../docs/COORDINATOR_POLL_API.md) — Coordinator polling endpoint spec
- [docs/RACINGSTATEENGINE.md](../docs/RACINGSTATEENGINE.md) — Cross-layer state machine documentation
- [inc/elimination-configs/README.md](inc/elimination-configs/README.md) — Tournament configuration framework

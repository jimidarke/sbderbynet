# Web App

The PHP web application is the central UI and the source of truth for the race database. Forked from DerbyNet, extensively modified for soapbox derby with elimination tournaments, broadcast messaging, pull-forward, and enhanced coordinator controls.

Lives at `website/`. PHP 7.0+ with PDO/SQLite; jQuery / jQuery UI / Dropzone / Jcrop in the front end. No Composer — all dependencies vendored.

---

## What it does

- Registration, scheduling, race operations, results, awards.
- Coordinator pages for heat management and timer status.
- Kiosk pages for displays.
- Admin / setup tools.
- AJAX API used by the race server, virtual hardware, and the Flutter app.

The race server (`extras/soapbox/infra/server/`) bridges hardware to this app via the HTTP API and direct SQLite writes. All kiosk displays, coordinator pages, and admin tools are served from here.

---

## Key files

- `action.php` — AJAX dispatcher. Routes `action=X` to `ajax/action.X.inc`, enforces permissions, returns JSON.
- `coordinator.php` — Race coordinator interface (heat management, timer status, broadcasts).
- `index.php` — Main dashboard entry point.
- `elimination-config-editor.php` — Tournament format configuration UI.
- `inc/elimination-config.inc` — JSON-based tournament format management.
- `inc/schedule_one_round.inc` — Core scheduling algorithms (rotation, ordered, elimination).
- `inc/racing-state.inc` — Race state management (`NowRacingState`).
- `inc/heartbeat-config.inc` — Centralised timeout constants (cross-component alignment — see [Race State Engine](../architecture/race-state-engine.md)).
- `inc/error-codes.inc` — Standardised error code registry.
- `inc/data.inc` — DB bootstrap; defines `is_cloud_mode()`, `is_cloud_public_mode()`, `cloud_last_sync_utc()`.
- `virtual/` — Cloud-only browser virtual hardware pages (finish/start timer, LED sign, display, control panel). Gated by `virtual/_guard.inc` (cloud-mode + coordinator permission). `B_`-prefixed hwids; never deployed for race-day use. See [Phone Usage](../operations/phone-usage.md) for why these are desktop-only.

---

## Naming conventions

- **Actions**: `ajax/action.{entity}.{operation}.inc` (e.g. `action.award.edit.inc`).
- **Queries**: `ajax/query.{entity}.{operation}.inc` (e.g. `query.poll.coordinator.inc`).
- **Includes**: `inc/{feature}.inc` — shared PHP libraries.
- **JavaScript**: `js/{feature}.js` — client-side behaviour.
- **CSS**: `css/{feature}.css`.
- **Kiosks**: `kiosks/{name}.kiosk` — display templates.

---

## Common tasks

```bash
# Run the integration tests
cd testing/ && ./test-basic-racing.sh

# Build version metadata
ant generated
```

- **Add an action**: create `ajax/action.{name}.inc`; the dispatcher in `action.php` finds it.
- **Add a query**: create `ajax/query.{name}.inc`; returns JSON.

---

## Gotchas worth knowing

- **Scheduling parameter trap**: `n_times_per_lane` is misnamed in upstream. `races_per_racer: 3` means `n_times_per_lane = 1` (one per lane × three lanes). See `action.schedule.generate.inc`.
- **Database-required actions**: most actions need a DB connection. Files with `.nodata` suffix bypass it.
- **Round naming**: round names must start with a number for proper sequencing.
- **Tournament configs**: hardcoded JSON in `inc/elimination-configs/`, not runtime-editable.
- **Heat-generation weights**: `avoid_consecutive=5000, group_weighted_cars=100, avoid_same_lane=200, heat_counts=10`. Pull-forward intentionally violates these — see [Pull-Forward](../features/pull-forward.md).

See also: [Round Setup](../features/round-setup.md), [Elimination Tournaments](../features/elimination-tournaments.md), [Coordinator Poll API](../reference/coordinator-poll-api.md).

# Ad-Hoc Racing Mode

Casual "come-as-you-are" racing on the real track. The race coordinator types
whichever pinnies are at the line and picks **each pinny's age group**, locks in
the heat, and the real timers record the run. A pinny's **single best time** is
its score (kids may run once or many times). Results are compared **like-to-like,
per age group** — mixed ages may share a heat, but the leaderboard shows the
**top 3 per age group**.

Ad-hoc racing is **roster-less and schedule-less**: there is no roster to load and
no schedule to generate. A run is stored as one self-describing row, so a drop-in
kid who never pre-registered can still race.

Ad-hoc results live in a **separate SQLite file** (`adhoc.sqlite3`) so casual fun
runs never touch the official event database.

## How isolation works (and why it no longer corrupts data)

On the race-day Pi the whole rig (PHP, race server, kiosks) opens **one** SQLite
file, chosen by a tiny filesystem **marker**:

```
/var/lib/derbynet/active-db        <- text file: one absolute *.sqlite3 path
  (absent / invalid)               -> official derbynet.sqlite3   (fail-safe)
  /…/adhoc.sqlite3                  -> ad-hoc mode
```

Turning ad-hoc mode **on** (`adhoc_build()` in `inc/adhoc.inc`):

1. **Builds `adhoc.sqlite3` FRESH from the schema** — the same `include(schema.inc)`
   path `create_tenant()` uses. It does **not** copy the live official file.
   *(The old design `@copy()`-ed a hot WAL database mid-write, which produced a
   "database disk image is malformed" file — that was the corruption bug.)*
2. Takes a **read-only snapshot** of just the reference data it needs from official
   — the age-group `Classes` and the display/config `RaceInfo` (lane_count, labels,
   time format) — in one read transaction, then seeds them into the fresh DB.
3. Creates one synthetic **"Ad-Hoc Open"** class + round to hold the open racing
   pool (this is plumbing, **not** a schedule — no heats are pre-generated).
4. Stamps `RaceInfo`: `adhoc-mode=1`, `scoring=2` (best single time), the round/
   class ids. The stamp is how any process knows the file it opened is ad-hoc.
5. Flips the marker to `adhoc.sqlite3` **atomically** (`dn_set_active_db()` writes
   a temp file + `fsync` + `rename`). The very next request opens the ad-hoc DB.

Turning ad-hoc mode **off** stops racing and clears the marker → back to official.
Every ad-hoc write also re-checks `adhoc-mode=1` in the *live* DB, a second
interlock so a heat can never be injected into the official database.

## Operator workflow

1. **Main page → "Ad-Hoc Racing"** (coordinator-only button in *During the Race*).
   It builds + switches to the isolated DB and lands you on the coordinator page.
   The button turns into **"Exit Ad-Hoc Racing"** while active.
2. On the coordinator dashboard a red **"AD-HOC RACING ACTIVE"** strip appears and
   an **Ad-Hoc Heat** card. Tap **Set Up Next Group**.
3. In the modal, for each physical lane enter the **pinny** and pick its **age
   group** (leave a lane blank for a bye). Tap **Lock In Heat & Race**.
   - All-or-nothing: an unknown age group, a non-numeric pinny, or the same pinny
     twice aborts the arm so no kid is silently dropped.
   - Physical lane numbers are preserved (cars in lanes 1 & 3 stay 1 & 3).
4. The real timers record the heat exactly as in official racing. After it
   finishes, racing turns off; set up the next group and lock in again. Each lock
   is a new heat, so a pinny can run repeatedly.
5. **Exit Ad-Hoc** (strip button or the main-menu button) returns the rig to the
   official DB. Official standings are untouched.

The public leaderboard is the **`adhoc-leaderboard`** kiosk: best single time per
pinny, grouped by age group, top 3 each, DNF excluded, **pinny + time only —
never names**. It shows "not currently active" when ad-hoc mode is off.

## Data model (roster-less)

`RaceChart` carries two nullable columns (schema **v18**), NULL for normal
scheduled racing:

| Column | Meaning |
|--------|---------|
| `display_pinny` | the raw pinny the coordinator typed (e.g. `"42"`) |
| `agegroup_classid` | the age group they picked (→ `Classes.classid`) |

One recorded run = one `RaceChart` row `(roundid, heat, lane, racerid NULL,
display_pinny, agegroup_classid, finishtime)`. No `RegistrationInfo`/`Roster` row
is needed. Ranking groups by `agegroup_classid` with `MIN(finishtime)` — best
single time, order-independent (a later slow run can never overwrite a faster
best). See `inc/adhoc-standings.inc`.

## Timer integration (no firmware/Python change)

`inc/json-current-racers.inc` `LEFT JOIN`s the roster (so roster-less rows survive)
and emits `carnumber = COALESCE(RaceChart.display_pinny, RegistrationInfo.carnumber)`.
The race server already reads that `carnumber` field as the lane pinny
(`derbyapi.py` aliases it to `racerid`), so finish-timer assignment, the start
gate, and the `FINISHED` result write all work unchanged. `write-heat-results.inc`
is lane-keyed and racerid-independent, so results land on the right row with no
racer.

## Race server (Python)

**Leave `DERBYNET_DB_PATH` UNSET on the Pi** (its current state — enforced by a
comment in `derbyrace.service`). The server then runs in HTTP-API mode and routes
every read/write through PHP, which resolves the marker per request and so follows
ad-hoc mode correctly. If `DERBYNET_DB_PATH` is ever set, the server caches one
SQLite connection at startup and never re-resolves the marker — ad-hoc heats would
be written into the official DB and corrupt it. Re-enable only after `derbyRace.py`
is taught to poll the marker and reconnect on change.

## Deployment checklist

Everything ships with the code **except two one-time manual steps on each Pi**
(marked ⚠️), unchanged from before. Nothing needs a new library or composer.

### Code (deploys normally via image/rsync/git)
- `website/inc/{db-marker,adhoc,adhoc-standings}.inc`
- `website/ajax/action.adhoc.{mode,heat}.inc`, `website/ajax/query.poll.coordinator.inc`
- `website/index.php`, `website/coordinator.php`, `website/js/coordinator-adhoc.js`
- `website/sql/sqlite/schema.inc` + `website/sql/sqlite/update-schema.inc` (schema **v18**)
- `website/kiosks/adhoc-leaderboard.kiosk`
- `testing/test-adhoc-rosterless.php` (offline test)

### Schema upgrade
Fresh DBs (image setup) get the v18 columns directly from `schema.inc`. **Existing
event DBs** gain them via the idempotent `ALTER TABLE` in `update-schema.inc` when
the schema upgrade runs — confirm the upgrade has applied before using ad-hoc
(`SELECT 1 FROM pragma_table_info('RaceChart') WHERE name='display_pinny'`).

### ⚠️ 1. Make `config-database.inc` marker-aware (Pi-local, gitignored)
`website/local/config-database.inc` is not version-controlled, so it must read the
marker. Required form (resolves the active DB, exposes `$official_db_path`):

```php
<?php
$official_db_path = '/var/lib/derbynet/2025/test2/derbynet.sqlite3'; // your event DB
$GLOBALS['official_db_path'] = $official_db_path;
$db_path = $official_db_path;
$marker_inc = dirname(__FILE__) . '/../inc/db-marker.inc';
if (@is_file($marker_inc)) {
  require_once($marker_inc);
  if (function_exists('dn_resolve_active_db')) {
    $db_path = dn_resolve_active_db($official_db_path);
  }
}
$homedir = dirname($db_path);
$db = new PDO('sqlite:' . $db_path, '', '', array());
$db->setAttribute(PDO::ATTR_CASE, PDO::CASE_LOWER);
?>
```
It fail-safes to official, so making this change while ad-hoc is unused is harmless.

### ⚠️ 2. Create the marker file, writable by the web user
```sh
sudo install -o derbynet -g www-data -m 0664 /dev/null /var/lib/derbynet/active-db
```
(Default path `/var/lib/derbynet/active-db`; override with `DERBYNET_ACTIVE_DB_MARKER`.)

### Already true in any working install (verify, don't re-do)
- **PHP `pdo_sqlite`** (the test also needs it in the CLI).
- **Event directory writable by the web user** — `adhoc_build()` creates
  `adhoc.sqlite3` beside the official DB (same dir DerbyNet already writes to).
- **`RaceInfo.lane_count` set** and real finish timers on the track.
- **Race-control permission** (`CONTROL_RACE_PERMISSION`) for the operator.

## Cloud twin — DEFERRED (follow-up)

The data model is cloud-ready (ordinary tables), but ad-hoc results do **not**
currently reach the cloud twin: `cloud-sync.sh` auto-detects and pushes
`derbynet.sqlite3` **by name**, and it does not honor the active-db marker — so
during ad-hoc mode the cloud keeps showing the (frozen) official DB. Surfacing
ad-hoc on the twin needs `cloud-sync.sh` to push the **marker-resolved active DB**
(so the twin mirrors whatever the rig is live on). That is an **outward-facing**
change (it changes what public spectators see during ad-hoc, and the public-stats
schedule pages have no schedule in ad-hoc mode), so it is intentionally **not** in
this change. Pi-local ad-hoc is fully functional without it.

## Files

| File | Purpose |
|------|---------|
| `inc/db-marker.inc` | Resolve/set the active-DB marker (allowlisted, atomic, fail-safe) |
| `inc/adhoc.inc` | `adhoc_build()` (fresh-from-schema), `adhoc_age_groups()`, `adhoc_arm_heat()`, mode/path helpers |
| `inc/adhoc-standings.inc` | Roster-less top-N-per-age-group best-time query + renderer |
| `ajax/action.adhoc.mode.inc` | Turn ad-hoc mode on/off (build + flip marker) |
| `ajax/action.adhoc.heat.inc` | Lock in a heat from coordinator pinny + age-group entry |
| `ajax/query.poll.coordinator.inc` | Adds `active_db_mode` so the dashboard flags ad-hoc |
| `inc/json-current-racers.inc` | LEFT JOIN + `COALESCE(display_pinny, carnumber)` for the timer path |
| `index.php` | Coordinator-gated "Ad-Hoc Racing" enable/exit button |
| `coordinator.php`, `js/coordinator-adhoc.js` | AD-HOC strip, Ad-Hoc Heat card + lock-in modal |
| `kiosks/adhoc-leaderboard.kiosk` | Public per-age-group best-times kiosk |
| `sql/sqlite/schema.inc`, `update-schema.inc` | `RaceChart.display_pinny` + `agegroup_classid` (v18) |

## Verification

- **`php testing/test-adhoc-rosterless.php`** — offline functional test (no
  server/Docker; needs PHP CLI with `pdo_sqlite`). Proves `adhoc_build()` is
  fresh-not-copied and roster-less, the new columns, atomic marker, roster-less
  arm (incl. bye-lane physical-lane preservation + all-or-nothing validation),
  per-age-group `MIN` standings (DNF excluded, top-N, no names), and official-DB
  isolation. Exit 0 = pass, 2 = skipped (no driver).
- `php -l` on all PHP files; `node --check website/js/coordinator-adhoc.js`.
- End-to-end with **faked timers** (local Docker, no hardware): enable from the
  main menu, lock a heat on the coordinator page, then POST
  `action=timer-message&message=STARTED` and `…&message=FINISHED&lane1=…&lane2=…`
  (the exact payload the race server sends) — or use the coordinator Manual
  Results modal — and confirm the leaderboard updates and the official DB is
  unchanged after **Exit Ad-Hoc**.

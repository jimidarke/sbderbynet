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

## Cloud twin — SHIPPED (commit 1192599a, 2026-06-19)

Ad-hoc now reaches the QR-linked spectator pages. `cloud-sync.sh` honors the
active-db marker (same allowlist + fail-safe as `inc/db-marker.inc`), pushing the
marker-resolved `adhoc.sqlite3` while the rig is in ad-hoc mode. `render.sh`
auto-detects `RaceInfo.adhoc-mode` and rebuilds the public surface roster-less:

- **Recent races** (schedule landing): every run since start, newest first.
- **Leaderboard** (recent.html): best single time, top 3 per age group
  (mirrors `inc/adhoc-standings.inc`).
- **My Races**: one page per captured pinny, built from `display_pinny`.

Nav/title/footer are relabeled ad-hoc-only via template placeholders; normal
rostered events render byte-identically. Pinny zero-padding is decimal-safe
everywhere (SQLite `printf` for ad-hoc, leading-zero strip for the roster path)
— a bare shell `printf "%04d"` parses leading-zero pinnies as octal and corrupts
`me/<pinny>.html` filenames. **No PII**: pinny + time only, never racer names.
See [PUBLIC_STATS.md](PUBLIC_STATS.md).

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

## Edge cases & hardening backlog (practice-day-default candidate)

Ad-hoc was a success at the 2026-06-20 Friday practice and is a candidate to
become the **default mode for practice days**. The data-isolation design is
solid (separate `adhoc.sqlite3`, atomic marker, fail-safe to official, no PII on
the cloud). The remaining items are **operator-error catches**, not data-safety
bugs — worth hardening before making ad-hoc the default, since practice days mean
frequent mode-switching by less-rehearsed operators. None are shipped yet; each
needs code verification before implementation.

| # | Case | Status today | Risk | Suggested hardening | Effort |
|---|------|--------------|------|---------------------|--------|
| 1 | **Enable ad-hoc while an official heat is armed/racing** | GAP — `action.adhoc.mode.inc` builds + flips the marker unconditionally | Marker flips immediately; the next result write lands in the ad-hoc DB instead of the official heat | Before `adhoc_build()`, refuse (or confirm) if `get_racing_state()` is non-zero or an official round has results | S |
| 2 | **Exit ad-hoc while an ad-hoc heat is armed/racing** | PARTIAL — exit stops racing state but gives no warning | Marker flips back to official; an in-flight ad-hoc heat is orphaned and its timer result is misrouted | In `coordinator-adhoc.js` exit, check poll `NowRacingState`; confirm "A heat is armed — exit anyway?" | M |
| 3 | **Oversized pinny (e.g. `999999999`)** | GAP — server regex `^[0-9]+$` accepts any length | `display_pinny` stored full-width breaks the 4-digit `pinny_display()` assumption on kiosk + cloud | Cap at 4 digits / reject `> 9999` in both `coordinator-adhoc.js` and `adhoc_arm_heat()` | S |
| 4 | **Timer fires for a bye/unknown lane** | GAP — `write-heat-results.inc` silently ignores lanes with no RaceChart row | Silent data loss; operator never learns a time was dropped | Warn (`derby_log_warn`) when a reported lane has no entry for the heat | S |
| 5 | **Same pinny re-entered under a different age group** | PARTIAL — allowed (legit for re-runs), no warning | Splits one car's results across two age-group leaderboards | On arm, warn if `display_pinny` previously raced under a different `agegroup_classid` | M |
| 6 | **Duplicate POST / browser refresh mid-heat-setup** | PARTIAL — arm increments the heat counter, so a re-POST mints a duplicate heat | Stray empty/duplicate heat in the feed | Idempotency token on the heat-setup form, or dedup identical consecutive arms | M |
| 7 | **Pinny collides with a real roster car number** | PARTIAL — roster-less model means no DB conflict, but the same printed number can mean two cars | Operator/ spectator confusion if a roster pinny re-enters as an ad-hoc pinny | Optional: warn if `display_pinny` matches any official `RegistrationInfo.carnumber` | S |

**Confirmed already-handled** (no action): non-numeric pinny rejected, `0000`/blank
rejected, leading-zero normalization, duplicate-in-same-heat dedup, byes / fewer
racers than lanes, single-racer heat, zero-racers rejected, DNF excluded from the
leaderboard, ties stably ordered, re-run a heat (reinstate), server restart
mid-ad-hoc (marker + counters persist), kiosk + cloud surfacing, PII scrubbed.

**Recommended order for practice-day-default:** #1 → #3 → #4 first (all small,
high-value safety/clarity catches), then #2 and #5 (operator-confirm polish).

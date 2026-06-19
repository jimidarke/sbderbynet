# Ad-Hoc Racing Mode

Casual "come-as-you-are" racing on the real track. A start-line **marshal** types
(or scans) whichever pinnies are at the line, the system forms that heat on the
fly, the real timers record the run, and a racer's **single best time** is their
score. Kids may run once or many times. The leaderboard shows the **top 3 per age
group**.

Ad-hoc results live in a **separate SQLite file** (`adhoc.sqlite3`) so casual fun
runs never pollute the official event database.

## Requirements & deployment checklist

Everything ships with the code **except two one-time manual steps on each Pi**
(marked ⚠️). Nothing here needs a new library or a composer install.

### Code (deploys normally via image/rsync/git)
- `website/inc/db-marker.inc`, `website/inc/adhoc.inc`, `website/inc/adhoc-standings.inc`
- `website/ajax/action.adhoc.mode.inc`, `website/ajax/action.adhoc.heat.inc`
- `website/adhoc.php`, `website/js/adhoc.js`, `website/css/adhoc.css`
- `website/kiosks/adhoc-leaderboard.kiosk` (auto-discovered by `kiosk.php`; no registration step)
- `testing/test-adhoc-mode.php` (offline test)

### ⚠️ 1. Make `config-database.inc` marker-aware (Pi-local, gitignored)
`website/local/config-database.inc` is **not** version-controlled, so it does **not**
deploy with the code — it must be hand-edited on each Pi to the form in
[Canonical `config-database.inc`](#canonical-config-databaseinc-pi-local-gitignored)
below (reads the marker, exposes `$official_db_path`). It fail-safes to the official
DB, so making this change while ad-hoc is unused is harmless.

### ⚠️ 2. Create the marker file, writable by the web user
The web app (`www-data`) rewrites the marker file's contents; pre-create it so the
parent directory's ownership doesn't matter:
```sh
sudo install -o derbynet -g www-data -m 0664 /dev/null /var/lib/derbynet/active-db
```
(Default path is `/var/lib/derbynet/active-db`; override with the
`DERBYNET_ACTIVE_DB_MARKER` env var if your DBs live elsewhere.)

### Already true in any working DerbyNet install (verify, don't re-do)
- **PHP `pdo_sqlite`** — baseline DerbyNet requirement (the test also needs it in the
  **CLI**: `php -m | grep pdo_sqlite`).
- **Event directory writable by `www-data`** — `adhoc_build()` creates/overwrites
  `adhoc.sqlite3` beside the official DB (same dir DerbyNet already writes its
  `derbynet.sqlite3` + `-wal`/`-shm` to). No extra grant needed.
- **`RaceInfo.lane_count` set** (e.g. 3) and real finish timers on the track — ad-hoc
  uses the identical timer/MQTT path as official racing.
- **Race-control permission** for whoever opens `/adhoc.php` (`CONTROL_RACE_PERMISSION`).

### Race server — no change required
Leave `DERBYNET_DB_PATH` **unset** in `derbyrace.service` (its current state). The
server then routes round/heat reads and result writes through PHP, which honors the
marker. See [Race server](#race-server-python).

## How isolation works

On the race-day Pi the whole rig (PHP, race server, kiosks) opens **one** SQLite
file. Ad-hoc mode re-points that selection at `adhoc.sqlite3` for the session and
back to the official DB afterward, via a tiny filesystem **marker**:

```
/var/lib/derbynet/active-db        <- text file: one absolute *.sqlite3 path
  (absent / invalid)               -> official derbynet.sqlite3   (fail-safe)
  /…/adhoc.sqlite3                  -> ad-hoc mode
```

- `website/inc/db-marker.inc` resolves the marker. It only ever accepts an
  existing `*.sqlite3` file **in the same directory as the official DB**; anything
  malformed/missing resolves back to official. No DB dependency, so it is safe to
  include before `$db` exists.
- `website/local/config-database.inc` reads the marker and also exposes
  `$official_db_path`. PHP opens a fresh connection per request, so a flip takes
  effect on the very next request.
- The ad-hoc DB carries `RaceInfo.adhoc-mode = 1`. Every ad-hoc write action
  refuses unless it sees this flag in the *live* DB — a second interlock so a heat
  can never be injected into the official database.

### Canonical `config-database.inc` (Pi-local, gitignored)

The per-deployment shim must read the marker. The required form:

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
$db_connection_string = 'sqlite:' . $db_path;
$db = new PDO($db_connection_string, '', '', array());
$db->setAttribute(PDO::ATTR_CASE, PDO::CASE_LOWER);
?>
```

The marker file must be writable by the web user (`www-data`) — create it
group-writable (e.g. owned by `derbynet:www-data`, mode `0664`), like the existing
cloud-sync trigger. Override its location in tests with
`DERBYNET_ACTIVE_DB_MARKER`.

## Operator workflow

Open **`/adhoc.php`** on a tablet (needs the race-control permission):

1. **Build & Switch to Ad-Hoc** — rebuilds `adhoc.sqlite3` from the current
   official roster and flips the marker. Only **checked-in** racers
   (`passedinspection = 1`) are loaded; they keep their official pinny.
2. **Enter the 3 pinnies** at the line (Lane 1/2/3) and tap **Arm Heat**. Fewer
   than 3 is fine (bye lanes). An unknown or duplicate pinny aborts the arm so no
   kid is silently dropped.
3. Run the cars — the real timers record the heat exactly as in official racing.
   After the heat finishes, racing turns off automatically; enter the next group
   and **Arm Heat** again. Each arm is a new heat, so kids can run repeatedly.
4. **End & Back to Official** — stops ad-hoc racing and clears the marker. The rig
   is back on the official DB; official standings are untouched.

The public leaderboard is the **`adhoc-leaderboard`** kiosk: best single time per
racer, grouped by age group, top 3 each, DNF excluded. It shows **pinny + age
group only — never names** (public PII rule). It refreshes on the standard kiosk
cadence and shows "not currently active" when ad-hoc mode is off.

### Policy: rebuild each session

"Build & Switch" overwrites `adhoc.sqlite3` every time — a fresh roster mirror
(including new check-ins) and a clean results pool. The file is kept between
sessions but the next build replaces it.

## How it works under the hood

- One synthetic **Ad-Hoc Open** class + one round hold the whole mixed-age racing
  pool. Racing is keyed by `(roundid, heat)`, so the timer flow is unchanged.
- Ranking ignores that synthetic class and groups by each racer's **real**
  `RegistrationInfo.classid` (their age group) via the result's `racerid`.
- Scoring is `RaceInfo.scoring = 2` (`MIN(finishtime)`), the existing best-single-
  time mode.
- Heat formation reuses the pull-forward INSERT pattern; arming reuses
  `set_current_heat()` + `set_racing_state()`. When a heat finishes with no next
  heat pre-scheduled, the normal `advance_heat` path simply turns racing off — the
  marshal's next arm re-enables it.

## Race server (Python)

No race-server change is required on the current Pi image: `derbyrace.service` does
not set `DERBYNET_DB_PATH`, so the server is DB-agnostic — it reads round/heat from
the coordinator poll and writes results via the HTTP API, both of which go through
PHP and therefore honor the marker.

**Deferred enhancement (only if the direct-DB fast path is enabled):** if
`DERBYNET_DB_PATH` is ever set so the server writes SQLite directly, its cached
connection would point at the wrong file after a mode flip. The fix is to have the
server's main loop poll the marker each tick and reconnect on change (close +
reopen `self.db`, reset `roundid/heatid`). Until then, leave `DERBYNET_DB_PATH`
unset so results route through PHP.

## Files

| File | Purpose |
|------|---------|
| `website/inc/db-marker.inc` | Resolve/set the active-DB marker (allowlisted, fail-safe) |
| `website/local/config-database.inc` | Marker-aware DB selection (Pi-local) |
| `website/inc/adhoc.inc` | `adhoc_build()`, path/mode/pinny helpers |
| `website/ajax/action.adhoc.mode.inc` | Turn ad-hoc mode on/off (build + flip marker) |
| `website/ajax/action.adhoc.heat.inc` | Form a heat from entered pinnies + arm |
| `website/inc/adhoc-standings.inc` | Top-N-per-age-group best-time query + renderer |
| `website/kiosks/adhoc-leaderboard.kiosk` | Public leaderboard kiosk |
| `website/adhoc.php`, `website/js/adhoc.js`, `website/css/adhoc.css` | Marshal page |

## Verification

- **`php testing/test-adhoc-mode.php`** — offline functional test (no server/Docker;
  needs PHP CLI with `pdo_sqlite`). Builds a throwaway official DB from the real
  schema and drives the real code: marker resolve/set + allowlist (incl. fail-safe
  on a dangling marker, non-`.sqlite3`, and path-traversal), `adhoc_build()`
  (roster mirror excludes not-checked-in racers), `adhoc_resolve_pinny()`,
  `adhoc_leaderboard_groups()`/`adhoc_write_leaderboard()` (best-of scoring, DNF
  exclusion, per-age-group top-N, pinny-only/no-names), and official-DB isolation.
  31 checks, all passing.
- `php -l` on all PHP files; `node --check website/js/adhoc.js`.
- End-to-end on the Pi (dress rehearsal): Build & Switch, arm a heat with real
  pinnies, run cars, confirm the leaderboard updates, then End and confirm the
  official standings are unchanged.

<?php
// Ad-hoc ("come-as-you-are") racing mode.
//
// Ad-hoc racing lives in a SEPARATE SQLite file (adhoc.sqlite3, a sibling of the
// official derbynet.sqlite3) so casual fun-run times never pollute the official
// event database. A filesystem marker (see inc/db-marker.inc) re-points the whole
// rig at that file while ad-hoc mode is on, and back to official afterwards.
//
// Racing is one common pool (a start-line marshal enters whichever 3 pinnies are
// at the line, mixed age), but ranking is per age group: every run goes into ONE
// synthetic "Ad-Hoc Open" round, scored by best single time (scoring=2), and the
// leaderboard (inc/adhoc-standings.inc) groups by each racer's REAL age group via
// RegistrationInfo.classid. See docs/ADHOC.md.

require_once('inc/data.inc');
require_once('inc/db-marker.inc');

define('ADHOC_CLASS_NAME', 'Ad-Hoc Open');
define('ADHOC_ROUND_NAME', '1 Ad-Hoc');   // must start with a number (round-naming rule)

// Canonical official DB path (set by local/config-database.inc). Falls back to
// the conventional name under $homedir if that global is absent (older shim).
function adhoc_official_db_path() {
  if (isset($GLOBALS['official_db_path']) && $GLOBALS['official_db_path'] !== '') {
    return $GLOBALS['official_db_path'];
  }
  return rtrim($GLOBALS['homedir'], '/') . '/derbynet.sqlite3';
}

// The ad-hoc DB lives beside the official one.
function adhoc_db_path() {
  return dirname(adhoc_official_db_path()) . '/adhoc.sqlite3';
}

// True when the LIVE database (whatever the marker selected) is the ad-hoc DB.
// Every ad-hoc write path checks this so it can never act on the official DB.
function adhoc_mode_active() {
  return read_raceinfo('adhoc-mode', 0) == 1;
}

// The single ad-hoc racing round id (stored at build time), or false.
function adhoc_roundid() {
  return read_raceinfo('adhoc-roundid', false);
}

// Resolve a marshal-entered pinny (raw digits) or a scanned "PWD..." barcode to a
// racerid, requiring the racer to be checked in. Returns 0 if not resolvable.
function adhoc_resolve_pinny($raw) {
  global $db;
  $raw = trim($raw);
  if ($raw === '') return 0;
  if (strncmp($raw, 'PWD', 3) === 0) {
    require_once('inc/barcode.inc');
    return barcode_to_racerid($raw);
  }
  if (!is_numeric($raw)) return 0;
  $carno = intval($raw);  // pinny "0042" → 42 (carnumber is an INTEGER column)
  return read_single_value(
    'SELECT racerid FROM RegistrationInfo'
    . ' WHERE carnumber = :c AND passedinspection = 1 AND COALESCE(exclude, 0) = 0',
    array(':c' => $carno), 0);
}

// Mirror of write_raceinfo() against an arbitrary PDO (the freshly-built ad-hoc DB).
function adhoc__raceinfo_set(PDO $pdo, $key, $val) {
  $chk = $pdo->prepare('SELECT COUNT(*) FROM RaceInfo WHERE itemkey = :k');
  $chk->execute(array(':k' => $key));
  if ($chk->fetchColumn() == 0) {
    $st = $pdo->prepare('INSERT INTO RaceInfo(itemkey, itemvalue) VALUES(:k, :v)');
  } else {
    $st = $pdo->prepare('UPDATE RaceInfo SET itemvalue = :v WHERE itemkey = :k');
  }
  $st->execute(array(':k' => $key, ':v' => $val));
}

// (Re)build the ad-hoc database from the current official roster.
//
// Strategy: copy the official file (which mirrors the roster — every racer with
// their real classid/rankid/partitionid, all Classes/Ranks/Partitions, schema,
// labels — by construction), then surgically reset all race state and create one
// synthetic Ad-Hoc Open class + round seeded with every checked-in racer.
//
// Always overwrites adhoc.sqlite3. Returns array(roundid, classid, path, racers).
// Throws RuntimeException on failure.
function adhoc_build() {
  $official = adhoc_official_db_path();
  $adhoc = adhoc_db_path();

  if (!@is_file($official)) {
    throw new RuntimeException("adhoc_build: official DB not found at $official");
  }

  // Checkpoint official's WAL via its own connection so the file copy is whole,
  // regardless of which DB the live $db currently points at.
  try {
    $o = new PDO('sqlite:' . $official, '', '', array());
    $o->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $o->exec('PRAGMA wal_checkpoint(TRUNCATE)');
    $o = null;
  } catch (Exception $e) {
    // Best effort — a non-WAL or busy official DB still copies fine.
  }

  // Replace any prior ad-hoc DB (and its sidecar WAL/SHM).
  foreach (array('', '-wal', '-shm') as $sfx) { @unlink($adhoc . $sfx); }
  if (!@copy($official, $adhoc)) {
    throw new RuntimeException("adhoc_build: copy failed ($official -> $adhoc)");
  }
  @chmod($adhoc, 0664);

  $a = new PDO('sqlite:' . $adhoc, '', '', array());
  $a->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
  $a->setAttribute(PDO::ATTR_CASE, PDO::CASE_LOWER);
  $a->exec('PRAGMA journal_mode=WAL');

  $a->beginTransaction();
  try {
    // Wipe all race state — keep only the roster (RegistrationInfo/Classes/Ranks/Partitions).
    $a->exec('DELETE FROM RaceChart');
    $a->exec('DELETE FROM Roster');
    $a->exec('DELETE FROM Rounds');
    foreach (array('EliminationRoundState', 'EliminationAdvancement',
                   'EliminationTournaments', 'EliminationConfig') as $t) {
      try { $a->exec("DELETE FROM $t"); } catch (Exception $e) { /* table may not exist */ }
    }

    // Synthetic single class for the open racing pool. (No racer belongs to it —
    // racers keep their real classid — so it never appears on the leaderboard.)
    $sortorder = (int)$a->query('SELECT 1 + COALESCE(MAX(sortorder), 0) FROM Classes')->fetchColumn();
    $st = $a->prepare('INSERT INTO Classes(class, sortorder) VALUES(:c, :s)');
    $st->execute(array(':c' => ADHOC_CLASS_NAME, ':s' => $sortorder));
    $classid = (int)$a->lastInsertId();

    // Single racing round under that class.
    $st = $a->prepare('INSERT INTO Rounds(round, roundname, classid) VALUES(1, :rn, :cid)');
    $st->execute(array(':rn' => ADHOC_ROUND_NAME, ':cid' => $classid));
    $roundid = (int)$a->lastInsertId();

    // Seed the roster with every checked-in racer, PRESERVING their real classid
    // (their age group) for per-group ranking even though they all race together.
    $st = $a->prepare(
      'INSERT INTO Roster(roundid, classid, racerid)'
      . ' SELECT :rid, classid, racerid FROM RegistrationInfo'
      . ' WHERE passedinspection = 1 AND COALESCE(exclude, 0) = 0');
    $st->execute(array(':rid' => $roundid));
    $racers = $st->rowCount();

    // Config: best single time, no points, identify ourselves, clean race state.
    adhoc__raceinfo_set($a, 'scoring', '2');         // MIN(finishtime)
    adhoc__raceinfo_set($a, 'use-points', '0');
    adhoc__raceinfo_set($a, 'adhoc-mode', '1');
    adhoc__raceinfo_set($a, 'adhoc-roundid', (string)$roundid);
    adhoc__raceinfo_set($a, 'NowRacingState', '0');
    adhoc__raceinfo_set($a, 'RoundID', (string)$roundid);
    adhoc__raceinfo_set($a, 'ClassID', (string)$classid);
    adhoc__raceinfo_set($a, 'Heat', '1');
    adhoc__raceinfo_set($a, 'refused-results', '0');
    adhoc__raceinfo_set($a, 'adhoc-built-utc', gmdate('c'));

    $a->commit();
  } catch (Exception $e) {
    $a->rollBack();
    $a = null;
    throw new RuntimeException('adhoc_build: ' . $e->getMessage());
  }

  // Checkpoint so the new DB is a single self-contained file before any switch.
  try { $a->exec('PRAGMA wal_checkpoint(TRUNCATE)'); } catch (Exception $e) {}
  $a = null;

  return array('roundid' => $roundid, 'classid' => $classid,
               'path' => $adhoc, 'racers' => $racers);
}
?>

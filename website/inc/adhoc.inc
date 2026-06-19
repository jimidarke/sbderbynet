<?php
// Ad-hoc ("come-as-you-are") racing mode — roster-less redesign.
//
// Ad-hoc racing lives in a SEPARATE SQLite file (adhoc.sqlite3, a sibling of the
// official derbynet.sqlite3) so casual fun-run times never pollute the official
// event database. A filesystem marker (see inc/db-marker.inc) re-points the whole
// rig at that file while ad-hoc mode is on, and back to official afterwards.
//
// The ad-hoc DB is built FRESH FROM THE SCHEMA (never copied from the live
// official file — copying a hot WAL database is the historical corruption bug).
// It carries NO roster and NO schedule: the start-line coordinator types whichever
// pinnies are at the line and picks each pinny's age group on the coordinator
// page. A run is stored as one self-describing RaceChart row (display_pinny +
// agegroup_classid, racerid NULL). Scoring is best single time (scoring=2); the
// leaderboard (inc/adhoc-standings.inc) ranks per age group. See docs/ADHOC.md.

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

// The synthetic Ad-Hoc Open class id (the racing pool; NOT an age group).
function adhoc_synthetic_classid() {
  return (int)read_raceinfo('adhoc-classid', 0);
}

// The real age groups available for the coordinator's per-pinny dropdown — the
// event's Classes, minus the synthetic Ad-Hoc Open pool class. Each entry:
// array('classid', 'class', 'sortorder').
function adhoc_age_groups() {
  global $db;
  $synthetic = adhoc_synthetic_classid();
  $stmt = $db->prepare('SELECT classid, class, sortorder FROM Classes'
                       . ' WHERE classid <> :syn'
                       . ' ORDER BY sortorder, class');
  $stmt->execute(array(':syn' => $synthetic));
  return $stmt->fetchAll(PDO::FETCH_ASSOC);
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

// (Re)build the ad-hoc database FROM SCHEMA — never a copy of the live official
// file. Strategy: take a read-only snapshot of the reference data we actually
// need from official (the age-group Classes + display/config RaceInfo), then
// create a blank adhoc.sqlite3, apply the canonical schema, seed those Classes,
// create one synthetic Ad-Hoc Open class + round, and stamp the file as ad-hoc.
// NO roster, NO schedule, NO RaceChart are carried over.
//
// Always overwrites adhoc.sqlite3. Returns array(roundid, classid, path, agegroups).
// Throws RuntimeException on failure.
function adhoc_build() {
  $official = adhoc_official_db_path();
  $adhoc = adhoc_db_path();

  if (!@is_file($official)) {
    throw new RuntimeException("adhoc_build: official DB not found at $official");
  }

  // Remove any prior ad-hoc DB and its sidecars. We never copy a live file, so
  // there is nothing to snapshot — just start clean.
  foreach (array('', '-wal', '-shm') as $sfx) {
    if (@is_file($adhoc . $sfx) && !@unlink($adhoc . $sfx)) {
      throw new RuntimeException("adhoc_build: could not remove stale " . $adhoc . $sfx);
    }
  }

  // Read-only snapshot from official: age-group Classes + display/config RaceInfo.
  // One read transaction on a fresh connection — read-only, so no copy-during-
  // write race and no writers blocked.
  try {
    $o = new PDO('sqlite:' . $official, '', '', array());
    $o->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $o->setAttribute(PDO::ATTR_CASE, PDO::CASE_LOWER);
    $o->beginTransaction();
    $classes  = $o->query('SELECT classid, class, sortorder FROM Classes ORDER BY sortorder, class')
                  ->fetchAll(PDO::FETCH_ASSOC);
    $raceinfo = $o->query('SELECT itemkey, itemvalue FROM RaceInfo')
                  ->fetchAll(PDO::FETCH_ASSOC);
    $o->commit();
    $o = null;
  } catch (Exception $e) {
    throw new RuntimeException('adhoc_build: could not read official DB: ' . $e->getMessage());
  }

  // Build a FRESH ad-hoc DB from the canonical schema (same path create_tenant()
  // uses). schema.inc consumes globals $db/$dbtype and expected_schema_version().
  $a = new PDO('sqlite:' . $adhoc, '', '', array());
  $a->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
  $a->setAttribute(PDO::ATTR_CASE, PDO::CASE_LOWER);
  @chmod($adhoc, 0664);

  $prev_db     = isset($GLOBALS['db']) ? $GLOBALS['db'] : null;
  $prev_dbtype = isset($GLOBALS['dbtype']) ? $GLOBALS['dbtype'] : null;
  $GLOBALS['db'] = $a;
  $GLOBALS['dbtype'] = 'sqlite';
  try {
    require_once('inc/schema_version.inc');
    require_once('inc/sql-script.inc');
    $script = include('sql/sqlite/schema.inc');
    if (!is_array($script)) {
      throw new RuntimeException('schema script missing');
    }
    foreach ($script as $stmt) { $a->exec($stmt); }

    $a->beginTransaction();

    // Overlay official's display/config RaceInfo (lane_count, labels, time format,
    // etc.) so the ad-hoc rig looks like the event. Skip the structural 'schema'
    // key (the fresh DB already has the correct version). Per-key replace, so
    // duplicate official keys collapse to the last value. Race-state keys are
    // overridden below.
    $rset = $a->prepare('INSERT INTO RaceInfo(itemkey, itemvalue) VALUES(:k, :v)');
    $rdel = $a->prepare('DELETE FROM RaceInfo WHERE itemkey = :k');
    foreach ($raceinfo as $ri) {
      if ($ri['itemkey'] === 'schema') continue;
      $rdel->execute(array(':k' => $ri['itemkey']));
      $rset->execute(array(':k' => $ri['itemkey'], ':v' => $ri['itemvalue']));
    }

    // Seed the event's age-group Classes (preserve classid so the age-group
    // identity is stable). These drive the coordinator's per-pinny age-group
    // dropdown and the leaderboard labels.
    $a->exec('DELETE FROM Classes');
    if (count($classes) > 0) {
      $cins = $a->prepare('INSERT INTO Classes(classid, class, sortorder) VALUES(:id, :c, :s)');
      foreach ($classes as $c) {
        $cins->execute(array(':id' => $c['classid'], ':c' => $c['class'], ':s' => $c['sortorder']));
      }
    }

    // Synthetic class + single round that hold the open racing pool. RaceChart
    // rows are keyed by (roundid, heat); per-age-group ranking uses
    // agegroup_classid, never this class.
    $sortorder = (int)$a->query('SELECT 1 + COALESCE(MAX(sortorder), 0) FROM Classes')->fetchColumn();
    $st = $a->prepare('INSERT INTO Classes(class, sortorder) VALUES(:c, :s)');
    $st->execute(array(':c' => ADHOC_CLASS_NAME, ':s' => $sortorder));
    $classid = (int)$a->lastInsertId();

    $st = $a->prepare('INSERT INTO Rounds(round, roundname, classid) VALUES(1, :rn, :cid)');
    $st->execute(array(':rn' => ADHOC_ROUND_NAME, ':cid' => $classid));
    $roundid = (int)$a->lastInsertId();

    // Stamp: this file IS ad-hoc. Override any race state carried from official.
    adhoc__raceinfo_set($a, 'adhoc-mode', '1');
    adhoc__raceinfo_set($a, 'adhoc-roundid', (string)$roundid);
    adhoc__raceinfo_set($a, 'adhoc-classid', (string)$classid);
    adhoc__raceinfo_set($a, 'scoring', '2');         // MIN(finishtime) — best single
    adhoc__raceinfo_set($a, 'use-points', '0');
    adhoc__raceinfo_set($a, 'NowRacingState', '0');
    adhoc__raceinfo_set($a, 'RoundID', (string)$roundid);
    adhoc__raceinfo_set($a, 'ClassID', (string)$classid);
    adhoc__raceinfo_set($a, 'Heat', '1');
    adhoc__raceinfo_set($a, 'refused-results', '0');
    adhoc__raceinfo_set($a, 'adhoc-built-utc', gmdate('c'));

    $a->commit();
  } catch (Exception $e) {
    if ($a->inTransaction()) { $a->rollBack(); }
    $GLOBALS['db'] = $prev_db;
    $GLOBALS['dbtype'] = $prev_dbtype;
    $a = null;
    throw new RuntimeException('adhoc_build: ' . $e->getMessage());
  }

  // Consolidate so the new DB is a single self-contained file before any switch.
  try { $a->exec('PRAGMA wal_checkpoint(TRUNCATE)'); } catch (Exception $e) {}
  $a = null;

  $GLOBALS['db'] = $prev_db;
  $GLOBALS['dbtype'] = $prev_dbtype;

  return array('roundid' => $roundid, 'classid' => $classid,
               'path' => $adhoc, 'agegroups' => count($classes));
}

// Form an ad-hoc heat from coordinator-entered (pinny + age group) lanes and
// insert it as a fresh, monotonically-numbered heat. Roster-less: each lane is a
// self-describing RaceChart row (racerid NULL, display_pinny, agegroup_classid).
//
// $lanes is an ordered array of array('pinny' => '42', 'agegroup_classid' => N).
// Blank-pinny lanes are skipped (bye lanes). Validation is all-or-nothing so a
// kid is never silently dropped. Does NOT touch racing state — the caller arms.
//
// Returns array(roundid, heat, lanes). Throws RuntimeException on any validation
// failure (the action maps the message to a json_failure).
function adhoc_arm_heat($lanes) {
  global $db;

  if (!adhoc_mode_active()) {
    throw new RuntimeException('Ad-hoc mode is not active. Turn it on first.');
  }
  $roundid = adhoc_roundid();
  if ($roundid === false) {
    throw new RuntimeException('Ad-hoc round is missing — rebuild ad-hoc mode.');
  }

  // Allowlist of real age-group classids.
  $valid = array();
  foreach (adhoc_age_groups() as $g) { $valid[(int)$g['classid']] = true; }

  // The position of each entry in $lanes IS its physical lane (1-based). Real
  // finish timers report by physical lane, so a bye in the middle must keep its
  // lane number (e.g. cars in lanes 1 and 3 stay 1 and 3, never compact to 1,2).
  $clean = array();
  $seen = array();
  $physical_lane = 0;
  foreach ($lanes as $lane_entry) {
    $physical_lane++;
    $rawpinny = isset($lane_entry['pinny']) ? trim((string)$lane_entry['pinny']) : '';
    if ($rawpinny === '') continue;   // empty slot = bye on this lane
    // Plain regex, not ctype_digit() — the alpine PHP build (and some minimal
    // installs) ship without the ctype extension.
    if (preg_match('/^[0-9]+$/', $rawpinny) !== 1) {
      throw new RuntimeException("Pinny '$rawpinny' is not a number.");
    }
    $pinny = (int)$rawpinny;
    if ($pinny <= 0) {
      throw new RuntimeException("Pinny '$rawpinny' is not valid.");
    }
    $ag = isset($lane_entry['agegroup_classid']) ? (int)$lane_entry['agegroup_classid'] : 0;
    if (!isset($valid[$ag])) {
      throw new RuntimeException("Pinny $pinny: choose an age group.");
    }
    if (isset($seen[$pinny])) {
      throw new RuntimeException("Pinny $pinny entered twice in one heat.");
    }
    $seen[$pinny] = true;
    $clean[] = array('lane' => $physical_lane, 'pinny' => (string)$pinny,
                     'agegroup_classid' => $ag);
  }

  if (count($clean) == 0) {
    throw new RuntimeException('Enter at least one pinny.');
  }

  $synthetic = adhoc_synthetic_classid();
  $heat = 1 + (int)read_single_value('SELECT MAX(heat) FROM RaceChart WHERE roundid = :r',
                                     array(':r' => $roundid), 0);

  $ins = $db->prepare('INSERT INTO RaceChart(roundid, heat, lane, racerid, classid,'
                      . ' display_pinny, agegroup_classid)'
                      . ' VALUES(:roundid, :heat, :lane, NULL, :classid, :pinny, :ag)');
  foreach ($clean as $c) {
    $ins->execute(array(':roundid' => $roundid, ':heat' => $heat, ':lane' => $c['lane'],
                        ':classid' => $synthetic, ':pinny' => $c['pinny'],
                        ':ag' => $c['agegroup_classid']));
  }

  return array('roundid' => $roundid, 'heat' => $heat, 'lanes' => count($clean));
}
?>

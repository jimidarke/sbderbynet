<?php
// Sentinel finishtime for a DNF (Did Not Finish). Must match DNF_TIME in
// extras/soapbox/infra/server/derbyRace.py, which detects coordinator DNFs
// as finishtime >= this value.
define('DNF_TIME', 99.999);

$configdir = isset($_SERVER['DERBYNET_CONFIG_DIR']) ? $_SERVER['DERBYNET_CONFIG_DIR'] : 'local';

// On the cloud VPS, the active database is per-browser-session ("tenant
// sandbox"), not server-global. The slug lives in $_SESSION['tenant_slug']
// and is set by tenant-picker.php / action.tenant-select.nodata.inc.
// Pi deployments fall through to the legacy single-DB include path below.
$_dn_cloud_mode = isset($_SERVER['DERBYNET_CLOUD_MODE']) ? $_SERVER['DERBYNET_CLOUD_MODE'] : '';
if ($_dn_cloud_mode !== '') {
  require_once(dirname(__FILE__) . DIRECTORY_SEPARATOR . 'cloud-tenant.inc');
  // Internal-service override: the race-server (and other backend services
  // that run without a browser session) cannot pick a tenant via the picker.
  // They send X-DerbyNet-Tenant + X-DerbyNet-Internal-Token; the token is a
  // shared secret known only to internal services. Caddy strips both headers
  // from external traffic so a public client cannot spoof them.
  $_dn_internal_token = getenv('DERBYNET_INTERNAL_TOKEN') ?: '';
  $_dn_hdr_token  = isset($_SERVER['HTTP_X_DERBYNET_INTERNAL_TOKEN'])
                    ? $_SERVER['HTTP_X_DERBYNET_INTERNAL_TOKEN'] : '';
  $_dn_hdr_tenant = isset($_SERVER['HTTP_X_DERBYNET_TENANT'])
                    ? $_SERVER['HTTP_X_DERBYNET_TENANT'] : '';
  $_dn_internal_tenant = '';
  if ($_dn_internal_token !== ''
      && hash_equals($_dn_internal_token, $_dn_hdr_token)
      && valid_tenant_slug($_dn_hdr_tenant)
      && tenant_exists($_dn_hdr_tenant)) {
    $_dn_internal_tenant = $_dn_hdr_tenant;
  }
  $_dn_active_tenant = $_dn_internal_tenant !== ''
    ? $_dn_internal_tenant
    : (isset($_SESSION['tenant_slug']) && tenant_exists($_SESSION['tenant_slug'])
       ? $_SESSION['tenant_slug'] : '');
  if ($_dn_active_tenant !== '') {
    $db_connection_string = 'sqlite:' . tenant_db_path($_dn_active_tenant);
    try {
      $db = new PDO($db_connection_string, '', '', array());
      $db->setAttribute(PDO::ATTR_CASE, PDO::CASE_LOWER);
    } catch (PDOException $p) {
    }
  }
  if (!isset($db)) {
    // Internal callers should never see a redirect — return 503 so they can
    // log/retry instead of following a browser-flow redirect.
    if ($_dn_internal_token !== ''
        && isset($_SERVER['HTTP_X_DERBYNET_INTERNAL_TOKEN'])) {
      http_response_code(503);
      header('Content-Type: application/json');
      echo json_encode(array('error' => 'tenant-not-bound',
                             'message' => 'Internal request did not match a known tenant'));
      exit();
    }
    // No tenant chosen yet — kick the browser to the picker. AJAX endpoints
    // that need a DB will receive HTML here, but those callers should already
    // be inside a session that has a tenant; no-tenant AJAX is a programming
    // error, not an end-user path.
    if (basename($_SERVER['SCRIPT_NAME']) !== 'tenant-picker.php') {
      header('Location: tenant-picker.php');
      exit();
    }
  }
} else {
  try {
      @include($configdir.DIRECTORY_SEPARATOR."config-database.inc");
  } catch (PDOException $p) {
  }

  if (!isset($db)) {
    $_SESSION['setting_up'] = 1;
    header('Location: setup.php');
    exit();
  }
}

$db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

// Enable WAL mode for SQLite to allow concurrent reads during writes
// This is critical for Python race server writing results while PHP reads
$dbtype = $db->getAttribute(PDO::ATTR_DRIVER_NAME);
if ($dbtype == 'sqlite') {
  $db->exec('PRAGMA journal_mode=WAL');
  $db->exec('PRAGMA busy_timeout=5000');  // Wait up to 5s for locks
}
if ($dbtype == 'odbc') {
	$dbtype = 'access';
}

// Cloud-mode detection. The cloud twin is a read-only replica used for dev,
// CI, and dress rehearsals. Race-day production is the local Pi and never
// runs in cloud mode.
//
// Allowed values:
//   ''       (default)  - normal local operation
//   'public' - cloud twin serving Pi-synced data; enforces name privacy and
//              suppresses device-offline alerts (no real hardware connects)
//
// Set via DERBYNET_CLOUD_MODE env var in installer/docker-cloud/.env.
if (!defined('DERBYNET_CLOUD_MODE')) {
  define('DERBYNET_CLOUD_MODE',
         isset($_SERVER['DERBYNET_CLOUD_MODE']) ? $_SERVER['DERBYNET_CLOUD_MODE'] : '');
}

function is_cloud_mode() {
  return DERBYNET_CLOUD_MODE !== '';
}

function is_cloud_public_mode() {
  return DERBYNET_CLOUD_MODE === 'public';
}

// Returns last cloud-sync timestamp (ISO 8601 UTC) if the .cloud_readonly
// sentinel exists, otherwise null. Cloud-sync (extras/soapbox/infra/server/
// cloud-sync.sh) writes this alongside the DB on every Pi -> cloud push.
function cloud_last_sync_utc() {
  $sentinel = '/var/lib/derbynet/.cloud_readonly';
  if (!is_cloud_mode() || !is_readable($sentinel)) {
    return null;
  }
  $contents = @file_get_contents($sentinel);
  if ($contents === false) return null;
  if (preg_match('/^last_sync_utc=(\S+)/m', $contents, $m)) {
    return $m[1];
  }
  return null;
}

function dbnow_expr() {
  global $dbtype;
  if ($dbtype == 'sqlite') {
    return "datetime('now', 'localtime')";
  } else {
    return "NOW()";
  }
}

// Returns an expression suitable for comparing with 'completed' in RaceChart
// $expr is an SQL expression that produces a value like '2013-11-14 14:57:14'
// (PHP format 'Y-m-d H:i:s')
function db_compare_completed($expr) {
  global $dbtype;
  if ($dbtype == 'sqlite') {
    return "datetime($expr)";
  } else if ($dbtype == 'access') {
    return "CDate($expr)";
  }
}

// inner_join('Classes', 'Rounds', on, 'Roster', on, ...)
function inner_join() {
  global $dbtype;
  $args = func_get_args();
  $expr = array_shift($args);  // Take off the first table name
  $first = true;
  while (count($args) > 0) {
    $table2 = array_shift($args);
    $on_condition = array_shift($args);
    if ($dbtype != 'sqlite') { // TODO == 'access') {
      if (!$first) {
        $expr = '('.$expr.')';
      }
      $expr = $table2.' INNER JOIN '.$expr.' ON '.$on_condition;
    } else {
      $expr = $expr.' INNER JOIN '.$table2.' ON '.$on_condition;
    }
    $first = false;
  }
  return $expr;
}

// Returns row with only numbered array elements
// (Use PDO::FETCH_ASSOC for named array elements)
function read_single_row($sql, $params = array(), $fetch = PDO::FETCH_NUM) {
  global $db;
  $rs = $db->prepare($sql);
  $rs->execute($params);
  $row = $rs->fetch($fetch);
  $rs->closeCursor();
  return $row;
}

function read_single_value($sql, $params = array(), $def = false) {
  $row = read_single_row($sql, $params);
  if ($row === false || $row[0] === null) {
	return $def;
  }

  return $row[0];
}

function execute_once($sql, $params = array()) {
  global $db;
  $rs = $db->prepare($sql);
  $rs->execute($params);
  $rs->closeCursor();
}


// The RaceInfo table is just a simple ItemKey/ItemValue association, and stores individual
// configuration settings from GPRM.  As long as there aren't any name conflicts, we can add a 
// few configuration settings of our own.
function read_raceinfo($key, $def = false) {
  return read_single_value('SELECT itemvalue FROM RaceInfo WHERE itemkey = :key',
						   array(':key' => $key), $def);
}

function read_raceinfo_boolean($key, $default = false) {
    $value = read_raceinfo($key);
    if ($value === false || $value === null) {
        return $default;
    }
    return $value == '1' || strtolower($value) == 'true';
}

// Returns true if testing/simulation mode is enabled
function testing_mode_enabled() {
    return read_raceinfo_boolean('testing-mode', false);
}

function write_raceinfo($key, $val) {
  global $db;
  $stmt = $db->prepare('SELECT COUNT(*) FROM RaceInfo WHERE itemkey = :key');
  $stmt->execute(array(':key' => $key));
  if ($stmt->fetchColumn() == 0) {
	$stmt = $db->prepare('INSERT INTO RaceInfo(itemkey, itemvalue) VALUES(:key, :value)');
  } else {
	$stmt = $db->prepare('UPDATE RaceInfo SET itemvalue = :value WHERE itemkey = :key');
  }
  $stmt->execute(array(':key' => $key,
					   ':value' => $val));
}

function delete_from_raceinfo($key) {
  global $db;
  $stmt = $db->prepare('DELETE FROM RaceInfo WHERE itemkey = :key');
  $stmt->execute(array(':key' => $key));
}
function delete_from_raceinfo_with_value($key, $val) {
  global $db;
  $stmt = $db->prepare('DELETE FROM RaceInfo WHERE itemkey = :key AND itemvalue = :value');
  $stmt->execute(array(':key' => $key,
                       ':value' => $val));
}  

function use_groups() {
  return read_single_value('SELECT COUNT(*) FROM Classes') > 1;
}

function use_subgroups() {
  return read_raceinfo_boolean('use-subgroups');
}

function use_master_sched() {
  return read_raceinfo_boolean('use-master-sched');
}

// Pinny (car number) display form. carnumber is an INTEGER column, so a
// pinny printed "0004" on the physical bib is stored as 4; restore the
// 4-digit zero padding whenever a carnumber is shown to a human.
function pinny_display($carnumber) {
  return is_numeric($carnumber)
      ? str_pad($carnumber, 4, '0', STR_PAD_LEFT)
      : $carnumber;
}

function update_period() {
  return read_raceinfo('update-period', 2500);
}

function get_lane_count() {
  return read_raceinfo('lane_count', 0);
}

// get_lane_count is used for creating schedules, while
// get_lane_count_for_results tells how big a table to prepare for displaying
// results.
function get_lane_count_from_results() {
  global $db;
  $nlanes = get_lane_count();
  if ($nlanes != 0) {
    return $nlanes;
  }
  $rs = $db->query('SELECT MAX(lane), COUNT(*) FROM RaceChart');
  $row = $rs->fetch(PDO::FETCH_NUM);
  if (!$row || !isset($row[0]) || !$row[0]) {
    return 0;
  } else {
    return $row[0];
  }
}

function get_finishtime_formatting_string() {
  return read_raceinfo('finish-formatting', '%5.3f');
}


// Returns the highest ResultID from the RaceChart table.
// Assuming this increases monotonically, a newly scheduled
// round is detected by a new high-water resultid.  Deleting a
// schedule is undetected, but we don't really care until/unless
// there's a new schedule to replace it.
function high_water_resultid() {
  return read_single_value('SELECT MAX(resultid) FROM RaceChart', array(), 0);
}

// Returns the highest RoundID from the Rounds table.
// For ondeck, a new high-water RoundID signals a page reload.
function high_water_rounds() {
  global $db;
  $stmt = $db->query('SELECT MAX(roundid), MAX(round) FROM Rounds');
  $rs = $stmt->fetch(PDO::FETCH_NUM);
  if ($rs === false || is_null($rs[0]) || is_null($rs[1])) {
    $rs = array(0 => 0, 1 => 0);
  } 
  return array('roundid' => $rs[0],
			   'round' => $rs[1]);
}

// When performing timer test heats, the current roundid is set to this value,
// and the current heat is relatively arbitrary (counts up from 1).
define('TIMER_TEST_ROUNDID', -100);

// Returns an array value with elements for { classid => , roundid => , heat => }
// describing the currently-running round and heat.
// function get_running_round() {

//   // global $db;
//   // $config = array('use_master_sched' => 0,
//   //                 'use_points' => 0,
//   //                 'now_racing' => 0,
// 	// 			  'class' => '',
// 	// 			  'roundid' => -1,
// 	// 			  'classid' => 1,
// 	// 			  'round' => 1,
//   //         'heat' => 1);  // May be overwritten

//   // foreach ($db->query('SELECT itemkey, itemvalue FROM RaceInfo') as $rs) {
//   //   $key = $rs['itemkey'];
//   //   $val = $rs['itemvalue'];
//   //   if ($key == 'ClassID')
//   //     $config['classid'] = $val;
//   //   else if ($key == 'RoundID')
//   //     $config['roundid'] = $val;
//   //   else if ($key == 'Heat')
//   //     $config['heat'] = $val;
//   //   // GPRM doesn't record use-master-sched in the database; it has to
//   //   // be set explicitly from the settings page.
//   //   // TODO: use-master-sched key => UseMasterSched
//   //   else if ($key == 'use-master-sched')
//   //     $config['use_master_sched'] = $val ? 1 : 0;
//   //   else if ($key == 'use-points')
//   //     $config['use_points'] = $val ? 1 : 0;
//   //   else if ($key == 'NowRacingState')
//   //     $config['now_racing'] = $val ? 1 : 0;
//   // }

//   // if (@$config['roundid'] == TIMER_TEST_ROUNDID) {
//   //   $config['class'] = 'Timer Test';
//   //   $config['round'] = 1;
//   // } else if (@$config['roundid']) {
//   //   $stmt = $db->prepare('SELECT round, class'
//   //                        .' FROM Rounds'
//   //                        .' INNER JOIN Classes'
//   //                        .' ON Rounds.classid = Classes.classid'
//   //                        .' WHERE roundid = :roundid'
//   //                        .' AND Rounds.classid = :classid');
//   //   $stmt->execute(array(':roundid' => @$config['roundid'],
//   //                        ':classid' => @$config['classid']));
//   //   $rs = $stmt->fetch(PDO::FETCH_ASSOC);
//   //   if ($rs !== false) {
//   //     $config['class'] = $rs['class'];
//   //     $config['round'] = $rs['round'];
//   //   }
//   // }

//   // Update As on 18-04-2025
//   // The above code is replaced with the following code to use the new
//     $config = array();
//     $config['roundid'] = read_raceinfo('RoundID', 0);
//     $config['heat'] = read_raceinfo('Heat', 0);
//     $config['now_racing'] = read_raceinfo('NowRacingState', 0);
//     $config['use_points'] = read_raceinfo('use-points', 0);
//     $config['use_master_sched'] = use_master_sched();

//     if ($config['roundid']) {
//         $round = read_single_row(
//             'SELECT Rounds.round, Rounds.roundname, Classes.classid, Classes.class 
//              FROM Rounds 
//              INNER JOIN Classes ON Classes.classid = Rounds.classid 
//              WHERE Rounds.roundid = :roundid',
//             [':roundid' => $config['roundid']]
//         );

//         if ($round) {
//             $config['round'] = $round['round'] ?? null;
//             $config['roundname'] = $round['roundname'] ?? null;
//             $config['class'] = $round['class'] ?? null;
//             $config['classid'] = $round['classid'] ?? null;
//         }
//     }

//     return $config;
// }


// Update As on 25-04-2025
function get_running_round() {
  $config = [
      'use_master_sched' => use_master_sched(), // assuming this is a function returning 0 or 1
      'use_points'       => read_raceinfo('use-points', 0),
      'now_racing'       => read_raceinfo('NowRacingState', 0),
      'class'            => '',
      'roundid'          => read_raceinfo('RoundID', -1),
      'classid'          => read_raceinfo('ClassID', 1),
      'round'            => 1,
      'heat'             => read_raceinfo('Heat', 1),
  ];

  // Special case for timer test round
  if ($config['roundid'] == TIMER_TEST_ROUNDID) {
      $config['class'] = 'Timer Test';
      $config['round'] = 1;
  }
  // Load full round and class details
  else if ($config['roundid'] > 0) {
      $round = read_single_row(
          'SELECT Rounds.round, Rounds.roundname, Classes.classid, Classes.class 
           FROM Rounds 
           INNER JOIN Classes ON Classes.classid = Rounds.classid 
           WHERE Rounds.roundid = :roundid 
           AND Rounds.classid = :classid',
          [
              ':roundid'  => $config['roundid'],
              ':classid'  => $config['classid'],
          ]
      );

      if ($round) {
          $config['round']     = $round['round'] ?? $config['round'];
          $config['roundname'] = $round['roundname'] ?? null;
          $config['class']     = $round['class'] ?? '';
          $config['classid']   = $round['classid'] ?? $config['classid'];
      }
  }

  return $config;
}

function record_action($args) {
  global $db;
  try {
    $logstmt = $db->prepare('INSERT INTO ActionHistory(received, request) VALUES('.dbnow_expr().', :args)');
    $logstmt->execute(array(':args' => json_encode($args, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)));
  } catch (PDOException $p) {
  }
}

// Request a near-immediate cloud-sync push of the event DB to the VPS twin.
// Best-effort: bumps the mtime of a world-writable trigger file that a systemd
// .path unit watches on the race-day Pi (see docs/PUBLIC_STATS.md). The file is
// owned by `derbynet` but mode 0666, so the web app (www-data) can update its
// mtime. Silent no-op off-Pi (cloud twin, dev, tests) where the file is absent,
// and never throws into the calling race action.
function request_cloud_push() {
  $f = '/run/derbynet-cloud-sync.trigger';
  if (@is_writable($f)) { @touch($f); }
}

function set_current_heat($roundid, $heat) {
  global $db;
  write_raceinfo('RoundID', $roundid);
  write_raceinfo('Heat', $heat);

  record_action(array('action' => 'heat.*advance',
                      'roundid' => $roundid,
                      'heat' => $heat));

  // Heat advance + round change → refresh the spectator pages promptly.
  request_cloud_push();
}

// If not working with a timer device, or if DerbyNet is just running as a
// companion to Grand Prix Race Manager (and so not actually running the race),
// we want not to put up warnings about not having an active timer connection.
function warn_no_timer() {
  return read_raceinfo('warn-no-timer', true) ? true : false;
}

function is_windows_server() {
  return strtoupper(substr(PHP_OS, 0, 3)) === 'WIN';
}

function is_no_such_table_exception(/* PDOException */ $p) {
  return $p->getCode() == '42S02' ||
      ($p->getCode() == 'HY000' && stripos($p->getMessage(), "no such table") !== false);
}
?>

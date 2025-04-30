<?php
$configdir = isset($_SERVER['DERBYNET_CONFIG_DIR']) ? $_SERVER['DERBYNET_CONFIG_DIR'] : 'local';
try {
    @include($configdir.DIRECTORY_SEPARATOR."config-database.inc");
} catch (PDOException $p) {
}

if (!isset($db)) {
    $_SESSION['setting_up'] = 1;
    header('Location: setup.php');
    exit();
}

// Check if we should be using test database
if (isset($_SESSION['test-mode']) && $_SESSION['test-mode'] && isset($_SESSION['test_database'])) {
    try {
        $test_db = new PDO('sqlite:' . $_SESSION['test_database']);
        $test_db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        
        // Switch to test database
        $db = $test_db;
        error_log("Using test database: " . $_SESSION['test_database']);
    } catch (Exception $e) {
        error_log("Failed to connect to test database: " . $e->getMessage());
        // Fall back to production database
        $_SESSION['test-mode'] = false;
    }
}

$db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

//echo '<pre>'; print_r(PDO::getAvailableDrivers()); echo '</pre>';
// On Mac, produces array('sqlite')
// On Windows, produces array('odbc', 'sqlite')

$dbtype = $db->getAttribute(PDO::ATTR_DRIVER_NAME);
if ($dbtype == 'odbc') {
	$dbtype = 'access';
}


function switch_database($use_test_mode = false) {
  global $db;
  
  try {
      $base_dir = dirname(dirname(__FILE__)); 
      $year = date('Y');
      
      // Define paths consistently
      $prod_dir = "$base_dir/Data/$year/derbynet_rms";
      $test_dir = "$base_dir/Data/test/$year/derbynet_rms";
      
      // Ensure base directories exist
      foreach ([$prod_dir, $test_dir] as $dir) {
          if (!file_exists($dir)) {
              mkdir($dir, 0777, true);
          }
      }

      // Define subdirectories structure
      $subdirs = ['racers', 'cars', 'videos', 'logs', 'imagery', 'slides'];
      
      // Create subdirectories for both production and test
      foreach ([$prod_dir, $test_dir] as $base) {
          foreach ($subdirs as $sub) {
              $path = "$base/$sub";
              if (!file_exists($path)) {
                  mkdir($path, 0777, true);
              }
          }
      }

      // Set target paths
      $target_dir = $use_test_mode ? $test_dir : $prod_dir;
      $db_path = $use_test_mode ? "$test_dir/derbynet.sqlite3" : "$prod_dir/derbynet.sqlite3";
      
      // Store current settings before switch
      $current_settings = null;
      if ($db) {
          try {
              $stmt = $db->query('SELECT itemkey, itemvalue FROM RaceInfo');
              $current_settings = $stmt->fetchAll(PDO::FETCH_KEY_PAIR);
          } catch (Exception $e) {
              error_log("Failed to backup settings: " . $e->getMessage());
          }
      }

      // If switching to test mode and test DB doesn't exist, copy from production
      if ($use_test_mode && !file_exists($db_path) && file_exists("$prod_dir/derbynet.sqlite3")) {
          if (!copy("$prod_dir/derbynet.sqlite3", $db_path)) {
              throw new Exception("Failed to initialize test database");
          }
          chmod($db_path, 0777);
      }

      // Close existing connection
      if ($db) {
          $db = null;
      }
      
      // Create new connection
      $new_db = new PDO("sqlite:$db_path");
      $new_db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
      $db = $new_db;

      // Build directory structure for current mode
      $current_directories = [
          'database' => $target_dir,
          'racers' => "$target_dir/racers",
          'cars' => "$target_dir/cars",
          'videos' => "$target_dir/videos",
          'logs' => "$target_dir/logs",
          'imagery' => "$target_dir/imagery",
          'slides' => "$target_dir/slides"
      ];

      // Update session state
      $_SESSION['test-mode'] = $use_test_mode;
      $_SESSION['settings']['test-mode'] = $use_test_mode ? '1' : '0';
      $_SESSION['current_database'] = $db_path;
      $_SESSION['current_directories'] = $current_directories;

      // Update database test mode
      $db->beginTransaction();
      try {
          // Update test mode flag
          $db->exec("DELETE FROM RaceInfo WHERE itemkey = 'test-mode'");
          $db->exec("INSERT INTO RaceInfo (itemkey, itemvalue) VALUES ('test-mode', '".($use_test_mode ? "1" : "0")."')");
          
          // Update directory paths
          $db->exec("UPDATE RaceInfo SET itemvalue = '{$current_directories['racers']}' WHERE itemkey = 'photo-directory'");
          $db->exec("UPDATE RaceInfo SET itemvalue = '{$current_directories['cars']}' WHERE itemkey = 'car-photo-directory'");
          $db->exec("UPDATE RaceInfo SET itemvalue = '{$current_directories['videos']}' WHERE itemkey = 'video-directory'");
          $db->exec("UPDATE RaceInfo SET itemvalue = '{$current_directories['logs']}' WHERE itemkey = 'logs-directory'");
          
          $db->commit();
      } catch (Exception $e) {
          $db->rollBack();
          throw new Exception("Failed to update database settings: " . $e->getMessage());
      }

      // Transfer settings if switching to test mode
      if ($use_test_mode && $current_settings) {
          try {
              $db->beginTransaction();
              
              foreach ($current_settings as $key => $value) {
                  // Skip certain settings that shouldn't be copied
                  if (!in_array($key, ['test-mode', 'schema'])) {
                      $stmt = $db->prepare('INSERT OR REPLACE INTO RaceInfo (itemkey, itemvalue) VALUES (:key, :value)');
                      $stmt->execute([':key' => $key, ':value' => $value]);
                  }
              }
              
              $db->commit();
          } catch (Exception $e) {
              $db->rollBack();
              error_log("Failed to transfer settings: " . $e->getMessage());
          }
      }

      error_log("Successfully switched to " . ($use_test_mode ? "test" : "production") . " database at: $db_path");
      return true;
      
  } catch (Exception $e) {
      error_log("Failed to switch database: " . $e->getMessage());
      return false;
  }
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

function set_current_heat($roundid, $heat) {
  global $db;
  write_raceinfo('RoundID', $roundid);
  write_raceinfo('Heat', $heat);

  record_action(array('action' => 'heat.*advance',
                      'roundid' => $roundid,
                      'heat' => $heat));
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

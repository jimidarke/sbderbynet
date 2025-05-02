<?php
require_once 'error-logging.inc';
function sql_file_path($stem) {
  global $dbtype;
  return 'sql'.DIRECTORY_SEPARATOR.$dbtype.DIRECTORY_SEPARATOR.$stem.'.inc';
}

// Returns two values, a bool (true for successful execution) and a list of results
function run_sql_script($scriptname) {
    global $db;
    global $dbtype;
    $ok = true;
    $executed = array();
    try {
        $sql_script = @include(sql_file_path($scriptname));
        if ($sql_script !== false) {
            foreach ($sql_script as $sql_stmt) {
                try {
                    // Add logging for each statement
                    error_log("Executing SQL: " . $sql_stmt);
                    
                    $sql_result = $db->exec($sql_stmt);
                    if ($sql_result !== false) {
                        $executed[] = array('sql' => $sql_stmt, 'result' => $sql_result);
                    } else {
                        $error = $db->errorInfo();
                        error_log("SQL Error: " . print_r($error, true));
                        json_sql_failure($sql_stmt);
                        $ok = false;
                        break;
                    }
                } catch (PDOException $p) {
                    error_log("PDO Exception: " . $p->getMessage());
                    $executed[] = array('sql' => $sql_stmt, 'result' => null, 'error' => $p->getMessage());

                    if ($dbtype == 'access' && substr($sql_stmt, 0, 4) == 'DROP') {
                        // This is expected for Access DB
                        continue;
                    } else {
                        json_sql_failure($sql_stmt);
                        $ok = false;
                        break;
                    }
                }
            }
        } else {
            error_log("SQL script not found: " . sql_file_path($scriptname));
            json_failure('sqlnoscript', "SQL script $scriptname not found.");
            $ok = false;
        }
    } catch (PDOException $p) {
        error_log("Database Error: " . $p->getMessage());
        json_failure('sqlfailure', $p->getMessage());
        $ok = false;
    }

    return array($ok, $executed);
}

function save_selected_race_info_values($keys) {
  global $db;
  $saved_raceinfo = array();
  foreach ($db->query('SELECT itemkey, itemvalue FROM RaceInfo') as $row) {
    if (in_array($row['itemkey'], $keys)) {
      $saved_raceinfo[$row['itemkey']] = $row['itemvalue'];
    }
  }
  return $saved_raceinfo;
}

function restore_saved_race_info_values(&$saved_raceinfo) {
  foreach ($saved_raceinfo as $key => $value) {
    write_raceinfo($key, $value);
  }
}

define('RACE_INFO_KEYS_FOR_SCHEMA_SCRIPT',
       ['photo-directory',
        'car-photo-directory',
        'video-directory',
        'logs-directory',
        'lane_count',

        '_websocket_url',
        '_ws_trigger_port']);

define('RACE_INFO_KEYS_FOR_SNAPSHOT',
       ['photo-directory',
        'car-photo-directory',
        'video-directory',
        'logs-directory',

        '_websocket_url',
        '_ws_trigger_port']);
?>

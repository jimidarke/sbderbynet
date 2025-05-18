<?php
require_once('inc/data.inc');

function load_all_settings_into_session() {
    global $db;
    
    try {
        if (!isset($_SESSION['settings'])) {
            $_SESSION['settings'] = array();
        }

        // Get current test mode state
        $test_mode = read_raceinfo('test-mode', '0') === '1';
        
        // Update test mode state consistently
        $_SESSION['test-mode'] = $test_mode;
        $_SESSION['settings']['test-mode'] = $test_mode ? '1' : '0';
        
        // Load settings from database
        $stmt = $db->prepare('SELECT itemkey, itemvalue FROM RaceInfo');
        $stmt->execute();
        
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            $_SESSION['settings'][$row['itemkey']] = $row['itemvalue'];
        }
        
        // Validate current database path
        $current_db = $db->query("SELECT file FROM pragma_database_list WHERE name='main'")->fetchColumn();
        $_SESSION['current_database'] = $current_db;
        
        // error_log("Session settings updated, test_mode: " . ($test_mode ? "1" : "0") . ", db: $current_db");
        return true;
        
    } catch (PDOException $e) {
        error_log("Error loading settings: " . $e->getMessage());
        return false;
    }
}

function get_active_connection_info() {
    global $db;
    
    // error_log("Getting connection info");
    
    try {
        $base_dir = dirname(dirname(__FILE__)); 
        $year = date('Y');
        
        $prod_dir = "$base_dir/Data/$year/derbynet_rms";
        $test_dir = "$base_dir/Data/test/$year/derbynet_rms";
        
        // Get current database path
        $current_db = $db->query("SELECT file FROM pragma_database_list WHERE name='main'")->fetchColumn();
        
        // Get test mode from database with explicit '1' or '0' values
        $test_mode_value = read_raceinfo('test-mode', '0');
        $is_test_mode = $test_mode_value === '1';
        
        // error_log("Current DB: $current_db, Test Mode Value: " . ($is_test_mode ? '1' : '0'));
        
        // Define expected database paths
        $expected_path = $is_test_mode ? 
            "$test_dir/derbynet.sqlite3" : 
            "$prod_dir/derbynet.sqlite3";
        
        // Sync session state with database state
        $_SESSION['test-mode'] = $is_test_mode;
        $_SESSION['settings']['test-mode'] = $is_test_mode ? '1' : '0';
        
        return [
            'is_test_mode' => $is_test_mode,
            'current_path' => $current_db,
            'expected_path' => $expected_path,
            'status' => ($current_db === $expected_path) ? 'valid' : 'mismatch',
            'test_mode_value' => $is_test_mode ? '1' : '0'
        ];
        
    } catch (Exception $e) {
        error_log("Error getting connection info: " . $e->getMessage());
        return [
            'is_test_mode' => false,
            'current_path' => null,
            'expected_path' => null,
            'status' => 'error',
            'test_mode_value' => '0'
        ];
    }
}
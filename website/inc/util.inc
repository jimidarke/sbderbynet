<?php
require_once('inc/data.inc');

function load_all_settings_into_session() {
    global $db;
    
    try {
        // Use PDO prepare instead of db_prepare
        $stmt = $db->prepare('SELECT itemkey, itemvalue FROM RaceInfo');
        $stmt->execute();
        
        // Initialize settings array if not exists
        if (!isset($_SESSION['settings'])) {
            $_SESSION['settings'] = array();
        }

        // Store all settings in session
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            $_SESSION['settings'][$row['itemkey']] = $row['itemvalue'];
        }

        // Load test mode settings
        if (isset($_SESSION['test-mode']) && $_SESSION['test-mode']) {
            // Add test database info to session
            $base_dir = dirname(dirname(__FILE__));
            $year = date('Y');
            $test_db = "$base_dir/Data/$year/derbynet_rms/test/derbynet-test.sqlite3";
            $_SESSION['test_database'] = $test_db;
        }

        return true;
    } catch (PDOException $e) {
        error_log("Error loading settings into session: " . $e->getMessage());
        return false;
    }
}

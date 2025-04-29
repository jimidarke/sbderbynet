<?php
require_once('inc/data.inc');
require_once('inc/authorize.inc');

function check_database_status() {
    global $db;
    $response = [
        'production' => [
            'path' => null,
            'connected' => false,
            'active' => false
        ],
        'test' => [
            'path' => null,
            'connected' => false,
            'active' => false
        ]
    ];

    try {
        // Get database paths
        $base_dir = dirname(dirname(__FILE__));
        $year = date('Y');
        $data_dir = "$base_dir/Data/$year/derbynet_rms";
        $prod_db = "$data_dir/derbynet.sqlite3";
        $test_db = "$data_dir/test/derbynet-test.sqlite3";

        // Check production database
        $response['production']['path'] = $prod_db;
        $response['production']['exists'] = file_exists($prod_db);
        
        // Check test database
        $response['test']['path'] = $test_db;
        $response['test']['exists'] = file_exists($test_db);

        // Check active connection
        $current_db_path = $_SESSION['test-mode'] ?? false ? $test_db : $prod_db;
        
        if (isset($db)) {
            $db_path = $db->query("SELECT file FROM pragma_database_list WHERE name='main'")->fetchColumn();
            
            // Update connection status
            $response['production']['connected'] = ($db_path === $prod_db);
            $response['test']['connected'] = ($db_path === $test_db);
            
            // Set active flag based on test_mode
            $response['production']['active'] = !($_SESSION['test-mode'] ?? false);
            $response['test']['active'] = ($_SESSION['test-mode'] ?? false);

            // Check schema versions
            if ($response['production']['connected']) {
                $response['production']['schema_version'] = read_raceinfo('schema', 0);
            }
            if ($response['test']['connected']) {
                $response['test']['schema_version'] = read_raceinfo('schema', 0);
            }
        }

    } catch (Exception $e) {
        error_log("Database status check error: " . $e->getMessage());
        json_failure('db_status_error', $e->getMessage());
        return;
    }

    json_out('status', $response);
}

check_database_status();
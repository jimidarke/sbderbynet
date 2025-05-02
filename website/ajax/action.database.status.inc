<?php

require_once('inc/data.inc');
require_once('inc/authorize.inc');

require_once('inc/error-logging.inc');
function check_database_status() {
    global $db;
    
    try {
        $base_dir = dirname(dirname(__FILE__));
        $year = date('Y');
        
        // Define paths consistently
        $prod_dir = "$base_dir/Data/$year/derbynet_rms";
        $test_dir = "$base_dir/Data/test/$year/derbynet_rms";
        
        $prod_db = "$prod_dir/derbynet.sqlite3";
        $test_db = "$test_dir/derbynet.sqlite3";
        
        // Get current connection info
        $current_db = $db->query("SELECT file FROM pragma_database_list WHERE name='main'")->fetchColumn();
        $test_mode = read_raceinfo('test-mode', '0') === '1';
        
        $response = [
            'production' => [
                'path' => $prod_db,
                'exists' => file_exists($prod_db),
                'connected' => ($current_db === $prod_db),
                'active' => !$test_mode,
                'schema_version' => null
            ],
            'test' => [
                'path' => $test_db,
                'exists' => file_exists($test_db),
                'connected' => ($current_db === $test_db),
                'active' => $test_mode,
                'schema_version' => null
            ]
        ];
        
        // Get schema version from connected database
        $current_key = $test_mode ? 'test' : 'production';
        $response[$current_key]['schema_version'] = read_raceinfo('schema', 0);

        $result = [
            'status' => 'success',
            'current' => [
                'mode' => $test_mode ? 'test' : 'production',
                'path' => $response[$current_key]['path'],
                'schema_version' => $response[$current_key]['schema_version']
            ],
            'production' => $response['production'],
            'test' => $response['test'],
            'directories' => [
                'production' => $prod_dir,
                'test' => $test_dir
            ]
        ];

        // error_log("Database status: " . print_r($result, true));

        header('Content-Type: application/json');
        echo json_encode($result);
        exit;

    } catch (Exception $e) {
        error_log("Database status check error: " . $e->getMessage());
        header('Content-Type: application/json');
        echo json_failure('db_status_error', $e->getMessage());
    }
}

check_database_status();
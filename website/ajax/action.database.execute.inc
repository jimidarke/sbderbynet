<?php
session_start();
require_once('inc/sql-script.inc');
require_once('inc/locked.inc');
require_once('inc/details-for-setup-page.inc');
require_once('inc/fake_images.inc');
require_once('inc/schema_version.inc');
require_once('inc/error-logging.inc');
require_once('inc/photo-config.inc');

header('Content-Type: application/json');
header('Cache-Control: no-cache, must-revalidate');
ob_clean();

if (!have_permission(SET_UP_PERMISSION)) {
    json_not_authorized();
    exit;
}

$script = $_POST['script'] ?? '';
$for_test = ($_POST['for_test'] ?? '') === '1';

if (strpbrk($script, DIRECTORY_SEPARATOR . "/\\") !== false) {
    echo json_encode([
        'outcome' => [
            'summary' => 'failure',
            'code' => 'insecure',
            'description' => 'Only local SQL script execution is allowed.'
        ]
    ]);
    exit;
}

try {
    $base_dir = dirname(dirname(__FILE__));
    $year = date('Y');
    $data_dir = "$base_dir/Data/$year/derbynet_rms";
    $prod_db = "$data_dir/derbynet.sqlite3";
    $test_dir = "$data_dir/test";
    $test_db = "$test_dir/derbynet-test.sqlite3";

    $test_dirs = [
        'database' => $test_dir,
        'racers' => "$test_dir/racers",
        'cars' => "$test_dir/cars",
        'videos' => "$test_dir/videos",
        'logs' => "$test_dir/logs",
        'imagery' => "$test_dir/imagery",
        'slides' => "$test_dir/slides"
    ];

    // Ensure test database and directories always exist
    foreach ($test_dirs as $dir) {
        if (!is_dir($dir) && !@mkdir($dir, 0777, true)) {
            throw new Exception("Failed to create test directory: $dir");
        }
    }

    if (!file_exists($test_db)) {
        if (file_exists($prod_db)) {
            if (!copy($prod_db, $test_db)) {
                throw new Exception("Failed to copy production DB to test DB.");
            }
        } else {
            // Create blank test DB
            $pdo = new PDO("sqlite:$test_db");
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        }
        chmod($test_db, 0777);
        error_log("Initialized test DB: $test_db");
    }

    $_SESSION['test_database'] = $test_db;
    $_SESSION['test_directories'] = $test_dirs;

    $db_path = $for_test ? $test_db : $prod_db;

    if (!$for_test && !file_exists($prod_db)) {
        if (!is_dir($data_dir) && !@mkdir($data_dir, 0777, true)) {
            throw new Exception("Failed to create production DB directory: $data_dir");
        }
        throw new Exception("Production DB not found at $prod_db.");
    }

    $db = new PDO("sqlite:$db_path");
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    error_log("Using " . ($for_test ? "test" : "production") . " database: $db_path");

    if ($for_test) {
        $db->exec("INSERT OR REPLACE INTO RaceInfo (itemkey, itemvalue) VALUES 
            ('photo-directory', '{$test_dirs['racers']}'),
            ('car-photo-directory', '{$test_dirs['cars']}'),
            ('video-directory', '{$test_dirs['videos']}'),
            ('logs-directory', '{$test_dirs['logs']}')");
    }

    $json_out = [];

    if ($script === 'schema') {
        $saved_info = save_selected_race_info_values(RACE_INFO_KEYS_FOR_SCHEMA_SCRIPT);
        remove_fake_images($photo_dir);
        remove_fake_images($car_photo_dir);
        error_log("Running SQL script for " . ($for_test ? "test" : "production") . " DB");

        list($ok, $executed) = run_sql_script($script, $db);

        if (!$ok) {
            throw new Exception("Failed to execute schema script");
        }

        if (!empty($saved_info)) {
            restore_saved_race_info_values($saved_info);
        }

        $json_out = [
            'executed' => $executed,
            'outcome' => [
                'summary' => 'success',
                'description' => 'Schema initialized successfully for ' . ($for_test ? 'test' : 'production') . ' database'
            ],
            'details' => build_setup_page_details()
        ];
    } else {
        $json_out = [
            'outcome' => [
                'summary' => 'failure',
                'code' => 'invalid_script',
                'description' => 'Unknown script requested'
            ]
        ];
    }
} catch (Exception $e) {
    error_log("Database error: " . $e->getMessage());
    $json_out = [
        'outcome' => [
            'summary' => 'failure',
            'code' => 'database_error',
            'description' => $e->getMessage()
        ]
    ];
}

echo json_encode($json_out, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
exit;

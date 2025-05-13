<?php
session_start();
require_once 'inc/sql-script.inc';
require_once 'inc/locked.inc';
require_once 'inc/details-for-setup-page.inc';
require_once 'inc/fake_images.inc';
require_once 'inc/schema_version.inc';
// require_once 'inc/error-logging.inc';
require_once 'inc/photo-config.inc';

header('Content-Type: application/json');
header('Cache-Control: no-cache, must-revalidate');
ob_clean();

if (!have_permission(SET_UP_PERMISSION)) {
    json_not_authorized();
    exit;
}

$script = $_POST['script'] ?? '';
$for_test = ($_POST['for_test'] ?? '') === '1';

if (preg_match('/[\/\\\\]/', $script)) {
    echo json_encode([
        'outcome' => [
            'summary' => 'failure',
            'code' => 'insecure',
            'description' => 'Only local SQL script execution is allowed.'
        ]
    ]);
    exit;
}

function ensure_directories_exist(array $dirs)
{
    foreach ($dirs as $dir) {
        if (!is_dir($dir) && !@mkdir($dir, 0777, true)) {
            throw new Exception("Failed to create directory: $dir");
        }
    }
}

try {
    $baseDir = dirname(__DIR__);
    $year = date('Y');

    // Define consistent path structure
    $prod_dir = "$baseDir/Data/$year/derbynet_rms";
    $test_dir = "$baseDir/Data/test/$year/derbynet_rms";

    $prodDb = "$prod_dir/derbynet.sqlite3";
    $testDb = "$test_dir/derbynet.sqlite3";

    // Get current test mode state
    $test_mode = isset($_SESSION['test-mode']) ? $_SESSION['test-mode'] : false;

    // If initializing test database, temporarily switch mode
    if ($for_test) {
        $_SESSION['test-mode'] = true;
        $_SESSION['settings']['test-mode'] = '1';
    }

    // Define directories for current mode
    $current_dir = $for_test ? $test_dir : $prod_dir;
    $dbPath = $for_test ? $testDb : $prodDb;

    // Ensure directories exist
    $dirs = [
        'database' => $current_dir,
        'racers' => "$current_dir/racers",
        'cars' => "$current_dir/cars",
        'videos' => "$current_dir/videos",
        'logs' => "$current_dir/logs",
        'imagery' => "$current_dir/imagery",
        'slides' => "$current_dir/slides"
    ];

    ensure_directories_exist(array_values($dirs));

    // Initialize database connection
    $db = new PDO("sqlite:$dbPath");
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    if ($script === 'schema') {
        // Store current settings before reinit
        $savedInfo = save_selected_race_info_values(RACE_INFO_KEYS_FOR_SCHEMA_SCRIPT);

        [$ok, $executed] = run_sql_script($script, $db);
        // error_log("run_sql_script ok: " . $ok . ", executed: " . print_r($executed, true));
        // error_log("run_sql_script returned: " . ($ok ? "OK" : "FAIL"));

        if (!$ok) {
            error_log("Schema initialization failed. Executed statements: " . print_r($executed, true));
            throw new Exception("Schema initialization failed - check error logs for details");
        }

        error_log("About to update RaceInfo...");
        $db->beginTransaction();
        try {
            $db->exec("DELETE FROM RaceInfo WHERE itemkey = 'test-mode'");
            error_log("Deleted test-mode from RaceInfo");
            $db->exec("INSERT INTO RaceInfo (itemkey, itemvalue) VALUES ('test-mode', '" . ($for_test ? "1" : "0") . "')");
            error_log("Inserted test-mode into RaceInfo");

            // Update directory paths
            foreach ($dirs as $key => $path) {
                $db->exec("INSERT OR REPLACE INTO RaceInfo (itemkey, itemvalue) VALUES 
                    ('" . ($key === 'racers' ? 'photo-directory' :
                    ($key === 'cars' ? 'car-photo-directory' :
                        "$key-directory")) . "', '$path')");
            }

            initialize_default_partition_rule();

            $db->commit();
        } catch (Exception $e) {
            $db->rollBack();
            throw new Exception("Failed to update database settings: " . $e->getMessage());
        }

        // Restore saved settings with proper paths
        if (!empty($savedInfo)) {
            restore_saved_race_info_values($savedInfo);
        }

        // Update session state
        $_SESSION['current_database'] = $dbPath;
        $_SESSION['current_directories'] = $dirs;

        $jsonOut = [
            'executed' => $executed,
            'outcome' => [
                'summary' => 'success',
                'description' => "Schema initialized successfully for " . ($for_test ? 'test' : 'production') . " database",
                'test_mode' => $for_test
            ],
            'current_db' => $dbPath,
            'details' => build_setup_page_details()
        ];
    } elseif ($script === 'update-schema') {
        require_once 'inc/update_schema.inc';
        after_update_schema($originalSchema);
        $jsonOut = [
            'outcome' => [
                'summary' => 'success',
                'description' => 'Schema update completed'
            ],
            'details' => build_setup_page_details()
        ];
    } else {
        $jsonOut = [
            'outcome' => [
                'summary' => 'failure',
                'code' => 'invalid_script',
                'description' => 'Unknown script requested'
            ],
            'details' => build_setup_page_details()
        ];
    }
} catch (Exception $e) {
    // Restore original test mode state if needed
    if ($for_test) {
        $_SESSION['test-mode'] = $test_mode;
        $_SESSION['settings']['test-mode'] = $test_mode ? '1' : '0';
    }

    error_log("Database initialization error: " . $e->getMessage());
    $jsonOut = [
        'outcome' => [
            'summary' => 'failure',
            'code' => 'database_error',
            'description' => $e->getMessage()
        ]
    ];
}

echo json_encode($jsonOut, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
exit;

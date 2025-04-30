<?php
session_start();
require_once 'inc/sql-script.inc';
require_once 'inc/locked.inc';
require_once 'inc/details-for-setup-page.inc';
require_once 'inc/fake_images.inc';
require_once 'inc/schema_version.inc';
require_once 'inc/error-logging.inc';
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

    // Define test directories under the test path
    $testDirs = [
        'database' => $test_dir,
        'racers' => "$test_dir/racers",
        'cars' => "$test_dir/cars",
        'videos' => "$test_dir/videos",
        'logs' => "$test_dir/logs",
        'imagery' => "$test_dir/imagery",
        'slides' => "$test_dir/slides"
    ];

    // Ensure directories exist before use
    if ($for_test) {
        ensure_directories_exist($testDirs);
    } else {
        ensure_directories_exist([$prod_dir]);
    }

    if ($for_test && !file_exists($testDb)) {
        if (file_exists($prodDb)) {
            if (!copy($prodDb, $testDb)) {
                throw new Exception("Failed to copy production DB to test DB.");
            }
            chmod($testDb, 0777);
            error_log("Initialized test DB: $testDb");
        } else {
            $pdo = new PDO("sqlite:$testDb");
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            chmod($testDb, 0777);
        }
    }

    $_SESSION['test_database'] = $testDb;
    $_SESSION['test_directories'] = $testDirs;

    $_SESSION['prod_database'] = $prodDb;
    $_SESSION['prod_directories'] = [
        'database' => $prod_dir,
        'racers' => "$prod_dir/racers",
        'cars' => "$prod_dir/cars",
        'videos' => "$prod_dir/videos",
        'logs' => "$prod_dir/logs",
        'imagery' => "$prod_dir/imagery",
        'slides' => "$prod_dir/slides"
    ];

    $dbPath = $for_test ? $testDb : $prodDb;
    
    // Validate database exists
    if (!file_exists($dbPath)) {
        throw new Exception(($for_test ? "Test" : "Production") . " DB not found at $dbPath");
    }

    $db = new PDO("sqlite:$dbPath");
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    error_log("Using " . ($for_test ? "test" : "production") . " database: $dbPath");

    if ($for_test) {
        $db->exec("
            INSERT OR REPLACE INTO RaceInfo (itemkey, itemvalue) VALUES
                ('photo-directory', '{$testDirs['racers']}'),
                ('car-photo-directory', '{$testDirs['cars']}'),
                ('video-directory', '{$testDirs['videos']}'),
                ('logs-directory', '{$testDirs['logs']}')
        ");
    }

    try {
        $originalSchema = schema_version();
    } catch (PDOException $e) {
        $originalSchema = null;
    }

    $jsonOut = [];

    if ($script === 'schema') {
        $savedInfo = save_selected_race_info_values(RACE_INFO_KEYS_FOR_SCHEMA_SCRIPT);
        error_log("Running SQL script for " . ($for_test ? "test" : "production") . " DB");

        [$ok, $executed] = run_sql_script($script, $db);

        if (!$ok) {
            throw new Exception("Failed to execute schema script");
        }

        if (!empty($savedInfo)) {
            restore_saved_race_info_values($savedInfo);
        }

        $jsonOut = [
            'executed' => $executed,
            'outcome' => [
                'summary' => 'success',
                'description' => "Schema initialized successfully for " . ($for_test ? 'test' : 'production') . " database"
            ],
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
    error_log("Database error: " . $e->getMessage());
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

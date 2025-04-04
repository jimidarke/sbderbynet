<?php


///////////////////////////////////////////////
// 
//  Error Reporting For Development Enviroment
// 
///////////////////////////////////////////////

error_reporting(E_ALL);
ini_set('display_errors', 1);


$log_dir = __DIR__ . '/error/error-logs';
if (!is_dir($log_dir)) {
    mkdir($log_dir, 0777, true); // Creates directory with full permissions
}

ini_set('log_errors', 1);
ini_set('error_log', $log_dir . '/error.log');

// error_log("Running schema update... Current schema version: " . schema_version());


// error_log("Test error log entry at " . date('Y-m-d H:i:s') . " in " . __FILE__ . " on line " . __LINE__);


////////////////////////////////////////////////////////
// 
//  Error Reporting For Development Enviroment Ends here
// 
////////////////////////////////////////////////////////


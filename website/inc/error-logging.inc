<?php
// Enable error reporting for development
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Set up error logging
$log_dir = __DIR__ . '/logs';

ini_set('log_errors', 1);
ini_set('error_log', $log_dir . '/error.log');

// Custom error handler for logging
set_error_handler(function ($errno, $errstr, $errfile, $errline) {
    $message = "[Error] [$errno] $errstr in $errfile on line $errline";
    error_log($message);
    return false; // Allow PHP's default error handler to continue
});

// Exception handler for uncaught exceptions
set_exception_handler(function ($exception) {
    $message = "[Exception] " . $exception->getMessage() . " in " . $exception->getFile() . " on line " . $exception->getLine();
    error_log($message);
});

// Shutdown function to catch fatal errors
register_shutdown_function(function () {
    $error = error_get_last();
    if ($error && ($error['type'] === E_ERROR || $error['type'] === E_PARSE)) {
        $message = "[Fatal Error] " . $error['message'] . " in " . $error['file'] . " on line " . $error['line'];
        error_log($message);
    }
});




// To Record errors: require_once('inc/error-logging.inc'); in a top-level of files
// require_once('inc/error-logging.inc');
?>
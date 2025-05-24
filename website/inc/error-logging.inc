<?php
/**
 * DerbyNet Centralized Error Logging
 * 
 * This file provides centralized error handling and logging for all PHP components.
 * It integrates with the rsyslog system and provides production/debug toggles.
 * 
 * Version: 1.0.0
 * Date: 2025-05-24
 * 
 * Updated from basic error logging to centralized rsyslog integration
 */

// Production mode toggle - set to false for production deployment
// TODO: Set DERBY_PHP_DEBUG=false in production environment
$DERBY_PHP_DEBUG = (getenv('DERBY_PHP_DEBUG') !== false) ? 
    filter_var(getenv('DERBY_PHP_DEBUG'), FILTER_VALIDATE_BOOLEAN) : true;

// Log level configuration based on environment
$DERBY_PHP_LOG_LEVEL = getenv('DERBY_PHP_LOG_LEVEL') ?: ($DERBY_PHP_DEBUG ? 'DEBUG' : 'WARNING');

/**
 * Initialize PHP error logging for DerbyNet
 */
function derby_init_error_logging() {
    global $DERBY_PHP_DEBUG, $DERBY_PHP_LOG_LEVEL;
    
    // Configure error reporting based on debug mode
    if ($DERBY_PHP_DEBUG) {
        // Development/Debug mode - show all errors
        error_reporting(E_ALL);
        ini_set('display_errors', '1');
        ini_set('display_startup_errors', '1');
        ini_set('log_errors', '1');
    } else {
        // Production mode - log errors but don't display them
        error_reporting(E_ERROR | E_WARNING | E_PARSE);
        ini_set('display_errors', '0');
        ini_set('display_startup_errors', '0');
        ini_set('log_errors', '1');
    }
    
    // Set custom error log destination
    // Try to use syslog first, fall back to file
    if (function_exists('openlog')) {
        // Use syslog for centralized logging
        ini_set('log_errors_max_len', '0'); // No limit for syslog
        openlog('derbynet-php', LOG_PID | LOG_PERROR, LOG_LOCAL0);
        
        // Set custom error handler for syslog
        set_error_handler('derby_error_handler');
        set_exception_handler('derby_exception_handler');
        register_shutdown_function('derby_fatal_error_handler');
    } else {
        // Fallback to file logging (maintain compatibility with old system)
        $log_dir = __DIR__ . '/../error/error-logs';
        if (!is_dir($log_dir)) {
            mkdir($log_dir, 0755, true);
        }
        
        ini_set('error_log', $log_dir . '/error.log');
        
        // Use simplified handlers for file logging
        set_error_handler('derby_simple_error_handler');
        set_exception_handler('derby_simple_exception_handler');
        register_shutdown_function('derby_simple_fatal_handler');
    }
    
    // Set memory and time limits for better error handling
    if ($DERBY_PHP_DEBUG) {
        ini_set('memory_limit', '256M');
        set_time_limit(60);
    } else {
        ini_set('memory_limit', '128M');
        set_time_limit(30);
    }
}

/**
 * Custom error handler for syslog integration
 */
function derby_error_handler($errno, $errstr, $errfile, $errline) {
    global $DERBY_PHP_DEBUG;
    
    // Don't handle errors that are suppressed with @
    if (!(error_reporting() & $errno)) {
        return false;
    }
    
    // Map PHP error levels to syslog priorities
    $priority_map = [
        E_ERROR => LOG_ERR,
        E_WARNING => LOG_WARNING,
        E_PARSE => LOG_ERR,
        E_NOTICE => LOG_NOTICE,
        E_CORE_ERROR => LOG_ERR,
        E_CORE_WARNING => LOG_WARNING,
        E_COMPILE_ERROR => LOG_ERR,
        E_COMPILE_WARNING => LOG_WARNING,
        E_USER_ERROR => LOG_ERR,
        E_USER_WARNING => LOG_WARNING,
        E_USER_NOTICE => LOG_NOTICE,
        E_STRICT => LOG_NOTICE,
        E_RECOVERABLE_ERROR => LOG_ERR,
        E_DEPRECATED => LOG_NOTICE,
        E_USER_DEPRECATED => LOG_NOTICE,
    ];
    
    $priority = $priority_map[$errno] ?? LOG_WARNING;
    $error_type = derby_get_error_type($errno);
    
    // Format error message with context
    $message = sprintf(
        "[%s] %s in %s:%d",
        $error_type,
        $errstr,
        basename($errfile),
        $errline
    );
    
    // Add request context in debug mode
    if ($DERBY_PHP_DEBUG) {
        $context = [
            'request_uri' => $_SERVER['REQUEST_URI'] ?? 'CLI',
            'request_method' => $_SERVER['REQUEST_METHOD'] ?? 'CLI',
            'remote_addr' => $_SERVER['REMOTE_ADDR'] ?? 'Unknown',
        ];
        $message .= ' Context: ' . json_encode($context);
    }
    
    // Log to syslog
    syslog($priority, $message);
    
    // Don't execute PHP internal error handler
    return true;
}

/**
 * Custom exception handler for syslog
 */
function derby_exception_handler($exception) {
    $message = sprintf(
        "[EXCEPTION] %s: %s in %s:%d",
        get_class($exception),
        $exception->getMessage(),
        basename($exception->getFile()),
        $exception->getLine()
    );
    
    syslog(LOG_ERR, $message);
    
    global $DERBY_PHP_DEBUG;
    if ($DERBY_PHP_DEBUG) {
        echo "<h1>Exception</h1><pre>$message</pre>";
    } else {
        echo "<h1>Application Error</h1><p>An error occurred. Please contact support.</p>";
    }
}

/**
 * Fatal error handler for syslog (called on shutdown)
 */
function derby_fatal_error_handler() {
    $error = error_get_last();
    
    if ($error !== null && in_array($error['type'], [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR])) {
        $message = sprintf(
            "[FATAL] %s in %s:%d",
            $error['message'],
            basename($error['file']),
            $error['line']
        );
        
        syslog(LOG_CRIT, $message);
    }
}

/**
 * Simple file-based error handlers (fallback)
 */
function derby_simple_error_handler($errno, $errstr, $errfile, $errline) {
    $message = "[Error] [$errno] $errstr in $errfile on line $errline";
    error_log($message);
    return false;
}

function derby_simple_exception_handler($exception) {
    $message = "[Exception] " . $exception->getMessage() . " in " . $exception->getFile() . " on line " . $exception->getLine();
    error_log($message);
}

function derby_simple_fatal_handler() {
    $error = error_get_last();
    if ($error && ($error['type'] === E_ERROR || $error['type'] === E_PARSE)) {
        $message = "[Fatal Error] " . $error['message'] . " in " . $error['file'] . " on line " . $error['line'];
        error_log($message);
    }
}

/**
 * Get human-readable error type
 */
function derby_get_error_type($errno) {
    $types = [
        E_ERROR => 'ERROR',
        E_WARNING => 'WARNING',
        E_PARSE => 'PARSE',
        E_NOTICE => 'NOTICE',
        E_CORE_ERROR => 'CORE_ERROR',
        E_CORE_WARNING => 'CORE_WARNING',
        E_COMPILE_ERROR => 'COMPILE_ERROR',
        E_COMPILE_WARNING => 'COMPILE_WARNING',
        E_USER_ERROR => 'USER_ERROR',
        E_USER_WARNING => 'USER_WARNING',
        E_USER_NOTICE => 'USER_NOTICE',
        E_STRICT => 'STRICT',
        E_RECOVERABLE_ERROR => 'RECOVERABLE_ERROR',
        E_DEPRECATED => 'DEPRECATED',
        E_USER_DEPRECATED => 'USER_DEPRECATED',
    ];
    
    return $types[$errno] ?? 'UNKNOWN';
}

/**
 * Convenience logging functions for application use
 */
function derby_log_error($message, $context = []) {
    if (function_exists('syslog')) {
        $formatted_message = $message;
        if (!empty($context)) {
            $formatted_message .= ' Context: ' . json_encode($context);
        }
        syslog(LOG_ERR, "[ERROR] $formatted_message");
    } else {
        error_log("[ERROR] $message");
    }
}

function derby_log_warning($message, $context = []) {
    if (function_exists('syslog')) {
        $formatted_message = $message;
        if (!empty($context)) {
            $formatted_message .= ' Context: ' . json_encode($context);
        }
        syslog(LOG_WARNING, "[WARNING] $formatted_message");
    } else {
        error_log("[WARNING] $message");
    }
}

function derby_log_info($message, $context = []) {
    global $DERBY_PHP_DEBUG;
    if ($DERBY_PHP_DEBUG) {
        if (function_exists('syslog')) {
            $formatted_message = $message;
            if (!empty($context)) {
                $formatted_message .= ' Context: ' . json_encode($context);
            }
            syslog(LOG_INFO, "[INFO] $formatted_message");
        } else {
            error_log("[INFO] $message");
        }
    }
}

// Initialize error logging when this file is included
derby_init_error_logging();

// Log that error logging has been initialized
derby_log_info("DerbyNet PHP error logging initialized", [
    'debug_mode' => $DERBY_PHP_DEBUG,
    'log_level' => $DERBY_PHP_LOG_LEVEL,
    'script' => basename($_SERVER['SCRIPT_NAME'] ?? 'CLI')
]);

// To Record errors: require_once('inc/error-logging.inc'); in a top-level of files
// require_once('inc/error-logging.inc');
?>
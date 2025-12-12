<?php
/**
 * DerbyNet Unified Logging - Text Format
 *
 * Centralized logging for all PHP components.
 * Writes human-readable text format to unified log file.
 *
 * Version: 2.0.0
 * Date: 2025-12-08
 *
 * OUTPUT FORMAT:
 *     2025-12-08 14:35:22.123 DEVICE:LEVEL [filename:line] message
 *
 * USAGE:
 *     require_once('inc/error-logging.inc');
 *
 *     derby_log_info("Heat started");
 *     derby_log_warning("Slow response detected");
 *     derby_log_error("Database connection failed");
 */

// ============================================================================
// CONFIGURATION - Change these values as needed
// ============================================================================
define('DERBY_TIMEZONE', 'America/Edmonton');
define('DERBY_LOG_FILE', '/var/log/derbynet.log');

// Set timezone for all date functions
date_default_timezone_set(DERBY_TIMEZONE);

// Debug mode from environment
$DERBY_PHP_DEBUG = (getenv('DERBY_PHP_DEBUG') !== false) ?
    filter_var(getenv('DERBY_PHP_DEBUG'), FILTER_VALIDATE_BOOLEAN) : true;

// Device ID from environment or hostname
$DERBY_DEVICE_ID = strtoupper(getenv('DERBY_DEVICE_ID') ?: gethostname());

/**
 * Get timestamp with milliseconds in configured timezone.
 *
 * @return string Formatted timestamp: YYYY-MM-DD HH:MM:SS.mmm
 */
function derby_get_timestamp() {
    $now = microtime(true);
    $ms = sprintf('%03d', ($now - floor($now)) * 1000);
    return date('Y-m-d H:i:s', (int)$now) . '.' . $ms;
}

/**
 * Write a log entry in text format to the unified log file.
 *
 * Format: timestamp DEVICE:LEVEL [filename:line] message
 *
 * @param string $level Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
 * @param string $message Log message
 */
function derby_log($level, $message) {
    global $DERBY_DEVICE_ID, $DERBY_PHP_DEBUG;

    // Skip DEBUG logs in production mode
    if ($level === 'DEBUG' && !$DERBY_PHP_DEBUG) {
        return;
    }

    // Get caller info
    $backtrace = debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS, 2);
    $caller = $backtrace[1] ?? $backtrace[0] ?? [];
    $file = isset($caller['file']) ? basename($caller['file']) : 'unknown';
    $line = $caller['line'] ?? 0;

    // Build log line
    $log_line = sprintf(
        "%s %s:%s [%s:%d] %s\n",
        derby_get_timestamp(),
        $DERBY_DEVICE_ID,
        strtoupper($level),
        $file,
        $line,
        $message
    );

    // Ensure directory exists
    $log_dir = dirname(DERBY_LOG_FILE);
    if (!is_dir($log_dir)) {
        @mkdir($log_dir, 0755, true);
    }

    // Append to file (atomic write with locking)
    @file_put_contents(DERBY_LOG_FILE, $log_line, FILE_APPEND | LOCK_EX);
}

/**
 * Convenience logging functions
 */
function derby_log_debug($message) {
    derby_log('DEBUG', $message);
}

function derby_log_info($message) {
    derby_log('INFO', $message);
}

function derby_log_warning($message) {
    derby_log('WARNING', $message);
}

function derby_log_error($message) {
    derby_log('ERROR', $message);
}

function derby_log_critical($message) {
    derby_log('CRITICAL', $message);
}

/**
 * Initialize PHP error logging
 */
function derby_init_error_logging() {
    global $DERBY_PHP_DEBUG;

    // Configure error reporting based on debug mode
    if ($DERBY_PHP_DEBUG) {
        error_reporting(E_ALL);
        ini_set('display_errors', '1');
        ini_set('display_startup_errors', '1');
    } else {
        error_reporting(E_ERROR | E_WARNING | E_PARSE);
        ini_set('display_errors', '0');
        ini_set('display_startup_errors', '0');
    }

    ini_set('log_errors', '1');

    // Set custom error handlers
    set_error_handler('derby_error_handler');
    set_exception_handler('derby_exception_handler');
    register_shutdown_function('derby_fatal_error_handler');

    // Memory and time limits
    if ($DERBY_PHP_DEBUG) {
        ini_set('memory_limit', '256M');
        set_time_limit(60);
    } else {
        ini_set('memory_limit', '128M');
        set_time_limit(30);
    }
}

/**
 * Map PHP error number to level string
 */
function derby_errno_to_level($errno) {
    $map = [
        E_ERROR => 'ERROR',
        E_WARNING => 'WARNING',
        E_PARSE => 'ERROR',
        E_NOTICE => 'INFO',
        E_CORE_ERROR => 'CRITICAL',
        E_CORE_WARNING => 'WARNING',
        E_COMPILE_ERROR => 'ERROR',
        E_COMPILE_WARNING => 'WARNING',
        E_USER_ERROR => 'ERROR',
        E_USER_WARNING => 'WARNING',
        E_USER_NOTICE => 'INFO',
        E_RECOVERABLE_ERROR => 'ERROR',
        E_DEPRECATED => 'DEBUG',
        E_USER_DEPRECATED => 'DEBUG',
        // E_STRICT (2048) was deprecated in PHP 8.4 - use numeric value for compatibility
        2048 => 'DEBUG',
    ];
    return $map[$errno] ?? 'WARNING';
}

/**
 * Custom error handler - writes to log file
 */
function derby_error_handler($errno, $errstr, $errfile, $errline) {
    // Don't handle errors suppressed with @
    if (!(error_reporting() & $errno)) {
        return false;
    }

    $level = derby_errno_to_level($errno);
    $file = basename($errfile);

    // Log with location from error, not from caller
    global $DERBY_DEVICE_ID;
    $log_line = sprintf(
        "%s %s:%s [%s:%d] %s\n",
        derby_get_timestamp(),
        $DERBY_DEVICE_ID,
        $level,
        $file,
        $errline,
        $errstr
    );

    @file_put_contents(DERBY_LOG_FILE, $log_line, FILE_APPEND | LOCK_EX);

    // Don't execute PHP internal error handler
    return true;
}

/**
 * Custom exception handler - writes to log file
 */
function derby_exception_handler($exception) {
    global $DERBY_DEVICE_ID;

    $file = basename($exception->getFile());
    $line = $exception->getLine();
    $message = get_class($exception) . ': ' . $exception->getMessage();

    $log_line = sprintf(
        "%s %s:ERROR [%s:%d] %s\n",
        derby_get_timestamp(),
        $DERBY_DEVICE_ID,
        $file,
        $line,
        $message
    );

    @file_put_contents(DERBY_LOG_FILE, $log_line, FILE_APPEND | LOCK_EX);

    global $DERBY_PHP_DEBUG;
    if ($DERBY_PHP_DEBUG) {
        echo "<h1>Exception</h1><pre>" . htmlspecialchars($exception->getMessage()) . "</pre>";
        echo "<pre>" . htmlspecialchars($exception->getTraceAsString()) . "</pre>";
    } else {
        echo "<h1>Application Error</h1><p>An error occurred. Please contact support.</p>";
    }
}

/**
 * Fatal error handler - called on shutdown
 */
function derby_fatal_error_handler() {
    $error = error_get_last();

    if ($error !== null && in_array($error['type'], [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR])) {
        global $DERBY_DEVICE_ID;

        $file = basename($error['file']);
        $log_line = sprintf(
            "%s %s:CRITICAL [%s:%d] %s\n",
            derby_get_timestamp(),
            $DERBY_DEVICE_ID,
            $file,
            $error['line'],
            $error['message']
        );

        @file_put_contents(DERBY_LOG_FILE, $log_line, FILE_APPEND | LOCK_EX);
    }
}

// Initialize error logging when this file is included
derby_init_error_logging();
?>

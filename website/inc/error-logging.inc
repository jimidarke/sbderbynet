<?php
/**
 * DerbyNet Unified Logging - Text + JSON Format
 *
 * Centralized logging for all PHP components.
 * Writes human-readable text format and parseable JSON (JSONL) to unified log files.
 *
 * Version: 3.1.0
 * Date: 2026-01-15
 *
 * CHANGELOG v3.1.0:
 *     - Added correlation ID support for request tracing across components
 *     - Added session ID for grouping related operations
 *     - Added sequence numbers for log ordering during sync
 *     - Added sync metadata for cloud transmission
 *
 * TIME SYNCHRONIZATION:
 *     All devices MUST sync time from the DerbyPi server (192.168.100.10).
 *     DerbyPi syncs via internet NTP or battery-backed RTC for offline use.
 *     Logs use local timezone (not UTC) for operator convenience.
 *     See extras/soapbox/infra/server/LOGGING.md for complete documentation.
 *
 * TEXT OUTPUT FORMAT:
 *     2025-12-08 14:35:22.123 DEVICE:LEVEL [filename:line] message
 *
 * JSON OUTPUT FORMAT (JSONL - one JSON object per line):
 *     {"ts": "2025-12-08T14:35:22.123-07:00", "level": "ERROR", "device": "SERVER1", ...}
 *
 * USAGE:
 *     require_once('inc/error-logging.inc');
 *
 *     derby_log_info("Heat started");
 *     derby_log_warning("Slow response detected");
 *     derby_log_error("Database connection failed", 'ERR-DB-201', ['query' => 'SELECT...']);
 */

// ============================================================================
// CONFIGURATION - Change these values as needed
// ============================================================================
define('DERBY_TIMEZONE', 'America/Edmonton');
define('DERBY_LOG_FILE', '/var/log/derbynet.log');
define('DERBY_JSON_FILE', '/var/log/derbynet.jsonl');

// Set timezone for all date functions
date_default_timezone_set(DERBY_TIMEZONE);

// Debug mode from environment
$DERBY_PHP_DEBUG = (getenv('DERBY_PHP_DEBUG') !== false) ?
    filter_var(getenv('DERBY_PHP_DEBUG'), FILTER_VALIDATE_BOOLEAN) : true;

// JSON logging mode from environment (default: true)
$DERBY_JSON_LOG = (getenv('DERBY_JSON_LOG') !== false) ?
    filter_var(getenv('DERBY_JSON_LOG'), FILTER_VALIDATE_BOOLEAN) : true;

// Device ID from environment or hostname
$DERBY_DEVICE_ID = strtoupper(getenv('DERBY_DEVICE_ID') ?: gethostname());

// ============================================================================
// CORRELATION CONTEXT - Request tracing across components
// ============================================================================

// Global sequence counter for log ordering
$_DERBY_SEQUENCE = 0;

// Correlation context storage (per-request)
$_DERBY_CORRELATION = [
    'corr_id' => null,
    'session_id' => null,
    'source' => null,
];

/**
 * Set correlation ID for request tracing.
 *
 * Call at the start of request processing to trace the request
 * across PHP → Python → MQTT → Timer components.
 *
 * @param string|null $corr_id Correlation ID (auto-generated if null)
 * @param string|null $session_id Optional session/batch ID
 * @param string|null $source Source component identifier
 * @return string The correlation ID being used
 */
function derby_set_correlation_id($corr_id = null, $session_id = null, $source = null) {
    global $_DERBY_CORRELATION;

    if ($corr_id === null) {
        // Generate short UUID (12 chars for readability)
        $corr_id = substr(bin2hex(random_bytes(6)), 0, 12);
    }

    $_DERBY_CORRELATION['corr_id'] = $corr_id;
    $_DERBY_CORRELATION['session_id'] = $session_id;
    $_DERBY_CORRELATION['source'] = $source;

    return $corr_id;
}

/**
 * Get current correlation ID.
 *
 * @return string|null Current correlation ID or null if not set
 */
function derby_get_correlation_id() {
    global $_DERBY_CORRELATION;
    return $_DERBY_CORRELATION['corr_id'];
}

/**
 * Get full correlation context as array.
 *
 * @return array Correlation context with corr_id, session_id, source, seq
 */
function derby_get_correlation_context() {
    global $_DERBY_CORRELATION, $_DERBY_SEQUENCE;

    $ctx = [];

    if ($_DERBY_CORRELATION['corr_id']) {
        $ctx['corr_id'] = $_DERBY_CORRELATION['corr_id'];
    }

    if ($_DERBY_CORRELATION['session_id']) {
        $ctx['session_id'] = $_DERBY_CORRELATION['session_id'];
    }

    if ($_DERBY_CORRELATION['source']) {
        $ctx['source'] = $_DERBY_CORRELATION['source'];
    }

    // Always add sequence for ordering
    $_DERBY_SEQUENCE++;
    $ctx['seq'] = $_DERBY_SEQUENCE;

    return $ctx;
}

/**
 * Clear correlation context after request processing.
 */
function derby_clear_correlation_id() {
    global $_DERBY_CORRELATION;
    $_DERBY_CORRELATION = [
        'corr_id' => null,
        'session_id' => null,
        'source' => null,
    ];
}

/**
 * Auto-initialize correlation ID from request headers or generate new one.
 *
 * Checks for X-Correlation-ID header (from Python/MQTT components),
 * or generates a new one for fresh requests.
 */
function derby_auto_init_correlation() {
    // Check for correlation ID in request header
    $headers = function_exists('getallheaders') ? getallheaders() : [];
    $corr_id = $headers['X-Correlation-ID'] ?? $headers['x-correlation-id'] ?? null;

    // Check for correlation ID in request body (for AJAX)
    if (!$corr_id && isset($_POST['corr_id'])) {
        $corr_id = $_POST['corr_id'];
    }

    // Determine source from request
    $source = 'php';
    if (isset($_SERVER['HTTP_X_REQUESTED_WITH']) && $_SERVER['HTTP_X_REQUESTED_WITH'] === 'XMLHttpRequest') {
        $source = 'ajax';
    }

    derby_set_correlation_id($corr_id, null, $source);
}

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
 * Get ISO 8601 timestamp with timezone offset.
 *
 * @return string Formatted timestamp: YYYY-MM-DDTHH:MM:SS.mmm+HH:MM
 */
function derby_get_iso8601_timestamp() {
    $now = microtime(true);
    $ms = sprintf('%03d', ($now - floor($now)) * 1000);
    return date('Y-m-d\TH:i:s', (int)$now) . '.' . $ms . date('P');
}

/**
 * Write a log entry to both text and JSON log files.
 *
 * Text Format: timestamp DEVICE:LEVEL [filename:line] message
 * JSON Format: {"ts": "...", "level": "...", "device": "...", ...}
 *
 * @param string $level Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
 * @param string $message Log message
 * @param string|null $error_code Optional error code (e.g., 'ERR-DB-201')
 * @param array|null $context Optional context data
 */
function derby_log($level, $message, $error_code = null, $context = null) {
    global $DERBY_DEVICE_ID, $DERBY_PHP_DEBUG, $DERBY_JSON_LOG;

    // Skip DEBUG logs in production mode
    if ($level === 'DEBUG' && !$DERBY_PHP_DEBUG) {
        return;
    }

    // Get caller info
    $backtrace = debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS, 2);
    $caller = $backtrace[1] ?? $backtrace[0] ?? [];
    $file = isset($caller['file']) ? basename($caller['file']) : 'unknown';
    $line = $caller['line'] ?? 0;

    // Get correlation context
    $corr_ctx = derby_get_correlation_context();
    $corr_id = $corr_ctx['corr_id'] ?? null;

    // Build text log line (include correlation ID if present)
    $display_message = $message;
    if ($error_code) {
        $display_message = "[$error_code] $message";
    }

    $corr_prefix = $corr_id ? "[$corr_id] " : '';

    $log_line = sprintf(
        "%s %s:%s [%s:%d] %s%s\n",
        derby_get_timestamp(),
        $DERBY_DEVICE_ID,
        strtoupper($level),
        $file,
        $line,
        $corr_prefix,
        $display_message
    );

    // Ensure directory exists
    $log_dir = dirname(DERBY_LOG_FILE);
    if (!is_dir($log_dir)) {
        @mkdir($log_dir, 0755, true);
    }

    // Append text to file (atomic write with locking)
    @file_put_contents(DERBY_LOG_FILE, $log_line, FILE_APPEND | LOCK_EX);

    // Write JSON if enabled
    if ($DERBY_JSON_LOG) {
        $json_entry = [
            'ts' => derby_get_iso8601_timestamp(),
            'level' => strtoupper($level),
            'device' => $DERBY_DEVICE_ID,
            'component' => 'php',
            'file' => $file,
            'line' => $line,
            'msg' => $message,
        ];

        // Add correlation context
        $json_entry = array_merge($json_entry, $corr_ctx);

        if ($error_code) {
            $json_entry['code'] = $error_code;
        }

        if ($context) {
            $json_entry['ctx'] = $context;
        }

        // Add sync metadata for cloud sync service
        $json_entry['sync_status'] = 'pending';

        $json_line = json_encode($json_entry, JSON_UNESCAPED_SLASHES) . "\n";

        $json_dir = dirname(DERBY_JSON_FILE);
        if (!is_dir($json_dir)) {
            @mkdir($json_dir, 0755, true);
        }

        @file_put_contents(DERBY_JSON_FILE, $json_line, FILE_APPEND | LOCK_EX);
    }
}

/**
 * Convenience logging functions
 *
 * @param string $message Log message
 * @param string|null $error_code Optional error code (e.g., 'ERR-DB-201')
 * @param array|null $context Optional context data
 */
function derby_log_debug($message, $error_code = null, $context = null) {
    derby_log('DEBUG', $message, $error_code, $context);
}

function derby_log_info($message, $error_code = null, $context = null) {
    derby_log('INFO', $message, $error_code, $context);
}

function derby_log_warning($message, $error_code = null, $context = null) {
    derby_log('WARNING', $message, $error_code, $context);
}

function derby_log_error($message, $error_code = null, $context = null) {
    derby_log('ERROR', $message, $error_code, $context);
}

function derby_log_critical($message, $error_code = null, $context = null) {
    derby_log('CRITICAL', $message, $error_code, $context);
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
 * Custom error handler - writes to both text and JSON log files
 */
function derby_error_handler($errno, $errstr, $errfile, $errline) {
    // Don't handle errors suppressed with @
    if (!(error_reporting() & $errno)) {
        return false;
    }

    $level = derby_errno_to_level($errno);
    $file = basename($errfile);

    // Log with location from error, not from caller
    global $DERBY_DEVICE_ID, $DERBY_JSON_LOG;

    // Text log
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

    // JSON log
    if ($DERBY_JSON_LOG) {
        $json_entry = [
            'ts' => derby_get_iso8601_timestamp(),
            'level' => $level,
            'device' => $DERBY_DEVICE_ID,
            'component' => 'php',
            'file' => $file,
            'line' => $errline,
            'msg' => $errstr,
            'code' => 'ERR-SYS-201', // PHP error
        ];

        $json_line = json_encode($json_entry, JSON_UNESCAPED_SLASHES) . "\n";
        @file_put_contents(DERBY_JSON_FILE, $json_line, FILE_APPEND | LOCK_EX);
    }

    // Don't execute PHP internal error handler
    return true;
}

/**
 * Custom exception handler - writes to both text and JSON log files
 */
function derby_exception_handler($exception) {
    global $DERBY_DEVICE_ID, $DERBY_JSON_LOG;

    $file = basename($exception->getFile());
    $line = $exception->getLine();
    $message = get_class($exception) . ': ' . $exception->getMessage();

    // Text log
    $log_line = sprintf(
        "%s %s:ERROR [%s:%d] %s\n",
        derby_get_timestamp(),
        $DERBY_DEVICE_ID,
        $file,
        $line,
        $message
    );

    @file_put_contents(DERBY_LOG_FILE, $log_line, FILE_APPEND | LOCK_EX);

    // JSON log
    if ($DERBY_JSON_LOG) {
        $json_entry = [
            'ts' => derby_get_iso8601_timestamp(),
            'level' => 'ERROR',
            'device' => $DERBY_DEVICE_ID,
            'component' => 'php',
            'file' => $file,
            'line' => $line,
            'msg' => $message,
            'code' => 'ERR-SYS-202', // PHP exception
            'ctx' => [
                'exception_class' => get_class($exception),
                'trace' => $exception->getTraceAsString(),
            ],
        ];

        $json_line = json_encode($json_entry, JSON_UNESCAPED_SLASHES) . "\n";
        @file_put_contents(DERBY_JSON_FILE, $json_line, FILE_APPEND | LOCK_EX);
    }

    global $DERBY_PHP_DEBUG;
    if ($DERBY_PHP_DEBUG) {
        echo "<h1>Exception</h1><pre>" . htmlspecialchars($exception->getMessage()) . "</pre>";
        echo "<pre>" . htmlspecialchars($exception->getTraceAsString()) . "</pre>";
    } else {
        echo "<h1>Application Error</h1><p>An error occurred. Please contact support.</p>";
    }
}

/**
 * Fatal error handler - called on shutdown, writes to both text and JSON log files
 */
function derby_fatal_error_handler() {
    $error = error_get_last();

    if ($error !== null && in_array($error['type'], [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR])) {
        global $DERBY_DEVICE_ID, $DERBY_JSON_LOG;

        $file = basename($error['file']);

        // Text log
        $log_line = sprintf(
            "%s %s:CRITICAL [%s:%d] %s\n",
            derby_get_timestamp(),
            $DERBY_DEVICE_ID,
            $file,
            $error['line'],
            $error['message']
        );

        @file_put_contents(DERBY_LOG_FILE, $log_line, FILE_APPEND | LOCK_EX);

        // JSON log
        if ($DERBY_JSON_LOG) {
            $json_entry = [
                'ts' => derby_get_iso8601_timestamp(),
                'level' => 'CRITICAL',
                'device' => $DERBY_DEVICE_ID,
                'component' => 'php',
                'file' => $file,
                'line' => $error['line'],
                'msg' => $error['message'],
                'code' => 'ERR-SYS-301', // PHP fatal error
                'ctx' => [
                    'error_type' => $error['type'],
                ],
            ];

            $json_line = json_encode($json_entry, JSON_UNESCAPED_SLASHES) . "\n";
            @file_put_contents(DERBY_JSON_FILE, $json_line, FILE_APPEND | LOCK_EX);
        }
    }
}

// Initialize error logging when this file is included
derby_init_error_logging();

// Auto-initialize correlation ID for request tracing
derby_auto_init_correlation();
?>

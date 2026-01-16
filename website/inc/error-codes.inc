<?php
/**
 * DerbyNet Unified Error Code Registry
 *
 * Standardized error codes for all Derby infrastructure components.
 * Mirrors the Python registry at extras/soapbox/infra/server/error_codes.py
 *
 * Version: 1.0.0
 * Date: 2026-01-14
 *
 * ERROR CODE FORMAT:
 *     ERR-{CATEGORY}-{NUMBER}
 *
 * CATEGORIES:
 *     AUTH - Authentication, permissions, session errors
 *     VAL  - Input validation, format errors
 *     DB   - Database operations, SQL errors
 *     HW   - Hardware (timers, sensors, LEDs)
 *     NET  - Network (MQTT, HTTP, connectivity)
 *     RACE - Race state, timing logic
 *     SYS  - System (memory, disk, process)
 *     CFG  - Configuration errors
 *
 * SEVERITY BY NUMBER:
 *     1xx = WARNING (monitor, non-critical)
 *     2xx = ERROR (operation failed, may retry)
 *     3xx = CRITICAL (immediate attention required, triggers alert)
 *
 * USAGE:
 *     require_once('inc/error-codes.inc');
 *
 *     $details = get_error_details('ERR-HW-301');
 *     echo $details['msg'];  // "Device offline"
 *
 *     // Map legacy code to standardized code
 *     $new_code = map_legacy_code('notauthorized');  // Returns 'ERR-AUTH-202'
 */

// =============================================================================
// ERROR CODE REGISTRY
// =============================================================================

$ERROR_CODES = [
    // =========================================================================
    // AUTH - Authentication & Authorization (1xx-3xx)
    // =========================================================================
    'ERR-AUTH-101' => [
        'level' => 'WARNING',
        'msg' => 'Session expiring soon',
        'alert' => false,
        'description' => 'User session will expire in less than 5 minutes'
    ],
    'ERR-AUTH-102' => [
        'level' => 'WARNING',
        'msg' => 'Session expired',
        'alert' => false,
        'description' => 'User session has expired, re-authentication required'
    ],
    'ERR-AUTH-201' => [
        'level' => 'ERROR',
        'msg' => 'Authentication failed',
        'alert' => false,
        'description' => 'Invalid credentials or authentication token'
    ],
    'ERR-AUTH-202' => [
        'level' => 'ERROR',
        'msg' => 'Not authorized',
        'alert' => false,
        'description' => 'User lacks permission for requested action'
    ],
    'ERR-AUTH-203' => [
        'level' => 'ERROR',
        'msg' => 'Invalid role',
        'alert' => false,
        'description' => 'Specified role does not exist or is not valid'
    ],

    // =========================================================================
    // VAL - Validation Errors (1xx-3xx)
    // =========================================================================
    'ERR-VAL-101' => [
        'level' => 'WARNING',
        'msg' => 'Optional field missing',
        'alert' => false,
        'description' => 'Optional field not provided, using default'
    ],
    'ERR-VAL-201' => [
        'level' => 'ERROR',
        'msg' => 'Missing required field',
        'alert' => false,
        'description' => 'A required field was not provided in the request'
    ],
    'ERR-VAL-202' => [
        'level' => 'ERROR',
        'msg' => 'Missing required arguments',
        'alert' => false,
        'description' => 'Required arguments not provided'
    ],
    'ERR-VAL-203' => [
        'level' => 'ERROR',
        'msg' => 'Invalid format',
        'alert' => false,
        'description' => 'Field value does not match expected format'
    ],
    'ERR-VAL-204' => [
        'level' => 'ERROR',
        'msg' => 'Value out of range',
        'alert' => false,
        'description' => 'Numeric value outside acceptable range'
    ],
    'ERR-VAL-205' => [
        'level' => 'ERROR',
        'msg' => 'Invalid JSON',
        'alert' => false,
        'description' => 'JSON data could not be parsed'
    ],
    'ERR-VAL-206' => [
        'level' => 'ERROR',
        'msg' => 'Invalid configuration',
        'alert' => false,
        'description' => 'Configuration validation failed'
    ],
    'ERR-VAL-207' => [
        'level' => 'ERROR',
        'msg' => 'Duplicate entry',
        'alert' => false,
        'description' => 'Entry already exists, cannot create duplicate'
    ],

    // =========================================================================
    // DB - Database Errors (1xx-3xx)
    // =========================================================================
    'ERR-DB-101' => [
        'level' => 'WARNING',
        'msg' => 'Database busy',
        'alert' => false,
        'description' => 'Database locked, retrying operation'
    ],
    'ERR-DB-102' => [
        'level' => 'WARNING',
        'msg' => 'Query slow',
        'alert' => false,
        'description' => 'Query took longer than expected threshold'
    ],
    'ERR-DB-201' => [
        'level' => 'ERROR',
        'msg' => 'SQL query failed',
        'alert' => false,
        'description' => 'Database query execution failed'
    ],
    'ERR-DB-202' => [
        'level' => 'ERROR',
        'msg' => 'Record not found',
        'alert' => false,
        'description' => 'Requested record does not exist in database'
    ],
    'ERR-DB-203' => [
        'level' => 'ERROR',
        'msg' => 'Constraint violation',
        'alert' => false,
        'description' => 'Database constraint (unique, foreign key) violated'
    ],
    'ERR-DB-204' => [
        'level' => 'ERROR',
        'msg' => 'Transaction failed',
        'alert' => false,
        'description' => 'Database transaction could not be completed'
    ],
    'ERR-DB-301' => [
        'level' => 'CRITICAL',
        'msg' => 'Database connection lost',
        'alert' => true,
        'description' => 'Cannot connect to database server'
    ],
    'ERR-DB-302' => [
        'level' => 'CRITICAL',
        'msg' => 'Database corruption detected',
        'alert' => true,
        'description' => 'Database integrity check failed'
    ],

    // =========================================================================
    // HW - Hardware Errors (1xx-3xx)
    // =========================================================================
    'ERR-HW-101' => [
        'level' => 'WARNING',
        'msg' => 'Low battery warning',
        'alert' => false,
        'description' => 'Device battery below 20%'
    ],
    'ERR-HW-102' => [
        'level' => 'WARNING',
        'msg' => 'Sensor calibration needed',
        'alert' => false,
        'description' => 'Sensor readings outside normal range'
    ],
    'ERR-HW-103' => [
        'level' => 'WARNING',
        'msg' => 'Timer heartbeat delayed',
        'alert' => false,
        'description' => 'Timer heartbeat received but delayed'
    ],
    'ERR-HW-201' => [
        'level' => 'ERROR',
        'msg' => 'Sensor timeout',
        'alert' => false,
        'description' => 'No response from sensor within timeout period'
    ],
    'ERR-HW-202' => [
        'level' => 'ERROR',
        'msg' => 'LED control failed',
        'alert' => false,
        'description' => 'Could not set LED state'
    ],
    'ERR-HW-203' => [
        'level' => 'ERROR',
        'msg' => 'Timer initialization failed',
        'alert' => false,
        'description' => 'Hardware timer could not be initialized'
    ],
    'ERR-HW-204' => [
        'level' => 'ERROR',
        'msg' => 'PCB communication error',
        'alert' => false,
        'description' => 'Error communicating with PCB via I2C/SPI'
    ],
    'ERR-HW-301' => [
        'level' => 'CRITICAL',
        'msg' => 'Device offline',
        'alert' => true,
        'description' => 'No heartbeat from device, considered offline'
    ],
    'ERR-HW-302' => [
        'level' => 'CRITICAL',
        'msg' => 'Battery critical',
        'alert' => true,
        'description' => 'Device battery below 5%, shutdown imminent'
    ],
    'ERR-HW-303' => [
        'level' => 'CRITICAL',
        'msg' => 'Timer hardware failure',
        'alert' => true,
        'description' => 'Timer hardware detected fault condition'
    ],

    // =========================================================================
    // NET - Network Errors (1xx-3xx)
    // =========================================================================
    'ERR-NET-101' => [
        'level' => 'WARNING',
        'msg' => 'Network latency high',
        'alert' => false,
        'description' => 'Network round-trip time exceeds threshold'
    ],
    'ERR-NET-102' => [
        'level' => 'WARNING',
        'msg' => 'MQTT reconnecting',
        'alert' => false,
        'description' => 'Lost MQTT connection, attempting reconnect'
    ],
    'ERR-NET-201' => [
        'level' => 'ERROR',
        'msg' => 'MQTT publish failed',
        'alert' => false,
        'description' => 'Could not publish message to MQTT broker'
    ],
    'ERR-NET-202' => [
        'level' => 'ERROR',
        'msg' => 'HTTP request failed',
        'alert' => false,
        'description' => 'HTTP request returned error status'
    ],
    'ERR-NET-203' => [
        'level' => 'ERROR',
        'msg' => 'Connection timeout',
        'alert' => false,
        'description' => 'Network connection timed out'
    ],
    'ERR-NET-204' => [
        'level' => 'ERROR',
        'msg' => 'DNS resolution failed',
        'alert' => false,
        'description' => 'Could not resolve hostname'
    ],
    'ERR-NET-301' => [
        'level' => 'CRITICAL',
        'msg' => 'MQTT broker disconnected',
        'alert' => true,
        'description' => 'Lost connection to MQTT broker, cannot recover'
    ],
    'ERR-NET-302' => [
        'level' => 'CRITICAL',
        'msg' => 'Network unreachable',
        'alert' => true,
        'description' => 'No network connectivity available'
    ],

    // =========================================================================
    // RACE - Race State & Timing Errors (1xx-3xx)
    // =========================================================================
    'ERR-RACE-101' => [
        'level' => 'WARNING',
        'msg' => 'Lane time discrepancy',
        'alert' => false,
        'description' => 'Lane finish time differs from expected range'
    ],
    'ERR-RACE-102' => [
        'level' => 'WARNING',
        'msg' => 'Race state mismatch',
        'alert' => false,
        'description' => 'PHP and Python race states differ'
    ],
    'ERR-RACE-201' => [
        'level' => 'ERROR',
        'msg' => 'Invalid state transition',
        'alert' => false,
        'description' => 'Attempted state transition is not valid'
    ],
    'ERR-RACE-202' => [
        'level' => 'ERROR',
        'msg' => 'Lane already finished',
        'alert' => false,
        'description' => 'Received finish signal for lane already marked finished'
    ],
    'ERR-RACE-203' => [
        'level' => 'ERROR',
        'msg' => 'No active race',
        'alert' => false,
        'description' => 'Received race event but no race is active'
    ],
    'ERR-RACE-204' => [
        'level' => 'ERROR',
        'msg' => 'Heat not found',
        'alert' => false,
        'description' => 'Specified heat does not exist'
    ],
    'ERR-RACE-205' => [
        'level' => 'ERROR',
        'msg' => 'Results write failed',
        'alert' => false,
        'description' => 'Could not write race results to database'
    ],
    'ERR-RACE-301' => [
        'level' => 'CRITICAL',
        'msg' => 'Timing system failure',
        'alert' => true,
        'description' => 'Race timing system has failed'
    ],
    'ERR-RACE-302' => [
        'level' => 'CRITICAL',
        'msg' => 'Start gate failure',
        'alert' => true,
        'description' => 'Start gate sensor not responding'
    ],

    // =========================================================================
    // SYS - System Errors (1xx-3xx)
    // =========================================================================
    'ERR-SYS-101' => [
        'level' => 'WARNING',
        'msg' => 'Memory usage high',
        'alert' => false,
        'description' => 'System memory usage above 80%'
    ],
    'ERR-SYS-102' => [
        'level' => 'WARNING',
        'msg' => 'Disk space low',
        'alert' => false,
        'description' => 'Available disk space below 1GB'
    ],
    'ERR-SYS-103' => [
        'level' => 'WARNING',
        'msg' => 'CPU usage high',
        'alert' => false,
        'description' => 'System CPU usage above 90%'
    ],
    'ERR-SYS-201' => [
        'level' => 'ERROR',
        'msg' => 'File operation failed',
        'alert' => false,
        'description' => 'Could not read or write to file'
    ],
    'ERR-SYS-202' => [
        'level' => 'ERROR',
        'msg' => 'Process spawn failed',
        'alert' => false,
        'description' => 'Could not start subprocess'
    ],
    'ERR-SYS-301' => [
        'level' => 'CRITICAL',
        'msg' => 'Out of memory',
        'alert' => true,
        'description' => 'System has run out of available memory'
    ],
    'ERR-SYS-302' => [
        'level' => 'CRITICAL',
        'msg' => 'Disk full',
        'alert' => true,
        'description' => 'No disk space remaining'
    ],

    // =========================================================================
    // CFG - Configuration Errors (1xx-3xx)
    // =========================================================================
    'ERR-CFG-101' => [
        'level' => 'WARNING',
        'msg' => 'Using default configuration',
        'alert' => false,
        'description' => 'Configuration file not found, using defaults'
    ],
    'ERR-CFG-201' => [
        'level' => 'ERROR',
        'msg' => 'Configuration file invalid',
        'alert' => false,
        'description' => 'Configuration file could not be parsed'
    ],
    'ERR-CFG-202' => [
        'level' => 'ERROR',
        'msg' => 'Missing required setting',
        'alert' => false,
        'description' => 'Required configuration setting not found'
    ],
    'ERR-CFG-203' => [
        'level' => 'ERROR',
        'msg' => 'Configuration save failed',
        'alert' => false,
        'description' => 'Could not save configuration changes'
    ],
];


// =============================================================================
// LEGACY CODE MAPPING
// Maps old ad-hoc error codes to standardized ERR-XXX-NNN format
// =============================================================================

$LEGACY_CODE_MAP = [
    // Authentication
    'notauthorized' => 'ERR-AUTH-202',
    'permission' => 'ERR-AUTH-202',

    // Validation
    'noname' => 'ERR-VAL-201',
    'missing-args' => 'ERR-VAL-202',
    'missing-data' => 'ERR-VAL-202',
    'invalid-json' => 'ERR-VAL-205',
    'invalid-config' => 'ERR-VAL-206',

    // Database
    'sql' => 'ERR-DB-201',
    'not-found' => 'ERR-DB-202',

    // Race
    'tournament-active' => 'ERR-RACE-201',
    'no-tournament' => 'ERR-RACE-203',

    // File operations
    'upload' => 'ERR-SYS-201',
    'save-failed' => 'ERR-SYS-201',

    // Configuration
    'exception' => 'ERR-SYS-201',
];


// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Get details for an error code.
 *
 * @param string $code Error code string (e.g., 'ERR-HW-301')
 * @return array Details with level, msg, alert, description keys
 */
function get_error_details($code) {
    global $ERROR_CODES;

    if (isset($ERROR_CODES[$code])) {
        return $ERROR_CODES[$code];
    }

    return [
        'level' => 'ERROR',
        'msg' => "Unknown error: $code",
        'alert' => false,
        'description' => 'Error code not found in registry'
    ];
}


/**
 * Map a legacy error code to the new standardized format.
 *
 * @param string $legacy_code Old-style error code (e.g., 'notauthorized')
 * @return string Standardized error code or original if no mapping exists
 */
function map_legacy_code($legacy_code) {
    global $LEGACY_CODE_MAP;

    // If it's already a standardized code, return as-is
    if (preg_match('/^ERR-[A-Z]+-[123]\d{2}$/', $legacy_code)) {
        return $legacy_code;
    }

    // Check for exact match in legacy map
    if (isset($LEGACY_CODE_MAP[$legacy_code])) {
        return $LEGACY_CODE_MAP[$legacy_code];
    }

    // Check for partial match (e.g., 'sql123' matches 'sql')
    foreach ($LEGACY_CODE_MAP as $prefix => $mapped) {
        if (strpos($legacy_code, $prefix) === 0) {
            return $mapped;
        }
    }

    // No mapping found, return original
    return $legacy_code;
}


/**
 * Check if an error code should trigger an alert.
 *
 * @param string $code Error code string
 * @return bool True if alert should be triggered
 */
function is_alert_required($code) {
    $details = get_error_details($code);
    return $details['alert'] ?? false;
}


/**
 * Get all error codes for a specific category.
 *
 * @param string $category Category prefix (e.g., 'HW', 'NET', 'RACE')
 * @return array Matching error codes
 */
function get_codes_by_category($category) {
    global $ERROR_CODES;

    $prefix = 'ERR-' . strtoupper($category) . '-';
    $result = [];

    foreach ($ERROR_CODES as $code => $details) {
        if (strpos($code, $prefix) === 0) {
            $result[$code] = $details;
        }
    }

    return $result;
}


/**
 * Get all CRITICAL level error codes.
 *
 * @return array Error codes with level='CRITICAL'
 */
function get_critical_codes() {
    global $ERROR_CODES;

    $result = [];
    foreach ($ERROR_CODES as $code => $details) {
        if ($details['level'] === 'CRITICAL') {
            $result[$code] = $details;
        }
    }

    return $result;
}

?>

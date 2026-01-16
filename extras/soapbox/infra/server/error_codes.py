"""
DerbyNet Unified Error Code Registry
=====================================

Standardized error codes for all Derby infrastructure components.
Shared between Python and PHP (mirrored in website/inc/error-codes.inc).

Version: 1.0.0
Date: 2026-01-14

ERROR CODE FORMAT:
------------------
    ERR-{CATEGORY}-{NUMBER}

CATEGORIES:
-----------
    AUTH - Authentication, permissions, session errors
    VAL  - Input validation, format errors
    DB   - Database operations, SQL errors
    HW   - Hardware (timers, sensors, LEDs)
    NET  - Network (MQTT, HTTP, connectivity)
    RACE - Race state, timing logic
    SYS  - System (memory, disk, process)
    CFG  - Configuration errors

SEVERITY BY NUMBER:
-------------------
    1xx = WARNING (monitor, non-critical)
    2xx = ERROR (operation failed, may retry)
    3xx = CRITICAL (immediate attention required, triggers alert)

USAGE:
------
    from error_codes import ERROR_CODES, get_error_details

    # Look up error details
    details = get_error_details('ERR-HW-301')
    print(details['msg'])  # "Device offline"

    # Use with logger
    logger.error(details['msg'], extra={
        'error_code': 'ERR-HW-301',
        'context': {'device': 'FINISH2', 'lane': 2}
    })
"""

from typing import Dict, Optional, Any


# =============================================================================
# ERROR CODE REGISTRY
# =============================================================================

ERROR_CODES: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # AUTH - Authentication & Authorization (1xx-3xx)
    # =========================================================================
    'ERR-AUTH-101': {
        'level': 'WARNING',
        'msg': 'Session expiring soon',
        'alert': False,
        'description': 'User session will expire in less than 5 minutes'
    },
    'ERR-AUTH-102': {
        'level': 'WARNING',
        'msg': 'Session expired',
        'alert': False,
        'description': 'User session has expired, re-authentication required'
    },
    'ERR-AUTH-201': {
        'level': 'ERROR',
        'msg': 'Authentication failed',
        'alert': False,
        'description': 'Invalid credentials or authentication token'
    },
    'ERR-AUTH-202': {
        'level': 'ERROR',
        'msg': 'Not authorized',
        'alert': False,
        'description': 'User lacks permission for requested action'
    },
    'ERR-AUTH-203': {
        'level': 'ERROR',
        'msg': 'Invalid role',
        'alert': False,
        'description': 'Specified role does not exist or is not valid'
    },

    # =========================================================================
    # VAL - Validation Errors (1xx-3xx)
    # =========================================================================
    'ERR-VAL-101': {
        'level': 'WARNING',
        'msg': 'Optional field missing',
        'alert': False,
        'description': 'Optional field not provided, using default'
    },
    'ERR-VAL-201': {
        'level': 'ERROR',
        'msg': 'Missing required field',
        'alert': False,
        'description': 'A required field was not provided in the request'
    },
    'ERR-VAL-202': {
        'level': 'ERROR',
        'msg': 'Missing required arguments',
        'alert': False,
        'description': 'Required arguments not provided'
    },
    'ERR-VAL-203': {
        'level': 'ERROR',
        'msg': 'Invalid format',
        'alert': False,
        'description': 'Field value does not match expected format'
    },
    'ERR-VAL-204': {
        'level': 'ERROR',
        'msg': 'Value out of range',
        'alert': False,
        'description': 'Numeric value outside acceptable range'
    },
    'ERR-VAL-205': {
        'level': 'ERROR',
        'msg': 'Invalid JSON',
        'alert': False,
        'description': 'JSON data could not be parsed'
    },
    'ERR-VAL-206': {
        'level': 'ERROR',
        'msg': 'Invalid configuration',
        'alert': False,
        'description': 'Configuration validation failed'
    },
    'ERR-VAL-207': {
        'level': 'ERROR',
        'msg': 'Duplicate entry',
        'alert': False,
        'description': 'Entry already exists, cannot create duplicate'
    },

    # =========================================================================
    # DB - Database Errors (1xx-3xx)
    # =========================================================================
    'ERR-DB-101': {
        'level': 'WARNING',
        'msg': 'Database busy',
        'alert': False,
        'description': 'Database locked, retrying operation'
    },
    'ERR-DB-102': {
        'level': 'WARNING',
        'msg': 'Query slow',
        'alert': False,
        'description': 'Query took longer than expected threshold'
    },
    'ERR-DB-201': {
        'level': 'ERROR',
        'msg': 'SQL query failed',
        'alert': False,
        'description': 'Database query execution failed'
    },
    'ERR-DB-202': {
        'level': 'ERROR',
        'msg': 'Record not found',
        'alert': False,
        'description': 'Requested record does not exist in database'
    },
    'ERR-DB-203': {
        'level': 'ERROR',
        'msg': 'Constraint violation',
        'alert': False,
        'description': 'Database constraint (unique, foreign key) violated'
    },
    'ERR-DB-204': {
        'level': 'ERROR',
        'msg': 'Transaction failed',
        'alert': False,
        'description': 'Database transaction could not be completed'
    },
    'ERR-DB-301': {
        'level': 'CRITICAL',
        'msg': 'Database connection lost',
        'alert': True,
        'description': 'Cannot connect to database server'
    },
    'ERR-DB-302': {
        'level': 'CRITICAL',
        'msg': 'Database corruption detected',
        'alert': True,
        'description': 'Database integrity check failed'
    },

    # =========================================================================
    # HW - Hardware Errors (1xx-3xx)
    # =========================================================================
    'ERR-HW-101': {
        'level': 'WARNING',
        'msg': 'Low battery warning',
        'alert': False,
        'description': 'Device battery below 20%'
    },
    'ERR-HW-102': {
        'level': 'WARNING',
        'msg': 'Sensor calibration needed',
        'alert': False,
        'description': 'Sensor readings outside normal range, calibration recommended'
    },
    'ERR-HW-103': {
        'level': 'WARNING',
        'msg': 'Timer heartbeat delayed',
        'alert': False,
        'description': 'Timer heartbeat received but delayed'
    },
    'ERR-HW-104': {
        'level': 'WARNING',
        'msg': 'CPU temperature high',
        'alert': False,
        'description': 'Device CPU temperature above 60°C, monitor for throttling'
    },
    'ERR-HW-201': {
        'level': 'ERROR',
        'msg': 'Sensor timeout',
        'alert': False,
        'description': 'No response from sensor within timeout period'
    },
    'ERR-HW-202': {
        'level': 'ERROR',
        'msg': 'LED control failed',
        'alert': False,
        'description': 'Could not set LED state'
    },
    'ERR-HW-203': {
        'level': 'ERROR',
        'msg': 'Timer initialization failed',
        'alert': False,
        'description': 'Hardware timer could not be initialized'
    },
    'ERR-HW-204': {
        'level': 'ERROR',
        'msg': 'PCB communication error',
        'alert': False,
        'description': 'Error communicating with PCB via I2C/SPI'
    },
    'ERR-HW-301': {
        'level': 'CRITICAL',
        'msg': 'Device offline',
        'alert': True,
        'description': 'No heartbeat from device, considered offline'
    },
    'ERR-HW-302': {
        'level': 'CRITICAL',
        'msg': 'Battery critical',
        'alert': True,
        'description': 'Device battery below 5%, shutdown imminent'
    },
    'ERR-HW-303': {
        'level': 'CRITICAL',
        'msg': 'Timer hardware failure',
        'alert': True,
        'description': 'Timer hardware detected fault condition'
    },

    # =========================================================================
    # NET - Network Errors (1xx-3xx)
    # =========================================================================
    'ERR-NET-101': {
        'level': 'WARNING',
        'msg': 'Network latency high',
        'alert': False,
        'description': 'Network round-trip time exceeds threshold'
    },
    'ERR-NET-102': {
        'level': 'WARNING',
        'msg': 'MQTT reconnecting',
        'alert': False,
        'description': 'Lost MQTT connection, attempting reconnect'
    },
    'ERR-NET-201': {
        'level': 'ERROR',
        'msg': 'MQTT publish failed',
        'alert': False,
        'description': 'Could not publish message to MQTT broker'
    },
    'ERR-NET-202': {
        'level': 'ERROR',
        'msg': 'HTTP request failed',
        'alert': False,
        'description': 'HTTP request returned error status'
    },
    'ERR-NET-203': {
        'level': 'ERROR',
        'msg': 'Connection timeout',
        'alert': False,
        'description': 'Network connection timed out'
    },
    'ERR-NET-204': {
        'level': 'ERROR',
        'msg': 'DNS resolution failed',
        'alert': False,
        'description': 'Could not resolve hostname'
    },
    'ERR-NET-301': {
        'level': 'CRITICAL',
        'msg': 'MQTT broker disconnected',
        'alert': True,
        'description': 'Lost connection to MQTT broker, cannot recover'
    },
    'ERR-NET-302': {
        'level': 'CRITICAL',
        'msg': 'Network unreachable',
        'alert': True,
        'description': 'No network connectivity available'
    },

    # =========================================================================
    # RACE - Race State & Timing Errors (1xx-3xx)
    # =========================================================================
    'ERR-RACE-101': {
        'level': 'WARNING',
        'msg': 'Lane time discrepancy',
        'alert': False,
        'description': 'Lane finish time differs from expected range'
    },
    'ERR-RACE-102': {
        'level': 'WARNING',
        'msg': 'Race state mismatch',
        'alert': False,
        'description': 'PHP and Python race states differ'
    },
    'ERR-RACE-201': {
        'level': 'ERROR',
        'msg': 'Invalid state transition',
        'alert': False,
        'description': 'Attempted state transition is not valid'
    },
    'ERR-RACE-202': {
        'level': 'ERROR',
        'msg': 'Lane already finished',
        'alert': False,
        'description': 'Received finish signal for lane already marked finished'
    },
    'ERR-RACE-203': {
        'level': 'ERROR',
        'msg': 'No active race',
        'alert': False,
        'description': 'Received race event but no race is active'
    },
    'ERR-RACE-204': {
        'level': 'ERROR',
        'msg': 'Heat not found',
        'alert': False,
        'description': 'Specified heat does not exist'
    },
    'ERR-RACE-205': {
        'level': 'ERROR',
        'msg': 'Results write failed',
        'alert': False,
        'description': 'Could not write race results to database'
    },
    'ERR-RACE-301': {
        'level': 'CRITICAL',
        'msg': 'Timing system failure',
        'alert': True,
        'description': 'Race timing system has failed, race results unreliable'
    },
    'ERR-RACE-302': {
        'level': 'CRITICAL',
        'msg': 'Start gate failure',
        'alert': True,
        'description': 'Start gate sensor not responding'
    },

    # =========================================================================
    # SYS - System Errors (1xx-3xx)
    # =========================================================================
    'ERR-SYS-101': {
        'level': 'WARNING',
        'msg': 'Memory usage high',
        'alert': False,
        'description': 'System memory usage above 80%'
    },
    'ERR-SYS-102': {
        'level': 'WARNING',
        'msg': 'Disk space low',
        'alert': False,
        'description': 'Available disk space below 1GB'
    },
    'ERR-SYS-103': {
        'level': 'WARNING',
        'msg': 'CPU usage high',
        'alert': False,
        'description': 'System CPU usage above 90%'
    },
    'ERR-SYS-201': {
        'level': 'ERROR',
        'msg': 'File operation failed',
        'alert': False,
        'description': 'Could not read or write to file'
    },
    'ERR-SYS-202': {
        'level': 'ERROR',
        'msg': 'Process spawn failed',
        'alert': False,
        'description': 'Could not start subprocess'
    },
    'ERR-SYS-301': {
        'level': 'CRITICAL',
        'msg': 'Out of memory',
        'alert': True,
        'description': 'System has run out of available memory'
    },
    'ERR-SYS-302': {
        'level': 'CRITICAL',
        'msg': 'Disk full',
        'alert': True,
        'description': 'No disk space remaining'
    },

    # =========================================================================
    # CFG - Configuration Errors (1xx-3xx)
    # =========================================================================
    'ERR-CFG-101': {
        'level': 'WARNING',
        'msg': 'Using default configuration',
        'alert': False,
        'description': 'Configuration file not found, using defaults'
    },
    'ERR-CFG-201': {
        'level': 'ERROR',
        'msg': 'Configuration file invalid',
        'alert': False,
        'description': 'Configuration file could not be parsed'
    },
    'ERR-CFG-202': {
        'level': 'ERROR',
        'msg': 'Missing required setting',
        'alert': False,
        'description': 'Required configuration setting not found'
    },
    'ERR-CFG-203': {
        'level': 'ERROR',
        'msg': 'Configuration save failed',
        'alert': False,
        'description': 'Could not save configuration changes'
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_error_details(code: str) -> Dict[str, Any]:
    """
    Get details for an error code.

    Args:
        code: Error code string (e.g., 'ERR-HW-301')

    Returns:
        Dictionary with level, msg, alert, description keys.
        Returns default ERROR entry if code not found.
    """
    return ERROR_CODES.get(code, {
        'level': 'ERROR',
        'msg': f'Unknown error: {code}',
        'alert': False,
        'description': 'Error code not found in registry'
    })


def is_alert_required(code: str) -> bool:
    """
    Check if an error code should trigger an alert.

    Args:
        code: Error code string

    Returns:
        True if alert should be triggered
    """
    details = get_error_details(code)
    return details.get('alert', False)


def get_codes_by_category(category: str) -> Dict[str, Dict[str, Any]]:
    """
    Get all error codes for a specific category.

    Args:
        category: Category prefix (e.g., 'HW', 'NET', 'RACE')

    Returns:
        Dictionary of matching error codes
    """
    prefix = f'ERR-{category.upper()}-'
    return {k: v for k, v in ERROR_CODES.items() if k.startswith(prefix)}


def get_critical_codes() -> Dict[str, Dict[str, Any]]:
    """
    Get all CRITICAL level error codes (should trigger alerts).

    Returns:
        Dictionary of all codes with level='CRITICAL'
    """
    return {k: v for k, v in ERROR_CODES.items() if v['level'] == 'CRITICAL'}


# =============================================================================
# VALIDATION
# =============================================================================

def validate_registry() -> bool:
    """
    Validate that all error codes follow the correct format and rules.

    Returns:
        True if all validations pass

    Raises:
        ValueError: If validation fails
    """
    import re

    pattern = r'^ERR-[A-Z]+-[123]\d{2}$'

    for code, details in ERROR_CODES.items():
        # Check code format
        if not re.match(pattern, code):
            raise ValueError(f"Invalid code format: {code}")

        # Check required fields
        for field in ['level', 'msg', 'alert']:
            if field not in details:
                raise ValueError(f"Missing required field '{field}' in {code}")

        # Check level is valid
        if details['level'] not in ('WARNING', 'ERROR', 'CRITICAL'):
            raise ValueError(f"Invalid level '{details['level']}' in {code}")

        # Check severity matches number range
        num = int(code.split('-')[-1])
        expected_level = {
            1: 'WARNING',
            2: 'ERROR',
            3: 'CRITICAL'
        }.get(num // 100)

        if expected_level and details['level'] != expected_level:
            raise ValueError(
                f"Code {code} has level '{details['level']}' but number "
                f"{num} suggests '{expected_level}'"
            )

        # Check CRITICAL codes have alert=True
        if details['level'] == 'CRITICAL' and not details['alert']:
            raise ValueError(f"CRITICAL code {code} should have alert=True")

    return True


if __name__ == '__main__':
    # Self-test when run directly
    print("=== Error Code Registry Validation ===\n")

    try:
        validate_registry()
        print(f"Total codes: {len(ERROR_CODES)}")
        print(f"Critical codes: {len(get_critical_codes())}")

        print("\nCodes by category:")
        for cat in ['AUTH', 'VAL', 'DB', 'HW', 'NET', 'RACE', 'SYS', 'CFG']:
            codes = get_codes_by_category(cat)
            print(f"  {cat}: {len(codes)} codes")

        print("\nValidation PASSED")

    except ValueError as e:
        print(f"Validation FAILED: {e}")

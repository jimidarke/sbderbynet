'''
Logging framework for Derby server components.

This module provides backward compatibility with existing code while
using the unified DerbyLogger for text-format logging.

Version: 2.0.0
Date: 2025-12-08

SAMPLE USAGE:

from serverlogger import ServerLogger
import logging

# Production logging (file only)
logger = ServerLogger(
    name='finishtimer',
    log_file='/var/log/derbynet.log',
    level=logging.INFO
).get_logger()

# Debug logging to console
debug_logger = ServerLogger(
    name='finishtimer',
    level=logging.DEBUG,
    console=True
).get_logger()

# Environment variable control for easy debugging
import os
console_mode = os.getenv('DERBY_CONSOLE_LOG', 'false').lower() == 'true'
debug_mode = os.getenv('DERBY_DEBUG', 'false').lower() == 'true'

logger = ServerLogger(
    name='derbyrace',
    level=logging.DEBUG if debug_mode else logging.INFO,
    console=console_mode
).get_logger()

# Usage examples:
logger.info("Finish timer initialized.")
logger.debug("Sensor reading: lane 1 = 3.24V")  # Only shows if level=DEBUG
logger.error("Sensor timeout on lane 2.")
logger.warning("Low battery on node 3.")

'''

import logging
import os

# Import from derbylogger (in same directory)
from derbylogger import DerbyLogger, DEFAULT_LOG_FILE, DERBY_TIMEZONE

# Re-export for convenience
__all__ = ['ServerLogger', 'DEFAULT_LOG_FILE', 'DERBY_TIMEZONE']


class ServerLogger:
    """
    A logger for Derby server components that supports file and console logging.

    This class wraps DerbyLogger for backward compatibility.

    Args:
        name: Logger name / component name
        log_file: Path to log file (default: /var/log/derbynet.log)
        level: Logging level (default: logging.INFO)
        console: Enable console output (disables rsyslog)
        enable_rsyslog: Enable rsyslog output (for remote devices only)
    """

    def __init__(self, name='derbyserver', log_file=None, level=logging.INFO,
                 console=False, enable_rsyslog=False):
        self.name = name

        # Convert level int to string for DerbyLogger
        log_level_name = logging.getLevelName(level) if isinstance(level, int) else level

        # Use default log file if not specified
        if log_file is None:
            log_file = DEFAULT_LOG_FILE

        # Create DerbyLogger instance
        self._derby_logger = DerbyLogger(
            component=name,
            device_id='SERVER',
            log_level=log_level_name,
            log_file=log_file,
            console=console,
            syslog=enable_rsyslog
        )
        self.logger = self._derby_logger.get_logger()

    def get_logger(self):
        """Get the underlying Python logger."""
        return self.logger


if __name__ == "__main__":
    print("=== ServerLogger Test ===")
    print(f"Timezone: {DERBY_TIMEZONE}")
    print(f"Log File: {DEFAULT_LOG_FILE}")
    print("")

    # Test with console output enabled (for debugging)
    print("=== Testing Console Debug Logging ===")
    debug_logger = ServerLogger(
        name='derby-test',
        level=logging.DEBUG,
        console=True
    ).get_logger()

    debug_logger.debug("DEBUG: This message shows in console with debug logging")
    debug_logger.info("INFO: Derby server logger test with console output")
    debug_logger.warning("WARNING: Example warning message")
    debug_logger.error("ERROR: Example error message")
    debug_logger.critical("CRITICAL: Example critical message")

    print("\n=== Testing Production Logging (file only) ===")
    prod_logger = ServerLogger(
        name='derby-prod',
        level=logging.INFO,
        console=False
    ).get_logger()

    prod_logger.debug("DEBUG: This won't show (level=INFO)")
    prod_logger.info("INFO: Production logging test - check /var/log/derbynet.log")
    prod_logger.warning("WARNING: Production warning message")

    print(f"\nLogger test complete.")
    print(f"To enable debug console logging in services:")
    print(f"  export DERBY_CONSOLE_LOG=true")
    print(f"  export DERBY_DEBUG=true")
    print(f"  python3 your_service.py")

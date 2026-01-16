#!/usr/bin/env python3
"""
Derby Display implementation of the standardized DerbyNet logging system.
Wrapper around the unified derbylogger.py for backward compatibility.

Version: 3.0.0
Date: 2026-01-14

This module delegates to the unified server derbylogger implementation,
with appropriate defaults for display components (console + syslog enabled).

USAGE:
    from derbylogger import setup_logger

    logger = setup_logger('display-main')
    logger.info("Display initialized")
    logger.error("Connection failed", extra={'error_code': 'ERR-NET-201'})
"""

import os
import sys
import logging

# Add server path to allow importing unified derbylogger
server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server'))
if server_path not in sys.path:
    sys.path.insert(0, server_path)

# Try to import from unified server derbylogger
try:
    from derbylogger import (
        DerbyLogger,
        setup_logger as server_setup_logger,
        get_device_id,
        DERBY_TIMEZONE,
        DEFAULT_LOG_FILE,
        DEFAULT_JSON_FILE,
        DEFAULT_RSYSLOG_IP,
        DEFAULT_RSYSLOG_PORT,
    )

    def setup_logger(name, log_dir=None):
        """
        Set up a logger for display components.

        Args:
            name: Logger name, typically module name
            log_dir: Optional custom log directory (for backward compatibility, ignored)

        Returns:
            Logger instance configured with standard settings
        """
        device_id = get_device_id()
        component = f"display-{name}" if not name.startswith('display') else name

        return server_setup_logger(
            component=component,
            device_id=device_id,
            log_level='INFO',
            console=True,
            syslog=True,
            log_file=DEFAULT_LOG_FILE,
            json_file=DEFAULT_JSON_FILE
        )

    def get_logger(name):
        """Get an existing logger by name."""
        return logging.getLogger(f'derby.{get_device_id()}.{name}')

except ImportError as e:
    # Fallback implementation if server derbylogger isn't available
    import logging.handlers
    import uuid
    from datetime import datetime

    print(f"WARNING: Using fallback logger - server derbylogger not available: {e}")

    # Try to use zoneinfo (Python 3.9+), fall back to pytz
    try:
        from zoneinfo import ZoneInfo
        def get_tz(tz_name):
            return ZoneInfo(tz_name)
    except ImportError:
        try:
            import pytz
            def get_tz(tz_name):
                return pytz.timezone(tz_name)
        except ImportError:
            def get_tz(tz_name):
                return None

    # Configuration
    DERBY_TIMEZONE = os.getenv('DERBY_TIMEZONE', 'America/Edmonton')
    DEFAULT_LOG_FILE = os.getenv('DERBY_LOG_FILE', '/var/log/derbynet.log')
    DEFAULT_RSYSLOG_IP = os.getenv('RSYSLOG_IP', '192.168.100.10')
    DEFAULT_RSYSLOG_PORT = int(os.getenv('RSYSLOG_PORT', '514'))

    def get_device_id():
        """Get device ID from derbyid.txt or hostname."""
        for path in ['/boot/firmware/derbyid.txt', '/boot/derbyid.txt']:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        device_id = f.read().strip()
                        if device_id:
                            return device_id.upper()
                except Exception:
                    pass

        # Fallback to MAC address
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff)
                        for i in range(0, 48, 8)][::-1])
        return mac.upper()

    def get_timezone_timestamp():
        """Return current timestamp string in configured timezone."""
        tz = get_tz(DERBY_TIMEZONE)
        now = datetime.now(tz) if tz else datetime.now()
        return now.strftime('%Y-%m-%d %H:%M:%S') + f'.{now.microsecond // 1000:03d}'

    class FallbackFormatter(logging.Formatter):
        """Fallback formatter matching unified logger format."""

        def __init__(self, device_id):
            super().__init__()
            self.device_id = device_id

        def format(self, record):
            timestamp = get_timezone_timestamp()
            location = f'{record.filename}:{record.lineno}'
            message = record.getMessage()
            return f'{timestamp} {self.device_id}:{record.levelname} [{location}] {message}'

    class SyslogFormatter(logging.Formatter):
        """Syslog formatter (without timestamp - server adds it)."""

        def __init__(self, device_id):
            super().__init__()
            self.device_id = device_id

        def format(self, record):
            location = f'{record.filename}:{record.lineno}'
            message = record.getMessage()
            return f'{self.device_id}:{record.levelname} [{location}] {message}'

    def setup_logger(name, log_dir=None):
        """
        Set up a logger for display components (fallback implementation).

        Args:
            name: Logger name
            log_dir: Optional custom log directory (ignored in fallback)

        Returns:
            Logger instance
        """
        device_id = get_device_id()
        component = f"display-{name}" if not name.startswith('display') else name
        logger_name = f'derby.{device_id}.{component}'

        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            formatter = FallbackFormatter(device_id)

            # File handler
            try:
                log_dir_path = os.path.dirname(DEFAULT_LOG_FILE)
                if log_dir_path:
                    os.makedirs(log_dir_path, exist_ok=True)
                file_handler = logging.FileHandler(DEFAULT_LOG_FILE)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as ex:
                print(f"Warning: Failed to create file handler: {ex}")

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            # Syslog handler
            try:
                syslog_handler = logging.handlers.SysLogHandler(
                    address=(DEFAULT_RSYSLOG_IP, DEFAULT_RSYSLOG_PORT),
                    facility=logging.handlers.SysLogHandler.LOG_LOCAL0
                )
                syslog_handler.setFormatter(SyslogFormatter(device_id))
                logger.addHandler(syslog_handler)
            except Exception as ex:
                print(f"Warning: Syslog connection failed: {ex}")

        return logger

    def get_logger(name):
        """Get an existing logger by name."""
        return logging.getLogger(f'derby.{get_device_id()}.{name}')


if __name__ == "__main__":
    print("=== Derby Display Logger v3.0.0 Test ===")
    print(f"Device ID: {get_device_id()}")
    print(f"Log File: {DEFAULT_LOG_FILE}")
    print("")

    logger = setup_logger('test')
    logger.info("INFO: Display logger test")
    logger.warning("WARNING: Display logger test")
    logger.error("ERROR: Display logger test")

    print("\nDisplay logger test complete.")

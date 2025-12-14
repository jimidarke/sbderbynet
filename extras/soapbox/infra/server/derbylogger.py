"""
DerbyNet Unified Logger - Text Format
======================================

Centralized logging framework for all Derby infrastructure components.
Outputs human-readable text format with timezone-aware timestamps.

Version: 2.0.0
Date: 2025-12-08

OUTPUT FORMAT:
--------------
    2025-12-08 14:35:22.123 DEVICE:LEVEL [filename:line] message

CONFIGURATION:
--------------
    DERBY_TIMEZONE = 'America/Edmonton'  # Change this to adjust timezone
    DEFAULT_LOG_FILE = '/var/log/derbynet.log'

USAGE:
------
    from derbylogger import setup_logger

    logger = setup_logger('finishtimer')
    logger.info("Lane triggered")
    logger.error("Sensor timeout on lane 2")

ENVIRONMENT VARIABLES:
----------------------
    DERBY_DEBUG=true        Enable DEBUG level logging
    DERBY_CONSOLE_LOG=true  Enable console output
    DERBY_DEVICE_ID=XXX     Override device ID (defaults to hostname)
"""

import logging
import logging.handlers
import os
import socket
import uuid
from datetime import datetime
from typing import Optional

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
        # No timezone library available - use local time
        def get_tz(tz_name):
            return None

# ============================================================================
# CONFIGURATION - Support Docker deployment via env vars, default to production values
# ============================================================================
DERBY_TIMEZONE = 'America/Edmonton'
DEFAULT_LOG_FILE = '/var/log/derbynet.log'
DEFAULT_RSYSLOG_IP = os.getenv('RSYSLOG_IP', '192.168.100.10')
DEFAULT_RSYSLOG_PORT = int(os.getenv('RSYSLOG_PORT', '514'))

# Log format template
LOG_FORMAT = '[{timestamp}] [{device}] [{level}] [{location}] {message}'


def get_device_id() -> str:
    """
    Get the device ID from various sources:
    1. /boot/firmware/derbyid.txt (Raspberry Pi)
    2. DERBY_DEVICE_ID environment variable
    3. Hostname
    4. MAC address (last resort)
    """
    # Try derbyid.txt first (Pi deployment)
    for path in ['/boot/firmware/derbyid.txt', '/boot/derbyid.txt']:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    device_id = f.read().strip()
                    if device_id:
                        return device_id.upper()
            except Exception:
                pass

    # Environment variable override
    env_id = os.getenv('DERBY_DEVICE_ID')
    if env_id:
        return env_id.upper()

    # Hostname
    hostname = socket.gethostname()
    if hostname and hostname != 'localhost':
        return hostname.upper()

    # MAC address fallback
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff)
                    for i in range(0, 48, 8)][::-1])
    return mac.upper()


def get_timezone_timestamp() -> str:
    """
    Return current timestamp string in configured timezone.
    Format: YYYY-MM-DD HH:MM:SS.mmm
    """
    tz = get_tz(DERBY_TIMEZONE)
    if tz:
        now = datetime.now(tz)
    else:
        now = datetime.now()

    # Format with milliseconds
    return now.strftime('%Y-%m-%d %H:%M:%S') + f'.{now.microsecond // 1000:03d}'


class DerbyTextFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as human-readable text.
    Format: timestamp DEVICE:LEVEL [filename:line] message
    """

    def __init__(self, device_id: str):
        super().__init__()
        self.device_id = device_id

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a text line."""
        timestamp = get_timezone_timestamp()
        device = getattr(record, 'device', self.device_id)
        location = f'{record.filename}:{record.lineno}'
        message = record.getMessage()

        return f'{timestamp} {device}:{record.levelname} [{location}] {message}'


class DerbySyslogFormatter(logging.Formatter):
    """
    Syslog formatter for remote devices.
    Format: DEVICE:LEVEL [filename:line] message
    (rsyslog server will prepend timestamp)
    """

    def __init__(self, device_id: str):
        super().__init__()
        self.device_id = device_id

    def format(self, record: logging.LogRecord) -> str:
        """Format for syslog (without timestamp - server adds it)."""
        device = getattr(record, 'device', self.device_id)
        location = f'{record.filename}:{record.lineno}'
        message = record.getMessage()

        return f'{device}:{record.levelname} [{location}] {message}'


class DerbyLogger:
    """
    Unified logging class for all Derby infrastructure components.

    Supports:
    - Text format output with timezone-aware timestamps
    - Multiple output handlers (file, console, syslog)
    - Environment variable configuration
    """

    def __init__(
        self,
        component: str,
        device_id: Optional[str] = None,
        log_level: str = 'INFO',
        log_file: Optional[str] = DEFAULT_LOG_FILE,
        console: Optional[bool] = None,
        syslog: bool = False,
        rsyslog_ip: Optional[str] = None
    ):
        """
        Initialize the Derby logger.

        Args:
            component: Name of the component/module (e.g., 'finishtimer', 'derbyrace')
            device_id: Device identifier (auto-detected if not provided)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file (None to disable file logging)
            console: Enable console output (auto-detected from DERBY_CONSOLE_LOG if None)
            syslog: Enable rsyslog output (for remote devices)
            rsyslog_ip: IP address of rsyslog server
        """
        self.component = component
        self.device_id = device_id or get_device_id()

        # Environment variable overrides
        debug_mode = os.getenv('DERBY_DEBUG', 'false').lower() == 'true'
        console_mode = os.getenv('DERBY_CONSOLE_LOG', 'false').lower() == 'true'

        if debug_mode:
            log_level = 'DEBUG'

        if console is None:
            console = console_mode

        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.log_file = log_file
        self.console = console
        self.syslog = syslog and not console  # Disable syslog if console is enabled
        self.rsyslog_ip = rsyslog_ip or os.getenv('DERBY_RSYSLOG_IP', DEFAULT_RSYSLOG_IP)

        # Create logger
        logger_name = f'derby.{self.device_id}.{component}'
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(self.log_level)

        # Configure handlers only if not already configured
        if not self.logger.hasHandlers():
            self._setup_handlers()

    def _setup_handlers(self):
        """Configure all logging handlers."""

        # 1. File handler (text format)
        if self.log_file:
            try:
                log_dir = os.path.dirname(self.log_file)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)

                file_handler = logging.FileHandler(self.log_file)
                file_handler.setLevel(self.log_level)
                file_handler.setFormatter(DerbyTextFormatter(self.device_id))
                self.logger.addHandler(file_handler)
            except Exception as e:
                print(f'Warning: Failed to create file handler for {self.log_file}: {e}')

        # 2. Console handler (for debugging)
        if self.console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(DerbyTextFormatter(self.device_id))
            self.logger.addHandler(console_handler)

        # 3. Syslog handler (for remote collection)
        if self.syslog:
            try:
                syslog_handler = logging.handlers.SysLogHandler(
                    address=(self.rsyslog_ip, DEFAULT_RSYSLOG_PORT)
                )
                syslog_handler.setLevel(self.log_level)
                syslog_handler.setFormatter(DerbySyslogFormatter(self.device_id))
                self.logger.addHandler(syslog_handler)
            except Exception as e:
                print(f'Warning: Failed to create syslog handler: {e}')

    def get_logger(self) -> logging.Logger:
        """
        Get the underlying Python logger.

        Returns:
            logging.Logger: Standard Python logger instance
        """
        return self.logger


def setup_logger(
    component: str,
    device_id: Optional[str] = None,
    log_level: str = 'INFO',
    console: bool = False,
    syslog: bool = False,
    log_file: Optional[str] = DEFAULT_LOG_FILE
) -> logging.Logger:
    """
    Convenience function to set up a logger with sensible defaults.

    For SERVER components - writes directly to log file.
    For REMOTE devices (finishtimer, starttimer) - use nodelogger.py instead.

    Args:
        component: Name of the component (e.g., 'derbyrace')
        device_id: Optional device identifier (auto-detected if not provided)
        log_level: Logging level (default: INFO)
        console: Enable console output (default: False)
        syslog: Enable rsyslog output (default: False)
        log_file: Path to log file (default: /var/log/derbynet.log)

    Returns:
        logging.Logger: Configured logger instance

    Example:
        logger = setup_logger('derbyrace')
        logger.info("Heat started")
        logger.error("Sensor timeout")
    """
    return DerbyLogger(
        component=component,
        device_id=device_id,
        log_level=log_level,
        console=console,
        syslog=syslog,
        log_file=log_file
    ).get_logger()


# Backward compatibility alias
ServerLogger = DerbyLogger


if __name__ == '__main__':
    # Test the logger
    print('=== DerbyLogger Test ===\n')
    print(f'Timezone: {DERBY_TIMEZONE}')
    print(f'Device ID: {get_device_id()}')
    print(f'Log File: {DEFAULT_LOG_FILE}')
    print('')

    # Test with console output
    os.environ['DERBY_CONSOLE_LOG'] = 'true'
    os.environ['DERBY_DEBUG'] = 'true'

    logger = setup_logger('test-component', device_id='TEST-DEVICE')

    logger.debug('Debug message - detailed troubleshooting info')
    logger.info('Info message - normal operation')
    logger.warning('Warning message - something to watch')
    logger.error('Error message - something failed')
    logger.critical('Critical message - system failure')

    print('\n=== Test Complete ===')

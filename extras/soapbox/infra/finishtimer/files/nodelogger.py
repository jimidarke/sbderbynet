'''
Logging framework for Derby remote devices (finish timer, derby display, etc.).
Not used on the server - use serverlogger.py instead.

Version: 2.0.0
Date: 2025-12-08

This logger sends logs to the central server via rsyslog UDP.
The rsyslog server prepends the timestamp in the configured timezone.

OUTPUT FORMAT (local file):
    2025-12-08 14:35:22.123 FINISH1:INFO [finishtimer.py:234] Lane triggered

OUTPUT FORMAT (syslog to server):
    FINISH1:INFO [finishtimer.py:234] Lane triggered
    (rsyslog server adds timestamp)

USAGE:

from nodelogger import NodeLogger

logger = NodeLogger(
    name='finishtimer',
    log_file='/var/log/derbynet.log',
    level=logging.INFO,
).get_logger()

logger.info("Finish timer initialized.")
logger.error("Sensor timeout on lane 2.")
logger.warning("Low battery on node 3.")

'''

import logging
import logging.handlers
import os
import socket
from datetime import datetime

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

# ============================================================================
# CONFIGURATION - Change these values as needed
# ============================================================================
DERBY_TIMEZONE = 'America/Edmonton'
DERBY_LOG_FILE = '/var/log/derbynet.log'
DERBY_RSYSLOG_IP = '192.168.100.10'
DERBY_RSYSLOG_PORT = 514


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

    # Fallback to hostname
    hostname = socket.gethostname()
    return hostname.split('.')[0].upper()


def get_timezone_timestamp():
    """Return current timestamp string in configured timezone."""
    tz = get_tz(DERBY_TIMEZONE)
    if tz:
        now = datetime.now(tz)
    else:
        now = datetime.now()
    return now.strftime('%Y-%m-%d %H:%M:%S') + f'.{now.microsecond // 1000:03d}'


class NodeTextFormatter(logging.Formatter):
    """
    Text formatter for local log files.
    Format: timestamp DEVICE:LEVEL [filename:line] message
    """

    def __init__(self, device_id):
        super().__init__()
        self.device_id = device_id

    def format(self, record):
        timestamp = get_timezone_timestamp()
        location = f'{record.filename}:{record.lineno}'
        message = record.getMessage()
        return f'{timestamp} {self.device_id}:{record.levelname} [{location}] {message}'


class NodeSyslogFormatter(logging.Formatter):
    """
    Syslog formatter for remote logging.
    Format: DEVICE:LEVEL [filename:line] message
    (rsyslog server will prepend timestamp)
    """

    def __init__(self, device_id):
        super().__init__()
        self.device_id = device_id

    def format(self, record):
        location = f'{record.filename}:{record.lineno}'
        message = record.getMessage()
        return f'{self.device_id}:{record.levelname} [{location}] {message}'


class NodeLogger:
    """
    A logger for Derby remote devices that supports local and rsyslog logging.
    Sends logs to central server via rsyslog UDP for unified logging.
    """

    def __init__(self, name='derby', log_file=None, level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Get device ID for log messages
        self.device_id = get_device_id()

        # Use default log file if not specified
        if log_file is None:
            log_file = DERBY_LOG_FILE

        # Avoid adding handlers multiple times
        if not self.logger.hasHandlers():
            # File handler (local backup with full format)
            try:
                log_dir = os.path.dirname(log_file)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(NodeTextFormatter(self.device_id))
                file_handler.setLevel(level)
                self.logger.addHandler(file_handler)
            except Exception as e:
                print(f'Warning: Failed to create file handler: {e}')

            # Console handler (for debugging)
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(NodeTextFormatter(self.device_id))
            console_handler.setLevel(level)
            self.logger.addHandler(console_handler)

            # Syslog handler - sends to central server
            try:
                syslog_handler = logging.handlers.SysLogHandler(
                    address=(DERBY_RSYSLOG_IP, DERBY_RSYSLOG_PORT),
                    facility=logging.handlers.SysLogHandler.LOG_LOCAL0
                )
                syslog_handler.ident = f'derby-{name}: '
                syslog_handler.setFormatter(NodeSyslogFormatter(self.device_id))
                syslog_handler.setLevel(level)
                self.logger.addHandler(syslog_handler)
            except Exception as e:
                print(f'Warning: Failed to create syslog handler: {e}')

    def get_logger(self):
        return self.logger


if __name__ == "__main__":
    print("=== NodeLogger Test ===")
    print(f"Timezone: {DERBY_TIMEZONE}")
    print(f"Device ID: {get_device_id()}")
    print(f"Log File: {DERBY_LOG_FILE}")
    print(f"rsyslog Server: {DERBY_RSYSLOG_IP}:{DERBY_RSYSLOG_PORT}")
    print("")

    logger = NodeLogger(name='nodetest', level=logging.DEBUG).get_logger()
    logger.debug("DEBUG: Node logger test - debug level")
    logger.info("INFO: Node logger test - info level")
    logger.warning("WARNING: Node logger test - warning level")
    logger.error("ERROR: Node logger test - error level")
    logger.critical("CRITICAL: Node logger test - critical level")

    print("\nNode logger test complete.")
    print(f"Check {DERBY_LOG_FILE} for local output.")
    print(f"Check central server at {DERBY_RSYSLOG_IP} for rsyslog output.")

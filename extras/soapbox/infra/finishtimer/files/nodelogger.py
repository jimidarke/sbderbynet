'''
Logging framework for Derby remote devices (finish timer, derby display, etc.).
Wrapper around derbylogger.py for backward compatibility.

Version: 3.1.0
Date: 2026-01-15

CHANGELOG v3.1.0:
    - Re-export correlation ID functions from derbylogger
    - Correlation IDs enable tracing across timer → server → database

This module is a compatibility layer that wraps the unified DerbyLogger.
Remote devices (finish timer, start timer, derby display) should use this
module which enables syslog by default for centralized logging.

OUTPUT FORMAT (local file):
    2025-12-08 14:35:22.123 FINISH1:INFO [finishtimer.py:234] Lane triggered

OUTPUT FORMAT (syslog to server):
    FINISH1:INFO [finishtimer.py:234] Lane triggered
    (rsyslog server adds timestamp)

JSON OUTPUT FORMAT (JSONL):
    {"ts": "2025-12-08T14:35:22.123-07:00", "level": "INFO", "device": "FINISH1", ...}

USAGE:

from nodelogger import NodeLogger

logger = NodeLogger(
    name='finishtimer',
    log_file='/var/log/derbynet.log',
    level=logging.INFO,
).get_logger()

logger.info("Finish timer initialized.")
logger.error("Sensor timeout on lane 2.", extra={'error_code': 'ERR-HW-201'})
logger.warning("Low battery on node 3.", extra={'context': {'battery': 15}})

'''

import logging
import os
import sys

# Try to import from derbylogger.py (server location)
# This handles deployment where derbylogger.py is available
try:
    # First try relative import (when installed as package)
    from derbylogger import (
        DerbyLogger, setup_logger, get_device_id,
        set_correlation_id, get_correlation_id, clear_correlation_id,
        correlation_context, CorrelationContext
    )
    HAS_CORRELATION = True
except ImportError:
    HAS_CORRELATION = False
    try:
        # Try to add server path for direct imports
        server_path = os.path.join(os.path.dirname(__file__), '..', '..', 'server')
        if server_path not in sys.path:
            sys.path.insert(0, os.path.abspath(server_path))
        from derbylogger import (
            DerbyLogger, setup_logger, get_device_id,
            set_correlation_id, get_correlation_id, clear_correlation_id,
            correlation_context, CorrelationContext
        )
        HAS_CORRELATION = True
    except ImportError:
        # Fallback: define minimal compatibility layer
        # This allows the module to work even if derbylogger isn't available
        import logging.handlers
        import socket
        from datetime import datetime

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
            hostname = socket.gethostname()
            return hostname.split('.')[0].upper()

        def get_timezone_timestamp():
            tz = get_tz(DERBY_TIMEZONE)
            now = datetime.now(tz) if tz else datetime.now()
            return now.strftime('%Y-%m-%d %H:%M:%S') + f'.{now.microsecond // 1000:03d}'

        class NodeTextFormatter(logging.Formatter):
            def __init__(self, device_id):
                super().__init__()
                self.device_id = device_id

            def format(self, record):
                timestamp = get_timezone_timestamp()
                location = f'{record.filename}:{record.lineno}'
                message = record.getMessage()
                return f'{timestamp} {self.device_id}:{record.levelname} [{location}] {message}'

        class NodeSyslogFormatter(logging.Formatter):
            def __init__(self, device_id):
                super().__init__()
                self.device_id = device_id

            def format(self, record):
                location = f'{record.filename}:{record.lineno}'
                message = record.getMessage()
                return f'{self.device_id}:{record.levelname} [{location}] {message}'

        class DerbyLogger:
            """Fallback DerbyLogger for when server module isn't available."""
            def __init__(self, component, device_id=None, log_level='INFO',
                         log_file=DEFAULT_LOG_FILE, json_file=None,
                         console=False, syslog=False, rsyslog_ip=None):
                self.component = component
                self.device_id = device_id or get_device_id()
                self.log_level = getattr(logging, log_level.upper(), logging.INFO)

                logger_name = f'derby.{self.device_id}.{component}'
                self.logger = logging.getLogger(logger_name)
                self.logger.setLevel(self.log_level)

                if not self.logger.handlers:
                    # File handler
                    if log_file:
                        try:
                            log_dir = os.path.dirname(log_file)
                            if log_dir:
                                os.makedirs(log_dir, exist_ok=True)
                            file_handler = logging.FileHandler(log_file)
                            file_handler.setFormatter(NodeTextFormatter(self.device_id))
                            file_handler.setLevel(self.log_level)
                            self.logger.addHandler(file_handler)
                        except Exception as e:
                            print(f'Warning: Failed to create file handler: {e}')

                    # Console handler
                    if console:
                        console_handler = logging.StreamHandler()
                        console_handler.setFormatter(NodeTextFormatter(self.device_id))
                        console_handler.setLevel(self.log_level)
                        self.logger.addHandler(console_handler)

                    # Syslog handler
                    if syslog:
                        try:
                            rsyslog_addr = rsyslog_ip or DEFAULT_RSYSLOG_IP
                            syslog_handler = logging.handlers.SysLogHandler(
                                address=(rsyslog_addr, DEFAULT_RSYSLOG_PORT),
                                facility=logging.handlers.SysLogHandler.LOG_LOCAL0
                            )
                            syslog_handler.ident = f'derby-{component}: '
                            syslog_handler.setFormatter(NodeSyslogFormatter(self.device_id))
                            syslog_handler.setLevel(self.log_level)
                            self.logger.addHandler(syslog_handler)
                        except Exception as e:
                            print(f'Warning: Failed to create syslog handler: {e}')

            def get_logger(self):
                return self.logger

        def setup_logger(component, device_id=None, log_level='INFO',
                         console=False, syslog=False, log_file=DEFAULT_LOG_FILE,
                         json_file=None):
            return DerbyLogger(
                component=component,
                device_id=device_id,
                log_level=log_level,
                console=console,
                syslog=syslog,
                log_file=log_file,
                json_file=json_file
            ).get_logger()

        # Stub correlation functions for fallback mode
        _fallback_corr_id = None

        def set_correlation_id(corr_id=None, session_id=None, source=None):
            global _fallback_corr_id
            import uuid
            _fallback_corr_id = corr_id or str(uuid.uuid4())[:12]
            return _fallback_corr_id

        def get_correlation_id():
            return _fallback_corr_id

        def clear_correlation_id():
            global _fallback_corr_id
            _fallback_corr_id = None

        class CorrelationContext:
            @classmethod
            def get(cls):
                return _fallback_corr_id

        from contextlib import contextmanager
        @contextmanager
        def correlation_context(corr_id=None, session_id=None, source=None):
            try:
                set_correlation_id(corr_id, session_id, source)
                yield get_correlation_id()
            finally:
                clear_correlation_id()


# ============================================================================
# CONFIGURATION - Environment variables for multi-site deployment
# ============================================================================
DERBY_TIMEZONE = os.getenv('DERBY_TIMEZONE', 'America/Edmonton')
DERBY_LOG_FILE = os.getenv('DERBY_LOG_FILE', '/var/log/derbynet.log')
DERBY_JSON_FILE = os.getenv('DERBY_JSON_FILE', '/var/log/derbynet.jsonl')
DERBY_RSYSLOG_IP = os.getenv('RSYSLOG_IP', '192.168.100.10')
DERBY_RSYSLOG_PORT = int(os.getenv('RSYSLOG_PORT', '514'))


class NodeLogger:
    """
    A logger for Derby remote devices that supports local and rsyslog logging.
    Wrapper around DerbyLogger with syslog enabled by default.

    This class provides backward compatibility for existing code while
    using the unified DerbyLogger under the hood.
    """

    def __init__(self, name='derby', log_file=None, level=logging.INFO,
                 console=True, syslog=True, json_file=None):
        """
        Initialize the node logger.

        Args:
            name: Logger name/component (e.g., 'finishtimer')
            log_file: Path to log file (default: /var/log/derbynet.log)
            level: Logging level (default: logging.INFO)
            console: Enable console output (default: True for remote devices)
            syslog: Enable rsyslog output (default: True for remote devices)
            json_file: Path to JSON log file (default: /var/log/derbynet.jsonl)
        """
        # Convert level to string for DerbyLogger
        level_name = logging.getLevelName(level) if isinstance(level, int) else level

        # Use defaults if not specified
        if log_file is None:
            log_file = DERBY_LOG_FILE
        if json_file is None:
            json_file = DERBY_JSON_FILE

        # Create the underlying DerbyLogger
        self._derby_logger = DerbyLogger(
            component=name,
            log_level=level_name,
            log_file=log_file,
            json_file=json_file,
            console=console,
            syslog=syslog,
            rsyslog_ip=DERBY_RSYSLOG_IP
        )

        self.logger = self._derby_logger.get_logger()

    def get_logger(self):
        """Get the underlying Python logger."""
        return self.logger


def setup_node_logger(component, level='INFO', console=True, syslog=True):
    """
    Convenience function to set up a node logger.

    Args:
        component: Component name (e.g., 'finishtimer')
        level: Logging level (default: 'INFO')
        console: Enable console output (default: True)
        syslog: Enable rsyslog output (default: True)

    Returns:
        logging.Logger: Configured logger instance
    """
    return NodeLogger(
        name=component,
        level=getattr(logging, level.upper(), logging.INFO),
        console=console,
        syslog=syslog
    ).get_logger()


if __name__ == "__main__":
    print("=== NodeLogger v3.0.0 Test ===")
    print(f"Timezone: {DERBY_TIMEZONE}")
    print(f"Device ID: {get_device_id()}")
    print(f"Log File: {DERBY_LOG_FILE}")
    print(f"JSON File: {DERBY_JSON_FILE}")
    print(f"rsyslog Server: {DERBY_RSYSLOG_IP}:{DERBY_RSYSLOG_PORT}")
    print("")

    logger = NodeLogger(name='nodetest', level=logging.DEBUG).get_logger()
    logger.debug("DEBUG: Node logger test - debug level")
    logger.info("INFO: Node logger test - info level")
    logger.warning("WARNING: Node logger test - warning level")
    logger.error("ERROR: Node logger test - error level", extra={
        'error_code': 'ERR-HW-201',
        'context': {'test': True}
    })
    logger.critical("CRITICAL: Node logger test - critical level")

    print("\nNode logger test complete.")
    print(f"Check {DERBY_LOG_FILE} for local text output.")
    print(f"Check {DERBY_JSON_FILE} for local JSON output.")
    print(f"Check central server at {DERBY_RSYSLOG_IP} for rsyslog output.")

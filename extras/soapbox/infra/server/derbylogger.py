"""
DerbyNet Unified Logger - Text + JSON Format
=============================================

Centralized logging framework for all Derby infrastructure components.
Supports dual output: human-readable text and parseable JSON (JSONL).

Version: 3.1.0
Date: 2026-01-15

CHANGELOG v3.1.0:
-----------------
    - Added correlation ID support for request tracing across components
    - Added session ID for grouping related operations
    - Added sequence numbers for log ordering during sync
    - Added sync metadata (sync_status, sync_batch) for cloud transmission
    - Thread-local correlation context for automatic propagation

TIME SYNCHRONIZATION:
---------------------
    All devices MUST sync time from the DerbyPi server (192.168.100.10).
    DerbyPi syncs via internet NTP or battery-backed RTC for offline use.
    Logs use local timezone (not UTC) for operator convenience.
    See LOGGING.md for complete time sync architecture documentation.

TEXT OUTPUT FORMAT:
-------------------
    2025-12-08 14:35:22.123 DEVICE:LEVEL [filename:line] message

JSON OUTPUT FORMAT (JSONL - one JSON object per line):
------------------------------------------------------
    {"ts": "2025-12-08T14:35:22.123-07:00", "level": "ERROR", "device": "FINISH1", ...}

CONFIGURATION:
--------------
    DERBY_TIMEZONE = 'America/Edmonton'     # All components MUST match
    DEFAULT_LOG_FILE = '/var/log/derbynet.log'        # Text format
    DEFAULT_JSON_FILE = '/var/log/derbynet.jsonl'     # JSON format

USAGE:
------
    from derbylogger import setup_logger, set_correlation_id, get_correlation_id

    logger = setup_logger('finishtimer')
    logger.info("Lane triggered")
    logger.error("Sensor timeout", extra={
        'error_code': 'ERR-HW-201',
        'context': {'lane': 2, 'timeout_ms': 5000}
    })

CORRELATION IDS:
----------------
    Correlation IDs trace requests across components (PHP → Python → MQTT → Timer).

    # At request start (e.g., MQTT message received)
    set_correlation_id('abc123')  # From incoming message
    # OR
    set_correlation_id()  # Auto-generate new ID

    # All subsequent logs automatically include the correlation ID
    logger.info("Processing race start")  # Includes corr_id: abc123

    # Pass to outgoing messages
    mqtt_msg['corr_id'] = get_correlation_id()

ENVIRONMENT VARIABLES:
----------------------
    DERBY_DEBUG=true        Enable DEBUG level logging
    DERBY_CONSOLE_LOG=true  Enable console output (disables JSON file)
    DERBY_DEVICE_ID=XXX     Override device ID (defaults to hostname)
    DERBY_JSON_LOG=true     Enable JSON file logging (default: true)
"""

import json
import logging
import logging.handlers
import os
import socket
import threading
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager

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
DEFAULT_JSON_FILE = '/var/log/derbynet.jsonl'
DEFAULT_RSYSLOG_IP = os.getenv('RSYSLOG_IP', '192.168.100.10')
DEFAULT_RSYSLOG_PORT = int(os.getenv('RSYSLOG_PORT', '514'))


# ============================================================================
# CORRELATION CONTEXT - Thread-local storage for request tracing
# ============================================================================

class CorrelationContext:
    """
    Thread-local storage for correlation IDs and session context.

    Enables tracing requests across components:
    - PHP request → Python server → MQTT → Timer → back

    All log entries automatically include the correlation ID when set.
    """

    _local = threading.local()
    _sequence_counter = 0
    _sequence_lock = threading.Lock()

    @classmethod
    def _get_next_sequence(cls) -> int:
        """Get next global sequence number for log ordering."""
        with cls._sequence_lock:
            cls._sequence_counter += 1
            return cls._sequence_counter

    @classmethod
    def set(cls, correlation_id: Optional[str] = None,
            session_id: Optional[str] = None,
            source: Optional[str] = None) -> str:
        """
        Set correlation context for current thread.

        Args:
            correlation_id: Request correlation ID (auto-generated if None)
            session_id: Session/batch ID for grouping operations
            source: Source component that initiated the request

        Returns:
            The correlation ID (generated or provided)
        """
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())[:12]  # Short UUID for readability

        cls._local.correlation_id = correlation_id
        cls._local.session_id = session_id
        cls._local.source = source
        cls._local.start_time = datetime.now()

        return correlation_id

    @classmethod
    def get(cls) -> Optional[str]:
        """Get current correlation ID for this thread."""
        return getattr(cls._local, 'correlation_id', None)

    @classmethod
    def get_session_id(cls) -> Optional[str]:
        """Get current session ID for this thread."""
        return getattr(cls._local, 'session_id', None)

    @classmethod
    def get_source(cls) -> Optional[str]:
        """Get source component for this request."""
        return getattr(cls._local, 'source', None)

    @classmethod
    def get_context(cls) -> Dict[str, Any]:
        """
        Get full correlation context as a dictionary.

        Returns:
            Dict with corr_id, session_id, source, seq (if set)
        """
        ctx = {}

        corr_id = cls.get()
        if corr_id:
            ctx['corr_id'] = corr_id

        session_id = cls.get_session_id()
        if session_id:
            ctx['session_id'] = session_id

        source = cls.get_source()
        if source:
            ctx['source'] = source

        # Always add sequence for ordering
        ctx['seq'] = cls._get_next_sequence()

        return ctx

    @classmethod
    def clear(cls):
        """Clear correlation context for current thread."""
        cls._local.correlation_id = None
        cls._local.session_id = None
        cls._local.source = None
        cls._local.start_time = None


# Convenience functions for correlation IDs
def set_correlation_id(correlation_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       source: Optional[str] = None) -> str:
    """
    Set correlation ID for request tracing.

    Call at the start of request processing (e.g., when MQTT message received).
    All subsequent log entries will include this correlation ID.

    Args:
        correlation_id: Request ID (auto-generated if None)
        session_id: Optional session/batch ID
        source: Optional source component identifier

    Returns:
        The correlation ID being used

    Example:
        # When receiving MQTT message
        msg_data = json.loads(payload)
        set_correlation_id(msg_data.get('corr_id'), source='finishtimer')

        # When starting new operation
        corr_id = set_correlation_id(source='derbyrace')
    """
    return CorrelationContext.set(correlation_id, session_id, source)


def get_correlation_id() -> Optional[str]:
    """
    Get current correlation ID.

    Use when passing correlation ID to outgoing messages.

    Example:
        mqtt_msg = {'corr_id': get_correlation_id(), 'data': ...}
    """
    return CorrelationContext.get()


def clear_correlation_id():
    """Clear correlation context after request processing complete."""
    CorrelationContext.clear()


@contextmanager
def correlation_context(correlation_id: Optional[str] = None,
                        session_id: Optional[str] = None,
                        source: Optional[str] = None):
    """
    Context manager for correlation ID scope.

    Automatically sets and clears correlation context.

    Example:
        with correlation_context(source='test'):
            logger.info("Starting test")
            do_work()
            logger.info("Test complete")
        # Context automatically cleared
    """
    try:
        set_correlation_id(correlation_id, session_id, source)
        yield get_correlation_id()
    finally:
        clear_correlation_id()


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


def get_iso8601_timestamp() -> str:
    """
    Return current timestamp in ISO 8601 format with timezone.
    Format: YYYY-MM-DDTHH:MM:SS.mmm+HH:MM
    """
    tz = get_tz(DERBY_TIMEZONE)
    if tz:
        now = datetime.now(tz)
        # Format with timezone offset
        return now.strftime('%Y-%m-%dT%H:%M:%S') + f'.{now.microsecond // 1000:03d}' + now.strftime('%z')
    else:
        now = datetime.now()
        return now.strftime('%Y-%m-%dT%H:%M:%S') + f'.{now.microsecond // 1000:03d}'


class DerbyTextFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as human-readable text.
    Format: timestamp DEVICE:LEVEL [filename:line] message
    """

    def __init__(self, device_id: str, component: str = ''):
        super().__init__()
        self.device_id = device_id
        self.component = component

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a text line."""
        timestamp = get_timezone_timestamp()
        device = getattr(record, 'device', self.device_id)
        location = f'{record.filename}:{record.lineno}'
        message = record.getMessage()

        # Include correlation ID if present
        corr_id = CorrelationContext.get()
        corr_prefix = f'[{corr_id}] ' if corr_id else ''

        # Include error code if present
        error_code = getattr(record, 'error_code', None)
        if error_code:
            message = f'[{error_code}] {message}'

        return f'{timestamp} {device}:{record.levelname} [{location}] {corr_prefix}{message}'


class DerbyJSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON (JSONL format).

    Each log entry is a single-line JSON object with fields:
    - ts: ISO 8601 timestamp with timezone
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - device: Device identifier
    - component: Module/component name
    - file: Source filename
    - line: Line number
    - msg: Log message
    - code: Error code (optional, from extra['error_code'])
    - ctx: Context data (optional, from extra['context'])
    """

    def __init__(self, device_id: str, component: str = ''):
        super().__init__()
        self.device_id = device_id
        self.component = component

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON line."""
        log_entry: Dict[str, Any] = {
            'ts': get_iso8601_timestamp(),
            'level': record.levelname,
            'device': getattr(record, 'device', self.device_id),
            'component': self.component or record.name.split('.')[-1],
            'file': record.filename,
            'line': record.lineno,
            'msg': record.getMessage(),
        }

        # Add correlation context (corr_id, session_id, source, seq)
        corr_ctx = CorrelationContext.get_context()
        log_entry.update(corr_ctx)

        # Add optional error code
        error_code = getattr(record, 'error_code', None)
        if error_code:
            log_entry['code'] = error_code

        # Add optional context
        context = getattr(record, 'context', None)
        if context:
            log_entry['ctx'] = context

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add sync metadata (for cloud sync service)
        log_entry['sync_status'] = 'pending'

        return json.dumps(log_entry, separators=(',', ':'))


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

        # Include error code if present
        error_code = getattr(record, 'error_code', None)
        if error_code:
            message = f'[{error_code}] {message}'

        return f'{device}:{record.levelname} [{location}] {message}'


class DerbyLogger:
    """
    Unified logging class for all Derby infrastructure components.

    Supports:
    - Text format output with timezone-aware timestamps
    - JSON format output for parsing and analysis (JSONL)
    - Multiple output handlers (file, JSON file, console, syslog)
    - Environment variable configuration
    - Error codes and context data
    """

    def __init__(
        self,
        component: str,
        device_id: Optional[str] = None,
        log_level: str = 'INFO',
        log_file: Optional[str] = DEFAULT_LOG_FILE,
        json_file: Optional[str] = None,
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
            log_file: Path to text log file (None to disable)
            json_file: Path to JSON log file (None = use default if DERBY_JSON_LOG=true)
            console: Enable console output (auto-detected from DERBY_CONSOLE_LOG if None)
            syslog: Enable rsyslog output (for remote devices)
            rsyslog_ip: IP address of rsyslog server
        """
        self.component = component
        self.device_id = device_id or get_device_id()

        # Environment variable overrides
        debug_mode = os.getenv('DERBY_DEBUG', 'false').lower() == 'true'
        console_mode = os.getenv('DERBY_CONSOLE_LOG', 'false').lower() == 'true'
        json_log_mode = os.getenv('DERBY_JSON_LOG', 'true').lower() == 'true'

        if debug_mode:
            log_level = 'DEBUG'

        if console is None:
            console = console_mode

        # Determine JSON file path
        if json_file is None and json_log_mode and not console:
            json_file = DEFAULT_JSON_FILE

        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.log_file = log_file
        self.json_file = json_file
        self.console = console
        self.syslog = syslog and not console  # Disable syslog if console is enabled
        self.rsyslog_ip = rsyslog_ip or os.getenv('DERBY_RSYSLOG_IP', DEFAULT_RSYSLOG_IP)

        # Create logger
        logger_name = f'derby.{self.device_id}.{component}'
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(self.log_level)

        # Configure handlers only if not already configured
        # Note: Use self.logger.handlers instead of hasHandlers() because
        # hasHandlers() returns True if parent loggers have handlers (like pytest)
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """Configure all logging handlers."""

        # 1. Text file handler
        if self.log_file:
            try:
                log_dir = os.path.dirname(self.log_file)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)

                file_handler = logging.FileHandler(self.log_file)
                file_handler.setLevel(self.log_level)
                file_handler.setFormatter(DerbyTextFormatter(self.device_id, self.component))
                self.logger.addHandler(file_handler)
            except Exception as e:
                print(f'Warning: Failed to create file handler for {self.log_file}: {e}')

        # 2. JSON file handler
        if self.json_file:
            try:
                json_dir = os.path.dirname(self.json_file)
                if json_dir:
                    os.makedirs(json_dir, exist_ok=True)

                json_handler = logging.FileHandler(self.json_file)
                json_handler.setLevel(self.log_level)
                json_handler.setFormatter(DerbyJSONFormatter(self.device_id, self.component))
                self.logger.addHandler(json_handler)
            except Exception as e:
                print(f'Warning: Failed to create JSON handler for {self.json_file}: {e}')

        # 3. Console handler (for debugging)
        if self.console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(DerbyTextFormatter(self.device_id, self.component))
            self.logger.addHandler(console_handler)

        # 4. Syslog handler (for remote collection)
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
    log_file: Optional[str] = DEFAULT_LOG_FILE,
    json_file: Optional[str] = None
) -> logging.Logger:
    """
    Convenience function to set up a logger with sensible defaults.

    For SERVER components - writes to text and JSON log files.
    For REMOTE devices (finishtimer, starttimer) - use with syslog=True.

    Args:
        component: Name of the component (e.g., 'derbyrace')
        device_id: Optional device identifier (auto-detected if not provided)
        log_level: Logging level (default: INFO)
        console: Enable console output (default: False)
        syslog: Enable rsyslog output (default: False)
        log_file: Path to text log file (default: /var/log/derbynet.log)
        json_file: Path to JSON log file (default: /var/log/derbynet.jsonl if not console)

    Returns:
        logging.Logger: Configured logger instance

    Example:
        logger = setup_logger('derbyrace')
        logger.info("Heat started")
        logger.error("Sensor timeout", extra={
            'error_code': 'ERR-HW-201',
            'context': {'lane': 2}
        })
    """
    return DerbyLogger(
        component=component,
        device_id=device_id,
        log_level=log_level,
        console=console,
        syslog=syslog,
        log_file=log_file,
        json_file=json_file
    ).get_logger()


# Backward compatibility alias
ServerLogger = DerbyLogger


if __name__ == '__main__':
    # Test the logger
    import tempfile
    import os

    print('=== DerbyLogger v3.0.0 Test ===\n')
    print(f'Timezone: {DERBY_TIMEZONE}')
    print(f'Device ID: {get_device_id()}')
    print(f'Text Log File: {DEFAULT_LOG_FILE}')
    print(f'JSON Log File: {DEFAULT_JSON_FILE}')
    print('')

    # Test with console output and temp files
    os.environ['DERBY_CONSOLE_LOG'] = 'true'
    os.environ['DERBY_DEBUG'] = 'true'

    with tempfile.TemporaryDirectory() as tmpdir:
        text_file = os.path.join(tmpdir, 'test.log')
        json_file = os.path.join(tmpdir, 'test.jsonl')

        logger = setup_logger(
            'test-component',
            device_id='TEST-DEVICE',
            log_file=text_file,
            json_file=json_file,
            console=True
        )

        print('\n--- Log Output ---')
        logger.debug('Debug message - detailed troubleshooting info')
        logger.info('Info message - normal operation')
        logger.warning('Warning message - something to watch')
        logger.error('Error message - something failed', extra={
            'error_code': 'ERR-HW-201',
            'context': {'lane': 2, 'timeout_ms': 5000}
        })
        logger.critical('Critical message - system failure', extra={
            'error_code': 'ERR-HW-301'
        })

        print('\n--- JSON File Contents ---')
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    print(json.dumps(entry, indent=2))
        else:
            print('(JSON file not created - console mode)')

    print('\n=== Test Complete ===')

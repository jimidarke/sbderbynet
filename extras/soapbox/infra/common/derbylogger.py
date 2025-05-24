#!/usr/bin/env python3
"""
DerbyNet Standardized Logging

VERSION = "0.5.1"

Version History:
- 0.5.1 - May 22, 2025 - Enhanced source file/line tracking and rsyslog integration
- 0.5.0 - May 19, 2025 - Standardized version schema across all components

This module provides a standardized logging framework for all DerbyNet components:
- Structured JSON logging
- Multi-destination logging (file, syslog, console)
- Correlation IDs for tracking related events
- Log rotation and management
- Configurable log levels per component
- Accurate file and line number tracking for log sources

Usage:
    from common.derbylogger import setup_logger, get_logger
    
    # Setup once at application start
    setup_logger('finish-timer', log_dir='/var/log/derbynet')
    
    # Get logger in any module
    logger = get_logger(__name__)
    
    # Standard logging
    logger.info("Processing race data")
    logger.error("Failed to connect", extra={"race_id": 123})
    
    # Structured logging with specific fields
    logger.structured_log(
        level="INFO", 
        message="Lane timer triggered",
        data={
            "lane": 1, 
            "time": 3.421,
            "race_id": 123
        }
    )
    
    # Create a child logger with correlation ID
    child_logger = logger.get_child("operation-xyz")
    child_logger.info("This log will include the correlation ID")
    
    # All logs will include the correct file and line number
    # In structured JSON output, they appear in the "location" field:
    # {
    #   "location": {
    #     "filename": "finishtimer.py",
    #     "lineno": 42,
    #     "function": "toggle_callback"
    #   }
    # }
"""

import os
import sys
import json
import uuid
import socket
import logging
import logging.handlers
import threading
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Optional, Callable, List, Union

# Import centralized configuration
try:
    from logging_config import get_config, is_production, is_debug
    CONFIG_AVAILABLE = True
except ImportError:
    # Fallback if config module not available
    CONFIG_AVAILABLE = False

# Constants
VERSION = "0.5.1"  # Module version - should match version in module docstring
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
DEFAULT_LOG_DIR = "/var/log/derbynet"
SYSLOG_ADDRESS = "/dev/log"  # Unix socket for syslog
SYSLOG_FACILITY = logging.handlers.SysLogHandler.LOG_LOCAL0
HOSTNAME = socket.gethostname()

# Global logger registry
_loggers = {}
_logger_lock = threading.Lock()
_log_config = {
    "log_dir": DEFAULT_LOG_DIR,
    "log_level": DEFAULT_LOG_LEVEL,
    "component": "unknown",
    "console_enabled": True,
    "file_enabled": True,
    "syslog_enabled": True,
    "json_enabled": True,
    "syslog_json": True,  # Use JSON format for syslog (recommended for troubleshooting)
    "file_json": False,   # Use plain text for local file logs
    "max_bytes": 2 * 1024 * 1024,  # 2 MB (reduced size for local backup files)
    "backup_count": 3,    # Reduced number of backup files
    "syslog_facility": SYSLOG_FACILITY,
}

def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance by name, creating it if necessary.
    
    Args:
        name: Logger name, typically __name__
    
    Returns:
        Logger instance with standard configuration
    """
    if not name:
        # If no name is provided, use the parent module name
        frame = sys._getframe(1)
        name = frame.f_globals.get('__name__', 'root')
    
    with _logger_lock:
        if name not in _loggers:
            _loggers[name] = DerbyLogger(name)
    
    return _loggers[name]

def setup_logger(
    component: str,
    log_dir: str = None,
    log_level: str = None,
    console: bool = None,
    file: bool = None,
    syslog: bool = None,
    json_format: bool = None,
    syslog_json: bool = None,
    file_json: bool = None,
    max_bytes: int = None,
    backup_count: int = None,
    syslog_facility: int = None,
    use_centralized_config: bool = True
) -> None:
    """
    Configure the logging system for this application.
    Should be called once at application startup.
    
    Args:
        component: Component name (e.g., 'finish-timer', 'server')
        log_dir: Directory for log files (None = use centralized config)
        log_level: Default log level (None = use centralized config)
        console: Enable console logging (None = use centralized config)
        file: Enable file logging (None = use centralized config)
        syslog: Enable syslog logging (None = use centralized config)
        json_format: Enable JSON-formatted logs (None = use centralized config)
        syslog_json: Use JSON format for syslog (None = use centralized config)
        file_json: Use JSON format for local file logs (None = use centralized config)
        max_bytes: Max log file size before rotation (None = use centralized config)
        backup_count: Number of backup log files to keep (None = use centralized config)
        syslog_facility: Syslog facility to use (None = use centralized config)
        use_centralized_config: Whether to use centralized configuration system
    """
    global _log_config
    
    # Get centralized configuration if available and requested
    if CONFIG_AVAILABLE and use_centralized_config:
        try:
            config = get_config()
            config_dict = config.get_config_dict()
            
            # Use centralized config as defaults, override with provided parameters
            log_dir = log_dir or config_dict["log_dir"]
            log_level = log_level or config_dict["log_level"]
            console = console if console is not None else config_dict["console_enabled"]
            file = file if file is not None else config_dict["file_enabled"]
            syslog = syslog if syslog is not None else config_dict["syslog_enabled"]
            syslog_json = syslog_json if syslog_json is not None else config.should_log_json("syslog")
            file_json = file_json if file_json is not None else config.should_log_json("file")
            max_bytes = max_bytes or config_dict["max_bytes"]
            backup_count = backup_count or config_dict["backup_count"]
            syslog_facility = syslog_facility or config.get_syslog_facility()
            
            # In production mode, output configuration info
            if config.is_production():
                sys.stderr.write(f"DerbyNet Logging: {component} configured for PRODUCTION mode\n")
            elif config.is_debug():
                sys.stderr.write(f"DerbyNet Logging: {component} configured for DEBUG mode\n")
                config.print_config()
        except Exception as e:
            sys.stderr.write(f"Warning: Error loading centralized config: {e}\n")
            # Fall back to defaults
            CONFIG_AVAILABLE = False
    
    # Apply fallback defaults if centralized config not available
    if not CONFIG_AVAILABLE or not use_centralized_config:
        log_dir = log_dir or DEFAULT_LOG_DIR
        log_level = log_level or DEFAULT_LOG_LEVEL
        console = console if console is not None else True
        file = file if file is not None else True
        syslog = syslog if syslog is not None else True
        syslog_json = syslog_json if syslog_json is not None else True
        file_json = file_json if file_json is not None else False
        max_bytes = max_bytes or (2 * 1024 * 1024)
        backup_count = backup_count or 3
        syslog_facility = syslog_facility or SYSLOG_FACILITY
    
    # Update configuration
    _log_config.update({
        "log_dir": log_dir,
        "log_level": log_level.upper(),
        "component": component,
        "console_enabled": console,
        "file_enabled": file,
        "syslog_enabled": syslog,
        "json_enabled": json_format or syslog_json,
        "syslog_json": syslog_json,
        "file_json": file_json,
        "max_bytes": max_bytes,
        "backup_count": backup_count,
        "syslog_facility": syslog_facility,
    })
    
    # Create log directory if it doesn't exist
    if file and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers to avoid duplicates during reconfiguration
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add standard handlers
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(CustomFormatter(json_format=False))  # Always use plain text for console
        root_logger.addHandler(console_handler)
    
    if file:
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, f"{component}.log"),
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(CustomFormatter(json_format=file_json))
        root_logger.addHandler(file_handler)
    
    if syslog:
        # Try remote rsyslog first, then fall back to local syslog
        syslog_handler = None
        
        if CONFIG_AVAILABLE and use_centralized_config:
            try:
                config = get_config()
                rsyslog_address = config.get_rsyslog_address()
                
                # Try remote rsyslog server
                syslog_handler = logging.handlers.SysLogHandler(
                    address=rsyslog_address,
                    facility=syslog_facility
                )
                # Test the connection with a dummy message
                test_record = logging.LogRecord(
                    name="test", level=logging.INFO, pathname="", lineno=0,
                    msg="DerbyNet logging test", args=(), exc_info=None
                )
                syslog_handler.emit(test_record)
                sys.stderr.write(f"DerbyNet Logging: Connected to remote rsyslog at {rsyslog_address[0]}:{rsyslog_address[1]}\n")
                
            except Exception as e:
                sys.stderr.write(f"Warning: Could not connect to remote rsyslog: {e}\n")
                syslog_handler = None
        
        # Fall back to local syslog if remote failed or not configured
        if syslog_handler is None and os.path.exists(SYSLOG_ADDRESS):
            try:
                syslog_handler = logging.handlers.SysLogHandler(
                    address=SYSLOG_ADDRESS,
                    facility=syslog_facility
                )
                sys.stderr.write("DerbyNet Logging: Using local syslog\n")
            except (socket.error, ConnectionRefusedError) as e:
                sys.stderr.write(f"Warning: Could not connect to local syslog: {e}\n")
        
        # Add the syslog handler if we got one
        if syslog_handler:
            syslog_handler.setFormatter(CustomFormatter(json_format=syslog_json))
            syslog_handler.setLevel(logging.DEBUG)  # Ensure all logs go to syslog
            root_logger.addHandler(syslog_handler)

class CustomFormatter(logging.Formatter):
    """Custom log formatter with enhanced JSON support for troubleshooting"""
    
    def __init__(self, json_format=False):
        """Initialize with JSON formatting option"""
        # Use a more detailed format for text logs
        text_format = "%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] %(message)s"
        super().__init__(text_format)
        self.json_format = json_format
    
    def format(self, record):
        """Format log record, optionally as JSON"""
        if not self.json_format:
            return super().format(record)
        
        # Extract standard fields
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "component": _log_config["component"],
            "hostname": HOSTNAME,
        }
        
        # Add location info - critical for troubleshooting
        log_data["location"] = {
            "filename": record.filename,
            "lineno": record.lineno,
            "function": record.funcName,
            "pathname": record.pathname,
            "module": record.module
        }
        
        # Add exception info if present with full traceback
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add process and thread info - useful for debugging concurrency issues
        log_data["process"] = {
            "id": record.process,
            "name": record.processName
        }
        
        log_data["thread"] = {
            "id": record.thread,
            "name": record.threadName
        }
        
        # Add correlation ID if present for request tracing
        if hasattr(record, 'correlation_id'):
            log_data["correlation_id"] = record.correlation_id
        
        # Add a timestamp_epoch for precise time ordering in logs
        log_data["timestamp_epoch"] = record.created
        
        # Add any extra fields passed by the application
        for key, value in record.__dict__.items():
            if key not in ['args', 'asctime', 'created', 'exc_info', 'exc_text', 
                          'filename', 'funcName', 'id', 'levelname', 'levelno', 
                          'lineno', 'module', 'msecs', 'message', 'msg', 'name', 
                          'pathname', 'process', 'processName', 'relativeCreated', 
                          'stack_info', 'thread', 'threadName']:
                if key != 'correlation_id':  # Already handled
                    log_data[key] = value
        
        # Format into compact JSON for rsyslog processing
        return json.dumps(log_data)

class DerbyLogger(logging.Logger):
    """Enhanced logger with additional features for DerbyNet"""
    
    def __init__(self, name):
        """Initialize the Derby logger"""
        super().__init__(name, _log_config["log_level"])
        self.correlation_id = None
    
    def get_child(self, name=None, correlation_id=None):
        """
        Get a child logger with optional correlation ID.
        
        Args:
            name: Optional additional name (will be appended to parent name)
            correlation_id: Optional correlation ID for tracking related events
        
        Returns:
            New logger instance with relationship to parent
        """
        if name:
            child_name = f"{self.name}.{name}"
        else:
            child_name = f"{self.name}.{str(uuid.uuid4())[:8]}"
        
        child = DerbyLogger(child_name)
        
        # Set correlation ID
        if correlation_id:
            child.correlation_id = correlation_id
        elif self.correlation_id:
            # Inherit parent's correlation ID
            child.correlation_id = self.correlation_id
        else:
            # Generate a new one
            child.correlation_id = str(uuid.uuid4())
        
        return child
    
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1):
        """Override _log to add correlation ID to all log records and increase stacklevel"""
        if extra is None:
            extra = {}
        
        if self.correlation_id and 'correlation_id' not in extra:
            extra['correlation_id'] = self.correlation_id
        
        # Increase stacklevel to skip our wrapper and capture the correct caller
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel + 1)
    
    # Override standard logging methods to use correct stacklevel
    def debug(self, msg, *args, **kwargs):
        """
        Log a message with level DEBUG.
        
        This override ensures that the correct file and line number are captured.
        """
        kwargs['stacklevel'] = kwargs.get('stacklevel', 1) + 1
        super().debug(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        """
        Log a message with level INFO.
        
        This override ensures that the correct file and line number are captured.
        """
        kwargs['stacklevel'] = kwargs.get('stacklevel', 1) + 1
        super().info(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        """
        Log a message with level WARNING.
        
        This override ensures that the correct file and line number are captured.
        """
        kwargs['stacklevel'] = kwargs.get('stacklevel', 1) + 1
        super().warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        """
        Log a message with level ERROR.
        
        This override ensures that the correct file and line number are captured.
        """
        kwargs['stacklevel'] = kwargs.get('stacklevel', 1) + 1
        super().error(msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        """
        Log a message with level CRITICAL.
        
        This override ensures that the correct file and line number are captured.
        """
        kwargs['stacklevel'] = kwargs.get('stacklevel', 1) + 1
        super().critical(msg, *args, **kwargs)
    
    def exception(self, msg, *args, exc_info=True, **kwargs):
        """
        Log a message with level ERROR, including exception info.
        
        This override ensures that the correct file and line number are captured.
        """
        kwargs['stacklevel'] = kwargs.get('stacklevel', 1) + 1
        super().exception(msg, *args, exc_info=exc_info, **kwargs)
    
    def structured_log(self, level, message, data=None, correlation_id=None):
        """
        Log a structured message with specific fields and data.
        
        Args:
            level: Log level (INFO, ERROR, etc.)
            message: Main log message
            data: Dictionary of additional data to include
            correlation_id: Optional correlation ID to use for this log only
        """
        if isinstance(level, str):
            level = getattr(logging, level.upper())
        
        extra = data or {}
        
        # Use provided correlation ID for this log only
        if correlation_id:
            extra['correlation_id'] = correlation_id
        
        # Use stacklevel=2 to skip the structured_log method call
        self.log(level, message, extra=extra, stacklevel=2)

def log_execution_time(logger=None, level=logging.INFO):
    """
    Decorator to log function execution time.
    
    Args:
        logger: Logger to use (if None, will get logger named after module)
        level: Log level for the timing message
    
    Usage:
        @log_execution_time()
        def my_function(arg1, arg2):
            # Function code here
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            
            if logger is None:
                logger = get_logger(func.__module__)
            
            start_time = datetime.now()
            result = func(*args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Use stacklevel=2 to skip the wrapper function and log with the decorator's caller's info
            logger.log(
                level, 
                f"Function {func.__name__} executed in {duration:.3f}s",
                extra={"duration": duration, "function": func.__name__},
                stacklevel=2
            )
            
            return result
        return wrapper
    return decorator

# Configure a default logger for imports
# Use centralized configuration system
try:
    setup_logger(component="default", use_centralized_config=True)
except Exception as e:
    # Fallback to basic configuration if centralized config fails
    sys.stderr.write(f"Warning: Centralized logging config failed, using defaults: {e}\n")
    setup_logger(
        component="default",
        log_dir=DEFAULT_LOG_DIR,
        log_level=DEFAULT_LOG_LEVEL,
        console=True,
        file=True,
        syslog=True,
        file_json=False,         # Plain text for local logs for easy reading
        syslog_json=True,        # Structured JSON for rsyslog for better troubleshooting
        max_bytes=2 * 1024 * 1024,  # 2MB max file size
        backup_count=3,          # Keep just 3 rotated files
        use_centralized_config=False
    )
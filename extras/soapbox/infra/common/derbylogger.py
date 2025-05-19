#!/usr/bin/env python3
"""
DerbyNet Standardized Logging

This module provides a standardized logging framework for all DerbyNet components:
- Structured JSON logging
- Multi-destination logging (file, syslog, console)
- Correlation IDs for tracking related events
- Log rotation and management
- Configurable log levels per component

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

# Constants
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
DEFAULT_LOG_DIR = "/var/log/derbynet"
SYSLOG_ADDRESS = "/dev/log"  # Unix socket for syslog
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
    "max_bytes": 10 * 1024 * 1024,  # 10 MB
    "backup_count": 5,
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
    log_dir: str = DEFAULT_LOG_DIR,
    log_level: str = DEFAULT_LOG_LEVEL,
    console: bool = True,
    file: bool = True,
    syslog: bool = True,
    json_format: bool = True,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5
) -> None:
    """
    Configure the logging system for this application.
    Should be called once at application startup.
    
    Args:
        component: Component name (e.g., 'finish-timer', 'server')
        log_dir: Directory for log files
        log_level: Default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console: Enable console logging
        file: Enable file logging
        syslog: Enable syslog logging
        json_format: Enable JSON-formatted logs
        max_bytes: Max log file size before rotation
        backup_count: Number of backup log files to keep
    """
    global _log_config
    
    # Update configuration
    _log_config.update({
        "log_dir": log_dir,
        "log_level": log_level.upper(),
        "component": component,
        "console_enabled": console,
        "file_enabled": file,
        "syslog_enabled": syslog,
        "json_enabled": json_format,
        "max_bytes": max_bytes,
        "backup_count": backup_count,
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
        console_handler.setFormatter(CustomFormatter())
        root_logger.addHandler(console_handler)
    
    if file:
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, f"{component}.log"),
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(CustomFormatter(json_format=json_format))
        root_logger.addHandler(file_handler)
    
    if syslog and os.path.exists(SYSLOG_ADDRESS):
        try:
            syslog_handler = logging.handlers.SysLogHandler(address=SYSLOG_ADDRESS)
            syslog_handler.setFormatter(CustomFormatter(json_format=json_format))
            root_logger.addHandler(syslog_handler)
        except (socket.error, ConnectionRefusedError) as e:
            sys.stderr.write(f"Warning: Could not connect to syslog: {e}\n")

class CustomFormatter(logging.Formatter):
    """Custom log formatter with JSON support"""
    
    def __init__(self, json_format=False):
        """Initialize with JSON formatting option"""
        super().__init__(DEFAULT_LOG_FORMAT)
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
        
        # Add location info
        log_data["location"] = {
            "filename": record.filename,
            "lineno": record.lineno,
            "function": record.funcName
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add thread info
        log_data["thread"] = {
            "id": record.thread,
            "name": record.threadName
        }
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_data["correlation_id"] = record.correlation_id
        
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in ['args', 'asctime', 'created', 'exc_info', 'exc_text', 
                          'filename', 'funcName', 'id', 'levelname', 'levelno', 
                          'lineno', 'module', 'msecs', 'message', 'msg', 'name', 
                          'pathname', 'process', 'processName', 'relativeCreated', 
                          'stack_info', 'thread', 'threadName']:
                if key != 'correlation_id':  # Already handled
                    log_data[key] = value
        
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
        """Override _log to add correlation ID to all log records"""
        if extra is None:
            extra = {}
        
        if self.correlation_id and 'correlation_id' not in extra:
            extra['correlation_id'] = self.correlation_id
        
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)
    
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
        
        self.log(level, message, extra=extra)

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
            
            logger.log(
                level, 
                f"Function {func.__name__} executed in {duration:.3f}s",
                extra={"duration": duration, "function": func.__name__}
            )
            
            return result
        return wrapper
    return decorator

# Configure a default logger for imports
setup_logger("default")
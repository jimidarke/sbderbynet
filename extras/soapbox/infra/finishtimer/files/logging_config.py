#!/usr/bin/env python3
"""
DerbyNet Centralized Logging Configuration

VERSION = "0.5.0"

This module provides centralized configuration for all DerbyNet logging.
It supports production/debug modes, environment variables, and centralized rsyslog.

Environment Variables:
    DERBY_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
    DERBY_LOG_MODE: production, development (default: development)
    DERBY_LOG_DEST: local, rsyslog, both (default: both)
    DERBY_RSYSLOG_SERVER: IP/hostname of rsyslog server (default: localhost)
    DERBY_RSYSLOG_PORT: Port for remote rsyslog (default: 514)
    DERBY_LOG_JSON: true/false - Use JSON formatting (default: true for rsyslog)
    DERBY_LOG_DIR: Directory for local log files (default: /var/log/derbynet)

Production Mode Features:
    - Reduces log levels (WARNING and above only)
    - Disables debug logging
    - Minimizes local file logging
    - Optimizes for performance
    - Uses centralized rsyslog exclusively
"""

import os
import socket
import logging
from typing import Dict, Any, Optional

VERSION = "0.5.0"

# Default configuration
DEFAULT_CONFIG = {
    # Server settings
    "rsyslog_server": "localhost",
    "rsyslog_port": 514,
    "rsyslog_facility": "local0",
    
    # Log levels per mode
    "log_level_production": "WARNING",
    "log_level_development": "INFO",
    "log_level_debug": "DEBUG",
    
    # Local logging settings
    "log_dir": "/var/log/derbynet",
    "max_bytes": 2 * 1024 * 1024,  # 2MB
    "backup_count": 3,
    
    # Format settings
    "json_format": True,
    "console_format": False,  # Always plain text for console
    
    # Feature toggles
    "console_enabled": True,
    "file_enabled": True,
    "syslog_enabled": True,
}

class LoggingConfig:
    """Centralized logging configuration for DerbyNet"""
    
    def __init__(self):
        """Initialize configuration from environment and defaults"""
        self.config = DEFAULT_CONFIG.copy()
        self._load_environment()
        self._validate_config()
    
    def _load_environment(self):
        """Load configuration from environment variables"""
        
        # Determine logging mode
        mode = os.environ.get("DERBY_LOG_MODE", "development").lower()
        self.config["mode"] = mode
        
        # Set log level based on mode and environment
        if mode == "production":
            default_level = self.config["log_level_production"]
            # In production, disable console and minimize file logging
            self.config["console_enabled"] = False
            self.config["file_enabled"] = True  # Keep minimal local backup
            self.config["max_bytes"] = 1024 * 1024  # 1MB max
            self.config["backup_count"] = 2  # Only 2 backups
        elif mode == "debug":
            default_level = self.config["log_level_debug"]
            # In debug mode, enable everything
            self.config["console_enabled"] = True
            self.config["file_enabled"] = True
        else:  # development
            default_level = self.config["log_level_development"]
        
        self.config["log_level"] = os.environ.get("DERBY_LOG_LEVEL", default_level).upper()
        
        # Destination configuration
        dest = os.environ.get("DERBY_LOG_DEST", "both").lower()
        if dest == "local":
            self.config["syslog_enabled"] = False
        elif dest == "rsyslog":
            self.config["file_enabled"] = False
            self.config["console_enabled"] = False
        # "both" is default - no changes needed
        
        # Network settings
        self.config["rsyslog_server"] = os.environ.get("DERBY_RSYSLOG_SERVER", "localhost")
        self.config["rsyslog_port"] = int(os.environ.get("DERBY_RSYSLOG_PORT", "514"))
        
        # Format settings
        json_env = os.environ.get("DERBY_LOG_JSON", "true").lower()
        self.config["json_format"] = json_env in ("true", "1", "yes")
        
        # Directory
        self.config["log_dir"] = os.environ.get("DERBY_LOG_DIR", self.config["log_dir"])
        
        # Service discovery for rsyslog server
        if self.config["rsyslog_server"] == "localhost":
            # Try to discover derbynetpi via hostname resolution
            try:
                derbynetpi_ip = socket.gethostbyname("derbynetpi")
                self.config["rsyslog_server"] = derbynetpi_ip
            except socket.gaierror:
                # Fallback to detecting if we're on the main server
                hostname = socket.gethostname()
                if hostname != "derbynetpi":
                    # We're on a remote device, try default server IP
                    self.config["rsyslog_server"] = "192.168.100.10"
    
    def _validate_config(self):
        """Validate the configuration"""
        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.config["log_level"] not in valid_levels:
            self.config["log_level"] = "INFO"
        
        # Validate mode
        valid_modes = ["production", "development", "debug"]
        if self.config["mode"] not in valid_modes:
            self.config["mode"] = "development"
        
        # Ensure at least one destination is enabled
        if not any([
            self.config["console_enabled"],
            self.config["file_enabled"], 
            self.config["syslog_enabled"]
        ]):
            # Fallback to console if nothing else is enabled
            self.config["console_enabled"] = True
    
    def get_rsyslog_address(self):
        """Get rsyslog address tuple for remote logging"""
        return (self.config["rsyslog_server"], self.config["rsyslog_port"])
    
    def get_syslog_facility(self):
        """Get syslog facility constant"""
        facility_map = {
            "local0": logging.handlers.SysLogHandler.LOG_LOCAL0,
            "local1": logging.handlers.SysLogHandler.LOG_LOCAL1,
            "local2": logging.handlers.SysLogHandler.LOG_LOCAL2,
            "local3": logging.handlers.SysLogHandler.LOG_LOCAL3,
            "local4": logging.handlers.SysLogHandler.LOG_LOCAL4,
            "local5": logging.handlers.SysLogHandler.LOG_LOCAL5,
            "local6": logging.handlers.SysLogHandler.LOG_LOCAL6,
            "local7": logging.handlers.SysLogHandler.LOG_LOCAL7,
        }
        return facility_map.get(self.config["rsyslog_facility"], 
                               logging.handlers.SysLogHandler.LOG_LOCAL0)
    
    def is_production(self):
        """Check if running in production mode"""
        return self.config["mode"] == "production"
    
    def is_debug(self):
        """Check if running in debug mode"""
        return self.config["mode"] == "debug"
    
    def get_log_level(self):
        """Get the configured log level as logging constant"""
        return getattr(logging, self.config["log_level"])
    
    def should_log_json(self, destination="syslog"):
        """Check if JSON logging should be used for a destination"""
        if destination == "console":
            return False  # Always plain text for console
        elif destination == "file":
            return self.config["json_format"] and not self.is_production()
        else:  # syslog
            return self.config["json_format"]
    
    def get_config_dict(self):
        """Get complete configuration as dictionary"""
        return self.config.copy()
    
    def print_config(self):
        """Print current configuration (for debugging)"""
        print("=== DerbyNet Logging Configuration ===")
        print(f"Mode: {self.config['mode']}")
        print(f"Log Level: {self.config['log_level']}")
        print(f"Rsyslog Server: {self.config['rsyslog_server']}:{self.config['rsyslog_port']}")
        print(f"Console: {self.config['console_enabled']}")
        print(f"File: {self.config['file_enabled']} ({'JSON' if self.should_log_json('file') else 'Text'})")
        print(f"Syslog: {self.config['syslog_enabled']} ({'JSON' if self.should_log_json('syslog') else 'Text'})")
        print(f"Log Directory: {self.config['log_dir']}")
        print("==========================================")

# Global configuration instance
_config = None

def get_config() -> LoggingConfig:
    """Get the global logging configuration instance"""
    global _config
    if _config is None:
        _config = LoggingConfig()
    return _config

def reload_config():
    """Reload configuration from environment (useful for testing)"""
    global _config
    _config = LoggingConfig()
    return _config

# Convenience functions
def is_production():
    """Check if running in production mode"""
    return get_config().is_production()

def is_debug():
    """Check if running in debug mode"""
    return get_config().is_debug()

def get_log_level():
    """Get current log level"""
    return get_config().get_log_level()

def get_rsyslog_server():
    """Get rsyslog server address"""
    config = get_config()
    return config.config["rsyslog_server"]

if __name__ == "__main__":
    # Test configuration
    config = get_config()
    config.print_config()
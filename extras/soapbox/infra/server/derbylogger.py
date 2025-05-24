#!/usr/bin/env python3
"""
Server implementation of the standardized DerbyNet logging system.
This module delegates to the common derbylogger implementation.
"""

import os
import sys

# Add common library path to allow importing modules
common_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'common'))
if common_path not in sys.path:
    sys.path.append(common_path)

try:
    # Import from common derbylogger implementation
    from common.derbylogger import setup_logger as common_setup_logger, get_logger
    
    def setup_logger(name, log_dir=None):
        """
        Set up a logger using the standardized common implementation.
        
        Args:
            name: Logger name, typically module name
            log_dir: Optional custom log directory
            
        Returns:
            Logger instance configured with standard settings
        """
        # Override default settings for server component
        log_dir = log_dir or "/var/log/derbynet"
        
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Set up with server-specific settings
        return common_setup_logger(
            component="server", 
            log_dir=log_dir,
            log_level="INFO",
            console=True,
            file=True,
            syslog=True,
            json_format=True
        )
    
except ImportError as e:
    # Fallback implementation if common logger isn't available
    import logging
    import logging.handlers
    import uuid
    
    LOG_FORMAT_LOCAL = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'
    LOG_FORMAT_SYSLOG = '{hwID} %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'
    LOG_FILE = '/var/log/derbynet.log'
    LOG_LEVEL = logging.INFO
    SYSLOG_HOST = 'localhost'
    SYSLOG_PORT = 514
    
    def setup_logger(name):
        #print(f"WARNING: Using fallback logger - common derbylogger not available")
        
        hwid = "SERVER"
        
        logger = logging.getLogger(name)
        logger.setLevel(LOG_LEVEL)
        
        # File handler
        formatter = logging.Formatter(LOG_FORMAT_LOCAL)
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setFormatter(formatter)
        
        # Syslog handler
        try:
            formatter = logging.Formatter(LOG_FORMAT_SYSLOG.format(hwID=hwid))
            syslog_handler = logging.handlers.SysLogHandler(address=(SYSLOG_HOST, SYSLOG_PORT))
            syslog_handler.setFormatter(formatter)
            
            # Avoid adding handlers multiple times if already configured
            if not logger.hasHandlers():
                logger.addHandler(file_handler)
                logger.addHandler(syslog_handler)
        except:
            # Fallback to file-only logging if syslog fails
            if not logger.hasHandlers():
                logger.addHandler(file_handler)
        
        return logger
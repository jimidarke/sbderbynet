#!/usr/bin/env python3
"""
Derby Display implementation of the standardized DerbyNet logging system.
This module delegates to the common derbylogger implementation.
"""

import os
import sys
import uuid

# Add common library path to allow importing modules
common_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'common'))
if common_path not in sys.path:
    sys.path.append(common_path)

# Get hardware ID from derbyid.txt or MAC address
def get_hardware_id():
    if os.path.exists("/boot/firmware/derbyid.txt"):
        with open("/boot/firmware/derbyid.txt", "r") as f:
            return f.read().strip()
    else:
        # Fallback to MAC address
        return ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])

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
        # Override default settings for display component
        log_dir = log_dir or "/var/log/derbynet"
        
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Set up with display-specific settings
        logger = common_setup_logger(
            component=f"display-{get_hardware_id()}", 
            log_dir=log_dir,
            log_level="INFO",
            console=True,
            file=True,
            syslog=True,
            json_format=True
        )
        
        return logger
    
except ImportError as e:
    # Fallback implementation if common logger isn't available
    import logging
    import logging.handlers
    
    LOG_FORMAT_LOCAL = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'
    LOG_FORMAT_SYSLOG = '{hwID} %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'
    LOG_FILE = '/var/log/derbynet.log'
    LOG_LEVEL = logging.INFO
    SYSLOG_HOST = '192.168.100.10'
    SYSLOG_PORT = 514
    
    def setup_logger(name):
        print(f"WARNING: Using fallback logger - common derbylogger not available: {e}")
        
        hwid = get_hardware_id()
        
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
        except Exception as ex:
            # Fallback to file-only logging if syslog fails
            print(f"Syslog connection failed: {ex}")
            if not logger.hasHandlers():
                logger.addHandler(file_handler)
        
        return logger
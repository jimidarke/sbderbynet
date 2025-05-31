'''
Logging framework for Derby nodes and server components.

SAMPLE USAGE:

from serverlogger import ServerLogger
import logging

# Production logging (file + rsyslog)
logger = ServerLogger(
    name='finishtimer',
    log_file='/var/log/derbynet.log',
    level=logging.INFO
).get_logger()

# Debug logging to console (disables rsyslog to avoid conflicts)
debug_logger = ServerLogger(
    name='finishtimer',
    log_file='/var/log/derbynet.log',
    level=logging.DEBUG,
    console=True  # Enables console output, disables rsyslog
).get_logger()

# Environment variable control for easy debugging
import os
console_mode = os.getenv('DERBY_CONSOLE_LOG', 'false').lower() == 'true'
debug_mode = os.getenv('DERBY_DEBUG', 'false').lower() == 'true'

logger = ServerLogger(
    name='derbyrace',
    level=logging.DEBUG if debug_mode else logging.INFO,
    console=console_mode
).get_logger()

# Usage examples:
logger.info("Finish timer initialized.")
logger.debug("Sensor reading: lane 1 = 3.24V")  # Only shows if level=DEBUG
logger.error("Sensor timeout on lane 2.")
logger.warning("Low battery on node 3.")

'''

#DERBY_LOG_FORMAT = '%(asctime)s [%(levelname)s] [{}] [%(filename)s] [%(lineno)d] %(message)s'  
#LOG_FORMAT_SYSLOG  = '{hwID} %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'

DERBY_LOG_FORMAT   = '%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s'  
DERBY_SYSLOG_FORMAT = '{} %(levelname)s [%(filename)s:%(lineno)d] %(message)s'

DERBY_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DERBY_RSYSLOG_IP = '127.0.0.1'

import logging
import logging.handlers
import os
import socket
import inspect

class ServerLogger:
    """
    A logger for Derby nodes that supports local and rsyslog logging with a consistent format.
    
    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level
        console: Enable console output (disables rsyslog to avoid conflicts)
        enable_rsyslog: Enable rsyslog output (disabled if console=True)
    """
    def __init__(self, name='derbyserver', log_file='/var/log/derbynet.log', level=logging.INFO, 
                 console=False, enable_rsyslog=True):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        formatter = logging.Formatter(fmt=DERBY_LOG_FORMAT, datefmt=DERBY_DATE_FORMAT)

        # Avoid adding handlers multiple times if already configured
        if not self.logger.hasHandlers():
            
            # File handler - always enabled
            try:
                # Create log directory if it doesn't exist
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                file_handler.setLevel(level)
                self.logger.addHandler(file_handler)
            except Exception as e:
                # If file logging fails, at least get console output
                console = True
                print(f"Warning: Failed to create file handler for {log_file}: {e}")
            
            # Console handler - for debugging (conflicts with rsyslog)
            if console:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                console_handler.setLevel(level)
                self.logger.addHandler(console_handler)
                enable_rsyslog = False  # Disable rsyslog when console is enabled
                
            # Syslog handler - disabled when console logging is enabled
            if enable_rsyslog:
                try:
                    syslog_formatter = logging.Formatter(fmt=DERBY_SYSLOG_FORMAT.format(name))
                    syslog_handler = logging.handlers.SysLogHandler(address=(DERBY_RSYSLOG_IP, 514))
                    syslog_handler.setFormatter(syslog_formatter)
                    syslog_handler.setLevel(level)
                    self.logger.addHandler(syslog_handler)
                except Exception as e:
                    # If syslog fails, don't crash - just log to console if available
                    if console:
                        print(f"Warning: Failed to create syslog handler: {e}")
                    else:
                        # Enable console as fallback
                        console_handler = logging.StreamHandler()
                        console_handler.setFormatter(formatter)
                        console_handler.setLevel(level)
                        self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger

if __name__ == "__main__":
    import sys
    
    # Test with console output enabled (for debugging)
    print("=== Testing Console Debug Logging ===")
    debug_logger = ServerLogger(
        name='derby-test', 
        level=logging.DEBUG, 
        console=True  # This disables rsyslog
    ).get_logger()
    
    debug_logger.debug("DEBUG: This message shows in console with debug logging")
    debug_logger.info("INFO: Derby node logger test with console output")
    debug_logger.warning("WARNING: Example warning message")
    debug_logger.error("ERROR: Example error message")
    debug_logger.critical("CRITICAL: Example critical message")
    
    print("\n=== Testing Production Logging (file + rsyslog) ===")
    prod_logger = ServerLogger(
        name='derby-prod',
        level=logging.INFO,
        console=False  # Uses rsyslog + file
    ).get_logger()
    
    prod_logger.debug("DEBUG: This won't show (level=INFO)")
    prod_logger.info("INFO: Production logging test - check /var/log/derbynet.log")
    prod_logger.warning("WARNING: Production warning message")
    
    print(f"\nLogger test complete. Console output shown above.")
    print(f"File output: Check /var/log/derbynet.log")
    print(f"Syslog output: Check syslog if rsyslog is configured")
    print(f"\nTo enable debug console logging in services:")
    print(f"  export DERBY_CONSOLE_LOG=true")
    print(f"  export DERBY_DEBUG=true")
    print(f"  python3 your_service.py")

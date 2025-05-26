'''
Logging framework for Derby nodes such as the finish timer and derby display. 
Not used on the server. 


SAMPLE:

from nodelogger import NodeLogger

logger = NodeLogger(
    name='finishtimer', # Name of the logger, can be anything like 'finishtimer', 'derbydisplay', etc.
    log_file='/var/log/derbynet.log', # Default
    level=logging.INFO,  # Default log level
).get_logger()

logger.info("Finish timer initialized.")
logger.error("Sensor timeout on lane 2.")
logger.warning("Low battery on node 3.")

'''

#DERBY_LOG_FORMAT = '%(asctime)s [%(levelname)s] [{}] [%(filename)s] [%(lineno)d] %(message)s'  
#LOG_FORMAT_SYSLOG  = '{hwID} %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'

DERBY_LOG_FORMAT   = '%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s'  
DERBY_SYSLOG_FORMAT = '{} %(levelname)s [%(filename)s:%(lineno)d] %(message)s'

DERBY_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DERBY_RSYSLOG_IP = '192.168.100.10'  # Default rsyslog server IP, can be overridden

import logging
import logging.handlers
import os
import socket
import inspect

class NodeLogger:
    """
    A logger for Derby nodes that supports local and rsyslog logging with a consistent format. 

    """
    def __init__(self, name='derby', log_file='/var/log/derbynet.log', level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        hostname = socket.gethostname()
        hostname = hostname.split('.')[0]  # Get just the hostname without domain
        hostname = f"{hostname}"
        formatter = logging.Formatter(fmt=DERBY_LOG_FORMAT,datefmt=DERBY_DATE_FORMAT)

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        
        # Add a console handler for debugging
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)

        # Syslog handler
        formatter = logging.Formatter(fmt=DERBY_SYSLOG_FORMAT.format(hostname))
        syslog_handler = logging.handlers.SysLogHandler(address=(DERBY_RSYSLOG_IP, 514))
        syslog_handler.setFormatter(formatter)
        syslog_handler.setLevel(level)
        
        # Avoid adding handlers multiple times if already configured
        if not self.logger.hasHandlers():
            self.logger.addHandler(file_handler)
            self.logger.addHandler(syslog_handler)
            self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger

if __name__ == "__main__":
    # Example usage
    #logger = NodeLogger(name='derby', log_file='/var/log/derbynet.log', level=logging.INFO).get_logger()
    logger = NodeLogger(level=logging.DEBUG).get_logger()
    logger.debug("EXAMPLE OF DERBY NODE LOGGER USAGE DEBUG")
    logger.info("EXAMPLE OF DERBY NODE LOGGER USAGE INFO ")
    logger.warning("EXAMPLE OF DERBY NODE LOGGER USAGE WARNING")
    logger.error("EXAMPLE OF DERBY NODE LOGGER USAGE ERROR")
    logger.critical("EXAMPLE OF DERBY NODE LOGGER USAGE CRITICAL")
    logger.info("Node logger test successful. Check /var/log/derbynet.log for output.")

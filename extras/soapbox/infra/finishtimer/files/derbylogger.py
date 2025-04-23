import logging
import logging.handlers
import os
import uuid

LOG_FORMAT_LOCAL    = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'
LOG_FORMAT_SYSLOG   = '{hwID} %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'
LOG_FILE            = '/var/log/derbynet.log'
LOG_LEVEL           = logging.INFO  # Set to DEBUG for detailed logs, INFO for less verbosity
SYSLOG_HOST         = '192.168.100.10' 
SYSLOG_PORT         = 514

def setup_logger(name):
    
    if os.path.exists("/boot/firmware/derbyid.txt"):
        with open("/boot/firmware/derbyid.txt", "r") as f:
            hwid = f.read().strip()
    else:
        hwid = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])

    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)  # You can change this to INFO for less verbosity

    # File handler
    formatter = logging.Formatter(LOG_FORMAT_LOCAL)
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)

    # Syslog handler
    formatter = logging.Formatter(LOG_FORMAT_SYSLOG.format(hwID=hwid))
    syslog_handler = logging.handlers.SysLogHandler(address=(SYSLOG_HOST, SYSLOG_PORT))
    syslog_handler.setFormatter(formatter)

    # Avoid adding handlers multiple times if already configured
    if not logger.hasHandlers():
        logger.addHandler(file_handler)
        logger.addHandler(syslog_handler)

    return logger

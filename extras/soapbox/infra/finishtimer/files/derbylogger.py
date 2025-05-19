import logging
import logging.handlers
import os
import uuid
import time
import json
import socket
import threading

# Logging configuration
LOG_FORMAT_LOCAL    = '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'
LOG_FORMAT_SYSLOG   = '{hwID} %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'
LOG_FORMAT_JSON     = '{{"timestamp":"%(asctime)s", "level":"%(levelname)s", "hwid":"{hwID}", "file":"%(filename)s", "line":%(lineno)d, "message":"%(message)s"}}'
LOG_FILE            = '/var/log/derbynet.log'
LOG_LEVEL           = logging.INFO  # Set to DEBUG for detailed logs, INFO for less verbosity
SYSLOG_HOST         = '192.168.100.10' 
SYSLOG_PORT         = 514

# Offline logging buffer
LOG_BUFFER_DIR      = '/var/log/derbynet/buffer'
BUFFER_MAX_SIZE     = 1000  # Maximum number of buffered log messages
BUFFER_SEND_INTERVAL = 30   # Seconds between buffer flush attempts

# Create buffer directory if it doesn't exist
os.makedirs(LOG_BUFFER_DIR, exist_ok=True)

# Buffer for storing logs when network is down
log_buffer = []
log_buffer_lock = threading.Lock()

# Context information for enhanced logging
context_data = {}
context_lock = threading.Lock()

class BufferedSysLogHandler(logging.handlers.SysLogHandler):
    """Extends SysLogHandler to buffer messages when connection fails"""
    
    def __init__(self, hwid, *args, **kwargs):
        self.hwid = hwid
        self.buffer_enabled = True
        self.last_connection_attempt = 0
        super().__init__(*args, **kwargs)
        
        # Start background thread for sending buffered logs
        self._start_buffer_processor()
    
    def emit(self, record):
        try:
            super().emit(record)
        except (socket.error, OSError) as e:
            # If connection fails, buffer the log message
            if self.buffer_enabled:
                self._buffer_record(record)
    
    def _buffer_record(self, record):
        """Store log record in buffer for later transmission"""
        global log_buffer
        
        with log_buffer_lock:
            # Convert record to a serializable format
            formatted = self.format(record)
            timestamp = time.time()
            
            # Create buffer entry
            entry = {
                'formatted': formatted,
                'timestamp': timestamp,
                'level': record.levelno,
                'module': record.module,
                'hwid': self.hwid
            }
            
            # Add to memory buffer
            log_buffer.append(entry)
            
            # Trim buffer if needed
            if len(log_buffer) > BUFFER_MAX_SIZE:
                log_buffer = log_buffer[-BUFFER_MAX_SIZE:]
            
            # Also write to disk for persistence
            self._write_buffer_to_disk(entry)
    
    def _write_buffer_to_disk(self, entry):
        """Write buffered log to disk"""
        try:
            filename = f"{LOG_BUFFER_DIR}/log_{int(entry['timestamp']*1000)}.json"
            with open(filename, 'w') as f:
                json.dump(entry, f)
        except Exception as e:
            pass  # Can't log this error since logging is what failed
    
    def _flush_buffer(self):
        """Try to send buffered logs to syslog server"""
        global log_buffer
        
        # Don't attempt reconnection too frequently
        now = time.time()
        if now - self.last_connection_attempt < 5:  # 5 second cooldown
            return
            
        self.last_connection_attempt = now
        
        if not log_buffer:
            return
            
        try:
            # Test connection to syslog server
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            sock.connect((SYSLOG_HOST, SYSLOG_PORT))
            sock.close()
            
            # Connection successful, try to send buffer
            with log_buffer_lock:
                # Process disk buffer first
                self._process_disk_buffer()
                
                # Process memory buffer
                remaining = []
                for entry in log_buffer:
                    try:
                        # Create a mock record to emit
                        record = logging.LogRecord(
                            name=entry.get('module', 'buffered'),
                            level=entry.get('level', logging.INFO),
                            pathname='',
                            lineno=0,
                            msg=entry.get('formatted', ''),
                            args=(),
                            exc_info=None
                        )
                        super().emit(record)
                    except Exception:
                        remaining.append(entry)
                
                # Update buffer with failed sends
                log_buffer = remaining
                
        except (socket.error, OSError):
            # Still can't connect, just exit
            pass
    
    def _process_disk_buffer(self):
        """Process logs that were saved to disk"""
        try:
            files = os.listdir(LOG_BUFFER_DIR)
            log_files = sorted([f for f in files if f.startswith('log_') and f.endswith('.json')])[:50]  # Process in batches
            
            for file in log_files:
                try:
                    filepath = os.path.join(LOG_BUFFER_DIR, file)
                    with open(filepath, 'r') as f:
                        entry = json.load(f)
                    
                    # Create a mock record to emit
                    record = logging.LogRecord(
                        name=entry.get('module', 'buffered'),
                        level=entry.get('level', logging.INFO),
                        pathname='',
                        lineno=0,
                        msg=entry.get('formatted', ''),
                        args=(),
                        exc_info=None
                    )
                    
                    # Try to send
                    super().emit(record)
                    
                    # If successful, remove the file
                    os.remove(filepath)
                except Exception:
                    # Failed to process this file, leave it for next attempt
                    continue
        except Exception:
            pass
    
    def _start_buffer_processor(self):
        """Start background thread to periodically flush buffer"""
        def buffer_processor():
            while True:
                try:
                    self._flush_buffer()
                except Exception:
                    pass
                time.sleep(BUFFER_SEND_INTERVAL)
        
        thread = threading.Thread(target=buffer_processor, daemon=True)
        thread.start()


def set_context(key, value):
    """Set context data that will be included in all log messages"""
    with context_lock:
        context_data[key] = value

def get_context():
    """Get the current logging context"""
    with context_lock:
        return context_data.copy()

def clear_context():
    """Clear all context data"""
    with context_lock:
        context_data.clear()

def setup_logger(name):
    """Set up a logger with file, syslog, and optional JSON handlers"""
    # Get hardware ID
    if os.path.exists("/boot/firmware/derbyid.txt"):
        with open("/boot/firmware/derbyid.txt", "r") as f:
            hwid = f.read().strip()
    else:
        hwid = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)])

    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # Skip setup if already configured
    if logger.hasHandlers():
        return logger

    # File handler - regular text format
    file_formatter = logging.Formatter(LOG_FORMAT_LOCAL)
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # JSON file handler - structured logging
    json_file = f"{os.path.splitext(LOG_FILE)[0]}.json"
    json_formatter = logging.Formatter(LOG_FORMAT_JSON.format(hwID=hwid))
    json_handler = logging.FileHandler(json_file)
    json_handler.setFormatter(json_formatter)
    logger.addHandler(json_handler)

    # Buffered Syslog handler
    syslog_formatter = logging.Formatter(LOG_FORMAT_SYSLOG.format(hwID=hwid))
    try:
        syslog_handler = BufferedSysLogHandler(hwid, address=(SYSLOG_HOST, SYSLOG_PORT))
        syslog_handler.setFormatter(syslog_formatter)
        logger.addHandler(syslog_handler)
    except Exception as e:
        # If syslog setup fails, log to file but continue
        fallback_handler = logging.FileHandler(LOG_FILE)
        fallback_handler.setFormatter(file_formatter)
        logger.addHandler(fallback_handler)
        logger.error(f"Failed to set up syslog handler: {e}")

    # Store the original _log method
    original_log = logging.Logger._log
    
    # Add a method to include context in logs
    def log_with_context(self, level, msg, *args, **kwargs):
        """Add current context to log message"""
        with context_lock:
            if context_data:
                context_str = ' '.join(f"{k}={v}" for k, v in context_data.items())
                msg = f"{msg} [{context_str}]"
        
        # Call original log method
        return original_log(self, level, msg, *args, **kwargs)
    
    # Replace the _log method to include context
    setattr(logging.Logger, '_log', log_with_context)

    return logger

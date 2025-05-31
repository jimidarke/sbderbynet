# Server Logging Guide

This document explains the logging system used by Derby server components.

## Overview

The `serverlogger.py` module provides unified logging for all server components with support for:
- **File logging**: Always enabled (`/var/log/derbynet.log`)
- **Rsyslog**: For centralized logging (production mode)
- **Console logging**: For debugging (disables rsyslog to avoid conflicts)

## Quick Debug Mode

For immediate troubleshooting, use the debug runner:

```bash
# Run any server component with debug console logging
./debug-run.sh derbyRace.py
./debug-run.sh derbyTime.py
./debug-run.sh lcdscreen/derbyLCD.py
```

This automatically enables:
- Console output (visible in terminal)
- Debug level logging (shows all messages)
- Disables rsyslog (prevents conflicts)

## Environment Variables

Control logging behavior with environment variables:

```bash
# Enable console output (disables rsyslog)
export DERBY_CONSOLE_LOG=true

# Enable debug level logging
export DERBY_DEBUG=true

# Run service
python3 derbyRace.py
```

## Logging Modes

### Production Mode (Default)
```python
from serverlogger import ServerLogger
import logging

logger = ServerLogger(
    name='derbyrace',
    level=logging.INFO,
    console=False  # Default - uses rsyslog + file
).get_logger()
```

**Output:**
- File: `/var/log/derbynet.log`
- Rsyslog: Sent to syslog daemon
- Console: None

### Debug Mode
```python
logger = ServerLogger(
    name='derbyrace',
    level=logging.DEBUG,
    console=True  # Enables console, disables rsyslog
).get_logger()
```

**Output:**
- File: `/var/log/derbynet.log`
- Console: All messages visible in terminal
- Rsyslog: Disabled (prevents conflicts)

### Environment-Controlled Mode
```python
import os
console_mode = os.getenv('DERBY_CONSOLE_LOG', 'false').lower() == 'true'
debug_mode = os.getenv('DERBY_DEBUG', 'false').lower() == 'true'

logger = ServerLogger(
    name='derbyrace',
    level=logging.DEBUG if debug_mode else logging.INFO,
    console=console_mode
).get_logger()
```

## Log Format

All logs use a consistent format:
```
2025-05-31 15:30:45 INFO [derbyRace.py:123] Race started for Class A
2025-05-31 15:30:46 DEBUG [derbyRace.py:145] MQTT message: {"lane": 1, "time": 3.45}
2025-05-31 15:30:47 ERROR [derbyRace.py:167] Sensor timeout on lane 2
```

Format: `timestamp level [filename:line] message`

## Why Console and Rsyslog Conflict

**Problem**: When both console and rsyslog handlers are active simultaneously, log messages can be duplicated or interfere with each other, especially in systemd services.

**Solution**: The logger automatically disables rsyslog when console logging is enabled.

## Integration Examples

### Existing Service (derbyRace.py)
```python
# Already updated to use environment variables
from serverlogger import ServerLogger
import os
import logging

console_mode = os.getenv('DERBY_CONSOLE_LOG', 'false').lower() == 'true'
debug_mode = os.getenv('DERBY_DEBUG', 'false').lower() == 'true'

logger = ServerLogger(
    name='derbyrace',
    level=logging.DEBUG if debug_mode else logging.INFO,
    console=console_mode
).get_logger()
```

### New Service
```python
from serverlogger import ServerLogger
import logging

# Simple production logging
logger = ServerLogger(name='mynewservice').get_logger()

# Use logger
logger.info("Service started")
logger.debug("This won't show unless debug is enabled")
logger.error("Something went wrong")
```

## Troubleshooting

### No Console Output
- Ensure `DERBY_CONSOLE_LOG=true` is set
- Check that service isn't running as systemd service (use debug-run.sh)

### Debug Messages Not Showing
- Set `DERBY_DEBUG=true` to enable debug level
- Check that logger level is set to `logging.DEBUG`

### Rsyslog Not Working
- Ensure console logging is disabled (`DERBY_CONSOLE_LOG=false`)
- Check that rsyslog daemon is running: `systemctl status rsyslog`
- Verify syslog configuration allows connections on port 514

### Permission Errors
- Ensure log directory exists: `sudo mkdir -p /var/log`
- Check write permissions: `sudo touch /var/log/derbynet.log`
- Run with appropriate user permissions

## Service Integration

For systemd services, add environment variables to the service file:

```ini
[Service]
Environment=DERBY_CONSOLE_LOG=false
Environment=DERBY_DEBUG=false
ExecStart=/usr/bin/python3 /opt/derbynet/derbyRace.py
```

For debug sessions, temporarily enable console logging:
```bash
sudo systemctl stop derbyrace
sudo -E ./debug-run.sh derbyRace.py
```
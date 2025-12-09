# DerbyNet Logging

All logs → `/var/log/derbynet.log`

## Format

```
2025-12-08 14:35:22.123 DERBYPI:INFO [finishtimer.py:234] Lane 1 triggered
```

| Part | Description |
|------|-------------|
| Timestamp | `YYYY-MM-DD HH:MM:SS.mmm` (America/Edmonton) |
| Device:Level | Hostname uppercase, level: DEBUG/INFO/WARNING/ERROR/CRITICAL |
| Location | `[filename:line]` |

## Usage

**Python (server)**
```python
from derbylogger import setup_logger
logger = setup_logger('derbyrace')
logger.info("Heat started")
```

**Python (remote device)**
```python
from nodelogger import NodeLogger
logger = NodeLogger(name='finishtimer').get_logger()
logger.info("Lane triggered")
```

**PHP**
```php
require_once('inc/error-logging.inc');
derby_log_info("Heat started");
derby_log_error("Database failed");
```

## Viewing Logs

```bash
tail -f /var/log/derbynet.log           # Live tail
grep ':ERROR \[' /var/log/derbynet.log  # By level
grep 'FINISH1:' /var/log/derbynet.log   # By device
grep 'derbyRace.py' /var/log/derbynet.log  # By file
```

## Configuration

**Timezone** - edit constant in each logger:
- Python: `DERBY_TIMEZONE = 'America/Edmonton'`
- PHP: `define('DERBY_TIMEZONE', 'America/Edmonton');`
- rsyslog: `sudo timedatectl set-timezone America/Edmonton`

**Debug mode**:
```bash
export DERBY_DEBUG=true        # Python
export DERBY_PHP_DEBUG=true    # PHP
export DERBY_CONSOLE_LOG=true  # Python console output
```

## Architecture

- Server components write directly to log file
- Remote devices (finish/start timer) send via rsyslog UDP 514

## Files

| File | Purpose |
|------|---------|
| `extras/soapbox/infra/server/derbylogger.py` | Python logger (server) |
| `extras/soapbox/infra/finishtimer/files/nodelogger.py` | Python logger (remote) |
| `website/inc/error-logging.inc` | PHP logger |
| `extras/soapbox/infra/server/rsyslog/10-derbynet.conf` | rsyslog config |

## Troubleshooting

```bash
# Check file/permissions
ls -la /var/log/derbynet.log

# Test Python logger
python3 /extras/soapbox/infra/server/derbylogger.py

# Check rsyslog
sudo systemctl status rsyslog
```

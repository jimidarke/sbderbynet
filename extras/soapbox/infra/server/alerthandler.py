"""
DerbyNet Alert Handler - MQTT-based alerting for critical errors
================================================================

Monitors log entries and publishes alerts to MQTT for critical errors.
Integrates with the unified logging framework for real-time alerting.

Version: 1.0.0
Date: 2026-01-14

USAGE:
------
    from alerthandler import AlertHandler

    # Initialize with MQTT client
    alert_handler = AlertHandler(mqtt_client)

    # Check log entry and alert if critical
    alert_handler.check_and_alert({
        'level': 'CRITICAL',
        'code': 'ERR-HW-301',
        'msg': 'Device offline',
        'device': 'FINISH1'
    })

MQTT TOPICS:
------------
    derbynet/alerts         - Critical error alerts
    derbynet/alerts/hw      - Hardware-specific alerts
    derbynet/alerts/net     - Network-specific alerts
    derbynet/alerts/db      - Database-specific alerts

ALERT MESSAGE FORMAT:
--------------------
    {
        "ts": "2025-12-08T14:35:22.123-07:00",
        "alert_id": "uuid",
        "code": "ERR-HW-301",
        "level": "CRITICAL",
        "device": "FINISH2",
        "msg": "Device offline - Lane 2 timer not responding",
        "ctx": {"last_heartbeat": "2025-12-08T14:35:12.000-07:00"}
    }
"""

import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from collections import defaultdict

try:
    from error_codes import get_error_details, is_alert_required
except ImportError:
    # Fallback if error_codes not available
    def get_error_details(code):
        return {'level': 'ERROR', 'msg': 'Unknown error', 'alert': False}

    def is_alert_required(code):
        return code and '-3' in code

try:
    from derbylogger import get_iso8601_timestamp
except ImportError:
    def get_iso8601_timestamp():
        return datetime.now().isoformat()


class AlertHandler:
    """
    Monitors log entries and publishes alerts for critical errors.

    Features:
    - Rate limiting to prevent alert storms
    - Category-based routing to specific MQTT topics
    - Alert deduplication within time windows
    - Callback support for custom alert handling
    """

    # MQTT topic prefix for alerts
    ALERT_TOPIC_BASE = 'derbynet/alerts'

    # Category to subtopic mapping
    CATEGORY_TOPICS = {
        'HW': 'hw',      # Hardware alerts
        'NET': 'net',    # Network alerts
        'DB': 'db',      # Database alerts
        'RACE': 'race',  # Race state alerts
        'SYS': 'sys',    # System alerts
        'AUTH': 'auth',  # Authentication alerts
    }

    # Default rate limit: max alerts per code per time window
    DEFAULT_RATE_LIMIT = 5  # alerts
    DEFAULT_RATE_WINDOW = 60  # seconds

    def __init__(
        self,
        mqtt_client,
        rate_limit: int = DEFAULT_RATE_LIMIT,
        rate_window: int = DEFAULT_RATE_WINDOW,
        on_alert: Optional[Callable[[Dict[str, Any]], None]] = None,
        tenant_slug: Optional[str] = None,
    ):
        """
        Initialize the alert handler.

        Args:
            mqtt_client: MQTT client instance with publish() method
            rate_limit: Maximum alerts per error code per time window
            rate_window: Time window in seconds for rate limiting
            on_alert: Optional callback function for custom alert handling
            tenant_slug: Cloud-twin tenant slug; when provided, alerts publish
                under ``derbynet/t/<slug>/alerts`` so sandboxes can't see each
                other's noise. Pi callers leave this None for legacy
                ``derbynet/alerts``.
        """
        self.mqtt = mqtt_client
        self.rate_limit = rate_limit
        self.rate_window = rate_window
        self.on_alert = on_alert
        # Shadow the class constant per-instance when running multi-tenant.
        if tenant_slug:
            self.ALERT_TOPIC_BASE = f'derbynet/t/{tenant_slug}/alerts'

        # Track alert counts for rate limiting: {code: [(timestamp, count), ...]}
        self._alert_history: Dict[str, list] = defaultdict(list)

        # Track recent alert hashes for deduplication
        self._recent_alerts: Dict[str, float] = {}
        self._dedup_window = 30  # seconds

    def check_and_alert(self, log_entry: Dict[str, Any]) -> bool:
        """
        Evaluate if log entry should trigger an alert.

        Args:
            log_entry: Dictionary with log entry data (level, code, msg, device, etc.)

        Returns:
            bool: True if alert was published, False otherwise
        """
        level = log_entry.get('level', '')
        code = log_entry.get('code', '')

        # Determine if this warrants an alert
        should_alert = False

        # Alert on CRITICAL level
        if level == 'CRITICAL':
            should_alert = True

        # Alert on 3xx error codes (CRITICAL severity)
        if code and is_alert_required(code):
            should_alert = True

        if not should_alert:
            return False

        # Check rate limiting
        if not self._check_rate_limit(code):
            return False

        # Check deduplication
        if self._is_duplicate(log_entry):
            return False

        # Publish the alert
        return self.publish_alert(log_entry)

    def publish_alert(self, log_entry: Dict[str, Any]) -> bool:
        """
        Publish alert to MQTT topic.

        Args:
            log_entry: Dictionary with log entry data

        Returns:
            bool: True if publish succeeded, False otherwise
        """
        # Build alert message
        alert = {
            'ts': log_entry.get('ts') or get_iso8601_timestamp(),
            'alert_id': str(uuid.uuid4()),
            'code': log_entry.get('code', 'UNKNOWN'),
            'level': log_entry.get('level', 'CRITICAL'),
            'device': log_entry.get('device', 'UNKNOWN'),
            'component': log_entry.get('component', ''),
            'msg': log_entry.get('msg', ''),
        }

        # Include context if present
        ctx = log_entry.get('ctx') or log_entry.get('context')
        if ctx:
            alert['ctx'] = ctx

        # Determine topic based on error code category
        topic = self._get_topic(log_entry.get('code', ''))

        try:
            # Publish to MQTT with QoS 1 (at least once delivery)
            payload = json.dumps(alert, separators=(',', ':'))
            result = self.mqtt.publish(topic, payload, qos=1)

            # Also publish to main alerts topic if using subtopic
            if topic != self.ALERT_TOPIC_BASE:
                self.mqtt.publish(self.ALERT_TOPIC_BASE, payload, qos=1)

            # Call custom handler if configured
            if self.on_alert:
                try:
                    self.on_alert(alert)
                except Exception:
                    pass  # Don't let callback errors break alerting

            # Track this alert for deduplication
            self._track_alert(log_entry)

            return result.rc == 0 if hasattr(result, 'rc') else True

        except Exception as e:
            # Log alert failure but don't raise
            print(f"Warning: Failed to publish alert: {e}")
            return False

    def _get_topic(self, error_code: str) -> str:
        """
        Determine MQTT topic based on error code category.

        Args:
            error_code: Error code (e.g., 'ERR-HW-301')

        Returns:
            str: MQTT topic for this alert
        """
        if not error_code or not error_code.startswith('ERR-'):
            return self.ALERT_TOPIC_BASE

        # Extract category from code (ERR-{CATEGORY}-{NUM})
        parts = error_code.split('-')
        if len(parts) >= 2:
            category = parts[1]
            if category in self.CATEGORY_TOPICS:
                return f"{self.ALERT_TOPIC_BASE}/{self.CATEGORY_TOPICS[category]}"

        return self.ALERT_TOPIC_BASE

    def _check_rate_limit(self, code: str) -> bool:
        """
        Check if alert is within rate limits.

        Args:
            code: Error code to check

        Returns:
            bool: True if within limits, False if rate limited
        """
        if not code:
            code = 'UNKNOWN'

        now = time.time()
        cutoff = now - self.rate_window

        # Clean old entries
        self._alert_history[code] = [
            ts for ts in self._alert_history[code]
            if ts > cutoff
        ]

        # Check if under limit
        if len(self._alert_history[code]) >= self.rate_limit:
            return False

        # Record this alert
        self._alert_history[code].append(now)
        return True

    def _is_duplicate(self, log_entry: Dict[str, Any]) -> bool:
        """
        Check if this is a duplicate of a recent alert.

        Args:
            log_entry: Log entry to check

        Returns:
            bool: True if duplicate, False otherwise
        """
        # Create hash of key fields
        alert_hash = f"{log_entry.get('code', '')}:{log_entry.get('device', '')}:{log_entry.get('msg', '')}"

        now = time.time()

        # Clean old entries
        self._recent_alerts = {
            h: ts for h, ts in self._recent_alerts.items()
            if now - ts < self._dedup_window
        }

        # Check if duplicate
        if alert_hash in self._recent_alerts:
            return True

        return False

    def _track_alert(self, log_entry: Dict[str, Any]) -> None:
        """
        Track alert for deduplication.

        Args:
            log_entry: Log entry that was alerted
        """
        alert_hash = f"{log_entry.get('code', '')}:{log_entry.get('device', '')}:{log_entry.get('msg', '')}"
        self._recent_alerts[alert_hash] = time.time()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get alerting statistics.

        Returns:
            dict: Statistics about alert counts and rate limiting
        """
        now = time.time()
        cutoff = now - self.rate_window

        stats = {
            'rate_window_seconds': self.rate_window,
            'rate_limit_per_code': self.rate_limit,
            'codes_in_window': {},
        }

        for code, timestamps in self._alert_history.items():
            recent = [ts for ts in timestamps if ts > cutoff]
            if recent:
                stats['codes_in_window'][code] = len(recent)

        return stats


class AlertLoggingHandler:
    """
    Python logging handler that forwards critical logs to AlertHandler.

    Usage:
        import logging
        from alerthandler import AlertLoggingHandler

        alert_handler = AlertHandler(mqtt_client)
        logging_handler = AlertLoggingHandler(alert_handler)

        logger = logging.getLogger('myapp')
        logger.addHandler(logging_handler)
    """

    def __init__(self, alert_handler: AlertHandler):
        """
        Initialize the logging handler.

        Args:
            alert_handler: AlertHandler instance to forward logs to
        """
        self.alert_handler = alert_handler

    def emit(self, record) -> None:
        """
        Process a log record and forward to alert handler if critical.

        Args:
            record: logging.LogRecord instance
        """
        log_entry = {
            'ts': get_iso8601_timestamp(),
            'level': record.levelname,
            'device': getattr(record, 'device', 'UNKNOWN'),
            'component': record.name.split('.')[-1] if record.name else '',
            'file': record.filename,
            'line': record.lineno,
            'msg': record.getMessage(),
        }

        # Extract error_code and context from extra
        error_code = getattr(record, 'error_code', None)
        if error_code:
            log_entry['code'] = error_code

        context = getattr(record, 'context', None)
        if context:
            log_entry['ctx'] = context

        self.alert_handler.check_and_alert(log_entry)


if __name__ == '__main__':
    # Test the alert handler
    print("=== AlertHandler v1.0.0 Test ===\n")

    # Mock MQTT client for testing
    class MockMQTT:
        def __init__(self):
            self.messages = []

        def publish(self, topic, payload, qos=0):
            self.messages.append((topic, payload, qos))
            print(f"MQTT publish: {topic}")
            print(f"  Payload: {payload[:100]}...")

            class Result:
                rc = 0
            return Result()

    mock_mqtt = MockMQTT()
    handler = AlertHandler(mock_mqtt)

    print("Test 1: INFO level (should NOT alert)")
    result = handler.check_and_alert({
        'level': 'INFO',
        'msg': 'Normal operation',
        'device': 'TEST1'
    })
    print(f"  Alerted: {result}\n")

    print("Test 2: CRITICAL level (should alert)")
    result = handler.check_and_alert({
        'level': 'CRITICAL',
        'code': 'ERR-HW-301',
        'msg': 'Device offline',
        'device': 'FINISH1'
    })
    print(f"  Alerted: {result}\n")

    print("Test 3: ERROR with 3xx code (should alert)")
    result = handler.check_and_alert({
        'level': 'ERROR',
        'code': 'ERR-NET-301',
        'msg': 'MQTT broker disconnected',
        'device': 'SERVER1'
    })
    print(f"  Alerted: {result}\n")

    print("Test 4: ERROR with 2xx code (should NOT alert)")
    result = handler.check_and_alert({
        'level': 'ERROR',
        'code': 'ERR-HW-201',
        'msg': 'Sensor timeout',
        'device': 'FINISH2'
    })
    print(f"  Alerted: {result}\n")

    print("Test 5: Duplicate alert (should NOT alert)")
    result = handler.check_and_alert({
        'level': 'CRITICAL',
        'code': 'ERR-HW-301',
        'msg': 'Device offline',
        'device': 'FINISH1'
    })
    print(f"  Alerted: {result}\n")

    print(f"Total MQTT messages: {len(mock_mqtt.messages)}")
    print("\nAlert stats:", handler.get_stats())
    print("\n=== Test Complete ===")

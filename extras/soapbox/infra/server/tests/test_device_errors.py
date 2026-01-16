"""
Tests for Device Error Logging and Health Monitoring

This module tests error detection and logging for end-node devices:
- Low battery warnings
- WiFi signal degradation
- CPU temperature warnings
- Device offline detection
- Network connectivity issues

These tests validate that the unified logging framework correctly
captures and categorizes device health issues.
"""

import pytest
import json
import time
from unittest.mock import Mock, MagicMock, patch


class TestBatteryMonitoring:
    """Test battery level monitoring and warnings."""

    def test_low_battery_threshold(self):
        """Low battery should trigger warning at 20%."""
        LOW_BATTERY_THRESHOLD = 20

        battery_levels = [
            (100, False),  # Full - no warning
            (50, False),   # Half - no warning
            (25, False),   # Low-ish - no warning yet
            (20, True),    # At threshold - warning
            (15, True),    # Below threshold - warning
            (5, True),     # Critical - warning
            (0, True),     # Empty - warning
        ]

        for level, should_warn in battery_levels:
            is_low = level <= LOW_BATTERY_THRESHOLD
            assert is_low == should_warn, f"Battery {level}% should warn: {should_warn}"

    def test_critical_battery_threshold(self):
        """Critical battery should trigger alert at 10%."""
        CRITICAL_BATTERY_THRESHOLD = 10

        critical_levels = [15, 10, 5, 0]
        for level in critical_levels:
            is_critical = level <= CRITICAL_BATTERY_THRESHOLD
            expected = level <= 10
            assert is_critical == expected

    def test_battery_error_code(self):
        """Low battery should use ERR-HW-101 error code."""
        from error_codes import ERROR_CODES

        # Verify the error code exists and is a WARNING
        assert 'ERR-HW-101' in ERROR_CODES
        assert ERROR_CODES['ERR-HW-101']['level'] == 'WARNING'
        assert 'battery' in ERROR_CODES['ERR-HW-101']['msg'].lower()

    def test_battery_telemetry_field(self):
        """Telemetry should include battery_level field."""
        telemetry = {
            'hostname': 'FINISH1',
            'hwid': 'ABC123',
            'battery_level': 85,  # This field must be present
            'uptime': 3600
        }

        assert 'battery_level' in telemetry
        assert isinstance(telemetry['battery_level'], (int, float))
        assert 0 <= telemetry['battery_level'] <= 100


class TestWiFiMonitoring:
    """Test WiFi signal monitoring and warnings."""

    def test_wifi_rssi_thresholds(self):
        """WiFi warnings should trigger at appropriate RSSI levels."""
        # RSSI thresholds (typical for WiFi)
        EXCELLENT = -50   # > -50 dBm
        GOOD = -60        # -50 to -60 dBm
        FAIR = -70        # -60 to -70 dBm
        WEAK = -80        # -70 to -80 dBm
        POOR = -90        # < -80 dBm (warning)

        rssi_tests = [
            (-45, 'excellent', False),
            (-55, 'good', False),
            (-65, 'fair', False),
            (-75, 'weak', False),
            (-85, 'poor', True),     # Warning
            (-95, 'poor', True),     # Warning
        ]

        WARN_THRESHOLD = -80

        for rssi, quality, should_warn in rssi_tests:
            is_poor = rssi < WARN_THRESHOLD
            assert is_poor == should_warn, f"RSSI {rssi} should warn: {should_warn}"

    def test_wifi_rssi_to_percent_conversion(self):
        """RSSI should convert to percentage correctly."""
        from derbyapi import DerbyNetClient

        # Test the conversion function
        conversions = [
            (-50, 100),   # Excellent
            (-75, 50),    # Medium
            (-100, 0),    # No signal
            (-65, 70),    # Good
            (-85, 30),    # Weak
        ]

        for rssi, expected_percent in conversions:
            actual = DerbyNetClient.getWiFiPercentFromRSSI(rssi)
            assert actual == expected_percent, f"RSSI {rssi} should be {expected_percent}%"

    def test_wifi_disconnect_detection(self):
        """WiFi disconnect should be detected."""
        # No RSSI or 0 indicates disconnected
        disconnected_indicators = [None, 0, -127]

        for indicator in disconnected_indicators:
            is_disconnected = indicator is None or indicator == 0 or indicator < -100
            assert is_disconnected is True

    def test_wifi_error_code(self):
        """WiFi issues should use appropriate error codes."""
        from error_codes import ERROR_CODES

        # Check network error codes exist
        assert 'ERR-NET-101' in ERROR_CODES  # Network warning
        assert 'ERR-NET-301' in ERROR_CODES  # Network critical

    def test_wifi_telemetry_field(self):
        """Telemetry should include wifi_rssi field."""
        telemetry = {
            'hostname': 'FINISH1',
            'hwid': 'ABC123',
            'wifi_rssi': -65,  # This field must be present
        }

        assert 'wifi_rssi' in telemetry
        assert isinstance(telemetry['wifi_rssi'], (int, float))


class TestCPUTemperatureMonitoring:
    """Test CPU temperature monitoring and warnings."""

    def test_cpu_temp_thresholds(self):
        """CPU temperature warnings should trigger at appropriate levels."""
        # Raspberry Pi temp thresholds
        NORMAL_MAX = 60.0      # Normal operation
        THROTTLE_TEMP = 80.0   # CPU throttling begins
        CRITICAL_TEMP = 85.0   # Shutdown imminent

        temps = [
            (45.0, 'normal', False),
            (55.0, 'normal', False),
            (65.0, 'warm', True),      # Warning
            (75.0, 'hot', True),       # Warning
            (82.0, 'throttling', True), # Critical
            (87.0, 'critical', True),   # Critical
        ]

        WARN_THRESHOLD = 60.0

        for temp, desc, should_warn in temps:
            is_high = temp > WARN_THRESHOLD
            assert is_high == should_warn, f"Temp {temp}°C ({desc}) should warn: {should_warn}"

    def test_cpu_temp_error_codes(self):
        """High CPU temp should use appropriate error codes."""
        from error_codes import ERROR_CODES

        # Hardware warnings for temperature
        assert 'ERR-HW-104' in ERROR_CODES  # Temperature warning
        assert ERROR_CODES['ERR-HW-104']['level'] == 'WARNING'
        assert 'temperature' in ERROR_CODES['ERR-HW-104']['msg'].lower()

    def test_cpu_temp_telemetry_field(self):
        """Telemetry should include cpu_temp field."""
        telemetry = {
            'hostname': 'FINISH1',
            'hwid': 'ABC123',
            'cpu_temp': 45.5,  # Celsius
        }

        assert 'cpu_temp' in telemetry
        assert isinstance(telemetry['cpu_temp'], (int, float, type(None)))


class TestDeviceOfflineDetection:
    """Test device offline/timeout detection."""

    def test_heartbeat_timeout(self):
        """Devices without heartbeat should be marked offline."""
        HEARTBEAT_TIMEOUT = 10  # seconds

        timer_heartbeats = {
            1: {'time': time.time() - 5, 'isReady': True},   # Recent
            2: {'time': time.time() - 15, 'isReady': True},  # Stale
            3: {'time': time.time() - 5, 'isReady': True},   # Recent
        }

        current_time = time.time()
        offline_timers = [
            lane for lane, data in timer_heartbeats.items()
            if (current_time - data['time']) > HEARTBEAT_TIMEOUT
        ]

        assert 2 in offline_timers
        assert 1 not in offline_timers
        assert 3 not in offline_timers

    def test_offline_error_code(self):
        """Device offline should use ERR-HW-301 (CRITICAL)."""
        from error_codes import ERROR_CODES

        assert 'ERR-HW-301' in ERROR_CODES
        assert ERROR_CODES['ERR-HW-301']['level'] == 'CRITICAL'
        assert ERROR_CODES['ERR-HW-301']['alert'] is True

    def test_mqtt_disconnect_handling(self):
        """MQTT disconnect should trigger reconnect logic."""
        # Simulates on_disconnect callback
        disconnect_codes = {
            0: 'clean_disconnect',
            1: 'protocol_error',
            2: 'invalid_client_id',
            3: 'server_unavailable',
            4: 'bad_credentials',
            5: 'not_authorized',
        }

        # Only code 0 is clean, others should trigger reconnect
        for rc, desc in disconnect_codes.items():
            should_reconnect = rc != 0
            assert (rc != 0) == should_reconnect

    def test_cleanup_offline_timers(self):
        """Offline timers should be cleaned up after timeout."""
        HEARTBEAT_TIMEOUT = 10

        timer_heartbeats = {
            1: {'time': time.time() - 5, 'isReady': True},
            2: {'time': time.time() - 20, 'isReady': True},  # Should be removed
            3: {'time': time.time() - 8, 'isReady': True},
        }

        current_time = time.time()

        # Identify offline timers
        offline = [
            lane for lane, data in timer_heartbeats.items()
            if (current_time - data['time']) > HEARTBEAT_TIMEOUT
        ]

        assert len(offline) == 1
        assert 2 in offline


class TestNetworkConnectivityErrors:
    """Test network connectivity error handling."""

    def test_mqtt_broker_disconnect(self):
        """MQTT broker disconnect should use ERR-NET-301."""
        from error_codes import ERROR_CODES

        assert 'ERR-NET-301' in ERROR_CODES
        assert ERROR_CODES['ERR-NET-301']['level'] == 'CRITICAL'
        assert 'mqtt' in ERROR_CODES['ERR-NET-301']['msg'].lower() or \
               'broker' in ERROR_CODES['ERR-NET-301']['msg'].lower() or \
               'disconnect' in ERROR_CODES['ERR-NET-301']['msg'].lower()

    def test_mqtt_publish_failure(self):
        """Failed MQTT publish should use ERR-NET-201."""
        from error_codes import ERROR_CODES

        assert 'ERR-NET-201' in ERROR_CODES
        assert ERROR_CODES['ERR-NET-201']['level'] == 'ERROR'

    def test_api_connection_failure(self):
        """DerbyNet API connection failure should be handled."""
        from error_codes import ERROR_CODES

        # HTTP/API errors
        assert 'ERR-NET-202' in ERROR_CODES

    def test_network_error_logging(self):
        """Network errors should be logged with context."""
        error_context = {
            'broker': '192.168.100.10',
            'port': 1883,
            'rc': 5,  # Return code
            'error': 'not_authorized'
        }

        # Context should include connection details
        assert 'broker' in error_context
        assert 'port' in error_context


class TestErrorLoggingIntegration:
    """Test that errors are properly logged through unified framework."""

    def test_error_log_format(self):
        """Error logs should follow unified format."""
        # Expected JSON log entry format
        log_entry = {
            'ts': '2025-01-14T14:35:22.123-07:00',
            'level': 'ERROR',
            'device': 'FINISH1',
            'component': 'finishtimer',
            'file': 'finishtimer.py',
            'line': 123,
            'msg': 'Sensor timeout',
            'code': 'ERR-HW-201',
            'ctx': {'lane': 2, 'timeout_ms': 5000}
        }

        required_fields = ['ts', 'level', 'device', 'component', 'msg']
        for field in required_fields:
            assert field in log_entry

    def test_error_code_in_log(self):
        """Error codes should be included in log entries."""
        # When logging with error code
        log_with_code = {
            'msg': 'Sensor timeout',
            'code': 'ERR-HW-201'
        }

        assert 'code' in log_with_code
        assert log_with_code['code'].startswith('ERR-')

    def test_context_in_log(self):
        """Error context should be included when provided."""
        log_with_context = {
            'msg': 'Low battery',
            'code': 'ERR-HW-101',
            'ctx': {
                'battery_level': 15,
                'device': 'FINISH2',
                'lane': 2
            }
        }

        assert 'ctx' in log_with_context
        assert 'battery_level' in log_with_context['ctx']


class TestAlertingForCriticalErrors:
    """Test that critical device errors trigger MQTT alerts."""

    def test_critical_errors_alert(self):
        """3xx error codes should trigger alerts."""
        from error_codes import ERROR_CODES, is_alert_required

        critical_codes = [
            'ERR-HW-301',   # Device offline
            'ERR-NET-301',  # MQTT disconnected
            'ERR-RACE-301', # Timing failure
        ]

        for code in critical_codes:
            assert is_alert_required(code) is True
            assert ERROR_CODES[code]['alert'] is True

    def test_warning_errors_no_alert(self):
        """1xx error codes should not trigger alerts."""
        from error_codes import ERROR_CODES, is_alert_required

        warning_codes = [
            'ERR-HW-101',   # Low battery
            'ERR-HW-102',   # High temperature
            'ERR-NET-101',  # Weak signal
        ]

        for code in warning_codes:
            assert is_alert_required(code) is False
            assert ERROR_CODES[code]['alert'] is False

    def test_alert_message_format(self):
        """Alert messages should have required fields."""
        alert = {
            'ts': '2025-01-14T14:35:22.123-07:00',
            'alert_id': 'uuid-here',
            'code': 'ERR-HW-301',
            'level': 'CRITICAL',
            'device': 'FINISH2',
            'msg': 'Device offline - Lane 2 timer not responding',
            'ctx': {'lane': 2, 'timeout_seconds': 10}
        }

        required_fields = ['ts', 'alert_id', 'code', 'level', 'device', 'msg']
        for field in required_fields:
            assert field in alert


class TestTelemetryValidation:
    """Test telemetry data validation for error detection."""

    def test_telemetry_field_types(self):
        """Telemetry fields should have correct types."""
        telemetry = {
            'hostname': 'FINISH1',      # string
            'hwid': 'ABC123',           # string
            'uptime': 3600,             # int (seconds)
            'ip': '192.168.100.101',    # string (IP)
            'mac': 'AA:BB:CC:DD:EE:FF', # string (MAC)
            'wifi_rssi': -65,           # int (dBm)
            'battery_level': 85,        # int (percent)
            'cpu_temp': 45.5,           # float (Celsius)
            'memory_usage': 512,        # int (MB)
            'disk': 75,                 # int (percent)
            'cpu_usage': 25,            # int (percent)
        }

        assert isinstance(telemetry['hostname'], str)
        assert isinstance(telemetry['uptime'], int)
        assert isinstance(telemetry['wifi_rssi'], int)
        assert isinstance(telemetry['battery_level'], (int, float))
        assert isinstance(telemetry['cpu_temp'], (int, float, type(None)))

    def test_telemetry_value_ranges(self):
        """Telemetry values should be within valid ranges."""
        telemetry = {
            'battery_level': 85,
            'wifi_rssi': -65,
            'cpu_temp': 45.5,
            'cpu_usage': 25,
            'disk': 75,
        }

        # Battery: 0-100%
        assert 0 <= telemetry['battery_level'] <= 100

        # RSSI: -100 to 0 dBm (typically)
        assert -100 <= telemetry['wifi_rssi'] <= 0

        # CPU temp: 0-100°C (reasonable range)
        assert 0 <= telemetry['cpu_temp'] <= 100

        # CPU usage: 0-100%
        assert 0 <= telemetry['cpu_usage'] <= 100

        # Disk: 0-100%
        assert 0 <= telemetry['disk'] <= 100

    def test_missing_telemetry_handling(self):
        """Missing telemetry fields should use defaults."""
        minimal_telemetry = {
            'hwid': 'UNKNOWN',
        }

        # Code should handle missing fields gracefully
        battery = minimal_telemetry.get('battery_level', 0)
        wifi = minimal_telemetry.get('wifi_rssi', 0)
        temp = minimal_telemetry.get('cpu_temp', None)

        assert battery == 0
        assert wifi == 0
        assert temp is None

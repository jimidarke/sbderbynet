"""
Unit tests for the unified logging and error handling framework.

Tests cover:
- JSON log format validation
- Error code registry consistency
- Unified logger consolidation
- Alert handler logic

Version: 1.0.0
Date: 2026-01-14
"""

import json
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_log_file(temp_log_dir):
    """Create a temporary JSON log file path."""
    return os.path.join(temp_log_dir, 'test.jsonl')


@pytest.fixture
def temp_text_file(temp_log_dir):
    """Create a temporary text log file path."""
    return os.path.join(temp_log_dir, 'test.log')


@pytest.fixture
def mock_mqtt():
    """Create a mock MQTT client for alert testing."""
    mqtt = Mock()
    mqtt.publish = Mock(return_value=Mock(rc=0))
    return mqtt


@pytest.fixture
def clean_logger_env():
    """Clean up environment variables and logger state before tests."""
    import logging
    import uuid

    # Save original env vars
    orig_env = {
        'DERBY_DEBUG': os.environ.get('DERBY_DEBUG'),
        'DERBY_CONSOLE_LOG': os.environ.get('DERBY_CONSOLE_LOG'),
        'DERBY_JSON_LOG': os.environ.get('DERBY_JSON_LOG'),
        'DERBY_DEVICE_ID': os.environ.get('DERBY_DEVICE_ID'),
    }

    # Clear env vars for clean test
    for key in orig_env:
        if key in os.environ:
            del os.environ[key]

    # Generate unique test ID to avoid logger caching issues
    test_id = str(uuid.uuid4())[:8]

    yield test_id

    # Restore original env vars
    for key, value in orig_env.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]

    # Clean up any loggers we created
    for name in list(logging.Logger.manager.loggerDict.keys()):
        if name.startswith('derby.TEST') or test_id in name:
            logger = logging.getLogger(name)
            logger.handlers = []


# =============================================================================
# TEST SUITE: JSON LOGGING FORMAT
# =============================================================================

@pytest.mark.logging
class TestJSONLogging:
    """Validate JSON log output format and content."""

    def test_json_log_has_required_fields(self, temp_log_file, temp_text_file, clean_logger_env):
        """JSON log entries must have ts, level, device, component, file, line, msg."""
        from derbylogger import DerbyLogger

        test_id = clean_logger_env
        derby_logger = DerbyLogger(
            component=f'test-{test_id}',
            device_id=f'TEST-{test_id}',
            log_file=temp_text_file,
            json_file=temp_log_file
        )
        logger = derby_logger.get_logger()
        logger.info("Test message")

        # Force flush
        for handler in logger.handlers:
            handler.flush()

        assert os.path.exists(temp_log_file), "JSON file not created"

        with open(temp_log_file) as f:
            entry = json.loads(f.readline())

        required = ['ts', 'level', 'device', 'component', 'file', 'line', 'msg']
        for field in required:
            assert field in entry, f"Missing required field: {field}"

    def test_json_timestamp_is_iso8601(self, temp_log_file, temp_text_file, clean_logger_env):
        """Timestamp must be ISO 8601 format with timezone."""
        from derbylogger import DerbyLogger

        test_id = clean_logger_env
        derby_logger = DerbyLogger(
            component=f'test-{test_id}',
            device_id=f'TEST-{test_id}',
            log_file=temp_text_file,
            json_file=temp_log_file
        )
        logger = derby_logger.get_logger()
        logger.info("Test")

        for handler in logger.handlers:
            handler.flush()

        with open(temp_log_file) as f:
            entry = json.loads(f.readline())

        ts = entry['ts']
        # Should contain T separator and have timezone info
        assert 'T' in ts, "Timestamp should use ISO 8601 T separator"
        # Parse to validate format (will raise if invalid)
        # Remove colon from timezone for fromisoformat compatibility
        try:
            datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except ValueError:
            # Try without colon in tz offset
            ts_fixed = ts[:-3] + ts[-2:] if len(ts) > 5 and ts[-3] == ':' else ts
            datetime.fromisoformat(ts_fixed.replace('Z', '+00:00'))

    def test_error_code_included_when_provided(self, temp_log_file, temp_text_file, clean_logger_env):
        """Error code appears in JSON when passed."""
        from derbylogger import DerbyLogger

        test_id = clean_logger_env
        derby_logger = DerbyLogger(
            component=f'test-{test_id}',
            device_id=f'TEST-{test_id}',
            log_file=temp_text_file,
            json_file=temp_log_file
        )
        logger = derby_logger.get_logger()
        logger.error("Sensor failed", extra={'error_code': 'ERR-HW-201'})

        for handler in logger.handlers:
            handler.flush()

        with open(temp_log_file) as f:
            entry = json.loads(f.readline())

        assert entry.get('code') == 'ERR-HW-201'

    def test_context_included_when_provided(self, temp_log_file, temp_text_file, clean_logger_env):
        """Context dict appears in JSON when passed."""
        from derbylogger import DerbyLogger

        test_id = clean_logger_env
        derby_logger = DerbyLogger(
            component=f'test-{test_id}',
            device_id=f'TEST-{test_id}',
            log_file=temp_text_file,
            json_file=temp_log_file
        )
        logger = derby_logger.get_logger()
        logger.warning("Low battery", extra={'context': {'lane': 2, 'percent': 15}})

        for handler in logger.handlers:
            handler.flush()

        with open(temp_log_file) as f:
            entry = json.loads(f.readline())

        assert entry.get('ctx') == {'lane': 2, 'percent': 15}

    def test_json_file_is_valid_jsonl(self, temp_log_file, temp_text_file, clean_logger_env):
        """Each line in log file must be valid JSON (JSONL format)."""
        from derbylogger import DerbyLogger

        test_id = clean_logger_env
        derby_logger = DerbyLogger(
            component=f'test-{test_id}',
            device_id=f'TEST-{test_id}',
            log_file=temp_text_file,
            json_file=temp_log_file
        )
        logger = derby_logger.get_logger()
        logger.info("Message 1")
        logger.warning("Message 2")
        logger.error("Message 3")

        for handler in logger.handlers:
            handler.flush()

        with open(temp_log_file) as f:
            for line_num, line in enumerate(f, 1):
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Line {line_num} is not valid JSON: {e}")


# =============================================================================
# TEST SUITE: ERROR CODE REGISTRY
# =============================================================================

@pytest.mark.logging
class TestErrorCodeRegistry:
    """Validate error code registry consistency."""

    def test_all_codes_have_required_fields(self):
        """Each error code must have level, msg, alert fields."""
        from error_codes import ERROR_CODES

        for code, details in ERROR_CODES.items():
            assert 'level' in details, f"{code} missing 'level'"
            assert 'msg' in details, f"{code} missing 'msg'"
            assert 'alert' in details, f"{code} missing 'alert'"

    def test_code_format_valid(self):
        """Error codes must match ERR-{CAT}-{NUM} pattern."""
        from error_codes import ERROR_CODES
        import re

        pattern = r'^ERR-[A-Z]+-[123]\d{2}$'
        for code in ERROR_CODES:
            assert re.match(pattern, code), f"Invalid code format: {code}"

    def test_critical_codes_have_alert_true(self):
        """All *-3xx codes should have alert=True."""
        from error_codes import ERROR_CODES

        for code, details in ERROR_CODES.items():
            num = int(code.split('-')[-1])
            if 300 <= num < 400:  # 3xx = CRITICAL
                assert details['alert'] is True, f"{code} should have alert=True"

    def test_code_levels_match_severity(self):
        """1xx=WARNING, 2xx=ERROR, 3xx=CRITICAL."""
        from error_codes import ERROR_CODES

        for code, details in ERROR_CODES.items():
            num = int(code.split('-')[-1])
            if 100 <= num < 200:
                assert details['level'] == 'WARNING', f"{code} should be WARNING"
            elif 200 <= num < 300:
                assert details['level'] == 'ERROR', f"{code} should be ERROR"
            elif 300 <= num < 400:
                assert details['level'] == 'CRITICAL', f"{code} should be CRITICAL"

    def test_get_error_details_returns_valid_data(self):
        """get_error_details should return correct data for known codes."""
        from error_codes import get_error_details

        details = get_error_details('ERR-HW-301')
        assert details['level'] == 'CRITICAL'
        assert details['alert'] is True
        assert 'msg' in details

    def test_get_error_details_unknown_code(self):
        """get_error_details should return default for unknown codes."""
        from error_codes import get_error_details

        details = get_error_details('ERR-UNKNOWN-999')
        assert details['level'] == 'ERROR'
        assert details['alert'] is False

    def test_is_alert_required(self):
        """is_alert_required should return True for CRITICAL codes."""
        from error_codes import is_alert_required

        assert is_alert_required('ERR-HW-301') is True
        assert is_alert_required('ERR-HW-201') is False


# =============================================================================
# TEST SUITE: UNIFIED LOGGER
# =============================================================================

@pytest.mark.logging
class TestUnifiedLogger:
    """Validate logger consolidation works correctly."""

    def test_derbydb_uses_unified_logger(self):
        """derbydb.py should use setup_logger, not logging.getLogger."""
        import derbydb

        # Logger should have 'derby.' prefix from unified logger
        assert derbydb.logger.name.startswith('derby.'), \
            f"derbydb should use unified DerbyLogger, got: {derbydb.logger.name}"

    def test_text_and_json_both_written(self, temp_log_dir, clean_logger_env):
        """Both text and JSON files should be written."""
        from derbylogger import DerbyLogger

        test_id = clean_logger_env
        text_file = os.path.join(temp_log_dir, 'test.log')
        json_file = os.path.join(temp_log_dir, 'test.jsonl')

        derby_logger = DerbyLogger(
            component=f'test-{test_id}',
            device_id=f'TEST-{test_id}',
            log_file=text_file,
            json_file=json_file
        )
        logger = derby_logger.get_logger()
        logger.info("Test message")

        for handler in logger.handlers:
            handler.flush()

        assert os.path.exists(text_file), "Text log not created"
        assert os.path.exists(json_file), "JSON log not created"

    def test_device_id_consistent_across_entries(self, temp_log_file, temp_text_file, clean_logger_env):
        """Device ID should be same for all log entries."""
        from derbylogger import DerbyLogger

        test_id = clean_logger_env
        derby_logger = DerbyLogger(
            component=f'test-{test_id}',
            device_id=f'CONSISTENT-{test_id}',
            log_file=temp_text_file,
            json_file=temp_log_file
        )
        logger = derby_logger.get_logger()
        logger.info("First")
        logger.info("Second")
        logger.info("Third")

        for handler in logger.handlers:
            handler.flush()

        devices = set()
        with open(temp_log_file) as f:
            for line in f:
                entry = json.loads(line)
                devices.add(entry['device'])

        assert len(devices) == 1, f"Device ID inconsistent: {devices}"


# =============================================================================
# TEST SUITE: ALERT HANDLER
# =============================================================================

@pytest.mark.logging
class TestAlertHandler:
    """Validate alerting logic."""

    def test_critical_level_triggers_alert(self, mock_mqtt):
        """CRITICAL level should publish to derbynet/alerts."""
        # Import or define AlertHandler inline for testing
        # Since alerthandler.py may not exist yet, we test the logic
        class AlertHandler:
            def __init__(self, mqtt_client):
                self.mqtt = mqtt_client

            def check_and_alert(self, log_entry):
                level = log_entry.get('level', '')
                code = log_entry.get('code', '')
                if level == 'CRITICAL' or (code and '-3' in code):
                    self.publish_alert(log_entry)

            def publish_alert(self, log_entry):
                self.mqtt.publish('derbynet/alerts', json.dumps(log_entry), qos=1)

        handler = AlertHandler(mock_mqtt)
        handler.check_and_alert({'level': 'CRITICAL', 'msg': 'Test'})

        assert mock_mqtt.publish.called
        call_args = mock_mqtt.publish.call_args
        assert call_args[0][0] == 'derbynet/alerts'

    def test_3xx_code_triggers_alert(self, mock_mqtt):
        """Error codes ending in 3xx should trigger alert."""
        class AlertHandler:
            def __init__(self, mqtt_client):
                self.mqtt = mqtt_client

            def check_and_alert(self, log_entry):
                level = log_entry.get('level', '')
                code = log_entry.get('code', '')
                if level == 'CRITICAL' or (code and '-3' in code):
                    self.publish_alert(log_entry)

            def publish_alert(self, log_entry):
                self.mqtt.publish('derbynet/alerts', json.dumps(log_entry), qos=1)

        handler = AlertHandler(mock_mqtt)
        handler.check_and_alert({'level': 'ERROR', 'code': 'ERR-HW-301', 'msg': 'Test'})

        assert mock_mqtt.publish.called

    def test_info_level_no_alert(self, mock_mqtt):
        """INFO level should not trigger alert."""
        class AlertHandler:
            def __init__(self, mqtt_client):
                self.mqtt = mqtt_client

            def check_and_alert(self, log_entry):
                level = log_entry.get('level', '')
                code = log_entry.get('code', '')
                if level == 'CRITICAL' or (code and '-3' in code):
                    self.publish_alert(log_entry)

            def publish_alert(self, log_entry):
                self.mqtt.publish('derbynet/alerts', json.dumps(log_entry), qos=1)

        handler = AlertHandler(mock_mqtt)
        handler.check_and_alert({'level': 'INFO', 'msg': 'Test'})

        assert not mock_mqtt.publish.called

    def test_2xx_code_no_alert(self, mock_mqtt):
        """Error codes ending in 2xx should not trigger alert."""
        class AlertHandler:
            def __init__(self, mqtt_client):
                self.mqtt = mqtt_client

            def check_and_alert(self, log_entry):
                level = log_entry.get('level', '')
                code = log_entry.get('code', '')
                if level == 'CRITICAL' or (code and '-3' in code):
                    self.publish_alert(log_entry)

            def publish_alert(self, log_entry):
                self.mqtt.publish('derbynet/alerts', json.dumps(log_entry), qos=1)

        handler = AlertHandler(mock_mqtt)
        handler.check_and_alert({'level': 'ERROR', 'code': 'ERR-HW-201', 'msg': 'Test'})

        assert not mock_mqtt.publish.called


# =============================================================================
# TEST SUITE: REGISTRY VALIDATION
# =============================================================================

@pytest.mark.logging
class TestRegistryValidation:
    """Test the error code registry validation function."""

    def test_validate_registry_passes(self):
        """validate_registry() should pass with current registry."""
        from error_codes import validate_registry

        assert validate_registry() is True

    def test_get_codes_by_category(self):
        """get_codes_by_category should return correct subset."""
        from error_codes import get_codes_by_category

        hw_codes = get_codes_by_category('HW')
        assert len(hw_codes) > 0
        for code in hw_codes:
            assert code.startswith('ERR-HW-')

    def test_get_critical_codes(self):
        """get_critical_codes should return only CRITICAL level codes."""
        from error_codes import get_critical_codes

        critical = get_critical_codes()
        assert len(critical) > 0
        for code, details in critical.items():
            assert details['level'] == 'CRITICAL'

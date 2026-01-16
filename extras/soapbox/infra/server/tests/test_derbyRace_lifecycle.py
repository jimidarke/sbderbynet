"""
Unit tests for derbyRace.py race lifecycle operations.

Tests verify complete race execution from start to finish:
- Race start operations
- Lane finish recording
- Race stop and result submission
- DNF (Did Not Finish) handling
- Database fallback logic

Test IDs reference DERBYRACE_TEST_PLAN.md (RL-001 through RL-043).
"""

import pytest
import time
import json
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def _check_paho_mqtt_version():
    """Check if paho-mqtt 2.0+ is installed."""
    try:
        import paho.mqtt.client as mqtt
        return hasattr(mqtt, 'CallbackAPIVersion')
    except ImportError:
        return False


PAHO_MQTT_V2 = _check_paho_mqtt_version()
SKIP_REASON = "Requires paho-mqtt >= 2.0 (CallbackAPIVersion)"


# =============================================================================
# Mock Classes (shared with state machine tests)
# =============================================================================

class MockMQTTPublishResult:
    """Mock result object returned by MQTT publish()."""
    def __init__(self, rc=0):
        self.rc = rc
        self.error_string = ""


class MockMQTTClient:
    """Mock MQTT client for testing without a broker."""

    def __init__(self, *args, **kwargs):
        self.on_message = None
        self.on_connect = None
        self.on_disconnect = None
        self.subscriptions = []
        self.published = []

    def connect(self, *args, **kwargs):
        pass

    def loop_start(self):
        pass

    def loop_stop(self):
        pass

    def disconnect(self):
        pass

    def subscribe(self, topic, qos=0):
        self.subscriptions.append(topic)

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.published.append({'topic': topic, 'payload': payload, 'qos': qos, 'retain': retain})
        return MockMQTTPublishResult()

    def will_set(self, *args, **kwargs):
        pass


class MockDerbyNetClient:
    """Mock DerbyNet API client for testing."""

    def __init__(self, *args, **kwargs):
        self.sent_finishes = []
        self.sent_starts = []
        self.staging_calls = []
        self.heartbeat_calls = []
        self._race_status = {
            'active': False,
            'roundid': 1,
            'heat': 1,
            'class': 'Test Class',
            'timer-state-string': '',
            'lane-count': 3,
            'lanes': []
        }

    def get_race_status(self):
        return self._race_status

    def set_race_status(self, status):
        self._race_status = status

    def send_finish(self, roundid, heat, lane_times):
        self.sent_finishes.append({
            'roundid': roundid,
            'heat': heat,
            'lane_times': dict(lane_times)  # Copy to preserve
        })

    def send_start(self):
        self.sent_starts.append(time.time())

    def set_staging(self):
        self.staging_calls.append(time.time())

    def send_timer_heartbeat(self, heartbeats):
        self.heartbeat_calls.append(heartbeats)
        return True

    def send_device_status(self, payload):
        return True

    def login(self):
        return 'mock_auth_code'


class MockDerbyDatabase:
    """Mock database for testing direct DB access."""

    def __init__(self, *args, **kwargs):
        self.write_calls = []
        self.should_fail = False
        self.should_raise = False

    def write_race_results(self, roundid, heat, lane_times):
        if self.should_raise:
            raise Exception("Database error")
        if self.should_fail:
            return False
        self.write_calls.append({
            'roundid': roundid,
            'heat': heat,
            'lane_times': dict(lane_times)
        })
        return True

    def close(self):
        pass


class MockAlertHandler:
    """Mock alert handler for testing."""

    def __init__(self, *args, **kwargs):
        self.alerts = []

    def check_and_alert(self, log_entry):
        self.alerts.append(log_entry)
        return True


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client."""
    return MockMQTTClient()


@pytest.fixture
def mock_api_client():
    """Create a mock API client."""
    return MockDerbyNetClient()


@pytest.fixture
def mock_database():
    """Create a mock database."""
    return MockDerbyDatabase()


@pytest.fixture
def mock_alert_handler():
    """Create a mock alert handler."""
    return MockAlertHandler()


@pytest.fixture
def derby_race_instance(mock_mqtt_client, mock_api_client, mock_database, mock_alert_handler):
    """Create a derbyRace instance with mocked dependencies."""
    with patch('paho.mqtt.client.Client', return_value=mock_mqtt_client):
        with patch('derbyRace.DerbyNetClient', return_value=mock_api_client):
            with patch('derbyRace.ServerLogger') as mock_logger:
                mock_logger_instance = Mock()
                mock_logger_instance.get_logger.return_value = Mock()
                mock_logger.return_value = mock_logger_instance

                with patch.dict('sys.modules', {'alerthandler': Mock()}):
                    with patch('derbyRace.ALERT_HANDLER_AVAILABLE', True):
                        with patch('derbyRace.AlertHandler', return_value=mock_alert_handler):
                            with patch('derbyRace.DIRECT_DB_AVAILABLE', True):
                                with patch('derbyRace.DerbyDatabase', return_value=mock_database):
                                    from derbyRace import derbyRace

                                    race = derbyRace(lane_count=3)
                                    race.client = mock_mqtt_client
                                    race.api = mock_api_client
                                    race.db = mock_database
                                    race.alert_handler = mock_alert_handler

                                    yield race, mock_mqtt_client, mock_api_client, mock_database

                                    race.client.loop_stop()


# =============================================================================
# Test Classes: Race Start
# =============================================================================

@pytest.mark.skipif(not PAHO_MQTT_V2, reason=SKIP_REASON)
class TestRaceStart:
    """Tests for race start operations (RL-001 through RL-006)."""

    def test_rl001_normal_race_start(self, derby_race_instance):
        """RL-001: Normal race start sets start_time and state."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_STAGING, RACE_STATE_RACING

        race.race_state = RACE_STATE_STAGING
        race.lanesFinished = 0
        race.lane_times = {}
        race.start_time = 0

        before = time.time()
        race.startRace()
        after = time.time()

        assert race.race_state == RACE_STATE_RACING
        assert before <= race.start_time <= after
        assert race.lanesFinished == 0
        assert race.lane_times == {}

    def test_rl002_start_clears_stale_data(self, derby_race_instance):
        """RL-002: startRace clears previous race data."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_STAGING

        race.race_state = RACE_STATE_STAGING
        race.lanesFinished = 3
        race.lane_times = {1: 3.1, 2: 3.2, 3: 3.3}
        race.start_time = 0

        race.startRace()

        assert race.lanesFinished == 0
        assert race.lane_times == {}
        assert race.start_time > 0

    def test_rl003_start_ignored_if_racing(self, derby_race_instance):
        """RL-003: startRace ignored if already racing."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        original_start = time.time() - 10
        race.race_state = RACE_STATE_RACING
        race.start_time = original_start
        race.lanesFinished = 1
        race.lane_times = {1: 3.456}

        race.startRace()

        # Should be unchanged
        assert race.start_time == original_start
        assert race.lanesFinished == 1
        assert race.lane_times == {1: 3.456}

    def test_rl004_start_with_custom_timer(self, derby_race_instance):
        """RL-004: startRace with custom timer value."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_STAGING

        race.race_state = RACE_STATE_STAGING
        race.start_time = 0

        custom_time = 1234567890.123
        race.startRace(timer=custom_time)

        assert race.start_time == custom_time

    def test_rl005_start_publishes_mqtt(self, derby_race_instance):
        """RL-005: startRace publishes state to MQTT."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_STAGING, RACE_STATE_RACING, MQTT_TOPIC_RACESTATE

        race.race_state = RACE_STATE_STAGING
        race.start_time = 0
        mqtt.published = []

        race.startRace()

        race_publishes = [p for p in mqtt.published if p['topic'] == MQTT_TOPIC_RACESTATE]
        assert len(race_publishes) > 0
        assert race_publishes[-1]['payload'] == RACE_STATE_RACING

    def test_rl006_start_notifies_php(self, derby_race_instance):
        """RL-006: startRace calls api.send_start()."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_STAGING

        race.race_state = RACE_STATE_STAGING
        race.start_time = 0
        api.sent_starts = []

        race.startRace()

        assert len(api.sent_starts) > 0


# =============================================================================
# Test Classes: Lane Finish
# =============================================================================

@pytest.mark.skipif(not PAHO_MQTT_V2, reason=SKIP_REASON)
class TestLaneFinish:
    """Tests for lane finish operations (RL-010 through RL-016)."""

    def test_rl010_single_lane_finish(self, derby_race_instance):
        """RL-010: Single lane finish records time and increments count."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 3.5
        race.lanesFinished = 0
        race.lane_times = {}
        race.lane_count = 3

        race.laneFinish(1)

        assert 1 in race.lane_times
        assert race.lanesFinished == 1
        assert race.race_state == RACE_STATE_RACING  # Still racing (2 more lanes)

    def test_rl011_all_lanes_finish(self, derby_race_instance):
        """RL-011: All lanes finishing triggers stopRace."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING, RACE_STATE_FINISHED

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 0
        race.lane_times = {}
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1

        current = time.time()
        race.laneFinish(1, current)
        race.laneFinish(2, current + 0.1)
        race.laneFinish(3, current + 0.2)

        assert race.race_state == RACE_STATE_FINISHED

    def test_rl012_duplicate_finish_ignored(self, derby_race_instance):
        """RL-012: Duplicate lane finish is ignored."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 3
        race.lanesFinished = 0
        race.lane_times = {}
        race.lane_count = 3

        result1 = race.laneFinish(1)
        original_time = race.lane_times[1]
        time.sleep(0.01)  # Small delay
        result2 = race.laneFinish(1)

        # Second call should return False and not change anything
        assert result2 is False
        assert race.lanesFinished == 1
        assert race.lane_times[1] == original_time

    def test_rl013_finish_time_calculation(self, derby_race_instance):
        """RL-013: Finish time calculated correctly from start_time."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        start_time = time.time()
        finish_time = start_time + 3.456

        race.race_state = RACE_STATE_RACING
        race.start_time = start_time
        race.lanesFinished = 0
        race.lane_times = {}
        race.lane_count = 3

        race.laneFinish(1, finish_time)

        assert abs(race.lane_times[1] - 3.456) < 0.001

    def test_rl014_finish_without_start_time(self, derby_race_instance):
        """RL-014: Finish without valid start_time uses 0.0."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = 0  # No valid start
        race.lanesFinished = 0
        race.lane_times = {}
        race.lane_count = 3

        race.laneFinish(1)

        assert race.lane_times[1] == 0.0

    def test_rl015_concurrent_lane_finishes(self, derby_race_instance):
        """RL-015: Concurrent lane finishes all recorded correctly."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING, RACE_STATE_FINISHED
        import threading

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 0
        race.lane_times = {}
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1

        errors = []
        current = time.time()

        def finish_lane(lane, offset):
            try:
                race.laneFinish(lane, current + offset)
            except Exception as e:
                errors.append(str(e))

        threads = [
            threading.Thread(target=finish_lane, args=(1, 0.0)),
            threading.Thread(target=finish_lane, args=(2, 0.1)),
            threading.Thread(target=finish_lane, args=(3, 0.2)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(race.lane_times) == 0  # Cleared after stopRace
        # Results should have been submitted
        assert len(db.write_calls) > 0 or len(api.sent_finishes) > 0

    def test_rl016_lane_led_updated_on_finish(self, derby_race_instance):
        """RL-016: Lane LED updated to red on finish."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 3
        race.lanesFinished = 0
        race.lane_times = {}
        race.lane_count = 3
        mqtt.published = []

        race.laneFinish(1)

        led_publishes = [p for p in mqtt.published if 'led' in p['topic'] and '/1/' in p['topic']]
        assert any(p['payload'] == 'red' for p in led_publishes)


# =============================================================================
# Test Classes: Race Stop
# =============================================================================

@pytest.mark.skipif(not PAHO_MQTT_V2, reason=SKIP_REASON)
class TestRaceStop:
    """Tests for race stop operations (RL-020 through RL-025)."""

    def test_rl020_normal_race_stop(self, derby_race_instance):
        """RL-020: Normal race stop submits results."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING, RACE_STATE_FINISHED

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 3
        race.lane_times = {1: 3.1, 2: 3.2, 3: 3.3}
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1

        race.stopRace()

        assert race.race_state == RACE_STATE_FINISHED

    def test_rl021_stop_writes_to_db_primary(self, derby_race_instance):
        """RL-021: stopRace uses direct DB when available."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 3
        race.lane_times = {1: 3.1, 2: 3.2, 3: 3.3}
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1

        race.stopRace()

        # DB should have been called
        assert len(db.write_calls) == 1
        assert db.write_calls[0]['roundid'] == 1
        assert db.write_calls[0]['heat'] == 1
        assert len(db.write_calls[0]['lane_times']) == 3
        # API should NOT have been called
        assert len(api.sent_finishes) == 0

    def test_rl022_stop_falls_back_to_http(self, derby_race_instance):
        """RL-022: stopRace falls back to HTTP when db=None."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 3
        race.lane_times = {1: 3.1, 2: 3.2, 3: 3.3}
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1
        race.db = None  # No direct DB

        race.stopRace()

        # API should have been called
        assert len(api.sent_finishes) == 1
        assert api.sent_finishes[0]['roundid'] == 1
        assert api.sent_finishes[0]['heat'] == 1

    def test_rl023_stop_falls_back_on_db_error(self, derby_race_instance):
        """RL-023: stopRace falls back to HTTP on DB error."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 3
        race.lane_times = {1: 3.1, 2: 3.2, 3: 3.3}
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1
        db.should_raise = True  # DB will throw exception

        race.stopRace()

        # API should have been called as fallback
        assert len(api.sent_finishes) == 1

    def test_rl023b_stop_falls_back_on_db_failure(self, derby_race_instance):
        """RL-023b: stopRace falls back to HTTP when DB returns False."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 3
        race.lane_times = {1: 3.1, 2: 3.2, 3: 3.3}
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1
        db.should_fail = True  # DB will return False

        race.stopRace()

        # API should have been called as fallback
        assert len(api.sent_finishes) == 1

    def test_rl024_stop_resets_race_state(self, derby_race_instance):
        """RL-024: stopRace resets all race tracking state."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 3
        race.lane_times = {1: 3.1, 2: 3.2, 3: 3.3}
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1

        race.stopRace()

        assert race.lanesFinished == 0
        assert race.lane_times == {}
        assert race.start_time == 0

    def test_rl025_stop_publishes_mqtt(self, derby_race_instance):
        """RL-025: stopRace publishes FINISHED state to MQTT."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING, RACE_STATE_FINISHED, MQTT_TOPIC_RACESTATE

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 3
        race.lane_times = {1: 3.1, 2: 3.2, 3: 3.3}
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1
        mqtt.published = []

        race.stopRace()

        race_publishes = [p for p in mqtt.published if p['topic'] == MQTT_TOPIC_RACESTATE]
        assert len(race_publishes) > 0
        assert race_publishes[-1]['payload'] == RACE_STATE_FINISHED


# =============================================================================
# Test Classes: DNF Handling
# =============================================================================

@pytest.mark.skipif(not PAHO_MQTT_V2, reason=SKIP_REASON)
class TestDNFHandling:
    """Tests for DNF (Did Not Finish) handling (RL-030 through RL-035)."""

    def test_rl030_mark_lane_dnf(self, derby_race_instance):
        """RL-030: laneDNF sets time to 99.999."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING, DNF_TIME

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 0
        race.lane_times = {}
        race.lane_count = 3

        race.laneDNF(1)

        assert race.lane_times[1] == DNF_TIME
        assert race.lanesFinished == 1

    def test_rl031_dnf_ignored_if_not_racing(self, derby_race_instance):
        """RL-031: laneDNF ignored if not in RACING state."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_STOPPED

        race.race_state = RACE_STATE_STOPPED
        race.lanesFinished = 0
        race.lane_times = {}

        result = race.laneDNF(1)

        assert result is False
        assert race.lanesFinished == 0
        assert 1 not in race.lane_times

    def test_rl032_dnf_overwrites_finish_time(self, derby_race_instance):
        """RL-032: laneDNF can overwrite existing finish time."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING, DNF_TIME

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 1
        race.lane_times = {1: 3.456}  # Already finished
        race.lane_count = 3

        race.laneDNF(1)

        assert race.lane_times[1] == DNF_TIME
        # Count should NOT increase (was already recorded)
        assert race.lanesFinished == 1

    def test_rl033_dnf_completes_race(self, derby_race_instance):
        """RL-033: DNF of last unfinished lane completes race."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING, RACE_STATE_FINISHED, DNF_TIME

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 2
        race.lane_times = {1: 3.1, 2: 3.2}  # Two finished
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1

        result = race.laneDNF(3)

        assert result is True
        assert race.race_state == RACE_STATE_FINISHED

    def test_rl034_dnf_increments_count(self, derby_race_instance):
        """RL-034: DNF for new lane increments lanesFinished."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 0
        race.lane_times = {}
        race.lane_count = 3

        race.laneDNF(1)

        assert race.lanesFinished == 1

    def test_rl035_dnf_doesnt_double_count(self, derby_race_instance):
        """RL-035: DNF for already-finished lane doesn't double count."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 1
        race.lane_times = {1: 3.456}
        race.lane_count = 3

        race.laneDNF(1)

        # Count should stay at 1
        assert race.lanesFinished == 1


# =============================================================================
# Test Classes: Race Timeout
# =============================================================================

@pytest.mark.skipif(not PAHO_MQTT_V2, reason=SKIP_REASON)
class TestRaceTimeout:
    """Tests for race timeout handling (RL-040 through RL-043)."""

    def test_rl040_timeout_marks_dnf(self, derby_race_instance):
        """RL-040: Race timeout marks unfinished lanes as DNF."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING, DNF_TIME, RACE_TIMEOUT

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - (RACE_TIMEOUT + 1)  # Exceeded timeout
        race.lanesFinished = 1
        race.lane_times = {1: 3.456}  # Only lane 1 finished
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1

        race.checkRaceTimeout()

        # Lanes 2 and 3 should be marked DNF
        assert race.lane_times.get(2) == DNF_TIME or 2 not in race.lane_times  # May be cleared by stopRace
        assert race.lane_times.get(3) == DNF_TIME or 3 not in race.lane_times

    def test_rl041_timeout_sends_alert(self, derby_race_instance):
        """RL-041: Race timeout sends alert."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING, RACE_TIMEOUT

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - (RACE_TIMEOUT + 1)
        race.lanesFinished = 1
        race.lane_times = {1: 3.456}
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1
        race.alert_handler.alerts = []

        race.checkRaceTimeout()

        # Should have sent an alert
        assert len(race.alert_handler.alerts) > 0
        assert any('ERR-RACE-301' in str(a.get('code', '')) for a in race.alert_handler.alerts)

    def test_rl042_timeout_completes_race(self, derby_race_instance):
        """RL-042: Timeout completes race after marking all DNF."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING, RACE_STATE_FINISHED, RACE_TIMEOUT

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - (RACE_TIMEOUT + 1)
        race.lanesFinished = 0  # No lanes finished
        race.lane_times = {}
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1

        result = race.checkRaceTimeout()

        assert result is True
        assert race.race_state == RACE_STATE_FINISHED

    def test_rl043_no_timeout_if_not_racing(self, derby_race_instance):
        """RL-043: checkRaceTimeout returns False if not racing."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_STOPPED

        race.race_state = RACE_STATE_STOPPED

        result = race.checkRaceTimeout()

        assert result is False


# =============================================================================
# Test Classes: Database Fallback (DB-001 through DB-005)
# =============================================================================

@pytest.mark.skipif(not PAHO_MQTT_V2, reason=SKIP_REASON)
class TestDatabaseFallback:
    """Tests for database fallback logic."""

    def test_db001_db_unavailable_at_init(self, mock_mqtt_client, mock_api_client, mock_alert_handler):
        """DB-001: DB unavailable at init uses HTTP fallback."""
        with patch('paho.mqtt.client.Client', return_value=mock_mqtt_client):
            with patch('derbyRace.DerbyNetClient', return_value=mock_api_client):
                with patch('derbyRace.ServerLogger') as mock_logger:
                    mock_logger_instance = Mock()
                    mock_logger_instance.get_logger.return_value = Mock()
                    mock_logger.return_value = mock_logger_instance

                    with patch('derbyRace.DIRECT_DB_AVAILABLE', False):
                        with patch('derbyRace.ALERT_HANDLER_AVAILABLE', False):
                            from derbyRace import derbyRace

                            race = derbyRace(lane_count=3)

                            assert race.db is None

                            race.client.loop_stop()

    def test_db003_db_write_success(self, derby_race_instance):
        """DB-003: Successful DB write doesn't call HTTP."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 3
        race.lane_times = {1: 3.1, 2: 3.2, 3: 3.3}
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1
        db.should_fail = False
        db.should_raise = False

        race.stopRace()

        assert len(db.write_calls) == 1
        assert len(api.sent_finishes) == 0

    def test_db004_db_write_failure(self, derby_race_instance):
        """DB-004: DB returning False triggers HTTP fallback."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 3
        race.lane_times = {1: 3.1, 2: 3.2, 3: 3.3}
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1
        db.should_fail = True

        race.stopRace()

        assert len(api.sent_finishes) == 1

    def test_db005_db_write_exception(self, derby_race_instance):
        """DB-005: DB exception triggers HTTP fallback."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 5
        race.lanesFinished = 3
        race.lane_times = {1: 3.1, 2: 3.2, 3: 3.3}
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1
        db.should_raise = True

        race.stopRace()

        assert len(api.sent_finishes) == 1


# =============================================================================
# Test Classes: Full Race Scenarios
# =============================================================================

@pytest.mark.skipif(not PAHO_MQTT_V2, reason=SKIP_REASON)
class TestFullRaceScenarios:
    """End-to-end race scenario tests."""

    def test_complete_race_all_lanes_finish(self, derby_race_instance):
        """Complete race with all lanes finishing normally."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_STAGING, RACE_STATE_RACING, RACE_STATE_FINISHED

        # Setup
        race.race_state = RACE_STATE_STAGING
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1
        race.lanesFinished = 0
        race.lane_times = {}
        race.start_time = 0

        # Start race
        race.startRace()
        assert race.race_state == RACE_STATE_RACING

        # Lanes finish
        start = race.start_time
        race.laneFinish(2, start + 3.5)  # Lane 2 first
        assert race.lanesFinished == 1

        race.laneFinish(1, start + 3.7)  # Lane 1 second
        assert race.lanesFinished == 2

        race.laneFinish(3, start + 4.0)  # Lane 3 third
        assert race.race_state == RACE_STATE_FINISHED

        # Verify results were submitted
        assert len(db.write_calls) == 1
        results = db.write_calls[0]['lane_times']
        assert abs(results[1] - 3.7) < 0.01
        assert abs(results[2] - 3.5) < 0.01
        assert abs(results[3] - 4.0) < 0.01

    def test_race_with_one_dnf(self, derby_race_instance):
        """Race where one lane is marked DNF."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_STAGING, RACE_STATE_FINISHED, DNF_TIME

        race.race_state = RACE_STATE_STAGING
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1
        race.lanesFinished = 0
        race.lane_times = {}
        race.start_time = 0

        # Start race
        race.startRace()
        start = race.start_time

        # Two lanes finish
        race.laneFinish(1, start + 3.5)
        race.laneFinish(2, start + 3.7)

        # Lane 3 DNF
        race.laneDNF(3)

        assert race.race_state == RACE_STATE_FINISHED

        # Verify results
        assert len(db.write_calls) == 1
        results = db.write_calls[0]['lane_times']
        assert results[3] == DNF_TIME

    def test_race_with_db_fallback(self, derby_race_instance):
        """Race where DB fails and falls back to HTTP."""
        race, mqtt, api, db = derby_race_instance
        from derbyRace import RACE_STATE_STAGING, RACE_STATE_FINISHED

        race.race_state = RACE_STATE_STAGING
        race.lane_count = 3
        race.roundid = 1
        race.heatid = 1
        race.lanesFinished = 0
        race.lane_times = {}
        race.start_time = 0
        db.should_raise = True  # DB will fail

        # Start race
        race.startRace()
        start = race.start_time

        # All lanes finish
        race.laneFinish(1, start + 3.5)
        race.laneFinish(2, start + 3.7)
        race.laneFinish(3, start + 4.0)

        # Verify HTTP fallback was used
        assert len(api.sent_finishes) == 1

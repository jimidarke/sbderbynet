"""
Unit tests for derbyRace.py hardware integration.

Tests verify:
- MQTT message parsing and dispatch
- DIP switch mapping
- LED control
- Timer heartbeat management

Test IDs reference DERBYRACE_TEST_PLAN.md (HW-001 through HW-035).
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
# Mock Classes
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
        self.device_status_calls = []
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
            'lane_times': dict(lane_times)
        })

    def send_start(self):
        self.sent_starts.append(time.time())

    def set_staging(self):
        self.staging_calls.append(time.time())

    def send_timer_heartbeat(self, heartbeats, starter_heartbeat=None):
        self.heartbeat_calls.append(dict(heartbeats))
        return True

    def send_device_status(self, payload):
        self.device_status_calls.append(payload)
        return True

    def login(self):
        return 'mock_auth_code'


class MockAlertHandler:
    """Mock alert handler for testing."""

    def __init__(self, *args, **kwargs):
        self.alerts = []

    def check_and_alert(self, log_entry):
        self.alerts.append(log_entry)
        return True


class MockMessage:
    """Mock MQTT message object."""
    def __init__(self, topic, payload):
        self.topic = topic
        if isinstance(payload, str):
            self.payload = payload.encode('utf-8')
        elif isinstance(payload, dict):
            self.payload = json.dumps(payload).encode('utf-8')
        else:
            self.payload = payload


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
def mock_alert_handler():
    """Create a mock alert handler."""
    return MockAlertHandler()


@pytest.fixture
def derby_race_instance(mock_mqtt_client, mock_api_client, mock_alert_handler):
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
                            with patch('derbyRace.DIRECT_DB_AVAILABLE', False):
                                from derbyRace import derbyRace

                                race = derbyRace(lane_count=3)
                                race.client = mock_mqtt_client
                                race.api = mock_api_client
                                race.alert_handler = mock_alert_handler

                                yield race, mock_mqtt_client, mock_api_client

                                race.client.loop_stop()


# =============================================================================
# Test Classes: DIP Switch Mapping
# =============================================================================

@pytest.mark.skipif(not PAHO_MQTT_V2, reason=SKIP_REASON)
class TestDIPSwitchMapping:
    """Tests for DIP switch to lane mapping (HW-010 through HW-014)."""

    def test_hw010_dip_1000_lane_1(self):
        """HW-010: DIP 1000 maps to Lane 1."""
        from derbyRace import derbyRace
        assert derbyRace.getDIPName("1000") == 1

    def test_hw011_dip_1001_lane_2(self):
        """HW-011: DIP 1001 maps to Lane 2."""
        from derbyRace import derbyRace
        assert derbyRace.getDIPName("1001") == 2

    def test_hw012_dip_1010_lane_3(self):
        """HW-012: DIP 1010 maps to Lane 3."""
        from derbyRace import derbyRace
        assert derbyRace.getDIPName("1010") == 3

    def test_hw013_dip_1011_lane_4(self):
        """HW-013: DIP 1011 maps to Lane 4."""
        from derbyRace import derbyRace
        assert derbyRace.getDIPName("1011") == 4

    def test_hw014_unknown_dip_returns_0(self):
        """HW-014: Unknown DIP value returns 0."""
        from derbyRace import derbyRace
        assert derbyRace.getDIPName("0000") == 0
        assert derbyRace.getDIPName("1111") == 0
        assert derbyRace.getDIPName("") == 0
        assert derbyRace.getDIPName("invalid") == 0


# =============================================================================
# Test Classes: MQTT Message Parsing
# =============================================================================

@pytest.mark.skipif(not PAHO_MQTT_V2, reason=SKIP_REASON)
class TestMQTTMessageParsing:
    """Tests for MQTT message parsing (HW-001 through HW-006)."""

    def test_hw001_parse_state_message_go(self, derby_race_instance):
        """HW-001: Parse state message with GO triggers startRace."""
        race, mqtt, api = derby_race_instance
        from derbyRace import RACE_STATE_STAGING, RACE_STATE_RACING

        race.race_state = RACE_STATE_STAGING
        race.start_time = 0
        race.lanesFinished = 0
        race.lane_times = {}

        message = MockMessage(
            "derbynet/device/timer1/state",
            {"state": "GO", "dip": "1000", "toggle": True}
        )

        race.on_message(mqtt, None, message)

        assert race.race_state == RACE_STATE_RACING
        assert race.start_time > 0

    def test_hw002_parse_finish_toggle(self, derby_race_instance):
        """HW-002: Parse toggle=false triggers laneFinish."""
        race, mqtt, api = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.start_time = time.time() - 3
        race.lanesFinished = 0
        race.lane_times = {}
        race.lane_count = 3

        message = MockMessage(
            "derbynet/device/timer1/state",
            {"state": "FINISH", "dip": "1000", "toggle": False}
        )

        race.on_message(mqtt, None, message)

        assert 1 in race.lane_times
        assert race.lanesFinished == 1

    def test_hw003_parse_telemetry(self, derby_race_instance):
        """HW-003: Parse telemetry updates heartbeat."""
        race, mqtt, api = derby_race_instance
        from derbyRace import RACE_STATE_STOPPED

        race.race_state = RACE_STATE_STOPPED
        race.timer_heartbeats = {}

        message = MockMessage(
            "derbynet/device/timer1/telemetry",
            {
                "hostname": "finish-timer-1",
                "hwid": "ABC123",
                "dip": "1000",
                "uptime": 3600,
                "ip": "192.168.1.100",
                "mac": "AA:BB:CC:DD:EE:FF",
                "readyToRace": True
            }
        )

        race.on_message(mqtt, None, message)

        assert 1 in race.timer_heartbeats
        assert race.timer_heartbeats[1]['isReady'] is True

    def test_hw004_ignore_finish_if_not_racing(self, derby_race_instance):
        """HW-004: Finish message ignored when not racing."""
        race, mqtt, api = derby_race_instance
        from derbyRace import RACE_STATE_STOPPED

        race.race_state = RACE_STATE_STOPPED
        race.lanesFinished = 0
        race.lane_times = {}

        message = MockMessage(
            "derbynet/device/timer1/state",
            {"state": "FINISH", "dip": "1000", "toggle": False}
        )

        race.on_message(mqtt, None, message)

        # Should be ignored
        assert race.lanesFinished == 0
        assert 1 not in race.lane_times

    def test_hw005_invalid_json_rejected(self, derby_race_instance):
        """HW-005: Invalid JSON is rejected without crash."""
        race, mqtt, api = derby_race_instance
        from derbyRace import RACE_STATE_STOPPED

        race.race_state = RACE_STATE_STOPPED

        message = MockMessage(
            "derbynet/device/timer1/state",
            b"not valid json {{"
        )

        # Should not raise exception
        try:
            race.on_message(mqtt, None, message)
        except Exception as e:
            pytest.fail(f"Should not raise: {e}")

    def test_hw006_missing_required_fields(self, derby_race_instance):
        """HW-006: Message with missing fields handled gracefully."""
        race, mqtt, api = derby_race_instance
        from derbyRace import RACE_STATE_STOPPED

        race.race_state = RACE_STATE_STOPPED

        # Telemetry missing required fields
        message = MockMessage(
            "derbynet/device/timer1/telemetry",
            {"hostname": "partial-data"}
        )

        # Should not crash
        try:
            race.on_message(mqtt, None, message)
        except Exception as e:
            pytest.fail(f"Should not raise: {e}")


# =============================================================================
# Test Classes: LED Control
# =============================================================================

@pytest.mark.skipif(not PAHO_MQTT_V2, reason=SKIP_REASON)
class TestLEDControl:
    """Tests for LED control operations (HW-020 through HW-024)."""

    def test_hw020_update_all_leds(self, derby_race_instance):
        """HW-020: updateLED("green", "all") publishes to all lanes."""
        race, mqtt, api = derby_race_instance

        race.lane_count = 3
        mqtt.published = []

        race.updateLED("green", "all")

        led_publishes = [p for p in mqtt.published if 'led' in p['topic']]
        assert len(led_publishes) == 3

        # Should have published to lanes 1, 2, 3
        topics = [p['topic'] for p in led_publishes]
        assert "derbynet/lane/1/led" in topics
        assert "derbynet/lane/2/led" in topics
        assert "derbynet/lane/3/led" in topics

        # All should be green
        assert all(p['payload'] == 'green' for p in led_publishes)

    def test_hw021_update_single_led(self, derby_race_instance):
        """HW-021: updateLED("red", 1) publishes to lane 1 only."""
        race, mqtt, api = derby_race_instance

        mqtt.published = []

        race.updateLED("red", 1)

        led_publishes = [p for p in mqtt.published if 'led' in p['topic']]
        assert len(led_publishes) == 1
        assert led_publishes[0]['topic'] == "derbynet/lane/1/led"
        assert led_publishes[0]['payload'] == "red"

    def test_hw022_led_blue_on_staging(self, derby_race_instance):
        """HW-022: LED is blue when entering STAGING."""
        race, mqtt, api = derby_race_instance
        from derbyRace import RACE_STATE_STOPPED, RACE_STATE_STAGING

        race.race_state = RACE_STATE_STOPPED
        race.lanesFinished = 0
        race.lane_times = {}
        race.start_time = 0
        mqtt.published = []

        api.set_race_status({
            'active': True,
            'timer-state-string': 'Staging',
            'lanes': []
        })

        race.setLEDFromRaceStat(api.get_race_status())

        assert race.led == "blue"

    def test_hw023_led_green_on_racing(self, derby_race_instance):
        """HW-023: LED is green when RACING."""
        race, mqtt, api = derby_race_instance
        from derbyRace import RACE_STATE_STAGING

        race.race_state = RACE_STATE_STAGING
        race.start_time = 0
        mqtt.published = []

        race.startRace()

        led_publishes = [p for p in mqtt.published if 'led' in p['topic']]
        green_publishes = [p for p in led_publishes if p['payload'] == 'green']
        assert len(green_publishes) > 0

    def test_hw024_led_red_on_stopped(self, derby_race_instance):
        """HW-024: LED is red when STOPPED."""
        race, mqtt, api = derby_race_instance
        from derbyRace import RACE_STATE_STAGING, RACE_STATE_STOPPED

        race.race_state = RACE_STATE_STAGING
        race.lanesFinished = 0
        race.lane_times = {}
        race.start_time = 0
        mqtt.published = []

        api.set_race_status({
            'active': False,
            'timer-state-string': '',
            'lanes': []
        })

        race.setLEDFromRaceStat(api.get_race_status())

        assert race.led == "red"


# =============================================================================
# Test Classes: Timer Heartbeat
# =============================================================================

@pytest.mark.skipif(not PAHO_MQTT_V2, reason=SKIP_REASON)
class TestTimerHeartbeat:
    """Tests for timer heartbeat management (HW-030 through HW-035)."""

    def test_hw030_heartbeat_updates_timestamp(self, derby_race_instance):
        """HW-030: timerHeartbeat updates timestamp."""
        race, mqtt, api = derby_race_instance

        race.timer_heartbeats = {}

        before = time.time()
        race.timerHeartbeat(1, True)
        after = time.time()

        assert 1 in race.timer_heartbeats
        assert before <= race.timer_heartbeats[1]['time'] <= after
        assert race.timer_heartbeats[1]['isReady'] is True

    def test_hw031_first_heartbeat_sets_online(self, derby_race_instance):
        """HW-031: First heartbeat marks timer as online."""
        race, mqtt, api = derby_race_instance

        race.timer_heartbeats = {}

        race.timerHeartbeat(1, True)

        assert 1 in race.timer_heartbeats

    def test_hw032_ready_state_tracked(self, derby_race_instance):
        """HW-032: Ready state change is tracked."""
        race, mqtt, api = derby_race_instance

        race.timer_heartbeats = {}

        race.timerHeartbeat(1, False)
        assert race.timer_heartbeats[1]['isReady'] is False

        race.timerHeartbeat(1, True)
        assert race.timer_heartbeats[1]['isReady'] is True

    def test_hw033_offline_timer_cleanup(self, derby_race_instance):
        """HW-033: Timer removed after heartbeat timeout."""
        race, mqtt, api = derby_race_instance
        from derbyRace import HEARTBEAT_TIMEOUT

        # Add a timer with old timestamp
        old_time = time.time() - (HEARTBEAT_TIMEOUT + 1)
        race.timer_heartbeats = {
            1: {'time': old_time, 'isReady': True}
        }

        # Cleanup should remove it
        removed = race.cleanup_offline_timers(time.time())

        assert 1 in removed
        assert 1 not in race.timer_heartbeats

    def test_hw034_offline_timer_alert(self, derby_race_instance):
        """HW-034: Timer going offline triggers alert."""
        race, mqtt, api = derby_race_instance
        from derbyRace import HEARTBEAT_TIMEOUT

        # Add a timer with old timestamp
        old_time = time.time() - (HEARTBEAT_TIMEOUT + 1)
        race.timer_heartbeats = {
            1: {'time': old_time, 'isReady': True}
        }
        race.alert_handler.alerts = []

        # Cleanup should trigger alert
        race.cleanup_offline_timers(time.time())

        assert len(race.alert_handler.alerts) > 0
        assert any('ERR-HW-301' in str(a.get('code', '')) for a in race.alert_handler.alerts)

    def test_hw035_heartbeat_sent_to_api(self, derby_race_instance):
        """HW-035: Heartbeat is sent to API."""
        race, mqtt, api = derby_race_instance

        race.timer_heartbeats = {1: {'time': time.time(), 'isReady': True}}
        race.last_heartbeat = 0
        api.heartbeat_calls = []

        race.send_heartbeat_to_api(time.time())

        assert len(api.heartbeat_calls) > 0


# =============================================================================
# Test Classes: Concurrent Heartbeat Access
# =============================================================================

@pytest.mark.skipif(not PAHO_MQTT_V2, reason=SKIP_REASON)
class TestConcurrentHeartbeatAccess:
    """Tests for thread-safe heartbeat operations."""

    def test_concurrent_heartbeat_updates(self, derby_race_instance):
        """Multiple timers updating heartbeats concurrently."""
        import threading

        race, mqtt, api = derby_race_instance
        race.timer_heartbeats = {}
        errors = []

        def update_heartbeat(lane):
            try:
                for _ in range(50):
                    race.timerHeartbeat(lane, True)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(str(e))

        threads = [
            threading.Thread(target=update_heartbeat, args=(1,)),
            threading.Thread(target=update_heartbeat, args=(2,)),
            threading.Thread(target=update_heartbeat, args=(3,)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(race.timer_heartbeats) == 3

    def test_heartbeat_copy_for_api(self, derby_race_instance):
        """send_heartbeat_to_api makes safe copy."""
        race, mqtt, api = derby_race_instance

        race.timer_heartbeats = {
            1: {'time': time.time(), 'isReady': True},
            2: {'time': time.time(), 'isReady': False},
        }
        api.heartbeat_calls = []

        race.send_heartbeat_to_api(time.time())

        # API should have received a copy
        assert len(api.heartbeat_calls) == 1
        sent = api.heartbeat_calls[0]
        assert 1 in sent
        assert 2 in sent

        # Modifying original shouldn't affect what was sent
        race.timer_heartbeats[3] = {'time': time.time(), 'isReady': True}
        assert 3 not in sent


# =============================================================================
# Test Classes: Pinny Assignment
# =============================================================================

@pytest.mark.skipif(not PAHO_MQTT_V2, reason=SKIP_REASON)
class TestPinnyAssignment:
    """Tests for pinny (racer number) assignment to lanes."""

    def test_set_lane_pinny_publishes(self, derby_race_instance):
        """setLanePinny publishes to correct topic."""
        race, mqtt, api = derby_race_instance

        mqtt.published = []
        race.lanePinny = {}

        race.setLanePinny(1, 42)

        pinny_publishes = [p for p in mqtt.published if 'pinny' in p['topic']]
        assert len(pinny_publishes) == 1
        assert pinny_publishes[0]['topic'] == "derbynet/lane/1/pinny"
        assert pinny_publishes[0]['payload'] == "0042"  # Zero-padded

    def test_pinny_not_republished_if_same(self, derby_race_instance):
        """setLanePinny doesn't republish same pinny."""
        race, mqtt, api = derby_race_instance

        race.lanePinny = {"1": "0042"}
        mqtt.published = []

        race.setLanePinny(1, 42)

        pinny_publishes = [p for p in mqtt.published if 'pinny' in p['topic']]
        assert len(pinny_publishes) == 0

    def test_pinny_zero_padded(self, derby_race_instance):
        """Pinny is zero-padded to 4 digits."""
        race, mqtt, api = derby_race_instance

        mqtt.published = []
        race.lanePinny = {}

        race.setLanePinny(1, 7)

        pinny_publishes = [p for p in mqtt.published if 'pinny' in p['topic']]
        assert pinny_publishes[0]['payload'] == "0007"

    def test_hw040_bye_pinny_published_verbatim(self, derby_race_instance):
        """HW-040: An empty (bye) lane publishes '----' verbatim, not coerced to '0000'."""
        race, mqtt, api = derby_race_instance
        from derbyRace import BYE_PINNY

        mqtt.published = []
        race.lanePinny = {}

        race.setLanePinny(3, BYE_PINNY)

        pinny_publishes = [p for p in mqtt.published if 'pinny' in p['topic']]
        assert len(pinny_publishes) == 1
        assert pinny_publishes[0]['topic'] == "derbynet/lane/3/pinny"
        assert pinny_publishes[0]['payload'] == BYE_PINNY  # not "0000"

    def test_hw041_trailing_bye_blanks_empty_lane(self, derby_race_instance):
        """HW-041: 2-racer heat on a 3-lane track blanks the trailing empty lane.

        Reproduces the race-day symptom: without this, lane 3 retains a stale
        pinny from the previous heat. Every physical lane must be refreshed.
        """
        race, mqtt, api = derby_race_instance
        from derbyRace import BYE_PINNY

        race.lanePinny = {}
        race.lane_count = 3
        api.set_race_status({
            'active': False, 'roundid': 1, 'heat': 5, 'class': 'Test',
            'timer-state-string': '', 'lane-count': 3,
            'lanes': [{'lane': 1, 'racerid': '0007', 'name': 'A', 'finishtime': ''},
                      {'lane': 2, 'racerid': '0012', 'name': 'B', 'finishtime': ''}],
        })
        mqtt.published = []

        race.updateFromDerbyAPI()

        pinny = {p['topic']: p['payload'] for p in mqtt.published if 'pinny' in p['topic']}
        assert pinny["derbynet/lane/1/pinny"] == "0007"
        assert pinny["derbynet/lane/2/pinny"] == "0012"
        assert pinny["derbynet/lane/3/pinny"] == BYE_PINNY  # empty lane blanked

    def test_hw042_middle_bye_preserves_alignment(self, derby_race_instance):
        """HW-042: Middle bye (racers in lanes 1 & 3) blanks lane 2, keeps alignment.

        The pinny loop is keyed by physical lane index, so a non-trailing bye does
        not shift racers onto the wrong lanes.
        """
        race, mqtt, api = derby_race_instance
        from derbyRace import BYE_PINNY

        race.lanePinny = {}
        race.lane_count = 3
        api.set_race_status({
            'active': False, 'roundid': 1, 'heat': 6, 'class': 'Test',
            'timer-state-string': '', 'lane-count': 3,
            'lanes': [{'lane': 1, 'racerid': '0007', 'name': 'A', 'finishtime': ''},
                      {'lane': 3, 'racerid': '0012', 'name': 'B', 'finishtime': ''}],
        })
        mqtt.published = []

        race.updateFromDerbyAPI()

        pinny = {p['topic']: p['payload'] for p in mqtt.published if 'pinny' in p['topic']}
        assert pinny["derbynet/lane/1/pinny"] == "0007"
        assert pinny["derbynet/lane/2/pinny"] == BYE_PINNY  # middle bye blanked
        assert pinny["derbynet/lane/3/pinny"] == "0012"     # NOT shifted to lane 2


# =============================================================================
# Test Classes: Physical vs Populated Lanes (bye-lane handling)
# =============================================================================

@pytest.mark.skipif(not PAHO_MQTT_V2, reason=SKIP_REASON)
class TestPhysicalVsPopulatedLanes:
    """Separation of PHYSICAL lane count (display) from POPULATED lanes (completion).

    Covers heats with a bye (empty lane) from pull-forward or odd racer counts
    (HW-050 through HW-054).
    """

    def test_hw050_expected_finishers_counts_populated(self, derby_race_instance):
        """HW-050: _expected_finishers counts populated lanes, not physical."""
        race, mqtt, api = derby_race_instance
        race.lane_count = 3
        race.active_lanes = {1, 2}
        assert race._expected_finishers() == 2

    def test_hw051_expected_finishers_fallback_physical(self, derby_race_instance):
        """HW-051: With no known roster, _expected_finishers falls back to physical."""
        race, mqtt, api = derby_race_instance
        race.lane_count = 3
        race.active_lanes = set()
        assert race._expected_finishers() == 3

    def test_hw052_physical_lane_count_from_poll(self, derby_race_instance):
        """HW-052: Physical lane count resolves from poll race_info when no DB."""
        race, mqtt, api = derby_race_instance
        race.db = None
        assert race._resolve_physical_lane_count({'lane-count': 4}, [{'lane': 1}]) == 4

    def test_hw053_physical_lane_count_max_index_fallback(self, derby_race_instance):
        """HW-053: Fallback uses max lane INDEX, so a middle bye still yields 3."""
        race, mqtt, api = derby_race_instance
        race.db = None
        race.lane_count = 1
        # racers in lanes 1 & 3, no DB/poll hint -> physical must be 3, not len()==2
        assert race._resolve_physical_lane_count({}, [{'lane': 1}, {'lane': 3}]) == 3

    def test_hw054_bye_heat_completes_without_waiting(self, derby_race_instance):
        """HW-054: A 2-racer heat on a 3-lane track completes after 2 finishes.

        Guards against the latent hang where the race waits forever on the empty
        physical lane.
        """
        race, mqtt, api = derby_race_instance
        from derbyRace import RACE_STATE_RACING

        race.race_state = RACE_STATE_RACING
        race.lane_count = 3          # physical
        race.active_lanes = {1, 2}   # populated (lane 3 is a bye)
        race.lane_times = {}
        race.lanesFinished = 0
        race.start_time = time.time() - 1

        assert race.laneFinish(1) is False   # 1/2 -> not complete
        assert race.laneFinish(2) is True    # 2/2 -> complete, no wait on lane 3

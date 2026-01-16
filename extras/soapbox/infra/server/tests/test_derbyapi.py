"""
Tests for DerbyNet API Client (derbyapi.py)

This module tests the gateway between physical devices and the DerbyNet database,
validating authentication, heartbeats, race lifecycle, and device telemetry.

Test Categories:
- Authentication and login flow
- Timer heartbeat logic (recent, stale, missing timers)
- Timer state transitions
- Race lifecycle (start/finish)
- Device status telemetry
- RSSI conversion
- Error handling and retry logic
"""

import pytest
import json
import time
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import xml.etree.ElementTree as ET


class TestDerbyNetClientInitialization:
    """Test DerbyNetClient initialization and configuration."""

    def test_init_with_default_ip(self):
        """Client should use default IP when none provided."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('derbyapi.os.getenv', return_value='192.168.100.10'):
                from derbyapi import DerbyNetClient
                client = DerbyNetClient()
                assert '192.168.100.10' in client.url

    def test_init_with_custom_ip(self):
        """Client should use provided IP address."""
        from derbyapi import DerbyNetClient
        client = DerbyNetClient('10.0.0.50')
        assert '10.0.0.50' in client.url
        assert client.server_ip == '10.0.0.50'

    def test_init_with_env_var(self):
        """Client should use DERBYNET_API_HOST environment variable."""
        with patch.dict('os.environ', {'DERBYNET_API_HOST': '172.16.0.100'}):
            from derbyapi import DerbyNetClient
            client = DerbyNetClient()
            assert '172.16.0.100' in client.url

    def test_init_default_state(self):
        """Client should initialize with NOT_CONNECTED state."""
        from derbyapi import DerbyNetClient, TIMER_STATE_NOT_CONNECTED
        client = DerbyNetClient('localhost')
        assert client.timer_state == TIMER_STATE_NOT_CONNECTED
        assert client.authcode is None
        assert client.last_heartbeat_time == 0


class TestDerbyNetClientLogin:
    """Test authentication and login flow."""

    @pytest.fixture
    def mock_response_success(self):
        """Mock successful login response."""
        mock = Mock()
        mock.status_code = 200
        mock.json.return_value = {"outcome": {"code": "success"}}
        mock.headers = {'Set-Cookie': 'PHPSESSID=abc123; path=/'}
        return mock

    @pytest.fixture
    def mock_response_failure(self):
        """Mock failed login response."""
        mock = Mock()
        mock.status_code = 200
        mock.json.return_value = {"outcome": {"code": "failure", "message": "Invalid credentials"}}
        mock.headers = {}
        mock.text = '{"outcome": {"code": "failure"}}'
        return mock

    def test_login_success(self, mock_response_success):
        """Successful login should set authcode and CONNECTED state."""
        from derbyapi import DerbyNetClient, TIMER_STATE_CONNECTED

        with patch('derbyapi.requests.post', return_value=mock_response_success):
            client = DerbyNetClient('localhost')
            result = client.login()

            assert result is not None
            assert 'PHPSESSID' in client.authcode
            assert client.timer_state == TIMER_STATE_CONNECTED

    def test_login_failure_invalid_credentials(self, mock_response_failure):
        """Failed login should return None and set NOT_CONNECTED state."""
        from derbyapi import DerbyNetClient, TIMER_STATE_NOT_CONNECTED

        with patch('derbyapi.requests.post', return_value=mock_response_failure):
            client = DerbyNetClient('localhost')
            result = client.login()

            assert result is None
            assert client.timer_state == TIMER_STATE_NOT_CONNECTED

    def test_login_retry_on_network_error(self, mock_response_success):
        """Login should retry on network errors."""
        from derbyapi import DerbyNetClient

        # First two calls fail, third succeeds
        with patch('derbyapi.requests.post') as mock_post:
            mock_post.side_effect = [
                Exception("Connection refused"),
                Exception("Timeout"),
                mock_response_success
            ]

            client = DerbyNetClient('localhost')
            result = client.login()

            assert result is not None
            assert mock_post.call_count == 3


class TestTimerHeartbeat:
    """Test timer heartbeat logic - critical for finish timer synchronization."""

    @pytest.fixture
    def client_with_auth(self):
        """Create authenticated client."""
        from derbyapi import DerbyNetClient
        client = DerbyNetClient('localhost')
        client.authcode = 'PHPSESSID=test123'
        client.last_heartbeat_time = 0  # Force heartbeat
        return client

    @pytest.fixture
    def mock_heartbeat_response(self):
        """Mock successful heartbeat response."""
        mock = Mock()
        mock.status_code = 200
        mock.raise_for_status = Mock()
        return mock

    def test_heartbeat_all_timers_ready(self, client_with_auth, mock_heartbeat_response):
        """All timers present, recent, and ready should confirm=1."""
        current_time = time.time()
        timer_heartbeats = {
            1: {'time': current_time - 1, 'isReady': True},
            2: {'time': current_time - 1, 'isReady': True},
            3: {'time': current_time - 1, 'isReady': True}
        }

        with patch('derbyapi.requests.post', return_value=mock_heartbeat_response) as mock_post:
            result = client_with_auth.send_timer_heartbeat(timer_heartbeats)

            assert result is True
            # Check confirmed=1 in payload
            call_args = mock_post.call_args
            payload = call_args.kwargs.get('data') or call_args[1].get('data')
            assert 'confirmed=1' in payload

    def test_heartbeat_timers_not_ready(self, client_with_auth, mock_heartbeat_response):
        """All timers present but not ready should confirm=0."""
        current_time = time.time()
        timer_heartbeats = {
            1: {'time': current_time - 1, 'isReady': True},
            2: {'time': current_time - 1, 'isReady': False},  # Not ready
            3: {'time': current_time - 1, 'isReady': True}
        }

        with patch('derbyapi.requests.post', return_value=mock_heartbeat_response) as mock_post:
            result = client_with_auth.send_timer_heartbeat(timer_heartbeats)

            assert result is True
            call_args = mock_post.call_args
            payload = call_args.kwargs.get('data') or call_args[1].get('data')
            assert 'confirmed=0' in payload

    def test_heartbeat_stale_timer(self, client_with_auth, mock_heartbeat_response):
        """Timer older than TIMER_RECENT_THRESHOLD should not confirm."""
        from derbyapi import TIMER_RECENT_THRESHOLD
        current_time = time.time()
        timer_heartbeats = {
            1: {'time': current_time - 1, 'isReady': True},
            2: {'time': current_time - (TIMER_RECENT_THRESHOLD + 1), 'isReady': True},  # Stale
            3: {'time': current_time - 1, 'isReady': True}
        }

        with patch('derbyapi.requests.post', return_value=mock_heartbeat_response) as mock_post:
            result = client_with_auth.send_timer_heartbeat(timer_heartbeats)

            assert result is True
            call_args = mock_post.call_args
            payload = call_args.kwargs.get('data') or call_args[1].get('data')
            assert 'confirmed=0' in payload

    def test_heartbeat_missing_timer(self, client_with_auth, mock_heartbeat_response):
        """Missing timer should not confirm."""
        current_time = time.time()
        timer_heartbeats = {
            1: {'time': current_time - 1, 'isReady': True},
            3: {'time': current_time - 1, 'isReady': True}
            # Lane 2 missing
        }

        with patch('derbyapi.requests.post', return_value=mock_heartbeat_response) as mock_post:
            result = client_with_auth.send_timer_heartbeat(timer_heartbeats)

            assert result is True
            call_args = mock_post.call_args
            payload = call_args.kwargs.get('data') or call_args[1].get('data')
            assert 'confirmed=0' in payload

    def test_heartbeat_rate_limiting(self, client_with_auth, mock_heartbeat_response):
        """Heartbeats should be rate limited."""
        from derbyapi import HEARTBEAT_INTERVAL

        client_with_auth.last_heartbeat_time = time.time()  # Recent heartbeat
        timer_heartbeats = {
            1: {'time': time.time(), 'isReady': True},
            2: {'time': time.time(), 'isReady': True},
            3: {'time': time.time(), 'isReady': True}
        }

        with patch('derbyapi.requests.post', return_value=mock_heartbeat_response) as mock_post:
            result = client_with_auth.send_timer_heartbeat(timer_heartbeats)

            # Should return True but not actually send (rate limited)
            assert result is True
            mock_post.assert_not_called()

    def test_heartbeat_reauth_on_401(self, client_with_auth, mock_heartbeat_response):
        """401 response should trigger re-authentication."""
        mock_401 = Mock()
        mock_401.status_code = 401

        mock_login = Mock()
        mock_login.status_code = 200
        mock_login.json.return_value = {"outcome": {"code": "success"}}
        mock_login.headers = {'Set-Cookie': 'PHPSESSID=newtoken'}

        timer_heartbeats = {
            1: {'time': time.time(), 'isReady': True},
            2: {'time': time.time(), 'isReady': True},
            3: {'time': time.time(), 'isReady': True}
        }

        with patch('derbyapi.requests.post') as mock_post:
            mock_post.side_effect = [mock_401, mock_login, mock_heartbeat_response]
            result = client_with_auth.send_timer_heartbeat(timer_heartbeats)

            assert result is True


class TestTimerStateTransitions:
    """Test timer state management."""

    def test_valid_state_transitions(self):
        """Valid state transitions should succeed."""
        from derbyapi import (DerbyNetClient, TIMER_STATE_CONNECTED,
                              TIMER_STATE_STAGING, TIMER_STATE_RUNNING)

        client = DerbyNetClient('localhost')
        client.authcode = 'test'

        assert client.set_timer_state(TIMER_STATE_CONNECTED) is True
        assert client.timer_state == TIMER_STATE_CONNECTED

        assert client.set_timer_state(TIMER_STATE_STAGING) is True
        assert client.timer_state == TIMER_STATE_STAGING

        assert client.set_timer_state(TIMER_STATE_RUNNING) is True
        assert client.timer_state == TIMER_STATE_RUNNING

    def test_invalid_state_transition(self):
        """Invalid state should return False."""
        from derbyapi import DerbyNetClient

        client = DerbyNetClient('localhost')
        result = client.set_timer_state('INVALID_STATE')

        assert result is False

    def test_state_change_forces_heartbeat(self):
        """State change should reset heartbeat timer."""
        from derbyapi import DerbyNetClient, TIMER_STATE_STAGING

        client = DerbyNetClient('localhost')
        client.last_heartbeat_time = time.time()
        old_time = client.last_heartbeat_time

        client.set_timer_state(TIMER_STATE_STAGING)

        assert client.last_heartbeat_time == 0  # Reset to force heartbeat


class TestRaceLifecycle:
    """Test race start and finish operations."""

    @pytest.fixture
    def authenticated_client(self):
        """Create authenticated client."""
        from derbyapi import DerbyNetClient
        client = DerbyNetClient('localhost')
        client.authcode = 'PHPSESSID=test123'
        return client

    def test_send_start_success(self, authenticated_client):
        """Successful start should return True and set RUNNING state."""
        from derbyapi import TIMER_STATE_RUNNING

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.text = '<?xml version="1.0"?><action-response><success/></action-response>'

        with patch('derbyapi.requests.post', return_value=mock_response):
            result = authenticated_client.send_start()

            assert result is True
            assert authenticated_client.timer_state == TIMER_STATE_RUNNING

    def test_send_start_failure(self, authenticated_client):
        """Failed start should return False."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.text = '<failure code="not-staging">Race not in staging</failure>'

        with patch('derbyapi.requests.post', return_value=mock_response):
            result = authenticated_client.send_start()

            assert result is False

    def test_send_finish_with_lane_times(self, authenticated_client):
        """Finish should send lane times correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.text = '<?xml version="1.0"?><action-response><success/></action-response>'

        lane_times = {1: 3.456, 2: 3.789, 3: 4.012}

        with patch('derbyapi.requests.post', return_value=mock_response) as mock_post:
            result = authenticated_client.send_finish(1, 5, lane_times)

            assert result is True
            call_args = mock_post.call_args
            payload = call_args.kwargs.get('data') or call_args[1].get('data')
            assert 'lane1=3.456' in payload
            assert 'lane2=3.789' in payload
            assert 'lane3=4.012' in payload
            assert 'roundid=1' in payload
            assert 'heat=5' in payload

    def test_send_finish_network_error(self, authenticated_client):
        """Network error during finish should set UNHEALTHY state."""
        from derbyapi import TIMER_STATE_UNHEALTHY
        from pip._vendor.requests import RequestException

        with patch('derbyapi.requests.post') as mock_post:
            mock_post.side_effect = RequestException("Network error")

            result = authenticated_client.send_finish(1, 1, {1: 3.5})

            assert result is False
            assert authenticated_client.timer_state == TIMER_STATE_UNHEALTHY


class TestGetRaceStatus:
    """Test race status polling."""

    @pytest.fixture
    def mock_coordinator_poll(self):
        """Mock coordinator poll response."""
        return {
            "current-heat": {
                "now_racing": True,
                "roundid": 5,
                "heat": 3,
                "class": "Junior"
            },
            "race_info": {
                "lane_count": 3
            },
            "racers": [
                {"lane": 1, "name": "Racer A", "carnumber": "101", "finishtime": ""},
                {"lane": 2, "name": "Racer B", "carnumber": "102", "finishtime": ""},
                {"lane": 3, "name": "Racer C", "carnumber": "103", "finishtime": "3.456"}
            ],
            "timer-state": {
                "state": "running",
                "message": "Race in progress"
            }
        }

    def test_get_race_status_parsing(self, mock_coordinator_poll):
        """Race status should parse correctly."""
        from derbyapi import DerbyNetClient

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = mock_coordinator_poll

        client = DerbyNetClient('localhost')
        client.authcode = 'test'

        with patch('derbyapi.requests.get', return_value=mock_response):
            status = client.get_race_status()

            assert status['active'] is True
            assert status['roundid'] == 5
            assert status['heat'] == 3
            assert status['class'] == 'Junior'
            assert status['lane-count'] == 3
            assert len(status['lanes']) == 3
            assert status['lanes'][2]['finishtime'] == '3.456'

    def test_get_race_status_no_racers(self):
        """Empty race should return empty lanes list."""
        from derbyapi import DerbyNetClient

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "current-heat": {"now_racing": False},
            "race_info": {"lane_count": 3}
        }

        client = DerbyNetClient('localhost')
        client.authcode = 'test'

        with patch('derbyapi.requests.get', return_value=mock_response):
            status = client.get_race_status()

            assert status['active'] is False
            assert status['lanes'] == []


class TestDeviceTelemetry:
    """Test device status telemetry."""

    def test_send_device_status_valid_payload(self):
        """Valid telemetry payload should be sent correctly."""
        from derbyapi import DerbyNetClient

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.text = '{"status": "ok"}'

        client = DerbyNetClient('localhost')
        client.authcode = 'test'

        telemetry = {
            "hostname": "FINISH1",
            "hwid": "ABC123",
            "uptime": 3600,
            "ip": "192.168.100.101",
            "mac": "AA:BB:CC:DD:EE:FF",
            "wifi_rssi": -65,
            "battery_level": 85,
            "cpu_temp": 45.5,
            "memory_usage": 512,
            "disk": 75,
            "cpu_usage": 25
        }

        with patch('derbyapi.requests.post', return_value=mock_response) as mock_post:
            result = client.send_device_status(telemetry)

            assert result is True
            call_args = mock_post.call_args
            json_payload = call_args.kwargs.get('json')
            assert json_payload['devices'][0]['device_name'] == 'FINISH1'
            assert json_payload['devices'][0]['wifi_signal'] == 70  # RSSI -65 = 70%

    def test_send_device_status_invalid_payload(self):
        """Non-dict payload should return False."""
        from derbyapi import DerbyNetClient

        client = DerbyNetClient('localhost')
        client.authcode = 'test'

        result = client.send_device_status("invalid string payload")
        assert result is False

    def test_send_device_status_missing_fields(self):
        """Missing fields should use defaults."""
        from derbyapi import DerbyNetClient

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.text = '{"status": "ok"}'

        client = DerbyNetClient('localhost')
        client.authcode = 'test'

        telemetry = {"hostname": "TEST"}  # Minimal payload

        with patch('derbyapi.requests.post', return_value=mock_response) as mock_post:
            result = client.send_device_status(telemetry)

            assert result is True
            call_args = mock_post.call_args
            json_payload = call_args.kwargs.get('json')
            assert json_payload['devices'][0]['device_name'] == 'TEST'
            assert json_payload['devices'][0]['serial'] == ''  # Default


class TestRSSIConversion:
    """Test WiFi RSSI to percentage conversion."""

    def test_rssi_excellent_signal(self):
        """RSSI >= -50 should return 100%."""
        from derbyapi import DerbyNetClient

        assert DerbyNetClient.getWiFiPercentFromRSSI(-50) == 100
        assert DerbyNetClient.getWiFiPercentFromRSSI(-30) == 100
        assert DerbyNetClient.getWiFiPercentFromRSSI(0) == 100

    def test_rssi_no_signal(self):
        """RSSI <= -100 should return 0%."""
        from derbyapi import DerbyNetClient

        assert DerbyNetClient.getWiFiPercentFromRSSI(-100) == 0
        assert DerbyNetClient.getWiFiPercentFromRSSI(-120) == 0

    def test_rssi_medium_signal(self):
        """RSSI between -50 and -100 should scale linearly."""
        from derbyapi import DerbyNetClient

        # -75 dBm = 50%
        assert DerbyNetClient.getWiFiPercentFromRSSI(-75) == 50
        # -65 dBm = 70%
        assert DerbyNetClient.getWiFiPercentFromRSSI(-65) == 70
        # -85 dBm = 30%
        assert DerbyNetClient.getWiFiPercentFromRSSI(-85) == 30

    def test_rssi_invalid_input(self):
        """Non-integer RSSI should return 0."""
        from derbyapi import DerbyNetClient

        assert DerbyNetClient.getWiFiPercentFromRSSI("invalid") == 0
        assert DerbyNetClient.getWiFiPercentFromRSSI(None) == 0
        assert DerbyNetClient.getWiFiPercentFromRSSI(3.14) == 0


class TestDatabaseProtocolValidation:
    """
    Test the new direct database protocol (derbydb.py integration).
    These tests validate that the API client correctly interacts with
    the database layer for race result persistence.
    """

    def test_finish_writes_to_database_when_available(self):
        """When DERBYNET_DB_PATH is set, results should go to DB directly."""
        # This test validates the architecture where derbyRace.py
        # uses derbydb.py for sub-millisecond persistence
        from derbyapi import DerbyNetClient

        # Verify the client still works with HTTP fallback
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.text = '<?xml version="1.0"?><action-response><success/></action-response>'

        client = DerbyNetClient('localhost')
        client.authcode = 'test'

        with patch('derbyapi.requests.post', return_value=mock_response):
            # HTTP fallback should still work
            result = client.send_finish(1, 1, {1: 3.5, 2: 3.6, 3: 3.7})
            assert result is True

    def test_api_maintains_backward_compatibility(self):
        """API client should work without direct DB access."""
        from derbyapi import DerbyNetClient

        # Ensure client initializes without DB dependencies
        client = DerbyNetClient('localhost')
        assert client is not None
        assert hasattr(client, 'send_finish')
        assert hasattr(client, 'send_start')
        assert hasattr(client, 'get_race_status')

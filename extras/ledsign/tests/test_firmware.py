"""
Integration Tests for LED Sign Main Firmware

Tests state management, message handling, WiFi/MQTT behavior,
and display logic.
"""

import pytest
import sys
import os
import json
from unittest.mock import Mock, MagicMock, patch

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def firmware_module():
    """Import the main firmware module with mocked dependencies"""
    # The conftest.py already installs MicroPython mocks
    import main
    return main


@pytest.fixture
def reset_firmware_state(firmware_module):
    """Reset firmware global state before each test"""
    firmware_module.device_state = firmware_module.STATE_UNCONFIGURED
    firmware_module.assigned_zone = None
    firmware_module.zone_display_name = None
    firmware_module.priority_active = False
    firmware_module.priority_expires = 0
    firmware_module.current_message = None
    firmware_module.current_config = None
    firmware_module.mac_address = "AA:BB:CC:DD:EE:FF"
    firmware_module.device_id = "AABBCCDDEEFF"
    yield
    # Cleanup after test


# =============================================================================
# State Management Tests
# =============================================================================

class TestDeviceStates:
    """Test device state constants and transitions"""

    def test_state_constants_defined(self, firmware_module):
        """Verify state constants are defined"""
        assert firmware_module.STATE_UNCONFIGURED == 'UNCONFIGURED'
        assert firmware_module.STATE_CONFIGURED == 'CONFIGURED'
        assert firmware_module.STATE_OFFLINE == 'OFFLINE'

    def test_initial_state_is_unconfigured(self, firmware_module):
        """Device should start in unconfigured state"""
        # Reset to initial
        firmware_module.device_state = firmware_module.STATE_UNCONFIGURED
        assert firmware_module.device_state == firmware_module.STATE_UNCONFIGURED

    def test_state_transition_to_configured(self, firmware_module, reset_firmware_state):
        """State should transition to configured when zone is assigned"""
        # Simulate config message
        payload = {"zone": "starter", "display_name": "Start Line"}

        # Mock the sign and mqtt_client
        firmware_module.sign = MagicMock()
        firmware_module.mqtt_client = MagicMock()

        firmware_module.handle_config_message(payload)

        assert firmware_module.device_state == firmware_module.STATE_CONFIGURED
        assert firmware_module.assigned_zone == "starter"
        assert firmware_module.zone_display_name == "Start Line"

    def test_state_transition_to_offline(self, firmware_module, reset_firmware_state):
        """State should transition to offline when connection lost"""
        firmware_module.sign = MagicMock()
        firmware_module.update_display_offline()

        assert firmware_module.device_state == firmware_module.STATE_OFFLINE


# =============================================================================
# Configuration Message Tests
# =============================================================================

class TestConfigMessageHandling:
    """Test zone configuration message handling"""

    def test_config_message_assigns_zone(self, firmware_module, reset_firmware_state):
        """Config message should assign zone"""
        payload = {"zone": "usher-lane1", "display_name": "Lane 1 Usher"}

        firmware_module.sign = MagicMock()
        firmware_module.mqtt_client = MagicMock()

        firmware_module.handle_config_message(payload)

        assert firmware_module.assigned_zone == "usher-lane1"
        assert firmware_module.zone_display_name == "Lane 1 Usher"

    def test_config_message_uses_zone_as_default_display_name(self, firmware_module, reset_firmware_state):
        """Config without display_name should use zone name"""
        payload = {"zone": "finish-lane2"}

        firmware_module.sign = MagicMock()
        firmware_module.mqtt_client = MagicMock()

        firmware_module.handle_config_message(payload)

        assert firmware_module.zone_display_name == "finish-lane2"

    def test_config_message_triggers_zone_subscription(self, firmware_module, reset_firmware_state):
        """Config should trigger subscription to zone topics"""
        payload = {"zone": "starter"}

        firmware_module.sign = MagicMock()
        mqtt_mock = MagicMock()
        firmware_module.mqtt_client = mqtt_mock

        firmware_module.handle_config_message(payload)

        # Should have called subscribe for zone topic
        mqtt_mock.subscribe.assert_called()

    def test_config_message_invalid_payload_ignored(self, firmware_module, reset_firmware_state):
        """Invalid config payload should be ignored"""
        firmware_module.sign = MagicMock()
        firmware_module.mqtt_client = MagicMock()

        initial_state = firmware_module.device_state
        firmware_module.handle_config_message("invalid string")

        # State should be unchanged
        assert firmware_module.device_state == initial_state


# =============================================================================
# Display Message Tests
# =============================================================================

class TestDisplayMessageHandling:
    """Test display message handling"""

    def test_simple_string_message(self, firmware_module, reset_firmware_state):
        """Simple string should be displayed"""
        firmware_module.sign = MagicMock()
        firmware_module.priority_active = False

        firmware_module.handle_display_message("Hello World")

        firmware_module.sign.write_text.assert_called()

    def test_json_message_with_config(self, firmware_module, reset_firmware_state):
        """JSON message with display_config should be applied"""
        payload = {
            "message": "Test Message",
            "priority": 2,
            "display_config": {
                "mode": "hold",
                "color": "green"
            }
        }

        firmware_module.sign = MagicMock()
        firmware_module.priority_active = False

        firmware_module.handle_display_message(payload)

        firmware_module.sign.write_text.assert_called()
        assert firmware_module.current_message == "Test Message"

    def test_priority_message_uses_priority_display(self, firmware_module, reset_firmware_state):
        """Priority message should use write_priority"""
        payload = {
            "message": "URGENT",
            "priority": 1,
            "display_config": {"mode": "flash", "color": "red"}
        }

        firmware_module.sign = MagicMock()

        firmware_module.handle_display_message(payload)

        firmware_module.sign.write_priority.assert_called()
        assert firmware_module.priority_active == True

    def test_normal_message_blocked_during_priority(self, firmware_module, reset_firmware_state):
        """Normal messages should not display during priority"""
        firmware_module.sign = MagicMock()
        firmware_module.priority_active = True

        payload = {
            "message": "Normal Message",
            "priority": 2,
            "display_config": {}
        }

        firmware_module.handle_display_message(payload)

        # Should store message but not display
        assert firmware_module.current_message == "Normal Message"
        firmware_module.sign.write_text.assert_not_called()


# =============================================================================
# Broadcast Message Tests
# =============================================================================

class TestBroadcastMessageHandling:
    """Test emergency broadcast message handling"""

    def test_broadcast_simple_string(self, firmware_module, reset_firmware_state):
        """Simple broadcast string should use priority display"""
        firmware_module.sign = MagicMock()

        firmware_module.handle_broadcast_message("EMERGENCY")

        firmware_module.sign.write_priority.assert_called()
        assert firmware_module.priority_active == True

    def test_broadcast_json_message(self, firmware_module, reset_firmware_state):
        """JSON broadcast should use specified config"""
        payload = {
            "message": "MISSING CHILD",
            "display_config": {
                "mode": "flash",
                "color": "red",
                "charset": "10high"
            }
        }

        firmware_module.sign = MagicMock()

        firmware_module.handle_broadcast_message(payload)

        firmware_module.sign.write_priority.assert_called()
        assert firmware_module.priority_active == True

    def test_broadcast_clear_command(self, firmware_module, reset_firmware_state):
        """Broadcast clear command should cancel priority"""
        firmware_module.sign = MagicMock()
        firmware_module.priority_active = True

        payload = {"clear": True}

        firmware_module.handle_broadcast_message(payload)

        firmware_module.sign.cancel_priority.assert_called()
        assert firmware_module.priority_active == False

    def test_broadcast_no_auto_expire(self, firmware_module, reset_firmware_state):
        """Emergency broadcasts should not auto-expire"""
        firmware_module.sign = MagicMock()

        payload = {"message": "EMERGENCY"}
        firmware_module.handle_broadcast_message(payload)

        assert firmware_module.priority_expires == 0


# =============================================================================
# Priority Timeout Tests
# =============================================================================

class TestPriorityTimeout:
    """Test priority message timeout handling"""

    def test_priority_expires_after_timeout(self, firmware_module, reset_firmware_state):
        """Priority should expire after timeout"""
        firmware_module.sign = MagicMock()
        firmware_module.priority_active = True
        firmware_module.priority_expires = 1  # Already expired

        # Mock get_timestamp to return 2 (after expiry)
        with patch.object(firmware_module, 'get_timestamp', return_value=2):
            firmware_module.check_priority_timeout()

        assert firmware_module.priority_active == False
        firmware_module.sign.cancel_priority.assert_called()

    def test_priority_not_expired_before_timeout(self, firmware_module, reset_firmware_state):
        """Priority should not expire before timeout"""
        firmware_module.sign = MagicMock()
        firmware_module.priority_active = True
        firmware_module.priority_expires = 100

        # Mock get_timestamp to return 50 (before expiry)
        with patch.object(firmware_module, 'get_timestamp', return_value=50):
            firmware_module.check_priority_timeout()

        assert firmware_module.priority_active == True
        firmware_module.sign.cancel_priority.assert_not_called()

    def test_zero_expires_never_auto_expires(self, firmware_module, reset_firmware_state):
        """Priority with expires=0 should never auto-expire"""
        firmware_module.sign = MagicMock()
        firmware_module.priority_active = True
        firmware_module.priority_expires = 0

        with patch.object(firmware_module, 'get_timestamp', return_value=999999):
            firmware_module.check_priority_timeout()

        # Should still be active (emergency broadcasts use expires=0)
        assert firmware_module.priority_active == True


# =============================================================================
# Zone Subscription Tests
# =============================================================================

class TestZoneSubscription:
    """Test zone-specific topic subscriptions"""

    def test_usher_zone_subscribes_to_pinny(self, firmware_module, reset_firmware_state):
        """Usher zones should subscribe to pinny topic"""
        firmware_module.assigned_zone = "usher-lane1"
        mqtt_mock = MagicMock()
        firmware_module.mqtt_client = mqtt_mock

        firmware_module.subscribe_zone_topics()

        # Should subscribe to both zone message and pinny
        calls = [str(c) for c in mqtt_mock.subscribe.call_args_list]
        assert any('pinny' in c for c in calls)

    def test_finish_zone_no_pinny_subscription(self, firmware_module, reset_firmware_state):
        """Finish zones should not subscribe to pinny topic"""
        firmware_module.assigned_zone = "finish-lane1"
        mqtt_mock = MagicMock()
        firmware_module.mqtt_client = mqtt_mock

        firmware_module.subscribe_zone_topics()

        calls = [str(c) for c in mqtt_mock.subscribe.call_args_list]
        # Should only have zone message subscription, no pinny
        assert not any('pinny' in c for c in calls)

    def test_registration_subscribes_to_sponsors(self, firmware_module, reset_firmware_state):
        """Registration zone should subscribe to sponsor rotation"""
        firmware_module.assigned_zone = "registration"
        mqtt_mock = MagicMock()
        firmware_module.mqtt_client = mqtt_mock

        firmware_module.subscribe_zone_topics()

        calls = [str(c) for c in mqtt_mock.subscribe.call_args_list]
        assert any('sponsors' in c for c in calls)

    def test_audience_subscribes_to_sponsors(self, firmware_module, reset_firmware_state):
        """Audience zone should subscribe to sponsor rotation"""
        firmware_module.assigned_zone = "audience"
        mqtt_mock = MagicMock()
        firmware_module.mqtt_client = mqtt_mock

        firmware_module.subscribe_zone_topics()

        calls = [str(c) for c in mqtt_mock.subscribe.call_args_list]
        assert any('sponsors' in c for c in calls)

    def test_starter_no_sponsor_subscription(self, firmware_module, reset_firmware_state):
        """Starter zone should not subscribe to sponsors"""
        firmware_module.assigned_zone = "starter"
        mqtt_mock = MagicMock()
        firmware_module.mqtt_client = mqtt_mock

        firmware_module.subscribe_zone_topics()

        calls = [str(c) for c in mqtt_mock.subscribe.call_args_list]
        assert not any('sponsors' in c for c in calls)


# =============================================================================
# Pinny Message Tests
# =============================================================================

class TestPinnyMessageHandling:
    """Test pinny number message handling for usher signs"""

    def test_pinny_updates_display(self, firmware_module, reset_firmware_state):
        """Pinny message should update usher display"""
        firmware_module.sign = MagicMock()
        firmware_module.priority_active = False

        firmware_module.handle_pinny_message("42")

        assert firmware_module.current_message == "#42"
        firmware_module.sign.write_text.assert_called()

    def test_pinny_blocked_during_priority(self, firmware_module, reset_firmware_state):
        """Pinny updates should not display during priority"""
        firmware_module.sign = MagicMock()
        firmware_module.priority_active = True

        firmware_module.handle_pinny_message("42")

        # Should not call write_text during priority
        firmware_module.sign.write_text.assert_not_called()


# =============================================================================
# Sponsor Rotation Tests
# =============================================================================

class TestSponsorRotation:
    """Test sponsor rotation handling"""

    def test_sponsor_displays_first_message(self, firmware_module, reset_firmware_state):
        """Sponsor rotation should display first sponsor"""
        payload = {
            "sponsors": [
                {
                    "id": "sponsor-001",
                    "message": "Thanks to ACME!",
                    "duration": 15,
                    "display_config": {"mode": "scroll", "color": "rainbow1"}
                }
            ]
        }

        firmware_module.sign = MagicMock()
        firmware_module.priority_active = False
        firmware_module.device_state = firmware_module.STATE_CONFIGURED

        firmware_module.handle_sponsor_rotation(payload)

        assert firmware_module.current_message == "Thanks to ACME!"
        firmware_module.sign.write_text.assert_called()

    def test_sponsor_blocked_during_priority(self, firmware_module, reset_firmware_state):
        """Sponsors should not display during priority"""
        payload = {
            "sponsors": [
                {"id": "sponsor-001", "message": "Sponsor", "duration": 15, "display_config": {}}
            ]
        }

        firmware_module.sign = MagicMock()
        firmware_module.priority_active = True
        firmware_module.device_state = firmware_module.STATE_CONFIGURED

        firmware_module.handle_sponsor_rotation(payload)

        firmware_module.sign.write_text.assert_not_called()

    def test_sponsor_blocked_when_unconfigured(self, firmware_module, reset_firmware_state):
        """Sponsors should not display when unconfigured"""
        payload = {
            "sponsors": [
                {"id": "sponsor-001", "message": "Sponsor", "duration": 15, "display_config": {}}
            ]
        }

        firmware_module.sign = MagicMock()
        firmware_module.priority_active = False
        firmware_module.device_state = firmware_module.STATE_UNCONFIGURED

        firmware_module.handle_sponsor_rotation(payload)

        firmware_module.sign.write_text.assert_not_called()


# =============================================================================
# Zone Ready Display Tests
# =============================================================================

class TestZoneReadyDisplay:
    """Test zone-appropriate ready state displays"""

    def test_starter_shows_ready(self, firmware_module, reset_firmware_state):
        """Starter zone should show READY"""
        firmware_module.sign = MagicMock()
        firmware_module.assigned_zone = "starter"

        firmware_module.show_zone_ready()

        call_args = firmware_module.sign.write_text.call_args
        assert "READY" in call_args[0][0]

    def test_usher_shows_waiting(self, firmware_module, reset_firmware_state):
        """Usher zone should show WAITING"""
        firmware_module.sign = MagicMock()
        firmware_module.assigned_zone = "usher-lane1"

        firmware_module.show_zone_ready()

        call_args = firmware_module.sign.write_text.call_args
        assert "WAITING" in call_args[0][0]

    def test_finish_shows_time_placeholder(self, firmware_module, reset_firmware_state):
        """Finish zone should show time placeholder"""
        firmware_module.sign = MagicMock()
        firmware_module.assigned_zone = "finish-lane2"

        firmware_module.show_zone_ready()

        call_args = firmware_module.sign.write_text.call_args
        assert "--:--.---" in call_args[0][0]

    def test_registration_shows_derbynet(self, firmware_module, reset_firmware_state):
        """Registration zone should show scrolling DERBYNET"""
        firmware_module.sign = MagicMock()
        firmware_module.assigned_zone = "registration"

        firmware_module.show_zone_ready()

        call_args = firmware_module.sign.write_text.call_args
        assert "DERBYNET" in call_args[0][0]

    def test_unconfigured_shows_mac(self, firmware_module, reset_firmware_state):
        """Unconfigured device should show MAC address"""
        firmware_module.sign = MagicMock()
        firmware_module.assigned_zone = None
        firmware_module.mac_address = "AA:BB:CC:DD:EE:FF"

        firmware_module.show_zone_ready()

        # Should fall back to show_unconfigured
        call_args = firmware_module.sign.write_text.call_args
        assert "SETUP:" in call_args[0][0]


# =============================================================================
# MQTT Topic Routing Tests
# =============================================================================

class TestMqttTopicRouting:
    """Test MQTT message routing by topic"""

    def test_config_topic_routes_to_handler(self, firmware_module, reset_firmware_state):
        """Config topic should route to handle_config_message"""
        firmware_module.sign = MagicMock()
        firmware_module.mqtt_client = MagicMock()
        firmware_module.device_id = "AABBCCDDEEFF"

        topic = b"derbynet/ledsign/device/AABBCCDDEEFF/config"
        msg = b'{"zone": "starter"}'

        firmware_module.on_mqtt_message(topic, msg)

        assert firmware_module.assigned_zone == "starter"

    def test_broadcast_topic_routes_to_handler(self, firmware_module, reset_firmware_state):
        """Broadcast topic should route to handle_broadcast_message"""
        firmware_module.sign = MagicMock()

        topic = b"derbynet/ledsign/broadcast"
        msg = b'{"message": "EMERGENCY"}'

        firmware_module.on_mqtt_message(topic, msg)

        assert firmware_module.priority_active == True

    def test_message_topic_routes_to_handler(self, firmware_module, reset_firmware_state):
        """Message topic should route to handle_display_message"""
        firmware_module.sign = MagicMock()
        firmware_module.assigned_zone = "starter"
        firmware_module.priority_active = False

        topic = b"derbynet/ledsign/device/AABBCCDDEEFF/message"
        msg = b'{"message": "Test", "priority": 2, "display_config": {}}'

        firmware_module.on_mqtt_message(topic, msg)

        assert firmware_module.current_message == "Test"

    def test_pinny_topic_routes_to_handler(self, firmware_module, reset_firmware_state):
        """Pinny topic should route to handle_pinny_message"""
        firmware_module.sign = MagicMock()
        firmware_module.priority_active = False

        topic = b"derbynet/lane/1/pinny"
        msg = b"42"

        firmware_module.on_mqtt_message(topic, msg)

        assert firmware_module.current_message == "#42"


# =============================================================================
# Utility Function Tests
# =============================================================================

class TestUtilityFunctions:
    """Test utility functions"""

    def test_get_mac_short_removes_colons(self, firmware_module, reset_firmware_state):
        """get_mac_short should return MAC without colons"""
        firmware_module.mac_address = "AA:BB:CC:DD:EE:FF"

        result = firmware_module.get_mac_short()

        assert result == "AABBCCDDEEFF"
        assert ":" not in result

    def test_exponential_backoff_increases(self, firmware_module):
        """Exponential backoff should increase with attempts"""
        b0 = firmware_module.exponential_backoff(0)
        b1 = firmware_module.exponential_backoff(1)
        b2 = firmware_module.exponential_backoff(2)

        assert b0 < b1 < b2

    def test_exponential_backoff_capped(self, firmware_module):
        """Exponential backoff should be capped at MAX_BACKOFF"""
        from config import MAX_BACKOFF

        result = firmware_module.exponential_backoff(100)

        assert result == MAX_BACKOFF


# =============================================================================
# Identity and Telemetry Tests
# =============================================================================

class TestIdentityPublishing:
    """Test identity message publishing"""

    def test_identity_contains_required_fields(self, firmware_module, reset_firmware_state):
        """Identity should contain all required fields"""
        firmware_module.wlan = MagicMock()
        firmware_module.wlan.ifconfig.return_value = ('192.168.100.150', '', '', '')
        mqtt_mock = MagicMock()
        firmware_module.mqtt_client = mqtt_mock
        firmware_module.mac_address = "AA:BB:CC:DD:EE:FF"
        firmware_module.device_id = "AABBCCDDEEFF"
        firmware_module.device_state = firmware_module.STATE_CONFIGURED
        firmware_module.assigned_zone = "starter"
        firmware_module.zone_display_name = "Start Line"

        firmware_module.publish_identity()

        # Get the published JSON
        call_args = mqtt_mock.publish.call_args
        topic = call_args[0][0]
        payload = json.loads(call_args[0][1])

        assert 'mac' in payload
        assert 'ip' in payload
        assert 'version' in payload
        assert 'configured' in payload
        assert 'zone' in payload


class TestTelemetryPublishing:
    """Test telemetry message publishing"""

    def test_telemetry_contains_health_metrics(self, firmware_module, reset_firmware_state):
        """Telemetry should contain health metrics"""
        firmware_module.wlan = MagicMock()
        firmware_module.wlan.ifconfig.return_value = ('192.168.100.150', '', '', '')
        firmware_module.wlan.status.return_value = -65
        mqtt_mock = MagicMock()
        firmware_module.mqtt_client = mqtt_mock
        firmware_module.mac_address = "AA:BB:CC:DD:EE:FF"
        firmware_module.device_id = "AABBCCDDEEFF"

        firmware_module.publish_telemetry()

        call_args = mqtt_mock.publish.call_args
        payload = json.loads(call_args[0][1])

        assert 'uptime' in payload
        assert 'wifi_rssi' in payload
        assert 'memory_free' in payload
        assert 'state' in payload

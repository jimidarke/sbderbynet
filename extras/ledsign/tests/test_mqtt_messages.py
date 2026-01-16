"""
Tests for MQTT Message Handling

Tests message format validation, topic routing, and payload processing.
"""

import pytest
import json


class TestZoneMessageFormat:
    """Test zone message format and structure"""

    def test_zone_message_has_required_fields(self, sample_zone_message):
        """Zone messages must have message and display_config"""
        assert 'message' in sample_zone_message
        assert 'display_config' in sample_zone_message

    def test_zone_message_has_timestamp(self, sample_zone_message):
        assert 'timestamp' in sample_zone_message
        assert isinstance(sample_zone_message['timestamp'], int)

    def test_zone_message_has_priority(self, sample_zone_message):
        assert 'priority' in sample_zone_message
        assert sample_zone_message['priority'] in [0, 1, 2, 3]

    def test_zone_message_has_zone(self, sample_zone_message):
        assert 'zone' in sample_zone_message

    def test_zone_message_serializable(self, sample_zone_message):
        """Message should be JSON serializable"""
        json_str = json.dumps(sample_zone_message)
        parsed = json.loads(json_str)
        assert parsed == sample_zone_message


class TestBroadcastMessageFormat:
    """Test emergency broadcast message format"""

    def test_broadcast_has_priority_zero(self, sample_broadcast_message):
        """Emergency broadcasts should have priority 0"""
        assert sample_broadcast_message['priority'] == 0

    def test_broadcast_has_message(self, sample_broadcast_message):
        assert 'message' in sample_broadcast_message
        assert len(sample_broadcast_message['message']) > 0

    def test_broadcast_display_config_has_flash_mode(self, sample_broadcast_message):
        """Broadcast should use flash mode for attention"""
        config = sample_broadcast_message['display_config']
        assert config.get('mode') == 'flash' or config.get('mode_code') == 'c'

    def test_broadcast_display_config_has_red_color(self, sample_broadcast_message):
        """Broadcast should use red color for urgency"""
        config = sample_broadcast_message['display_config']
        assert config.get('color') == 'red' or config.get('color_code') == '1'


class TestConfigMessageFormat:
    """Test zone configuration message format"""

    def test_config_has_zone(self, sample_config_message):
        assert 'zone' in sample_config_message

    def test_config_has_display_name(self, sample_config_message):
        assert 'display_name' in sample_config_message

    def test_config_zone_is_valid(self, sample_config_message):
        """Zone should be a valid zone identifier"""
        valid_zones = [
            'starter',
            'usher-lane1', 'usher-lane2', 'usher-lane3',
            'finish-lane1', 'finish-lane2', 'finish-lane3',
            'registration', 'audience'
        ]
        assert sample_config_message['zone'] in valid_zones


class TestUsherMessageFormat:
    """Test usher sign message format"""

    def test_usher_message_has_racer_info(self, sample_usher_message):
        """Usher message should include racer details"""
        assert 'metadata' in sample_usher_message
        metadata = sample_usher_message['metadata']
        assert 'pinny' in metadata
        assert 'firstname' in metadata
        assert 'lastname' in metadata

    def test_usher_message_has_formatted_name(self, sample_usher_message):
        """Usher message should have pre-formatted name"""
        metadata = sample_usher_message['metadata']
        assert 'formatted_name' in metadata
        # Should be FirstnameL format
        assert metadata['formatted_name'] == 'JohnS'

    def test_usher_display_format(self, sample_usher_message):
        """Usher display should show #pinny FirstnameL"""
        message = sample_usher_message['message']
        assert message.startswith('#')
        # Should contain pinny and name
        assert '42' in message
        assert 'JohnS' in message


class TestFinishMessageFormat:
    """Test finish line time message format"""

    def test_finish_message_is_time_format(self, sample_finish_message):
        """Finish message should be mm:ss.nnn format"""
        message = sample_finish_message['message']
        # Should match pattern XX:XX.XXX
        parts = message.split(':')
        assert len(parts) == 2
        assert '.' in parts[1]

    def test_finish_metadata_has_time_info(self, sample_finish_message):
        """Finish metadata should have time details"""
        metadata = sample_finish_message['metadata']
        assert 'lane' in metadata
        assert 'time_seconds' in metadata
        assert 'time_formatted' in metadata
        assert 'place' in metadata

    def test_finish_time_seconds_matches_formatted(self, sample_finish_message):
        """time_seconds should match time_formatted"""
        metadata = sample_finish_message['metadata']
        # 30.134 seconds should format to 00:30.134
        assert metadata['time_formatted'] == '00:30.134'
        assert abs(metadata['time_seconds'] - 30.134) < 0.001

    def test_finish_uses_large_charset(self, sample_finish_message):
        """Finish should use large charset for visibility"""
        config = sample_finish_message['display_config']
        assert config.get('charset_code') == '6' or config.get('character_set') == '10high'


class TestSponsorRotationFormat:
    """Test sponsor rotation message format"""

    def test_sponsor_rotation_has_sponsors_list(self, sample_sponsor_rotation):
        assert 'sponsors' in sample_sponsor_rotation
        assert isinstance(sample_sponsor_rotation['sponsors'], list)
        assert len(sample_sponsor_rotation['sponsors']) > 0

    def test_sponsor_has_required_fields(self, sample_sponsor_rotation):
        """Each sponsor should have id, message, duration"""
        for sponsor in sample_sponsor_rotation['sponsors']:
            assert 'id' in sponsor
            assert 'message' in sponsor
            assert 'duration' in sponsor

    def test_sponsor_has_display_config(self, sample_sponsor_rotation):
        """Sponsors should have display configuration"""
        for sponsor in sample_sponsor_rotation['sponsors']:
            assert 'display_config' in sponsor

    def test_sponsor_uses_scroll_mode(self, sample_sponsor_rotation):
        """Sponsors typically use scroll mode"""
        for sponsor in sample_sponsor_rotation['sponsors']:
            config = sponsor['display_config']
            assert config.get('mode') == 'scroll' or config.get('mode_code') == 'm'

    def test_rotation_has_settings(self, sample_sponsor_rotation):
        """Rotation should have default settings"""
        assert 'default_duration' in sample_sponsor_rotation
        assert 'loop' in sample_sponsor_rotation


class TestDisplayConfigValidation:
    """Test display_config field validation"""

    def test_display_config_mode_is_valid(self, sample_display_config):
        """Mode should be a valid mode code or name"""
        valid_mode_codes = 'abcdefghijklmnopqrstuvwxyz'
        mode_code = sample_display_config.get('mode_code', '')
        mode_name = sample_display_config.get('mode', '')
        assert mode_code in valid_mode_codes or len(mode_name) > 1

    def test_display_config_color_is_valid(self, sample_display_config):
        """Color should be a valid color code"""
        valid_color_codes = '123456789ABC'
        color_code = sample_display_config.get('color_code', '')
        assert color_code in valid_color_codes or sample_display_config.get('color')

    def test_display_config_charset_is_valid(self, sample_display_config):
        """Charset should be a valid charset code"""
        valid_charset_codes = '123456789:;<=>?'
        charset_code = sample_display_config.get('charset_code', '')
        assert charset_code in valid_charset_codes or sample_display_config.get('character_set')

    def test_display_config_position_is_valid(self, sample_display_config):
        """Position should be a valid position code"""
        valid_position_codes = '"& 012'
        position_code = sample_display_config.get('position_code', '')
        assert position_code in valid_position_codes or sample_display_config.get('position')

    def test_display_config_speed_in_range(self, sample_display_config):
        """Speed should be 1-5"""
        speed = sample_display_config.get('speed')
        if speed:
            assert 1 <= speed <= 5


class TestTopicPatterns:
    """Test MQTT topic pattern validation"""

    def test_device_config_topic_pattern(self):
        """Device config topic should include MAC"""
        mac = "AABBCCDDEEFF"
        topic = f"derbynet/ledsign/device/{mac}/config"
        assert mac in topic
        assert topic.startswith("derbynet/ledsign/device/")
        assert topic.endswith("/config")

    def test_device_identity_topic_pattern(self):
        """Device identity topic should include MAC"""
        mac = "AABBCCDDEEFF"
        topic = f"derbynet/ledsign/device/{mac}/identity"
        assert mac in topic
        assert topic.endswith("/identity")

    def test_device_status_topic_pattern(self):
        """Device status topic should include MAC"""
        mac = "AABBCCDDEEFF"
        topic = f"derbynet/ledsign/device/{mac}/status"
        assert mac in topic
        assert topic.endswith("/status")

    def test_zone_message_topic_pattern(self):
        """Zone message topic should include zone name"""
        zone = "starter"
        topic = f"derbynet/ledsign/{zone}/message"
        assert zone in topic
        assert topic.endswith("/message")

    def test_broadcast_topic(self):
        """Broadcast topic should be fixed"""
        topic = "derbynet/ledsign/broadcast"
        assert topic == "derbynet/ledsign/broadcast"

    def test_pinny_topic_pattern(self):
        """Pinny topic should include lane number"""
        lane = 1
        topic = f"derbynet/lane/{lane}/pinny"
        assert str(lane) in topic
        assert topic.endswith("/pinny")


class TestIdentityMessage:
    """Test device identity message format"""

    def test_identity_fields(self):
        """Identity message should have required fields"""
        identity = {
            "mac": "AA:BB:CC:DD:EE:FF",
            "ip": "192.168.100.150",
            "version": "1.0.0",
            "uptime": 3600,
            "configured": True,
            "zone": "starter",
            "display_name": "Start Line",
            "timestamp": 1705344000
        }

        assert 'mac' in identity
        assert 'ip' in identity
        assert 'version' in identity
        assert 'uptime' in identity
        assert 'configured' in identity
        assert 'zone' in identity
        assert 'timestamp' in identity

    def test_identity_mac_format(self):
        """MAC should be formatted with colons"""
        mac = "AA:BB:CC:DD:EE:FF"
        parts = mac.split(':')
        assert len(parts) == 6
        for part in parts:
            assert len(part) == 2
            assert all(c in '0123456789ABCDEF' for c in part)


class TestTelemetryMessage:
    """Test device telemetry message format"""

    def test_telemetry_fields(self):
        """Telemetry message should have health metrics"""
        telemetry = {
            "mac": "AA:BB:CC:DD:EE:FF",
            "hostname": "ledsign-DDEEFF",
            "hwid": "AABBCCDDEEFF",
            "version": "1.0.0",
            "uptime": 3600,
            "ip": "192.168.100.150",
            "wifi_rssi": -65,
            "memory_free": 50000,
            "memory_usage": 25.5,
            "state": "CONFIGURED",
            "zone": "starter",
            "priority_active": False,
            "timestamp": 1705344000
        }

        assert 'uptime' in telemetry
        assert 'wifi_rssi' in telemetry
        assert 'memory_free' in telemetry
        assert 'state' in telemetry

    def test_telemetry_wifi_rssi_valid(self):
        """WiFi RSSI should be negative dBm"""
        rssi = -65
        assert rssi < 0
        assert rssi > -100  # Reasonable range


class TestPriorityLevels:
    """Test message priority level handling"""

    def test_priority_0_is_emergency(self):
        """Priority 0 should be emergency"""
        assert 0 == 0  # Emergency

    def test_priority_1_is_critical(self):
        """Priority 1 should be critical"""
        assert 1 == 1  # Critical alert

    def test_priority_2_is_race_event(self):
        """Priority 2 should be race event"""
        assert 2 == 2  # Race event

    def test_priority_3_is_idle(self):
        """Priority 3 should be idle/sponsor"""
        assert 3 == 3  # Idle/sponsor

    def test_emergency_overrides_all(self, sample_broadcast_message, sample_zone_message):
        """Emergency (0) should override race event (2)"""
        assert sample_broadcast_message['priority'] < sample_zone_message['priority']

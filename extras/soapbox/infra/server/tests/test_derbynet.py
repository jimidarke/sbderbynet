"""
Tests for DerbyNet Shared Network Library (derbynet.py)

This module tests the MQTT communication layer, message queuing for offline
operation, device telemetry collection, and network diagnostics.

Test Categories:
- MessageQueue persistence and recovery
- MQTTClient connection management
- DeviceTelemetry collection
- Network diagnostics
"""

import pytest
import json
import time
import os
import tempfile
import threading
from unittest.mock import Mock, MagicMock, patch, PropertyMock


class TestMessageQueuePersistence:
    """Test MessageQueue offline message handling."""

    @pytest.fixture
    def temp_queue_dir(self):
        """Create temporary directory for queue storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_queue_creates_directory(self, temp_queue_dir):
        """Queue should create storage directory if it doesn't exist."""
        from derbynet import MessageQueue

        queue_path = os.path.join(temp_queue_dir, 'subdir', 'queue')
        queue = MessageQueue(queue_dir=queue_path)

        assert os.path.exists(queue_path)

    def test_queue_put_creates_file(self, temp_queue_dir):
        """Queued messages should be persisted to disk."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)
        queue.put('test/topic', '{"test": "data"}', qos=1)

        # Check file was created
        files = os.listdir(temp_queue_dir)
        assert len(files) == 1
        assert files[0].endswith('.json')

    def test_queue_message_format(self, temp_queue_dir):
        """Persisted messages should have correct format."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)
        queue.put('derbynet/test', 'payload_data', qos=2, retain=True)

        # Read the persisted file
        files = os.listdir(temp_queue_dir)
        with open(os.path.join(temp_queue_dir, files[0]), 'r') as f:
            message = json.load(f)

        assert message['topic'] == 'derbynet/test'
        assert message['payload'] == 'payload_data'
        assert message['qos'] == 2
        assert message['retain'] is True
        assert 'id' in message
        assert 'timestamp' in message

    def test_queue_load_from_disk(self, temp_queue_dir):
        """Queue should load existing messages on initialization."""
        from derbynet import MessageQueue

        # Create a message file manually
        message = {
            "id": "test-uuid-123",
            "timestamp": "2025-01-01T00:00:00",
            "topic": "restored/topic",
            "payload": "restored_payload",
            "qos": 1,
            "retain": False
        }
        with open(os.path.join(temp_queue_dir, 'test-uuid-123.json'), 'w') as f:
            json.dump(message, f)

        # Initialize queue - should load the message
        queue = MessageQueue(queue_dir=temp_queue_dir)

        assert queue.size() == 1
        restored = queue.get(block=False)
        assert restored['topic'] == 'restored/topic'

    def test_queue_task_done_removes_file(self, temp_queue_dir):
        """Completing a message should remove its persistence file."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)
        queue.put('test/topic', 'data')

        # Get the message ID from file
        files = os.listdir(temp_queue_dir)
        message_id = files[0].replace('.json', '')

        # Complete the task
        queue.get(block=False)
        queue.task_done(message_id)

        # File should be removed
        assert len(os.listdir(temp_queue_dir)) == 0

    def test_queue_size_tracking(self, temp_queue_dir):
        """Queue size should be tracked correctly."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)

        assert queue.size() == 0

        queue.put('topic1', 'data1')
        assert queue.size() == 1

        queue.put('topic2', 'data2')
        assert queue.size() == 2

        queue.get(block=False)
        assert queue.size() == 1


class TestMQTTClientConnection:
    """Test MQTTClient connection management."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, temp_queue_dir):
        """Set up mocks for all tests in this class."""
        # Patch MessageQueue before MQTTClient is imported
        self.temp_queue_dir = temp_queue_dir

        with patch('derbynet.mqtt.Client') as MockClient:
            self.mock_paho_client = MagicMock()
            MockClient.return_value = self.mock_paho_client

            with patch('derbynet.MessageQueue') as MockQueue:
                self.mock_queue = MagicMock()
                self.mock_queue.size.return_value = 0
                MockQueue.return_value = self.mock_queue
                yield

    @pytest.fixture
    def temp_queue_dir(self):
        """Create temporary directory for queue storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @property
    def mock_paho_client(self):
        return self._mock_paho_client

    @mock_paho_client.setter
    def mock_paho_client(self, value):
        self._mock_paho_client = value

    @property
    def mock_queue(self):
        return self._mock_queue

    @mock_queue.setter
    def mock_queue(self, value):
        self._mock_queue = value

    def test_client_initialization(self):
        """Client should initialize with correct defaults."""
        from derbynet import MQTTClient, DEFAULT_MQTT_BROKER, DEFAULT_MQTT_PORT

        client = MQTTClient('test-device')

        assert client.client_id == 'test-device'
        assert client.broker == DEFAULT_MQTT_BROKER
        assert client.port == DEFAULT_MQTT_PORT
        assert client.connected is False

    def test_client_custom_broker(self):
        """Client should accept custom broker settings."""
        from derbynet import MQTTClient

        client = MQTTClient('test', broker='mqtt.example.com', port=8883)

        assert client.broker == 'mqtt.example.com'
        assert client.port == 8883

    def test_client_env_var_configuration(self):
        """Client should use environment variables for broker config."""
        with patch.dict('os.environ', {
            'MQTT_BROKER': '10.0.0.100',
            'MQTT_PORT': '1884'
        }):
            # Re-import to pick up env vars
            import importlib
            import derbynet
            importlib.reload(derbynet)

            assert derbynet.DEFAULT_MQTT_BROKER == '10.0.0.100'
            assert derbynet.DEFAULT_MQTT_PORT == 1884

    def test_publish_when_connected(self):
        """Publishing when connected should send immediately."""
        from derbynet import MQTTClient

        # Set up mock publish result
        mock_result = MagicMock()
        mock_result.rc = 0  # MQTT_ERR_SUCCESS
        self.mock_paho_client.publish.return_value = mock_result

        client = MQTTClient('test')
        client.connected = True
        client.client = self.mock_paho_client

        result = client.publish('test/topic', 'message')

        assert result is True
        self.mock_paho_client.publish.assert_called_once()

    def test_publish_when_disconnected_queues(self):
        """Publishing when disconnected should queue the message."""
        from derbynet import MQTTClient

        client = MQTTClient('test')
        client.connected = False
        client.message_queue = self.mock_queue

        result = client.publish('test/topic', 'message')

        assert result is False
        self.mock_queue.put.assert_called_once()

    def test_publish_json_serialization(self):
        """Dict payloads should be JSON serialized."""
        from derbynet import MQTTClient

        mock_result = MagicMock()
        mock_result.rc = 0
        self.mock_paho_client.publish.return_value = mock_result

        client = MQTTClient('test')
        client.connected = True
        client.client = self.mock_paho_client

        payload = {"lane": 1, "time": 3.456}
        client.publish('test/topic', payload)

        call_args = self.mock_paho_client.publish.call_args
        sent_payload = call_args[0][1]
        assert json.loads(sent_payload) == payload

    def test_subscribe_registers_callback(self):
        """Subscribing should register the callback."""
        from derbynet import MQTTClient

        client = MQTTClient('test')
        client.connected = True
        client.client = self.mock_paho_client

        callback = Mock()
        client.subscribe('test/topic/#', callback)

        assert 'test/topic/#' in client.subscriptions
        assert client.subscriptions['test/topic/#'] == callback

    def test_on_connect_resubscribes(self):
        """Reconnection should resubscribe to topics."""
        from derbynet import MQTTClient

        client = MQTTClient('test')
        client.client = self.mock_paho_client
        client.subscriptions = {
            'topic1': Mock(),
            'topic2': Mock()
        }

        # Simulate successful connection
        client._on_connect(self.mock_paho_client, None, None, 0)

        assert client.connected is True
        assert self.mock_paho_client.subscribe.call_count == 2

    def test_on_disconnect_sets_flag(self):
        """Disconnection should update connected flag."""
        from derbynet import MQTTClient

        client = MQTTClient('test')
        client.connected = True

        client._on_disconnect(self.mock_paho_client, None, 1)

        assert client.connected is False

    def test_on_message_dispatches_to_callback(self):
        """Incoming messages should be dispatched to correct callback."""
        from derbynet import MQTTClient

        client = MQTTClient('test')
        callback = Mock()
        client.subscriptions = {'derbynet/lane/+/state': callback}

        # Create mock message
        mock_msg = MagicMock()
        mock_msg.topic = 'derbynet/lane/1/state'
        mock_msg.payload = b'{"toggle": true}'

        with patch('derbynet.mqtt.topic_matches_sub', return_value=True):
            client._on_message(self.mock_paho_client, None, mock_msg)

        callback.assert_called_once()
        call_args = callback.call_args[0]
        assert call_args[0] == 'derbynet/lane/1/state'
        assert call_args[1] == {'toggle': True}


class TestDeviceTelemetry:
    """Test device telemetry collection."""

    def test_telemetry_basic_fields(self):
        """Telemetry should include required fields."""
        from derbynet import DeviceTelemetry

        telemetry = DeviceTelemetry('FINISH1', 'finish_timer')
        data = telemetry.collect()

        assert 'hostname' in data
        assert 'hwid' in data
        assert data['hwid'] == 'FINISH1'
        assert data['device_type'] == 'finish_timer'
        assert 'uptime' in data
        assert 'timestamp' in data
        assert 'cpu_usage' in data
        assert 'memory_usage' in data
        assert 'disk' in data
        assert 'network' in data

    def test_telemetry_uptime_increases(self):
        """Uptime should increase over time."""
        from derbynet import DeviceTelemetry

        telemetry = DeviceTelemetry('TEST', 'test')
        data1 = telemetry.collect()

        time.sleep(0.1)  # Brief delay

        data2 = telemetry.collect()

        # Uptime should have increased (or stayed same if sub-second)
        assert data2['uptime'] >= data1['uptime']

    def test_telemetry_memory_structure(self):
        """Memory telemetry should have correct structure."""
        from derbynet import DeviceTelemetry

        telemetry = DeviceTelemetry('TEST', 'test')
        data = telemetry.collect()

        mem = data['memory_usage']
        assert 'total' in mem
        assert 'used' in mem
        assert 'percent' in mem
        assert isinstance(mem['percent'], float)

    def test_telemetry_disk_structure(self):
        """Disk telemetry should have correct structure."""
        from derbynet import DeviceTelemetry

        telemetry = DeviceTelemetry('TEST', 'test')
        data = telemetry.collect()

        disk = data['disk']
        assert 'total' in disk
        assert 'used' in disk
        assert 'percent' in disk

    def test_telemetry_cpu_temp_raspberry_pi(self):
        """CPU temp should be read on Raspberry Pi."""
        from derbynet import DeviceTelemetry

        telemetry = DeviceTelemetry('TEST', 'test')

        # Mock the thermal zone file
        with patch('builtins.open', MagicMock(return_value=MagicMock(
            __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value='45000'))),
            __exit__=MagicMock(return_value=False)
        ))):
            with patch('os.path.exists', return_value=True):
                temp = telemetry._get_cpu_temperature()
                assert temp == 45.0

    def test_telemetry_cpu_temp_unavailable(self):
        """CPU temp should be None when unavailable."""
        from derbynet import DeviceTelemetry

        telemetry = DeviceTelemetry('TEST', 'test')

        with patch('os.path.exists', return_value=False):
            temp = telemetry._get_cpu_temperature()
            assert temp is None


class TestNetworkDiagnostics:
    """Test network diagnostic utilities."""

    def test_diagnostics_returns_structure(self):
        """Diagnostics should return expected structure."""
        from derbynet import network_diagnostics

        with patch('socket.create_connection') as mock_conn:
            mock_conn.return_value = MagicMock()
            with patch('socket.gethostbyname', return_value='8.8.8.8'):
                results = network_diagnostics()

        assert 'connectivity' in results
        assert 'latency' in results
        assert 'dns' in results

    def test_diagnostics_connectivity_check(self):
        """Connectivity checks should test broker and external hosts."""
        from derbynet import network_diagnostics, DEFAULT_MQTT_BROKER

        with patch('socket.create_connection') as mock_conn:
            mock_conn.return_value = MagicMock()
            with patch('socket.gethostbyname', return_value='8.8.8.8'):
                results = network_diagnostics()

        # Should check both broker and external IP
        assert DEFAULT_MQTT_BROKER in results['connectivity']
        assert '8.8.8.8' in results['connectivity']

    def test_diagnostics_handles_failures(self):
        """Failed connectivity should be recorded as False."""
        from derbynet import network_diagnostics

        with patch('socket.create_connection') as mock_conn:
            mock_conn.side_effect = Exception("Connection failed")
            with patch('socket.gethostbyname') as mock_dns:
                mock_dns.side_effect = Exception("DNS failed")
                results = network_diagnostics()

        # All checks should show failure
        for host, status in results['connectivity'].items():
            assert status is False
        for domain, status in results['dns'].items():
            assert status is False

    def test_service_discovery_disabled(self):
        """Service discovery should return empty dict (disabled)."""
        from derbynet import discover_services

        result = discover_services()

        assert result == {}


class TestRetryLogic:
    """Test connection retry with exponential backoff."""

    def test_retry_delay_increases(self):
        """Retry delay should increase with exponential backoff."""
        from derbynet import (INITIAL_RETRY_DELAY, MAX_RETRY_DELAY,
                              RETRY_BACKOFF_FACTOR)

        delay = INITIAL_RETRY_DELAY
        delays = [delay]

        for _ in range(10):
            delay = min(delay * RETRY_BACKOFF_FACTOR, MAX_RETRY_DELAY)
            delays.append(delay)

        # Delays should increase
        assert delays[1] > delays[0]
        assert delays[5] > delays[1]

        # Should cap at MAX_RETRY_DELAY
        assert delays[-1] <= MAX_RETRY_DELAY

    def test_initial_retry_delay(self):
        """Initial retry delay should be 1 second."""
        from derbynet import INITIAL_RETRY_DELAY

        assert INITIAL_RETRY_DELAY == 1.0

    def test_max_retry_delay(self):
        """Max retry delay should be 5 minutes."""
        from derbynet import MAX_RETRY_DELAY

        assert MAX_RETRY_DELAY == 300.0


class TestMQTTTopicMatching:
    """Test MQTT topic wildcard matching for subscriptions."""

    def test_wildcard_plus_matches(self):
        """+ wildcard should match single level."""
        import paho.mqtt.client as mqtt

        assert mqtt.topic_matches_sub('derbynet/lane/+/state', 'derbynet/lane/1/state')
        assert mqtt.topic_matches_sub('derbynet/lane/+/state', 'derbynet/lane/2/state')
        assert not mqtt.topic_matches_sub('derbynet/lane/+/state', 'derbynet/lane/1/2/state')

    def test_wildcard_hash_matches(self):
        """# wildcard should match multiple levels."""
        import paho.mqtt.client as mqtt

        assert mqtt.topic_matches_sub('derbynet/#', 'derbynet/lane/1/state')
        assert mqtt.topic_matches_sub('derbynet/#', 'derbynet/device/ABC/telemetry')
        assert mqtt.topic_matches_sub('derbynet/lane/#', 'derbynet/lane/1/led')

    def test_exact_match(self):
        """Exact topics should match exactly."""
        import paho.mqtt.client as mqtt

        assert mqtt.topic_matches_sub('derbynet/race/state', 'derbynet/race/state')
        assert not mqtt.topic_matches_sub('derbynet/race/state', 'derbynet/race/status')

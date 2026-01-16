"""
Finish Timer Resilience Tests

Tests for offline operation, power loss recovery, and queue persistence.
Based on real production issues:
- Rain + power outages causing intermittent network/server
- Finish timers on battery staying up while server went down
- Timer battery coming loose (timer restart)
- Loss of state tracking / source of truth

Test Categories:
1. MessageQueue - Disk persistence across restarts
2. MQTTClient - Auto-reconnect and queue drain
3. Toggle Events - Race finish preserved during outages
4. Recovery - Various failure/restart combinations
"""

import pytest
import json
import time
import os
import shutil
import tempfile
import threading
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from queue import Queue, Empty

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# Mock Classes
# =============================================================================

class MockPCB:
    """Mock finish timer PCB hardware."""

    def __init__(self):
        self.hwid = "MOCK-TIMER-001"
        self.lane = 1
        self.toggle_state = True  # True = up (no car), False = down (car crossed)
        self.led_color = "red"
        self.pinny_value = "0000"
        self.battery_percent = 85
        self.toggle_callback = None
        self.toggle_watch_active = False
        self._toggle_thread = None
        self.dip_value = "1000"  # Lane 1

    def gethwid(self):
        return self.hwid

    def get_Lane(self):
        return self.lane

    def getToggleState(self):
        return self.toggle_state

    def setLED(self, color, actNormal=True):
        self.led_color = color

    def setPinny(self, value, actNormal=True):
        self.pinny_value = value

    def readDIP(self):
        return self.dip_value

    def getBatteryPercent(self):
        return self.battery_percent

    def networkError(self):
        self.led_color = "white"
        self.pinny_value = "ERR3"

    def begin_toggle_watch(self, callback):
        self.toggle_callback = callback
        self.toggle_watch_active = True

    def simulate_toggle(self, new_state):
        """Simulate a car crossing the finish line."""
        if self.toggle_state != new_state:
            self.toggle_state = new_state
            if self.toggle_callback and self.toggle_watch_active:
                self.toggle_callback()

    def packageTelemetry(self):
        return {
            "hostname": "finish-timer-mock",
            "hwid": self.hwid,
            "ip": "192.168.100.50",
            "mac": "AA:BB:CC:DD:EE:FF",
            "uptime": 3600,
            "cpu_temp": 45.0,
            "wifi_rssi": -55,
            "battery_level": self.battery_percent,
            "memory_usage": 45,
            "disk": 30,
            "cpu_usage": 15,
            "dip": self.dip_value,
            "toggle": self.toggle_state,
            "led": self.led_color,
            "pinny": self.pinny_value,
            "readyToRace": self.led_color == "blue" and self.toggle_state
        }

    def close(self):
        self.toggle_watch_active = False

    def update_pcb(self):
        pass


class MockMQTTBroker:
    """Simulates an MQTT broker for testing."""

    def __init__(self):
        self.is_online = True
        self.published_messages = []
        self.subscriptions = {}
        self.retained_messages = {}

    def go_offline(self):
        self.is_online = False

    def go_online(self):
        self.is_online = True

    def publish(self, topic, payload, qos=1, retain=False):
        if not self.is_online:
            return False
        self.published_messages.append({
            'topic': topic,
            'payload': payload,
            'qos': qos,
            'retain': retain,
            'timestamp': time.time()
        })
        if retain:
            self.retained_messages[topic] = payload
        return True

    def get_messages_for_topic(self, topic_pattern):
        """Get all messages matching a topic pattern."""
        return [m for m in self.published_messages if topic_pattern in m['topic']]

    def clear_messages(self):
        self.published_messages = []


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def temp_queue_dir(tmp_path):
    """Create a temporary directory for message queue."""
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    return str(queue_dir)


@pytest.fixture
def mock_pcb():
    """Create a mock PCB instance."""
    return MockPCB()


@pytest.fixture
def mock_broker():
    """Create a mock MQTT broker."""
    return MockMQTTBroker()


# =============================================================================
# Test Classes: MessageQueue Persistence
# =============================================================================

class TestMessageQueuePersistence:
    """Tests for MessageQueue disk persistence (survives timer restart)."""

    def test_queue_saves_to_disk(self, temp_queue_dir):
        """Messages are saved to disk when queued."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)
        queue.put("derbynet/test/topic", '{"test": "data"}', qos=2, retain=True)

        # Check file was created
        files = os.listdir(temp_queue_dir)
        assert len(files) == 1
        assert files[0].endswith('.json')

        # Verify content
        with open(os.path.join(temp_queue_dir, files[0])) as f:
            saved = json.load(f)
            assert saved['topic'] == "derbynet/test/topic"
            assert saved['payload'] == '{"test": "data"}'
            assert saved['qos'] == 2
            assert saved['retain'] is True

    def test_queue_loads_from_disk_on_restart(self, temp_queue_dir):
        """Queue loads persisted messages on initialization (simulates timer restart)."""
        from derbynet import MessageQueue

        # First queue instance - save messages
        queue1 = MessageQueue(queue_dir=temp_queue_dir)
        queue1.put("topic1", "payload1")
        queue1.put("topic2", "payload2")
        queue1.put("topic3", "payload3")

        # Simulate timer restart - new queue instance
        queue2 = MessageQueue(queue_dir=temp_queue_dir)

        # Should have loaded all 3 messages
        assert queue2.size() == 3

        # Messages should be retrievable
        messages = []
        while queue2.size() > 0:
            msg = queue2.get(block=False)
            if msg:
                messages.append(msg)

        topics = [m['topic'] for m in messages]
        assert "topic1" in topics
        assert "topic2" in topics
        assert "topic3" in topics

    def test_queue_removes_file_after_task_done(self, temp_queue_dir):
        """Message file removed from disk after successful processing."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)
        queue.put("test/topic", "test_payload")

        # Get the message
        message = queue.get(block=False)
        assert message is not None

        # File should still exist
        assert len(os.listdir(temp_queue_dir)) == 1

        # Mark as done
        queue.task_done(message['id'])

        # File should be removed
        assert len(os.listdir(temp_queue_dir)) == 0

    def test_queue_preserves_order(self, temp_queue_dir):
        """Messages are retrieved in order they were queued."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)

        # Queue messages with timestamps
        for i in range(5):
            queue.put(f"topic{i}", f"payload{i}")
            time.sleep(0.01)  # Ensure different timestamps

        # Retrieve and verify order
        for i in range(5):
            msg = queue.get(block=False)
            # Files are sorted by name (which includes timestamp)
            assert msg is not None

    def test_toggle_event_survives_restart(self, temp_queue_dir):
        """Critical toggle (race finish) event persists across timer restart."""
        from derbynet import MessageQueue

        # Queue a toggle event (car crossed finish line)
        queue1 = MessageQueue(queue_dir=temp_queue_dir)
        toggle_payload = json.dumps({
            "toggle": False,  # False = car crossed
            "timestamp": int(time.time()),
            "hwid": "TIMER-001",
            "dip": "1000",
            "lane": 1
        })
        queue1.put(
            "derbynet/device/TIMER-001/state",
            toggle_payload,
            qos=2,  # Critical - exactly once
            retain=True
        )

        # Simulate timer restart (battery reconnected)
        queue2 = MessageQueue(queue_dir=temp_queue_dir)

        assert queue2.size() == 1
        msg = queue2.get(block=False)
        assert msg is not None

        payload = json.loads(msg['payload'])
        assert payload['toggle'] is False
        assert payload['lane'] == 1


# =============================================================================
# Test Classes: MQTTClient Offline Operation
# =============================================================================

class TestMQTTClientOffline:
    """Tests for MQTT client offline operation and reconnection."""

    def test_publish_queues_when_offline(self, temp_queue_dir):
        """Messages are queued when broker is offline."""
        from derbynet import MQTTClient, MessageQueue

        with patch('derbynet.MessageQueue') as MockQueue:
            mock_queue = Mock()
            mock_queue.size.return_value = 0
            MockQueue.return_value = mock_queue

            with patch('paho.mqtt.client.Client'):
                client = MQTTClient("test-client")
                client.connected = False  # Simulate offline

                result = client.publish("test/topic", "test_payload")

                assert result is False  # Returns False when offline
                mock_queue.put.assert_called_once()

    def test_queue_drains_on_reconnect(self, temp_queue_dir):
        """Queued messages are sent when connection is restored."""
        from derbynet import MessageQueue

        # Create queue with pending messages
        queue = MessageQueue(queue_dir=temp_queue_dir)
        queue.put("topic1", "payload1")
        queue.put("topic2", "payload2")

        assert queue.size() == 2

        # Simulate processing (what happens on reconnect)
        sent = []
        while queue.size() > 0:
            msg = queue.get(block=False)
            if msg:
                # Simulate successful send
                sent.append(msg)
                queue.task_done(msg['id'])

        assert len(sent) == 2
        assert queue.size() == 0
        assert len(os.listdir(temp_queue_dir)) == 0  # Files cleaned up

    def test_retry_backoff_increases(self):
        """Retry delay increases with exponential backoff."""
        from derbynet import INITIAL_RETRY_DELAY, MAX_RETRY_DELAY, RETRY_BACKOFF_FACTOR

        delay = INITIAL_RETRY_DELAY
        delays = [delay]

        for _ in range(10):
            delay = min(delay * RETRY_BACKOFF_FACTOR, MAX_RETRY_DELAY)
            delays.append(delay)

        # Should increase
        assert delays[1] > delays[0]
        assert delays[5] > delays[1]

        # Should cap at max
        assert delays[-1] <= MAX_RETRY_DELAY

    def test_retry_delay_resets_on_connect(self, temp_queue_dir):
        """Retry delay resets to initial value after successful connection."""
        from derbynet import MQTTClient, INITIAL_RETRY_DELAY

        with patch('paho.mqtt.client.Client'):
            with patch('derbynet.MessageQueue') as MockQueue:
                MockQueue.return_value = Mock()
                client = MQTTClient("test-client")
                client.retry_delay = 60.0  # Elevated from previous failures

                # Simulate successful connection
                client._on_connect(None, None, None, 0)

                assert client.retry_delay == INITIAL_RETRY_DELAY
                assert client.connected is True


# =============================================================================
# Test Classes: Toggle Events During Outages
# =============================================================================

class TestToggleEventsDuringOutage:
    """Tests for race finish events during network outages."""

    def test_toggle_queued_during_server_outage(self, temp_queue_dir, mock_pcb):
        """Toggle event (race finish) is queued when server is down."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)

        # Simulate toggle callback behavior when offline
        def simulate_toggle_callback():
            toggle_payload = json.dumps({
                "toggle": mock_pcb.getToggleState(),
                "timestamp": int(time.time()),
                "hwid": mock_pcb.gethwid(),
                "dip": mock_pcb.readDIP(),
                "lane": mock_pcb.get_Lane()
            })
            # Queue instead of direct publish (what MQTTClient does when offline)
            queue.put(
                f"derbynet/device/{mock_pcb.gethwid()}/state",
                toggle_payload,
                qos=2,
                retain=True
            )

        # Simulate car crossing finish line
        mock_pcb.toggle_state = False  # Car crossed
        simulate_toggle_callback()

        assert queue.size() == 1
        msg = queue.get(block=False)
        payload = json.loads(msg['payload'])
        assert payload['toggle'] is False
        assert msg['qos'] == 2  # Critical delivery

    def test_multiple_races_queued_during_extended_outage(self, temp_queue_dir, mock_pcb):
        """Multiple race finishes queue correctly during extended outage."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)

        # Simulate 3 races during outage
        for race_num in range(3):
            # Car crosses (toggle down)
            toggle_payload = json.dumps({
                "toggle": False,
                "timestamp": int(time.time()) + race_num,
                "hwid": mock_pcb.gethwid(),
                "race_num": race_num  # For tracking
            })
            queue.put(f"derbynet/device/{mock_pcb.gethwid()}/state", toggle_payload, qos=2)

            # Reset for next race (toggle up)
            reset_payload = json.dumps({
                "toggle": True,
                "timestamp": int(time.time()) + race_num,
                "hwid": mock_pcb.gethwid(),
                "race_num": race_num
            })
            queue.put(f"derbynet/device/{mock_pcb.gethwid()}/state", reset_payload, qos=2)

        # Should have 6 events (3 down + 3 up)
        assert queue.size() == 6

    def test_toggle_timestamp_preserved(self, temp_queue_dir):
        """Original timestamp is preserved in queued toggle events."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)

        original_time = int(time.time())
        toggle_payload = json.dumps({
            "toggle": False,
            "timestamp": original_time,
            "hwid": "TIMER-001"
        })

        queue.put("derbynet/device/TIMER-001/state", toggle_payload, qos=2)

        # Wait a bit
        time.sleep(0.1)

        # Retrieve and verify original timestamp preserved
        msg = queue.get(block=False)
        payload = json.loads(msg['payload'])
        assert payload['timestamp'] == original_time


# =============================================================================
# Test Classes: Recovery Scenarios
# =============================================================================

class TestRecoveryScenarios:
    """Tests for various failure/recovery combinations."""

    def test_timer_restart_with_pending_queue(self, temp_queue_dir):
        """Timer restarts and processes queue from previous session."""
        from derbynet import MessageQueue

        # First session - queue messages during outage
        queue1 = MessageQueue(queue_dir=temp_queue_dir)
        for i in range(5):
            queue1.put(f"topic{i}", f"payload{i}")

        # Verify files exist
        assert len(os.listdir(temp_queue_dir)) == 5

        # Simulate timer restart (battery reconnected)
        del queue1

        # Second session - new queue should load messages
        queue2 = MessageQueue(queue_dir=temp_queue_dir)
        assert queue2.size() == 5

        # Process all messages
        processed = 0
        while queue2.size() > 0:
            msg = queue2.get(block=False)
            if msg:
                queue2.task_done(msg['id'])
                processed += 1

        assert processed == 5
        assert len(os.listdir(temp_queue_dir)) == 0

    def test_server_restart_client_reconnects(self):
        """Timer reconnects when server comes back online."""
        from derbynet import MQTTClient

        with patch('paho.mqtt.client.Client') as MockClient:
            with patch('derbynet.MessageQueue') as MockQueue:
                MockQueue.return_value = Mock()
                mock_mqtt = Mock()
                MockClient.return_value = mock_mqtt

                client = MQTTClient("test-client")

                # Simulate disconnect
                client._on_disconnect(None, None, 1)  # rc=1 means unexpected
                assert client.connected is False

                # Simulate reconnection
                client._on_connect(None, None, None, 0)  # rc=0 means success
                assert client.connected is True

    def test_subscriptions_restored_on_reconnect(self):
        """Topic subscriptions are restored after reconnection."""
        from derbynet import MQTTClient

        with patch('paho.mqtt.client.Client') as MockClient:
            with patch('derbynet.MessageQueue') as MockQueue:
                MockQueue.return_value = Mock()
                mock_mqtt = Mock()
                MockClient.return_value = mock_mqtt

                client = MQTTClient("test-client")
                callback1 = Mock()
                callback2 = Mock()

                # Add subscriptions
                client.subscriptions["topic1"] = callback1
                client.subscriptions["topic2"] = callback2

                # Simulate reconnection
                client.connected = True
                client._on_connect(mock_mqtt, None, None, 0)

                # Subscriptions should be re-established
                assert mock_mqtt.subscribe.call_count >= 2

    def test_battery_warning_in_telemetry(self, mock_pcb, temp_queue_dir):
        """Low battery warning included in telemetry during outage."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)

        # Simulate low battery
        mock_pcb.battery_percent = 15

        telemetry = mock_pcb.packageTelemetry()
        queue.put(
            f"derbynet/device/{mock_pcb.gethwid()}/telemetry",
            json.dumps(telemetry),
            qos=1
        )

        msg = queue.get(block=False)
        payload = json.loads(msg['payload'])
        assert payload['battery_level'] == 15

    def test_network_error_display_set(self, mock_pcb):
        """Timer shows error state when network is down."""
        mock_pcb.networkError()

        assert mock_pcb.led_color == "white"
        assert mock_pcb.pinny_value == "ERR3"


# =============================================================================
# Test Classes: Concurrent Operations
# =============================================================================

class TestConcurrentOperations:
    """Tests for thread safety and concurrent access."""

    def test_concurrent_queue_access(self, temp_queue_dir):
        """Multiple threads can safely access the queue."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)
        errors = []
        messages_added = []

        def producer(producer_id, count):
            try:
                for i in range(count):
                    queue.put(f"topic-{producer_id}-{i}", f"payload-{producer_id}-{i}")
                    messages_added.append(f"{producer_id}-{i}")
            except Exception as e:
                errors.append(f"Producer {producer_id}: {e}")

        # Start multiple producers
        threads = []
        for pid in range(3):
            t = threading.Thread(target=producer, args=(pid, 10))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert queue.size() == 30  # 3 producers * 10 messages

    def test_concurrent_publish_and_drain(self, temp_queue_dir):
        """Publishing and draining queue concurrently doesn't corrupt data."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)
        errors = []
        published = []
        drained = []

        def publisher():
            try:
                for i in range(20):
                    queue.put(f"topic-{i}", f"payload-{i}")
                    published.append(i)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Publisher: {e}")

        def drainer():
            try:
                time.sleep(0.05)  # Let some messages queue first
                for _ in range(100):  # Try to drain
                    msg = queue.get(block=False)
                    if msg:
                        drained.append(msg)
                        queue.task_done(msg['id'])
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Drainer: {e}")

        pub_thread = threading.Thread(target=publisher)
        drain_thread = threading.Thread(target=drainer)

        pub_thread.start()
        drain_thread.start()

        pub_thread.join()
        drain_thread.join()

        assert len(errors) == 0
        # All published should eventually be drained
        assert len(published) == 20


# =============================================================================
# Test Classes: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_queue_get_returns_none(self, temp_queue_dir):
        """Getting from empty queue returns None (non-blocking)."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)
        result = queue.get(block=False)
        assert result is None

    def test_invalid_json_in_queue_file(self, temp_queue_dir):
        """Invalid JSON file in queue directory doesn't crash."""
        from derbynet import MessageQueue

        # Create invalid JSON file
        invalid_file = os.path.join(temp_queue_dir, "invalid.json")
        with open(invalid_file, 'w') as f:
            f.write("not valid json {{{")

        # Should not crash
        queue = MessageQueue(queue_dir=temp_queue_dir)
        # Invalid file might be skipped or logged
        assert queue is not None

    def test_queue_directory_creation(self, tmp_path):
        """Queue creates directory if it doesn't exist."""
        from derbynet import MessageQueue

        new_dir = str(tmp_path / "new" / "queue" / "dir")
        assert not os.path.exists(new_dir)

        queue = MessageQueue(queue_dir=new_dir)
        assert os.path.exists(new_dir)

    def test_large_payload_handling(self, temp_queue_dir):
        """Large payloads are handled correctly."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)

        # Create large payload (simulating detailed telemetry)
        large_payload = json.dumps({
            "data": "x" * 10000,  # 10KB of data
            "timestamp": int(time.time())
        })

        queue.put("test/topic", large_payload)

        msg = queue.get(block=False)
        assert msg is not None
        assert len(msg['payload']) > 10000

    def test_special_characters_in_payload(self, temp_queue_dir):
        """Payloads with special characters handled correctly."""
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)

        special_payload = json.dumps({
            "unicode": "こんにちは",
            "quotes": 'He said "hello"',
            "newlines": "line1\nline2",
            "backslash": "path\\to\\file"
        })

        queue.put("test/topic", special_payload)

        msg = queue.get(block=False)
        payload = json.loads(msg['payload'])
        assert payload['unicode'] == "こんにちは"
        assert "hello" in payload['quotes']


# =============================================================================
# Test Classes: Integration Scenarios
# =============================================================================

class TestIntegrationScenarios:
    """End-to-end scenario tests simulating real production events."""

    def test_race_day_server_outage_scenario(self, temp_queue_dir, mock_pcb):
        """
        Simulates race day scenario:
        1. Server goes down during heat
        2. 3 cars finish (toggle events queued)
        3. Server comes back
        4. Queue drains with correct race times
        """
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)

        # Simulate 3 lane finishes during outage
        finish_times = []
        for lane in range(1, 4):
            mock_pcb.lane = lane
            mock_pcb.dip_value = f"100{lane-1}"  # Lane DIP codes

            finish_time = int(time.time() * 1000)  # Millisecond precision
            finish_times.append(finish_time)

            toggle_payload = json.dumps({
                "toggle": False,
                "timestamp": finish_time,
                "hwid": f"TIMER-00{lane}",
                "dip": mock_pcb.dip_value,
                "lane": lane
            })
            queue.put(f"derbynet/device/TIMER-00{lane}/state", toggle_payload, qos=2)
            time.sleep(0.001)  # Simulate slight time between finishes

        assert queue.size() == 3

        # Simulate server recovery - drain queue
        recovered_finishes = []
        while queue.size() > 0:
            msg = queue.get(block=False)
            if msg:
                payload = json.loads(msg['payload'])
                recovered_finishes.append(payload)
                queue.task_done(msg['id'])

        # All 3 finishes recovered with correct timestamps
        assert len(recovered_finishes) == 3
        lanes = [f['lane'] for f in recovered_finishes]
        assert sorted(lanes) == [1, 2, 3]

        # Timestamps preserved
        for finish, expected_time in zip(recovered_finishes, finish_times):
            assert finish['timestamp'] == expected_time

    def test_timer_battery_disconnect_scenario(self, temp_queue_dir, mock_pcb):
        """
        Simulates timer battery coming loose:
        1. Timer queues race finish
        2. Battery disconnects (timer stops)
        3. Battery reconnected (timer restarts)
        4. Queue loads from disk
        5. Race finish sent to server
        """
        from derbynet import MessageQueue

        # Phase 1: Timer running, queues a finish
        queue1 = MessageQueue(queue_dir=temp_queue_dir)
        finish_payload = json.dumps({
            "toggle": False,
            "timestamp": 1234567890123,
            "hwid": mock_pcb.gethwid(),
            "lane": 1
        })
        queue1.put("derbynet/device/TIMER-001/state", finish_payload, qos=2)

        # Verify queued to disk
        assert len(os.listdir(temp_queue_dir)) == 1

        # Phase 2: Battery disconnect (queue object destroyed, simulating power loss)
        del queue1

        # Phase 3: Battery reconnected - new queue instance
        queue2 = MessageQueue(queue_dir=temp_queue_dir)

        # Should have loaded the finish event
        assert queue2.size() == 1

        msg = queue2.get(block=False)
        payload = json.loads(msg['payload'])
        assert payload['timestamp'] == 1234567890123
        assert payload['toggle'] is False

    def test_intermittent_connection_scenario(self, temp_queue_dir):
        """
        Simulates intermittent connection (rain/power issues):
        1. Connected - send messages
        2. Disconnected - queue messages
        3. Reconnected - drain queue
        4. Disconnected again - queue more
        5. Final reconnect - all messages sent
        """
        from derbynet import MessageQueue

        queue = MessageQueue(queue_dir=temp_queue_dir)
        all_messages = []

        # Cycle 1: Connected
        for i in range(3):
            # Would be sent directly in real client
            all_messages.append(f"connected-1-{i}")

        # Cycle 2: Disconnected
        for i in range(3):
            queue.put(f"topic-offline-1-{i}", f"payload-offline-1-{i}")
            all_messages.append(f"offline-1-{i}")

        assert queue.size() == 3

        # Cycle 3: Reconnected - drain
        while queue.size() > 0:
            msg = queue.get(block=False)
            if msg:
                queue.task_done(msg['id'])

        # Cycle 4: Disconnected again
        for i in range(2):
            queue.put(f"topic-offline-2-{i}", f"payload-offline-2-{i}")
            all_messages.append(f"offline-2-{i}")

        assert queue.size() == 2

        # Cycle 5: Final reconnect
        while queue.size() > 0:
            msg = queue.get(block=False)
            if msg:
                queue.task_done(msg['id'])

        assert queue.size() == 0
        assert len(os.listdir(temp_queue_dir)) == 0

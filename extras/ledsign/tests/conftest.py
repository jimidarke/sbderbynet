"""
Pytest Configuration and Fixtures for LED Sign Tests

Provides mocks for MicroPython hardware modules to enable
testing on desktop Python.
"""

import sys
import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any


# =============================================================================
# Mock MicroPython Modules
# =============================================================================

class MockUART:
    """Mock UART for serial communication testing"""

    def __init__(self, id=2, baudrate=9600, tx=17, rx=16):
        self.id = id
        self.baudrate = baudrate
        self.tx = tx
        self.rx = rx
        self.written_data: List[bytes] = []
        self.read_buffer: bytes = b''

    def write(self, data: bytes) -> int:
        """Record written data"""
        self.written_data.append(data)
        return len(data)

    def read(self, nbytes: int = -1) -> bytes:
        """Return mock read data"""
        if nbytes == -1:
            data = self.read_buffer
            self.read_buffer = b''
            return data
        data = self.read_buffer[:nbytes]
        self.read_buffer = self.read_buffer[nbytes:]
        return data

    def any(self) -> int:
        """Return number of bytes available"""
        return len(self.read_buffer)

    def get_last_write(self) -> bytes:
        """Get the last written data"""
        return self.written_data[-1] if self.written_data else b''

    def get_all_writes(self) -> List[bytes]:
        """Get all written data"""
        return self.written_data

    def clear_writes(self):
        """Clear recorded writes"""
        self.written_data = []


class MockPin:
    """Mock GPIO Pin"""

    IN = 0
    OUT = 1
    PULL_UP = 2
    PULL_DOWN = 3

    def __init__(self, pin_num, mode=None, pull=None):
        self.pin_num = pin_num
        self.mode = mode
        self.pull = pull
        self._value = 0

    def value(self, val=None):
        if val is None:
            return self._value
        self._value = val

    def on(self):
        self._value = 1

    def off(self):
        self._value = 0


class MockWDT:
    """Mock Watchdog Timer"""

    def __init__(self, timeout=60000):
        self.timeout = timeout
        self.feed_count = 0

    def feed(self):
        self.feed_count += 1


class MockWLAN:
    """Mock WiFi WLAN interface"""

    STA_IF = 0
    AP_IF = 1

    def __init__(self, interface=0):
        self.interface = interface
        self._active = False
        self._connected = False
        self._ssid = None
        self._password = None
        self._mac = b'\xaa\xbb\xcc\xdd\xee\xff'
        self._ip = '192.168.100.150'
        self._rssi = -65

    def active(self, val=None):
        if val is None:
            return self._active
        self._active = val

    def isconnected(self) -> bool:
        return self._connected

    def connect(self, ssid: str, password: str):
        self._ssid = ssid
        self._password = password
        self._connected = True

    def disconnect(self):
        self._connected = False

    def config(self, param: str):
        if param == 'mac':
            return self._mac
        return None

    def ifconfig(self):
        return (self._ip, '255.255.255.0', '192.168.100.1', '8.8.8.8')

    def status(self, param: str = None):
        if param == 'rssi':
            return self._rssi
        return 0


class MockMQTTClient:
    """Mock MQTT Client"""

    def __init__(self, client_id, server, port=1883, keepalive=60):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.keepalive = keepalive
        self.connected = False
        self.subscriptions: List[str] = []
        self.published: List[Dict[str, Any]] = []
        self.callback = None
        self.lwt_topic = None
        self.lwt_msg = None
        self.message_queue: List[tuple] = []  # Simulated incoming messages

    def set_callback(self, callback):
        self.callback = callback

    def set_last_will(self, topic, msg, retain=False, qos=0):
        self.lwt_topic = topic
        self.lwt_msg = msg

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def subscribe(self, topic):
        self.subscriptions.append(topic)

    def publish(self, topic, msg, retain=False, qos=0):
        self.published.append({
            'topic': topic,
            'msg': msg,
            'retain': retain,
            'qos': qos
        })

    def check_msg(self):
        """Process any queued messages"""
        if self.message_queue and self.callback:
            topic, msg = self.message_queue.pop(0)
            self.callback(topic.encode(), msg.encode() if isinstance(msg, str) else msg)

    def ping(self):
        pass

    # Test helpers
    def simulate_message(self, topic: str, msg):
        """Queue a message to be delivered on next check_msg()"""
        self.message_queue.append((topic, msg))

    def get_published(self, topic: str = None) -> List[Dict]:
        """Get published messages, optionally filtered by topic"""
        if topic:
            return [p for p in self.published if p['topic'] == topic]
        return self.published

    def clear_published(self):
        """Clear published messages"""
        self.published = []


# =============================================================================
# Mock Machine Module
# =============================================================================

mock_machine = MagicMock()
mock_machine.UART = MockUART
mock_machine.Pin = MockPin
mock_machine.WDT = MockWDT
mock_machine.reset = MagicMock()


# =============================================================================
# Mock Network Module
# =============================================================================

mock_network = MagicMock()
mock_network.WLAN = MockWLAN
mock_network.STA_IF = MockWLAN.STA_IF
mock_network.AP_IF = MockWLAN.AP_IF


# =============================================================================
# Mock umqtt Module
# =============================================================================

mock_umqtt = MagicMock()
mock_umqtt.simple = MagicMock()
mock_umqtt.simple.MQTTClient = MockMQTTClient


# =============================================================================
# Install Mocks
# =============================================================================

sys.modules['machine'] = mock_machine
sys.modules['network'] = mock_network
sys.modules['umqtt'] = mock_umqtt
sys.modules['umqtt.simple'] = mock_umqtt.simple
sys.modules['ubinascii'] = MagicMock()
sys.modules['ubinascii'].hexlify = lambda x, sep=None: x.hex().encode() if sep is None else sep.join(f'{b:02x}' for b in x).encode()

# Mock gc module for memory stats
mock_gc = MagicMock()
mock_gc.mem_free.return_value = 50000
mock_gc.mem_alloc.return_value = 100000
mock_gc.collect = MagicMock()
sys.modules['gc'] = mock_gc

# Mock time module with MicroPython-specific functions
import time as _real_time
class MockTime:
    """Mock time module with MicroPython compatibility"""
    def __init__(self):
        self._ticks = 0

    def time(self):
        return _real_time.time()

    def sleep(self, seconds):
        pass  # Don't actually sleep in tests

    def ticks_ms(self):
        return self._ticks

    def ticks_diff(self, a, b):
        return a - b

mock_time = MockTime()
sys.modules['time'] = mock_time


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture
def mock_uart():
    """Provide a fresh MockUART instance"""
    return MockUART()


@pytest.fixture
def mock_wlan():
    """Provide a fresh MockWLAN instance"""
    return MockWLAN()


@pytest.fixture
def mock_mqtt():
    """Provide a fresh MockMQTTClient instance"""
    return MockMQTTClient('test-client', '192.168.100.10')


@pytest.fixture
def mock_wdt():
    """Provide a fresh MockWDT instance"""
    return MockWDT()


@pytest.fixture
def betabrite(mock_uart):
    """Provide a BetaBrite instance with mock UART"""
    # Import after mocks are installed
    import os
    src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from betabrite import BetaBrite
    return BetaBrite(mock_uart)


@pytest.fixture
def sample_display_config():
    """Sample display configuration from MQTT message"""
    return {
        "mode": "flash",
        "mode_code": "c",
        "color": "red",
        "color_code": "1",
        "character_set": "10high",
        "charset_code": "6",
        "position": "fill",
        "position_code": "0",
        "speed": 4,
        "speed_code": "\\030",
        "special_effect": None,
        "effect_code": None,
        "priority": True,
        "duration": 30
    }


@pytest.fixture
def sample_zone_message():
    """Sample zone message payload"""
    return {
        "timestamp": 1705344000,
        "priority": 2,
        "title": "RACE STAGED",
        "message": "Heat 12 - Ready to start",
        "display_config": {
            "mode": "hold",
            "mode_code": "b",
            "color": "green",
            "color_code": "2",
            "character_set": "7high",
            "charset_code": "3",
            "position": "fill",
            "position_code": "0",
            "speed": 2,
            "speed_code": "\\026"
        },
        "zone": "starter",
        "source": "derbyrace-server"
    }


@pytest.fixture
def sample_broadcast_message():
    """Sample emergency broadcast payload"""
    return {
        "timestamp": 1705344000,
        "priority": 0,
        "title": "EMERGENCY",
        "message": "MISSING CHILD - BLUE SHIRT",
        "display_config": {
            "mode": "flash",
            "mode_code": "c",
            "color": "red",
            "color_code": "1",
            "character_set": "10high",
            "charset_code": "6",
            "position": "fill",
            "position_code": "0",
            "speed": 5,
            "speed_code": "\\031",
            "priority": True
        },
        "zone": "broadcast",
        "source": "coordinator-emergency"
    }


@pytest.fixture
def sample_config_message():
    """Sample zone configuration payload"""
    return {
        "zone": "starter",
        "display_name": "Start Line"
    }


@pytest.fixture
def sample_usher_message():
    """Sample usher sign message"""
    return {
        "timestamp": 1705344000,
        "priority": 2,
        "title": "NEXT",
        "message": "#42 JohnS",
        "display_config": {
            "mode": "hold",
            "mode_code": "b",
            "color": "green",
            "color_code": "2",
            "character_set": "7high",
            "charset_code": "3",
            "position": "fill",
            "position_code": "0"
        },
        "zone": "usher-lane1",
        "metadata": {
            "pinny": "42",
            "firstname": "John",
            "lastname": "Smith",
            "formatted_name": "JohnS"
        }
    }


@pytest.fixture
def sample_finish_message():
    """Sample finish line time message"""
    return {
        "timestamp": 1705344000,
        "priority": 2,
        "message": "00:30.134",
        "display_config": {
            "mode": "hold",
            "mode_code": "b",
            "color": "green",
            "color_code": "2",
            "character_set": "10high",
            "charset_code": "6",
            "position": "fill",
            "position_code": "0"
        },
        "zone": "finish-lane1",
        "metadata": {
            "lane": 1,
            "time_seconds": 30.134,
            "time_formatted": "00:30.134",
            "place": 2
        }
    }


@pytest.fixture
def sample_sponsor_rotation():
    """Sample sponsor rotation payload"""
    return {
        "timestamp": 1705344000,
        "sponsors": [
            {
                "id": "sponsor-001",
                "message": "Thanks to ACME Racing!",
                "duration": 15,
                "display_config": {
                    "mode": "scroll",
                    "mode_code": "m",
                    "color": "rainbow1",
                    "color_code": "9"
                }
            },
            {
                "id": "sponsor-002",
                "message": "Local Pizza Co - Best in town!",
                "duration": 12,
                "display_config": {
                    "mode": "scroll",
                    "mode_code": "m",
                    "color": "amber",
                    "color_code": "3"
                }
            }
        ],
        "default_duration": 15,
        "loop": True
    }

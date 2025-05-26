#!/usr/bin/env python3
"""
DerbyNet Shared Network Library

This module provides standardized network functionality for all DerbyNet components:
- MQTT connection management with advanced retry logic
- Message queuing for offline operation
- Device telemetry standardization
- Service discovery
- Network diagnostics

Usage:
    from common.derbynet import MQTTClient, DeviceTelemetry
    
    # Create a client with device ID
    mqtt = MQTTClient("finish-timer-1")
    
    # Connect with auto-reconnect
    mqtt.connect()
    
    # Send message (will queue if offline)
    mqtt.publish("derbynet/device/finish-timer-1/status", "ONLINE")
    
    # Subscribe to topics
    mqtt.subscribe("derbynet/race/state", callback_function)
"""

import os
import json
import time
import uuid
import socket
import logging
import threading
import queue
import paho.mqtt.client as mqtt
import psutil
from datetime import datetime

# Default configuration
DEFAULT_MQTT_BROKER = "192.168.100.10"
DEFAULT_MQTT_PORT = 1883
DEFAULT_QOS = 1
DEFAULT_RETAIN = False

# Constants for retry logic
INITIAL_RETRY_DELAY = 1.0  # seconds
MAX_RETRY_DELAY = 300.0    # 5 minutes
RETRY_BACKOFF_FACTOR = 2.0
RETRY_JITTER = 0.1

class MessageQueue:
    """Persistent message queue for offline operation"""
    
    def __init__(self, queue_dir="/var/lib/derbynet/queue"):
        """Initialize the message queue with storage directory"""
        self.queue_dir = queue_dir
        self.queue = queue.Queue()
        self.queue_lock = threading.Lock()
        
        # Create queue directory if it doesn't exist
        os.makedirs(self.queue_dir, exist_ok=True)
        
        # Load any previously queued messages
        self._load_from_disk()
    
    def put(self, topic, payload, qos=DEFAULT_QOS, retain=DEFAULT_RETAIN):
        """Add a message to the queue"""
        message = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "topic": topic,
            "payload": payload,
            "qos": qos,
            "retain": retain
        }
        
        with self.queue_lock:
            self.queue.put(message)
            self._save_to_disk(message)
    
    def get(self, block=True, timeout=None):
        """Get a message from the queue"""
        try:
            message = self.queue.get(block=block, timeout=timeout)
            return message
        except queue.Empty:
            return None
    
    def task_done(self, message_id):
        """Mark a message as processed and remove from disk"""
        self.queue.task_done()
        
        # Remove from disk
        message_file = os.path.join(self.queue_dir, f"{message_id}.json")
        try:
            if os.path.exists(message_file):
                os.remove(message_file)
        except Exception as e:
            logging.warning(f"Failed to remove message file {message_file}: {e}")
    
    def _save_to_disk(self, message):
        """Save a message to disk for persistence"""
        message_file = os.path.join(self.queue_dir, f"{message['id']}.json")
        try:
            with open(message_file, 'w') as f:
                json.dump(message, f)
        except Exception as e:
            logging.error(f"Failed to save message to disk: {e}")
    
    def _load_from_disk(self):
        """Load previously queued messages from disk"""
        if not os.path.exists(self.queue_dir):
            return
            
        for filename in sorted(os.listdir(self.queue_dir)):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(self.queue_dir, filename), 'r') as f:
                        message = json.load(f)
                        self.queue.put(message)
                except Exception as e:
                    logging.error(f"Failed to load message from disk: {e}")
    
    def size(self):
        """Get the current queue size"""
        return self.queue.qsize()

class MQTTClient:
    """Enhanced MQTT client with resilient connection handling"""
    
    def __init__(self, client_id, broker=DEFAULT_MQTT_BROKER, port=DEFAULT_MQTT_PORT):
        """Initialize the MQTT client"""
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self.connected = False
        self.connecting = False
        self.subscriptions = {}
        self.retry_delay = INITIAL_RETRY_DELAY
        self.message_queue = MessageQueue()
        self.stop_event = threading.Event()
        
        # Initialize MQTT client
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Set up message queue processor
        self.queue_processor = threading.Thread(target=self._process_queue, daemon=True)
        
        # Set up connection monitor
        self.connection_monitor = threading.Thread(target=self._monitor_connection, daemon=True)
    
    def connect(self, username=None, password=None):
        """Connect to the MQTT broker with auto-reconnect"""
        if username:
            self.client.username_pw_set(username, password)
        
        self.connecting = True
        self._connect_with_retry()
        
        # Start queue processor and connection monitor
        self.queue_processor.start()
        self.connection_monitor.start()
        
        return self.connected
    
    def disconnect(self):
        """Disconnect from the MQTT broker"""
        self.stop_event.set()
        self.client.disconnect()
        self.connected = False
        self.connecting = False
    
    def publish(self, topic, payload, qos=DEFAULT_QOS, retain=DEFAULT_RETAIN):
        """Publish a message, queue if offline"""
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        
        if self.connected:
            result = self.client.publish(topic, payload, qos, retain)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                # If publish fails, queue the message
                self.message_queue.put(topic, payload, qos, retain)
                return False
            return True
        else:
            # Queue message for later
            self.message_queue.put(topic, payload, qos, retain)
            return False
    
    def subscribe(self, topic, callback, qos=DEFAULT_QOS):
        """Subscribe to a topic with callback"""
        self.subscriptions[topic] = callback
        if self.connected:
            self.client.subscribe(topic, qos)
    
    def unsubscribe(self, topic):
        """Unsubscribe from a topic"""
        if topic in self.subscriptions:
            del self.subscriptions[topic]
            if self.connected:
                self.client.unsubscribe(topic)
    
    def _connect_with_retry(self):
        """Attempt connection with exponential backoff"""
        try:
            self.client.connect_async(self.broker, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            logging.error(f"Failed to connect to MQTT broker: {e}")
            # Will retry via the connection monitor
    
    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection established event"""
        if rc == 0:
            self.connected = True
            self.retry_delay = INITIAL_RETRY_DELAY
            logging.info(f"Connected to MQTT broker {self.broker}:{self.port}")
            
            # Resubscribe to topics
            for topic, callback in self.subscriptions.items():
                self.client.subscribe(topic)
        else:
            self.connected = False
            logging.error(f"Failed to connect to MQTT broker, return code: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection event"""
        self.connected = False
        if rc != 0:
            logging.warning(f"Unexpected disconnection from MQTT broker: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming message"""
        topic = msg.topic
        payload = msg.payload.decode()
        
        # Try to parse JSON
        try:
            payload = json.loads(payload)
        except (ValueError, TypeError):
            pass
        
        # Find and call the correct callback
        for subscription, callback in self.subscriptions.items():
            # Support wildcards in subscriptions
            if mqtt.topic_matches_sub(subscription, topic) and callback:
                callback(topic, payload)
    
    def _process_queue(self):
        """Process queued messages when online"""
        while not self.stop_event.is_set():
            if self.connected and self.message_queue.size() > 0:
                message = self.message_queue.get(block=False)
                if message:
                    try:
                        result = self.client.publish(
                            message["topic"], 
                            message["payload"], 
                            message["qos"], 
                            message["retain"]
                        )
                        if result.rc == mqtt.MQTT_ERR_SUCCESS:
                            self.message_queue.task_done(message["id"])
                        else:
                            # Put it back in the queue
                            self.message_queue.put(
                                message["topic"], 
                                message["payload"], 
                                message["qos"], 
                                message["retain"]
                            )
                    except Exception as e:
                        logging.error(f"Error publishing queued message: {e}")
            
            # Sleep briefly to avoid cpu spin
            time.sleep(0.1)
    
    def _monitor_connection(self):
        """Monitor connection and attempt reconnect if necessary"""
        while not self.stop_event.is_set():
            if not self.connected and self.connecting:
                # Calculate retry delay with exponential backoff and jitter
                jitter = self.retry_delay * RETRY_JITTER * (2 * (0.5 - (time.time() % 1)) or 1)
                delay = min(self.retry_delay + jitter, MAX_RETRY_DELAY)
                
                logging.info(f"Attempting reconnection in {delay:.1f} seconds")
                time.sleep(delay)
                
                try:
                    # Try to reconnect
                    self._connect_with_retry()
                    
                    # Update retry delay for next time
                    self.retry_delay = min(self.retry_delay * RETRY_BACKOFF_FACTOR, MAX_RETRY_DELAY)
                except Exception as e:
                    logging.error(f"Reconnection attempt failed: {e}")
            
            # Check less frequently when connected
            time.sleep(5)

class DeviceTelemetry:
    """Standardized device telemetry collector"""
    
    def __init__(self, device_id, device_type):
        """Initialize telemetry collector for a device"""
        self.device_id = device_id
        self.device_type = device_type
        self.start_time = time.time()
    
    def collect(self):
        """Collect standard system telemetry"""
        # Get system information
        cpu_temp = self._get_cpu_temperature()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_info = self._get_network_info()
        
        return {
            "hostname": socket.gethostname(),
            "hwid": self.device_id,
            "device_type": self.device_type,
            "uptime": int(time.time() - self.start_time),
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": psutil.cpu_percent(),
            "cpu_temp": cpu_temp,
            "memory_usage": {
                "total": mem.total,
                "used": mem.used,
                "percent": mem.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "percent": disk.percent
            },
            "network": net_info
        }
    
    def _get_cpu_temperature(self):
        """Get CPU temperature on supported platforms"""
        temp = None
        try:
            # Raspberry Pi
            if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = float(f.read()) / 1000.0
        except Exception:
            pass
        return temp
    
    def _get_network_info(self):
        """Get network information"""
        result = {}
        try:
            # Get primary network interface
            net_io = psutil.net_io_counters(pernic=True)
            net_addrs = psutil.net_if_addrs()
            
            primary_nic = None
            for nic in ('eth0', 'wlan0', 'enp0s3', 'wlp2s0'):
                if nic in net_io:
                    primary_nic = nic
                    break
            
            if primary_nic and primary_nic in net_addrs:
                for addr in net_addrs[primary_nic]:
                    if addr.family == socket.AF_INET:
                        result["ip"] = addr.address
                    elif addr.family == psutil.AF_LINK:
                        result["mac"] = addr.address
                
                # Add network traffic stats
                if primary_nic in net_io:
                    net = net_io[primary_nic]
                    result["bytes_sent"] = net.bytes_sent
                    result["bytes_recv"] = net.bytes_recv
            
            # Try to get WiFi signal strength on Raspberry Pi
            if os.path.exists('/proc/net/wireless') and 'wlan' in primary_nic:
                with open('/proc/net/wireless', 'r') as f:
                    for line in f:
                        if primary_nic in line:
                            parts = line.strip().split()
                            if len(parts) >= 4:
                                result["wifi_rssi"] = float(parts[3].strip('.'))
        except Exception as e:
            logging.warning(f"Error getting network info: {e}")
        
        return result

def discover_services(service_type="_derbynet._tcp.local.", timeout=5):
    """
    Discover DerbyNet services on the local network using mDNS
    
    Note: This requires the zeroconf package to be installed:
    pip install zeroconf
    """
    try:
        from zeroconf import ServiceBrowser, Zeroconf
        
        class ServiceListener:
            def __init__(self):
                self.services = {}
            
            def add_service(self, zc, type, name):
                info = zc.get_service_info(type, name)
                if info:
                    self.services[name] = {
                        "name": name,
                        "host": info.server,
                        "ip": ".".join(str(b) for b in info.addresses[0]),
                        "port": info.port,
                        "properties": {k.decode(): v.decode() for k, v in info.properties.items()}
                    }
        
        zeroconf = Zeroconf()
        listener = ServiceListener()
        browser = ServiceBrowser(zeroconf, service_type, listener)
        
        # Wait for services to be discovered
        time.sleep(timeout)
        
        zeroconf.close()
        return listener.services
    except ImportError:
        logging.warning("Zeroconf package not installed. Service discovery not available.")
        return {}
    except Exception as e:
        logging.error(f"Error discovering services: {e}")
        return {}

def network_diagnostics():
    """Run network diagnostics and return results"""
    results = {
        "connectivity": {},
        "latency": {},
        "dns": {}
    }
    
    # Check basic connectivity
    for host in [DEFAULT_MQTT_BROKER, "8.8.8.8"]:
        try:
            # Use socket with timeout for faster check
            socket.create_connection((host, 80), timeout=2)
            results["connectivity"][host] = True
        except Exception:
            results["connectivity"][host] = False
    
    # Check DNS resolution
    for domain in ["google.com", "example.com"]:
        try:
            socket.gethostbyname(domain)
            results["dns"][domain] = True
        except Exception:
            results["dns"][domain] = False
    
    # Measure latency to MQTT broker
    try:
        start = time.time()
        socket.create_connection((DEFAULT_MQTT_BROKER, DEFAULT_MQTT_PORT), timeout=2)
        latency = (time.time() - start) * 1000  # in ms
        results["latency"][DEFAULT_MQTT_BROKER] = round(latency, 2)
    except Exception:
        results["latency"][DEFAULT_MQTT_BROKER] = None
    
    return results

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create a client
    client = MQTTClient("test-client")
    
    # Define a callback
    def on_message(topic, payload):
        print(f"Received message on {topic}: {payload}")
    
    # Connect
    client.connect()
    
    # Subscribe
    client.subscribe("derbynet/test/#", on_message)
    
    # Publish
    client.publish("derbynet/test/hello", "world")
    
    # Get telemetry
    telemetry = DeviceTelemetry("test-client", "test").collect()
    print(json.dumps(telemetry, indent=2))
    
    # Wait a bit
    time.sleep(5)
    
    # Disconnect
    client.disconnect()
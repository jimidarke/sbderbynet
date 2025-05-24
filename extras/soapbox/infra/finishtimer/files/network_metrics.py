#!/usr/bin/env python3
"""
Network metrics collection and monitoring for DerbyNet components

This module provides utilities for:
1. Measuring network latency and throughput
2. Tracking MQTT message delivery times
3. Collecting and reporting network performance metrics
4. Storing historical network performance data

Usage:
    from network_metrics import NetworkMetrics
    
    # Initialize metrics collector
    metrics = NetworkMetrics()
    
    # Record message send
    msg_id = metrics.record_message_send("topic/example", payload)
    
    # Record message delivery (in receiver)
    metrics.record_message_delivery(msg_id)
    
    # Get current metrics
    current_metrics = metrics.get_metrics()
    
    # Get historical report
    report = metrics.get_report(hours=24)
"""

import time
import json
import uuid
import socket
import logging
import threading
import statistics
from collections import deque
from datetime import datetime, timedelta
import os
import sqlite3

try:
    from derbylogger import get_logger
    logger = get_logger("network_metrics")
except ImportError:
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("network_metrics")

class NetworkMetrics:
    """Collects and reports network performance metrics"""
    
    def __init__(self, db_path=None, history_size=1000):
        """
        Initialize the metrics collector
        
        Args:
            db_path: Path to SQLite database for persistent storage
            history_size: Number of measurements to keep in memory
        """
        self.instance_id = str(uuid.uuid4())
        self.hostname = socket.gethostname()
        
        # In-memory storage for recent metrics
        self.messages = {}  # track in-flight messages
        self.latency_history = deque(maxlen=history_size)
        self.throughput_history = deque(maxlen=history_size)
        self.message_size_history = deque(maxlen=history_size)
        self.packet_loss_history = deque(maxlen=history_size)
        
        # Periodic measurement timing
        self.last_measurement_time = time.time()
        self.messages_since_last = 0
        self.bytes_since_last = 0
        
        # Database for persistent storage
        self.db_path = db_path
        if db_path:
            self._init_db()
        
        # Start background measurement thread
        self.running = True
        self.measurement_thread = threading.Thread(target=self._periodic_measurements, daemon=True)
        self.measurement_thread.start()
        
        logger.info(f"Network metrics initialized on {self.hostname}")
    
    def _init_db(self):
        """Initialize SQLite database for metrics storage"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_metrics (
                id TEXT PRIMARY KEY,
                topic TEXT,
                send_time REAL,
                receive_time REAL,
                size INTEGER,
                hostname TEXT,
                instance_id TEXT
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS network_metrics (
                timestamp REAL,
                metric_type TEXT,
                value REAL,
                hostname TEXT,
                instance_id TEXT,
                PRIMARY KEY (timestamp, metric_type, hostname)
            )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            self.db_path = None
    
    def _store_metric(self, metric_type, value):
        """Store a metric value in the database"""
        if not self.db_path:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO network_metrics VALUES (?, ?, ?, ?, ?)",
                (time.time(), metric_type, value, self.hostname, self.instance_id)
            )
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to store metric in database: {e}")
    
    def _periodic_measurements(self):
        """Background thread for periodic measurements"""
        measurement_interval = 10  # seconds
        
        while self.running:
            try:
                # Sleep first to allow initial data collection
                time.sleep(measurement_interval)
                
                # Calculate throughput
                current_time = time.time()
                elapsed = current_time - self.last_measurement_time
                
                if elapsed > 0:
                    # Calculate messages per second
                    msg_rate = self.messages_since_last / elapsed
                    self.throughput_history.append((current_time, msg_rate))
                    
                    # Calculate bytes per second
                    byte_rate = self.bytes_since_last / elapsed
                    
                    # Store metrics
                    if self.db_path:
                        self._store_metric("msg_rate", msg_rate)
                        self._store_metric("byte_rate", byte_rate)
                
                # Measure network latency with ping
                self._measure_ping_latency()
                
                # Reset counters
                self.last_measurement_time = current_time
                self.messages_since_last = 0
                self.bytes_since_last = 0
                
            except Exception as e:
                logger.error(f"Error in periodic measurements: {e}")
    
    def _measure_ping_latency(self):
        """Measure network latency with ping to MQTT broker"""
        # This would use ping or other methods to measure network latency
        # For now, we'll just use a placeholder value
        try:
            # Use socket connection time as a simple latency measure
            start_time = time.time()
            
            # Try to connect to MQTT broker (default port)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            
            # Use localhost if no server is specified
            host = "localhost"
            port = 1883
            
            s.connect((host, port))
            s.close()
            
            latency = (time.time() - start_time) * 1000  # convert to ms
            self.latency_history.append((time.time(), latency))
            
            if self.db_path:
                self._store_metric("latency", latency)
                
        except Exception as e:
            logger.warning(f"Failed to measure network latency: {e}")
            # Record a high latency value to indicate problems
            self.latency_history.append((time.time(), 9999))
            
            if self.db_path:
                self._store_metric("latency", 9999)
    
    def record_message_send(self, topic, payload, qos=0):
        """
        Record when a message is sent
        
        Args:
            topic: MQTT topic
            payload: Message payload
            qos: MQTT QoS level
            
        Returns:
            message_id: Unique ID for tracking the message
        """
        send_time = time.time()
        message_id = str(uuid.uuid4())
        
        # Calculate message size
        try:
            if isinstance(payload, (str, bytes)):
                size = len(payload)
            else:
                # Convert to JSON string to get size
                size = len(json.dumps(payload))
        except:
            size = 0
        
        # Store message details
        self.messages[message_id] = {
            'topic': topic,
            'send_time': send_time,
            'size': size,
            'qos': qos
        }
        
        # Update counters
        self.messages_since_last += 1
        self.bytes_since_last += size
        
        # Store message size for statistics
        self.message_size_history.append((send_time, size))
        
        return message_id
    
    def record_message_delivery(self, message_id, success=True):
        """
        Record when a message is delivered
        
        Args:
            message_id: ID returned from record_message_send
            success: Whether delivery was successful
        """
        if message_id not in self.messages:
            return False
        
        receive_time = time.time()
        message = self.messages[message_id]
        
        # Calculate latency
        latency = (receive_time - message['send_time']) * 1000  # ms
        self.latency_history.append((receive_time, latency))
        
        if self.db_path:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute(
                    "INSERT INTO message_metrics VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (message_id, message['topic'], message['send_time'], 
                     receive_time, message['size'], self.hostname, self.instance_id)
                )
                
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Failed to store message metrics: {e}")
        
        # Remove from tracking
        del self.messages[message_id]
        
        return True
    
    def record_packet_loss(self, loss_rate):
        """
        Record packet loss rate
        
        Args:
            loss_rate: Packet loss rate (0.0 to 1.0)
        """
        self.packet_loss_history.append((time.time(), loss_rate))
        
        if self.db_path:
            self._store_metric("packet_loss", loss_rate)
    
    def get_metrics(self):
        """
        Get current network metrics
        
        Returns:
            dict: Current network performance metrics
        """
        current_time = time.time()
        
        # Calculate message delivery rate
        message_rate = 0
        if self.throughput_history:
            recent_rates = [rate for ts, rate in self.throughput_history 
                          if current_time - ts < 60]
            message_rate = statistics.mean(recent_rates) if recent_rates else 0
        
        # Calculate average latency
        avg_latency = 0
        if self.latency_history:
            recent_latencies = [lat for ts, lat in self.latency_history 
                              if current_time - ts < 60 and lat < 9000]
            avg_latency = statistics.mean(recent_latencies) if recent_latencies else 0
        
        # Calculate packet loss
        packet_loss = 0
        if self.packet_loss_history:
            recent_losses = [loss for ts, loss in self.packet_loss_history 
                           if current_time - ts < 60]
            packet_loss = statistics.mean(recent_losses) if recent_losses else 0
        
        # Calculate in-flight messages
        in_flight = len(self.messages)
        
        # Calculate message size statistics
        avg_size = 0
        if self.message_size_history:
            recent_sizes = [size for ts, size in self.message_size_history 
                          if current_time - ts < 60]
            avg_size = statistics.mean(recent_sizes) if recent_sizes else 0
        
        return {
            'timestamp': current_time,
            'message_rate': message_rate,
            'in_flight_messages': in_flight,
            'average_latency_ms': avg_latency,
            'packet_loss_rate': packet_loss,
            'average_message_size': avg_size
        }
    
    def get_report(self, hours=24):
        """
        Get historical network performance report
        
        Args:
            hours: Number of hours to include in report
            
        Returns:
            dict: Historical network performance metrics
        """
        if not self.db_path:
            return {
                'error': 'No database configured for historical reporting'
            }
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate start time
            start_time = time.time() - (hours * 3600)
            
            # Query for metrics
            cursor.execute("""
                SELECT metric_type, 
                       AVG(value) as avg_value, 
                       MIN(value) as min_value, 
                       MAX(value) as max_value,
                       COUNT(*) as sample_count
                FROM network_metrics
                WHERE timestamp >= ? AND hostname = ?
                GROUP BY metric_type
            """, (start_time, self.hostname))
            
            metrics = {}
            for row in cursor.fetchall():
                metric_type, avg, min_val, max_val, count = row
                metrics[metric_type] = {
                    'average': avg,
                    'minimum': min_val,
                    'maximum': max_val,
                    'sample_count': count
                }
            
            # Query for message delivery stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_messages,
                    AVG(receive_time - send_time) * 1000 as avg_latency,
                    AVG(size) as avg_size
                FROM message_metrics
                WHERE send_time >= ? AND hostname = ?
            """, (start_time, self.hostname))
            
            row = cursor.fetchone()
            if row:
                total_messages, avg_latency, avg_size = row
                message_stats = {
                    'total_messages': total_messages,
                    'average_latency_ms': avg_latency or 0,
                    'average_size_bytes': avg_size or 0
                }
            else:
                message_stats = {
                    'total_messages': 0,
                    'average_latency_ms': 0,
                    'average_size_bytes': 0
                }
            
            conn.close()
            
            return {
                'hostname': self.hostname,
                'report_time': time.time(),
                'report_period_hours': hours,
                'metrics': metrics,
                'message_stats': message_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to generate metrics report: {e}")
            return {'error': str(e)}
    
    def close(self):
        """Close the metrics collector and stop background threads"""
        self.running = False
        if self.measurement_thread.is_alive():
            self.measurement_thread.join(timeout=1.0)
        logger.info("Network metrics collector closed")


class MQTTMetrics:
    """Helper class for MQTT-specific metrics collection"""
    
    def __init__(self, client_id, db_path=None):
        """
        Initialize MQTT metrics collector
        
        Args:
            client_id: MQTT client ID for tracking
            db_path: Path to SQLite database for historical data
        """
        self.client_id = client_id
        self.metrics = NetworkMetrics(db_path=db_path)
        self.message_ids = {}  # map MQTT message IDs to our internal IDs
        
        logger.info(f"MQTT metrics initialized for client {client_id}")
    
    def on_publish(self, client, userdata, mid):
        """
        Callback for MQTT message published
        
        Args:
            client: MQTT client instance
            userdata: User data
            mid: Message ID
        """
        if mid in self.message_ids:
            internal_id = self.message_ids[mid]
            self.metrics.record_message_delivery(internal_id)
            del self.message_ids[mid]
    
    def before_publish(self, topic, payload, qos=0):
        """
        Call before publishing an MQTT message
        
        Args:
            topic: MQTT topic
            payload: Message payload
            qos: QoS level
            
        Returns:
            internal_id: Internal message ID for tracking
        """
        return self.metrics.record_message_send(topic, payload, qos)
    
    def after_publish(self, client, mid, internal_id):
        """
        Call after publishing an MQTT message
        
        Args:
            client: MQTT client instance
            mid: MQTT message ID
            internal_id: Internal message ID from before_publish
        """
        self.message_ids[mid] = internal_id
    
    def on_message(self, client, userdata, message):
        """
        Callback for MQTT message received
        
        Args:
            client: MQTT client instance
            userdata: User data
            message: MQTT message
        """
        # Generate an ID for received messages
        internal_id = self.metrics.record_message_send(
            message.topic, message.payload, message.qos)
        
        # Immediately mark as delivered since we've received it
        self.metrics.record_message_delivery(internal_id)
    
    def get_metrics(self):
        """Get current MQTT metrics"""
        metrics = self.metrics.get_metrics()
        metrics['client_id'] = self.client_id
        return metrics
    
    def get_report(self, hours=24):
        """Get historical MQTT metrics report"""
        report = self.metrics.get_report(hours)
        report['client_id'] = self.client_id
        return report
    
    def close(self):
        """Close the metrics collector"""
        self.metrics.close()


# Example usage
if __name__ == "__main__":
    import paho.mqtt.client as mqtt
    
    # Set up MQTT metrics
    mqtt_metrics = MQTTMetrics("test-client", db_path="/tmp/network_metrics.db")
    
    # Use with MQTT client
    client = mqtt.Client("test-client")
    client.on_publish = mqtt_metrics.on_publish
    client.on_message = mqtt_metrics.on_message
    
    # Example publish with metrics
    topic = "test/topic"
    payload = "Hello World"
    
    internal_id = mqtt_metrics.before_publish(topic, payload)
    result = client.publish(topic, payload)
    mqtt_metrics.after_publish(client, result.mid, internal_id)
    
    # Get current metrics
    current_metrics = mqtt_metrics.get_metrics()
    print(json.dumps(current_metrics, indent=2))
    
    # Wait a bit and get a report
    time.sleep(5)
    report = mqtt_metrics.get_report(hours=1)
    print(json.dumps(report, indent=2))
    
    # Clean up
    mqtt_metrics.close()
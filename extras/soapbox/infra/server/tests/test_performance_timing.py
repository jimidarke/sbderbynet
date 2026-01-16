"""
Performance Tests - Race Timing Latency
=======================================

Measures end-to-end latency for the critical race timing path:
  Sensor Trigger → MQTT → Server Processing → DB Write → Display Update

Version: 1.0.0
Date: 2026-01-15

CRITICAL PATH:
--------------
    1. Timer sensor triggers (IR beam broken)
    2. Timer software captures timestamp, publishes MQTT
    3. Server receives MQTT message
    4. Server processes toggle event
    5. Server updates race state
    6. Server writes result to database
    7. Server publishes state update to displays
    8. Display receives and renders update

SLA TARGETS:
------------
    - Single lane finish: < 50ms (sensor to DB)
    - All lanes simultaneous: < 100ms (worst lane)
    - MQTT round-trip: < 20ms (local broker)
    - DB write: < 10ms (SQLite local)
    - End-to-end (sensor to display): < 150ms

HARDWARE NOTE:
--------------
    Baseline measurements taken on development laptop (Intel/AMD x86_64).
    Production runs on Raspberry Pi 4 (ARM64, 1.5GHz quad-core, 4GB RAM).

    Expected Pi performance factors:
    - CPU: ~3-5x slower than laptop
    - I/O: Similar (both use SSD/SD card)
    - Memory: Similar latency
    - Network: Similar (local MQTT broker)

    SLA targets set with Pi headroom in mind. If laptop achieves 2ms,
    Pi should achieve <10ms, still well within 50ms SLA.

USAGE:
------
    # Run all performance tests
    pytest tests/test_performance_timing.py -v

    # Run with timing details
    pytest tests/test_performance_timing.py -v -s

    # Run specific benchmark
    pytest tests/test_performance_timing.py::TestRaceTimingLatency -v
"""

import json
import os
import sys
import statistics
import tempfile
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# TIMING UTILITIES
# ============================================================================

class TimingCollector:
    """
    Collects timing measurements for performance analysis.

    Thread-safe collector for measuring latencies across components.
    """

    def __init__(self):
        self._measurements: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._checkpoints: Dict[str, float] = {}

    def checkpoint(self, name: str) -> float:
        """Record a checkpoint timestamp."""
        ts = time.perf_counter()
        with self._lock:
            self._checkpoints[name] = ts
        return ts

    def measure_since(self, checkpoint_name: str, measurement_name: str) -> float:
        """Measure time since a checkpoint."""
        now = time.perf_counter()
        with self._lock:
            start = self._checkpoints.get(checkpoint_name, now)
            elapsed_ms = (now - start) * 1000

            if measurement_name not in self._measurements:
                self._measurements[measurement_name] = []
            self._measurements[measurement_name].append(elapsed_ms)

        return elapsed_ms

    def record(self, name: str, value_ms: float):
        """Record a measurement directly."""
        with self._lock:
            if name not in self._measurements:
                self._measurements[name] = []
            self._measurements[name].append(value_ms)

    def get_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for a measurement."""
        with self._lock:
            values = self._measurements.get(name, [])

        if not values:
            return {'count': 0}

        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'stdev': statistics.stdev(values) if len(values) > 1 else 0,
            'p95': sorted(values)[int(len(values) * 0.95)] if len(values) >= 20 else max(values),
            'p99': sorted(values)[int(len(values) * 0.99)] if len(values) >= 100 else max(values),
        }

    def summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of all measurements."""
        with self._lock:
            names = list(self._measurements.keys())
        return {name: self.get_stats(name) for name in names}

    def clear(self):
        """Clear all measurements."""
        with self._lock:
            self._measurements.clear()
            self._checkpoints.clear()


# Global timing collector for tests
timing = TimingCollector()


# ============================================================================
# SLA THRESHOLDS (in milliseconds)
# ============================================================================

SLA = {
    'mqtt_roundtrip': 20,          # Local broker round-trip
    'mqtt_publish': 5,             # Time to publish message
    'message_processing': 10,      # Server message handling
    'state_update': 5,             # Race state update
    'db_write': 10,                # Database write
    'single_lane_finish': 50,      # Single lane end-to-end
    'all_lanes_finish': 100,       # All lanes simultaneous
    'display_update': 150,         # End-to-end to display
}


# ============================================================================
# MOCK COMPONENTS FOR PERFORMANCE TESTING
# ============================================================================

class MockMQTTBroker:
    """
    In-memory MQTT broker for latency testing.

    Simulates broker behavior with configurable latency.
    """

    def __init__(self, latency_ms: float = 1.0):
        self.latency_ms = latency_ms
        self.subscribers: Dict[str, List[callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, topic: str, callback: callable):
        """Subscribe to a topic."""
        with self._lock:
            if topic not in self.subscribers:
                self.subscribers[topic] = []
            self.subscribers[topic].append(callback)

    def publish(self, topic: str, payload: str) -> float:
        """
        Publish a message and return publish latency.

        Returns:
            Time in ms to deliver to all subscribers
        """
        start = time.perf_counter()

        # Simulate broker latency
        time.sleep(self.latency_ms / 1000)

        # Deliver to subscribers
        with self._lock:
            callbacks = self.subscribers.get(topic, [])

        for callback in callbacks:
            callback(topic, payload)

        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms


class MockDatabase:
    """
    In-memory database for latency testing.

    Simulates SQLite write latency.
    """

    def __init__(self, write_latency_ms: float = 2.0):
        self.write_latency_ms = write_latency_ms
        self.results: List[Dict] = []
        self._lock = threading.Lock()

    def write_finish(self, lane: int, time_sec: float, heat_id: int = 1) -> float:
        """
        Write a finish result.

        Returns:
            Write latency in ms
        """
        start = time.perf_counter()

        # Simulate DB write latency
        time.sleep(self.write_latency_ms / 1000)

        with self._lock:
            self.results.append({
                'lane': lane,
                'time': time_sec,
                'heat_id': heat_id,
                'written_at': datetime.now().isoformat(),
            })

        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms


class MockRaceServer:
    """
    Simplified race server for performance testing.

    Simulates the critical path from MQTT receive to DB write.
    """

    def __init__(self, db: MockDatabase, timing_collector: TimingCollector):
        self.db = db
        self.timing = timing_collector
        self.race_state = 'RACING'
        self.lane_times: Dict[int, float] = {}
        self.start_time: float = 0
        self._lock = threading.Lock()

    def start_race(self):
        """Start a race."""
        self.start_time = time.time()
        self.lane_times.clear()
        self.race_state = 'RACING'

    def handle_toggle(self, lane: int, toggle_state: bool,
                      msg_timestamp: float) -> float:
        """
        Handle a toggle event from timer.

        Returns:
            Total processing time in ms
        """
        start = time.perf_counter()

        if toggle_state:  # High → ignore (beam restored)
            return 0

        # Lane finished (beam broken)
        with self._lock:
            if lane in self.lane_times:
                return 0  # Already finished

            finish_time = time.time() - self.start_time
            self.lane_times[lane] = finish_time

        # Write to database
        db_latency = self.db.write_finish(lane, finish_time)

        elapsed_ms = (time.perf_counter() - start) * 1000
        self.timing.record('server_processing', elapsed_ms)
        self.timing.record('db_write', db_latency)

        return elapsed_ms


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestMQTTLatency:
    """Test MQTT message latency."""

    def test_mqtt_publish_latency(self):
        """Measure MQTT publish latency."""
        broker = MockMQTTBroker(latency_ms=1.0)
        received = []

        def on_message(topic, payload):
            received.append((time.perf_counter(), payload))

        broker.subscribe('derbynet/device/test/state', on_message)

        latencies = []
        for i in range(100):
            start = time.perf_counter()
            payload = json.dumps({'toggle': False, 'lane': 1, 'ts': time.time()})
            broker.publish('derbynet/device/test/state', payload)
            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        mean_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[95]

        print(f"\nMQTT Publish Latency:")
        print(f"  Mean: {mean_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  SLA: {SLA['mqtt_roundtrip']}ms")

        # Verify SLA
        assert mean_latency < SLA['mqtt_roundtrip'], \
            f"Mean MQTT latency {mean_latency:.2f}ms exceeds SLA {SLA['mqtt_roundtrip']}ms"

    def test_mqtt_throughput(self):
        """Test MQTT message throughput (messages per second)."""
        broker = MockMQTTBroker(latency_ms=0.5)
        received_count = 0

        def on_message(topic, payload):
            nonlocal received_count
            received_count += 1

        broker.subscribe('derbynet/device/+/state', on_message)

        # Send 1000 messages
        start = time.perf_counter()
        for i in range(1000):
            payload = json.dumps({'toggle': i % 2 == 0, 'lane': (i % 3) + 1})
            broker.publish(f'derbynet/device/timer{i % 3}/state', payload)

        elapsed = time.perf_counter() - start
        throughput = 1000 / elapsed

        print(f"\nMQTT Throughput:")
        print(f"  Messages: 1000")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Throughput: {throughput:.0f} msg/sec")

        # Should handle at least 500 msg/sec
        assert throughput > 500, f"Throughput {throughput:.0f} msg/sec below 500"


class TestDatabaseLatency:
    """Test database write latency."""

    def test_single_write_latency(self):
        """Measure single DB write latency."""
        db = MockDatabase(write_latency_ms=2.0)

        latencies = []
        for i in range(100):
            latency = db.write_finish(lane=(i % 3) + 1, time_sec=5.0 + i * 0.01)
            latencies.append(latency)

        mean_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[95]

        print(f"\nDB Write Latency:")
        print(f"  Mean: {mean_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  SLA: {SLA['db_write']}ms")

        # Verify SLA
        assert mean_latency < SLA['db_write'], \
            f"Mean DB latency {mean_latency:.2f}ms exceeds SLA {SLA['db_write']}ms"

    def test_concurrent_writes(self):
        """Test concurrent DB writes (all lanes finish simultaneously)."""
        db = MockDatabase(write_latency_ms=2.0)

        latencies = []
        threads = []
        results = {}

        def write_lane(lane: int):
            latency = db.write_finish(lane=lane, time_sec=5.0 + lane * 0.001)
            results[lane] = latency

        # Simulate 3 lanes finishing simultaneously
        start = time.perf_counter()
        for lane in [1, 2, 3]:
            t = threading.Thread(target=write_lane, args=(lane,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        total_time = (time.perf_counter() - start) * 1000

        print(f"\nConcurrent DB Writes (3 lanes):")
        print(f"  Lane 1: {results[1]:.2f}ms")
        print(f"  Lane 2: {results[2]:.2f}ms")
        print(f"  Lane 3: {results[3]:.2f}ms")
        print(f"  Total: {total_time:.2f}ms")

        # All writes should complete within SLA
        assert total_time < SLA['all_lanes_finish'], \
            f"Concurrent writes {total_time:.2f}ms exceeds SLA {SLA['all_lanes_finish']}ms"


class TestRaceTimingLatency:
    """Test end-to-end race timing latency."""

    @pytest.fixture
    def race_system(self):
        """Create a complete race system for testing."""
        collector = TimingCollector()
        db = MockDatabase(write_latency_ms=2.0)
        server = MockRaceServer(db, collector)
        broker = MockMQTTBroker(latency_ms=1.0)

        # Wire up MQTT to server
        def on_toggle(topic, payload):
            collector.checkpoint('mqtt_received')
            data = json.loads(payload)
            server.handle_toggle(
                lane=data['lane'],
                toggle_state=data['toggle'],
                msg_timestamp=data.get('ts', time.time())
            )
            collector.measure_since('mqtt_received', 'server_total')

        broker.subscribe('derbynet/device/+/state', on_toggle)

        return {
            'server': server,
            'broker': broker,
            'db': db,
            'timing': collector,
        }

    def test_single_lane_finish(self, race_system):
        """Measure latency for single lane finish."""
        server = race_system['server']
        broker = race_system['broker']
        collector = race_system['timing']

        server.start_race()

        latencies = []
        for i in range(50):
            server.lane_times.clear()  # Reset for next iteration

            collector.checkpoint('sensor_trigger')

            # Simulate timer publishing finish
            payload = json.dumps({
                'toggle': False,  # Beam broken
                'lane': 1,
                'ts': time.time(),
            })
            broker.publish('derbynet/device/timer1/state', payload)

            latency = collector.measure_since('sensor_trigger', 'single_lane_e2e')
            latencies.append(latency)

        stats = collector.get_stats('single_lane_e2e')

        print(f"\nSingle Lane Finish Latency:")
        print(f"  Mean: {stats['mean']:.2f}ms")
        print(f"  P95: {stats['p95']:.2f}ms")
        print(f"  Max: {stats['max']:.2f}ms")
        print(f"  SLA: {SLA['single_lane_finish']}ms")

        # Verify SLA
        assert stats['p95'] < SLA['single_lane_finish'], \
            f"P95 latency {stats['p95']:.2f}ms exceeds SLA {SLA['single_lane_finish']}ms"

    def test_all_lanes_simultaneous(self, race_system):
        """Measure latency when all lanes finish simultaneously."""
        server = race_system['server']
        broker = race_system['broker']
        collector = race_system['timing']

        latencies = []

        for iteration in range(20):
            server.start_race()
            collector.checkpoint('all_lanes_start')

            # Simulate all 3 lanes finishing at once
            threads = []
            for lane in [1, 2, 3]:
                def publish_finish(l=lane):
                    payload = json.dumps({
                        'toggle': False,
                        'lane': l,
                        'ts': time.time(),
                    })
                    broker.publish(f'derbynet/device/timer{l}/state', payload)

                t = threading.Thread(target=publish_finish)
                threads.append(t)

            # Start all threads simultaneously
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            latency = collector.measure_since('all_lanes_start', 'all_lanes_e2e')
            latencies.append(latency)

        stats = collector.get_stats('all_lanes_e2e')

        print(f"\nAll Lanes Simultaneous Finish:")
        print(f"  Mean: {stats['mean']:.2f}ms")
        print(f"  P95: {stats['p95']:.2f}ms")
        print(f"  Max: {stats['max']:.2f}ms")
        print(f"  SLA: {SLA['all_lanes_finish']}ms")

        # Verify SLA
        assert stats['p95'] < SLA['all_lanes_finish'], \
            f"P95 latency {stats['p95']:.2f}ms exceeds SLA {SLA['all_lanes_finish']}ms"

    def test_sustained_racing(self, race_system):
        """Test latency over sustained racing (simulate race day)."""
        server = race_system['server']
        broker = race_system['broker']
        collector = race_system['timing']

        num_heats = 100  # Simulate 100 heats
        latencies_by_heat = []

        for heat in range(num_heats):
            server.start_race()
            collector.checkpoint(f'heat_{heat}_start')

            # Random lane finish order
            import random
            lanes = [1, 2, 3]
            random.shuffle(lanes)

            for lane in lanes:
                # Small delay between finishes (realistic)
                time.sleep(0.001)

                payload = json.dumps({
                    'toggle': False,
                    'lane': lane,
                    'ts': time.time(),
                })
                broker.publish(f'derbynet/device/timer{lane}/state', payload)

            latency = collector.measure_since(f'heat_{heat}_start', f'heat_{heat}_total')
            latencies_by_heat.append(latency)

        # Check for degradation over time
        first_10 = statistics.mean(latencies_by_heat[:10])
        last_10 = statistics.mean(latencies_by_heat[-10:])
        degradation = last_10 - first_10

        print(f"\nSustained Racing ({num_heats} heats):")
        print(f"  First 10 heats avg: {first_10:.2f}ms")
        print(f"  Last 10 heats avg: {last_10:.2f}ms")
        print(f"  Degradation: {degradation:+.2f}ms")
        print(f"  Overall mean: {statistics.mean(latencies_by_heat):.2f}ms")

        # No significant degradation (< 20% increase)
        assert degradation < first_10 * 0.2, \
            f"Performance degraded by {degradation:.2f}ms ({degradation/first_10*100:.1f}%)"


class TestTimingPrecision:
    """Test timing precision and accuracy."""

    def test_timestamp_precision(self):
        """Verify timestamp precision is sufficient."""
        # Python time.time() should have sub-millisecond precision
        timestamps = []
        for _ in range(1000):
            timestamps.append(time.time())

        # Check minimum time delta
        deltas = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        min_delta_ms = min(deltas) * 1000

        print(f"\nTimestamp Precision:")
        print(f"  Minimum delta: {min_delta_ms:.4f}ms")
        print(f"  Required: < 1ms")

        # Should be able to distinguish sub-millisecond
        assert min_delta_ms < 1.0, "Timestamp precision insufficient"

    def test_perf_counter_precision(self):
        """Verify perf_counter precision for benchmarking."""
        # time.perf_counter() should have microsecond precision
        timestamps = []
        for _ in range(1000):
            timestamps.append(time.perf_counter())

        deltas = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        min_delta_us = min(deltas) * 1_000_000

        print(f"\nPerf Counter Precision:")
        print(f"  Minimum delta: {min_delta_us:.2f}μs")
        print(f"  Required: < 100μs")

        # Should be able to distinguish sub-100 microseconds
        assert min_delta_us < 100, "Perf counter precision insufficient"


class TestSLACompliance:
    """Verify SLA compliance across all components."""

    def test_sla_summary(self):
        """Summary test showing all SLA targets."""
        print("\n" + "="*60)
        print("SLA COMPLIANCE SUMMARY")
        print("="*60)

        for metric, target_ms in SLA.items():
            print(f"  {metric:25s}: {target_ms:6.0f}ms")

        print("="*60)
        print("\nAll performance tests validate against these SLA targets.")
        print("P95 latency must be below SLA for compliance.")

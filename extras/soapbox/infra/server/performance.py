"""
DerbyNet Performance Instrumentation
====================================

Lightweight performance instrumentation for production monitoring.
Tracks latencies at key points in the race timing critical path.

Version: 1.0.0
Date: 2026-01-15

USAGE:
------
    from performance import perf, checkpoint, measure, get_metrics

    # At race start
    checkpoint('race_start')

    # At lane finish
    checkpoint('lane_finish')
    latency = measure('lane_finish', 'race_start', 'lane_finish_latency')

    # Get metrics for reporting
    metrics = get_metrics()

METRICS COLLECTED:
------------------
    - mqtt_receive_latency: Time from publish to receive
    - toggle_processing: Time to process toggle event
    - db_write_latency: Time to write result to database
    - race_end_to_end: Total race time
    - api_call_latency: HTTP API call times

CONFIGURATION:
--------------
    PERF_ENABLED=true       Enable instrumentation (default: true)
    PERF_LOG_SLOW=true      Log slow operations (default: true)
    PERF_SLOW_THRESHOLD_MS=50  Threshold for slow operation (default: 50ms)
"""

import json
import os
import statistics
import threading
import time
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from functools import wraps

# Configuration
PERF_ENABLED = os.getenv('PERF_ENABLED', 'true').lower() == 'true'
PERF_LOG_SLOW = os.getenv('PERF_LOG_SLOW', 'true').lower() == 'true'
PERF_SLOW_THRESHOLD_MS = float(os.getenv('PERF_SLOW_THRESHOLD_MS', '50'))
PERF_HISTORY_SIZE = int(os.getenv('PERF_HISTORY_SIZE', '1000'))


class PerformanceMonitor:
    """
    Thread-safe performance monitoring for race timing.

    Collects timing metrics with minimal overhead when enabled.
    When disabled, all operations are no-ops.
    """

    def __init__(self, enabled: bool = True, history_size: int = 1000):
        self.enabled = enabled
        self.history_size = history_size
        self._lock = threading.Lock()
        self._checkpoints: Dict[str, float] = {}  # Per-thread checkpoints
        self._local = threading.local()
        self._metrics: Dict[str, deque] = {}
        self._slow_operations: deque = deque(maxlen=100)

    def _get_checkpoints(self) -> Dict[str, float]:
        """Get thread-local checkpoints."""
        if not hasattr(self._local, 'checkpoints'):
            self._local.checkpoints = {}
        return self._local.checkpoints

    def checkpoint(self, name: str) -> float:
        """
        Record a checkpoint timestamp.

        Args:
            name: Checkpoint name (e.g., 'mqtt_received')

        Returns:
            Timestamp (perf_counter)
        """
        if not self.enabled:
            return 0

        ts = time.perf_counter()
        self._get_checkpoints()[name] = ts
        return ts

    def measure(self, end_checkpoint: str, start_checkpoint: str,
                metric_name: str) -> float:
        """
        Measure time between two checkpoints.

        Args:
            end_checkpoint: Name of end checkpoint (or 'now' for current time)
            start_checkpoint: Name of start checkpoint
            metric_name: Name for this metric

        Returns:
            Elapsed time in milliseconds
        """
        if not self.enabled:
            return 0

        checkpoints = self._get_checkpoints()

        start = checkpoints.get(start_checkpoint)
        if start is None:
            return 0

        if end_checkpoint == 'now':
            end = time.perf_counter()
        else:
            end = checkpoints.get(end_checkpoint)
            if end is None:
                return 0

        elapsed_ms = (end - start) * 1000

        # Record metric
        self._record(metric_name, elapsed_ms)

        # Log slow operations
        if PERF_LOG_SLOW and elapsed_ms > PERF_SLOW_THRESHOLD_MS:
            self._log_slow(metric_name, elapsed_ms)

        return elapsed_ms

    def _record(self, metric_name: str, value_ms: float):
        """Record a metric value."""
        with self._lock:
            if metric_name not in self._metrics:
                self._metrics[metric_name] = deque(maxlen=self.history_size)
            self._metrics[metric_name].append(value_ms)

    def _log_slow(self, metric_name: str, elapsed_ms: float):
        """Log a slow operation."""
        with self._lock:
            self._slow_operations.append({
                'metric': metric_name,
                'elapsed_ms': elapsed_ms,
                'timestamp': datetime.now().isoformat(),
            })

    def record(self, metric_name: str, value_ms: float):
        """Record a metric value directly."""
        if not self.enabled:
            return

        self._record(metric_name, value_ms)

        if PERF_LOG_SLOW and value_ms > PERF_SLOW_THRESHOLD_MS:
            self._log_slow(metric_name, value_ms)

    def time_operation(self, metric_name: str):
        """
        Decorator/context manager for timing operations.

        Usage as decorator:
            @perf.time_operation('db_write')
            def write_result():
                ...

        Usage as context manager:
            with perf.time_operation('db_write'):
                write_result()
        """
        return TimingContext(self, metric_name)

    def get_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric."""
        with self._lock:
            if metric_name not in self._metrics:
                return {'count': 0}

            values = list(self._metrics[metric_name])

        if not values:
            return {'count': 0}

        sorted_values = sorted(values)
        count = len(values)

        return {
            'count': count,
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'stdev': statistics.stdev(values) if count > 1 else 0,
            'p95': sorted_values[int(count * 0.95)] if count >= 20 else max(values),
            'p99': sorted_values[int(count * 0.99)] if count >= 100 else max(values),
        }

    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all metrics."""
        with self._lock:
            metric_names = list(self._metrics.keys())

        return {name: self.get_stats(name) for name in metric_names}

    def get_slow_operations(self) -> List[Dict]:
        """Get recent slow operations."""
        with self._lock:
            return list(self._slow_operations)

    def get_metrics_json(self) -> str:
        """Get all metrics as JSON string."""
        return json.dumps({
            'timestamp': datetime.now().isoformat(),
            'metrics': self.get_all_stats(),
            'slow_operations': self.get_slow_operations()[-10:],  # Last 10
        }, indent=2)

    def clear(self):
        """Clear all metrics."""
        with self._lock:
            self._metrics.clear()
            self._slow_operations.clear()
        self._get_checkpoints().clear()


class TimingContext:
    """Context manager for timing operations."""

    def __init__(self, monitor: PerformanceMonitor, metric_name: str):
        self.monitor = monitor
        self.metric_name = metric_name
        self.start_time: float = 0

    def __enter__(self):
        if self.monitor.enabled:
            self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.monitor.enabled:
            elapsed_ms = (time.perf_counter() - self.start_time) * 1000
            self.monitor.record(self.metric_name, elapsed_ms)
        return False

    def __call__(self, func: Callable) -> Callable:
        """Allow use as decorator."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper


# ============================================================================
# GLOBAL INSTANCE AND CONVENIENCE FUNCTIONS
# ============================================================================

# Global performance monitor
perf = PerformanceMonitor(enabled=PERF_ENABLED, history_size=PERF_HISTORY_SIZE)


def checkpoint(name: str) -> float:
    """Record a checkpoint timestamp."""
    return perf.checkpoint(name)


def measure(end: str, start: str, metric: str) -> float:
    """Measure time between checkpoints."""
    return perf.measure(end, start, metric)


def record(metric: str, value_ms: float):
    """Record a metric value."""
    perf.record(metric, value_ms)


def time_operation(metric: str):
    """Decorator/context manager for timing."""
    return perf.time_operation(metric)


def get_metrics() -> Dict[str, Dict[str, float]]:
    """Get all metric statistics."""
    return perf.get_all_stats()


def get_metrics_json() -> str:
    """Get metrics as JSON."""
    return perf.get_metrics_json()


# ============================================================================
# SLA CHECKING
# ============================================================================

# SLA thresholds (milliseconds)
SLA_THRESHOLDS = {
    'mqtt_receive': 20,
    'toggle_processing': 10,
    'db_write': 10,
    'lane_finish_e2e': 50,
    'all_lanes_e2e': 100,
    'api_call': 100,
}


def check_sla_compliance() -> Dict[str, Any]:
    """
    Check if current metrics meet SLA thresholds.

    Returns:
        Dict with 'compliant' bool and details
    """
    stats = perf.get_all_stats()
    violations = []

    for metric_name, threshold_ms in SLA_THRESHOLDS.items():
        if metric_name in stats:
            metric_stats = stats[metric_name]
            p95 = metric_stats.get('p95', 0)

            if p95 > threshold_ms:
                violations.append({
                    'metric': metric_name,
                    'p95': p95,
                    'threshold': threshold_ms,
                    'exceeded_by': p95 - threshold_ms,
                })

    return {
        'compliant': len(violations) == 0,
        'violations': violations,
        'checked_at': datetime.now().isoformat(),
    }


# ============================================================================
# CLI
# ============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='DerbyNet Performance Monitor')
    parser.add_argument('--demo', action='store_true', help='Run demo')
    parser.add_argument('--sla', action='store_true', help='Show SLA thresholds')

    args = parser.parse_args()

    if args.sla:
        print("SLA Thresholds:")
        for metric, threshold in SLA_THRESHOLDS.items():
            print(f"  {metric}: {threshold}ms")
        exit(0)

    if args.demo:
        print("Performance Instrumentation Demo")
        print("="*50)

        # Simulate some operations
        for i in range(10):
            checkpoint('start')
            time.sleep(0.005)  # Simulate work
            checkpoint('middle')
            time.sleep(0.003)
            checkpoint('end')

            measure('middle', 'start', 'first_half')
            measure('end', 'middle', 'second_half')
            measure('end', 'start', 'total')

        # Also test decorator
        @time_operation('decorated_func')
        def do_work():
            time.sleep(0.002)

        for _ in range(5):
            do_work()

        # Show results
        print("\nMetrics:")
        print(get_metrics_json())

        print("\nSLA Compliance:")
        compliance = check_sla_compliance()
        print(f"  Compliant: {compliance['compliant']}")
        if compliance['violations']:
            print("  Violations:")
            for v in compliance['violations']:
                print(f"    - {v['metric']}: {v['p95']:.2f}ms > {v['threshold']}ms")

"""
Tests for Correlation ID System
===============================

Tests the correlation ID functionality for request tracing across components.

Version: 1.0.0
Date: 2026-01-15
"""

import json
import os
import sys
import tempfile
import threading
import time
import pytest

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from derbylogger import (
    setup_logger, set_correlation_id, get_correlation_id,
    clear_correlation_id, correlation_context, CorrelationContext,
    DerbyJSONFormatter, get_device_id
)


class TestCorrelationContext:
    """Test the CorrelationContext class."""

    def test_set_returns_correlation_id(self):
        """Setting correlation ID returns the ID."""
        corr_id = CorrelationContext.set('test-123')
        assert corr_id == 'test-123'
        CorrelationContext.clear()

    def test_set_auto_generates_id(self):
        """Setting without ID auto-generates one."""
        corr_id = CorrelationContext.set()
        assert corr_id is not None
        assert len(corr_id) == 12  # Short UUID format
        CorrelationContext.clear()

    def test_get_returns_current_id(self):
        """Get returns the current correlation ID."""
        CorrelationContext.set('test-456')
        assert CorrelationContext.get() == 'test-456'
        CorrelationContext.clear()

    def test_get_returns_none_when_not_set(self):
        """Get returns None when no correlation ID is set."""
        CorrelationContext.clear()
        assert CorrelationContext.get() is None

    def test_clear_removes_correlation_id(self):
        """Clear removes the correlation ID."""
        CorrelationContext.set('test-789')
        CorrelationContext.clear()
        assert CorrelationContext.get() is None

    def test_session_id_stored(self):
        """Session ID is stored and retrievable."""
        CorrelationContext.set('corr-1', session_id='session-abc')
        assert CorrelationContext.get_session_id() == 'session-abc'
        CorrelationContext.clear()

    def test_source_stored(self):
        """Source is stored and retrievable."""
        CorrelationContext.set('corr-2', source='finishtimer')
        assert CorrelationContext.get_source() == 'finishtimer'
        CorrelationContext.clear()

    def test_get_context_includes_all_fields(self):
        """get_context includes all set fields."""
        CorrelationContext.set('corr-3', session_id='sess-1', source='test')
        ctx = CorrelationContext.get_context()

        assert ctx['corr_id'] == 'corr-3'
        assert ctx['session_id'] == 'sess-1'
        assert ctx['source'] == 'test'
        assert 'seq' in ctx  # Sequence number always included
        CorrelationContext.clear()

    def test_sequence_numbers_increment(self):
        """Sequence numbers increment with each context retrieval."""
        CorrelationContext.set('corr-seq')
        seq1 = CorrelationContext.get_context()['seq']
        seq2 = CorrelationContext.get_context()['seq']
        seq3 = CorrelationContext.get_context()['seq']

        assert seq2 > seq1
        assert seq3 > seq2
        CorrelationContext.clear()


class TestCorrelationConvenienceFunctions:
    """Test the convenience functions for correlation IDs."""

    def test_set_correlation_id_returns_id(self):
        """set_correlation_id returns the ID."""
        corr_id = set_correlation_id('func-test-1')
        assert corr_id == 'func-test-1'
        clear_correlation_id()

    def test_get_correlation_id_retrieves_id(self):
        """get_correlation_id retrieves the current ID."""
        set_correlation_id('func-test-2')
        assert get_correlation_id() == 'func-test-2'
        clear_correlation_id()

    def test_clear_correlation_id_clears(self):
        """clear_correlation_id clears the ID."""
        set_correlation_id('func-test-3')
        clear_correlation_id()
        assert get_correlation_id() is None


class TestCorrelationContextManager:
    """Test the correlation_context context manager."""

    def test_context_manager_sets_id(self):
        """Context manager sets the correlation ID."""
        with correlation_context('cm-test-1'):
            assert get_correlation_id() == 'cm-test-1'

    def test_context_manager_clears_on_exit(self):
        """Context manager clears ID on exit."""
        with correlation_context('cm-test-2'):
            pass
        assert get_correlation_id() is None

    def test_context_manager_yields_id(self):
        """Context manager yields the correlation ID."""
        with correlation_context('cm-test-3') as corr_id:
            assert corr_id == 'cm-test-3'

    def test_context_manager_auto_generates_id(self):
        """Context manager auto-generates ID if not provided."""
        with correlation_context() as corr_id:
            assert corr_id is not None
            assert len(corr_id) == 12

    def test_context_manager_clears_on_exception(self):
        """Context manager clears ID even on exception."""
        try:
            with correlation_context('cm-test-4'):
                raise ValueError("Test exception")
        except ValueError:
            pass
        assert get_correlation_id() is None


class TestThreadIsolation:
    """Test that correlation IDs are thread-isolated."""

    def test_threads_have_separate_ids(self):
        """Different threads have separate correlation IDs."""
        results = {}

        def thread_func(thread_id, corr_id):
            set_correlation_id(corr_id)
            time.sleep(0.1)  # Allow time for interleaving
            results[thread_id] = get_correlation_id()
            clear_correlation_id()

        threads = [
            threading.Thread(target=thread_func, args=(1, 'thread-1-id')),
            threading.Thread(target=thread_func, args=(2, 'thread-2-id')),
            threading.Thread(target=thread_func, args=(3, 'thread-3-id')),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results[1] == 'thread-1-id'
        assert results[2] == 'thread-2-id'
        assert results[3] == 'thread-3-id'

    def test_main_thread_isolated_from_child(self):
        """Main thread ID is isolated from child thread."""
        set_correlation_id('main-thread-id')

        child_result = {}

        def child_func():
            child_result['before'] = get_correlation_id()
            set_correlation_id('child-thread-id')
            child_result['after'] = get_correlation_id()
            clear_correlation_id()

        thread = threading.Thread(target=child_func)
        thread.start()
        thread.join()

        # Main thread should still have its ID
        assert get_correlation_id() == 'main-thread-id'
        # Child thread should have started with None
        assert child_result['before'] is None
        # Child thread should have its own ID
        assert child_result['after'] == 'child-thread-id'

        clear_correlation_id()


class TestCorrelationInLogs:
    """Test that correlation IDs appear in log output."""

    def test_json_log_includes_correlation_id(self):
        """JSON log entries include correlation ID when set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, 'test.jsonl')

            logger = setup_logger(
                'test-corr',
                log_file=None,
                json_file=json_file,
                console=False
            )

            set_correlation_id('log-corr-1')
            logger.info("Test message with correlation")
            clear_correlation_id()

            # Read JSON log
            with open(json_file, 'r') as f:
                entry = json.loads(f.readline())

            assert entry.get('corr_id') == 'log-corr-1'

    def test_json_log_includes_sequence(self):
        """JSON log entries include sequence number."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, 'test.jsonl')

            logger = setup_logger(
                'test-seq',
                log_file=None,
                json_file=json_file,
                console=False
            )

            logger.info("Message 1")
            logger.info("Message 2")

            with open(json_file, 'r') as f:
                entry1 = json.loads(f.readline())
                entry2 = json.loads(f.readline())

            assert 'seq' in entry1
            assert 'seq' in entry2
            assert entry2['seq'] > entry1['seq']

    def test_json_log_includes_sync_status(self):
        """JSON log entries include sync_status field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, 'test.jsonl')

            logger = setup_logger(
                'test-sync',
                log_file=None,
                json_file=json_file,
                console=False
            )

            logger.info("Test message")

            with open(json_file, 'r') as f:
                entry = json.loads(f.readline())

            assert entry.get('sync_status') == 'pending'

    def test_json_log_omits_corr_id_when_not_set(self):
        """JSON log entries omit corr_id when not set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, 'test.jsonl')

            clear_correlation_id()  # Ensure no correlation ID

            logger = setup_logger(
                'test-no-corr',
                log_file=None,
                json_file=json_file,
                console=False
            )

            logger.info("Message without correlation")

            with open(json_file, 'r') as f:
                entry = json.loads(f.readline())

            # corr_id should not be present (or should be None)
            assert entry.get('corr_id') is None


class TestCorrelationPropagation:
    """Test correlation ID propagation patterns."""

    def test_propagate_to_mqtt_message(self):
        """Correlation ID can be included in MQTT message payload."""
        set_correlation_id('mqtt-corr-1', session_id='race-123')

        mqtt_payload = {
            'toggle': True,
            'lane': 1,
            'timestamp': time.time(),
            'corr_id': get_correlation_id(),
        }

        assert mqtt_payload['corr_id'] == 'mqtt-corr-1'
        clear_correlation_id()

    def test_receive_from_mqtt_message(self):
        """Correlation ID can be extracted from incoming MQTT message."""
        # Simulate incoming MQTT message
        incoming_msg = {
            'toggle': False,
            'lane': 2,
            'timestamp': time.time(),
            'corr_id': 'incoming-corr-1',
        }

        # Set correlation from incoming message
        set_correlation_id(incoming_msg.get('corr_id'), source='mqtt')

        assert get_correlation_id() == 'incoming-corr-1'
        assert CorrelationContext.get_source() == 'mqtt'

        clear_correlation_id()

    def test_full_round_trip(self):
        """Test full correlation ID round-trip."""
        # 1. PHP generates correlation ID
        php_corr_id = 'php-generated-123'

        # 2. PHP sends to Python server via HTTP (header)
        # Simulated by setting correlation ID from "header"
        set_correlation_id(php_corr_id, source='php')

        # 3. Python logs with correlation ID
        # (verified by TestCorrelationInLogs)

        # 4. Python sends to MQTT with correlation ID
        mqtt_msg = {'corr_id': get_correlation_id()}
        assert mqtt_msg['corr_id'] == php_corr_id

        # 5. Timer receives and uses same correlation ID
        # Simulated by new context receiving the ID
        received_id = mqtt_msg['corr_id']

        # In timer context
        clear_correlation_id()
        set_correlation_id(received_id, source='timer')
        assert get_correlation_id() == php_corr_id

        clear_correlation_id()

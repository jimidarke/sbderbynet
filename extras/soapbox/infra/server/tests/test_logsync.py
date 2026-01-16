"""
Tests for Log Sync Service
==========================

Tests the log sync service for cloud log transmission.

Version: 1.0.0
Date: 2026-01-15
"""

import gzip
import json
import os
import sys
import tempfile
import time
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logsync import (
    SyncState, LogReader, LogSyncService, MockCloudAPI,
    get_config, DEFAULT_CONFIG
)


class TestSyncState:
    """Test the SyncState class for state persistence."""

    def test_initial_state_has_defaults(self):
        """Initial state has default values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, 'state.json')
            state = SyncState(state_file)

            assert state.position == 0
            assert state.failures == 0
            assert state.deployment_id is not None

    def test_update_success_updates_position(self):
        """update_success updates the position."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, 'state.json')
            state = SyncState(state_file)

            state.update_success(1000, 'batch-1', 500)

            assert state.position == 1000

    def test_update_success_resets_failures(self):
        """update_success resets failure count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, 'state.json')
            state = SyncState(state_file)

            state.update_failure()
            state.update_failure()
            assert state.failures == 2

            state.update_success(1000, 'batch-1', 500)
            assert state.failures == 0

    def test_update_failure_increments_count(self):
        """update_failure increments failure count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, 'state.json')
            state = SyncState(state_file)

            state.update_failure()
            assert state.failures == 1

            state.update_failure()
            assert state.failures == 2

    def test_state_persists_to_file(self):
        """State persists to file and survives reload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, 'state.json')

            # First instance
            state1 = SyncState(state_file)
            state1.update_success(5000, 'batch-x', 1000)

            # Second instance (reload)
            state2 = SyncState(state_file)
            assert state2.position == 5000

    def test_deployment_id_persists(self):
        """Deployment ID persists across reloads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, 'state.json')

            state1 = SyncState(state_file)
            deployment_id = state1.deployment_id

            # Must save state for it to persist
            state1.update_success(100, 'batch-1', 50)

            state2 = SyncState(state_file)
            assert state2.deployment_id == deployment_id


class TestLogReader:
    """Test the LogReader class for reading log entries."""

    def test_read_empty_file(self):
        """Reading empty file returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test.jsonl')
            open(log_file, 'w').close()

            reader = LogReader(log_file)
            entries, pos = reader.read_batch(0, 100, 1000000)

            assert entries == []
            assert pos == 0

    def test_read_single_entry(self):
        """Reading single entry returns it correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test.jsonl')

            entry = {'ts': '2026-01-15T10:00:00', 'level': 'INFO', 'msg': 'Test'}
            with open(log_file, 'w') as f:
                f.write(json.dumps(entry) + '\n')

            reader = LogReader(log_file)
            entries, pos = reader.read_batch(0, 100, 1000000)

            assert len(entries) == 1
            assert entries[0]['msg'] == 'Test'

    def test_read_multiple_entries(self):
        """Reading multiple entries returns all."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test.jsonl')

            with open(log_file, 'w') as f:
                for i in range(5):
                    entry = {'ts': f'2026-01-15T10:0{i}:00', 'msg': f'Message {i}'}
                    f.write(json.dumps(entry) + '\n')

            reader = LogReader(log_file)
            entries, pos = reader.read_batch(0, 100, 1000000)

            assert len(entries) == 5

    def test_read_respects_max_entries(self):
        """Reading respects max_entries limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test.jsonl')

            with open(log_file, 'w') as f:
                for i in range(10):
                    entry = {'msg': f'Message {i}'}
                    f.write(json.dumps(entry) + '\n')

            reader = LogReader(log_file)
            entries, pos = reader.read_batch(0, 3, 1000000)

            assert len(entries) == 3

    def test_read_from_position(self):
        """Reading from position skips earlier entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test.jsonl')

            # Write entries with known byte lengths
            entries_data = []
            with open(log_file, 'w') as f:
                for i in range(5):
                    entry = {'msg': f'Message {i}'}
                    line = json.dumps(entry) + '\n'
                    f.write(line)
                    entries_data.append(line)

            # Calculate position after first 2 entries
            pos_after_2 = len(entries_data[0]) + len(entries_data[1])

            # Read starting from known position (skip first 2)
            reader = LogReader(log_file)
            entries, _ = reader.read_batch(pos_after_2, 2, 1000000)

            assert len(entries) == 2
            assert entries[0]['msg'] == 'Message 2'
            assert entries[1]['msg'] == 'Message 3'

    def test_has_new_entries(self):
        """has_new_entries detects new entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test.jsonl')

            with open(log_file, 'w') as f:
                f.write(json.dumps({'msg': 'Test'}) + '\n')

            reader = LogReader(log_file)

            # Has entries from start
            assert reader.has_new_entries(0) is True

            # Read all
            entries, pos = reader.read_batch(0, 100, 1000000)

            # No new entries after reading all
            assert reader.has_new_entries(pos) is False

            # Add more entries
            with open(log_file, 'a') as f:
                f.write(json.dumps({'msg': 'New'}) + '\n')

            # Now has new entries
            assert reader.has_new_entries(pos) is True

    def test_handles_malformed_json(self):
        """Handles malformed JSON lines gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test.jsonl')

            with open(log_file, 'w') as f:
                f.write(json.dumps({'msg': 'Valid 1'}) + '\n')
                f.write('not valid json\n')
                f.write(json.dumps({'msg': 'Valid 2'}) + '\n')

            reader = LogReader(log_file)
            entries, pos = reader.read_batch(0, 100, 1000000)

            # Should skip malformed and return valid entries
            assert len(entries) == 2
            assert entries[0]['msg'] == 'Valid 1'
            assert entries[1]['msg'] == 'Valid 2'

    def test_handles_file_rotation(self):
        """Handles file rotation (truncation) gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test.jsonl')

            # Write initial entries
            with open(log_file, 'w') as f:
                for i in range(10):
                    f.write(json.dumps({'msg': f'Old {i}'}) + '\n')

            reader = LogReader(log_file)
            _, pos = reader.read_batch(0, 100, 1000000)

            # Simulate rotation - truncate and write new entries
            with open(log_file, 'w') as f:
                f.write(json.dumps({'msg': 'New after rotation'}) + '\n')

            # Position is now larger than file - should reset
            entries, new_pos = reader.read_batch(pos, 100, 1000000)

            assert len(entries) == 1
            assert entries[0]['msg'] == 'New after rotation'


class TestLogSyncService:
    """Test the LogSyncService class."""

    def test_service_initializes(self):
        """Service initializes with config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DEFAULT_CONFIG.copy()
            config['log_file'] = os.path.join(tmpdir, 'test.jsonl')
            config['state_file'] = os.path.join(tmpdir, 'state.json')
            config['enabled'] = True

            service = LogSyncService(config)

            assert service.config == config

    def test_sync_disabled_returns_true(self):
        """Sync when disabled returns True without doing anything."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DEFAULT_CONFIG.copy()
            config['log_file'] = os.path.join(tmpdir, 'test.jsonl')
            config['state_file'] = os.path.join(tmpdir, 'state.json')
            config['enabled'] = False

            service = LogSyncService(config)

            assert service.sync_once() is True

    def test_sync_no_new_entries_returns_true(self):
        """Sync with no new entries returns True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test.jsonl')
            open(log_file, 'w').close()  # Empty file

            config = DEFAULT_CONFIG.copy()
            config['log_file'] = log_file
            config['state_file'] = os.path.join(tmpdir, 'state.json')
            config['enabled'] = True

            service = LogSyncService(config)

            assert service.sync_once() is True

    def test_compress_batch_creates_gzip(self):
        """_compress_batch creates valid gzip data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DEFAULT_CONFIG.copy()
            config['log_file'] = os.path.join(tmpdir, 'test.jsonl')
            config['state_file'] = os.path.join(tmpdir, 'state.json')

            service = LogSyncService(config)

            entries = [
                {'msg': 'Test 1'},
                {'msg': 'Test 2'},
            ]

            compressed = service._compress_batch(entries)

            # Should be gzip
            assert compressed[:2] == b'\x1f\x8b'  # gzip magic number

            # Should decompress to JSONL
            decompressed = gzip.decompress(compressed).decode('utf-8')
            lines = decompressed.strip().split('\n')

            assert len(lines) == 2
            assert json.loads(lines[0])['msg'] == 'Test 1'

    @patch('logsync.HAS_REQUESTS', True)
    def test_send_batch_makes_http_request(self):
        """_send_batch makes HTTP POST request."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DEFAULT_CONFIG.copy()
            config['log_file'] = os.path.join(tmpdir, 'test.jsonl')
            config['state_file'] = os.path.join(tmpdir, 'state.json')

            service = LogSyncService(config)

            with patch('logsync.requests') as mock_requests:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_requests.post.return_value = mock_response

                compressed = gzip.compress(b'test data')
                result = service._send_batch(compressed, 'batch-1', 1)

                assert result is True
                mock_requests.post.assert_called_once()

    @patch('logsync.HAS_REQUESTS', True)
    def test_sync_once_successful(self):
        """sync_once completes successfully with valid entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test.jsonl')

            # Write test entries
            with open(log_file, 'w') as f:
                for i in range(5):
                    entry = {'ts': f'2026-01-15T10:0{i}:00', 'msg': f'Message {i}'}
                    f.write(json.dumps(entry) + '\n')

            config = DEFAULT_CONFIG.copy()
            config['log_file'] = log_file
            config['state_file'] = os.path.join(tmpdir, 'state.json')
            config['enabled'] = True

            service = LogSyncService(config)

            with patch('logsync.requests') as mock_requests:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_requests.post.return_value = mock_response

                result = service.sync_once()

                assert result is True
                assert service.state.position > 0


class TestMockCloudAPI:
    """Test the MockCloudAPI for local testing."""

    def test_receive_batch_stores_entries(self):
        """receive_batch stores decompressed entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            api = MockCloudAPI(tmpdir)

            entries = [
                {'msg': 'Test 1', 'ts': '2026-01-15T10:00:00'},
                {'msg': 'Test 2', 'ts': '2026-01-15T10:01:00'},
            ]

            jsonl = '\n'.join(json.dumps(e) for e in entries)
            compressed = gzip.compress(jsonl.encode('utf-8'))

            result = api.receive_batch(
                compressed,
                batch_id='test-batch',
                device_id='TEST-DEVICE',
                deployment_id='test-deploy'
            )

            assert result is True

            # Check stored file
            stored_file = os.path.join(tmpdir, 'test-deploy_test-batch.json')
            assert os.path.exists(stored_file)

            with open(stored_file, 'r') as f:
                stored = json.load(f)

            assert stored['batch_id'] == 'test-batch'
            assert stored['entry_count'] == 2


class TestGetConfig:
    """Test the get_config function."""

    def test_default_config(self):
        """get_config returns default config without env vars."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_config()

            assert config['enabled'] is True
            assert config['batch_size'] == 1000

    def test_env_override(self):
        """get_config respects environment variable overrides."""
        with patch.dict(os.environ, {
            'LOGSYNC_ENABLED': 'false',
            'LOGSYNC_BATCH_SIZE': '500',
        }):
            config = get_config()

            assert config['enabled'] is False
            assert config['batch_size'] == 500

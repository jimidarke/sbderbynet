"""
DerbyNet Log Sync Service - Cloud Log Transmission
===================================================

Background service that syncs local JSON logs to the cloud for
support and troubleshooting purposes. Operates independently of
premium subscription status.

Version: 1.0.0
Date: 2026-01-15

FEATURES:
---------
    - Reads from local JSONL log file (/var/log/derbynet.jsonl)
    - Batches logs together (configurable batch size)
    - Compresses batches with gzip before transmission
    - Syncs to cloud when connectivity is available
    - Low priority - uses nice/ionice, won't block race operations
    - Tracks sync state to avoid re-syncing
    - Resilient to network failures (retries with backoff)
    - Works for ALL deployments (not just premium)

ARCHITECTURE:
-------------
    1. Service runs as systemd timer (every 5 minutes)
    2. Reads unsyncted logs from position file
    3. Batches into chunks of ~1000 entries
    4. Compresses with gzip (~10x compression for JSON)
    5. POSTs to cloud API endpoint
    6. Updates position file on success

LOG SYNC STATE FILE:
--------------------
    /var/lib/derbynet/logsync_state.json
    {
        "last_sync_position": 12345,      # Byte offset in log file
        "last_sync_timestamp": "...",     # ISO 8601
        "last_batch_id": "uuid",          # For deduplication
        "sync_failures": 0,               # Consecutive failures
        "total_synced": 98765             # Total bytes synced
    }

CLOUD API ENDPOINT:
-------------------
    POST https://api.soapboxderbynet.com/v1/logs/ingest
    Headers:
        X-Device-ID: DERBY-PI-001
        X-Deployment-ID: <deployment-uuid>
        Content-Type: application/gzip
        Content-Encoding: gzip
    Body: gzip-compressed JSONL

USAGE:
------
    # Run once (for testing)
    python logsync.py

    # Run as systemd service
    systemctl start derbynet-logsync.timer

ENVIRONMENT VARIABLES:
----------------------
    LOGSYNC_ENABLED=true           Enable/disable sync (default: true)
    LOGSYNC_ENDPOINT=https://...   Cloud API endpoint
    LOGSYNC_BATCH_SIZE=1000        Max logs per batch
    LOGSYNC_INTERVAL=300           Sync interval in seconds
    LOGSYNC_DEPLOYMENT_ID=uuid     Unique deployment identifier
"""

import gzip
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import threading

# Try to import requests, fall back to urllib
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False

from derbylogger import setup_logger, get_device_id

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default configuration (overridable via environment)
DEFAULT_CONFIG = {
    'enabled': True,
    'log_file': '/var/log/derbynet.jsonl',
    'state_file': '/var/lib/derbynet/logsync_state.json',
    'endpoint': 'https://api.soapboxderbynet.com/v1/logs/ingest',
    'batch_size': 1000,           # Max entries per batch
    'max_batch_bytes': 1048576,   # 1MB uncompressed max
    'sync_interval': 300,         # 5 minutes
    'retry_delay': 60,            # 1 minute on failure
    'max_retries': 3,             # Max retries before giving up on batch
    'connection_timeout': 30,     # HTTP timeout in seconds
}


def get_config() -> Dict[str, Any]:
    """Get configuration from environment variables with defaults."""
    config = DEFAULT_CONFIG.copy()

    # Override from environment
    if os.getenv('LOGSYNC_ENABLED'):
        config['enabled'] = os.getenv('LOGSYNC_ENABLED', 'true').lower() == 'true'

    if os.getenv('LOGSYNC_ENDPOINT'):
        config['endpoint'] = os.getenv('LOGSYNC_ENDPOINT')

    if os.getenv('LOGSYNC_BATCH_SIZE'):
        config['batch_size'] = int(os.getenv('LOGSYNC_BATCH_SIZE'))

    if os.getenv('LOGSYNC_INTERVAL'):
        config['sync_interval'] = int(os.getenv('LOGSYNC_INTERVAL'))

    if os.getenv('LOGSYNC_LOG_FILE'):
        config['log_file'] = os.getenv('LOGSYNC_LOG_FILE')

    if os.getenv('LOGSYNC_STATE_FILE'):
        config['state_file'] = os.getenv('LOGSYNC_STATE_FILE')

    return config


# ============================================================================
# SYNC STATE MANAGEMENT
# ============================================================================

class SyncState:
    """
    Manages sync state persistence.

    Tracks:
    - Last position in log file (byte offset)
    - Last sync timestamp
    - Consecutive failure count
    - Total bytes synced
    """

    def __init__(self, state_file: str):
        self.state_file = state_file
        self._lock = threading.Lock()
        self._state = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load state from file or return defaults."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            pass

        # Default state
        return {
            'last_sync_position': 0,
            'last_sync_timestamp': None,
            'last_batch_id': None,
            'sync_failures': 0,
            'total_synced': 0,
            'deployment_id': os.getenv('LOGSYNC_DEPLOYMENT_ID') or str(uuid.uuid4()),
        }

    def _save(self):
        """Save state to file."""
        try:
            state_dir = os.path.dirname(self.state_file)
            if state_dir:
                os.makedirs(state_dir, exist_ok=True)

            with open(self.state_file, 'w') as f:
                json.dump(self._state, f, indent=2)
        except IOError as e:
            pass  # Silent failure - state will be reconstructed

    @property
    def position(self) -> int:
        """Get last sync position (byte offset)."""
        with self._lock:
            return self._state.get('last_sync_position', 0)

    @property
    def deployment_id(self) -> str:
        """Get unique deployment identifier."""
        with self._lock:
            return self._state.get('deployment_id', '')

    @property
    def failures(self) -> int:
        """Get consecutive failure count."""
        with self._lock:
            return self._state.get('sync_failures', 0)

    def update_success(self, new_position: int, batch_id: str, bytes_synced: int):
        """Update state after successful sync."""
        with self._lock:
            self._state['last_sync_position'] = new_position
            self._state['last_sync_timestamp'] = datetime.now().isoformat()
            self._state['last_batch_id'] = batch_id
            self._state['sync_failures'] = 0
            self._state['total_synced'] = self._state.get('total_synced', 0) + bytes_synced
            self._save()

    def update_failure(self):
        """Update state after failed sync."""
        with self._lock:
            self._state['sync_failures'] = self._state.get('sync_failures', 0) + 1
            self._save()

    def reset_failures(self):
        """Reset failure count (e.g., after connectivity restored)."""
        with self._lock:
            self._state['sync_failures'] = 0
            self._save()


# ============================================================================
# LOG READER
# ============================================================================

class LogReader:
    """
    Reads log entries from JSONL file starting from a position.

    Features:
    - Handles file rotation (detects if file was truncated)
    - Validates JSON lines
    - Batches entries efficiently
    """

    def __init__(self, log_file: str):
        self.log_file = log_file

    def read_batch(self, start_position: int, max_entries: int,
                   max_bytes: int) -> Tuple[List[Dict], int]:
        """
        Read a batch of log entries starting from position.

        Args:
            start_position: Byte offset to start reading from
            max_entries: Maximum entries to read
            max_bytes: Maximum uncompressed bytes to read

        Returns:
            Tuple of (list of log entries, new position)
        """
        entries = []
        new_position = start_position
        bytes_read = 0

        try:
            if not os.path.exists(self.log_file):
                return [], 0

            file_size = os.path.getsize(self.log_file)

            # Handle file rotation (file smaller than position)
            if file_size < start_position:
                start_position = 0

            with open(self.log_file, 'r') as f:
                f.seek(start_position)

                for line in f:
                    if len(entries) >= max_entries:
                        break

                    if bytes_read + len(line) > max_bytes:
                        break

                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)
                        entries.append(entry)
                        bytes_read += len(line)
                    except json.JSONDecodeError:
                        # Skip malformed lines
                        pass

                new_position = f.tell()

        except IOError:
            pass

        return entries, new_position

    def has_new_entries(self, position: int) -> bool:
        """Check if there are new entries since position."""
        try:
            if not os.path.exists(self.log_file):
                return False

            file_size = os.path.getsize(self.log_file)
            return file_size > position
        except IOError:
            return False


# ============================================================================
# LOG SYNC SERVICE
# ============================================================================

class LogSyncService:
    """
    Background service for syncing logs to cloud.

    Designed to be:
    - Low priority (won't interfere with race operations)
    - Resilient (handles failures gracefully)
    - Efficient (batches and compresses logs)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config()
        self.logger = setup_logger('logsync', log_file=None, console=True)
        self.state = SyncState(self.config['state_file'])
        self.reader = LogReader(self.config['log_file'])
        self.device_id = get_device_id()
        self._running = False

    def sync_once(self) -> bool:
        """
        Perform a single sync operation.

        Returns:
            True if sync was successful or no new logs, False on error
        """
        if not self.config['enabled']:
            self.logger.debug("Log sync disabled")
            return True

        # Check for new entries
        if not self.reader.has_new_entries(self.state.position):
            self.logger.debug("No new log entries to sync")
            return True

        # Read batch
        entries, new_position = self.reader.read_batch(
            self.state.position,
            self.config['batch_size'],
            self.config['max_batch_bytes']
        )

        if not entries:
            self.logger.debug("No entries read (empty batch)")
            return True

        # Generate batch ID
        batch_id = str(uuid.uuid4())[:12]

        # Add sync metadata to entries
        for entry in entries:
            entry['_batch_id'] = batch_id
            entry['_device_id'] = self.device_id
            entry['_deployment_id'] = self.state.deployment_id

        # Compress batch
        compressed = self._compress_batch(entries)

        self.logger.info(f"Syncing batch {batch_id}: {len(entries)} entries, "
                        f"{len(compressed)} bytes compressed")

        # Send to cloud
        success = self._send_batch(compressed, batch_id, len(entries))

        if success:
            self.state.update_success(new_position, batch_id, len(compressed))
            self.logger.info(f"Batch {batch_id} synced successfully")
            return True
        else:
            self.state.update_failure()
            self.logger.warning(f"Batch {batch_id} sync failed "
                              f"(failures: {self.state.failures})")
            return False

    def _compress_batch(self, entries: List[Dict]) -> bytes:
        """Compress batch of entries with gzip."""
        # Convert to JSONL
        jsonl = '\n'.join(json.dumps(e, separators=(',', ':')) for e in entries)

        # Compress
        return gzip.compress(jsonl.encode('utf-8'))

    def _send_batch(self, compressed: bytes, batch_id: str,
                    entry_count: int) -> bool:
        """Send compressed batch to cloud API."""
        headers = {
            'Content-Type': 'application/gzip',
            'Content-Encoding': 'gzip',
            'X-Device-ID': self.device_id,
            'X-Deployment-ID': self.state.deployment_id,
            'X-Batch-ID': batch_id,
            'X-Entry-Count': str(entry_count),
        }

        endpoint = self.config['endpoint']
        timeout = self.config['connection_timeout']

        try:
            if HAS_REQUESTS:
                response = requests.post(
                    endpoint,
                    data=compressed,
                    headers=headers,
                    timeout=timeout
                )
                return response.status_code in (200, 201, 202)
            else:
                # Fallback to urllib
                req = urllib.request.Request(
                    endpoint,
                    data=compressed,
                    headers=headers,
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.status in (200, 201, 202)

        except Exception as e:
            self.logger.warning(f"HTTP error during sync: {e}")
            return False

    def run_daemon(self):
        """Run as background daemon with periodic sync."""
        self._running = True
        self.logger.info("Log sync service started")

        while self._running:
            try:
                self.sync_once()
            except Exception as e:
                self.logger.error(f"Sync error: {e}")

            # Calculate next sync time (with backoff on failures)
            delay = self.config['sync_interval']
            if self.state.failures > 0:
                delay = min(delay * (2 ** self.state.failures),
                           delay * 10)  # Max 10x delay

            time.sleep(delay)

    def stop(self):
        """Stop the daemon."""
        self._running = False


# ============================================================================
# CLOUD API MOCK (for testing)
# ============================================================================

class MockCloudAPI:
    """
    Mock cloud API for local testing.

    Stores received batches in /var/lib/derbynet/logsync_mock/
    """

    def __init__(self, storage_dir: str = '/var/lib/derbynet/logsync_mock'):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def receive_batch(self, compressed: bytes, batch_id: str,
                      device_id: str, deployment_id: str) -> bool:
        """Receive and store a batch (simulates cloud API)."""
        try:
            # Decompress
            jsonl = gzip.decompress(compressed).decode('utf-8')
            entries = [json.loads(line) for line in jsonl.split('\n') if line]

            # Store
            filename = f"{deployment_id}_{batch_id}.json"
            filepath = os.path.join(self.storage_dir, filename)

            with open(filepath, 'w') as f:
                json.dump({
                    'batch_id': batch_id,
                    'device_id': device_id,
                    'deployment_id': deployment_id,
                    'received_at': datetime.now().isoformat(),
                    'entry_count': len(entries),
                    'entries': entries,
                }, f, indent=2)

            return True
        except Exception:
            return False


# ============================================================================
# CLI / MAIN
# ============================================================================

def main():
    """Run log sync service."""
    import argparse

    parser = argparse.ArgumentParser(description='DerbyNet Log Sync Service')
    parser.add_argument('--daemon', action='store_true',
                        help='Run as background daemon')
    parser.add_argument('--once', action='store_true',
                        help='Run single sync and exit')
    parser.add_argument('--status', action='store_true',
                        help='Show sync status')
    parser.add_argument('--config', action='store_true',
                        help='Show configuration')

    args = parser.parse_args()

    config = get_config()
    service = LogSyncService(config)

    if args.config:
        print("Log Sync Configuration:")
        for key, value in config.items():
            print(f"  {key}: {value}")
        return

    if args.status:
        print("Log Sync Status:")
        print(f"  Deployment ID: {service.state.deployment_id}")
        print(f"  Last position: {service.state.position} bytes")
        print(f"  Failures: {service.state.failures}")
        print(f"  Log file exists: {os.path.exists(config['log_file'])}")
        if os.path.exists(config['log_file']):
            size = os.path.getsize(config['log_file'])
            pending = max(0, size - service.state.position)
            print(f"  Log file size: {size} bytes")
            print(f"  Pending sync: {pending} bytes")
        return

    if args.once:
        success = service.sync_once()
        print("Sync successful" if success else "Sync failed")
        return

    if args.daemon:
        try:
            service.run_daemon()
        except KeyboardInterrupt:
            service.stop()
            print("\nLog sync service stopped")
        return

    # Default: single sync
    success = service.sync_once()
    print("Sync successful" if success else "Sync failed")


if __name__ == '__main__':
    main()

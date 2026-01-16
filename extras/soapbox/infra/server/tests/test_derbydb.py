"""
Unit tests for derbydb.py - Direct SQLite database access module.

Tests cover:
- Database initialization and WAL mode
- RaceInfo key-value operations
- Race results writing and place calculation
- Heat advancement
- Thread safety under concurrent access
"""

import pytest
import sqlite3
import threading
import time
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from derbydb import DerbyDatabase, get_database


class TestDerbyDatabaseInit:
    """Tests for database initialization."""

    def test_init_with_valid_path(self, populated_db):
        """Database should initialize successfully with valid path."""
        db = DerbyDatabase(populated_db)
        assert db.conn is not None
        assert db.db_path == populated_db
        db.close()

    def test_init_with_invalid_path(self, tmp_path):
        """Database should raise FileNotFoundError for non-existent file."""
        invalid_path = str(tmp_path / "nonexistent.sqlite3")
        with pytest.raises(FileNotFoundError) as exc_info:
            DerbyDatabase(invalid_path)
        assert "Database not found" in str(exc_info.value)

    def test_wal_mode_enabled(self, populated_db):
        """Database should enable WAL mode on initialization."""
        db = DerbyDatabase(populated_db)
        cursor = db.conn.execute('PRAGMA journal_mode')
        mode = cursor.fetchone()[0]
        assert mode.lower() == 'wal'
        db.close()

    def test_close_connection(self, populated_db):
        """close() should properly close the database connection."""
        db = DerbyDatabase(populated_db)
        assert db.conn is not None
        db.close()
        assert db.conn is None


class TestRaceInfoOperations:
    """Tests for RaceInfo key-value table operations."""

    def test_read_existing_key(self, derby_db):
        """read_raceinfo should return value for existing key."""
        value = derby_db.read_raceinfo('RoundID')
        assert value == '1'

    def test_read_missing_key_returns_default(self, derby_db):
        """read_raceinfo should return default for missing key."""
        value = derby_db.read_raceinfo('NonExistentKey', 'default_value')
        assert value == 'default_value'

    def test_read_missing_key_returns_none(self, derby_db):
        """read_raceinfo should return None for missing key with no default."""
        value = derby_db.read_raceinfo('NonExistentKey')
        assert value is None

    def test_write_new_key(self, derby_db):
        """write_raceinfo should insert new key-value pair."""
        derby_db.write_raceinfo('TestKey', 'TestValue')
        value = derby_db.read_raceinfo('TestKey')
        assert value == 'TestValue'

    def test_write_update_existing_key(self, derby_db):
        """write_raceinfo should update existing key."""
        derby_db.write_raceinfo('RoundID', '99')
        value = derby_db.read_raceinfo('RoundID')
        assert value == '99'

    def test_read_boolean_true_values(self, derby_db):
        """read_raceinfo_boolean should return True for '1' or 'true'."""
        derby_db.write_raceinfo('BoolTest1', '1')
        derby_db.write_raceinfo('BoolTest2', 'true')
        derby_db.write_raceinfo('BoolTest3', 'True')

        assert derby_db.read_raceinfo_boolean('BoolTest1') is True
        assert derby_db.read_raceinfo_boolean('BoolTest2') is True
        assert derby_db.read_raceinfo_boolean('BoolTest3') is True

    def test_read_boolean_false_values(self, derby_db):
        """read_raceinfo_boolean should return False for '0' or other values."""
        derby_db.write_raceinfo('BoolTest', '0')
        assert derby_db.read_raceinfo_boolean('BoolTest') is False

        derby_db.write_raceinfo('BoolTest', 'false')
        assert derby_db.read_raceinfo_boolean('BoolTest') is False

    def test_read_boolean_missing_key_default(self, derby_db):
        """read_raceinfo_boolean should return default for missing key."""
        assert derby_db.read_raceinfo_boolean('MissingKey') is False
        assert derby_db.read_raceinfo_boolean('MissingKey', True) is True


class TestRaceStateOperations:
    """Tests for race state retrieval."""

    def test_get_running_round(self, derby_db):
        """get_running_round should return current race state."""
        state = derby_db.get_running_round()

        assert state['roundid'] == 1
        assert state['heat'] == 34  # completed_db is on heat 34
        assert state['classid'] == 1
        assert state['now_racing'] is False
        assert state['class'] == 'Ages 6-8'  # Test data uses age-based classes
        assert state['round'] == 1

    def test_get_running_round_no_round(self, derby_db):
        """get_running_round should handle no active round gracefully."""
        derby_db.write_raceinfo('RoundID', '-1')
        state = derby_db.get_running_round()

        assert state['roundid'] == -1
        assert state['class'] == ''

    def test_get_lane_count(self, derby_db):
        """get_lane_count should return configured lane count."""
        count = derby_db.get_lane_count()
        assert count == 3  # Test data uses 3-lane track


class TestRaceResultsOperations:
    """Tests for race results writing."""

    def test_write_race_results_basic(self, derby_db):
        """write_race_results should write times and calculate places."""
        # Test data uses 3 lanes
        lane_times = {1: 3.456, 2: 3.789, 3: 3.600}
        success = derby_db.write_race_results(roundid=1, heat=1, lane_times=lane_times)

        assert success is True

        # Verify results were written
        with derby_db._lock:
            cursor = derby_db.conn.execute('''
                SELECT lane, finishtime, finishplace, completed
                FROM RaceChart
                WHERE roundid = 1 AND heat = 1
                ORDER BY lane
            ''')
            results = cursor.fetchall()

        assert len(results) == 3  # 3-lane track
        assert results[0]['lane'] == 1
        assert results[0]['finishtime'] == 3.456
        assert results[0]['finishplace'] == 1  # Fastest time = 1st place
        assert results[0]['completed'] is not None

        assert results[1]['lane'] == 2
        assert results[1]['finishtime'] == 3.789
        assert results[1]['finishplace'] == 3  # Slowest time = 3rd place

        assert results[2]['lane'] == 3
        assert results[2]['finishtime'] == 3.600
        assert results[2]['finishplace'] == 2  # Middle time = 2nd place

    def test_write_race_results_with_explicit_places(self, derby_db):
        """write_race_results should use provided places when given."""
        lane_times = {1: 3.456, 2: 3.789}
        lane_places = {1: 2, 2: 1}  # Override: lane 2 wins despite slower time
        success = derby_db.write_race_results(
            roundid=1, heat=1,
            lane_times=lane_times,
            lane_places=lane_places
        )

        assert success is True

        # Verify places match provided values
        with derby_db._lock:
            cursor = derby_db.conn.execute('''
                SELECT lane, finishplace FROM RaceChart
                WHERE roundid = 1 AND heat = 1 ORDER BY lane
            ''')
            results = cursor.fetchall()

        assert results[0]['finishplace'] == 2  # Lane 1 = 2nd
        assert results[1]['finishplace'] == 1  # Lane 2 = 1st

    def test_write_race_results_tie_handling(self, derby_db):
        """write_race_results should handle ties correctly."""
        lane_times = {1: 3.500, 2: 3.500}  # Exact tie
        success = derby_db.write_race_results(roundid=1, heat=1, lane_times=lane_times)

        assert success is True

        # Both should get 1st place (tie)
        with derby_db._lock:
            cursor = derby_db.conn.execute('''
                SELECT lane, finishplace FROM RaceChart
                WHERE roundid = 1 AND heat = 1 ORDER BY lane
            ''')
            results = cursor.fetchall()

        assert results[0]['finishplace'] == 1
        assert results[1]['finishplace'] == 1

    def test_write_race_results_records_last_heat(self, derby_db):
        """write_race_results should update last-heat tracking."""
        lane_times = {1: 3.456, 2: 3.789}
        derby_db.write_race_results(roundid=1, heat=1, lane_times=lane_times)

        assert derby_db.read_raceinfo('last-heat-roundid') == '1'
        assert derby_db.read_raceinfo('last-heat-heat') == '1'

    def test_clear_heat_results(self, derby_db):
        """clear_heat_results should reset times and places."""
        # First write some results
        lane_times = {1: 3.456, 2: 3.789}
        derby_db.write_race_results(roundid=1, heat=1, lane_times=lane_times)

        # Now clear them
        success = derby_db.clear_heat_results(roundid=1, heat=1)
        assert success is True

        # Verify results are cleared
        with derby_db._lock:
            cursor = derby_db.conn.execute('''
                SELECT finishtime, finishplace, completed FROM RaceChart
                WHERE roundid = 1 AND heat = 1
            ''')
            results = cursor.fetchall()

        for result in results:
            assert result['finishtime'] is None
            assert result['finishplace'] is None
            assert result['completed'] is None


class TestHeatAdvancement:
    """Tests for heat advancement functionality."""

    def test_advance_heat_to_next(self, derby_db_scheduled):
        """advance_heat should move to next heat in round."""
        # scheduled_db starts at heat 1
        roundid, heat = derby_db_scheduled.advance_heat()

        assert roundid == 1
        assert heat == 2  # Advanced from heat 1 to heat 2
        assert derby_db_scheduled.read_raceinfo('Heat') == '2'

    def test_advance_heat_end_of_round(self, derby_db_scheduled):
        """advance_heat should return None when round complete."""
        # Move to last heat (34 heats in test data)
        derby_db_scheduled.write_raceinfo('Heat', '34')

        roundid, heat = derby_db_scheduled.advance_heat()

        assert roundid is None
        assert heat is None
        assert derby_db_scheduled.read_raceinfo('NowRacingState') == '0'

    def test_advance_heat_no_round(self, derby_db):
        """advance_heat should handle no active round."""
        derby_db.write_raceinfo('RoundID', '-1')

        roundid, heat = derby_db.advance_heat()

        assert roundid is None
        assert heat is None


class TestActionHistory:
    """Tests for action history recording."""

    def test_record_action_basic(self, derby_db):
        """record_action should insert action into ActionHistory."""
        derby_db.record_action('test.action', {'key': 'value'})

        with derby_db._lock:
            cursor = derby_db.conn.execute(
                'SELECT request FROM ActionHistory ORDER BY historyid DESC LIMIT 1'
            )
            result = cursor.fetchone()

        import json
        payload = json.loads(result['request'])
        assert payload['action'] == 'test.action'
        assert payload['key'] == 'value'


@pytest.mark.threading
class TestThreadSafety:
    """Tests for thread safety under concurrent access."""

    def test_concurrent_raceinfo_writes(self, derby_db):
        """Multiple threads should safely write to RaceInfo."""
        errors = []
        results = {}

        def writer(thread_id, count):
            try:
                for i in range(count):
                    key = f'thread_{thread_id}_key_{i}'
                    value = f'value_{thread_id}_{i}'
                    derby_db.write_raceinfo(key, value)
                    # Verify immediately
                    read_value = derby_db.read_raceinfo(key)
                    if read_value != value:
                        errors.append(f"Thread {thread_id}: expected {value}, got {read_value}")
                results[thread_id] = count
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        threads = []
        for i in range(5):
            t = threading.Thread(target=writer, args=(i, 20))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent writes: {errors}"
        assert len(results) == 5, "Not all threads completed"

    def test_concurrent_race_results(self, derby_db):
        """Multiple threads should safely write race results."""
        errors = []

        def write_result(heat):
            try:
                lane_times = {1: 3.0 + heat * 0.1, 2: 3.1 + heat * 0.1}
                # Note: Using same roundid but different heats
                success = derby_db.write_race_results(roundid=1, heat=heat, lane_times=lane_times)
                if not success:
                    errors.append(f"Heat {heat}: write_race_results returned False")
            except Exception as e:
                errors.append(f"Heat {heat}: {e}")

        threads = [
            threading.Thread(target=write_result, args=(1,)),
            threading.Thread(target=write_result, args=(2,)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent race results: {errors}"

    def test_read_write_contention(self, derby_db):
        """Reads should not block on writes and vice versa."""
        read_count = 0
        write_count = 0
        errors = []
        stop_flag = threading.Event()

        def reader():
            nonlocal read_count
            try:
                while not stop_flag.is_set():
                    derby_db.read_raceinfo('RoundID')
                    read_count += 1
            except Exception as e:
                errors.append(f"Reader: {e}")

        def writer():
            nonlocal write_count
            try:
                for i in range(100):
                    derby_db.write_raceinfo('WriteTest', str(i))
                    write_count += 1
            except Exception as e:
                errors.append(f"Writer: {e}")

        reader_threads = [threading.Thread(target=reader) for _ in range(3)]
        writer_thread = threading.Thread(target=writer)

        for t in reader_threads:
            t.start()
        writer_thread.start()

        writer_thread.join()
        stop_flag.set()

        for t in reader_threads:
            t.join()

        assert len(errors) == 0, f"Errors during contention test: {errors}"
        assert write_count == 100, f"Expected 100 writes, got {write_count}"
        assert read_count > 0, "Readers were blocked"


class TestSingletonAccess:
    """Tests for the singleton get_database() function."""

    def test_get_database_requires_path_first_call(self, monkeypatch):
        """get_database should require path on first call if env var not set."""
        # Clear the singleton and env var
        import derbydb
        derbydb._db_instance = None
        monkeypatch.delenv('DERBYNET_DB_PATH', raising=False)

        with pytest.raises(ValueError) as exc_info:
            get_database()
        assert "Database path required" in str(exc_info.value)

    def test_get_database_uses_env_var(self, populated_db, monkeypatch):
        """get_database should use DERBYNET_DB_PATH environment variable."""
        import derbydb
        derbydb._db_instance = None
        monkeypatch.setenv('DERBYNET_DB_PATH', populated_db)

        db = get_database()
        assert db is not None
        assert db.db_path == populated_db

        # Cleanup
        db.close()
        derbydb._db_instance = None

    def test_get_database_returns_singleton(self, populated_db, monkeypatch):
        """get_database should return same instance on subsequent calls."""
        import derbydb
        derbydb._db_instance = None
        monkeypatch.setenv('DERBYNET_DB_PATH', populated_db)

        db1 = get_database()
        db2 = get_database()

        assert db1 is db2

        # Cleanup
        db1.close()
        derbydb._db_instance = None

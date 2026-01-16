"""
Schema validation tests for DerbyNet database.

These tests verify that:
1. The Python test schema matches expected DerbyNet structure
2. Key tables and columns exist
3. Schema can be initialized successfully

When making schema changes in PHP, update tests/schema.sql and these tests.
"""

import pytest
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSchemaInitialization:
    """Tests for database schema initialization."""

    def test_schema_creates_all_core_tables(self, initialized_db):
        """All core DerbyNet tables should be created."""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()

        # Query for all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cursor.fetchall()}

        conn.close()

        # Core tables that must exist
        required_tables = {
            'RaceInfo',
            'Classes',
            'Ranks',
            'RegistrationInfo',
            'Rounds',
            'RaceChart',
            'ActionHistory',
            'Awards',
            'AwardTypes',
        }

        missing = required_tables - tables
        assert not missing, f"Missing required tables: {missing}"

    def test_schema_creates_elimination_tables(self, initialized_db):
        """Elimination tournament tables should be created."""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cursor.fetchall()}

        conn.close()

        elimination_tables = {
            'EliminationTournaments',
            'EliminationRoundState',
            'EliminationAdvancement',
        }

        missing = elimination_tables - tables
        assert not missing, f"Missing elimination tables: {missing}"

    def test_wal_mode_enabled(self, initialized_db):
        """WAL mode should be enabled for concurrent access."""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()

        cursor.execute('PRAGMA journal_mode')
        mode = cursor.fetchone()[0]

        conn.close()

        assert mode.lower() == 'wal', f"Expected WAL mode, got {mode}"


class TestRaceInfoTable:
    """Tests for RaceInfo table structure (key-value store)."""

    def test_raceinfo_has_required_columns(self, initialized_db):
        """RaceInfo should have itemkey and itemvalue columns."""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(RaceInfo)")
        columns = {row[1] for row in cursor.fetchall()}

        conn.close()

        assert 'itemkey' in columns
        assert 'itemvalue' in columns

    def test_raceinfo_default_values(self, initialized_db):
        """RaceInfo should have default configuration values."""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()

        cursor.execute("SELECT itemkey FROM RaceInfo")
        keys = {row[0] for row in cursor.fetchall()}

        conn.close()

        # Check for expected default keys (from schema.sql)
        expected_keys = {'schema', 'photos-on-now-racing'}
        present = expected_keys & keys

        assert len(present) > 0, "No default RaceInfo values found"


class TestRaceChartTable:
    """Tests for RaceChart table structure (race results)."""

    def test_racechart_has_required_columns(self, initialized_db):
        """RaceChart should have all columns needed for race results."""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(RaceChart)")
        columns = {row[1] for row in cursor.fetchall()}

        conn.close()

        required_columns = {
            'resultid',
            'roundid',
            'heat',
            'lane',
            'racerid',
            'finishtime',
            'finishplace',
            'completed',
        }

        missing = required_columns - columns
        assert not missing, f"Missing RaceChart columns: {missing}"

    def test_racechart_finishtime_allows_null(self, initialized_db):
        """finishtime should allow NULL for unfinished races."""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()

        # Insert a race entry without finishtime
        cursor.execute("""
            INSERT INTO Classes (classid, class) VALUES (99, 'Test Class')
        """)
        cursor.execute("""
            INSERT INTO Rounds (roundid, classid, round) VALUES (99, 99, 1)
        """)
        cursor.execute("""
            INSERT INTO RaceChart (resultid, roundid, heat, lane, finishtime)
            VALUES (999, 99, 1, 1, NULL)
        """)

        conn.commit()

        # Verify NULL is stored
        cursor.execute("SELECT finishtime FROM RaceChart WHERE resultid = 999")
        result = cursor.fetchone()

        conn.close()

        assert result[0] is None


class TestRegistrationInfoTable:
    """Tests for RegistrationInfo table (racer data)."""

    def test_registrationinfo_has_pii_columns(self, initialized_db):
        """RegistrationInfo should have name columns (PII - local only)."""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(RegistrationInfo)")
        columns = {row[1] for row in cursor.fetchall()}

        conn.close()

        pii_columns = {'firstname', 'lastname'}
        assert pii_columns.issubset(columns), "PII columns missing"

    def test_registrationinfo_has_carnumber(self, initialized_db):
        """RegistrationInfo should have carnumber (pinny) for public sync."""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(RegistrationInfo)")
        columns = {row[1] for row in cursor.fetchall()}

        conn.close()

        assert 'carnumber' in columns, "carnumber (pinny) column missing"


class TestIndexes:
    """Tests for database indexes."""

    def test_raceinfo_itemkey_indexed(self, initialized_db):
        """RaceInfo.itemkey should be indexed for fast lookups."""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='RaceInfo'")
        indexes = {row[0] for row in cursor.fetchall()}

        conn.close()

        # Should have an index on itemkey
        assert any('itemkey' in idx.lower() for idx in indexes), "No index on RaceInfo.itemkey"

    def test_racechart_roundid_indexed(self, initialized_db):
        """RaceChart.roundid should be indexed for heat queries."""
        conn = sqlite3.connect(initialized_db)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='RaceChart'")
        indexes = {row[0] for row in cursor.fetchall()}

        conn.close()

        assert any('roundid' in idx.lower() for idx in indexes), "No index on RaceChart.roundid"


class TestSchemaCompatibility:
    """Tests ensuring Python and PHP schema compatibility."""

    def test_derbydb_can_read_schema(self, initialized_db):
        """derbydb.py should work with the test schema."""
        from derbydb import DerbyDatabase

        db = DerbyDatabase(initialized_db)

        # Should be able to read from RaceInfo
        value = db.read_raceinfo('schema')
        assert value is not None, "Could not read schema version from RaceInfo"

        db.close()

    def test_derbydb_can_write_schema(self, populated_db):
        """derbydb.py should be able to write to all required tables."""
        from derbydb import DerbyDatabase

        db = DerbyDatabase(populated_db)

        # Test RaceInfo write
        db.write_raceinfo('test_key', 'test_value')
        assert db.read_raceinfo('test_key') == 'test_value'

        # Test race results write
        success = db.write_race_results(
            roundid=1,
            heat=1,
            lane_times={1: 3.456, 2: 3.789}
        )
        assert success, "Failed to write race results"

        # Test action history
        db.record_action('test.action', {'test': True})

        db.close()

"""
Pytest configuration and fixtures for DerbyNet server tests.

Provides test database fixtures at different states:
- empty_db: Schema only, no data
- registered_db: Classes, ranks, 107 racers (pre-race registration)
- scheduled_db: Above + rounds and scheduled heats (no results)
- completed_db: Above + 102 completed race results

Also provides mock MQTT clients and environment variable utilities.

The database schema used here mirrors the PHP-defined schema in website/sql/sqlite/.
Test data is extracted from a real DerbyNet event for realistic testing.
"""

import pytest
import sqlite3
import tempfile
import os
import sys
import shutil
from pathlib import Path

# Add tests directory to path for test_data import
sys.path.insert(0, str(Path(__file__).parent))

from test_data import (
    CLASSES, RANKS, RACERS, ROUNDS, RACE_RESULTS,
    RACEINFO_EMPTY, RACEINFO_PRE_RACE, RACEINFO_MID_RACE, RACEINFO_COMPLETED,
    get_scheduled_heats,
)


# Path to the SQL schema file
SCHEMA_SQL_PATH = Path(__file__).parent / "schema.sql"


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database file path."""
    db_path = tmp_path / "test_derby.sqlite3"
    return str(db_path)


def _init_schema(db_path: str) -> None:
    """Initialize database with DerbyNet schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable WAL mode like production
    cursor.execute('PRAGMA journal_mode=WAL')

    # Load and execute the schema SQL
    if SCHEMA_SQL_PATH.exists():
        schema_sql = SCHEMA_SQL_PATH.read_text()
        cursor.executescript(schema_sql)
    else:
        # Fallback to minimal schema if schema.sql not found
        _create_minimal_schema(cursor)

    conn.commit()
    conn.close()


def _create_minimal_schema(cursor):
    """
    Create minimal schema as fallback.

    This should only be used if schema.sql is missing.
    Prefer using the full schema for accurate testing.
    """
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS RaceInfo (
            raceinfoid INTEGER PRIMARY KEY,
            itemkey VARCHAR(20) NOT NULL,
            itemvalue VARCHAR(200)
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS RaceInfo_itemkey ON RaceInfo(itemkey)')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Classes (
            classid INTEGER PRIMARY KEY,
            class VARCHAR(75) NOT NULL UNIQUE COLLATE NOCASE,
            sortorder INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Ranks (
            rankid INTEGER PRIMARY KEY,
            rank VARCHAR(75) NOT NULL COLLATE NOCASE,
            classid INTEGER NOT NULL,
            sortorder INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Rounds (
            roundid INTEGER PRIMARY KEY,
            classid INTEGER NOT NULL,
            round INTEGER NOT NULL,
            roundname VARCHAR NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS RegistrationInfo (
            racerid INTEGER PRIMARY KEY,
            carnumber INTEGER NOT NULL,
            firstname VARCHAR(30) NOT NULL,
            lastname VARCHAR(30) NOT NULL,
            classid INTEGER NOT NULL,
            rankid INTEGER NOT NULL,
            partitionid INTEGER NOT NULL DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS RaceChart (
            resultid INTEGER PRIMARY KEY,
            roundid INTEGER NOT NULL,
            heat INTEGER NOT NULL,
            lane INTEGER NOT NULL,
            racerid INTEGER,
            finishtime DOUBLE NULL,
            finishplace INTEGER,
            completed TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ActionHistory (
            historyid INTEGER PRIMARY KEY,
            received TIMESTAMP,
            request TEXT
        )
    ''')


def _insert_raceinfo(cursor, raceinfo: dict) -> None:
    """Insert RaceInfo key-value pairs."""
    for key, value in raceinfo.items():
        cursor.execute(
            "INSERT OR REPLACE INTO RaceInfo (itemkey, itemvalue) VALUES (?, ?)",
            (key, value)
        )


def _insert_classes(cursor) -> None:
    """Insert all classes from test data."""
    for cls in CLASSES:
        cursor.execute(
            "INSERT INTO Classes (classid, class, sortorder) VALUES (?, ?, ?)",
            (cls["classid"], cls["class"], cls["sortorder"])
        )


def _insert_ranks(cursor) -> None:
    """Insert all ranks from test data."""
    for rank in RANKS:
        cursor.execute(
            "INSERT INTO Ranks (rankid, rank, classid, sortorder) VALUES (?, ?, ?, ?)",
            (rank["rankid"], rank["rank"], rank["classid"], rank["sortorder"])
        )


def _insert_racers(cursor) -> None:
    """Insert all 107 racers from test data."""
    for racer in RACERS:
        cursor.execute(
            """INSERT INTO RegistrationInfo
               (racerid, carnumber, firstname, lastname, classid, rankid, partitionid)
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            (racer["racerid"], racer["carnumber"], racer["firstname"],
             racer["lastname"], racer["classid"], racer["rankid"])
        )


def _insert_rounds(cursor) -> None:
    """Insert all rounds from test data."""
    for rnd in ROUNDS:
        cursor.execute(
            "INSERT INTO Rounds (roundid, classid, round, roundname) VALUES (?, ?, ?, ?)",
            (rnd["roundid"], rnd["classid"], rnd["round"], rnd["roundname"])
        )


def _insert_scheduled_heats(cursor, num_heats: int = 34) -> None:
    """Insert scheduled heats without results."""
    heats = get_scheduled_heats(roundid=1, num_heats=num_heats)
    for heat in heats:
        cursor.execute(
            """INSERT INTO RaceChart
               (resultid, roundid, heat, lane, racerid, finishtime, finishplace)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (heat["resultid"], heat["roundid"], heat["heat"], heat["lane"],
             heat["racerid"], heat["finishtime"], heat["finishplace"])
        )


def _insert_race_results(cursor) -> None:
    """Insert all completed race results from test data."""
    for result in RACE_RESULTS:
        cursor.execute(
            """INSERT INTO RaceChart
               (resultid, roundid, heat, lane, racerid, finishtime, finishplace)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (result["resultid"], result["roundid"], result["heat"], result["lane"],
             result["racerid"], result["finishtime"], result["finishplace"])
        )


# =============================================================================
# Database Fixtures - Different States
# =============================================================================

@pytest.fixture
def empty_db(temp_db_path):
    """
    Database with schema only, no data.

    Use for testing initial setup, schema validation, or empty-state handling.
    """
    _init_schema(temp_db_path)

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    _insert_raceinfo(cursor, RACEINFO_EMPTY)
    conn.commit()
    conn.close()

    return temp_db_path


@pytest.fixture
def registered_db(temp_db_path):
    """
    Database with 107 registered racers, ready for race scheduling.

    Contains:
    - 3 classes (Ages 6-8, 9-11, 12-14)
    - 3 ranks (one per class)
    - 107 racers with realistic names
    - No rounds or race schedule yet

    Use for testing registration, check-in, and pre-race workflows.
    """
    _init_schema(temp_db_path)

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    _insert_classes(cursor)
    _insert_ranks(cursor)
    _insert_racers(cursor)
    _insert_raceinfo(cursor, RACEINFO_PRE_RACE)

    conn.commit()
    conn.close()

    return temp_db_path


@pytest.fixture
def scheduled_db(temp_db_path):
    """
    Database with scheduled heats, ready to start racing.

    Contains:
    - Everything in registered_db
    - 11 rounds (Preliminary through Finals)
    - 34 scheduled heats (no results yet)

    Use for testing race start, heat advancement, and mid-race workflows.
    """
    _init_schema(temp_db_path)

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    _insert_classes(cursor)
    _insert_ranks(cursor)
    _insert_racers(cursor)
    _insert_rounds(cursor)
    _insert_scheduled_heats(cursor)
    _insert_raceinfo(cursor, RACEINFO_MID_RACE)

    conn.commit()
    conn.close()

    return temp_db_path


@pytest.fixture
def completed_db(temp_db_path):
    """
    Database with completed race results.

    Contains:
    - Everything in registered_db
    - 11 rounds
    - 102 completed heats with finish times (4.5s - 8.5s range)

    Use for testing results display, standings calculation, and post-race workflows.
    """
    _init_schema(temp_db_path)

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    _insert_classes(cursor)
    _insert_ranks(cursor)
    _insert_racers(cursor)
    _insert_rounds(cursor)
    _insert_race_results(cursor)
    _insert_raceinfo(cursor, RACEINFO_COMPLETED)

    conn.commit()
    conn.close()

    return temp_db_path


# =============================================================================
# Legacy Fixtures - Backward Compatibility
# =============================================================================

@pytest.fixture
def initialized_db(temp_db_path):
    """
    Legacy fixture: Empty database with schema.

    Equivalent to empty_db. Kept for backward compatibility.
    """
    _init_schema(temp_db_path)
    return temp_db_path


@pytest.fixture
def populated_db(completed_db):
    """
    Legacy fixture: Database with sample data.

    Now uses the full 107-racer dataset instead of minimal 4-racer synthetic data.
    Equivalent to completed_db. Kept for backward compatibility.
    """
    return completed_db


# =============================================================================
# DerbyDatabase Instance Fixtures
# =============================================================================

@pytest.fixture
def derby_db(completed_db):
    """
    DerbyDatabase instance connected to a completed test database.

    Automatically closes the database connection after the test.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from derbydb import DerbyDatabase

    db = DerbyDatabase(completed_db)
    yield db
    db.close()


@pytest.fixture
def derby_db_empty(empty_db):
    """
    DerbyDatabase instance connected to an empty database.

    Use for testing initial setup and empty-state handling.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from derbydb import DerbyDatabase

    db = DerbyDatabase(empty_db)
    yield db
    db.close()


@pytest.fixture
def derby_db_registered(registered_db):
    """
    DerbyDatabase instance connected to a registered (pre-race) database.

    Use for testing pre-race workflows.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from derbydb import DerbyDatabase

    db = DerbyDatabase(registered_db)
    yield db
    db.close()


@pytest.fixture
def derby_db_scheduled(scheduled_db):
    """
    DerbyDatabase instance connected to a scheduled (ready to race) database.

    Use for testing race execution workflows.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from derbydb import DerbyDatabase

    db = DerbyDatabase(scheduled_db)
    yield db
    db.close()


# =============================================================================
# Mock MQTT Client
# =============================================================================

@pytest.fixture
def mock_mqtt_client():
    """
    Create a mock MQTT client for testing without a broker.

    Returns a mock that tracks published messages and subscriptions.
    """
    class MockMQTTClient:
        def __init__(self):
            self.published_messages = []
            self.subscriptions = []
            self.connected = False
            self.on_connect = None
            self.on_message = None
            self.on_disconnect = None

        def connect(self, host, port=1883, keepalive=60):
            self.connected = True
            if self.on_connect:
                # Simulate successful connection callback
                self.on_connect(self, None, None, 0, None)

        def disconnect(self):
            self.connected = False
            if self.on_disconnect:
                self.on_disconnect(self, None, 0)

        def subscribe(self, topic, qos=0):
            self.subscriptions.append({'topic': topic, 'qos': qos})

        def publish(self, topic, payload, qos=0, retain=False):
            self.published_messages.append({
                'topic': topic,
                'payload': payload,
                'qos': qos,
                'retain': retain
            })

        def loop_start(self):
            pass

        def loop_stop(self):
            pass

        def simulate_message(self, topic, payload):
            """Simulate receiving a message (for testing callbacks)."""
            if self.on_message:
                class MockMessage:
                    def __init__(self, topic, payload):
                        self.topic = topic
                        self.payload = payload.encode() if isinstance(payload, str) else payload

                self.on_message(self, None, MockMessage(topic, payload))

    return MockMQTTClient()


# =============================================================================
# Environment Variable Utilities
# =============================================================================

@pytest.fixture
def env_vars(monkeypatch):
    """
    Fixture for testing environment variable configuration.

    Returns a helper function to set environment variables.
    """
    def set_env(**kwargs):
        for key, value in kwargs.items():
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, str(value))
    return set_env


@pytest.fixture
def temp_queue_dir(tmp_path):
    """Create a temporary directory for MessageQueue testing."""
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    return str(queue_dir)


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create a temporary directory for log file testing."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return str(log_dir)

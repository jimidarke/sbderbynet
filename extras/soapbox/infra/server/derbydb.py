"""
DerbyNet Direct Database Access Module

Provides direct SQLite database access for the Python race server,
eliminating the HTTP bridge to PHP for race-critical operations.

This module uses WAL mode for concurrent access - PHP can read while
Python writes race results.

Usage:
    from derbydb import DerbyDatabase

    db = DerbyDatabase('/var/lib/derbynet/2025/event1/derbynet.sqlite3')

    # Write race results
    db.write_race_results(roundid=1, heat=3, lane_times={1: 3.456, 2: 3.789, 3: 4.012})

    # Read/write race info
    db.write_raceinfo('NowRacingState', '1')
    state = db.read_raceinfo('NowRacingState')

Version: 0.1.2 - Uses unified DerbyLogger, fixed nested lock deadlock with RLock
"""

import sqlite3
import threading
import os
import time
from datetime import datetime
from typing import Dict, Optional, Any, List, Tuple

# Set up logging using unified logger
from derbylogger import setup_logger
logger = setup_logger('derbydb')


class DerbyDatabase:
    """
    Thread-safe SQLite database access for DerbyNet.

    Uses WAL mode for concurrent access and internal locking
    for thread safety within Python.
    """

    def __init__(self, db_path: str):
        """
        Initialize database connection.

        Args:
            db_path: Path to the SQLite database file
        """
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")

        self.db_path = db_path
        self._lock = threading.RLock()  # Reentrant lock for nested calls

        # Create connection with WAL mode
        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False,  # Allow multi-threaded access
            timeout=30.0  # Wait up to 30s for locks
        )
        self.conn.row_factory = sqlite3.Row

        # Enable WAL mode for concurrent access
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA busy_timeout=5000')  # 5s busy timeout
        self.conn.execute('PRAGMA synchronous=NORMAL')  # Good balance of safety/speed

        logger.info(f"DerbyDatabase initialized: {db_path}")

    def close(self):
        """Close the database connection."""
        with self._lock:
            if self.conn:
                self.conn.close()
                self.conn = None
                logger.info("Database connection closed")

    # =========================================================================
    # RaceInfo Table Operations (Key-Value Store)
    # =========================================================================

    def read_raceinfo(self, key: str, default: Any = None) -> Optional[str]:
        """
        Read a value from the RaceInfo key-value table.

        Args:
            key: The item key to read
            default: Value to return if key not found

        Returns:
            The item value, or default if not found
        """
        with self._lock:
            cursor = self.conn.execute(
                'SELECT itemvalue FROM RaceInfo WHERE itemkey = ?',
                (key,)
            )
            row = cursor.fetchone()
            return row['itemvalue'] if row else default

    def write_raceinfo(self, key: str, value: str) -> None:
        """
        Write a value to the RaceInfo key-value table.

        Uses UPSERT pattern (INSERT OR REPLACE).

        Args:
            key: The item key
            value: The item value
        """
        with self._lock:
            # Check if key exists
            cursor = self.conn.execute(
                'SELECT COUNT(*) as cnt FROM RaceInfo WHERE itemkey = ?',
                (key,)
            )
            exists = cursor.fetchone()['cnt'] > 0

            if exists:
                self.conn.execute(
                    'UPDATE RaceInfo SET itemvalue = ? WHERE itemkey = ?',
                    (value, key)
                )
            else:
                self.conn.execute(
                    'INSERT INTO RaceInfo (itemkey, itemvalue) VALUES (?, ?)',
                    (key, value)
                )
            self.conn.commit()
            logger.debug(f"RaceInfo: {key} = {value}")

    def read_raceinfo_boolean(self, key: str, default: bool = False) -> bool:
        """Read a boolean value from RaceInfo."""
        value = self.read_raceinfo(key)
        if value is None:
            return default
        return value == '1' or str(value).lower() == 'true'

    # =========================================================================
    # Race State Operations
    # =========================================================================

    def get_running_round(self) -> Dict[str, Any]:
        """
        Get the currently running round and heat information.

        Returns:
            Dictionary with roundid, heat, classid, class name, etc.
        """
        config = {
            'roundid': int(self.read_raceinfo('RoundID', -1) or -1),
            'heat': int(self.read_raceinfo('Heat', 1) or 1),
            'classid': int(self.read_raceinfo('ClassID', 1) or 1),
            'now_racing': self.read_raceinfo_boolean('NowRacingState'),
            'class': '',
            'round': 1,
        }

        if config['roundid'] > 0:
            with self._lock:
                cursor = self.conn.execute('''
                    SELECT Rounds.round, Rounds.roundname, Classes.classid, Classes.class
                    FROM Rounds
                    INNER JOIN Classes ON Classes.classid = Rounds.classid
                    WHERE Rounds.roundid = ? AND Rounds.classid = ?
                ''', (config['roundid'], config['classid']))
                row = cursor.fetchone()
                if row:
                    config['round'] = row['round']
                    config['roundname'] = row['roundname']
                    config['class'] = row['class']
                    config['classid'] = row['classid']

        return config

    def get_lane_count(self) -> int:
        """Get the configured number of lanes."""
        return int(self.read_raceinfo('lane_count', 0) or 0)

    # =========================================================================
    # Race Results Operations
    # =========================================================================

    def write_race_results(self, roundid: int, heat: int,
                          lane_times: Dict[int, float],
                          lane_places: Optional[Dict[int, int]] = None) -> bool:
        """
        Write race results to the RaceChart table.

        This is the critical race timing operation - writes finish times
        and places for all lanes in a heat.

        Args:
            roundid: The round ID
            heat: The heat number
            lane_times: Dictionary of {lane: finishtime} (DNF = 9.999 or None)
            lane_places: Optional dictionary of {lane: place}, auto-calculated if not provided

        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                # Get existing results for this heat
                cursor = self.conn.execute('''
                    SELECT resultid, lane, finishtime, finishplace
                    FROM RaceChart
                    WHERE roundid = ? AND heat = ?
                    ORDER BY lane
                ''', (roundid, heat))

                results = []
                for row in cursor:
                    lane = row['lane']
                    result = {
                        'resultid': row['resultid'],
                        'lane': lane,
                        'finishtime': lane_times.get(lane, row['finishtime']),
                        'finishplace': None
                    }
                    results.append(result)

                # Calculate places if not provided
                if lane_places:
                    for result in results:
                        result['finishplace'] = lane_places.get(result['lane'])
                else:
                    # Sort by time and assign places
                    valid_results = [r for r in results if r['finishtime'] is not None]
                    valid_results.sort(key=lambda x: float(x['finishtime']) if x['finishtime'] else 999.999)

                    place = 1
                    for i, result in enumerate(valid_results):
                        result['finishplace'] = place
                        # Handle ties
                        if i + 1 < len(valid_results):
                            if result['finishtime'] != valid_results[i + 1]['finishtime']:
                                place = i + 2

                    # Map back to original results list
                    place_map = {r['resultid']: r['finishplace'] for r in valid_results}
                    for result in results:
                        if result['resultid'] in place_map:
                            result['finishplace'] = place_map[result['resultid']]

                # Update database
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                for result in results:
                    self.conn.execute('''
                        UPDATE RaceChart
                        SET finishtime = ?, finishplace = ?, completed = ?
                        WHERE resultid = ?
                    ''', (result['finishtime'], result['finishplace'], now, result['resultid']))

                self.conn.commit()

                # Record last heat
                self._record_last_heat(roundid, heat)

                logger.info(f"Race results written: round={roundid}, heat={heat}, times={lane_times}")
                return True

        except Exception as e:
            logger.error(f"Failed to write race results: {e}")
            return False

    def _record_last_heat(self, roundid: int, heat: int) -> None:
        """Record the last completed heat for replay/history purposes."""
        self.write_raceinfo('last-heat-roundid', str(roundid))
        self.write_raceinfo('last-heat-heat', str(heat))

    def clear_heat_results(self, roundid: int, heat: int) -> bool:
        """
        Clear results for a specific heat (for re-runs).

        Args:
            roundid: The round ID
            heat: The heat number

        Returns:
            True if successful
        """
        try:
            with self._lock:
                self.conn.execute('''
                    UPDATE RaceChart
                    SET finishtime = NULL, finishplace = NULL, completed = NULL
                    WHERE roundid = ? AND heat = ?
                ''', (roundid, heat))
                self.conn.commit()
                logger.info(f"Heat results cleared: round={roundid}, heat={heat}")
                return True
        except Exception as e:
            logger.error(f"Failed to clear heat results: {e}")
            return False

    # =========================================================================
    # Heat Advancement
    # =========================================================================

    def advance_heat(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Advance to the next heat in the current round.

        Returns:
            Tuple of (roundid, heat) for the new current heat,
            or (None, None) if no more heats in round
        """
        current = self.get_running_round()
        roundid = current['roundid']
        heat = current['heat']

        if roundid < 0:
            return None, None

        # Check if there's a next heat
        with self._lock:
            cursor = self.conn.execute('''
                SELECT MAX(heat) as max_heat
                FROM RaceChart
                WHERE roundid = ?
            ''', (roundid,))
            row = cursor.fetchone()
            max_heat = row['max_heat'] if row else 0

        if heat < max_heat:
            # Advance to next heat
            new_heat = heat + 1
            self.write_raceinfo('Heat', str(new_heat))
            logger.info(f"Advanced to heat {new_heat} in round {roundid}")
            return roundid, new_heat
        else:
            # No more heats - turn off racing
            self.write_raceinfo('NowRacingState', '0')
            logger.info(f"Round {roundid} complete - no more heats")
            return None, None

    # =========================================================================
    # Event Logging
    # =========================================================================

    def record_action(self, action: str, details: Dict[str, Any] = None) -> None:
        """
        Record an action to the ActionHistory table.

        Args:
            action: Action name/type
            details: Additional details as dictionary
        """
        import json

        payload = {'action': action}
        if details:
            payload.update(details)

        try:
            with self._lock:
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.conn.execute('''
                    INSERT INTO ActionHistory (received, request)
                    VALUES (?, ?)
                ''', (now, json.dumps(payload)))
                self.conn.commit()
        except Exception as e:
            logger.warning(f"Failed to record action: {e}")


# Singleton instance for easy access
_db_instance: Optional[DerbyDatabase] = None


def get_database(db_path: Optional[str] = None) -> DerbyDatabase:
    """
    Get or create a singleton database instance.

    Args:
        db_path: Path to database (required on first call)

    Returns:
        DerbyDatabase instance
    """
    global _db_instance

    if _db_instance is None:
        if db_path is None:
            # Try to find database from environment
            db_path = os.getenv('DERBYNET_DB_PATH')
            if db_path is None:
                raise ValueError("Database path required - set DERBYNET_DB_PATH or pass db_path")
        _db_instance = DerbyDatabase(db_path)

    return _db_instance

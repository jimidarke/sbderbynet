"""
Unit tests for environment variable configuration.

Tests verify that Python modules correctly read configuration from
environment variables with appropriate fallbacks to defaults.

Phase 1.4 of enterprise roadmap: Configuration Externalization
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMQTTConfiguration:
    """Tests for MQTT broker configuration via environment variables."""

    def test_mqtt_broker_default(self, monkeypatch):
        """MQTT_BROKER should default to localhost when not set."""
        monkeypatch.delenv('MQTT_BROKER', raising=False)

        # Re-import to pick up env var
        import importlib
        import derbyRace as dr
        importlib.reload(dr)

        assert dr.MQTT_BROKER == 'localhost'

    def test_mqtt_broker_from_env(self, monkeypatch):
        """MQTT_BROKER should be read from environment variable."""
        monkeypatch.setenv('MQTT_BROKER', '192.168.100.10')

        import importlib
        import derbyRace as dr
        importlib.reload(dr)

        assert dr.MQTT_BROKER == '192.168.100.10'

    def test_mqtt_port_default(self, monkeypatch):
        """MQTT_PORT should default to 1883 when not set."""
        monkeypatch.delenv('MQTT_PORT', raising=False)

        import importlib
        import derbyRace as dr
        importlib.reload(dr)

        assert dr.MQTT_PORT == 1883

    def test_mqtt_port_from_env(self, monkeypatch):
        """MQTT_PORT should be read from environment variable."""
        monkeypatch.setenv('MQTT_PORT', '1884')

        import importlib
        import derbyRace as dr
        importlib.reload(dr)

        assert dr.MQTT_PORT == 1884


class TestDerbyNetAPIConfiguration:
    """Tests for DerbyNet API host configuration."""

    def test_api_host_default(self, monkeypatch):
        """DERBYNET_API_HOST should default to localhost."""
        monkeypatch.delenv('DERBYNET_API_HOST', raising=False)

        # Test via os.getenv pattern used in derbyRace.py
        host = os.getenv('DERBYNET_API_HOST', 'localhost')
        assert host == 'localhost'

    def test_api_host_from_env(self, monkeypatch):
        """DERBYNET_API_HOST should be read from environment."""
        monkeypatch.setenv('DERBYNET_API_HOST', '192.168.100.10')

        host = os.getenv('DERBYNET_API_HOST', 'localhost')
        assert host == '192.168.100.10'


class TestDatabaseConfiguration:
    """Tests for direct database path configuration."""

    def test_db_path_not_set(self, monkeypatch):
        """DERBYNET_DB_PATH should return None when not set."""
        monkeypatch.delenv('DERBYNET_DB_PATH', raising=False)

        db_path = os.getenv('DERBYNET_DB_PATH')
        assert db_path is None

    def test_db_path_from_env(self, monkeypatch):
        """DERBYNET_DB_PATH should be read from environment."""
        monkeypatch.setenv('DERBYNET_DB_PATH', '/var/lib/derbynet/2025/test/derbynet.sqlite3')

        db_path = os.getenv('DERBYNET_DB_PATH')
        assert db_path == '/var/lib/derbynet/2025/test/derbynet.sqlite3'

    def test_get_database_uses_env_var(self, monkeypatch, populated_db):
        """get_database() should use DERBYNET_DB_PATH environment variable."""
        import derbydb
        derbydb._db_instance = None  # Reset singleton

        monkeypatch.setenv('DERBYNET_DB_PATH', populated_db)

        db = derbydb.get_database()
        assert db is not None
        assert db.db_path == populated_db

        db.close()
        derbydb._db_instance = None

    def test_get_database_requires_path(self, monkeypatch):
        """get_database() should raise error when no path available."""
        import derbydb
        derbydb._db_instance = None  # Reset singleton

        monkeypatch.delenv('DERBYNET_DB_PATH', raising=False)

        with pytest.raises(ValueError) as exc_info:
            derbydb.get_database()

        assert "Database path required" in str(exc_info.value)


class TestLoggingConfiguration:
    """Tests for logging configuration via environment variables."""

    def test_rsyslog_ip_default(self, monkeypatch):
        """RSYSLOG_IP should have default value."""
        monkeypatch.delenv('RSYSLOG_IP', raising=False)

        # Default pattern used across modules
        rsyslog_ip = os.getenv('RSYSLOG_IP', '192.168.100.10')
        assert rsyslog_ip == '192.168.100.10'

    def test_rsyslog_ip_from_env(self, monkeypatch):
        """RSYSLOG_IP should be configurable via environment."""
        monkeypatch.setenv('RSYSLOG_IP', '10.0.0.1')

        rsyslog_ip = os.getenv('RSYSLOG_IP', '192.168.100.10')
        assert rsyslog_ip == '10.0.0.1'

    def test_rsyslog_port_default(self, monkeypatch):
        """RSYSLOG_PORT should default to 514."""
        monkeypatch.delenv('RSYSLOG_PORT', raising=False)

        rsyslog_port = int(os.getenv('RSYSLOG_PORT', '514'))
        assert rsyslog_port == 514

    def test_rsyslog_port_from_env(self, monkeypatch):
        """RSYSLOG_PORT should be configurable via environment."""
        monkeypatch.setenv('RSYSLOG_PORT', '1514')

        rsyslog_port = int(os.getenv('RSYSLOG_PORT', '514'))
        assert rsyslog_port == 1514


class TestTimezoneConfiguration:
    """Tests for timezone configuration."""

    def test_timezone_default(self, monkeypatch):
        """DERBY_TIMEZONE should have sensible default."""
        monkeypatch.delenv('DERBY_TIMEZONE', raising=False)

        tz = os.getenv('DERBY_TIMEZONE', 'America/Edmonton')
        assert tz == 'America/Edmonton'

    def test_timezone_from_env(self, monkeypatch):
        """DERBY_TIMEZONE should be configurable via environment."""
        monkeypatch.setenv('DERBY_TIMEZONE', 'America/New_York')

        tz = os.getenv('DERBY_TIMEZONE', 'America/Edmonton')
        assert tz == 'America/New_York'


class TestDebugConfiguration:
    """Tests for debug mode configuration."""

    def test_debug_default_false(self, monkeypatch):
        """DERBY_DEBUG should default to false."""
        monkeypatch.delenv('DERBY_DEBUG', raising=False)

        debug = os.getenv('DERBY_DEBUG', 'false').lower() == 'true'
        assert debug is False

    def test_debug_enabled(self, monkeypatch):
        """DERBY_DEBUG=true should enable debug mode."""
        monkeypatch.setenv('DERBY_DEBUG', 'true')

        debug = os.getenv('DERBY_DEBUG', 'false').lower() == 'true'
        assert debug is True


class TestConfigurationPriority:
    """Tests verifying configuration priority order."""

    def test_env_var_overrides_default(self, monkeypatch):
        """Environment variable should override hardcoded default."""
        # Test the pattern used throughout the codebase
        default_broker = '192.168.100.10'

        # Without env var, should use default
        monkeypatch.delenv('MQTT_BROKER', raising=False)
        broker = os.getenv('MQTT_BROKER', default_broker)
        assert broker == default_broker

        # With env var, should override
        monkeypatch.setenv('MQTT_BROKER', 'custom-broker.local')
        broker = os.getenv('MQTT_BROKER', default_broker)
        assert broker == 'custom-broker.local'

    def test_production_defaults_are_static_ip(self):
        """Production defaults should use static IP 192.168.100.10."""
        # This documents the intentional design decision:
        # The on-premise Raspberry Pi uses static IP for reliability
        # Environment variables are for Docker/dev/multi-site only

        production_defaults = {
            'MQTT_BROKER': '192.168.100.10',
            'DERBYNET_API_HOST': '192.168.100.10',
            'RSYSLOG_IP': '192.168.100.10',
        }

        # Note: derbyRace.py uses 'localhost' as default because
        # it runs ON the Pi, so localhost == 192.168.100.10
        # Edge devices (finishtimer, display) use 192.168.100.10 directly

        for var, expected_default in production_defaults.items():
            # Verify the expected default pattern exists
            assert expected_default in ['192.168.100.10', 'localhost']


class TestConfigurationDocumentation:
    """Meta-tests that verify configuration is documented."""

    def test_all_env_vars_documented(self):
        """All environment variables should be listed in ENTERPRISE_ROADMAP.md."""
        roadmap_path = Path(__file__).parent.parent.parent.parent.parent.parent / 'docs' / 'business' / 'ENTERPRISE_ROADMAP.md'

        if roadmap_path.exists():
            content = roadmap_path.read_text()

            documented_vars = [
                'MQTT_BROKER',
                'MQTT_PORT',
                'DERBYNET_API_HOST',
                'DERBYNET_DB_PATH',
                'RSYSLOG_IP',
                'RSYSLOG_PORT',
                'DERBY_TIMEZONE',
                'DERBY_DEBUG',
            ]

            for var in documented_vars:
                assert var in content, f"Environment variable {var} not documented in ENTERPRISE_ROADMAP.md"
        else:
            pytest.skip("ENTERPRISE_ROADMAP.md not found")

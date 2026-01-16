"""
DerbyNet Server Test Suite

Unit and integration tests for the soapbox derby race server components.

Test Categories:
- test_derbydb.py: Direct SQLite database access module
- test_derbyRace_threading.py: Thread safety for race state management
- test_config.py: Environment variable configuration

Run tests with:
    cd extras/soapbox/infra/server
    pytest

Run with coverage:
    pytest --cov=. --cov-report=html

Run specific test markers:
    pytest -m threading  # Thread safety tests only
    pytest -m "not slow" # Skip slow tests
"""

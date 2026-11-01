"""
Recruitment & Placement Management System
Pytest Configuration & Fixtures
Sets up isolated test database for repeatable automated testing.
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from sql.init_database import init_sqlite
from app import app as flask_app


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create a temporary SQLite test database and point Config to it."""
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_placement.db")

    # Set config to sqlite test db
    original_engine = Config.DB_ENGINE
    original_path = Config.SQLITE_DB_PATH

    Config.DB_ENGINE = "sqlite"
    Config.SQLITE_DB_PATH = test_db_path

    # Initialize schema and seed data
    init_sqlite(test_db_path)

    yield test_db_path

    # Cleanup
    Config.DB_ENGINE = original_engine
    Config.SQLITE_DB_PATH = original_path
    try:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    except Exception:
        pass


@pytest.fixture
def client():
    """Provides Flask test client."""
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.test_client() as client:
        with flask_app.app_context():
            yield client


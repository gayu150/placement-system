"""
Recruitment & Placement Management System
Application Configuration Module
Loads configuration values from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load .env file if it exists
load_dotenv(BASE_DIR / ".env")


class Config:
    """Application configuration parameters."""
    SECRET_KEY = os.getenv("SECRET_KEY", "student-recruitment-secret-key-2026")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
    PORT = int(os.getenv("PORT", "5000"))

    # Database configuration
    DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").lower()  # 'mysql' or 'sqlite'
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "placement_db")

    # SQLite database file path (used when DB_ENGINE=sqlite or test fallback)
    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", str(BASE_DIR / "placement.db"))

    # Session settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


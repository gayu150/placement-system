"""
Recruitment & Placement Management System
Database Access & Connection Module
Provides connection management, dictionary cursors, transaction context,
and parameterized query execution for MySQL (with SQLite compatibility mode).
"""

import sqlite3
import re
from contextlib import contextmanager
from config import Config

# Try importing mysql.connector
try:
    import mysql.connector
    from mysql.connector import pooling
    HAS_MYSQL_CONNECTOR = True
except ImportError:
    HAS_MYSQL_CONNECTOR = False

# Global MySQL connection pool if MySQL is enabled
_mysql_pool = None


def get_active_engine():
    """Determine the active database engine."""
    engine = Config.DB_ENGINE.lower()
    if engine == "mysql" and not HAS_MYSQL_CONNECTOR:
        print("[DB Warning] mysql-connector-python not available, falling back to sqlite.")
        return "sqlite"
    return engine


def get_raw_connection():
    """Create and return a raw database connection based on configured engine."""
    engine = get_active_engine()
    if engine == "mysql":
        global _mysql_pool
        try:
            if _mysql_pool is None:
                _mysql_pool = pooling.MySQLConnectionPool(
                    pool_name="placement_pool",
                    pool_size=5,
                    host=Config.DB_HOST,
                    port=Config.DB_PORT,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD,
                    database=Config.DB_NAME,
                    autocommit=False
                )
            return _mysql_pool.get_connection()
        except Exception as e:
            # Fallback to direct connection if pool fails or if server error
            try:
                return mysql.connector.connect(
                    host=Config.DB_HOST,
                    port=Config.DB_PORT,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD,
                    database=Config.DB_NAME,
                    autocommit=False
                )
            except Exception as direct_err:
                raise ConnectionError(
                    f"Failed to connect to MySQL database '{Config.DB_NAME}' at {Config.DB_HOST}:{Config.DB_PORT}. "
                    f"Ensure MySQL is running and credentials in .env are correct. Details: {direct_err}"
                ) from direct_err
    else:
        # SQLite connection
        conn = sqlite3.connect(Config.SQLITE_DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn


def _adapt_query(sql, engine):
    """
    Adapts parameterized SQL syntax if running on SQLite.
    MySQL uses '%s', SQLite uses '?'.
    """
    if engine == "sqlite":
        # Replace %s with ? for parameter binding
        return sql.replace("%s", "?")
    return sql


class TransactionContext:
    """
    A transactional cursor wrapper that handles MySQL and SQLite identically.
    Provides dict-like row results and lastrowid.
    """
    def __init__(self, conn, engine):
        self.conn = conn
        self.engine = engine
        if self.engine == "mysql":
            self.cursor = conn.cursor(dictionary=True)
        else:
            self.cursor = conn.cursor()

    def execute(self, sql, params=None):
        adapted = _adapt_query(sql, self.engine)
        if params is None:
            return self.cursor.execute(adapted)
        return self.cursor.execute(adapted, params)

    def executemany(self, sql, seq_of_params):
        adapted = _adapt_query(sql, self.engine)
        return self.cursor.executemany(adapted, seq_of_params)

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        if self.engine == "sqlite":
            return dict(row)
        return row

    def fetchall(self):
        rows = self.cursor.fetchall()
        if self.engine == "sqlite":
            return [dict(r) for r in rows]
        return rows

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def close(self):
        try:
            self.cursor.close()
        except Exception:
            pass


@contextmanager
def db_transaction():
    """
    Context manager for database transactions.
    Automatically commits on success or rolls back on exception.
    Usage:
        with db_transaction() as tx:
            tx.execute("INSERT INTO ...", (val1, val2))
            cand_id = tx.lastrowid
            tx.execute("UPDATE ...", (cand_id,))
    """
    conn = get_raw_connection()
    engine = get_active_engine()
    tx = TransactionContext(conn, engine)
    try:
        yield tx
        conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise exc
    finally:
        tx.close()
        try:
            conn.close()
        except Exception:
            pass


def execute_query(sql, params=None):
    """Execute a parameterized query returning all matching rows as dictionaries."""
    conn = get_raw_connection()
    engine = get_active_engine()
    tx = TransactionContext(conn, engine)
    try:
        tx.execute(sql, params)
        rows = tx.fetchall()
        return rows
    finally:
        tx.close()
        conn.close()


def execute_one(sql, params=None):
    """Execute a parameterized query returning a single row as a dictionary, or None."""
    conn = get_raw_connection()
    engine = get_active_engine()
    tx = TransactionContext(conn, engine)
    try:
        tx.execute(sql, params)
        row = tx.fetchone()
        return row
    finally:
        tx.close()
        conn.close()


def execute_insert(sql, params=None):
    """Execute an INSERT statement, commit, and return lastrowid."""
    conn = get_raw_connection()
    engine = get_active_engine()
    tx = TransactionContext(conn, engine)
    try:
        tx.execute(sql, params)
        conn.commit()
        return tx.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        tx.close()
        conn.close()


def execute_update(sql, params=None):
    """Execute an UPDATE or DELETE statement, commit, and return rowcount."""
    conn = get_raw_connection()
    engine = get_active_engine()
    tx = TransactionContext(conn, engine)
    try:
        tx.execute(sql, params)
        conn.commit()
        return tx.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        tx.close()
        conn.close()


"""Blindfold settings database module for storing global settings."""

import sqlite3
from datetime import datetime


def init_settings(conn: sqlite3.Connection) -> None:
    """
    Initialize the settings table schema.
    
    Args:
        conn: SQLite database connection
    """
    # Create settings table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        )
    """)
    
    # Commit the changes
    conn.commit()


def set_setting(conn, key: str, value: str) -> None:
    """
    Set a setting value.
    
    Args:
        conn: SQLite database connection
        key: Setting key
        value: Setting value
    """
    updated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    conn.execute("""
        INSERT INTO settings (key, value, updated_at_utc)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value=excluded.value,
            updated_at_utc=excluded.updated_at_utc
    """, (key, value, updated_at))
    
    conn.commit()


def get_setting(conn, key: str) -> str | None:
    """
    Get a setting value.
    
    Args:
        conn: SQLite database connection
        key: Setting key
        
    Returns:
        str | None: Setting value or None if not found
    """
    cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else None
"""Blindfold state database module for managing sessions and variables."""

import sqlite3
from datetime import datetime


def init_db(conn: sqlite3.Connection) -> None:
    """
    Initialize the database schema.
    
    Args:
        conn: SQLite database connection
    """
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys=ON")
    
    # Create sessions table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            created_at_utc TEXT NOT NULL
        )
    """)
    
    # Create session_vars table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_vars (
            id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT "string",
            updated_at_utc TEXT NOT NULL,
            UNIQUE(session_id, key),
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    """)
    
    # Commit the changes
    conn.commit()


def ensure_session(conn, name: str) -> int:
    """
    Create session if not exists and return session_id.
    If exists, return existing id.
    
    Args:
        conn: SQLite database connection
        name: Session name
        
    Returns:
        int: Session ID
    """
    # Try to get existing session
    cursor = conn.execute("SELECT id FROM sessions WHERE name = ?", (name,))
    row = cursor.fetchone()
    
    if row:
        return row[0]
    
    # Create new session
    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.execute(
        "INSERT INTO sessions (name, created_at_utc) VALUES (?, ?)",
        (name, created_at)
    )
    conn.commit()
    
    return cursor.lastrowid


def list_sessions(conn) -> list[str]:
    """
    List all session names.
    
    Args:
        conn: SQLite database connection
        
    Returns:
        list[str]: List of session names
    """
    cursor = conn.execute("SELECT name FROM sessions ORDER BY name")
    return [row[0] for row in cursor.fetchall()]


def delete_session(conn, name: str) -> bool:
    """
    Delete a session by name.
    
    Args:
        conn: SQLite database connection
        name: Session name to delete
        
    Returns:
        bool: True if deleted, False if not found
    """
    cursor = conn.execute("DELETE FROM sessions WHERE name = ?", (name,))
    conn.commit()
    
    return cursor.rowcount > 0


def set_var(conn, session_name: str, key: str, value: str, type_: str = "string") -> None:
    """
    Set a variable in a session.
    If the variable already exists, it will be updated.
    
    Args:
        conn: SQLite database connection
        session_name: Session name
        key: Variable key
        value: Variable value
        type_: Variable type (default "string")
    """
    session_id = ensure_session(conn, session_name)
    updated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    # Upsert the variable
    conn.execute("""
        INSERT INTO session_vars (session_id, key, value, type, updated_at_utc)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(session_id, key) DO UPDATE SET
            value=excluded.value,
            type=excluded.type,
            updated_at_utc=excluded.updated_at_utc
    """, (session_id, key, value, type_, updated_at))
    
    conn.commit()


def get_var(conn, session_name: str, key: str) -> tuple[str, str] | None:
    """
    Get a variable from a session.
    
    Args:
        conn: SQLite database connection
        session_name: Session name
        key: Variable key
        
    Returns:
        tuple[str, str] | None: (value, type) or None if not found
    """
    cursor = conn.execute("""
        SELECT sv.value, sv.type
        FROM session_vars sv
        JOIN sessions s ON sv.session_id = s.id
        WHERE s.name = ? AND sv.key = ?
    """, (session_name, key))
    
    row = cursor.fetchone()
    return (row[0], row[1]) if row else None


def list_vars(conn, session_name: str) -> list[tuple[str, str, str]]:
    """
    List all variables in a session.

    Args:
        conn: SQLite database connection
        session_name: Session name

    Returns:
        list[tuple[str, str, str]]: List of (key, value, type) tuples
    """
    cursor = conn.execute("""
        SELECT sv.key, sv.value, sv.type
        FROM session_vars sv
        JOIN sessions s ON sv.session_id = s.id
        WHERE s.name = ?
        ORDER BY sv.key
    """, (session_name,))

    return cursor.fetchall()


def list_vars_as_dict(conn, session_name: str) -> dict[str, str]:
    """
    List all variables in a session as a dictionary.

    Args:
        conn: SQLite database connection
        session_name: Session name

    Returns:
        dict[str, str]: Dictionary of key-value pairs
    """
    cursor = conn.execute("""
        SELECT sv.key, sv.value
        FROM session_vars sv
        JOIN sessions s ON sv.session_id = s.id
        WHERE s.name = ?
        ORDER BY sv.key
    """, (session_name,))

    return dict(cursor.fetchall())
"""Blindfold database module."""

import sqlite3

def get_db_path(state_dir):
    """
    Get the path to the database file.

    Args:
        state_dir (str): Path to the state directory

    Returns:
        str: Path to the database file
    """
    return state_dir + "/blindfold.sqlite3"

def connect(db_path):
    """
    Connect to the database.

    Args:
        db_path (str): Path to the database file

    Returns:
        sqlite3.Connection: Database connection
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn
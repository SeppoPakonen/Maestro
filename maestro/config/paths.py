"""Path resolution utilities for Maestro.

Provides centralized path resolution with environment variable overrides for testing.
"""

import os
from pathlib import Path


def get_docs_root() -> Path:
    """Get the docs root directory, respecting MAESTRO_DOCS_ROOT override.

    Returns:
        Path to docs root directory (defaults to current dir if not set)

    Environment Variables:
        MAESTRO_DOCS_ROOT: Override for docs root (useful for testing)
    """
    docs_root = os.environ.get('MAESTRO_DOCS_ROOT', '.')
    return Path(docs_root)


def get_lock_dir() -> Path:
    """Get the lock directory for repo locks.

    Returns:
        Path to lock directory (docs/maestro/locks by default)
    """
    return get_docs_root() / "docs" / "maestro" / "locks"


def get_ai_logs_dir(engine: str) -> Path:
    """Get the AI logs directory for a specific engine.

    Args:
        engine: Name of the AI engine

    Returns:
        Path to AI logs directory for the engine
    """
    return get_docs_root() / "docs" / "logs" / "ai" / engine


def get_state_dir() -> Path:
    """Get the state directory.

    Returns:
        Path to state directory (docs/state by default)
    """
    return get_docs_root() / "docs" / "state"

"""Interactive gating utilities for CLI commands."""
from __future__ import annotations

import os
import sys


def is_interactive_allowed() -> bool:
    """Return True only when explicitly enabled and running in a TTY."""
    if os.environ.get("MAESTRO_INTERACTIVE", "0") not in ("1", "true", "yes"):
        return False
    if not (hasattr(sys.stdin, "isatty") and hasattr(sys.stdout, "isatty")):
        return False
    return bool(sys.stdin.isatty() and sys.stdout.isatty())

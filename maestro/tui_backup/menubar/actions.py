"""
Utilities for executing menu actions safely.
"""
from __future__ import annotations

import inspect
from typing import Optional

from maestro.tui.menubar.model import MenuItem


async def execute_menu_action(item: MenuItem) -> Optional[Exception]:
    """Run the callable attached to a menu item, handling sync/async uniformly."""
    if not item.action:
        return None
    try:
        result = item.action()
        if inspect.isawaitable(result):
            await result
    except Exception as exc:  # pragma: no cover - safety net
        return exc
    return None


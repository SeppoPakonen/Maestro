"""
Registry for MC shell pane views.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from maestro.tui.panes.base import PaneFactory, PaneView

_REGISTRY: Dict[str, PaneFactory] = {}


def register_pane(section: str, factory: PaneFactory) -> None:
    """Register a pane factory for a section name."""
    _REGISTRY[section] = factory


def get_pane_factory(section: str) -> Optional[PaneFactory]:
    """Return the factory for a given section, if any."""
    return _REGISTRY.get(section)


def create_pane(section: str) -> Optional[PaneView]:
    """Create a pane instance for the section, if registered."""
    factory = get_pane_factory(section)
    if not factory:
        return None
    return factory()


def registered_sections() -> List[str]:
    """List registered section names."""
    return list(_REGISTRY.keys())

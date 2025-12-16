"""Pane views package for MC shell."""

from maestro.tui.panes.base import PaneView
from maestro.tui.panes.registry import register_pane, get_pane_factory, create_pane, registered_sections

__all__ = ["PaneView", "register_pane", "get_pane_factory", "create_pane", "registered_sections"]

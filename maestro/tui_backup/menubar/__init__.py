"""
Menubar package for Midnight Commander–style navigation.
"""
from maestro.tui.menubar.model import MenuBar, Menu, MenuItem, Separator
from maestro.tui.menubar.widget import MenuActionRequested, MenuBarDeactivated, MenuBarWidget

__all__ = [
    "MenuBar",
    "Menu",
    "MenuItem",
    "Separator",
    "MenuBarWidget",
    "MenuActionRequested",
    "MenuBarDeactivated",
]

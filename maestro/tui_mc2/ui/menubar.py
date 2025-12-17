"""
Menubar for MC2 Curses TUI
"""
import curses
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from maestro.tui_mc2.ui.modals import ModalDialog


@dataclass
class MenuItem:
    id: str
    label: str
    callback: Optional[Callable] = None
    enabled: bool = True
    key_hint: Optional[str] = None


class Menu:
    def __init__(self, label: str, items: List[MenuItem]):
        self.label = label
        self.items = items
        self.selected_index: int = 0
        self.active: bool = False


class Menubar:
    def __init__(self, window, context):
        self.window = window
        self.context = context
        self.menus: List[Menu] = self._create_default_menus()
        self.active_menu_index: int = -1  # -1 means no active menu
        self.menu_items = []  # List of (start_col, end_col, menu_index) for click detection

    def set_window(self, window):
        """Update the curses window for the menubar."""
        self.window = window
        
    def _create_default_menus(self) -> List[Menu]:
        """Create default menu structure"""
        return [
            Menu("File", [
                MenuItem("quit", "Quit", key_hint="F10"),
                MenuItem("refresh", "Refresh", key_hint="F5"),
            ]),
            Menu("Edit", [
                MenuItem("new", "New", key_hint="F7"),
                MenuItem("delete", "Delete", key_hint="F8"),
            ]),
            Menu("View", [
                MenuItem("toggle_menu", "Toggle Menu", key_hint="F9"),
            ]),
            Menu("Help", [
                MenuItem("help", "Help", key_hint="F1"),
            ])
        ]
    
    def is_active(self) -> bool:
        return self.active_menu_index >= 0
    
    def activate(self):
        """Activate the menubar (show dropdowns)"""
        self.active_menu_index = 0
        self.context.status_message = "Menubar active - Use left/right to navigate, enter to open"
    
    def deactivate(self):
        """Deactivate the menubar"""
        for menu in self.menus:
            menu.active = False
        self.active_menu_index = -1
        self.context.status_message = "Menubar closed"
    
    def handle_key(self, key: int) -> bool:
        """Handle keyboard input when menubar is active, return True if handled"""
        if not self.is_active():
            return False
            
        active_menu = self.menus[self.active_menu_index] if 0 <= self.active_menu_index < len(self.menus) else None
        
        if key == curses.KEY_LEFT:
            # Move to previous menu
            if self.active_menu_index > 0:
                self.active_menu_index -= 1
            return True
            
        elif key == curses.KEY_RIGHT:
            # Move to next menu
            if self.active_menu_index < len(self.menus) - 1:
                self.active_menu_index += 1
            return True
            
        elif key == ord('\n') or key == 10 or key == 13:  # Enter
            # Open the active menu if there is one, or execute the selected item
            if active_menu:
                # In this implementation, we'll just execute the first item (simplified)
                if active_menu.items:
                    item = active_menu.items[0]
                    if item.enabled and item.callback:
                        item.callback()
                    else:
                        # Handle default actions for known menu items
                        self._handle_builtin_action(item.id)
            return True
            
        elif key == 27:  # ESC
            self.deactivate()
            return True
            
        elif key == curses.KEY_DOWN or key == ord(' '):  # Space or Down arrow
            # Open the active menu
            if active_menu:
                active_menu.active = not active_menu.active
            return True
            
        return False
    
    def _handle_builtin_action(self, action_id: str):
        """Handle built-in menu actions"""
        if action_id == "quit":
            self.context.should_exit = True
        elif action_id == "refresh":
            # Trigger refresh in the main app
            pass  # This will be handled by the main app
        elif action_id == "new":
            pass  # Handled by panes
        elif action_id == "delete":
            pass  # Handled by panes
        elif action_id == "help":
            # Show help modal
            modal = ModalDialog(self.window, "Help", [
                "Menubar Help",
                "",
                "Use arrow keys to navigate",
                "Enter to activate",
                "Escape to close",
                "",
                "Press any key to close..."
            ])
            modal.show()
    
    def render(self):
        """Render the menubar"""
        self.window.erase()
        height, width = self.window.getmaxyx()
        
        # Initialize color pair for menubar
        if curses.has_colors():
            self.window.bkgd(' ', curses.color_pair(1) | curses.A_REVERSE)
        
        # Calculate menu item positions
        self.menu_items = []
        col = 1  # Start from 1 to have padding
        
        for i, menu in enumerate(self.menus):
            # Determine if this menu should be highlighted (active or selected)
            is_highlighted = (i == self.active_menu_index)
            
            menu_label = f" {menu.label} "
            end_col = col + len(menu_label) - 1
            
            # Store position for click detection
            self.menu_items.append((col, end_col, i))
            
            # Add the menu label
            attr = curses.A_REVERSE if is_highlighted else 0
            if is_highlighted and curses.has_colors():
                attr = curses.color_pair(3) | curses.A_BOLD
            try:
                self.window.addstr(0, col, menu_label, attr)
            except:
                # Handle case where string goes beyond window
                pass
            
            col = end_col + 2  # Add padding between menus
        
        # Add key hints at the right side
        try:
            hint = " F1=Help F9=Menu F10=Quit "
            self.window.addstr(0, max(0, width - len(hint) - 1), hint)
        except:
            pass
        
        self.window.noutrefresh()

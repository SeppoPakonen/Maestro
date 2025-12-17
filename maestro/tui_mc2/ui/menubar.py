"""
Menubar for MC2 Curses TUI
"""
import curses
from typing import List, Optional, Callable
from dataclasses import dataclass


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
        self.last_action_id: Optional[str] = None
        self.dropdown_win = None

    def set_window(self, window):
        """Update the curses window for the menubar."""
        self.window = window
        
    def _create_default_menus(self) -> List[Menu]:
        """Create default menu structure"""
        return [
            Menu("Sessions", [
                MenuItem("sessions.refresh", "Refresh", key_hint="F5"),
                MenuItem("sessions.new", "New", key_hint="F7"),
                MenuItem("sessions.delete", "Delete", key_hint="F8"),
                MenuItem("sessions.set_active", "Set Active", key_hint="Enter"),
            ]),
            Menu("Plans", [
                MenuItem("plans.refresh", "Refresh", key_hint="F5"),
                MenuItem("plans.set_active", "Set Active", key_hint="Enter"),
                MenuItem("plans.kill", "Kill Branch", key_hint="F8"),
                MenuItem("plans.toggle_collapse", "Toggle Collapse", key_hint="Left/Right"),
            ]),
            Menu("File", [
                MenuItem("quit", "Quit", key_hint="F10"),
                MenuItem("refresh", "Refresh", key_hint="F5"),
            ]),
            Menu("Edit", [
                MenuItem("new", "New", key_hint="F7"),
                MenuItem("delete", "Delete", key_hint="F8"),
            ]),
            Menu("View", [
                MenuItem("view.sessions", "Sessions", key_hint="F9"),
                MenuItem("view.plans", "Plans", key_hint="F9"),
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
            menu.selected_index = 0
        self.active_menu_index = -1
        self.context.status_message = "Menubar closed"
        self.last_action_id = None

    def handle_key(self, key: int) -> bool:
        """Handle keyboard input when menubar is active, return True if handled"""
        if not self.is_active():
            return False
            
        active_menu = self.menus[self.active_menu_index] if 0 <= self.active_menu_index < len(self.menus) else None
        
        if key == curses.KEY_LEFT:
            if self.active_menu_index > 0:
                was_open = active_menu.active if active_menu else False
                if active_menu:
                    active_menu.active = False
                self.active_menu_index -= 1
                if was_open:
                    new_menu = self.menus[self.active_menu_index]
                    new_menu.active = True
                    new_menu.selected_index = 0
            return True

        if key == curses.KEY_RIGHT:
            if self.active_menu_index < len(self.menus) - 1:
                was_open = active_menu.active if active_menu else False
                if active_menu:
                    active_menu.active = False
                self.active_menu_index += 1
                if was_open:
                    new_menu = self.menus[self.active_menu_index]
                    new_menu.active = True
                    new_menu.selected_index = 0
            return True

        if key in (curses.KEY_DOWN, ord(' ')):
            if active_menu:
                if not active_menu.active:
                    active_menu.active = True
                    active_menu.selected_index = 0
                else:
                    active_menu.selected_index = min(active_menu.selected_index + 1, len(active_menu.items) - 1)
            return True

        if key == curses.KEY_UP:
            if active_menu and active_menu.active:
                active_menu.selected_index = max(active_menu.selected_index - 1, 0)
                return True
            return False

        if key in (ord('\n'), 10, 13):
            if active_menu:
                if not active_menu.active:
                    active_menu.active = True
                    active_menu.selected_index = 0
                else:
                    self._activate_selected_item(active_menu)
                    self.deactivate()
            return True

        if key == 27:  # ESC
            self.deactivate()
            return True

        if key == curses.KEY_F9:
            self.deactivate()
            return True

        return True

    def _activate_selected_item(self, menu: Menu):
        if not menu.items:
            return
        item = menu.items[menu.selected_index]
        if not item.enabled:
            return
        if item.callback:
            item.callback()
            return
        self.last_action_id = item.id

    def consume_last_action(self) -> Optional[str]:
        action = self.last_action_id
        self.last_action_id = None
        return action

    def _format_menu_item(self, item: MenuItem, width: int) -> str:
        hint = f" {item.key_hint}" if item.key_hint else ""
        text = f"{item.label}{hint}"
        if width <= 0:
            return text
        if len(text) > width:
            return text[:max(0, width - 3)] + "..."
        return text.ljust(width)
    
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

        if self.is_active():
            active_menu = self.menus[self.active_menu_index]
            if active_menu.active and active_menu.items:
                start_col = self.menu_items[self.active_menu_index][0] if self.menu_items else 0
                max_item_width = max(len(self._format_menu_item(item, 0)) for item in active_menu.items)
                dropdown_width = min(width - start_col - 1, max(12, max_item_width + 4))
                begin_y, begin_x = self.window.getbegyx()
                dropdown_y = begin_y + 1
                dropdown_x = begin_x + start_col
                screen_height = getattr(curses, "LINES", dropdown_y + len(active_menu.items) + 2)
                max_height = max(3, screen_height - dropdown_y - 1)
                dropdown_height = min(len(active_menu.items) + 2, max_height)
                try:
                    self.dropdown_win = curses.newwin(dropdown_height, dropdown_width, dropdown_y, dropdown_x)
                    if curses.has_colors():
                        self.dropdown_win.bkgd(' ', curses.color_pair(3))
                    self.dropdown_win.border()
                    for idx, item in enumerate(active_menu.items):
                        if idx + 1 >= dropdown_height - 1:
                            break
                        attr = curses.A_REVERSE if idx == active_menu.selected_index else 0
                        if not item.enabled:
                            attr |= curses.A_DIM
                        text = self._format_menu_item(item, dropdown_width - 2)
                        try:
                            self.dropdown_win.addstr(idx + 1, 1, text[: dropdown_width - 2], attr)
                        except Exception:
                            pass
                    self.dropdown_win.noutrefresh()
                except Exception:
                    self.dropdown_win = None
            elif self.dropdown_win:
                try:
                    self.dropdown_win.erase()
                    self.dropdown_win.noutrefresh()
                except Exception:
                    pass
                self.dropdown_win = None
        elif self.dropdown_win:
            try:
                self.dropdown_win.erase()
                self.dropdown_win.noutrefresh()
            except Exception:
                pass
            self.dropdown_win = None

        self.window.noutrefresh()

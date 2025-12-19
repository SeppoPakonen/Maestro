"""
Midnight Commander–style shell skeleton for Maestro TUI.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List, Optional

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Label, ListItem, ListView, Static

from maestro.ui_facade.build import get_active_build_target
from maestro.ui_facade.phases import get_active_phase
from maestro.ui_facade.sessions import get_active_session
from maestro.tui.menubar import Menu, MenuActionRequested, MenuBar, MenuBarDeactivated, MenuBarWidget, MenuItem
from maestro.tui.menubar.actions import execute_menu_action
from maestro.tui.panes.base import PaneFocusRequest, PaneMenuRequest, PaneStatus, PaneView
from maestro.tui.panes.registry import create_pane, create_pane_safe
from maestro.tui.utils import ErrorModal, ErrorNormalizer, write_smoke_success
from maestro.tui.widgets.command_palette import CommandPaletteScreen
from maestro.tui.widgets.status_line import StatusLine
from maestro.tui.widgets.text_viewer import TextViewerModal
import maestro.tui.panes.sessions  # noqa: F401 - ensure pane is registered
import maestro.tui.panes.plans  # noqa: F401 - ensure pane is registered
import maestro.tui.panes.tasks  # noqa: F401 - ensure pane is registered
import maestro.tui.panes.build  # noqa: F401 - ensure pane is registered
import maestro.tui.panes.convert  # noqa: F401 - ensure pane is registered
import maestro.tui.panes.semantic  # noqa: F401 - ensure pane is registered
import maestro.tui.panes.batch  # noqa: F401 - ensure pane is registered


class MainShellScreen(Screen):
    """MC-style two-pane shell with focus + navigation scaffolding."""

    CAPTURE_TAB = True
    status_message: reactive[str] = reactive("Ready")  # Maintained for compatibility with tests
    show_key_hints: reactive[bool] = reactive(True)

    BINDINGS = [
        ("up", "move_up", "Up"),
        ("down", "move_down", "Down"),
        ("left", "move_left", "Left"),
        ("right", "move_right", "Right"),
        ("tab", "cycle_focus", "Switch pane"),
        ("shift+tab", "cycle_focus_reverse", "Focus previous"),
        ("backtab", "cycle_focus_reverse", "Focus previous"),
        ("enter", "open_selection", "Open"),
        ("escape", "soft_back", "Back"),
        ("r", "refresh_view", "Refresh"),
        ("f1", "open_help", "Help"),
        ("f2", "pane_actions", "Actions"),
        ("f3", "view_menu", "View"),
        ("f5", "run_action", "Run"),
        ("f7", "new_action", "New"),
        ("f8", "delete_action", "Delete"),
        ("f9", "toggle_menu", "Menu"),
        ("f10", "quit_app", "Quit"),
    ]

    DEFAULT_CSS = """
    MainShellScreen {
        layout: vertical;
    }

    #main-content {
        height: 1fr;
        layout: horizontal;
    }

    .pane {
        height: 1fr;
        border: solid $primary;
        background: $surface 80%;
        padding: 1;
    }

    .pane.focused {
        border: double $accent;
        background: $surface 60%;
    }

    #section-list {
        height: 1fr;
        border: solid $primary 50%;
        margin-top: 1;
    }

    #section-list ListItem:hover {
        background: $primary 20%;
        text-style: bold;
    }

    #content-host {
        height: 1fr;
        border: solid $primary 50%;
        padding: 1;
    }

    #content-host .content-item:hover {
        background: $primary 10%;
    }

    #content-host .content-item {
        height: 1;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        # Use the pane registry to get available sections, with default fallback
        from maestro.tui.panes.registry import registered_pane_ids
        registry_sections = registered_pane_ids()
        # Map display labels to registry IDs (normalize to Title case for UI)
        self.section_id_map = {name.title(): name for name in registry_sections}
        registry_sections = list(self.section_id_map.keys())
        # Add some default sections that may not be in the registry yet
        self.sections: List[str] = registry_sections + [
            "Home",
            "Plans",
            "Tasks",
            "Build",
            "Convert",
            "Vault",
            "Replay",
            "Confidence",
            "Integrity",
        ]
        # Remove duplicates while preserving order
        seen = set()
        unique_sections = []
        for s in self.sections:
            if s.lower() not in {sec.lower() for sec in unique_sections}:
                unique_sections.append(s)
        self.sections = unique_sections

        self.focus_pane: str = "left"
        self.current_section: str = self.sections[0] if self.sections else "Home"
        self.session_summary: str = "Session: None | Plan: None | Build: None"
        self.menu_bar_model: MenuBar = MenuBar()
        self.menubar: Optional[MenuBarWidget] = None
        self.status_line: Optional[StatusLine] = None
        self._pane_menu: Optional[Menu] = None
        self._menu_focus_restore: Optional[str] = None
        self.current_view: Optional[PaneView] = None
        self._placeholder_counter: int = 0
        self._suppress_select_open: bool = False

    def compose(self) -> ComposeResult:
        """Compose MC shell layout."""
        self.menu_bar_model = MenuBar(
            menus=self._base_menus(self._placeholder_menu(self.current_section)),
            session_summary=self.session_summary,
        )
        self.menubar = MenuBarWidget(self.menu_bar_model)
        yield self.menubar

        with Horizontal(id="main-content"):
            with Vertical(id="left-pane", classes="pane focused"):
                yield Label("Sections", id="left-title")
                section_items = [ListItem(Label(name)) for name in self.sections]
                yield ListView(*section_items, id="section-list")

            with Vertical(id="right-pane", classes="pane"):
                yield Label(self.current_section, id="content-title")
                with Vertical(id="content-host"):
                    placeholder = Static(self._content_placeholder(self.current_section), id="content-placeholder")
                    placeholder.can_focus = True
                    yield placeholder

        self.status_line = StatusLine(
            initial_message="Ready",
            initial_hints="Tab Switch | Enter Open | Esc Back | F9 Menu | F10 Quit",
            initial_focus="FOCUS: LEFT",
            initial_sticky_status=self.session_summary,
            id="status-line"
        )
        yield self.status_line

    def on_mount(self) -> None:
        """Initialize state after mounting."""
        self._load_status_state()
        section_list = self.query_one("#section-list", ListView)
        section_list.index = 0
        self._update_focus("left")
        self._refresh_menu_bar()
        self._open_current_selection()
        self._update_status_hints()

        if getattr(self.app, "smoke_mode", False):
            # Signal readiness early for smoke validation
            print("MC_SHELL_READY", flush=True)

    def _load_status_state(self) -> None:
        """Load session/plan/build summary for the menubar and status line."""
        try:
            session = get_active_session()
        except Exception:
            session = None

        try:
            plan = get_active_phase(session.id) if session else None
        except Exception:
            plan = None

        try:
            build = get_active_build_target(session.id if session else "default_session")
        except Exception:
            build = None

        session_display = session.id[:8] + "..." if session else "None"
        plan_display = plan.plan_id[:8] + "..." if plan else "None"
        build_display = build.id[:8] + "..." if build else "None"

        self.session_summary = f"Session: {session_display} | Plan: {plan_display} | Build: {build_display}"
        if self.menubar:
            self.menubar.set_session_summary(self.session_summary)
        if self.status_line:
            self.status_line.set_sticky_status(self.session_summary)

    def _update_focus(self, target: str) -> None:
        """Switch focus to the requested pane."""
        # Handle blur of current view if switching from right pane
        if self.focus_pane == "right" and target == "left" and self.current_view:
            if hasattr(self.current_view, 'on_blur') and callable(self.current_view.on_blur):
                try:
                    self.current_view.on_blur()
                except Exception as e:
                    self._handle_pane_error(e, "blurring current pane")

        # Update focus state
        self.focus_pane = target
        left_pane = self.query_one("#left-pane", Vertical)
        right_pane = self.query_one("#right-pane", Vertical)
        left_pane.set_class(target == "left", "focused")
        right_pane.set_class(target == "right", "focused")

        if target == "left":
            self.query_one("#section-list", ListView).focus()
        else:
            if self.current_view:
                # Handle focus of current view if switching to right pane
                if hasattr(self.current_view, 'on_focus') and callable(self.current_view.on_focus):
                    try:
                        self.current_view.on_focus()
                    except Exception as e:
                        self._handle_pane_error(e, "focusing current pane")
                self.current_view.focus()
            else:
                try:
                    self.query_one("#content-placeholder", Static).focus()
                except Exception:
                    pass

        if self.status_line:
            self.status_line.set_focus_indicator(f"FOCUS: {target.upper()}")

    def _content_placeholder(self, section_name: str) -> str:
        """Render placeholder content for a section."""
        return (
            f"[b]{section_name}[/b]\n\n"
            "This is a placeholder view. Future tasks will embed the real module here."
        )

    def _safe_facade_call(self, func, context: str = "operation"):
        """Safe wrapper for facade calls that returns stable empty states on failure."""
        try:
            result = func()
            return result, None
        except Exception as exc:
            error_msg = ErrorNormalizer.normalize_exception(exc, context)
            self._update_status(error_msg.message)
            return None, error_msg

    def _open_current_selection(self) -> None:
        """Open the currently selected section into the right pane."""
        content_title = self.query_one("#content-title", Label)
        title_text = self.current_section
        host = self.query_one("#content-host", Vertical)
        self._clear_current_view(host)

        # Use hard failure containment for pane creation
        pane_id = self._pane_id_for_section(self.current_section)
        view, error = create_pane_safe(pane_id)

        if error:
            content_title.update(title_text)
            self._handle_pane_error(error, f"loading {self.current_section}")
            # Show pane error widget instead of crashing
            self._show_pane_error(host, error, self.current_section)
            self.current_view = None
            self._refresh_menu_bar(self._placeholder_menu(self.current_section))
            return

        if view is None:
            content_title.update(title_text)
            self._show_placeholder(host, self.current_section)
            self.current_view = None
            self._refresh_menu_bar(self._placeholder_menu(self.current_section))
            return

        # Set up proper lifecycle
        self.current_view = view
        try:
            title_text = view.title() if hasattr(view, 'title') and callable(view.title) else getattr(view, 'pane_title', self.current_section)
        except Exception:
            title_text = self.current_section
        content_title.update(title_text)

        # Follow deterministic lifecycle: construct -> mount -> focus
        host.mount(view)
        if hasattr(view, 'on_mount') and callable(view.on_mount):
            try:
                view.on_mount()
            except Exception as mount_error:
                self._handle_pane_error(mount_error, f"mounting {self.current_section}")
                # Replace with error widget
                self._clear_current_view(host)
                self._show_pane_error(host, mount_error, self.current_section)
                self.current_view = None
                self._refresh_menu_bar(self._placeholder_menu(self.current_section))
                return

        if hasattr(view, 'on_focus') and callable(view.on_focus):
            try:
                view.on_focus()
            except Exception as focus_error:
                self._handle_pane_error(focus_error, f"focusing {self.current_section}")

        self._refresh_menu_bar()

    def _selected_section_name(self) -> Optional[str]:
        """Get the current highlighted section name."""
        section_list = self.query_one("#section-list", ListView)
        index = section_list.index if section_list.index is not None else 0
        if index < 0 or index >= len(self.sections):
            return None
        return self.sections[index]

    def _pane_id_for_section(self, section: str) -> str:
        """Map a display section name to a registered pane ID."""
        return self.section_id_map.get(section, section).lower()

    def _clear_current_view(self, host: Vertical) -> None:
        """Remove the current view and clean up."""
        if self.current_view:
            try:
                self.current_view.remove()
            except Exception:
                pass
        try:
            host.remove_children(*list(host.children))
        except Exception:
            for child in list(host.children):
                try:
                    child.remove()
                except Exception:
                    continue
        self.current_view = None

    def _show_placeholder(self, host: Vertical, section: str) -> None:
        """Render placeholder content into the host."""
        self._placeholder_counter += 1
        placeholder_id = f"content-placeholder-{self._placeholder_counter}"
        placeholder = Static(self._content_placeholder(section), id=placeholder_id)
        placeholder.can_focus = True
        host.mount(placeholder)

    def _refresh_current_view_data(self) -> None:
        """Invoke refresh on the current pane if it supports the new contract."""
        if not self.current_view:
            # Show a placeholder if there's no current view
            self._update_status("No active pane to refresh")
            return

        # Check if the current view implements the new contract
        if hasattr(self.current_view, 'refresh') and callable(self.current_view.refresh):
            # Use the new contract refresh method
            try:
                self.current_view.refresh()
                self._update_status(f"Refreshed {self.current_section}")
            except Exception as e:
                self._handle_pane_error(e, f"refreshing {self.current_section}")
        else:
            # Fallback to the old refresh_data method for backward compatibility
            def do_refresh():
                return self.current_view.refresh_data()

            result, error = self._safe_facade_call(do_refresh, f"refreshing {self.current_section}")

            if error:
                self._handle_normalized_error(error, f"refreshing {self.current_section}")
                # Even if refresh fails, we still want to maintain the shell state
                return

            if asyncio.iscoroutine(result):
                asyncio.create_task(self._run_view_refresh(result))
            # If it's not a coroutine, the refresh completed synchronously

    async def _run_view_refresh(self, coro) -> None:
        try:
            await coro
        except Exception as exc:
            # Use safe error handling to prevent crashes
            error_msg = ErrorNormalizer.normalize_exception(exc, f"refreshing {self.current_section}")
            self._handle_normalized_error(error_msg, f"refreshing {self.current_section}")

    def _update_status(self, message: str) -> None:
        """Update status message in status line."""
        # Update the reactive attribute for compatibility with tests
        self.status_message = message
        # Also update the status line widget
        if self.status_line:
            self.status_line.set_message(message, ttl=3.0)  # Auto-clear after 3 seconds

    def _get_focusables(self) -> list:
        """Return list of focusable elements in the proper order for the focus ring."""
        focusables = []

        # Add left pane (section list)
        focusables.append(self.query_one("#section-list", ListView))

        # Add right pane (current view content) or placeholder
        if self.current_view:
            # Check if the current view can be focused
            if self.current_view.can_focus:
                focusables.append(self.current_view)
        else:
            # If no current view, add the content host as fallback (which has placeholder inside)
            content_host = self.query_one("#content-host", Vertical)
            if content_host and content_host.can_focus:
                focusables.append(content_host)

        # Add menubar if it's open/active
        if self.menubar and self.menubar.is_active:
            focusables.append(self.menubar)

        return focusables

    def _focus_next(self) -> None:
        """Move focus to the next element in the focus ring."""
        focusables = self._get_focusables()
        if not focusables:
            return

        # Find current focused widget
        current_focus = self.focused
        try:
            current_idx = next(i for i, widget in enumerate(focusables) if widget == current_focus)
            next_idx = (current_idx + 1) % len(focusables)
        except (StopIteration, ValueError):
            # If current focus isn't in our list, focus first element
            next_idx = 0

        target = focusables[next_idx]

        # Handle special cases for switching panes
        if target == self.query_one("#section-list", ListView):
            self._update_focus("left")
        elif target == self.current_view or (not self.current_view and self.query_one("#content-host", Vertical) == target):
            self._update_focus("right")
        elif target == self.menubar:
            # If menubar is already active, don't change pane focus
            target.focus()

        target.focus()

    def _focus_prev(self) -> None:
        """Move focus to the previous element in the focus ring."""
        focusables = self._get_focusables()
        if not focusables:
            return

        # Find current focused widget
        current_focus = self.focused
        try:
            current_idx = next(i for i, widget in enumerate(focusables) if widget == current_focus)
            prev_idx = (current_idx - 1) % len(focusables)
        except (StopIteration, ValueError):
            # If current focus isn't in our list, focus first element backwards
            prev_idx = -1  # Last element

        target = focusables[prev_idx]

        # Handle special cases for switching panes
        if target == self.query_one("#section-list", ListView):
            self._update_focus("left")
        elif target == self.current_view or (not self.current_view and self.query_one("#content-host", Vertical) == target):
            self._update_focus("right")
        elif target == self.menubar:
            # If menubar is already active, don't change pane focus
            target.focus()

        target.focus()

    def action_focus_right(self) -> None:
        """Focus right pane."""
        self._suppress_select_open = True
        self._update_focus("right")
        self._update_status("Focused right pane")
        self.call_after_refresh(lambda: setattr(self, "_suppress_select_open", False))

    def action_focus_left(self) -> None:
        """Focus left pane."""
        self._suppress_select_open = True
        self._update_focus("left")
        self._update_status("Focused left pane")
        self.call_after_refresh(lambda: setattr(self, "_suppress_select_open", False))

    def action_move_up(self) -> None:
        """Move selection up in focused list."""
        if self.focus_pane == "left":
            section_list = self.query_one("#section-list", ListView)
            section_list.action_cursor_up()
            self._update_status("Moved up in sections")
        elif self.current_view:
            # Let the current view handle the up arrow
            self.current_view.action_cursor_up() if hasattr(self.current_view, 'action_cursor_up') else None
            self._update_status("Moved up in current pane")
        else:
            # If no current view, try to handle the up arrow on the placeholder/host
            pass

    def action_move_down(self) -> None:
        """Move selection down in focused list."""
        if self.focus_pane == "left":
            section_list = self.query_one("#section-list", ListView)
            section_list.action_cursor_down()
            self._update_status("Moved down in sections")
        elif self.current_view:
            # Let the current view handle the down arrow
            self.current_view.action_cursor_down() if hasattr(self.current_view, 'action_cursor_down') else None
            self._update_status("Moved down in current pane")
        else:
            # If no current view, try to handle the down arrow on the placeholder/host
            pass

    def action_move_right(self) -> None:
        """Move focus from left pane to right pane."""
        if self.focus_pane == "left":
            self._update_focus("right")
            self._update_status("Moved focus to right pane")
        else:
            # On right pane, let the current view handle the right arrow
            if self.current_view and hasattr(self.current_view, 'action_cursor_right'):
                self.current_view.action_cursor_right()
                self._update_status("Right arrow in current pane")

    def action_move_left(self) -> None:
        """Move focus from right pane to left pane."""
        if self.focus_pane == "right":
            self._update_focus("left")
            self._update_status("Moved focus to left pane")
        else:
            # On left pane, left arrow does nothing (per requirements)
            self._update_status("Left arrow does nothing in left pane")

    def action_open_selection(self) -> None:
        """Enter to open selection or show safe no-op on right pane."""
        if self.focus_pane == "left":
            selected = self._selected_section_name()
            if not selected:
                return
            self.current_section = selected
            self._open_current_selection()
            self._update_focus("right")
            self._update_status(f"Opened {selected}")
        else:
            if not self.current_view:
                self._update_status("No action yet in right pane")
            # Let the pane handle Enter on its own

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Mirror ListView selection into the content pane."""
        if event.list_view.id != "section-list":
            return
        selected = self._selected_section_name()
        if not selected:
            return
        if self._suppress_select_open:
            self._suppress_select_open = False
            return
        self.current_section = selected
        self._open_current_selection()
        self._update_focus("right")
        self._update_status(f"Opened {selected}")

    def action_soft_back(self) -> None:
        """Esc to cancel/back hint."""
        if self.menubar and self.menubar.is_active:
            self.menubar.deactivate()
            self._restore_focus_after_menu()
            return
        self._update_status("Back (no modal to close)")

    def action_quit_app(self) -> None:
        """F10 quits the application."""
        self.app.exit()

    def action_cycle_focus(self) -> None:
        """Tab cycles through the focus ring."""
        self._focus_next()
        self._update_status("Cycled focus forward")

    def action_cycle_focus_reverse(self) -> None:
        """Shift+Tab cycles through the focus ring in reverse."""
        self._focus_prev()
        self._update_status("Cycled focus backward")

    def action_toggle_menu(self) -> None:
        """Toggle the menubar (F9 style)."""
        if not self.menubar:
            return
        if self.menubar.is_active:
            self.menubar.deactivate()
            self._restore_focus_after_menu()
            return
        self._menu_focus_restore = self.focus_pane
        self.menubar.activate()
        self._update_status("Menubar active - Left/Right switch, Enter/Down opens")
        self._update_status_line_for_menubar(True)

    def _update_status_line_for_menubar(self, active: bool) -> None:
        """Update status line to show menubar active state."""
        if self.status_line:
            if active:
                self.status_line.set_hints("F9 Menu | ← → select | ↓ open | Enter run | Esc close")
            else:
                self.status_line.set_hints("Tab Switch | Enter Open | Esc Back | F9 Menu | F10 Quit")

    def _restore_focus_after_menu(self, status: Optional[str] = "Menubar closed") -> None:
        """Restore focus to the prior pane after closing the menubar."""
        if self._menu_focus_restore:
            self._update_focus(self._menu_focus_restore)
        self._menu_focus_restore = None
        if status:
            self._update_status(status)
        self._update_status_line_for_menubar(False)

    def action_refresh_view(self) -> None:
        """Refresh the current view or reload placeholder."""
        if self.current_view:
            self._refresh_current_view_data()
            self._update_status(f"Refreshed {self.current_section}")
        else:
            self._open_current_selection()
            self._update_status(f"Loaded {self.current_section}")

    def action_open_help(self) -> None:
        """Open the help surface."""
        try:
            from maestro.tui.screens.help import HelpScreen
        except Exception:
            HelpScreen = None  # type: ignore

        if HelpScreen:
            self.app.push_screen(HelpScreen())
        else:
            self._update_status("Help screen not available yet")

    def on_menu_action_requested(self, message: MenuActionRequested) -> None:
        """Handle activation events coming from the menubar widget."""
        menu_label = message.menu.label
        item = message.item
        if not message.enabled:
            self._update_status(f"{item.label} is disabled")
            return

        if menu_label == "Sections":
            self._select_section_from_menu(item)
        elif menu_label == "Navigation":
            self._select_navigation_from_menu(item)
        elif menu_label == "Help":
            self._handle_help_menu(item)
        elif menu_label == "Maestro":
            if item.id == "status":
                self._update_status(self.session_summary)
            elif item.id == "contract":
                self._open_contract()
            else:
                self._update_status(f"{item.label} selected")
        elif menu_label == "View":
            self._handle_view_menu(item)
        elif self._pane_menu and menu_label == self._pane_menu.label:
            asyncio.create_task(self._execute_pane_menu_item(item))

    def on_menu_bar_deactivated(self, message: MenuBarDeactivated) -> None:
        """Return focus when the menubar closes."""
        self._restore_focus_after_menu(status=None)

    def _base_menus(self, pane_menu: Menu) -> List[Menu]:
        """Construct the ordered menus with the pane-owned entry."""
        return [
            self._maestro_menu(),
            self._navigation_menu(),
            pane_menu,
            self._view_menu(),
            self._sections_menu(),  # New: Sections menu added to menubar
            self._help_menu(),
        ]

    def _view_menu(self) -> Menu:
        """View menu for pane switching."""
        return Menu(
            label="View",
            items=[
                MenuItem(id=section, label=section, action_id=f"view.{section.lower()}", trust_label="[RO]") for section in self.sections
            ],
        )

    def _navigation_menu(self) -> Menu:
        """Menu entries mirroring the navigation list."""
        return Menu(
            label="Navigation",
            items=[
                MenuItem(id=section, label=section, action_id=f"nav.{section.lower()}", key_hint=None, trust_label="[RO]") for section in self.sections
            ],
        )

    def _help_menu(self) -> Menu:
        """Help menu actions."""
        return Menu(
            label="Help",
            items=[
                MenuItem(id="help", label="F1 Help", key_hint="F1", trust_label="[RO]"),
                MenuItem(id="contract", label="Keys & Contract", trust_label="[RO]"),
            ],
        )

    def _sections_menu(self) -> Menu:
        """Sections menu for switching between panes from the menubar."""
        return Menu(
            label="Sections",
            items=[
                MenuItem(id=section, label=section, action_id=f"sections.{section.lower()}", trust_label="[RO]") for section in self.sections
            ],
        )

    def _maestro_menu(self) -> Menu:
        """Base Maestro menu with safe items."""
        return Menu(
            label="Maestro",
            items=[
                MenuItem(id="status", label="Status Summary", trust_label="[RO]"),
                MenuItem(id="contract", label="MC Contract", trust_label="[RO]"),
            ],
        )

    def _placeholder_menu(self, section: str) -> Menu:
        """Fallback menu when a pane does not expose its own."""
        return Menu(
            label=section,
            items=[
                MenuItem(
                    id="noop",
                    label="No actions available",
                    enabled=False,
                    trust_label="[RO]",
                )
            ],
        )

    def _pane_menu_for_current(self) -> Menu:
        """Return the active pane's menu, falling back to a placeholder."""
        if self.current_view:
            # Check for the new contract method first
            if hasattr(self.current_view, 'get_menu_spec') and callable(self.current_view.get_menu_spec):
                try:
                    menu_spec = self.current_view.get_menu_spec()
                    # Convert the menu spec to the old Menu format for compatibility
                    from maestro.tui.menubar.model import Menu as NewMenu, MenuItem as NewMenuItem
                    if isinstance(menu_spec, NewMenu):
                        return menu_spec
                    # If it's a different format or needs conversion, create a compatible menu
                    menu_label = getattr(self.current_view, 'pane_title', self.current_section)
                    return NewMenu(label=menu_label, items=getattr(menu_spec, 'items', []))
                except Exception as e:
                    self._handle_pane_error(e, f"getting menu spec for {self.current_section}")
                    # Fall back to old method
                    pass

            # Use safe facade call for old menu creation as fallback
            def get_menu():
                return self.current_view.menu() if self.current_view else None

            menu, error = self._safe_facade_call(get_menu, f"building menu for {self.current_section}")

            if error:
                self._update_status(f"Error getting menu: {error.message}")
                # Still return the menu if we got one despite the error
                if menu:
                    return menu
            elif menu:
                return menu
        return self._placeholder_menu(self.current_section)

    def _refresh_menu_bar(self, pane_menu: Optional[Menu] = None) -> None:
        """Refresh the menubar with the latest pane menu and summary."""
        if not self.menubar:
            return
        self._pane_menu = pane_menu or self._pane_menu_for_current()
        menus = self._base_menus(self._pane_menu)
        self.menu_bar_model = MenuBar(menus=menus, session_summary=self.session_summary)
        self.menubar.set_session_summary(self.session_summary)
        self.menubar.set_menus(menus)

    def _select_section_from_menu(self, item: MenuItem) -> None:
        """Update section selection based on a menu activation."""
        section = getattr(item, "payload", None) or item.id
        if section in self.sections:
            section_list = self.query_one("#section-list", ListView)
            section_list.index = self.sections.index(section)
            self.current_section = section
            self._open_current_selection()
            self._update_focus("right")
            self._update_status(f"Opened {section} from Sections menu")
        else:
            self._update_status(f"Unknown section {section}")

    def _select_navigation_from_menu(self, item: MenuItem) -> None:
        """Update section selection based on a menu activation."""
        section = getattr(item, "payload", None) or item.id
        if section in self.sections:
            section_list = self.query_one("#section-list", ListView)
            section_list.index = self.sections.index(section)
            self.current_section = section
            self._open_current_selection()
            self._update_focus("right")
            self._update_status(f"Opened {section} from Navigation menu")
        else:
            self._update_status(f"Unknown section {section}")

    def _handle_view_menu(self, item: MenuItem) -> None:
        """Handle view menu selections to switch between panes."""
        section = getattr(item, "payload", None) or item.id
        if section in self.sections:
            # Find and select the section in the left list
            section_list = self.query_one("#section-list", ListView)
            section_list.index = self.sections.index(section)
            self.current_section = section
            self._open_current_selection()
            self._update_focus("right")
            self._update_status(f"Switched to {section} via View menu")
        else:
            self._update_status(f"Unknown section {section}")

    def _handle_help_menu(self, item: MenuItem) -> None:
        """Open help or contract viewer."""
        if item.id == "help":
            self.action_open_help()
        elif item.id == "contract":
            self._open_contract()
        else:
            self._update_status(f"{item.label} not wired yet")

    async def _execute_pane_menu_item(self, item: MenuItem) -> None:
        """Execute a pane-owned menu item with error discipline."""
        if not item.enabled:
            self._update_status(f"{item.label} is disabled")
            return

        if not item.action:
            self._update_status(f"{self.current_section}: {item.label} not wired yet")
            return

        error = await execute_menu_action(item)
        if error:
            self._handle_view_error(error, f"executing {item.label}")
            return
        self._update_status(f"{self.current_section}: {item.label}")

    def _open_contract(self) -> None:
        """Open the MC contract file in a viewer modal."""
        contract_path = Path(__file__).resolve().parents[2] / "docs" / "tui" / "MC_CONTRACT.md"
        try:
            text = contract_path.read_text()
        except Exception as exc:
            self._update_status(f"Could not open contract: {exc}")
            return
        self.app.push_screen(TextViewerModal("Keys & Contract", text))

    def _update_status_hints(self) -> None:
        """Show or hide verbose key hints."""
        hints = (
            "Tab Switch | Enter Open | Esc Back | F9 Menu | F10 Quit"
            if self.show_key_hints
            else "Hints hidden"
        )
        if self.status_line:
            self.status_line.set_hints(hints)

    def _handle_pane_error(self, exc: Exception, context: str) -> None:
        """Normalize and display pane errors without crashing."""
        error_msg = ErrorNormalizer.normalize_exception(exc, context)
        self._update_status(error_msg.message)

    def _handle_view_error(self, exc: Exception, context: str) -> None:
        """Normalize and display view errors without crashing."""
        error_msg = ErrorNormalizer.normalize_exception(exc, context)
        self._update_status(error_msg.message)
        self.app.push_screen(ErrorModal(error_msg))

    def _handle_normalized_error(self, error_msg: ErrorMessage, context: str) -> None:
        """Handle pre-normalized error messages."""
        self._update_status(error_msg.message)
        self.app.push_screen(ErrorModal(error_msg))

    def _show_pane_error(self, host: Vertical, error: Exception, section_name: str) -> None:
        """Show a pane error widget in place of the pane content."""
        # Import the error widget
        from maestro.tui.widgets.pane_error_widget import PaneErrorWidget, PaneRetryRequest
        from textual.containers import Vertical

        # Clear the host first
        self._clear_current_view(host)

        # Create the error widget
        error_widget = PaneErrorWidget(
            error_message=f"Error loading {section_name} pane: {str(error)}",
            error_exception=error,
            pane_id=section_name
        )

        # Mount the error widget
        host.mount(error_widget)

        # Set up event handler for retries
        self.bind(PaneRetryRequest, self._on_pane_retry, selector="*")

    def _on_pane_retry(self, event: PaneRetryRequest) -> None:
        """Handle pane retry requests."""
        self.current_section = event.pane_id
        self._open_current_selection()
        self._update_focus("right")
        self._update_status(f"Retried loading {event.pane_id}")

    def _handle_key_hint(self, key: str) -> bool:
        """Allow direct function key activation for the active pane menu."""
        if not self._pane_menu:
            return False
        normalized = self._normalize_key_hint(key)
        if normalized == "enter":
            return False
        for entry in self._pane_menu.items:
            if not isinstance(entry, MenuItem):
                continue
            # check legacy key_hint or explicit fkey
            if (
                (entry.key_hint and self._normalize_key_hint(entry.key_hint) == normalized)
                or (entry.fkey and self._normalize_key_hint(entry.fkey) == normalized)
            ) and entry.enabled:
                asyncio.create_task(self._execute_pane_menu_item(entry))
                return True
        return False

    def _normalize_key_hint(self, key: str) -> str:
        """Normalize textual keys and labels for comparison."""
        return key.lower().replace("+", "").strip()

    def _dispatch_fkey(self, key: str) -> None:
        """Dispatch an F-key to the active pane's menu if supported.

        Searches for entries with matching key_hint or fkey and executes the first enabled one.
        If none found, shows a non-modal status message.
        """
        if not self._pane_menu or not self.current_view:
            self._update_status("Not available in this pane")
            return
        normalized = self._normalize_key_hint(key)
        for entry in self._pane_menu.items:
            if not isinstance(entry, MenuItem):
                continue
            if not entry.enabled:
                continue
            if (entry.key_hint and self._normalize_key_hint(entry.key_hint) == normalized) or (
                entry.fkey and self._normalize_key_hint(entry.fkey) == normalized
            ):
                asyncio.create_task(self._execute_pane_menu_item(entry))
                return
        # No matching menu item found
        self._update_status("Not available in this pane")

    def action_run_action(self) -> None:
        """F5 action - run the default action for the current pane."""
        self._dispatch_fkey("f5")

    def action_new_action(self) -> None:
        """F7 action - create new item in the current pane."""
        self._dispatch_fkey("f7")

    def action_delete_action(self) -> None:
        """F8 action - delete selected item in the current pane."""
        self._dispatch_fkey("f8")

    async def _dispatch_fkey_by_action_id(self, action_id: str) -> None:
        """Dispatch an action by its action_id to the active pane."""
        if not self.current_view or not hasattr(self.current_view, 'get_action'):
            self._update_status(f"Action {action_id} not available in current pane")
            return

        try:
            action = await self.current_view.get_action(action_id)
            if action:
                # Execute the action - the action could be a callable or a coroutine
                if asyncio.iscoroutinefunction(action):
                    await action()
                else:
                    action()
            else:
                self._update_status(f"Action {action_id} not found in current pane")
        except Exception as exc:
            self._handle_view_error(exc, f"executing action {action_id}")

    def on_key(self, event: events.Key) -> None:
        """Ensure global keys always reach the shell."""
        key = event.key

        # If menubar is active, only process F9 (which toggles it) - other keys go to menubar
        if self.menubar and self.menubar.is_active:
            if key == "f9":
                # F9 is allowed to toggle the active menubar back off
                self.action_toggle_menu()
                event.stop()
            # For other keys when menubar is active, don't process them here
            # The menubar widget has its own on_key method to handle them
            return

        # F9 handled specially to toggle menubar (when not active)
        if key == "f9":
            self.action_toggle_menu()
            event.stop()
            return

        # F1 -> help
        if key == "f1":
            self.action_open_help()
            event.stop()
            return

        # F10 -> quit
        if key == "f10":
            self.action_quit_app()
            event.stop()
            return

        # F2 -> open the active pane's menu directly
        if key == "f2":
            if self.menubar:
                self._menu_focus_restore = self.focus_pane
                # try to focus the pane menu if present
                try:
                    menus = self.menubar.menu_bar.menus
                    for idx, m in enumerate(menus):
                        if self._pane_menu and m.label == self._pane_menu.label:
                            self.menubar.activate()
                            # set active menu index then open
                            self.menubar.active_menu_index = idx
                            self.menubar.open_current_menu()
                            self._update_status("Pane actions opened")
                            self._update_status_line_for_menubar(True)
                            event.stop()
                            return
                except Exception:
                    pass
            self._update_status("No pane actions available")
            event.stop()
            return

        # F3 -> View menu
        if key == "f3":
            if self.menubar:
                self._menu_focus_restore = self.focus_pane
                # Try to find the View menu
                try:
                    menus = self.menubar.menu_bar.menus
                    for idx, m in enumerate(menus):
                        if m.label.lower() == "view":
                            self.menubar.activate()
                            # set active menu index then open
                            self.menubar.active_menu_index = idx
                            self.menubar.open_current_menu()
                            self._update_status("View menu opened")
                            self._update_status_line_for_menubar(True)
                            event.stop()
                            return
                    # If no View menu doesn't exist, try to find a view-related action in pane menu
                    self._dispatch_fkey(key)
                except Exception:
                    self._dispatch_fkey(key)
            else:
                self._dispatch_fkey(key)
            event.stop()
            return

        # Function keys may route to pane menu entries if no specific action is bound
        # The bound actions (f5 -> run_action, f7 -> new_action, f8 -> delete_action)
        # should be allowed to execute normally
        # Only fall back to menu dispatch if the bound action is not found or doesn't exist

        # Check if we should dispatch F-keys to the pane menu
        # Only do this if the key isn't handled by a bound action or if the bound action
        # doesn't exist for the current pane
        if key in ("f5", "f7", "f8"):
            # Let the bound action execute first, if it exists
            # If we need to dispatch F-keys to menus, we should do it in the respective action methods
            pass

        if self._handle_key_hint(key):
            event.stop()

    def on_click(self, event: events.Click) -> None:
        """Handle mouse clicks for pane interaction."""
        # Handle clicking on the menubar to activate it
        if self.menubar and self.menubar.region.contains(event.x, event.y):
            # Activate menubar if not already active
            if not self.menubar.is_active:
                self._menu_focus_restore = self.focus_pane
                self.menubar.activate()
                self._update_status("Menubar activated via mouse")
                self._update_status_line_for_menubar(True)
            # Let the menubar handle the click
            return

        # Determine which pane was clicked
        left_pane = self.query_one("#left-pane", Vertical)
        right_pane = self.query_one("#right-pane", Vertical)

        # Check if click is in left pane (section list)
        if left_pane.region.contains(event.x, event.y):
            self._update_focus("left")
            self._update_status("Left pane clicked - focus set to sections")
            # The ListView will handle its own item selection and trigger on_list_view_selected
            # event, so we don't need to handle that here

        # Check if click is in right pane (content)
        elif right_pane.region.contains(event.x, event.y):
            if self.current_view:
                # Let the current pane handle the click - delegate to pane-specific behavior
                self._update_focus("right")
                self._update_status("Right pane clicked")
                # Trigger a click event that the current view might handle
                if hasattr(self.current_view, 'on_click'):
                    try:
                        self.current_view.on_click(event)
                    except Exception:
                        # If the view doesn't handle click properly, just focus it
                        pass
            else:
                # Click on right pane placeholder
                self._update_focus("right")

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        """Handle mouse scroll up in the currently focused pane."""
        if self.focus_pane == "left":
            # Scroll the section list
            section_list = self.query_one("#section-list", ListView)
            section_list.action_cursor_up()
        elif self.current_view and hasattr(self.current_view, 'action_cursor_up'):
            # Let the current view handle scroll
            self.current_view.action_cursor_up()
        event.stop()

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        """Handle mouse scroll down in the currently focused pane."""
        if self.focus_pane == "left":
            # Scroll the section list
            section_list = self.query_one("#section-list", ListView)
            section_list.action_cursor_down()
        elif self.current_view and hasattr(self.current_view, 'action_cursor_down'):
            # Let the current view handle scroll
            self.current_view.action_cursor_down()
        event.stop()

    def on_pane_status(self, message: PaneStatus) -> None:
        """Update shell status from a pane."""
        self._update_status(message.message)
        self._load_status_state()

    def on_pane_menu_request(self, message: PaneMenuRequest) -> None:
        """Refresh menubar when a pane signals a menu change."""
        self._refresh_menu_bar()

    def on_pane_focus_request(self, message: PaneFocusRequest) -> None:
        """Honor pane focus requests (e.g., Tab back to sections)."""
        if message.target == "left":
            self._update_focus("left")


class MaestroMCShellApp(App):
    """Minimal app wrapper for MC shell mode."""

    CAPTURE_TAB = True
    CSS = """
    Screen {
        background: $background;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+p", "show_command_palette", "Palette"),
    ]

    ENABLE_MOUSE_SUPPORT = True

    def __init__(self, smoke_mode: bool = False, smoke_seconds: float = 0.5, smoke_out: Optional[str] = None):
        super().__init__()
        self.smoke_mode = smoke_mode
        self.smoke_seconds = smoke_seconds
        self.smoke_out = smoke_out

    def on_mount(self) -> None:
        """Mount the MC shell screen and start smoke timer if needed."""
        self.title = "Maestro TUI - MC Shell"
        self.push_screen(MainShellScreen())
        if self.smoke_mode:
            self.set_timer(self.smoke_seconds, self._smoke_exit)

    def action_show_command_palette(self) -> None:
        """Open the existing command palette (Ctrl+P)."""
        try:
            session = get_active_session()
            session_id = session.id if session else None
        except Exception:
            session_id = None

        palette = CommandPaletteScreen(session_id=session_id)
        self.push_screen(palette)

    def _smoke_exit(self) -> None:
        """Exit cleanly for smoke runs."""
        write_smoke_success(self.smoke_out)
        self.exit()

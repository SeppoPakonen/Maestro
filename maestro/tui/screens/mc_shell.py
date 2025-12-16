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
from maestro.ui_facade.plans import get_active_plan
from maestro.ui_facade.sessions import get_active_session
from maestro.tui.panes.base import PaneFocusRequest, PaneStatus, PaneView, ensure_iterable
from maestro.tui.panes.registry import create_pane
from maestro.tui.utils import ErrorModal, ErrorNormalizer, write_smoke_success
from maestro.tui.widgets.command_palette import CommandPaletteScreen
from maestro.tui.widgets.menubar import MenuItem, MenuItemActivated, Menubar
from maestro.tui.widgets.text_viewer import TextViewerModal
import maestro.tui.panes.sessions  # noqa: F401 - ensure pane is registered


class MainShellScreen(Screen):
    """MC-style two-pane shell with focus + navigation scaffolding."""

    CAPTURE_TAB = True
    status_message: reactive[str] = reactive("Ready")
    show_help_panel: reactive[bool] = reactive(False)
    show_key_hints: reactive[bool] = reactive(True)

    BINDINGS = [
        ("up", "move_up", "Up"),
        ("down", "move_down", "Down"),
        ("enter", "open_selection", "Open"),
        ("escape", "soft_back", "Back"),
        ("r", "refresh_view", "Refresh"),
        ("f1", "open_help", "Help"),
        ("f2", "reserved('F2 Actions')", "Actions"),
        ("f3", "reserved('F3 View')", "View"),
        ("f4", "reserved('F4 Edit')", "Edit"),
        ("f5", "reserved('F5 Run')", "Run"),
        ("f6", "reserved('F6 Switch')", "Switch"),
        ("f7", "reserved('F7 New')", "New"),
        ("f8", "reserved('F8 Delete')", "Delete"),
        ("f9", "toggle_menu", "Menu"),
        ("m", "toggle_menu", "Menu"),
        ("f10", "quit_app", "Quit"),
    ]

    DEFAULT_CSS = """
    MainShellScreen {
        layout: vertical;
    }

    #panes {
        height: 1fr;
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

    #content-host {
        height: 1fr;
        border: solid $primary 50%;
        padding: 1;
    }

    #status-area {
        height: 3;
        background: $surface;
        border-top: solid $primary;
        padding: 0 1;
    }

    #status-bar {
        height: 2;
    }

    #status-hints {
        width: 55%;
        content-align: left middle;
    }

    #focus-indicator {
        width: 20%;
        content-align: center middle;
        text-style: bold;
    }

    #status-message {
        width: 25%;
        content-align: right middle;
        color: $text 80%;
    }

    #function-strip {
        height: 1;
        content-align: center middle;
        color: $text 70%;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.sections: List[str] = [
            "Home",
            "Sessions",
            "Plans",
            "Tasks",
            "Build",
            "Convert",
            "Vault",
            "Replay",
            "Confidence",
            "Integrity",
        ]
        self.focus_pane: str = "left"
        self.current_section: str = self.sections[0]
        self.session_summary: str = "Session: None | Plan: None | Build: None"
        self.menubar: Optional[Menubar] = None
        self._menu_focus_restore: Optional[str] = None
        self.current_view: Optional[PaneView] = None
        self._placeholder_counter: int = 0
        self._suppress_select_open: bool = False

    def compose(self) -> ComposeResult:
        """Compose MC shell layout."""
        self.menubar = Menubar(session_summary=self.session_summary)
        yield self.menubar

        with Horizontal(id="panes"):
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

        with Vertical(id="status-area"):
            with Horizontal(id="status-bar"):
                yield Label(
                    "Tab Switch Pane | Enter Open | Esc Back | F1 Help | F10 Quit",
                    id="status-hints",
                )
                yield Label("FOCUS: LEFT", id="focus-indicator")
                yield Label(self.status_message, id="status-message")
            yield Label(
                "F1 Help  F2 Actions  F3 View  F4 Edit  F5 Run  F6 Switch  F7 New  F8 Delete  F9 Menu  F10 Quit",
                id="function-strip",
            )

    def on_mount(self) -> None:
        """Initialize state after mounting."""
        self._load_status_state()
        section_list = self.query_one("#section-list", ListView)
        section_list.index = 0
        self._update_focus("left")
        self._prepare_menus()
        self._open_current_selection()
        self._update_status_hints()

        if getattr(self.app, "smoke_mode", False):
            # Signal readiness early for smoke validation
            print("MC_SHELL_READY", flush=True)

    def _load_status_state(self) -> None:
        """Load session/plan/build summary for the menubar."""
        try:
            session = get_active_session()
        except Exception:
            session = None

        try:
            plan = get_active_plan(session.id) if session else None
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

    def _update_focus(self, target: str) -> None:
        """Switch focus to the requested pane."""
        self.focus_pane = target
        left_pane = self.query_one("#left-pane", Vertical)
        right_pane = self.query_one("#right-pane", Vertical)
        left_pane.set_class(target == "left", "focused")
        right_pane.set_class(target == "right", "focused")

        if target == "left":
            self.query_one("#section-list", ListView).focus()
        else:
            if self.current_view:
                self.current_view.focus()
            else:
                try:
                    self.query_one("#content-placeholder", Static).focus()
                except Exception:
                    pass

        self.query_one("#focus-indicator", Label).update(f"FOCUS: {target.upper()}")

    def _content_placeholder(self, section_name: str) -> str:
        """Render placeholder content for a section."""
        return (
            f"[b]{section_name}[/b]\n\n"
            "This is a placeholder view. Future tasks will embed the real module here."
        )

    def _open_current_selection(self) -> None:
        """Open the currently selected section into the right pane."""
        content_title = self.query_one("#content-title", Label)
        title_text = self.current_section
        host = self.query_one("#content-host", Vertical)
        self._clear_current_view(host)

        try:
            view = create_pane(self.current_section)
        except Exception as exc:
            content_title.update(title_text)
            self._handle_view_error(exc, f"loading {self.current_section}")
            self._show_placeholder(host, self.current_section)
            self._refresh_actions_menu()
            return

        if view is None:
            content_title.update(title_text)
            self._show_placeholder(host, self.current_section)
            self.current_view = None
            self._refresh_actions_menu()
            return

        self.current_view = view
        try:
            title_text = view.title()
        except Exception:
            title_text = self.current_section
        content_title.update(title_text)
        host.mount(view)
        self._refresh_actions_menu()

    def _selected_section_name(self) -> Optional[str]:
        """Get the current highlighted section name."""
        section_list = self.query_one("#section-list", ListView)
        index = section_list.index if section_list.index is not None else 0
        if index < 0 or index >= len(self.sections):
            return None
        return self.sections[index]

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
        """Invoke refresh on the current pane if it supports it."""
        if not self.current_view:
            return
        try:
            result = self.current_view.refresh_data()
        except Exception as exc:
            self._handle_view_error(exc, f"refreshing {self.current_section}")
            return

        if asyncio.iscoroutine(result):
            asyncio.create_task(self._run_view_refresh(result))

    async def _run_view_refresh(self, coro) -> None:
        try:
            await coro
        except Exception as exc:
            self._handle_view_error(exc, f"refreshing {self.current_section}")

    def _update_status(self, message: str) -> None:
        """Update status message in status bar."""
        self.status_message = message
        self.query_one("#status-message", Label).update(message)

    def action_focus_right(self) -> None:
        """Tab to right pane."""
        self._update_focus("right")
        self._update_status("Focused right pane")

    def action_focus_left(self) -> None:
        """Shift+Tab to left pane."""
        self._suppress_select_open = True
        self._update_focus("left")
        self._update_status("Focused left pane")
        self.call_after_refresh(lambda: setattr(self, "_suppress_select_open", False))

    def action_move_up(self) -> None:
        """Move selection up in focused list."""
        if self.focus_pane != "left":
            return
        section_list = self.query_one("#section-list", ListView)
        section_list.action_cursor_up()
        self._update_status("Moved up")

    def action_move_down(self) -> None:
        """Move selection down in focused list."""
        if self.focus_pane != "left":
            return
        section_list = self.query_one("#section-list", ListView)
        section_list.action_cursor_down()
        self._update_status("Moved down")

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
        if self.menubar and self.menubar.is_open:
            self._close_menubar_restore_focus()
            return
        self._update_status("Back (no modal to close)")

    def action_quit_app(self) -> None:
        """F10 quits the application."""
        self.app.exit()

    def action_reserved(self, label: str) -> None:
        """Placeholder for reserved function keys."""
        self._update_status(f"{label} reserved for future use")

    def action_toggle_menu(self) -> None:
        """Toggle the menubar (F9 style)."""
        if not self.menubar:
            return
        if self.menubar.is_open:
            self._close_menubar_restore_focus()
        else:
            self._menu_focus_restore = self.focus_pane
            self.menubar.open()
            self.menubar.focus()
            self._update_status("Menubar open - arrows to navigate, Esc to close")

    def _close_menubar_restore_focus(self, status: Optional[str] = "Menubar closed") -> None:
        """Close the menubar and restore pane focus."""
        if self.menubar:
            self.menubar.close()
        if self._menu_focus_restore:
            self._update_focus(self._menu_focus_restore)
        self._menu_focus_restore = None
        if status:
            self._update_status(status)

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

    def on_menu_item_activated(self, message: MenuItemActivated) -> None:
        """Handle activated items from the menubar."""
        menu = message.menu
        item = message.item

        if menu == "Navigation":
            self._select_navigation_from_menu(item)
        elif menu == "View":
            self._handle_view_menu(item)
        elif menu == "Actions":
            self._handle_actions_menu(item)
        elif menu == "Help":
            self._handle_help_menu(item)
        elif menu == "Maestro":
            if item.id == "status":
                self._update_status(self.session_summary)
            else:
                self._update_status(f"{item.label} selected")
        self._close_menubar_restore_focus(status=None)

    def _prepare_menus(self) -> None:
        """Load menu contents once the menubar exists."""
        if not self.menubar:
            return
        self.menubar.set_menu_items("Navigation", self._navigation_menu_items())
        self.menubar.set_menu_items("View", self._view_menu_items())
        self.menubar.set_menu_items("Help", self._help_menu_items())
        self.menubar.set_menu_items("Maestro", self._maestro_menu_items())
        self._refresh_actions_menu()

    def _navigation_menu_items(self) -> List[MenuItem]:
        """Menu entries mirroring the navigation list."""
        return [MenuItem(id=section, label=section, trust="[RO]") for section in self.sections]

    def _view_menu_items(self) -> List[MenuItem]:
        """Safe view actions."""
        return [
            MenuItem(id="refresh", label="Refresh", trust="[RO]"),
            MenuItem(id="toggle_help_panel", label="Toggle Help Panel", trust="[RO]"),
            MenuItem(id="toggle_key_hints", label="Toggle Key Hints", trust="[RO]"),
        ]

    def _help_menu_items(self) -> List[MenuItem]:
        """Help menu actions."""
        return [
            MenuItem(id="help", label="F1 Help", trust="[RO]"),
            MenuItem(id="contract", label="Keys & Contract", trust="[RO]"),
        ]

    def _maestro_menu_items(self) -> List[MenuItem]:
        """Base Maestro menu with safe items."""
        return [
            MenuItem(id="about", label="About Maestro", trust="[RO]"),
            MenuItem(id="status", label="Status Summary", trust="[RO]"),
        ]

    def _actions_menu_items(self, section: str) -> List[MenuItem]:
        """Dynamic actions based on current section."""
        mapping = {
            "Sessions": [
                MenuItem("list", "List", "[RO]"),
                MenuItem("set_active", "Set Active", "[MUT][CONF]"),
                MenuItem("new", "New", "[MUT][CONF]"),
                MenuItem("remove", "Remove", "[MUT][CONF]"),
            ],
            "Plans": [
                MenuItem("tree", "Tree", "[RO]"),
                MenuItem("set_active", "Set Active", "[MUT][CONF]"),
                MenuItem("kill_branch", "Kill Branch", "[MUT][CONF]"),
            ],
            "Tasks": [
                MenuItem("run", "Run", "[MUT][CONF]"),
                MenuItem("run_limit", "Run Limit", "[MUT][CONF]"),
                MenuItem("stop", "Stop", "[MUT][CONF]"),
            ],
            "Build": [
                MenuItem("run", "Run", "[MUT][CONF]"),
                MenuItem("status", "Status", "[RO]"),
                MenuItem("fix_loop", "Fix Loop", "[MUT][CONF]"),
            ],
            "Convert": [
                MenuItem("status", "Status", "[RO]"),
                MenuItem("run_next", "Run Next", "[MUT][CONF]"),
                MenuItem("rehearse", "Rehearse", "[MUT][CONF]"),
                MenuItem("promote", "Promote", "[MUT][CONF]"),
            ],
            "Vault": [
                MenuItem("search", "Search", "[RO]"),
                MenuItem("export_selected", "Export Selected", "[RO]"),
            ],
            "Replay": [
                MenuItem("list_runs", "List Runs", "[RO]"),
                MenuItem("replay_dry", "Replay Dry", "[MUT][CONF]"),
                MenuItem("replay_apply", "Replay Apply", "[MUT][CONF]"),
            ],
            "Confidence": [
                MenuItem("open", "Open", "[RO]"),
            ],
            "Integrity": [
                MenuItem("open", "Open", "[RO]"),
            ],
            "Arbitration": [
                MenuItem("open", "Open", "[RO]"),
            ],
        }
        return mapping.get(section, [MenuItem("open", "Open", "[RO]")])

    def _refresh_actions_menu(self) -> None:
        """Update the Actions menu to reflect the current section."""
        if not self.menubar:
            return
        if self.current_view:
            custom_actions = self.current_view.menu_actions()
            if custom_actions:
                self.menubar.set_menu_items("Actions", ensure_iterable(custom_actions))
                return
        actions = self._actions_menu_items(self.current_section)
        self.menubar.set_menu_items("Actions", actions)

    def _select_navigation_from_menu(self, item: MenuItem) -> None:
        """Update section selection based on a menu activation."""
        section = item.payload or item.id
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
        """Execute a view menu selection."""
        if item.id == "refresh":
            self.action_refresh_view()
        elif item.id == "toggle_help_panel":
            self.show_help_panel = not self.show_help_panel
            state = "shown" if self.show_help_panel else "hidden"
            self._update_status(f"Help panel {state} (placeholder)")
        elif item.id == "toggle_key_hints":
            self.show_key_hints = not self.show_key_hints
            self._update_status(f"Key hints {'shown' if self.show_key_hints else 'hidden'}")
            self._update_status_hints()
        else:
            self._update_status(f"{item.label} not wired yet")

    def _handle_actions_menu(self, item: MenuItem) -> None:
        """Handle dynamic action menu items safely."""
        if self.current_view and self.current_view.handle_action(item.id):
            self._update_status(f"{self.current_section}: {item.label}")
            return
        self._update_status(f"{self.current_section}: {item.label} not wired yet")

    def _handle_help_menu(self, item: MenuItem) -> None:
        """Open help or contract viewer."""
        if item.id == "help":
            self.action_open_help()
        elif item.id == "contract":
            self._open_contract()
        else:
            self._update_status(f"{item.label} not wired yet")

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
            "Tab Switch Pane | Enter Open | Esc Back | F1 Help | F10 Quit"
            if self.show_key_hints
            else "Hints hidden (View > Toggle Key Hints)"
        )
        self.query_one("#status-hints", Label).update(hints)

    def _cycle_focus(self) -> None:
        """Move focus to the right pane when requested."""
        if self.focus_pane != "right":
            self.action_focus_right()

    def _handle_view_error(self, exc: Exception, context: str) -> None:
        """Normalize and display view errors without crashing."""
        error_msg = ErrorNormalizer.normalize_exception(exc, context)
        self._update_status(error_msg.message)
        self.app.push_screen(ErrorModal(error_msg))

    def on_key(self, event: events.Key) -> None:
        """Ensure global keys always reach the shell."""
        if event.key in ("f9", "m"):
            self.action_toggle_menu()
            event.stop()

    def on_pane_status(self, message: PaneStatus) -> None:
        """Update shell status from a pane."""
        self._update_status(message.message)
        self._load_status_state()

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
        ("tab", "cycle_focus", "Focus cycle"),
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
    
    def action_focus_left(self) -> None:
        """Proxy focus back to shell when Shift+Tab pressed globally."""
        if isinstance(self.screen, MainShellScreen):
            self.screen.action_focus_left()

    def action_cycle_focus(self) -> None:
        """Cycle focus between panes."""
        if isinstance(self.screen, MainShellScreen):
            self.screen._cycle_focus()

    def on_key(self, event: events.Key) -> None:
        """Catch global navigation keys at the app level."""
        if event.key == "tab":
            if isinstance(self.screen, MainShellScreen):
                self.screen._cycle_focus()
            event.stop()
        elif event.key in ("shift+tab", "backtab"):
            self.action_focus_left()
            event.stop()
        elif event.key == "enter":
            if isinstance(self.screen, MainShellScreen):
                self.screen.action_open_selection()
            event.stop()
        elif event.key in ("f9", "m"):
            if isinstance(self.screen, MainShellScreen):
                self.screen.action_toggle_menu()
            event.stop()

    def _smoke_exit(self) -> None:
        """Exit cleanly for smoke runs."""
        write_smoke_success(self.smoke_out)
        self.exit()

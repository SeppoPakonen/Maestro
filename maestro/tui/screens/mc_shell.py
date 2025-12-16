"""
Midnight Commander–style shell skeleton for Maestro TUI.
"""
from __future__ import annotations

from typing import List, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Label, ListItem, ListView, Static

from maestro.ui_facade.build import get_active_build_target
from maestro.ui_facade.plans import get_active_plan
from maestro.ui_facade.sessions import get_active_session
from maestro.tui.utils import write_smoke_success
from maestro.tui.widgets.command_palette import CommandPaletteScreen


class MainShellScreen(Screen):
    """MC-style two-pane shell with focus + navigation scaffolding."""

    status_message: reactive[str] = reactive("Ready")

    BINDINGS = [
        ("tab", "focus_right", "Focus right pane"),
        ("shift+tab", "focus_left", "Focus left pane"),
        ("up", "move_up", "Up"),
        ("down", "move_down", "Down"),
        ("enter", "open_selection", "Open"),
        ("escape", "soft_back", "Back"),
        ("f1", "reserved('F1 Help')", "Help"),
        ("f2", "reserved('F2 Actions')", "Actions"),
        ("f3", "reserved('F3 View')", "View"),
        ("f4", "reserved('F4 Edit')", "Edit"),
        ("f5", "reserved('F5 Run')", "Run"),
        ("f6", "reserved('F6 Switch')", "Switch"),
        ("f7", "reserved('F7 New')", "New"),
        ("f8", "reserved('F8 Delete')", "Delete"),
        ("f9", "reserved('F9 Menu')", "Menu"),
        ("f10", "quit_app", "Quit"),
    ]

    DEFAULT_CSS = """
    MainShellScreen {
        layout: vertical;
    }

    #menubar {
        height: 1;
        padding: 0 1;
        background: $surface;
        color: $text;
        text-style: bold;
    }

    #menubar Label {
        height: 1;
        content-align: left middle;
    }

    #menu-left {
        width: 20%;
    }

    #menu-center {
        width: 40%;
        content-align: center middle;
    }

    #menu-right {
        width: 40%;
        content-align: right middle;
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

    #content-body {
        height: 1fr;
        border: solid $primary 50%;
        padding: 1;
    }

    #status-bar {
        height: 1;
        background: $surface;
        border-top: solid $primary;
        padding: 0 1;
    }

    #status-hints {
        width: 70%;
        content-align: left middle;
    }

    #focus-indicator {
        width: 15%;
        content-align: center middle;
        text-style: bold;
    }

    #status-message {
        width: 15%;
        content-align: right middle;
        color: $text 80%;
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

    def compose(self) -> ComposeResult:
        """Compose MC shell layout."""
        yield Horizontal(
            Label("Maestro", id="menu-left"),
            Label("Navigator", id="menu-center"),
            Label(self.session_summary, id="menu-right"),
            id="menubar",
        )

        with Horizontal(id="panes"):
            with Vertical(id="left-pane", classes="pane focused"):
                yield Label("Sections", id="left-title")
                section_items = [ListItem(Label(name)) for name in self.sections]
                yield ListView(*section_items, id="section-list")

            with Vertical(id="right-pane", classes="pane"):
                yield Label(self.current_section, id="content-title")
                content_body = Static(self._content_placeholder(self.current_section), id="content-body")
                content_body.can_focus = True
                yield content_body

        yield Horizontal(
            Label("Tab Switch Pane | Enter Open | Esc Back | F1 Help | F10 Quit", id="status-hints"),
            Label("FOCUS: LEFT", id="focus-indicator"),
            Label(self.status_message, id="status-message"),
            id="status-bar",
        )

    def on_mount(self) -> None:
        """Initialize state after mounting."""
        self._load_status_state()
        section_list = self.query_one("#section-list", ListView)
        section_list.index = 0
        self._update_focus("left")
        self._open_current_selection()

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
        self.query_one("#menu-right", Label).update(self.session_summary)

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
            self.query_one("#content-body", Static).focus()

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
        content_body = self.query_one("#content-body", Static)
        content_title.update(self.current_section)
        content_body.update(self._content_placeholder(self.current_section))
        self.query_one("#menu-center", Label).update(f"Navigator | {self.current_section}")

    def _selected_section_name(self) -> Optional[str]:
        """Get the current highlighted section name."""
        section_list = self.query_one("#section-list", ListView)
        index = section_list.index if section_list.index is not None else 0
        if index < 0 or index >= len(self.sections):
            return None
        return self.sections[index]

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
        self._update_focus("left")
        self._update_status("Focused left pane")

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
            self._update_status(f"Opened {selected}")
        else:
            self._update_status("No action yet in right pane")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Mirror ListView selection into the content pane."""
        if event.list_view.id != "section-list":
            return
        selected = self._selected_section_name()
        if not selected:
            return
        self.current_section = selected
        self._open_current_selection()
        self._update_status(f"Opened {selected}")

    def action_soft_back(self) -> None:
        """Esc to cancel/back hint."""
        self._update_status("Back (no modal to close)")

    def action_quit_app(self) -> None:
        """F10 quits the application."""
        self.app.exit()

    def action_reserved(self, label: str) -> None:
        """Placeholder for reserved function keys."""
        self._update_status(f"{label} reserved for future use")


class MaestroMCShellApp(App):
    """Minimal app wrapper for MC shell mode."""

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

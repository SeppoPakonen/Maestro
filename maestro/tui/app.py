"""
Maestro TUI Application
"""
from textual.app import App
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Footer, Header
from textual import on
from textual.types import MessageTarget
from maestro.ui_facade.sessions import get_active_session, list_sessions
from maestro.ui_facade.plans import get_active_plan, list_plans
from maestro.ui_facade.build import get_active_build_target, list_build_targets
from maestro.tui.screens.home import HomeScreen
from maestro.tui.screens.sessions import SessionsScreen
from maestro.tui.screens.plans import PlansScreen
from maestro.tui.screens.tasks import TasksScreen
from maestro.tui.screens.build import BuildScreen
from maestro.tui.screens.convert import ConvertScreen
from maestro.tui.screens.logs import LogsScreen
from maestro.tui.screens.help import HelpScreen
from maestro.tui.widgets.command_palette import CommandPaletteScreen


class MaestroTUI(App):
    """Main Maestro TUI application."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        height: 1fr;
        width: 100%;
    }

    #status-bar {
        dock: top;
        height: 1;
        background: $primary;
        color: $text;
        text-style: bold;
    }

    #nav-menu {
        dock: left;
        width: 25;
        background: $surface;
        border-right: solid $primary;
    }

    #main-content {
        height: 1fr;
        width: 100%;
    }

    .status-label {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
        ("?", "show_help", "Help"),
        ("r", "refresh_status", "Refresh"),
        ("ctrl+p", "show_command_palette", "Palette"),
        ("home", "switch_to_screen('home')", "Home"),
        ("s", "switch_to_screen('sessions')", "Sessions"),
        ("p", "switch_to_screen('plans')", "Plans"),
        ("t", "switch_to_screen('tasks')", "Tasks"),
        ("b", "switch_to_screen('build')", "Build"),
        ("c", "switch_to_screen('convert')", "Convert"),
        ("l", "switch_to_screen('logs')", "Logs"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_session = None
        self.active_plan = None
        self.active_build_target = None
        self.repo_root = "./"  # Simplified for now
        self._load_status_state()

    def _load_status_state(self) -> None:
        """Load the current status state from facade."""
        try:
            self.active_session = get_active_session()
        except Exception:
            self.active_session = None

        # We need session ID to get active plan, so check if we have an active session
        if self.active_session:
            try:
                from maestro.ui_facade.plans import get_active_plan
                self.active_plan = get_active_plan(self.active_session.id)
            except Exception:
                self.active_plan = None
        else:
            self.active_plan = None

        try:
            # Get build target only if there's an active session
            if self.active_session:
                self.active_build_target = get_active_build_target(self.active_session.id)
            else:
                self.active_build_target = get_active_build_target("default_session")  # fallback
        except Exception:
            self.active_build_target = None

    def compose(self):
        """Create child widgets for the app."""
        # Create status bar with global information
        status_container = Horizontal(
            Label(f"Root: {self.repo_root}", id="repo-root", classes="status-label"),
            Label(f" | Session: {self.active_session.id[:8] + '...' if self.active_session else 'None'}",
                  id="active-session", classes="status-label"),
            Label(f" | Plan: {self.active_plan.plan_id[:8] + '...' if self.active_plan else 'None'}",
                  id="active-plan", classes="status-label"),
            Label(f" | Build: {self.active_build_target.id[:8] + '...' if self.active_build_target else 'None'}",
                  id="active-build", classes="status-label"),
            id="status-bar"
        )

        yield status_container

        # Create main layout
        main_layout = Horizontal(id="main-container")
        main_layout.mount(
            Vertical(
                Label("[b]Navigation[/b]", classes="nav-title"),
                Label("🏠 Home", id="nav-home", classes="nav-item"),
                Label("📋 Sessions", id="nav-sessions", classes="nav-item"),
                Label("📊 Plans", id="nav-plans", classes="nav-item"),
                Label("✅ Tasks", id="nav-tasks", classes="nav-item"),
                Label("🔨 Build", id="nav-build", classes="nav-item"),
                Label("🔄 Convert", id="nav-convert", classes="nav-item"),
                Label("📄 Logs", id="nav-logs", classes="nav-item"),
                Label("❓ Help", id="nav-help", classes="nav-item"),
                id="nav-menu"
            )
        )

        main_content = Vertical(
            id="main-content"
        )
        main_layout.mount(main_content)

        yield main_layout
        yield Footer(show_command_palette=False)

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.title = "Maestro TUI"
        # Start with home screen
        self.switch_screen(HomeScreen())

        # Bind click events for navigation items
        self.query_one("#nav-home").on("click", lambda: self.switch_to_screen("home"))
        self.query_one("#nav-sessions").on("click", lambda: self.switch_to_screen("sessions"))
        self.query_one("#nav-plans").on("click", lambda: self.switch_to_screen("plans"))
        self.query_one("#nav-tasks").on("click", lambda: self.switch_to_screen("tasks"))
        self.query_one("#nav-build").on("click", lambda: self.switch_to_screen("build"))
        self.query_one("#nav-convert").on("click", lambda: self.switch_to_screen("convert"))
        self.query_one("#nav-logs").on("click", lambda: self.switch_to_screen("logs"))
        self.query_one("#nav-help").on("click", lambda: self.switch_to_screen("help"))

    def switch_to_screen(self, screen_name: str) -> None:
        """Switch to a specific screen."""
        screen_map = {
            "home": HomeScreen,
            "sessions": SessionsScreen,
            "plans": PlansScreen,
            "tasks": TasksScreen,
            "build": BuildScreen,
            "convert": ConvertScreen,
            "logs": LogsScreen,
            "help": HelpScreen,
        }

        if screen_name in screen_map:
            self.switch_screen(screen_map[screen_name]())

    def action_switch_to_screen(self, screen_name: str) -> None:
        """Action to switch to a specific screen."""
        self.switch_to_screen(screen_name)

    def action_show_help(self) -> None:
        """Action to show help screen."""
        self.switch_to_screen("help")

    def action_refresh_status(self) -> None:
        """Action to refresh status information."""
        self._load_status_state()
        # Update the status bar labels with new information
        self.query_one("#repo-root").update(f"Root: {self.repo_root}")
        self.query_one("#active-session").update(
            f" | Session: {self.active_session.id[:8] + '...' if self.active_session else 'None'}"
        )
        self.query_one("#active-plan").update(
            f" | Plan: {self.active_plan.plan_id[:8] + '...' if self.active_plan else 'None'}"
        )
        self.query_one("#active-build").update(
            f" | Build: {self.active_build_target.id[:8] + '...' if self.active_build_target else 'None'}"
        )

    def action_show_command_palette(self) -> None:
        """Action to show command palette."""
        # Get the active session ID for context
        session_id = self.active_session.id if self.active_session else None
        palette = CommandPaletteScreen(session_id=session_id)
        self.push_screen(palette)


def main():
    """Run the TUI application."""
    app = MaestroTUI()
    app.run()


if __name__ == "__main__":
    main()
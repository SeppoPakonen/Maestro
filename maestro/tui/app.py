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

    /* Task Screen Styles */
    #control-bar {
        height: 3;
        dock: top;
        background: $surface;
        border-bottom: solid $primary;
    }

    .control-buttons {
        height: 100%;
        align: center middle;
        gap: 1;
    }

    .control-buttons Button {
        width: 20;
    }

    #main-content {
        layout: horizontal;
        height: 1fr;
    }

    .task-list-container {
        width: 60%;
        height: 1fr;
        border-right: solid $primary;
    }

    .log-viewer-container {
        width: 40%;
        height: 1fr;
    }

    .task-item {
        height: 1;
        padding: 0 1;
    }

    .task-item.running {
        background: $success 10%;
        text-style: bold;
    }

    .task-item.selected {
        background: $accent 20%;
        text-style: reverse;
    }

    #log-viewer {
        height: 1fr;
        width: 1fr;
        border: solid $primary;
    }

    .status-message {
        height: 1;
        dock: bottom;
        background: $surface;
        border-top: solid $primary;
        content-align: left middle;
        padding: 0 1;
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

    def __init__(self, smoke_mode=False, smoke_seconds=0.5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.smoke_mode = smoke_mode
        self.smoke_seconds = smoke_seconds
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
        # Create status bar with global information - use getattr for safe access during initialization
        session_id_display = getattr(self, 'active_session', None)
        session_id_display = session_id_display.id[:8] + '...' if session_id_display else 'None'

        plan_id_display = getattr(self, 'active_plan', None)
        plan_id_display = plan_id_display.plan_id[:8] + '...' if plan_id_display else 'None'

        build_id_display = getattr(self, 'active_build_target', None)
        build_id_display = build_id_display.id[:8] + '...' if build_id_display else 'None'

        yield Horizontal(
            Label(f"Root: {getattr(self, 'repo_root', 'unknown')}", id="repo-root", classes="status-label"),
            Label(f" | Session: {session_id_display}", id="active-session", classes="status-label"),
            Label(f" | Plan: {plan_id_display}", id="active-plan", classes="status-label"),
            Label(f" | Build: {build_id_display}", id="active-build", classes="status-label"),
            id="status-bar"
        )

        # Create main layout with both navigation and content side by side
        with Horizontal(id="main-container"):
            yield Vertical(
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

            yield Vertical(
                id="main-content"
            )

        yield Footer(show_command_palette=False)

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.title = "Maestro TUI"
        # Mount the home screen content directly in the main content area
        main_content = self.query_one("#main-content", Vertical)
        home_screen = HomeScreen()
        widgets = list(home_screen.compose())
        for widget in widgets:
            main_content.mount(widget)

        # Bind click events for navigation items - need to wait a bit for the DOM to be ready
        self.call_after_refresh(self._bind_navigation_events)

        # If in smoke mode, set up a timer to exit after the specified time
        if self.smoke_mode:
            # Use a small delay to ensure the app starts rendering before exiting
            self.set_timer(self.smoke_seconds, self._smoke_exit)

    def _bind_navigation_events(self) -> None:
        """Bind navigation events after the DOM is loaded."""
        try:
            self.query_one("#nav-home").can_focus = True
            self.query_one("#nav-home").tooltip = "Go to Home"
            # Set up click events using set_timer to ensure elements exist
            self.set_timer(0.1, lambda: self._setup_click_handlers())
        except:
            # If immediate setup fails, try again after a short delay
            self.set_timer(0.2, lambda: self._setup_click_handlers())

    def _setup_click_handlers(self):
        """Actually set up the click handlers."""
        try:
            # Replace the current content with new screen content
            home_widget = self.query_one("#nav-home", Label)
            home_widget.styles.cursor = "pointer"
            self.query_one("#nav-home").on("click", lambda: self._switch_main_content(HomeScreen()))

            sessions_widget = self.query_one("#nav-sessions", Label)
            sessions_widget.styles.cursor = "pointer"
            self.query_one("#nav-sessions").on("click", lambda: self._switch_main_content(SessionsScreen()))

            plans_widget = self.query_one("#nav-plans", Label)
            plans_widget.styles.cursor = "pointer"
            self.query_one("#nav-plans").on("click", lambda: self._switch_main_content(PlansScreen()))

            tasks_widget = self.query_one("#nav-tasks", Label)
            tasks_widget.styles.cursor = "pointer"
            self.query_one("#nav-tasks").on("click", lambda: self._switch_main_content(TasksScreen()))

            build_widget = self.query_one("#nav-build", Label)
            build_widget.styles.cursor = "pointer"
            self.query_one("#nav-build").on("click", lambda: self._switch_main_content(BuildScreen()))

            convert_widget = self.query_one("#nav-convert", Label)
            convert_widget.styles.cursor = "pointer"
            self.query_one("#nav-convert").on("click", lambda: self._switch_main_content(ConvertScreen()))

            logs_widget = self.query_one("#nav-logs", Label)
            logs_widget.styles.cursor = "pointer"
            self.query_one("#nav-logs").on("click", lambda: self._switch_main_content(LogsScreen()))

            help_widget = self.query_one("#nav-help", Label)
            help_widget.styles.cursor = "pointer"
            self.query_one("#nav-help").on("click", lambda: self._switch_main_content(HelpScreen()))
        except Exception as e:
            # If binding fails, just continue without it
            pass

    def _switch_main_content(self, screen_instance):
        """Replace the main content area with a new screen."""
        try:
            # Clear the main content area
            main_content = self.query_one("#main-content", Vertical)
            main_content.remove_children()

            # Use the screen's compose method to get widgets and mount them
            # Since compose() returns a generator, we need to collect the widgets
            widgets = list(screen_instance.compose())
            for widget in widgets:
                main_content.mount(widget)
        except Exception as e:
            # If all else fails, just display an error message
            main_content = self.query_one("#main-content", Vertical)
            main_content.remove_children()
            main_content.mount(Label("Error loading screen content"))

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

    def _smoke_exit(self):
        """Handle the smoke mode exit."""
        import sys
        import os
        # Write success indicator to file to avoid terminal output issues
        smoke_success_file = os.environ.get("MAESTRO_SMOKE_SUCCESS_FILE", "/tmp/maestro_tui_smoke_success")
        try:
            with open(smoke_success_file, 'w') as f:
                f.write("MAESTRO_TUI_SMOKE_OK\n")
        except:
            # If file writing fails, try standard output as backup
            print("MAESTRO_TUI_SMOKE_OK")

        # Also print to stdout as backup (though may not be visible in full-screen apps)
        print("MAESTRO_TUI_SMOKE_OK", flush=True)
        sys.stdout.flush()
        self.exit()


def main(smoke_mode=False, smoke_seconds=0.5):
    """Run the TUI application."""
    app = MaestroTUI(smoke_mode=smoke_mode, smoke_seconds=smoke_seconds)
    app.run()


if __name__ == "__main__":
    main()
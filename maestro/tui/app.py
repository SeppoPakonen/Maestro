"""
Maestro TUI Application
"""
import time
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
from maestro.tui.screens.memory import MemoryScreen
from maestro.tui.screens.semantic import SemanticScreen
from maestro.tui.screens.arbitration import ArbitrationScreen
from maestro.tui.screens.replay import ReplayScreen
from maestro.tui.screens.semantic_diff import SemanticDiffScreen
from maestro.tui.screens.confidence import ConfidenceScreen
from maestro.tui.screens.vault import VaultScreen
from maestro.tui.widgets.command_palette import CommandPaletteScreen
from maestro.tui.utils import global_status_manager, LoadingIndicator


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

    .min-height-stable {
        height: 10;
    }

    .placeholder-stable {
        height: 1fr;
        content-align: center middle;
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

    /* Convert Dashboard Styles */
    #dashboard-container {
        height: 1fr;
        width: 100%;
    }

    .dashboard-panel {
        height: 1fr;
        border: solid $primary;
    }

    #stage-timeline-container {
        width: 30%;
        border-right: solid $primary;
    }

    #stage-details-container {
        width: 40%;
        border-right: solid $primary;
    }

    #controls-container {
        width: 30%;
    }

    .stage-item {
        height: 1;
        padding: 0 1;
        background: $surface;
    }

    .stage-item.selected {
        background: $accent 30%;
        text-style: bold;
    }

    .stage-title {
        text-style: bold;
        color: $success;
    }

    .stage-status {
        color: $text;
    }

    .stage-detail {
        color: $text 70%;
    }

    .artifacts-title, .description-title, .blocking-title {
        text-style: bold;
        color: $primary;
    }

    .artifact-item {
        color: $text 80%;
        text-style: italic;
    }

    .description-text {
        color: $text 90%;
    }

    .blocking-reason {
        color: $warning;
        text-style: bold;
    }

    .pipeline-status, .active-stage {
        color: $primary;
        text-style: bold;
    }

    .checkpoints-title {
        color: $warning;
        text-style: bold;
    }

    .checkpoint-button {
        width: 100%;
        margin: 1 0;
    }

    .checkpoint-controls {
        width: 100%;
    }

    .checkpoint-controls Button {
        width: 30%;
        margin-right: 1;
    }

    .run-history-title {
        color: $primary;
        text-style: bold;
    }

    .run-item {
        color: $text 80%;
    }

    .run-summary {
        color: $text 60%;
        margin-left: 1;
    }

    .run-item-sm {
        color: $text 70%;
    }

    .history-title {
        color: $primary;
        text-style: bold;
    }

    .history-placeholder {
        color: $text 40%;
        text-style: italic;
    }

    .placeholder {
        color: $text 50%;
        text-style: italic;
    }

    /* Memory Screen Styles */
    #memory-container {
        height: 1fr;
        width: 100%;
    }

    .memory-panel {
        height: 1fr;
        border: solid $primary;
    }

    .category-title {
        text-style: bold;
        color: $primary;
        margin: 0 0 1 0;
    }

    .category-item {
        padding: 0 1;
        height: 1;
        background: $surface;
        border-left: solid $primary;
    }

    .category-item:hover {
        background: $surface 20%;
    }

    .selected {
        background: $accent 30%;
        text-style: bold;
    }

    .entry-item {
        height: 1;
        padding: 0 1;
        background: $surface;
    }

    .entry-item:hover {
        background: $surface 20%;
    }

    .entry-meta {
        padding: 0 1 0 2;
        color: $text 70%;
        height: 1;
    }

    .detail-title {
        text-style: bold;
        color: $success;
        margin: 0 0 1 0;
    }

    .detail-status, .detail-timestamp, .detail-origin, .detail-field {
        margin: 0 0 1 0;
        color: $text 90%;
    }

    .detail-section-title {
        text-style: bold;
        color: $primary;
        margin: 1 0 0 0;
    }

    .detail-reason, .detail-reference, .detail-file, .detail-example, .detail-note {
        margin: 0 0 1 1;
        color: $text 80%;
    }

    .search-title {
        text-style: bold;
        color: $primary;
        margin: 0 1 0 0;
    }

    .search-input {
        width: 1fr;
    }

    .filter-title, .search-title {
        text-style: bold;
        color: $primary;
        margin: 0 1 0 0;
    }

    .filter-row {
        margin: 0 0 1 0;
    }

    .filter-label {
        width: 15;
        color: $text 80%;
    }

    .filter-value {
        color: $text 90%;
    }

    /* Vault Screen Styles */
    #vault-layout {
        height: 1fr;
        width: 100%;
    }

    .panel {
        height: 1fr;
        border: solid $primary;
    }

    #source-selector-container {
        width: 25%;
        border-right: solid $primary;
    }

    #item-list-container {
        width: 30%;
        border-right: solid $primary;
    }

    #viewer-container {
        width: 35%;
        border-right: solid $primary;
    }

    #metadata-container {
        width: 10%;
    }

    .filter-option {
        height: 1;
        padding: 0 1;
        background: $surface;
    }

    .filter-option:hover {
        background: $surface 20%;
    }

    .items-list {
        height: 1fr;
    }

    .items-list ListItem {
        height: 1;
        padding: 0 1;
    }

    .items-list ListItem:hover {
        background: $surface 20%;
    }

    .content-display {
        height: 1fr;
        width: 1fr;
        border: solid $primary;
        padding: 1;
    }

    .meta-field {
        margin: 0 0 1 0;
        color: $text 90%;
    }

    .actions-title {
        text-style: bold;
        color: $primary;
        margin: 0 0 1 0;
    }

    .action-item {
        margin: 0 0 1 0;
        color: $text 80%;
    }

    .action-item:hover {
        color: $text;
        text-style: bold;
    }

    .panel {
        padding: 1;
    }

    /* Trust Signal Colors - Consistent Color Discipline */
    .safe { color: $success; }
    .warning { color: $warning; }
    .danger { color: $error; }
    .info { color: $primary; }

    /* Trust Signal Labels */
    .trust-label {
        text-style: italic;
        color: $text 70%;
    }

    /* Explicit state indicators */
    .read-only-indicator {
        color: $success;
        text-style: italic;
    }

    .mutation-indicator {
        color: $warning;
        text-style: bold;
    }

    .confirmation-required {
        color: $warning;
        text-style: bold;
    }

    .hidden {
        display: none;
    }

    .visible {
        display: block;
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
        ("y", "switch_to_screen('replay')", "Replay"),
        ("a", "switch_to_screen('arbitration')", "Arbitration Arena"),
        ("i", "switch_to_screen('semantic')", "Semantic Integrity"),
        ("d", "switch_to_screen('semantic_diff')", "Semantic Diff Explorer"),
        ("m", "switch_to_screen('memory')", "Memory"),
        ("l", "switch_to_screen('logs')", "Logs"),
        ("f", "switch_to_screen('confidence')", "Confidence Scoreboard"),
        ("v", "switch_to_screen('vault')", "Vault"),
    ]

    def __init__(self, smoke_mode=False, smoke_seconds=0.5, smoke_out=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.smoke_mode = smoke_mode
        self.smoke_seconds = smoke_seconds
        self.smoke_out = smoke_out
        self.active_session = None
        self.active_plan = None
        self.active_build_target = None
        self.repo_root = "./"  # Simplified for now
        self.loading_indicator = LoadingIndicator()
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

        # Create status bar with loading indicator
        yield Horizontal(
            Label(" ⏳ ", id="global-loading-indicator", classes="status-label hidden"),
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
                Label("📺 Replay", id="nav-replay", classes="nav-item"),
                Label("🏆 Arbitration", id="nav-arbitration", classes="nav-item"),
                Label("🔍 Integrity", id="nav-semantic", classes="nav-item"),
                Label("🔍 Diff Explorer", id="nav-semantic-diff", classes="nav-item"),
                Label("🧠 Memory", id="nav-memory", classes="nav-item"),
                Label("📄 Logs", id="nav-logs", classes="nav-item"),
                Label("📊 Confidence", id="nav-confidence", classes="nav-item"),
                Label("📦 Vault", id="nav-vault", classes="nav-item"),
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

        # Set up global status manager
        global_status_manager.set_status_bar_widget(self.query_one("#status-bar", Horizontal))

        # Mount the home screen content directly in the main content area
        main_content = self.query_one("#main-content", Vertical)
        home_screen = HomeScreen()
        widgets = list(home_screen.compose())
        for widget in widgets:
            main_content.mount(widget)

        # Bind click events for navigation items - need to wait a bit for the DOM to be ready
        self.call_after_refresh(self._bind_navigation_events)

        # Set up periodic update for loading indicators
        self.set_interval(0.2, self._update_loading_indicators)

        # If in smoke mode, set up a timer to exit after the specified time
        if self.smoke_mode:
            # Use a small delay to ensure the app starts rendering before exiting
            self.set_timer(self.smoke_seconds, self._smoke_exit)

    def _update_loading_indicators(self) -> None:
        """Update loading indicators based on active loaders."""
        loading_indicator = self.query_one("#global-loading-indicator", Label)

        if self.loading_indicator.global_loader_active:
            # Show the loading indicator by removing the hidden class
            loading_indicator.remove_class("hidden")
            loading_indicator.add_class("visible")
        else:
            # Hide the loading indicator by adding the hidden class
            loading_indicator.remove_class("visible")
            loading_indicator.add_class("hidden")

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

            replay_widget = self.query_one("#nav-replay", Label)
            replay_widget.styles.cursor = "pointer"
            self.query_one("#nav-replay").on("click", lambda: self._switch_main_content(ReplayScreen()))

            arbitration_widget = self.query_one("#nav-arbitration", Label)
            arbitration_widget.styles.cursor = "pointer"
            self.query_one("#nav-arbitration").on("click", lambda: self._switch_main_content(ArbitrationScreen()))

            semantic_widget = self.query_one("#nav-semantic", Label)
            semantic_widget.styles.cursor = "pointer"
            self.query_one("#nav-semantic").on("click", lambda: self._switch_main_content(SemanticScreen()))

            semantic_diff_widget = self.query_one("#nav-semantic-diff", Label)
            semantic_diff_widget.styles.cursor = "pointer"
            self.query_one("#nav-semantic-diff").on("click", lambda: self._switch_main_content(SemanticDiffScreen()))

            memory_widget = self.query_one("#nav-memory", Label)
            memory_widget.styles.cursor = "pointer"
            self.query_one("#nav-memory").on("click", lambda: self._switch_main_content(MemoryScreen()))

            logs_widget = self.query_one("#nav-logs", Label)
            logs_widget.styles.cursor = "pointer"
            self.query_one("#nav-logs").on("click", lambda: self._switch_main_content(LogsScreen()))

            confidence_widget = self.query_one("#nav-confidence", Label)
            confidence_widget.styles.cursor = "pointer"
            self.query_one("#nav-confidence").on("click", lambda: self._switch_main_content(ConfidenceScreen()))

            vault_widget = self.query_one("#nav-vault", Label)
            vault_widget.styles.cursor = "pointer"
            self.query_one("#nav-vault").on("click", lambda: self._switch_main_content(VaultScreen()))

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
            "replay": ReplayScreen,
            "arbitration": ArbitrationScreen,
            "semantic": SemanticScreen,
            "semantic_diff": SemanticDiffScreen,
            "memory": MemoryScreen,
            "logs": LogsScreen,
            "confidence": ConfidenceScreen,
            "vault": VaultScreen,
            "help": HelpScreen,
        }

        if screen_name in screen_map:
            self._switch_main_content(screen_map[screen_name]())

    def action_switch_to_screen(self, screen_name: str) -> None:
        """Action to switch to a specific screen."""
        self.switch_to_screen(screen_name)

    def action_show_help(self) -> None:
        """Action to show help screen."""
        self._switch_main_content(HelpScreen())

    def action_refresh_status(self) -> None:
        """Action to refresh status information."""
        # Start loader for refresh operation
        refresh_call_id = f"refresh_{time.time()}"
        self.loading_indicator.start_loader(refresh_call_id)

        try:
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
        finally:
            # Stop loader for refresh operation
            self.loading_indicator.stop_loader(refresh_call_id)

    def action_show_command_palette(self) -> None:
        """Action to show command palette."""
        # Get the active session ID for context
        session_id = self.active_session.id if self.active_session else None
        from maestro.tui.widgets.command_palette import CommandPaletteScreen
        palette = CommandPaletteScreen(session_id=session_id)
        self.push_screen(palette)

    def _smoke_exit(self):
        """Handle the smoke mode exit."""
        import sys
        import os
        # Write success indicator to file if specified
        smoke_success_file = self.smoke_out or os.environ.get("MAESTRO_SMOKE_SUCCESS_FILE", "/tmp/maestro_tui_smoke_success")
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


def main(smoke_mode=False, smoke_seconds=0.5, smoke_out=None):
    """Run the TUI application."""
    app = MaestroTUI(smoke_mode=smoke_mode, smoke_seconds=smoke_seconds, smoke_out=smoke_out)
    app.run()


if __name__ == "__main__":
    main()
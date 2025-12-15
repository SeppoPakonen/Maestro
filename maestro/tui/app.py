"""
Maestro TUI Application
"""
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Label, Static
from maestro.ui_facade.sessions import get_active_session


class MaestroTUI(App):
    """Main Maestro TUI application."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        # Try to get active session using the facade
        try:
            active_session = get_active_session()
            if active_session:
                session_info = f"Active Session: {active_session.id[:8]}... - {active_session.root_task[:30]}..."
            else:
                session_info = "No active session found"
        except Exception as e:
            session_info = f"Error accessing sessions: {str(e)}"

        yield Vertical(
            Label("[b]Maestro TUI[/b]", classes="title"),
            Label("Human interface (CLI remains primary automation surface)", classes="subtitle"),
            Label(f"\nSession Status: {session_info}", classes="status"),
            Label("\nPress 'q' to quit", classes="instructions"),
            classes="main-container"
        )

        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.title = "Maestro TUI"


def main():
    """Run the TUI application."""
    app = MaestroTUI()
    app.run()


if __name__ == "__main__":
    main()
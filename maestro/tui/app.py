"""
Maestro TUI Application
"""
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Label


class MaestroTUI(App):
    """Main Maestro TUI application."""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        
        yield Vertical(
            Label("[b]Maestro TUI[/b]", classes="title"),
            Label("Human interface (CLI remains primary automation surface)", classes="subtitle"),
            Label("\nPlaceholder UI - TUI development has not started yet", classes="status"),
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
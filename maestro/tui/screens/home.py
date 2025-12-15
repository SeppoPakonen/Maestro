"""
Home Screen for Maestro TUI
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Button
from textual.containers import Vertical, Horizontal, Container


class HomeScreen(Screen):
    """Home screen of the Maestro TUI."""
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the home screen."""
        yield Header()
        
        yield Vertical(
            Label("[b]Maestro TUI - Home[/b]", classes="title"),
            Label("\nWelcome to Maestro TUI", classes="subtitle"),
            Label("This is the main dashboard for Maestro AI Task Management", classes="content"),
            Label("\nUse the navigation menu or command palette (Ctrl+P) to browse:", classes="instructions"),
            Label("- Sessions", classes="list-item"),
            Label("- Plans", classes="list-item"), 
            Label("- Tasks", classes="list-item"),
            Label("- Build", classes="list-item"),
            Label("- Convert", classes="list-item"),
            Label("- Logs", classes="list-item"),
            Label("\nNot implemented yet", classes="placeholder"),
            classes="main-container"
        )
        
        yield Footer()
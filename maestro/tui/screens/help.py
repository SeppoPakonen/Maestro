"""
Help Screen for Maestro TUI
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Static
from textual.containers import Vertical, Container


class HelpScreen(Screen):
    """Help screen of the Maestro TUI."""
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the help screen."""
        yield Header()
        
        yield Vertical(
            Label("[b]Help & Keybindings[/b]", classes="title"),
            Label("\n[b]Navigation:[/b]", classes="subtitle"),
            Label("  Ctrl+P     - Open command palette", classes="help-item"),
            Label("  ?          - Open this help screen", classes="help-item"),
            Label("  q or Ctrl+C - Quit application", classes="help-item"),
            Label("  r          - Refresh status", classes="help-item"),
            Label("  Esc        - Close modals/palette", classes="help-item"),
            Label("\n[b]Available Screens:[/b]", classes="subtitle"),
            Label("  home       - Home dashboard", classes="help-item"),
            Label("  sessions   - Session management", classes="help-item"),
            Label("  phases     - Phase visualization", classes="help-item"),
            Label("  tasks      - Task management", classes="help-item"),
            Label("  build      - Build targets", classes="help-item"),
            Label("  convert    - Format conversion tools", classes="help-item"),
            Label("  logs       - System logs", classes="help-item"),
            Label("  help       - This help screen", classes="help-item"),
            Label("\n[b]Quick Actions (Read-only):[/b]", classes="subtitle"),
            Label("  Show active session", classes="help-item"),
            Label("  List sessions", classes="help-item"),
            Label("  Show active phase", classes="help-item"),
            Label("  List phases", classes="help-item"),
            Label("  Show active build target", classes="help-item"),
            Label("\n[b]Status:[/b]", classes="subtitle"),
            Label("  All status information comes from UI Facade", classes="help-item"),
            Label("  No CLI subprocess calls are made", classes="help-item"),
            classes="main-container"
        )
        
        yield Footer()
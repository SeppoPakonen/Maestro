"""
Table formatter for session list visualization.
"""
from typing import List
from rich.console import Console
from rich.table import Table
from ..work_session import WorkSession


class SessionTableFormatter:
    """Format session list as table."""

    def __init__(self):
        self.console = Console()

    def format_table(self, sessions: List[WorkSession], columns: List[str] = None) -> str:
        """
        Format sessions as table.

        Args:
            sessions: List of sessions to display
            columns: Column names to include (default: all standard columns)

        Returns:
            Formatted table string
        """
        if columns is None:
            columns = ["ID", "Type", "Status", "Created", "Entity"]

        table = Table(title="Work Sessions")
        
        # Add columns to the table
        for col in columns:
            if col == "Status":
                table.add_column(col, style="bold")
            elif col == "ID":
                table.add_column(col, style="cyan")
            elif col == "Type":
                table.add_column(col, style="magenta")
            elif col == "Created":
                table.add_column(col, style="blue")
            elif col == "Entity":
                table.add_column(col, style="yellow")
            else:
                table.add_column(col)

        # Add rows
        for session in sessions:
            row = []
            for col in columns:
                if col == "ID":
                    row.append(session.session_id[:12])  # Truncate ID
                elif col == "Type":
                    row.append(session.session_type)
                elif col == "Status":
                    status_emoji = {
                        "running": "🔄",
                        "paused": "⏸️",
                        "completed": "✅",
                        "failed": "❌",
                        "interrupted": "⏹️"
                    }.get(session.status, "?")
                    row.append(f"{status_emoji} {session.status}")
                elif col == "Created":
                    row.append(session.created.split(".")[0])  # Remove microseconds
                elif col == "Entity":
                    # Extract entity name or ID from related_entity
                    entity = session.related_entity.get("name") or session.related_entity.get("id") or session.related_entity.get("track_id") or session.related_entity.get("phase_id") or "-"
                    row.append(str(entity))
                else:
                    # For other columns, use attribute if available
                    if hasattr(session, col.lower()):
                        row.append(str(getattr(session, col.lower())))
                    else:
                        row.append("-")
            table.add_row(*row)

        # Capture table as string using rich's built-in export functionality
        import io
        from rich.text import Text

        # Create a text buffer to capture the table
        text_buffer = io.StringIO()

        # Use rich's console to render the table to text
        with self.console.capture() as capture:
            self.console.print(table)

        output = capture.get()
        return output

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text with ellipsis."""
        return text[:max_len-3] + "..." if len(text) > max_len else text
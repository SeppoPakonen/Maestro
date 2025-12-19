"""
Status Indicators for Maestro TUI

Provides emoji and progress bar utility functions for visual status indicators
"""
import locale
from typing import Optional
from textual.widgets import Label


def supports_emoji() -> bool:
    """Check if terminal supports emoji"""
    encoding = locale.getpreferredencoding()
    return encoding.lower() in ['utf-8', 'utf8']


def get_status_emoji(status: str) -> str:
    """Get emoji for status indicator"""
    status_emojis = {
        'done': '✅',
        'in_progress': '🚧',
        'planned': '📋',
        'proposed': '💡',
    }
    return status_emojis.get(status.lower(), '❓')


def get_status_indicator(status: str) -> str:
    """Get status indicator (emoji or text)"""
    if supports_emoji():
        return get_status_emoji(status)
    else:
        # Text fallback
        status_text = {
            'done': '[✓]',
            'in_progress': '[~]',
            'planned': '[ ]',
            'proposed': '[?]',
        }
        return status_text.get(status.lower(), '[?]')


def get_priority_style(priority: str) -> str:
    """Get style for priority indicator"""
    priority_styles = {
        'P0': 'bold red',
        'P1': 'yellow',
        'P2': 'default',
    }
    return priority_styles.get(priority, 'default')


def get_progress_bar(completion: int, width: int = 10) -> str:
    """Create a text-based progress bar"""
    filled = int(width * completion / 100)
    empty = width - filled
    bar = '█' * filled + '░' * empty

    # Color coding
    if completion < 30:
        color = 'red'
    elif completion < 70:
        color = 'yellow'
    else:
        color = 'green'

    return f"[{color}]{bar}[/] {completion}%"


def format_phase_with_status(phase_label: str, status: str, completion: Optional[int] = None) -> str:
    """Format phase with status emoji and optional progress bar"""
    emoji = get_status_indicator(status)
    result = f"{emoji} {phase_label}"
    
    if completion is not None:
        progress_bar = get_progress_bar(completion)
        result += f" {progress_bar}"
    
    return result


def format_task_with_priority(task_label: str, priority: str) -> str:
    """Format task with priority styling"""
    style = get_priority_style(priority)
    return f"[{style}]{task_label}[/]"
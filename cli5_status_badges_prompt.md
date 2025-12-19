# CLI5 Status Badges and Emoji Support

## Context

The TUI terminology has been updated and markdown backend is integrated. Now we need to add visual status indicators using emojis and colors to match the CLI/markdown display.

## Task: Add Status Badges and Visual Indicators

According to the CLI5 phase document (docs/phases/cli5.md), we need:

### Emoji Status Indicators
- ✅ for "done" status
- 🚧 for "in_progress" status
- 📋 for "planned" status
- 💡 for "proposed" status

### Completion Progress Bars
- Show completion percentage for phases
- Visual progress bar for phases with tasks
- Color coding:
  - Red < 30%
  - Yellow 30-70%
  - Green > 70%
- Show overall track completion

### Priority Indicators
- Show P0 tasks in red/bold
- Show P1 tasks in yellow
- Show P2 tasks in normal text
- Allow filtering by priority

## Implementation Steps

### Step 1: Update Phase/Task Display to Show Emojis

In both TUI implementations (maestro/tui and maestro/tui_mc2), update the phase/task list displays to show status emojis.

**Files to update:**
- `maestro/tui/screens/phases.py` - Phase tree display
- `maestro/tui/panes/phases.py` - Phase pane display
- `maestro/tui_mc2/panes/phases.py` - MC2 phase pane display

**Implementation:**
```python
def get_status_emoji(status: str) -> str:
    """Get emoji for status indicator"""
    status_emojis = {
        'done': '✅',
        'in_progress': '🚧',
        'planned': '📋',
        'proposed': '💡',
    }
    return status_emojis.get(status.lower(), '❓')

def format_phase_with_status(phase: PhaseInfo) -> str:
    """Format phase with status emoji"""
    emoji = get_status_emoji(phase.status)
    return f"{emoji} {phase.label}"
```

### Step 2: Add Completion Progress Bars

Add progress indicators for phases that show completion percentage.

**Implementation:**
```python
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
```

### Step 3: Add Priority Indicators

Update task displays to show priority with color coding.

**Files to update:**
- `maestro/tui/screens/tasks.py` - Task screen
- `maestro/tui/panes/tasks.py` - Task pane
- `maestro/tui_mc2/panes/tasks.py` - MC2 task pane

**Implementation:**
```python
def get_priority_style(priority: str) -> str:
    """Get style for priority indicator"""
    priority_styles = {
        'P0': 'bold red',
        'P1': 'yellow',
        'P2': 'default',
    }
    return priority_styles.get(priority, 'default')

def format_task_with_priority(task: TaskInfo) -> str:
    """Format task with priority styling"""
    style = get_priority_style(task.priority)
    return f"[{style}]{task.label}[/]"
```

### Step 4: Handle Terminals Without Emoji Support

Add fallback for terminals that don't support emoji.

**Implementation:**
```python
import sys
import locale

def supports_emoji() -> bool:
    """Check if terminal supports emoji"""
    encoding = locale.getpreferredencoding()
    return encoding.lower() in ['utf-8', 'utf8']

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
```

### Step 5: Update Help Text

Update help panels to explain the new visual indicators.

**Files to update:**
- `maestro/tui/widgets/help_panel.py`
- `maestro/tui/onboarding.py`

## Testing Checklist

1. Test emoji display in different terminals
2. Test progress bar colors
3. Test priority indicators
4. Test fallback for non-UTF8 terminals
5. Verify alignment and spacing
6. Test with long phase/task names
7. Test with different screen sizes

## Deliverables

1. Updated TUI files with status badges and emoji support
2. Progress bar implementation
3. Priority indicators
4. Terminal compatibility handling
5. Summary document (cli5_status_badges_summary.md)

## Example Output

Before:
```
Phase: CLI1 Markdown Data Backend
Status: done
Completion: 100%
```

After:
```
✅ CLI1: Markdown Data Backend [████████████] 100%
```

With priority:
```
🚧 P0: Fix critical bug (in_progress)
📋 P1: Add new feature (planned)
📋 P2: Refactor code (planned)
```

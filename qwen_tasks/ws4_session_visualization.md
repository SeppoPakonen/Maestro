# Task: Implement WS4 - Session Visualization

## Context
You are implementing Phase WS4 (Session Visualization) of the Work & Session Framework track for the Maestro project. This adds comprehensive visualization and reporting capabilities for work sessions, allowing users to see session hierarchies, timelines, and detailed information.

## Dependencies
**REQUIRES**:
- WS1 (Session Infrastructure) must be completed
- WS2 (Breadcrumb System) must be completed
- WS3 (Work Command) should be completed (optional but helpful)

## Requirements from docs/todo.md

### WS4.1: Session List

Enhance `maestro session list` command to show work sessions:

```python
def handle_wsession_list(args):
    """
    List all work sessions with filtering and sorting.

    Display format:
    ID          Type        Status      Created              Entity
    --------------------------------------------------------------------------
    sess-1234   work_track  running     2025-12-20 10:30:00  repo-foundation
    sess-5678   work_phase  completed   2025-12-20 09:15:00  ws1
    sess-9012   discussion  paused      2025-12-20 11:45:00  -

    Filters:
    - --status: Filter by session status
    - --type: Filter by session type
    - --since: Show sessions created since date
    - --entity: Filter by related entity (track/phase/issue ID)

    Sort options:
    - --sort-by: created (default), modified, status, type
    - --reverse: Reverse sort order
    """
```

### WS4.2: Session Tree

Implement hierarchical tree visualization:

```python
def handle_wsession_tree(args):
    """
    Display session hierarchy as ASCII tree.

    Example output:
    📊 Work Sessions
    │
    ├─ ✅ sess-1234 (work_track: repo-foundation) [completed]
    │  ├─ ✅ sess-1235 (work_phase: rf1) [completed]
    │  │  └─ ⚠️ sess-1236 (fix: build error) [failed]
    │  └─ 🔄 sess-1237 (work_phase: rf2) [running]
    │     └─ 🔄 sess-1238 (analyze: hierarchy detection) [running]
    │
    └─ ⏸️ sess-5678 (discussion: AI planning) [paused]

    Features:
    - Tree structure with proper indentation
    - Emoji status indicators:
      - 🔄 running (green)
      - ⏸️ paused (yellow)
      - ❌ failed (red)
      - ✅ completed (blue)
      - ⏹️ interrupted (gray)
    - Session type and entity info
    - Color-coded by status (using colorama or rich)
    - Collapsible/expandable (future enhancement)

    Options:
    - --depth: Maximum depth to show (default: unlimited)
    - --filter-status: Only show sessions with status
    - --show-breadcrumbs: Include breadcrumb count
    """
```

Tree building algorithm:
```python
def build_session_tree() -> Dict[str, Any]:
    """
    Build hierarchical tree structure from sessions.

    Returns:
        {
          "roots": [sess1, sess2, ...],  # Top-level sessions
          "children": {
            "sess-1234": [sess-1235, sess-1236, ...],
            ...
          }
        }
    """
```

### WS4.3: Session Details

Enhance `maestro session show <id>` for work sessions:

```python
def handle_wsession_show(args):
    """
    Show comprehensive session details.

    Display:
    ═══════════════════════════════════════════════════════════════
    Session: sess-1234
    ═══════════════════════════════════════════════════════════════

    Basic Information:
      Type:           work_phase
      Status:         running
      Created:        2025-12-20 10:30:00
      Modified:       2025-12-20 11:45:00
      Duration:       1h 15m

    Related Entity:
      Track:          work-session
      Phase:          ws1
      Phase Name:     Session Infrastructure

    Parent Session:
      ID:             sess-1233
      Type:           work_track
      Status:         running

    Child Sessions: (2)
      - sess-1235 (analyze) - completed
      - sess-1236 (fix) - failed

    Breadcrumbs: (15 total)
      Latest:
        - 2025-12-20 11:45:00 - AI response (1,234 tokens)
        - 2025-12-20 11:40:00 - Tool: grep (success)
        - 2025-12-20 11:35:00 - File modified: maestro/work_session.py

    Statistics:
      Total breadcrumbs:     15
      Total tokens:          45,678 (input: 25,000, output: 20,678)
      Estimated cost:        $0.68
      Files modified:        5
      Tools called:          23

    Options:
      --show-all-breadcrumbs: Display all breadcrumbs (not just latest)
      --export-json: Export session data to JSON file
    """
```

## Visualization Components

### Tree Renderer

Create tree rendering utility in `maestro/visualization/tree.py`:

```python
class SessionTreeRenderer:
    """Render session hierarchy as ASCII tree."""

    def __init__(self, color: bool = True):
        self.color = color
        self.status_emoji = {
            "running": "🔄",
            "paused": "⏸️",
            "completed": "✅",
            "failed": "❌",
            "interrupted": "⏹️"
        }
        self.status_colors = {
            "running": "green",
            "paused": "yellow",
            "completed": "blue",
            "failed": "red",
            "interrupted": "gray"
        }

    def render(self, tree: Dict[str, Any], depth: int = 0) -> str:
        """Render tree structure."""
        pass

    def _render_node(self, session: WorkSession, is_last: bool, prefix: str) -> str:
        """Render single tree node."""
        pass
```

### List Formatter

Create list formatting utility in `maestro/visualization/table.py`:

```python
class SessionTableFormatter:
    """Format session list as table."""

    def format_table(self, sessions: List[WorkSession], columns: List[str]) -> str:
        """
        Format sessions as table.

        Args:
            sessions: List of sessions to display
            columns: Column names to include

        Returns:
            Formatted table string
        """
        pass

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text with ellipsis."""
        return text[:max_len-3] + "..." if len(text) > max_len else text
```

### Detail View

Create detail view formatter in `maestro/visualization/detail.py`:

```python
class SessionDetailFormatter:
    """Format detailed session information."""

    def format_details(
        self,
        session: WorkSession,
        include_breadcrumbs: bool = True,
        include_children: bool = True
    ) -> str:
        """Format comprehensive session details."""
        pass

    def format_breadcrumb_summary(self, breadcrumbs: List[Breadcrumb]) -> str:
        """Format breadcrumb summary."""
        pass

    def format_statistics(self, session: WorkSession) -> str:
        """Format session statistics."""
        pass
```

## Statistics Calculation

Create statistics module in `maestro/stats/session_stats.py`:

```python
@dataclass
class SessionStats:
    """Session statistics."""
    total_breadcrumbs: int
    total_tokens_input: int
    total_tokens_output: int
    estimated_cost: float
    files_modified: int
    tools_called: int
    duration_seconds: float
    success_rate: float  # % of successful operations

def calculate_session_stats(session: WorkSession) -> SessionStats:
    """
    Calculate comprehensive session statistics.

    Args:
        session: WorkSession to analyze

    Returns:
        SessionStats object with calculated metrics
    """
    # Load all breadcrumbs
    # Aggregate token counts
    # Calculate costs
    # Count file modifications and tool calls
    # Calculate duration
    pass

def calculate_tree_stats(root_session: WorkSession) -> SessionStats:
    """
    Calculate statistics for session and all children.

    Args:
        root_session: Root of session tree

    Returns:
        Aggregated SessionStats for entire tree
    """
    pass
```

## Export Functionality

Add export capabilities in `maestro/commands/work_session.py`:

```python
def export_session_json(session: WorkSession, output_path: str):
    """
    Export session to JSON file.

    Includes:
    - Session metadata
    - All breadcrumbs
    - Child sessions
    - Statistics
    """
    pass

def export_session_markdown(session: WorkSession, output_path: str):
    """
    Export session to Markdown file.

    Formatted report suitable for documentation.
    """
    pass
```

## CLI Enhancement

Update CLI commands in `maestro/main.py`:

```python
# Enhanced session list
wsession_list_parser.add_argument('--status', help='Filter by status')
wsession_list_parser.add_argument('--type', help='Filter by session type')
wsession_list_parser.add_argument('--since', help='Show sessions since date')
wsession_list_parser.add_argument('--entity', help='Filter by entity ID')
wsession_list_parser.add_argument('--sort-by', default='created',
                                 choices=['created', 'modified', 'status', 'type'])
wsession_list_parser.add_argument('--reverse', action='store_true')

# Session tree
wsession_tree_parser.add_argument('--depth', type=int, help='Max depth')
wsession_tree_parser.add_argument('--filter-status', help='Filter by status')
wsession_tree_parser.add_argument('--show-breadcrumbs', action='store_true')

# Session show
wsession_show_parser.add_argument('--show-all-breadcrumbs', action='store_true')
wsession_show_parser.add_argument('--export-json', help='Export to JSON file')
wsession_show_parser.add_argument('--export-md', help='Export to Markdown file')

# New: Session stats command
wsession_stats_parser = wsession_subparsers.add_parser(
    'stats',
    help='Show session statistics'
)
wsession_stats_parser.add_argument('session_id', nargs='?', help='Session ID (default: all)')
wsession_stats_parser.add_argument('--summary', action='store_true', help='Show summary only')
wsession_stats_parser.add_argument('--tree', action='store_true', help='Include children')
```

## Color Output

Use `rich` library for colored output (already in maestro dependencies):

```python
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel

console = Console()

def print_session_list_rich(sessions: List[WorkSession]):
    """Print session list using rich table."""
    table = Table(title="Work Sessions")

    table.add_column("ID", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Created", style="blue")
    table.add_column("Entity", style="yellow")

    for session in sessions:
        status_color = get_status_color(session.status)
        table.add_row(
            session.session_id,
            session.session_type,
            f"[{status_color}]{session.status}[/{status_color}]",
            session.created,
            get_entity_display(session.related_entity)
        )

    console.print(table)

def print_session_tree_rich(tree: Dict[str, Any]):
    """Print session tree using rich tree."""
    rich_tree = Tree("📊 Work Sessions")

    for root_session in tree["roots"]:
        _add_tree_node(rich_tree, root_session, tree["children"])

    console.print(rich_tree)
```

## Testing Requirements

Create test file `tests/test_session_visualization.py`:

1. Test session list with various filters
2. Test session list sorting
3. Test session tree building
4. Test session tree rendering (ASCII output)
5. Test session detail formatting
6. Test statistics calculation
7. Test export to JSON
8. Test export to Markdown
9. Test color output (mocked terminal)
10. Test truncation and formatting utilities

## File Structure to Create

```
maestro/
  visualization/
    __init__.py                # New module
    tree.py                    # New - tree rendering
    table.py                   # New - table formatting
    detail.py                  # New - detail view formatting
  stats/
    __init__.py                # New module
    session_stats.py           # New - statistics calculation
  commands/
    work_session.py            # Update - add export functions
tests/
  test_session_visualization.py  # New test file
qwen_tasks/
  ws4_session_visualization.md   # This file
```

## Implementation Steps

1. Create `maestro/visualization/` module with rendering classes
2. Create `maestro/stats/session_stats.py` with statistics calculation
3. Update `maestro/commands/work_session.py` with enhanced handlers
4. Update `maestro/main.py` to add new CLI options
5. Add export functionality
6. Create `tests/test_session_visualization.py`
7. Test all visualization commands

## Important Notes

1. **TERMINAL WIDTH** - Respect terminal width for tables and trees
2. **COLOR DETECTION** - Detect if terminal supports colors (use `rich.console`)
3. **LARGE SESSIONS** - Handle sessions with many breadcrumbs gracefully
4. **PAGINATION** - Consider adding pagination for large lists (future)
5. **PERFORMANCE** - Optimize tree building for deep hierarchies
6. **EXPORT FORMAT** - Ensure exported JSON is valid and readable
7. **UNICODE SUPPORT** - Use emoji only if terminal supports Unicode

## Edge Cases

Handle these scenarios:
- Empty session list
- Session with no breadcrumbs
- Orphaned sessions (parent deleted)
- Circular references (shouldn't happen but defensive)
- Very deep hierarchies (>10 levels)
- Very wide trees (>20 children)
- Sessions with missing metadata

## Expected Deliverables

1. Session list command with filtering and sorting
2. Session tree visualization with colors and emojis
3. Detailed session view with all information
4. Statistics calculation for sessions
5. Export to JSON and Markdown
6. Comprehensive test coverage

## Success Criteria

- [ ] Can list sessions with filters and sorting
- [ ] Can display session tree with proper hierarchy
- [ ] Can show detailed session information
- [ ] Statistics calculated correctly
- [ ] Can export session to JSON
- [ ] Can export session to Markdown
- [ ] Colors and emojis display correctly
- [ ] All tests pass
- [ ] Output is readable and informative

## Code Quality Standards

- Type hints on all function signatures
- Docstrings with Args, Returns, Raises sections
- Error handling for missing/corrupted data
- Logging for important operations
- Follow PEP 8 style guidelines
- Use rich library for enhanced terminal output

## Time Estimate

This is a MEDIUM complexity task. Estimated implementation time: 25-35 minutes.

# Task: Implement WS5 - Migrate CLI Discussions to Sessions

## Context
You are implementing Phase WS5 (Migrate CLI Discussions to Sessions) of the Work & Session Framework track for the Maestro project. This migrates the existing CLI discussion system (Phase CLI3) to use the new work session framework with breadcrumb tracking.

## Dependencies
**REQUIRES**:
- WS1 (Session Infrastructure) must be completed
- WS2 (Breadcrumb System) must be completed
- WS3 (Work Command) should be completed
- WS4 (Session Visualization) should be completed

## Background

### Existing CLI Discussion System (CLI3)

Current implementation in maestro allows discussions via:
- `maestro track <id> discuss` - Track planning discussion
- `maestro phase <id> discuss` - Phase-specific discussion
- `maestro discuss` - General discussion

Features:
- Editor mode ($EDITOR) with `# comment` syntax for user input
- Terminal stream mode (Enter to send, Ctrl+J for newline)
- `/done` command to finish and generate JSON actions
- `/quit` command to cancel
- JSON action processor for track/phase/task operations

## Requirements from docs/todo.md

### WS5.1: Update Discussion Commands

Migrate discussion commands to create work sessions:

```python
def handle_track_discuss(args):
    """
    Start discussion session for a track.

    Old behavior:
      - Enter discussion mode
      - AI responds
      - User types /done
      - Generate JSON actions

    New behavior:
      - Create WorkSession(type='discussion', related_entity={'track_id': ...})
      - Enter discussion mode
      - Create breadcrumbs for each interaction
      - User types /done
      - Complete session
      - Optionally generate JSON actions
    """

def handle_phase_discuss(args):
    """Similar to track discuss but for phases."""

def handle_discuss_general(args):
    """
    General discussion session (no specific entity).

    Creates WorkSession(type='discussion', related_entity={})
    """
```

### WS5.2: Backward Compatibility

Maintain existing CLI3 interface:

```python
class DiscussionSession:
    """
    Wrapper around WorkSession for discussion mode.

    Maintains CLI3 compatibility while using WS infrastructure.
    """

    def __init__(self, work_session: WorkSession, mode: str = "editor"):
        self.work_session = work_session
        self.mode = mode  # "editor" or "terminal"
        self.history = []  # Conversation history

    def run_editor_mode(self):
        """
        Run discussion in editor mode.

        Process:
        1. Open $EDITOR with template
        2. User writes prompt (non-comment lines)
        3. Save and close
        4. Parse prompt
        5. Call AI
        6. Create breadcrumb
        7. Show response
        8. Repeat until /done or /quit
        """

    def run_terminal_mode(self):
        """
        Run discussion in terminal mode.

        Process:
        1. Show prompt (>)
        2. User types (Enter to send, Ctrl+J for newline)
        3. Call AI
        4. Create breadcrumb
        5. Stream response
        6. Repeat until /done or /quit
        """

    def process_command(self, command: str) -> bool:
        """
        Process special commands.

        Commands:
        - /done: Complete session and generate actions
        - /quit: Cancel session
        - /save: Save current state
        - /history: Show conversation history

        Returns:
            True if session should continue, False if done
        """

    def generate_actions(self) -> List[Dict[str, Any]]:
        """
        Generate JSON actions from discussion.

        Uses AI to analyze conversation and propose actions.
        """
```

### WS5.3: Session-Aware Actions

Integrate JSON actions with sessions:

```python
def process_discussion_actions(
    session: WorkSession,
    actions: List[Dict[str, Any]]
) -> None:
    """
    Process JSON actions from discussion.

    Actions can be:
    - create_track
    - create_phase
    - update_track
    - update_phase
    - create_task
    - etc.

    Each action execution creates a breadcrumb.
    """

def create_breadcrumb_for_action(
    session: WorkSession,
    action: Dict[str, Any],
    result: Any,
    error: Optional[str] = None
) -> None:
    """
    Create breadcrumb for an action execution.

    Breadcrumb includes:
    - Action type and parameters
    - Result or error
    - Files modified (if any)
    """
```

## Discussion Template

Create discussion templates in `maestro/templates/`:

```python
# maestro/templates/discussion.py

TRACK_DISCUSSION_TEMPLATE = """
# Track Discussion: {track_name}

You are discussing the "{track_name}" track.

Current status:
- Track ID: {track_id}
- Status: {status}
- Completion: {completion}%
- Phases: {phase_count}

Enter your prompt below (lines starting with # are comments):
# Type /done when finished
# Type /quit to cancel

"""

PHASE_DISCUSSION_TEMPLATE = """
# Phase Discussion: {phase_name}

You are discussing phase "{phase_name}" in track "{track_name}".

Current status:
- Phase ID: {phase_id}
- Status: {status}
- Completion: {completion}%
- Tasks: {task_count}

Enter your prompt below:
# Type /done when finished
# Type /quit to cancel

"""

GENERAL_DISCUSSION_TEMPLATE = """
# General Discussion

General AI discussion session.

Enter your prompt below:
# Type /done when finished
# Type /quit to cancel

"""
```

## Session History

Implement session history viewing:

```python
def show_discussion_history(session: WorkSession) -> None:
    """
    Show discussion history from breadcrumbs.

    Display:
    ════════════════════════════════════════════════
    Discussion History: {session_id}
    ════════════════════════════════════════════════

    [2025-12-20 10:30:00] User:
      How should we implement the session infrastructure?

    [2025-12-20 10:30:15] AI (sonnet):
      Let me help you implement the session infrastructure.
      We should start by...

    [2025-12-20 10:35:00] User:
      What about breadcrumb storage?

    ...

    Total interactions: 5
    Total tokens: 12,345
    Estimated cost: $0.18
    """
```

## CLI Integration

Update discussion commands in `maestro/main.py`:

```python
# Track discuss
track_discuss_parser = track_subparsers.add_parser(
    'discuss',
    help='Start discussion session for track'
)
track_discuss_parser.add_argument('track_id', help='Track ID')
track_discuss_parser.add_argument('--mode', choices=['editor', 'terminal'],
                                 default='editor', help='Discussion mode')

# Phase discuss
phase_discuss_parser = phase_subparsers.add_parser(
    'discuss',
    help='Start discussion session for phase'
)
phase_discuss_parser.add_argument('phase_id', help='Phase ID')
phase_discuss_parser.add_argument('--mode', choices=['editor', 'terminal'],
                                 default='editor', help='Discussion mode')

# General discuss
discuss_parser = subparsers.add_parser(
    'discuss',
    help='Start general discussion session'
)
discuss_parser.add_argument('--mode', choices=['editor', 'terminal'],
                          default='editor', help='Discussion mode')
discuss_parser.add_argument('--resume', help='Resume previous discussion session')
```

## Resume Discussion

Allow resuming interrupted discussions:

```python
def resume_discussion(session_id: str) -> None:
    """
    Resume a previous discussion session.

    Process:
    1. Load session
    2. Load conversation history from breadcrumbs
    3. Show history
    4. Continue discussion
    5. Create new breadcrumbs
    """
```

## Migration Strategy

Migrate existing discussions (if any):

```python
def migrate_old_discussions() -> None:
    """
    Migrate old CLI3 discussions to work sessions.

    If old discussion data exists:
    1. Scan for old discussion files/data
    2. Convert to WorkSession format
    3. Create breadcrumbs from history
    4. Save in new format
    5. Archive old data
    """
```

## Testing Requirements

Create test file `tests/test_discussion_migration.py`:

1. Test track discuss command creates session
2. Test phase discuss command creates session
3. Test general discuss command creates session
4. Test editor mode discussion flow
5. Test terminal mode discussion flow
6. Test /done command generates actions
7. Test /quit command cancels session
8. Test breadcrumb creation during discussion
9. Test action processing with breadcrumbs
10. Test session history display
11. Test resume discussion
12. Test backward compatibility with CLI3

## File Structure to Create/Update

```
maestro/
  templates/
    __init__.py                # New module
    discussion.py              # New - discussion templates
  commands/
    discuss.py                 # New - discussion command handlers
  discussion.py                # Update or create - DiscussionSession class
tests/
  test_discussion_migration.py  # New test file
qwen_tasks/
  ws5_migrate_discussions.md     # This file
```

## Implementation Steps

1. Create `maestro/templates/discussion.py` with templates
2. Create or update `maestro/discussion.py` with DiscussionSession class
3. Create `maestro/commands/discuss.py` with command handlers
4. Update `maestro/main.py` to add/update discussion commands
5. Integrate breadcrumb creation in discussion flow
6. Add resume functionality
7. Create `tests/test_discussion_migration.py`
8. Test all discussion modes and commands

## Important Notes

1. **BACKWARD COMPATIBILITY** - Existing discussion workflow should still work
2. **EDITOR DETECTION** - Handle missing $EDITOR gracefully, fallback to terminal mode
3. **SIGNAL HANDLING** - Handle Ctrl+C and other interrupts properly
4. **STREAMING** - Maintain streaming AI responses in terminal mode
5. **COMMAND PARSING** - Properly parse /done, /quit commands
6. **BREADCRUMB TIMING** - Create breadcrumbs after AI response, not before
7. **SESSION LINKING** - Link discussion sessions to related entities

## Edge Cases

Handle these scenarios:
- User closes editor without saving
- Editor opens but user types nothing
- AI response fails mid-discussion
- Network error during streaming
- User sends empty message
- Very long discussion (100+ turns)
- Malformed JSON actions from AI

## Integration with Work Command

Discussion sessions should integrate with work command:

```python
# When working on a phase, user can pause and discuss
# This creates a child discussion session

def work_with_discussion(phase_id: str):
    """
    Work on phase with discussion support.

    Process:
    1. Create work session
    2. Start phase work
    3. If AI has questions, pause work
    4. Create child discussion session
    5. Resume work after discussion
    6. Link sessions properly
    """
```

## Expected Deliverables

1. DiscussionSession class with editor and terminal modes
2. Discussion templates for track/phase/general
3. Command handlers integrated with work sessions
4. Breadcrumb creation during discussions
5. Action processing with breadcrumb tracking
6. Session history viewing
7. Resume discussion functionality
8. Comprehensive test coverage
9. Backward compatibility maintained

## Success Criteria

- [ ] Can start track discuss and create session
- [ ] Can start phase discuss and create session
- [ ] Can start general discuss and create session
- [ ] Editor mode works as before
- [ ] Terminal mode works as before
- [ ] /done generates actions as before
- [ ] /quit cancels session
- [ ] Breadcrumbs created for each interaction
- [ ] Can view discussion history
- [ ] Can resume interrupted discussions
- [ ] All tests pass
- [ ] Existing CLI3 workflows still work

## Code Quality Standards

- Type hints on all function signatures
- Docstrings with Args, Returns, Raises sections
- Error handling for editor/terminal issues
- Graceful degradation if session creation fails
- Logging for important operations
- Follow PEP 8 style guidelines

## Deprecation Notes

Mark CLI3 as deprecated in documentation:
- Note in docs/todo.md that CLI3 is replaced by WS5
- Add deprecation warning in old discussion code
- Keep old code for backward compatibility
- Plan removal in future version

## Time Estimate

This is a MEDIUM-HIGH complexity task. Estimated implementation time: 30-40 minutes.

# Task: Implement WS1 - Session Infrastructure for Work & Session Framework

## Context
You are implementing Phase WS1 (Session Infrastructure) of the Work & Session Framework track for the Maestro project. This is a NEW session system distinct from the existing `maestro/session_model.py` which is used for the old planning system. The Work & Session Framework creates a hierarchical AI pair programming system with session tracking and breadcrumb management.

## Existing Code Analysis

### Current Session Model (maestro/session_model.py)
The existing session model is used for task planning and subtasks. It has:
- `Session` class with subtasks and plan nodes
- `PlanNode` for branching support
- `Subtask` for individual task items
- File location: `.maestro/sessions/`

**DO NOT MODIFY** the existing session_model.py. The WS1 session system is SEPARATE.

### Command Structure (maestro/main.py)
Commands are defined using argparse with subparsers:
- Main parser in `main()` function around line 3733
- Subparsers for each command group (session, plan, track, phase, etc.)
- Command handlers typically call functions that process arguments
- Look for patterns like `track_parser = subparsers.add_parser('track', ...)`

### Data Storage Pattern
Maestro uses markdown files in `docs/` for persistence:
- `docs/todo.md` - tracks and phases
- `docs/Settings.md` - configuration
- `docs/RepoRules.md` - repository rules
- Look at existing parsers in the codebase for reference

## Requirements from docs/todo.md

### WS1.1: Session Data Model

Create a new session data model in `maestro/work_session.py` with the following structure:

```python
@dataclass
class WorkSession:
    """Session for AI work interactions with hierarchical tracking."""
    session_id: str  # UUID or timestamp-based ID
    session_type: str  # work_track, work_phase, work_issue, discussion, analyze, fix
    parent_session_id: Optional[str]  # Link to parent if this is a sub-worker
    status: str  # running, paused, completed, interrupted, failed
    created: str  # ISO 8601 timestamp
    modified: str  # ISO 8601 timestamp
    related_entity: Dict[str, Any]  # {track_id: ..., phase_id: ..., issue_id: ..., etc.}
    breadcrumbs_dir: str  # Path to breadcrumbs subdirectory
    metadata: Dict[str, Any]  # Additional flexible metadata
```

### WS1.2: Session Storage

Storage structure in `docs/sessions/`:
- Top-level sessions: `docs/sessions/<session-id>/`
- Each session directory contains:
  - `session.json` - session metadata (using WorkSession model)
  - `breadcrumbs/` - subdirectory for breadcrumb files (Phase WS2)
- Nested sessions (sub-workers): `docs/sessions/<parent-id>/<child-id>/`
- Directory nesting depth indicates session hierarchy

### WS1.3: Session Lifecycle

Implement session lifecycle management functions in `maestro/work_session.py`:

1. **create_session()**: Create new session
   - Generate unique session ID
   - Create session directory structure
   - Write initial session.json
   - Return WorkSession object

2. **load_session()**: Load existing session
   - Read session.json
   - Parse into WorkSession object
   - Handle missing/corrupted files gracefully

3. **save_session()**: Save session updates
   - Write WorkSession to session.json
   - Update modified timestamp
   - Atomic write (write to temp file, then rename)

4. **list_sessions()**: List all sessions
   - Scan docs/sessions/ directory
   - Return list of WorkSession objects
   - Option to filter by type/status
   - Option to include nested sessions

5. **get_session_hierarchy()**: Get parent-child session tree
   - Build tree structure from session IDs
   - Return hierarchical representation

6. **interrupt_session()**: Handle interruptions
   - Update status to 'interrupted'
   - Save current state
   - Log interruption reason

7. **resume_session()**: Resume interrupted session
   - Load interrupted session
   - Update status to 'running'
   - Return session context for continuation

8. **complete_session()**: Mark session as completed
   - Update status to 'completed'
   - Set completion timestamp
   - Optionally run cleanup

### WS1.4: Session Pausing (Interactive Mode) - STUB ONLY

For WS1.4, create STUB functions only (to be fully implemented later):

```python
def pause_session_for_user_input(session: WorkSession, question: str) -> None:
    """
    STUB: Pause session and request user input.
    TODO: Implement in future phase.
    """
    raise NotImplementedError("Session pausing not yet implemented")
```

Document in docstrings that this will:
- Allow AI to ask questions via JSON response
- Block execution waiting for user response
- Continue with user's answer in new context

## CLI Integration

Add basic CLI commands in `maestro/main.py`:

```python
# Work command (basic structure)
work_parser = subparsers.add_parser('work', help='AI work commands')
work_subparsers = work_parser.add_subparsers(dest='work_subcommand')

# Session command (for viewing/managing work sessions)
wsession_parser = subparsers.add_parser('session', help='Work session management')
wsession_subparsers = wsession_parser.add_subparsers(dest='wsession_subcommand')

# session list
wsession_list_parser = wsession_subparsers.add_parser('list', help='List all work sessions')
wsession_list_parser.add_argument('--type', help='Filter by session type')
wsession_list_parser.add_argument('--status', help='Filter by status')

# session show <id>
wsession_show_parser = wsession_subparsers.add_parser('show', help='Show session details')
wsession_show_parser.add_argument('session_id', help='Session ID to show')

# session tree
wsession_tree_parser = wsession_subparsers.add_parser('tree', help='Show session hierarchy tree')
```

Implement command handlers in `maestro/commands/work_session.py`:
- `handle_wsession_list()`
- `handle_wsession_show()`
- `handle_wsession_tree()`

## Testing Requirements

Create test file `tests/test_work_session.py`:

1. Test session creation and storage
2. Test session loading and saving
3. Test nested session creation (parent-child)
4. Test session listing and filtering
5. Test session lifecycle (create → running → completed)
6. Test interruption and resume
7. Test hierarchy building

## File Structure to Create

```
maestro/
  work_session.py              # New module - WorkSession model and functions
  commands/
    work_session.py            # New module - CLI command handlers
tests/
  test_work_session.py         # New test file
docs/
  sessions/                    # Directory (create if doesn't exist)
    .gitkeep                   # Keep empty directory in git
qwen_tasks/
  ws1_session_infrastructure.md  # This file
```

## Implementation Steps

1. Create `maestro/work_session.py` with WorkSession dataclass and lifecycle functions
2. Create `maestro/commands/work_session.py` with CLI handlers
3. Update `maestro/main.py` to add CLI argument parsers and connect handlers
4. Create `tests/test_work_session.py` with comprehensive tests
5. Create `docs/sessions/` directory with `.gitkeep`
6. Run tests to verify implementation

## Important Notes

1. **DO NOT** modify `maestro/session_model.py` - this is for the old system
2. **DO NOT** conflict with existing 'session' command - use different naming or merge carefully
3. **USE** consistent naming: "work session" vs "session" to differentiate
4. **FOLLOW** existing code style in maestro codebase
5. **USE** type hints and docstrings for all functions
6. **HANDLE** errors gracefully with try/except blocks
7. **VALIDATE** session IDs, paths, and data before operations
8. **USE** pathlib.Path for file operations
9. **ATOMIC** writes for session.json (write to temp, then rename)

## Expected Deliverables

1. Working WorkSession model with all required fields
2. All lifecycle management functions implemented and tested
3. CLI commands integrated into maestro
4. Comprehensive test coverage
5. Documentation in docstrings
6. No breaking changes to existing code

## Success Criteria

- [ ] Can create a new work session with unique ID
- [ ] Can save and load session from disk
- [ ] Can create nested sessions (parent-child hierarchy)
- [ ] Can list all sessions with filtering
- [ ] Can show session details including hierarchy
- [ ] Can mark session as completed/interrupted
- [ ] All tests pass
- [ ] CLI commands work correctly

## Code Quality Standards

- Type hints on all function signatures
- Docstrings with Args, Returns, Raises sections
- Error handling with specific exception types
- Logging for important operations (use Python logging module)
- Follow PEP 8 style guidelines
- Keep functions focused and under 50 lines when possible

## Time Estimate

This is a MEDIUM complexity task. Estimated implementation time: 20-30 minutes.

# Task: Implement WS2 - Breadcrumb System

## Context
You are implementing Phase WS2 (Breadcrumb System) of the Work & Session Framework track for the Maestro project. This builds on top of WS1 (Session Infrastructure) to add breadcrumb tracking - a way to record every AI interaction, tool call, file modification, and decision made during a session.

## Dependencies
**REQUIRES**: WS1 (Session Infrastructure) must be completed first.
- Uses `maestro/work_session.py` and the WorkSession model
- Uses session directories in `docs/sessions/<session-id>/`

## Requirements from docs/todo.md

### WS2.1: Breadcrumb Schema

Create breadcrumb data model in `maestro/breadcrumb.py`:

```python
@dataclass
class Breadcrumb:
    """Records a single interaction step in an AI work session."""
    # Auto-added by maestro (not AI):
    timestamp: str  # ISO 8601 timestamp, auto-added by system
    breadcrumb_id: str  # Unique ID for this breadcrumb

    # AI interaction data:
    prompt: str  # Input prompt text
    response: str  # AI response (can be JSON)
    tools_called: List[Dict[str, Any]]  # List of tool invocations with args and results
    files_modified: List[Dict[str, Any]]  # List of {path, diff, operation}

    # Context:
    parent_session_id: Optional[str]  # Reference if this is a sub-worker
    depth_level: int  # Directory depth in session tree (0 for top-level)

    # Metadata:
    model_used: str  # AI model name (sonnet, opus, haiku)
    token_count: Dict[str, int]  # {input: N, output: M}
    cost: Optional[float]  # Estimated cost in USD
    error: Optional[str]  # Error message if operation failed
```

### WS2.2: Breadcrumb Storage

Storage structure:
- Breadcrumbs stored in: `docs/sessions/<session-id>/breadcrumbs/<depth>/`
- One file per breadcrumb: `<timestamp>.json`
- Timestamp format: `YYYYMMDD_HHMMSS_microseconds.json`
- Timestamped by maestro system, NOT by AI
- Full AI dialog can be parsed into multiple breadcrumbs

Example directory structure:
```
docs/sessions/sess-12345/
  session.json
  breadcrumbs/
    0/
      20251220_143025_123456.json
      20251220_143127_789012.json
    1/  # Sub-worker breadcrumbs
      20251220_143200_345678.json
```

### WS2.3: Breadcrumb Writing

Implement breadcrumb creation and writing in `maestro/breadcrumb.py`:

1. **create_breadcrumb()**: Create new breadcrumb
   - Auto-generate timestamp (system time, not AI time)
   - Generate unique breadcrumb ID
   - Parse AI response for tool calls and file changes
   - Calculate token counts and costs
   - Return Breadcrumb object

2. **write_breadcrumb()**: Write breadcrumb to disk
   - Determine depth level from session hierarchy
   - Create `breadcrumbs/<depth>/` directory if needed
   - Generate filename from timestamp
   - Write JSON atomically (temp file + rename)
   - Return path to written file

3. **auto_breadcrumb_wrapper()**: Decorator for functions
   - Wrap function to automatically create breadcrumb
   - Capture function args, return value, exceptions
   - Write breadcrumb before returning
   - Use for AI interaction functions

4. **parse_ai_dialog()**: Parse AI conversation into breadcrumbs
   - Input: Full AI dialog with multiple turns
   - Output: List of Breadcrumb objects (one per turn)
   - Extract prompts, responses, tool calls

### WS2.4: Breadcrumb Reading

Implement breadcrumb reading in `maestro/breadcrumb.py`:

1. **load_breadcrumb()**: Load single breadcrumb from file
   - Read JSON file
   - Parse into Breadcrumb object
   - Handle corrupted files gracefully

2. **list_breadcrumbs()**: List all breadcrumbs for a session
   - Scan `breadcrumbs/` directory recursively
   - Return sorted list (by timestamp)
   - Option to filter by depth level
   - Option to filter by date range

3. **reconstruct_session_timeline()**: Build full session history
   - Load all breadcrumbs for a session
   - Sort chronologically
   - Include parent-child relationships
   - Return timeline structure

4. **get_breadcrumb_summary()**: Summarize breadcrumbs
   - Input: Session ID
   - Output: {total_breadcrumbs, total_tokens, total_cost, duration}
   - Aggregate statistics across all breadcrumbs

## Configuration

Add settings to `docs/Settings.md`:

```markdown
## Work Session Settings

breadcrumb_enabled: true
breadcrumb_auto_write: true
breadcrumb_include_tool_results: true
breadcrumb_max_response_length: 50000
breadcrumb_cost_tracking: true
```

Implement settings parser in `maestro/work_session.py`:
- `load_breadcrumb_settings()`: Read from Settings.md
- `is_breadcrumb_enabled()`: Check if breadcrumbs are enabled
- Default: enabled unless explicitly disabled

## CLI Integration

Add CLI commands in `maestro/main.py` for breadcrumb viewing:

```python
# session breadcrumbs <session-id>
wsession_breadcrumbs_parser = wsession_subparsers.add_parser(
    'breadcrumbs',
    help='Show breadcrumbs for a session'
)
wsession_breadcrumbs_parser.add_argument('session_id', help='Session ID')
wsession_breadcrumbs_parser.add_argument('--depth', type=int, help='Filter by depth level')
wsession_breadcrumbs_parser.add_argument('--limit', type=int, default=20, help='Max breadcrumbs to show')
wsession_breadcrumbs_parser.add_argument('--summary', action='store_true', help='Show summary only')

# session timeline <session-id>
wsession_timeline_parser = wsession_subparsers.add_parser(
    'timeline',
    help='Show full session timeline with breadcrumbs'
)
wsession_timeline_parser.add_argument('session_id', help='Session ID')
wsession_timeline_parser.add_argument('--include-children', action='store_true', help='Include child sessions')
```

Implement handlers in `maestro/commands/work_session.py`:
- `handle_wsession_breadcrumbs()`
- `handle_wsession_timeline()`

## Tool Call Capture

Implement tool call capturing in `maestro/breadcrumb.py`:

```python
def capture_tool_call(
    tool_name: str,
    tool_args: Dict[str, Any],
    tool_result: Any,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """
    Capture a single tool invocation for breadcrumb.
    Returns structured dict with tool call details.
    """
    return {
        "tool": tool_name,
        "args": tool_args,
        "result": serialize_result(tool_result),
        "error": error,
        "timestamp": datetime.now().isoformat()
    }
```

## File Modification Tracking

Implement file change tracking in `maestro/breadcrumb.py`:

```python
def track_file_modification(
    file_path: str,
    operation: str,  # "create", "modify", "delete"
    diff: Optional[str] = None
) -> Dict[str, Any]:
    """
    Track a file modification for breadcrumb.
    Returns structured dict with file change details.
    """
    return {
        "path": file_path,
        "operation": operation,
        "diff": diff,
        "timestamp": datetime.now().isoformat(),
        "size": get_file_size(file_path) if operation != "delete" else None
    }
```

## Testing Requirements

Create test file `tests/test_breadcrumb.py`:

1. Test breadcrumb creation with all fields
2. Test breadcrumb writing to correct depth directory
3. Test breadcrumb loading and parsing
4. Test breadcrumb listing and filtering
5. Test session timeline reconstruction
6. Test tool call capture
7. Test file modification tracking
8. Test settings parsing
9. Test auto-breadcrumb wrapper
10. Test AI dialog parsing into breadcrumbs

## File Structure to Create

```
maestro/
  breadcrumb.py                # New module - Breadcrumb model and functions
  commands/
    work_session.py            # Update - add breadcrumb handlers
tests/
  test_breadcrumb.py           # New test file
docs/
  sessions/
    .../breadcrumbs/           # Created automatically
qwen_tasks/
  ws2_breadcrumb_system.md     # This file
```

## Implementation Steps

1. Create `maestro/breadcrumb.py` with Breadcrumb dataclass and all functions
2. Update `maestro/commands/work_session.py` with breadcrumb CLI handlers
3. Update `maestro/main.py` to add breadcrumb CLI commands
4. Add breadcrumb settings to `docs/Settings.md`
5. Create `tests/test_breadcrumb.py` with comprehensive tests
6. Integrate breadcrumb writing into existing AI interaction points
7. Run tests to verify implementation

## Integration Points

Breadcrumbs should be automatically created when:
1. AI work commands are executed (work track, work phase, etc.)
2. AI discussions are initiated
3. AI fixes issues
4. Any AI interaction that modifies files or calls tools

Example integration in hypothetical AI interaction function:
```python
@auto_breadcrumb_wrapper
def run_ai_worker(session: WorkSession, prompt: str) -> str:
    # AI interaction happens here
    response = call_ai_model(prompt)
    return response
```

## Important Notes

1. **TIMESTAMP** must be generated by maestro system, NOT passed from AI
2. **ATOMIC WRITES** - always write to temp file then rename
3. **DEPTH LEVELS** - must correctly track session hierarchy depth
4. **GRACEFUL DEGRADATION** - if breadcrumbs disabled, functions should no-op
5. **PRIVACY** - do not store sensitive data (API keys, passwords) in breadcrumbs
6. **PERFORMANCE** - breadcrumb writing should not slow down AI interactions
7. **STORAGE** - consider rotation/cleanup for old breadcrumbs (future)

## Token Counting

Implement simple token estimation in `maestro/breadcrumb.py`:

```python
def estimate_tokens(text: str, model: str = "claude") -> int:
    """
    Estimate token count for text.
    Simple heuristic: ~4 chars per token for English.
    """
    return len(text) // 4

def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """
    Calculate estimated cost in USD.
    Use current pricing for Claude models.
    """
    # Pricing as of 2025 (approximate)
    pricing = {
        "sonnet": {"input": 0.003 / 1000, "output": 0.015 / 1000},
        "opus": {"input": 0.015 / 1000, "output": 0.075 / 1000},
        "haiku": {"input": 0.00025 / 1000, "output": 0.00125 / 1000},
    }
    rates = pricing.get(model.lower(), pricing["sonnet"])
    return (input_tokens * rates["input"]) + (output_tokens * rates["output"])
```

## Expected Deliverables

1. Working Breadcrumb model with all required fields
2. All breadcrumb I/O functions implemented and tested
3. CLI commands for viewing breadcrumbs and timelines
4. Automatic breadcrumb creation for AI interactions
5. Settings integration for enabling/disabling breadcrumbs
6. Tool call and file modification tracking
7. Comprehensive test coverage

## Success Criteria

- [ ] Can create breadcrumbs with auto-generated timestamps
- [ ] Can write breadcrumbs to correct depth directories
- [ ] Can load and list breadcrumbs for a session
- [ ] Can reconstruct full session timeline
- [ ] Can track tool calls and file modifications
- [ ] Can view breadcrumbs via CLI commands
- [ ] Settings control whether breadcrumbs are written
- [ ] All tests pass
- [ ] No performance impact on AI interactions

## Code Quality Standards

- Type hints on all function signatures
- Docstrings with Args, Returns, Raises sections
- Error handling with specific exception types
- Logging for important operations
- Follow PEP 8 style guidelines
- Async-friendly (no blocking I/O in main paths)

## Time Estimate

This is a MEDIUM-HIGH complexity task. Estimated implementation time: 25-35 minutes.

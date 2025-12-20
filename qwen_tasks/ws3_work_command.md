# Task: Implement WS3 - Work Command

## Context
You are implementing Phase WS3 (Work Command) of the Work & Session Framework track for the Maestro project. This implements the AI-powered work selection and execution system that allows the AI to autonomously select and work on tasks, tracks, phases, or issues.

## Dependencies
**REQUIRES**:
- WS1 (Session Infrastructure) must be completed
- WS2 (Breadcrumb System) must be completed
- Existing track/phase system in `docs/todo.md` and `docs/done.md`

## Requirements from docs/todo.md

### WS3.1: Work Selection Algorithm

Create AI-powered work selection in `maestro/commands/work.py`:

```python
def ai_select_work_items(
    items: List[Dict[str, Any]],
    context: Optional[str] = None,
    mode: str = "best"  # "best" or "top_n"
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Use AI to evaluate and rank work items (tracks/phases/issues).

    Args:
        items: List of work items with metadata
        context: Additional context for selection (user preferences, etc.)
        mode: "best" returns single best item, "top_n" returns top 3

    Returns:
        Selected item(s) with reasoning
    """
```

Selection criteria (provided to AI):
- Priority level
- Dependencies (blocked by other items?)
- Complexity (can AI handle it?)
- User preferences
- Recent activity
- Estimated impact

AI should return JSON:
```json
{
  "selected": [
    {
      "id": "ws1",
      "type": "phase",
      "name": "Session Infrastructure",
      "track": "work-session",
      "reason": "Foundational work needed before other phases can proceed",
      "confidence": 0.9,
      "estimated_difficulty": "medium"
    },
    ...
  ],
  "reasoning": "Full explanation of selection logic"
}
```

### WS3.2: Work Any

Implement `maestro work any` command:

```python
async def handle_work_any(args):
    """
    AI picks best work item and starts working on it automatically.

    Steps:
    1. Load all available work items (tracks, phases, issues)
    2. Use AI to select best item
    3. Create work session for selected item
    4. Execute work (call appropriate worker)
    5. Write breadcrumbs throughout
    6. Report progress
    7. Complete or pause with status update
    """
```

Flow:
1. Scan `docs/todo.md` for open tracks/phases
2. Scan `docs/issues/` for open issues
3. Call `ai_select_work_items()` to rank
4. Create WorkSession with type based on selected item
5. Execute appropriate worker:
   - Track → call track worker
   - Phase → call phase worker
   - Issue → call issue worker
6. Auto-create breadcrumbs during execution
7. Update track/phase status when complete
8. Print summary

### WS3.3: Work Any Pick

Implement `maestro work any pick` command:

```python
async def handle_work_any_pick(args):
    """
    AI shows top 3 work options, user selects one.

    Steps:
    1. Load all available work items
    2. Use AI to select top 3 options
    3. Display formatted list to user
    4. Prompt user to select (1, 2, or 3)
    5. Create session for selected item
    6. Execute work
    """
```

Display format:
```
Top 3 recommended work items:

1. [Phase] Session Infrastructure (work-session track)
   Reason: Foundational work needed before other phases
   Difficulty: Medium | Priority: High

2. [Issue] Build error in package scanner
   Reason: Blocking other development work
   Difficulty: Low | Priority: High

3. [Track] Observability
   Reason: Good parallelization opportunity
   Difficulty: High | Priority: Medium

Select option (1-3) or 'q' to quit:
```

### WS3.4: Work Track/Phase/Issue

Implement specific work commands:

```python
# maestro work track [<id>]
async def handle_work_track(args):
    """
    Work on a specific track or list tracks for selection.

    If <id> provided:
      - Load track from docs/todo.md
      - Create WorkSession with type='work_track'
      - Execute track worker

    If no <id>:
      - List all tracks
      - Use AI to sort by recommendation
      - User selects from list
      - Execute selected track
    """

# maestro work phase [<id>]
async def handle_work_phase(args):
    """Similar to handle_work_track but for phases."""

# maestro work issue [<id>]
async def handle_work_issue(args):
    """Similar to handle_work_track but for issues."""
```

### WS3.5: Work Integration with Issues

Implement 4-phase workflow for issues:

```python
async def work_on_issue(issue_id: str, parent_session: Optional[WorkSession] = None):
    """
    Execute full issue workflow with sub-sessions.

    Workflow:
    1. Analyze phase:
       - Create child session (type='analyze')
       - Run issue analysis
       - Write breadcrumbs
       - Return analysis result

    2. Decide phase:
       - Create child session (type='decide')
       - AI decides whether to fix issue
       - Write breadcrumbs
       - Return decision

    3. Fix phase (if decision = yes):
       - Create child session (type='fix')
       - Execute fix
       - Write breadcrumbs
       - Return fix result

    4. Verify phase:
       - Create child session (type='verify')
       - Run tests/validation
       - Write breadcrumbs
       - Complete parent session

    All child sessions linked via parent_session_id.
    """
```

## Worker Implementation

Create worker modules for each work type in `maestro/workers/`:

```python
# maestro/workers/track_worker.py
async def execute_track_work(track_id: str, session: WorkSession) -> WorkResult:
    """Execute work on a track."""

# maestro/workers/phase_worker.py
async def execute_phase_work(phase_id: str, session: WorkSession) -> WorkResult:
    """Execute work on a phase."""

# maestro/workers/issue_worker.py
async def execute_issue_work(issue_id: str, session: WorkSession) -> WorkResult:
    """Execute work on an issue using 4-phase workflow."""
```

## CLI Integration

Add work commands in `maestro/main.py`:

```python
# Work command group
work_parser = subparsers.add_parser('work', help='AI-powered work commands')
work_subparsers = work_parser.add_subparsers(dest='work_subcommand')

# work any
work_any_parser = work_subparsers.add_parser(
    'any',
    help='AI selects and works on best task'
)
work_any_parser.add_argument(
    'pick',
    nargs='?',
    help='Show top 3 options and let user pick'
)

# work track [<id>]
work_track_parser = work_subparsers.add_parser(
    'track',
    help='Work on a specific track'
)
work_track_parser.add_argument('id', nargs='?', help='Track ID')

# work phase [<id>]
work_phase_parser = work_subparsers.add_parser(
    'phase',
    help='Work on a specific phase'
)
work_phase_parser.add_argument('id', nargs='?', help='Phase ID')

# work issue [<id>]
work_issue_parser = work_subparsers.add_parser(
    'issue',
    help='Work on a specific issue'
)
work_issue_parser.add_argument('id', nargs='?', help='Issue ID')
```

## Data Loading

Create data loading utilities in `maestro/commands/work.py`:

```python
def load_available_work() -> Dict[str, List[Dict[str, Any]]]:
    """
    Load all available work items from various sources.

    Returns:
        {
          "tracks": [...],
          "phases": [...],
          "issues": [...]
        }
    """
    # Parse docs/todo.md for tracks and phases
    # Scan docs/issues/ for open issues
    # Return structured data

def parse_todo_md() -> Dict[str, Any]:
    """Parse docs/todo.md for tracks and phases."""

def load_issues() -> List[Dict[str, Any]]:
    """Load all issues from docs/issues/."""
```

## Progress Reporting

Implement progress reporting in workers:

```python
class WorkProgress:
    """Track and report work progress during execution."""

    def __init__(self, session: WorkSession):
        self.session = session
        self.steps_completed = 0
        self.total_steps = 0
        self.current_step = None

    def start_step(self, step_name: str):
        """Mark step as started."""
        self.current_step = step_name
        print(f"Starting: {step_name}")

    def complete_step(self):
        """Mark current step as completed."""
        self.steps_completed += 1
        print(f"Completed: {self.current_step} ({self.steps_completed}/{self.total_steps})")

    def report_error(self, error: str):
        """Report error during step."""
        print(f"Error in {self.current_step}: {error}")
```

## Testing Requirements

Create test file `tests/test_work_command.py`:

1. Test work item loading from todo.md and issues
2. Test AI work selection algorithm
3. Test work any command (mock AI calls)
4. Test work any pick command
5. Test work track/phase/issue commands
6. Test session creation for each work type
7. Test breadcrumb creation during work
8. Test issue 4-phase workflow
9. Test child session linking
10. Test progress reporting

## File Structure to Create

```
maestro/
  commands/
    work.py                    # New module - work command handlers
  workers/
    __init__.py                # New module
    track_worker.py            # New module - track worker
    phase_worker.py            # New module - phase worker
    issue_worker.py            # New module - issue worker
tests/
  test_work_command.py         # New test file
qwen_tasks/
  ws3_work_command.md          # This file
```

## Implementation Steps

1. Create `maestro/commands/work.py` with:
   - Data loading functions
   - AI selection algorithm
   - Command handlers
2. Create worker modules in `maestro/workers/`
3. Update `maestro/main.py` to add work command parsers
4. Create `tests/test_work_command.py`
5. Integrate with WS1 sessions and WS2 breadcrumbs
6. Test all work commands end-to-end

## AI Integration

Use existing AI engines from `maestro/engines.py`:

```python
from maestro.engines import call_ai, EngineError

def ai_select_work_items(...):
    prompt = f"""
    Select the best work item(s) from the following:

    {json.dumps(items, indent=2)}

    Consider:
    - Priority and urgency
    - Dependencies
    - Complexity vs available time
    - Recent context: {context}

    Return JSON with selected item(s) and reasoning.
    """

    try:
        response = call_ai(prompt, model="sonnet")
        return json.loads(response)
    except EngineError as e:
        # Fallback to simple heuristic
        return simple_priority_sort(items)
```

## Important Notes

1. **ASYNC** - Use async/await for all worker functions
2. **SESSION CREATION** - Always create WorkSession before starting work
3. **BREADCRUMBS** - Auto-create breadcrumbs for all AI interactions
4. **ERROR HANDLING** - Graceful degradation if AI selection fails
5. **ATOMICITY** - Work operations should be atomic where possible
6. **STATUS UPDATES** - Update track/phase status in docs/todo.md when completed
7. **PARENT-CHILD** - Properly link child sessions to parent

## Expected Deliverables

1. Working work command with all subcommands
2. AI-powered work selection algorithm
3. Worker implementations for track/phase/issue
4. Session and breadcrumb integration
5. Progress reporting during work execution
6. Comprehensive test coverage

## Success Criteria

- [ ] Can run `maestro work any` and AI selects best work
- [ ] Can run `maestro work any pick` and user selects from top 3
- [ ] Can run `maestro work track <id>` and work on specific track
- [ ] Can run `maestro work phase <id>` and work on specific phase
- [ ] Can run `maestro work issue <id>` with 4-phase workflow
- [ ] Sessions created with correct type and parent links
- [ ] Breadcrumbs written throughout execution
- [ ] Progress reported to user
- [ ] All tests pass

## Code Quality Standards

- Type hints on all function signatures
- Docstrings with Args, Returns, Raises sections
- Async/await for I/O operations
- Error handling with specific exception types
- Logging for important operations
- Follow PEP 8 style guidelines

## Time Estimate

This is a HIGH complexity task. Estimated implementation time: 35-45 minutes.

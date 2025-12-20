# Task: Implement Missing Work Command Handlers

## Context

The Maestro project has a work command system in `maestro/commands/work.py`. The main CLI (`maestro/main.py`) imports and tries to use two functions that don't exist yet:
- `handle_work_analyze`
- `handle_work_fix`

These functions need to be implemented to complete the WS3 phase (Work Command).

## Current State

### Existing Functions in maestro/commands/work.py:
- `async def handle_work_any(args)` - AI picks best work and starts automatically
- `async def handle_work_any_pick(args)` - AI shows top 3, user picks
- `async def handle_work_track(args)` - Work on specific track or list tracks
- `async def handle_work_phase(args)` - Work on specific phase or list phases
- `async def handle_work_issue(args)` - Work on specific issue or list issues
- `def handle_work_discuss(args)` - Start discussion session

### Import Statement in maestro/main.py (line 6376-6384):
```python
from .commands.work import (
    handle_work_track,
    handle_work_phase,
    handle_work_issue,
    handle_work_discuss,
    handle_work_analyze,
    handle_work_fix,
    handle_work_any,
    handle_work_any_pick
)
```

### Command Line Argument Parsers (maestro/main.py):

```python
# work analyze - Analyze the current state
work_analyze_parser = work_subparsers.add_parser('analyze', aliases=['a'], help='Analyze the current state')
work_analyze_parser.add_argument('target', nargs='?', help='Target to analyze')

# work fix - Fix an issue
work_fix_parser = work_subparsers.add_parser('fix', aliases=['f'], help='Fix an issue')
work_fix_parser.add_argument('target', help='Target to fix')
work_fix_parser.add_argument('--issue', help='Issue ID to fix')
```

### Handlers Called in main.py (lines 6419-6422):
```python
elif args.work_subcommand == 'analyze' or args.work_subcommand == 'a':
    handle_work_analyze(args)
elif args.work_subcommand == 'fix' or args.work_subcommand == 'f':
    handle_work_fix(args)
```

## Task Requirements

### 1. Implement `handle_work_analyze(args)`

This function should:
- Accept an `args` parameter with `args.target` (optional)
- If `target` is provided:
  - Analyze the specified target (could be a file, directory, phase, track, or issue)
  - Create a work session with type='analyze'
  - Use AI to analyze the target and provide insights
  - Write breadcrumbs during the analysis
  - Report findings
- If `target` is not provided:
  - Analyze the current repository state
  - Show overall health, pending tasks, blocking issues
  - Provide actionable recommendations

### 2. Implement `handle_work_fix(args)`

This function should:
- Accept an `args` parameter with `args.target` and optional `args.issue`
- Create a work session with type='fix'
- If `--issue` is provided:
  - Link the fix session to the specified issue ID
  - Follow the 4-phase workflow for issues (analyze → decide → fix → verify)
  - Create sub-sessions for each phase
  - Link sessions in parent-child relationship
- If only `target` is provided without `--issue`:
  - Attempt to fix the specified target directly
  - Use AI to understand the problem and generate a fix
  - Write breadcrumbs throughout
  - Report success or failure

### Implementation Guidelines

1. **Follow Existing Patterns**: Study the existing async handlers like `handle_work_issue` and `handle_work_track` for patterns
2. **Use WorkSession**: Create sessions using `create_session()` from `..work_session`
3. **Write Breadcrumbs**: Use `_run_ai_interaction_with_breadcrumb()` for AI calls
4. **Error Handling**: Wrap worker calls in try-except blocks with ImportError handling (like existing handlers)
5. **Async Pattern**: Both functions should likely be async (to match other handlers)
6. **AI Integration**: Use the AI engine for analysis and fix generation

### For the 4-Phase Workflow (WS3.5 requirement for handle_work_fix):

When working on an issue, create sub-sessions:
1. **Analyze Phase**: Create `analyze_issue` session, understand the problem
2. **Decide Phase**: Create `decide_fix` session, determine solution approach
3. **Fix Phase**: Create `fix_issue` session, implement the fix
4. **Verify Phase**: Create `verify_fix` session, test and validate

Link sessions hierarchically so `maestro session tree` shows the workflow.

## Output Requirements

Create a unified diff file that:
1. Adds the two new functions to `maestro/commands/work.py`
2. Follows the existing code style and patterns
3. Includes proper imports (if any new ones needed)
4. Includes docstrings explaining what each function does
5. Handles errors gracefully

## Files to Read and Understand

1. `/common/active/sblo/Dev/Maestro/maestro/commands/work.py` - Existing work handlers
2. `/common/active/sblo/Dev/Maestro/maestro/work_session.py` - Session management
3. `/common/active/sblo/Dev/Maestro/maestro/breadcrumb.py` - Breadcrumb system
4. `/common/active/sblo/Dev/Maestro/maestro/engines.py` - AI engine interface
5. `/common/active/sblo/Dev/Maestro/maestro/main.py` - CLI argument parsing (lines 3879-3920, 6374-6433)

## Success Criteria

- [ ] Both functions are implemented and follow existing patterns
- [ ] Functions can be imported without errors
- [ ] Argument parsing works correctly
- [ ] Sessions and breadcrumbs are created properly
- [ ] Error handling is robust
- [ ] Code style matches existing codebase
- [ ] 4-phase workflow is implemented for handle_work_fix when --issue is provided

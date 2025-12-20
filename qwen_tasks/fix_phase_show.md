# Task: Fix Phase Show Command to Display Sub-tasks

## Context
The user wants to see phase sub-tasks (like WS1.1, WS1.2, WS1.3) when running:
- `m phase ws1 show`
- `m t work-session details` (currently doesn't exist)

Currently, `m phase ws1 show` doesn't work due to argument parsing issues, and sub-tasks from `docs/todo.md` aren't being displayed.

## Issues to Fix

### Issue 1: Phase Command Argument Parsing
The command `m phase ws1 show` fails because the parser treats `ws1` as a subcommand choice rather than a phase_id.

**Current behavior:**
```
$ m phase ws1 show
error: argument phase_subcommand: invalid choice: 'ws1'
```

**Expected behavior:**
```
$ m phase ws1 show
Shows phase WS1 details with all sub-tasks
```

### Issue 2: Sub-tasks Not Parsed from todo.md
When phases are defined in `docs/todo.md` like this:

```markdown
### Phase WS1: Session Infrastructure

- [x] **WS1.1: Session Data Model** ✅
  - WorkSession dataclass with all required fields ✅

- [x] **WS1.2: Session Storage** ✅
  - Store in `docs/sessions/<session-id>/` ✅

- [x] **WS1.3: Session Lifecycle** ✅
  - create_session() - Create new session ✅
```

The parser in `parse_todo_md()` doesn't extract these sub-tasks into the `tasks` field.

### Issue 3: Track Details Command Missing
The command `m t work-session details` should show the full track with all phases and their sub-tasks, but this subcommand doesn't exist.

## Implementation Requirements

### 1. Fix Argument Parsing in main.py

Find the phase parser definition in `maestro/main.py` (around line 3800+) and fix it so that `phase_id` can be passed without being interpreted as a subcommand.

**Hint**: The parser should use `nargs='?'` for optional phase_id after the subcommand.

### 2. Enhance todo.md Parser

File: `maestro/commands/phase.py` or wherever `parse_todo_md()` is defined.

Update the parser to:
1. Extract sub-tasks from the list items under each phase section
2. Parse the checkbox status `[x]` vs `[ ]`
3. Extract the sub-task ID (e.g., `WS1.1`) and description
4. Store in `phase['tasks']` list with structure:
   ```python
   {
       'task_id': 'WS1.1',
       'name': 'Session Data Model',
       'status': 'done',  # or 'todo'
       'description': ['WorkSession dataclass...', ...]
   }
   ```

### 3. Enhance show_phase Display

File: `maestro/commands/phase.py` (function `show_phase()` around line 128)

Update the display to show sub-tasks with their completion status:

```
Tasks (3):
  ✅ [WS1.1] Session Data Model
      - WorkSession dataclass with all required fields

  ✅ [WS1.2] Session Storage
      - Store in docs/sessions/<session-id>/
      - session.json - metadata

  ✅ [WS1.3] Session Lifecycle
      - create_session() - Create new session
      - load_session() - Load existing session
      ...
```

Use emojis: ✅ for done, ⬜ for todo

### 4. Add Track Details Command

File: `maestro/commands/track.py`

Add a `details` subcommand to the track parser that shows the full track with all phases and their sub-tasks expanded.

**Command**: `m t work-session details` or `m track work-session details`

**Output format:**
```
================================================================================
TRACK: Work & Session Framework
================================================================================

ID:          work-session
Priority:    3
Status:      in_progress
Completion:  40%

Description:
  This track implements the AI pair programming system...

================================================================================
PHASES
================================================================================

✅ Phase WS1: Session Infrastructure [DONE]
   Completion: 100%

   Tasks:
     ✅ [WS1.1] Session Data Model
         - WorkSession dataclass with all required fields

     ✅ [WS1.2] Session Storage
         - Store in docs/sessions/<session-id>/

     ✅ [WS1.3] Session Lifecycle
         - create_session(), load_session(), save_session()...

✅ Phase WS2: Breadcrumb System [DONE]
   Completion: 100%

   Tasks:
     ✅ [WS2.1] Breadcrumb Schema
     ✅ [WS2.2] Breadcrumb Storage
     ...

📋 Phase WS3: Work Command [PLANNED]
   Completion: 0%

   Tasks:
     ⬜ [WS3.1] Work Selection Algorithm
     ⬜ [WS3.2] Work Any
     ...
```

## Testing

After implementation, verify:

```bash
# Test phase show
m phase ws1 show        # Should work and show sub-tasks
m phase ws2 show        # Should work and show sub-tasks
m phase ws3 show        # Should work even though not complete

# Test track details
m t work-session details    # Should show all phases with sub-tasks
m track work-session details    # Same as above
```

## Files to Modify

1. `maestro/main.py` - Fix phase argument parser
2. `maestro/commands/phase.py` - Enhance parser and display
3. `maestro/commands/track.py` - Add details subcommand
4. Possibly create/update parser utilities for todo.md parsing

## Important Notes

- **DO NOT** break existing functionality
- Ensure backward compatibility with current commands
- Follow existing code style and patterns
- Use type hints where appropriate
- Keep display formatting clean and readable
- Test with the actual `docs/todo.md` file in this project

## Time Estimate

This is a LOW-MEDIUM complexity task. Estimated time: 15-20 minutes.

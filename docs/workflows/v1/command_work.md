# Command Workflow: `maestro work`

## Purpose

The `maestro work` command is Maestro's primary work execution interface. It enables the Operator (human or AI runner) to select and execute work items (tracks, phases, issues, tasks) systematically.

This document describes the **current implementation** based on `maestro/commands/work.py` and `maestro/commands/work_session.py`.

---

## Actor Model Note

**Important**: The `maestro work` command does NOT treat AI as a separate actor. The Operator invokes `maestro work ...` via CLI, and Maestro may use an AI engine internally during execution, but this is an implementation detail, not a workflow participant.

- Operator = human OR AI runner
- Both use the same CLI syntax
- Engine (AI or rule-based) is invoked BY Maestro CLI, not separately

---

## Command Syntax

```bash
maestro work [subcommand] [arguments]
```

### Subcommands

| Subcommand | Purpose | Syntax |
|------------|---------|--------|
| `any` | AI selects and works on best available item | `maestro work any` |
| `any pick` | AI shows top 3 options, user selects | `maestro work any pick` |
| `track <id>` | Work on specific track (or list if no ID) | `maestro work track [<track_id>]` |
| `phase <id>` | Work on specific phase (or list if no ID) | `maestro work phase [<phase_id>]` |
| `issue <id>` | Work on specific issue (or list if no ID) | `maestro work issue [<issue_id>]` |
| `task <id>` | Work on specific task (or list if no ID) | `maestro work task [<task_id>] [--simulate]` |
| `discuss <entity_type> <entity_id>` | Start discussion for entity | `maestro work discuss <track\|phase\|task> <id>` |
| `analyze <target>` | Analyze target before work | `maestro work analyze [<target>] [--simulate]` |
| `fix <target>` | Fix target or issue | `maestro work fix <target> [--issue <id>] [--simulate]` |

---

## Implementation Details

### State & Invariants

**Data Sources**:
- `active tasks in JSON`: Tracks and phases with status "todo"
- `issue data*.md`: Open issues (not marked as "Resolved" or "Closed")
- `docs/maestro/phases/*.md`: Tasks within phases (parsed from phase markdown files)

**Work Session Creation**:
- All work commands create a `WorkSession` object
- Session tracks: session_type, related_entity, parent_session_id, metadata
- Sessions are stored in `docs/sessions/<session_id>/`

**Breadcrumb Tracking**:
- If breadcrumb mode is enabled, all AI interactions create breadcrumbs
- Breadcrumbs stored in `docs/sessions/<session_id>/breadcrumbs/`
- Tracks: prompt, response, tools_called, files_modified, token_count, cost

---

## Decision Points & Flow

### 1. `maestro work any`

**Purpose**: AI automatically selects the best work item and starts working on it.

**Flow**:
1. Load available work items from `active tasks in JSON` and `issue data`
2. Call `ai_select_work_items(all_items, mode="best")`
   - Uses configured AI engine (e.g., claude_planner)
   - Engine returns JSON with selected item and reasoning
   - **Fallback**: If engine fails, use `simple_priority_sort()` (phases > tracks > issues, then by ID)
3. Display selected item and reason to Operator
4. Create WorkSession with type `work_{item_type}` (e.g., `work_phase`)
5. Dispatch to appropriate worker:
   - Track → `execute_track_work()`
   - Phase → `execute_phase_work()`
   - Issue → `execute_issue_work()`
6. If workers not available (ImportError), create simple AI interaction with breadcrumb
7. Display result

**Hard Stops**:
- No work items available
- Engine error (falls back to heuristic)
- Worker import error (falls back to simple interaction)

**Recoverable**:
- Engine selection fails → fallback to simple heuristic
- Worker not available → simple AI interaction

---

### 2. `maestro work any pick`

**Purpose**: AI shows top 3 recommended work items; Operator selects one.

**Flow**:
1. Load available work items
2. Call `ai_select_work_items(all_items, mode="top_n")`
   - Engine returns top 3 items with reasoning
   - **Fallback**: If engine fails, use `simple_priority_sort()` for top 3
3. Display formatted list:
   ```
   1. [PHASE] Session Infrastructure (work-session track)
      Reason: Foundational work needed
      Difficulty: Medium | Priority: High

   2. [TRACK] AI CLI Integration
      Reason: High-impact feature
      Difficulty: High | Priority: Medium

   3. [ISSUE] Fix build errors in core module
      Reason: Blocking other work
      Difficulty: Low | Priority: Critical
   ```
4. Prompt Operator: "Select option (1-3) or 'q' to quit:"
5. Operator selects option (1, 2, 3, or q)
6. Create WorkSession for selected item
7. Dispatch to appropriate worker (same as `maestro work any`)

**Hard Stops**:
- No work items available
- Invalid selection (retry prompt)

**Recoverable**:
- Engine fails → fallback to heuristic
- Operator quits (choice 'q')

---

### 3. `maestro work track <id>`

**Purpose**: Work on a specific track (or list tracks if no ID provided).

**Flow (with ID)**:
1. Load available work items from `active tasks in JSON`
2. Find matching track by `track_id`
3. If not found: Display error "Track with ID '<id>' not found or already completed"
4. Create WorkSession with type `work_track`, related_entity=`{"track_id": id}`
5. Dispatch to `execute_track_work(track_id, session)`
6. If worker not available: Simple AI interaction with prompt "Work on track '<id>'"

**Flow (no ID - list mode)**:
1. Load available tracks from `active tasks in JSON`
2. If no tracks: Display "No tracks available!"
3. Display numbered list of tracks
4. If only 1 track: Auto-select
5. If multiple: Use AI to recommend order (call `ai_select_work_items(tracks, mode="top_n")`)
6. Display recommended order
7. Prompt Operator to select track number
8. Create WorkSession and dispatch to worker

**Hard Stops**:
- Track ID not found
- Worker import error (falls back to simple interaction)

---

### 4. `maestro work phase <id>`

**Purpose**: Work on a specific phase (or list phases if no ID provided).

**Flow**: Similar to `maestro work track`, but:
- Loads phases from `active tasks in JSON`
- Filters by `phase_id`
- Displays track association: `"phase_id: name (in track_name track)"`
- Creates WorkSession with type `work_phase`
- Dispatches to `execute_phase_work(phase_id, session)`

---

### 5. `maestro work issue <id>`

**Purpose**: Work on a specific issue (or list issues if no ID provided).

**Flow**: Similar to track/phase, but:
- Loads issues from `issue data*.md`
- Checks if issue is open (not "Status: Resolved" or "Status: Closed")
- Creates WorkSession with type `work_issue`
- Dispatches to `execute_issue_work(issue_id, session)`

---

### 6. `maestro work task <id>`

**Purpose**: Work on a specific task (or list tasks if no ID provided).

**Flow (with ID)**:
1. Call `find_task_context(task_id)` to locate task in phase files
2. If not found: Display "Task with ID '<id>' not found"
3. Load phase and task context
4. Build task queue: `build_task_queue(phase)`
5. Create WorkSession with type `work_task`, metadata includes task_queue and current_task_id
6. Write sync state to track task progress
7. Build task prompt using `build_task_prompt(task_id, task, phase, session_id)`
8. If `--simulate` flag: Print prompt and exit (no execution)
9. Otherwise: Run AI interaction with breadcrumb tracking
10. Display AI response

**Flow (no ID - list mode)**:
1. Load all tasks from `docs/maestro/phases/*.md` (via `_load_task_entries()`)
2. Filter out tasks marked as done
3. Display numbered list with phase association
4. Prompt Operator to select task number
5. Execute same flow as with ID

**Hard Stops**:
- Task ID not found
- Engine error (no fallback for task execution)

**Special Features**:
- `--simulate` flag: Print the prompt without executing
- Sync state tracking for task queues

---

### 7. `maestro work analyze <target>`

**Purpose**: Analyze a target (file, directory, track, phase, issue, or current repository) before working on it.

**Flow (with target)**:
1. Check if target is a file path:
   - If file: Read content (first 4000 chars), prompt engine to analyze
   - If directory: List contents, prompt engine to analyze directory structure
2. If not a file/directory, check if it's a work item ID (track/phase/issue)
3. If work item found: Prompt engine to analyze the work item
4. If not found: Generic analysis of target
5. Create WorkSession with type `analyze`
6. Run AI interaction with breadcrumb tracking
7. Display analysis results
8. Complete session

**Flow (no target - analyze repository)**:
1. Load available work items (tracks, phases, issues)
2. Count items, check git repository, get recent commits
3. Prompt engine to analyze overall repository health, priority items, blocking issues, recommendations
4. Display comprehensive analysis

**Simulation Mode** (`--simulate` flag):
- Does not create session or write breadcrumbs
- Calls engine with simulation prompt (summarize what would be done)
- Displays simulation output

**Hard Stops**:
- Engine error

**Recoverable**:
- Target not found → Generic analysis

---

### 8. `maestro work fix <target> [--issue <id>]`

**Purpose**: Fix a target or resolve an issue using a 4-phase workflow.

**Flow (with --issue)**:
1. Implement **4-phase workflow**:
   - **Phase 1: Analyze Issue**
     - Create sub-session `analyze_issue` (parent: main fix session)
     - Load issue details from `issue data`
     - Prompt engine: "Analyze issue, what is root cause?"
     - Complete sub-session
   - **Phase 2: Decide on Fix Approach**
     - Create sub-session `decide_fix`
     - Prompt engine: "Based on analysis, what is best approach?"
     - Complete sub-session
   - **Phase 3: Implement Fix**
     - Create sub-session `fix_issue`
     - Prompt engine: "Implement the fix, generate code/file changes"
     - Complete sub-session
   - **Phase 4: Verify Fix**
     - Create sub-session `verify_fix`
     - Prompt engine: "Verify fix, what tests should run? Side effects?"
     - Complete sub-session
2. All sub-sessions are linked via `parent_session_id`
3. Display session IDs for tracking

**Flow (without --issue - direct fix)**:
1. Check if target is a file or directory
2. Read content or list contents
3. Prompt engine: "Fix this target, what should be fixed?"
4. Run AI interaction with breadcrumb
5. Display fix results

**Simulation Mode** (`--simulate` flag):
- No sessions created, no breadcrumbs
- Calls engine with simulation prompt for each phase
- Displays what would be done without actual execution

**Hard Stops**:
- Engine error during any phase

---

### 9. `maestro work discuss <entity_type> <entity_id>`

**Purpose**: Start a discussion session for a work item (track, phase, or task).

**Flow**:
1. Map entity_type to handler:
   - `track` → `handle_track_discuss(entity_id, args)`
   - `phase` → `handle_phase_discuss(entity_id, args)`
   - `task` → `handle_task_discuss(entity_id, args)`
2. Handlers invoke discussion commands from `maestro.commands.discuss`

**Hard Stops**:
- Unsupported entity_type
- Discussion handler error

---

## Extension Points

### Worker Modules

The `maestro work` command dispatches to worker modules for actual execution:

- `maestro.workers.track_worker.execute_track_work()`
- `maestro.workers.phase_worker.execute_phase_work()`
- `maestro.workers.issue_worker.execute_issue_work()`

**Current Status**: These workers may not be fully implemented. When ImportError occurs, the command falls back to simple AI interaction.

**Extension Point**: Implement these workers to provide specialized execution logic for each work item type.

### Engine Selection

The command uses `get_engine(model_name)` to obtain AI engines:
- Default engine for selection: `claude_planner`
- Can be configured via settings

**Extension Point**: Add new engines or configure different engines for different work types.

### Breadcrumb Settings

Breadcrumbs can be enabled/disabled via `is_breadcrumb_enabled()` and configured via `load_breadcrumb_settings()`.

**Extension Point**: Configure breadcrumb behavior (token estimation, cost tracking, depth levels).

---

## State Transitions

### Work Item Status

- **todo** → Selected for work → WorkSession created → Work executed → **completed** (manually via `maestro task complete` or similar)
- Work items remain in "todo" state during `maestro work` execution
- Completion requires explicit command

### Session Lifecycle

1. **Created**: `create_session(session_type, related_entity, metadata)`
2. **In Progress**: Work is being executed
3. **Completed**: `complete_session(session)` marks session as done
4. **Failed**: `session.status = "failed"` on error

### Breadcrumb Accumulation

- Each AI interaction appends a breadcrumb to `docs/sessions/<session_id>/breadcrumbs/<timestamp>.json`
- Breadcrumbs are immutable once written
- Can be retrieved and analyzed later via `list_breadcrumbs(session_id)`

---

## Validation & Gating Rules

### Work Item Validation

1. **Status filter**: Only items with status "todo" (tracks/phases) or "open" (issues) are available
2. **ID uniqueness**: Each work item must have unique ID
3. **Dependency blocking**: (Future) Tasks with unsatisfied dependencies are not selectable

### Engine Output Validation

1. **JSON validation**: For selection/recommendation responses, output must parse as valid JSON
2. **Fallback on failure**: If JSON parsing fails, fall back to simple heuristic
3. **Schema validation**: (Future) Validate engine responses against expected schema

### Session Validation

1. **Session directory creation**: Validates that session directory can be created
2. **Breadcrumb writes**: Validates breadcrumb JSON structure before writing

---

## Failure Modes & Recovery

### Hard Stops (Execution Halts)

1. **No work items available**: Exit with message "No work items available!"
2. **Invalid target/ID**: Exit with message "Item not found"
3. **Engine critical error**: Exit with error message (no fallback for critical operations)

### Recoverable Failures (Graceful Degradation)

1. **Engine selection fails**: Fall back to `simple_priority_sort()` heuristic
2. **Worker import fails**: Fall back to simple AI interaction with breadcrumb
3. **Engine timeout**: Retry or fall back to manual mode

---

## Test Mapping

### Unit Tests

1. **Work Item Loading**:
   - `test_load_available_work_from_todo_md()`
   - `test_load_issues_from_docs_issues()`
   - `test_load_task_entries_from_phases()`
   - `test_work_status_normalization()`

2. **AI Selection**:
   - `test_ai_select_work_items_best_mode()`
   - `test_ai_select_work_items_top_n_mode()`
   - `test_ai_select_fallback_to_heuristic()`
   - `test_simple_priority_sort()`

3. **Session Management**:
   - `test_create_work_session()`
   - `test_session_parent_child_linking()`
   - `test_breadcrumb_creation()`
   - `test_breadcrumb_token_estimation()`

4. **Command Routing**:
   - `test_work_any_dispatches_to_worker()`
   - `test_work_track_with_id()`
   - `test_work_phase_list_mode()`
   - `test_work_task_simulate_mode()`

5. **4-Phase Fix Workflow**:
   - `test_fix_with_issue_creates_four_sub_sessions()`
   - `test_fix_sub_sessions_linked_to_parent()`
   - `test_fix_phases_execute_in_order()`

### Integration Tests

1. **Fixture Scenarios**:
   - `fixture_work_items_mixed`: todo.md with tracks, phases; issues/ with open issues
   - `fixture_work_session_hierarchy`: Parent session with multiple child sessions
   - `fixture_fix_workflow`: Issue requiring 4-phase fix

2. **End-to-End Tests**:
   - `test_work_any_full_flow()`: Load items → AI select → dispatch → complete
   - `test_work_any_pick_user_selection()`: Display top 3 → user selects → execute
   - `test_work_task_with_queue()`: Execute task with task queue tracking
   - `test_work_fix_issue_full_4_phase()`: Complete fix workflow with all phases

---

## Example Sessions

### Example 1: AI Auto-Selection

```bash
$ maestro work any
Loading available work items...
Found 12 work items. Asking AI to select the best one...
AI selected: Session Infrastructure (phase)
Reason: Foundational work needed before other phases can proceed

Working on selected item: Session Infrastructure
Work completed for phase ws1
```

### Example 2: Top 3 Selection

```bash
$ maestro work any pick
Loading available work items...
Found 12 work items. Asking AI to select top 3 options...

Top 3 recommended work items:

1. [PHASE] Session Infrastructure (work-session track)
   Reason: Foundational work needed before other phases
   Difficulty: Medium | Priority: High

2. [ISSUE] Fix undefined symbol in core.rs
   Reason: Blocking compilation, must be fixed first
   Difficulty: Low | Priority: Critical

3. [TRACK] AI CLI Integration
   Reason: High-impact feature for end users
   Difficulty: High | Priority: Medium

Select option (1-3) or 'q' to quit: 2

Working on selected item: Fix undefined symbol in core.rs
Work completed for issue ISS-042
```

### Example 3: Task Execution

```bash
$ maestro work task T-ws1-001
Task: Implement WorkSession dataclass
Phase: Session Infrastructure
Track: work-session

[AI executes task, creates files, writes code]

AI response: Created WorkSession dataclass in maestro/work_session.py with fields:
- session_id (UUID)
- session_type (str)
- parent_session_id (optional)
- status (enum)
- created/modified timestamps
- related_entity (dict)
- breadcrumbs_dir (Path)
```

### Example 4: Simulation Mode

```bash
$ maestro work analyze --simulate
SIMULATION MODE - No actions will be executed

[SIMULATE] Would create analysis session
  - Session type: analyze
  - Target: current repository

[SIMULATE] AI Work Plan:
Would analyze repository health and identify top 3 priority items
- Check git status and recent commits
- Scan active tasks in JSON for pending phases
- Evaluate issue complexity and dependencies
- Recommend next actionable item
- Estimate time/effort required

[SIMULATE] No session created, no breadcrumbs written
SIMULATION COMPLETE - No actual work performed
```

---

## Related Documentation

- [Scenario WF-01](scenario_01_existing_repo_single_main.md): Existing repo bootstrap (uses work loop)
- [Scenario WF-02](scenario_02_new_project_manual_plan.md): Greenfield manual planning (uses `maestro work task`)
- `maestro/commands/work.py`: Source code
- `maestro/commands/work_session.py`: Session management source
- `maestro/work_session.py`: WorkSession dataclass
- `maestro/breadcrumb.py`: Breadcrumb tracking

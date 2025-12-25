---
id: WF-02
title: New Project from Empty Directory (Manual Track/Phase/Task Planning)
tags: [bootstrap, greenfield, manual-planning, work-loop, track-phase-task]
entry_conditions: |
  - Empty directory OR new directory for project
  - No git repository yet (will be initialized)
  - Operator has clear plan/requirements (e.g., assignment, spec document)
  - Maestro not initialized
exit_conditions: |
  - Maestro initialized in new repository
  - Git repository created
  - Tracks, phases, and tasks manually created via CLI
  - Work loop operational (maestro work task <id>)
  - Initial work completed or in progress
artifacts_created: |
  - .git/ (git repository)
  - docs/maestro/tracks/*.json (manually defined tracks)
  - docs/maestro/phases/*.json (manually defined phases)
  - docs/maestro/tasks/*.json (manually defined tasks)
  - docs/maestro/index.json (manual plan structure)
  - active tasks in JSON (task list)
  - completed tasks in JSON (completed work)
  - Source files created during work execution
failure_semantics: |
  - Hard stop: Invalid track/phase/task JSON structure
  - Hard stop: Circular task dependencies detected
  - Hard stop: Engine validation fails for work output
  - Recoverable: Work task produces unexpected output (operator adjusts)
related_commands: |
  - maestro init
  - maestro track add <id> --name "<name>"
  - maestro phase add <phase_id> --track <track_id> --name "<name>"
  - maestro task add <task_id> --phase <phase_id> --name "<name>" --description "<desc>"
  - maestro work task <task_id>
  - maestro task complete <task_id>
follow_on_scenarios: [WF-05]
---

# Scenario WF-02: New Project from Empty Directory (Manual Planning)

## Actor Model Note

**Important**: In Maestro, there is no separate "AI" workflow participant. The **Operator** (either a human user or an AI runner) interacts with Maestro via the same CLI command interface. Commands like `maestro work task` may internally invoke an AI engine, but this is an execution mode of the Maestro CLI itself, not a separate actor. Therefore:
- Operator = human OR AI runner
- Both use identical CLI commands
- Behavior is the same at the command boundary

## Overview

This scenario documents the **greenfield project bootstrap process** when an Operator starts a **new project from scratch** with:
- An empty directory (or new directory to be created)
- A clear plan or requirements (e.g., university assignment with strict intermediate steps)
- Manual creation of tracks, phases, and tasks via CLI
- Work execution using `maestro work task`

The workflow covers:
1. Directory and git initialization
2. Maestro initialization
3. Manual track creation
4. Manual phase creation (linked to tracks)
5. Manual task creation (linked to phases)
6. Work loop using `maestro work task <id>`
7. Task completion and progression

---

## Phase 0: Entry & Preconditions

### Preconditions

Before entering this scenario, the following must be true:

- **Empty or new directory**: The operator is starting fresh (no existing codebase)
- **Clear plan/requirements**: The operator has defined requirements (assignment spec, project requirements doc, etc.)
- **Manual planning preferred**: The operator wants explicit control over task breakdown
- **No git repository yet**: Will be initialized during the scenario
- **Maestro not initialized**: No `docs/` structure exists yet

### Operator Intent

The Operator (human or AI runner) wants to:
- Start a new project with explicit planning upfront
- Break down work into tracks → phases → tasks manually
- Use Maestro to execute and track work systematically
- Have full control over work structure before execution begins

---

## Phase 1: Directory & Git Initialization

### Step 1.1: Create project directory (if needed)

```bash
mkdir my-new-project
cd my-new-project
```

### Step 1.2: Initialize git repository

**Command**: `git init`

**Purpose**: Create version control for the new project.

**Outputs**:
- `.git/` directory created
- Initial empty repository

**State Change**:
- Directory state: `empty` → `git repository`

---

## Phase 2: Maestro Initialization

### Command: `maestro init`

**Purpose**: Bootstrap Maestro's directory structure and initial state files in the new repository.

**Inputs**:
- Current directory (now a git repo)

**Outputs**:
- Creates directory structure:
  ```
  docs/
    tracks/
    phases/
    tasks/
    issues/
    plan.json       (empty scaffold: {"tracks": [], "version": "1.0"})
    todo.md         (empty: "# TODO\n")
    done.md         (empty: "# DONE\n")
  ```

**Failure Modes**:
- **Idempotent**: Already initialized (warning, no-op)

**State Change**:
- Project state: `git repository` → `maestro initialized`

---

## Phase 3: Manual Track Creation

### Purpose

Define high-level work tracks that organize phases. For example:
- "Project Setup" track
- "Core Features" track
- "Testing & Validation" track

### Command: `maestro track add <track_id> --name "<track_name>"`

**Example**:
```bash
maestro track add setup --name "Project Setup"
maestro track add core --name "Core Features Implementation"
maestro track add validation --name "Testing & Validation"
```

**Purpose**: Create named tracks to organize phases.

**Inputs**:
- `track_id`: Unique identifier (e.g., `setup`, `core`)
- `--name`: Human-readable track name

**Outputs**:
- Creates `docs/maestro/tracks/<track_id>.json`:
  ```json
  {
    "track_id": "setup",
    "name": "Project Setup",
    "description": "",
    "status": "todo",
    "phases": []
  }
  ```
- Updates `docs/maestro/index.json` to reference the track

**Validation**:
- `track_id` must be unique
- Must be valid JSON structure

**Failure Modes**:
- **Hard stop**: Duplicate `track_id`
- **Hard stop**: Invalid JSON structure

**State Change**:
- Track list updated in `docs/maestro/index.json`

---

## Phase 4: Manual Phase Creation

### Purpose

Define phases within each track. Phases represent logical groupings of related tasks.

### Command: `maestro phase add <phase_id> --track <track_id> --name "<phase_name>"`

**Example**:
```bash
maestro phase add setup-env --track setup --name "Environment Setup"
maestro phase add core-logic --track core --name "Implement Core Logic"
maestro phase add unit-tests --track validation --name "Write Unit Tests"
```

**Purpose**: Create phases linked to tracks.

**Inputs**:
- `phase_id`: Unique identifier
- `--track`: Parent track ID
- `--name`: Human-readable phase name

**Outputs**:
- Creates `docs/maestro/phases/<phase_id>.json`:
  ```json
  {
    "phase_id": "setup-env",
    "track_id": "setup",
    "name": "Environment Setup",
    "description": "",
    "status": "todo",
    "tasks": []
  }
  ```
- Updates `docs/maestro/tracks/<track_id>.json` to reference the phase

**Validation**:
- `phase_id` must be unique
- `track_id` must exist
- Must be valid JSON structure

**Failure Modes**:
- **Hard stop**: Duplicate `phase_id`
- **Hard stop**: Referenced `track_id` does not exist
- **Hard stop**: Invalid JSON structure

**State Change**:
- Phase added to track's phase list

---

## Phase 5: Manual Task Creation

### Purpose

Define specific tasks within phases. Tasks are the atomic units of work that can be executed.

### Command: `maestro task add <task_id> --phase <phase_id> --name "<task_name>" --description "<task_desc>"`

**Example**:
```bash
maestro task add T001 --phase setup-env --name "Create project structure" \
  --description "Set up src/, tests/, docs/ directories"

maestro task add T002 --phase setup-env --name "Initialize dependencies" \
  --description "Create Cargo.toml with required crates"

maestro task add T003 --phase core-logic --name "Implement parse_input function" \
  --description "Parse command-line arguments and validate"
```

**Purpose**: Create tasks linked to phases with clear descriptions of work to be done.

**Inputs**:
- `task_id`: Unique identifier
- `--phase`: Parent phase ID
- `--name`: Human-readable task name
- `--description`: Detailed description of the task

**Outputs**:
- Creates `docs/maestro/tasks/<task_id>.json`:
  ```json
  {
    "task_id": "T001",
    "phase_id": "setup-env",
    "track_id": "setup",
    "name": "Create project structure",
    "description": "Set up src/, tests/, docs/ directories",
    "status": "todo",
    "dependencies": []
  }
  ```
- Updates `docs/maestro/phases/<phase_id>.json` to reference the task
- Updates `active tasks in JSON` with new task

**Validation**:
- `task_id` must be unique
- `phase_id` must exist
- Must be valid JSON structure

**Failure Modes**:
- **Hard stop**: Duplicate `task_id`
- **Hard stop**: Referenced `phase_id` does not exist
- **Hard stop**: Invalid JSON structure

**State Change**:
- Task added to phase's task list
- Task added to `active tasks in JSON`

**Optional**: Add task dependencies if tasks have ordering requirements:
```bash
maestro task add T004 --phase core-logic --name "Add error handling" \
  --depends-on T003
```

---

## Phase 6: Work Loop (Execute Tasks)

### Purpose

Execute tasks systematically using `maestro work task`. The Operator selects tasks from `active tasks in JSON` and uses Maestro to work on them.

### Step 6.1: Select next task

**Command**: `maestro task next`

**Purpose**: Display the next available task (no unsatisfied dependencies).

**Outputs**:
- Displays task ID, name, description
- Shows dependencies (if any)

**Example Output**:
```
Next available task:
  ID: T001
  Name: Create project structure
  Description: Set up src/, tests/, docs/ directories
  Phase: setup-env (Project Setup track)
  Dependencies: None
```

### Step 6.2: Execute work on task

**Command**: `maestro work task <task_id>`

**Example**:
```bash
maestro work task T001
```

**Purpose**: Execute the task using the configured engine (AI or manual). The Operator may work manually or invoke engine assistance.

**Inputs**:
- `task_id`: Task to work on
- Task context (from `docs/maestro/tasks/<task_id>.json` and `docs/maestro/phases/<phase_id>.json`)

**Engine Invocation** (if using AI mode):
- Maestro CLI loads task context
- Invokes engine with task prompt:
  ```
  Task: Create project structure
  Description: Set up src/, tests/, docs/ directories

  Current directory state: <lists files>

  Please execute this task. Create necessary directories and files.
  ```

**Engine Output** (example):
- Creates `src/` directory
- Creates `tests/` directory
- Creates `docs/` directory
- Creates initial files (e.g., `src/main.rs`, `tests/.gitkeep`)

**Validation**:
- If engine is used, output must conform to expected structure
- File operations are validated (paths exist, no conflicts)

**Failure Modes**:
- **Hard stop**: Engine returns invalid operations
- **Recoverable**: Operator adjusts engine output or works manually

**State Change**:
- Task status remains `todo` until explicitly completed
- Work artifacts created in repository

### Step 6.3: Complete task

**Command**: `maestro task complete <task_id>`

**Example**:
```bash
maestro task complete T001
```

**Purpose**: Mark task as completed and move it from `todo.md` to `done.md`.

**Inputs**:
- `task_id`: Task to mark complete

**Outputs**:
- Updates `docs/maestro/tasks/<task_id>.json`: `status: "todo"` → `status: "completed"`
- Moves task from `active tasks in JSON` to `completed tasks in JSON`
- Updates phase completion percentage

**Validation**:
- Task must exist and be in `todo` status
- Task work should be verifiable (files exist, tests pass, etc.)

**Failure Modes**:
- **Hard stop**: Task not found
- **Hard stop**: Task already completed

**State Change**:
- Task status: `todo` → `completed`
- Task moved from todo.md to done.md (Mandatory Task Lifecycle Rule)

---

## Phase 7: Iteration & Progression

### Loop Until All Tasks Complete

The Operator repeats Phase 6 (work loop) for each task:

1. `maestro task next` - Find next available task
2. `maestro work task <task_id>` - Execute the task
3. `maestro task complete <task_id>` - Mark as complete
4. Repeat until `active tasks in JSON` is empty

### Decision Gates

**GATE: "More tasks in todo.md?"**
- **Yes** → Loop back to Phase 6.1
- **No** → All tasks completed; project work finished

**GATE: "Task execution successful?"**
- **Yes** → Complete task (Phase 6.3)
- **No** → Retry, adjust, or break task into subtasks

---

## Exit Points

### EXIT_WF_02_SUCCESS

**Success Criteria Met**:
- Maestro initialized in new repository
- Tracks, phases, tasks created manually
- All tasks completed and moved to `completed tasks in JSON`
- Work artifacts created (source files, tests, documentation)

**Artifacts Created**:
- `.git/` repository
- `docs/maestro/tracks/*.json` (all manually defined tracks)
- `docs/maestro/phases/*.json` (all manually defined phases)
- `docs/maestro/tasks/*.json` (all tasks with status `completed`)
- `active tasks in JSON` (empty)
- `completed tasks in JSON` (all completed tasks)
- Source code and project files

**Follow-On Scenarios**:
- **WF-05**: Feature Request Workflow (add new features to completed project)

### EXIT_WF_02_PARTIAL

**Partial Completion**:
- Maestro initialized
- Tracks, phases, tasks created
- Some tasks completed, others remaining in `active tasks in JSON`

**Operator may continue later** by resuming work loop at Phase 6.

---

## Command Contracts Summary

| Command | Purpose | Inputs | Outputs | Hard Stops |
|---------|---------|--------|---------|-----------|
| `git init` | Initialize repository | Current directory | `.git/` directory | None |
| `maestro init` | Bootstrap Maestro | Current directory | `docs/` structure | Already initialized (idempotent) |
| `maestro track add <id> --name "<name>"` | Create track | Track ID, name | `docs/maestro/tracks/<id>.json` | Duplicate track_id |
| `maestro phase add <id> --track <track> --name "<name>"` | Create phase | Phase ID, track ID, name | `docs/maestro/phases/<id>.json` | Duplicate phase_id, invalid track_id |
| `maestro task add <id> --phase <phase> --name "<name>" --description "<desc>"` | Create task | Task ID, phase ID, name, description | `docs/maestro/tasks/<id>.json` | Duplicate task_id, invalid phase_id |
| `maestro task next` | Show next available task | None | Task details | No tasks available |
| `maestro work task <id>` | Execute task | Task ID | Work artifacts | Engine validation fails |
| `maestro task complete <id>` | Complete task | Task ID | Updated task status, moved to done.md | Task not found, already completed |

---

## Tests Implied by this Scenario

### Unit Tests

1. **Directory & Initialization**:
   - `test_git_init_creates_repository()`
   - `test_maestro_init_creates_directory_structure()`
   - `test_maestro_init_idempotent()`

2. **Track Creation**:
   - `test_track_add_creates_json()`
   - `test_track_add_rejects_duplicate_id()`
   - `test_track_add_validates_json_structure()`

3. **Phase Creation**:
   - `test_phase_add_creates_json()`
   - `test_phase_add_rejects_invalid_track_id()`
   - `test_phase_add_links_to_track()`

4. **Task Creation**:
   - `test_task_add_creates_json()`
   - `test_task_add_rejects_invalid_phase_id()`
   - `test_task_add_with_dependencies()`
   - `test_task_add_updates_todo_md()`

5. **Work Loop**:
   - `test_task_next_selects_unblocked_task()`
   - `test_work_task_executes_with_engine()`
   - `test_task_complete_moves_to_done_md()`
   - `test_task_complete_validates_task_exists()`

### Integration Tests

1. **Fixture Scenarios**:
   - `fixture_greenfield_rust_project`: Empty dir → full Rust project setup
   - `fixture_greenfield_python_project`: Empty dir → Python project with manual tasks
   - `fixture_manual_task_chain`: Create track → phase → 5 dependent tasks → execute in order

2. **End-to-End Scenarios**:
   - `test_scenario_02_full_workflow()`: Run entire WF-02 from empty dir to completed project
   - `test_manual_planning_with_dependencies()`: Create complex task graph, verify execution order
   - `test_work_loop_iteration()`: Execute multiple tasks in sequence, verify state transitions

### Example Sessions

**Session 1: University Assignment Workflow**

```bash
# Operator has assignment: "Build a command-line calculator"
mkdir calculator-assignment
cd calculator-assignment
git init
maestro init

# Manual planning
maestro track add assignment --name "Calculator Assignment"
maestro phase add setup --track assignment --name "Project Setup"
maestro phase add impl --track assignment --name "Implementation"
maestro phase add test --track assignment --name "Testing"

# Add tasks
maestro task add T001 --phase setup --name "Create Cargo.toml"
maestro task add T002 --phase impl --name "Implement addition function"
maestro task add T003 --phase impl --name "Implement subtraction function"
maestro task add T004 --phase test --name "Write unit tests"

# Work loop
maestro task next              # Shows T001
maestro work task T001         # Execute setup
maestro task complete T001     # Mark done

maestro task next              # Shows T002
maestro work task T002
maestro task complete T002

# Continue for all tasks...
```

---

## Relationship to Other Scenarios

- **WF-01** (Existing Repo Bootstrap): Covers retrofitting Maestro to existing code
- **WF-02** (This scenario): Covers greenfield manual planning
- **WF-05** (Feature Request): May follow this scenario after initial project completion

**Key Differences from WF-01**:
- WF-01 starts with existing code; WF-02 starts from empty directory
- WF-01 uses reconstruction; WF-02 uses manual planning
- WF-01 may detect build errors automatically; WF-02 relies on explicit task definitions

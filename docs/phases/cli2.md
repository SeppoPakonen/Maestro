# Phase CLI2: Track/Phase/Task Commands 📋 **[Planned]**

- *phase_id*: *cli-tpt-2*
- *track*: *Track/Phase/Task CLI and AI Discussion System*
- *track_id*: *cli-tpt*
- *status*: *planned*
- *completion*: 0
- *duration*: *1-2 weeks*
- *dependencies*: [*cli-tpt-1*]
- *priority*: *P0*

**Objective**: Implement the complete Track/Phase/Task command-line interface, providing CRUD operations and navigation for all three hierarchy levels.

## Background

The new CLI provides a structured way to manage project planning:
- **Tracks**: High-level feature areas (e.g., "Build System", "TU/AST", "CLI")
- **Phases**: Major milestones within tracks (e.g., "Phase 1: Core Builder")
- **Tasks**: Individual work items within phases (e.g., "Task 1.1: Module Structure")

This replaces the old "plan/task" terminology and provides richer navigation and management.

## Tasks

### Task cli2.1: Track Commands

- *task_id*: *cli-tpt-2-1*
- *priority*: *P0*
- *estimated_hours*: 12

Implement `maestro track` command group.

- [ ] **cli2.1.1: Track List Command**
  - [ ] Implement `maestro track list`
    - Display all tracks from docs/todo.md
    - Show track ID, name, status, phase count
    - Format:
      ```
      Tracks:
        0. [🚧] Track/Phase/Task CLI (4 phases)
        1. [🚧] UMK Integration (12 phases)
        2. [📋] TU/AST System (6 phases)
      ```
  - [ ] Add `--all` flag to include completed tracks from docs/done.md
  - [ ] Add `--json` flag for machine-readable output

- [ ] **cli2.1.2: Track Show Command**
  - [ ] Implement `maestro track <id>` (alias for `maestro track <id> show`)
    - Display track details: name, status, description
    - List all phases with status
    - Show overall completion percentage
  - [ ] Support both numeric ID and track_id string
  - [ ] Add `--verbose` for full details including metadata

- [ ] **cli2.1.3: Track Add Command**
  - [ ] Implement `maestro track add <name>`
    - Prompt for track description
    - Generate unique track_id
    - Add to docs/todo.md
    - Create initial phase structure prompt
  - [ ] Add `--description` flag for non-interactive mode
  - [ ] Add `--priority` flag to set priority (default: lowest+1)

- [ ] **cli2.1.4: Track Remove Command**
  - [ ] Implement `maestro track remove <id>`
    - Prompt for confirmation
    - Move to docs/done.md if has completed work
    - Delete if never started
  - [ ] Add `--force` to skip confirmation
  - [ ] Add `--archive` to move to done even if not complete

- [ ] **cli2.1.5: Track Edit Command**
  - [ ] Implement `maestro track <id> edit`
    - Open docs/todo.md in $EDITOR at track location
    - Jump to track heading line
  - [ ] Validate markdown after editing
  - [ ] Offer to fix if validation fails

- [ ] **cli2.1.6: Track Phase Navigation**
  - [ ] Implement `maestro track <id> phase`
    - Alias for `maestro phase list --track <id>`
    - Show phases filtered to specific track
  - [ ] Implement `maestro track <id> phase <phase-id>`
    - Direct navigation to phase within track

### Task cli2.2: Phase Commands

- *task_id*: *cli-tpt-2-2*
- *priority*: *P0*
- *estimated_hours*: 16

Implement `maestro phase` command group.

- [ ] **cli2.2.1: Phase List Command**
  - [ ] Implement `maestro phase list`
    - Display all phases from all tracks
    - Show phase ID, name, track, status, completion
    - Format:
      ```
      Phases:
        cli-tpt-1  [📋  0%] CLI1: Markdown Data Backend (Track/Phase/Task CLI)
        cli-tpt-2  [📋  0%] CLI2: Track/Phase/Task Commands (Track/Phase/Task CLI)
        umk-1      [🚧 60%] Phase 1: Core Builder Abstraction (UMK Integration)
      ```
  - [ ] Add `--track <id>` to filter by track
  - [ ] Add `--status <status>` to filter by status (planned, in_progress, done)
  - [ ] Add `--all` to include completed phases from docs/done.md
  - [ ] Add `--json` for machine-readable output

- [ ] **cli2.2.2: Phase Show Command**
  - [ ] Implement `maestro phase <id>` (alias for `maestro phase <id> show`)
    - Display phase details from docs/phases/*.md
    - Show: name, track, status, completion, duration, dependencies
    - List all tasks with status
    - Show objective and deliverables
  - [ ] Support both numeric index and phase_id string
  - [ ] Add `--tasks` to show task details inline
  - [ ] Add `--verbose` for full details

- [ ] **cli2.2.3: Phase Add Command**
  - [ ] Implement `maestro phase add <track-id> <name>`
    - Prompt for phase details (duration, dependencies, objective)
    - Generate unique phase_id
    - Add to docs/todo.md under specified track
    - Create docs/phases/<phase-id>.md file
  - [ ] Add `--template <file>` to use phase template
  - [ ] Add non-interactive mode with flags

- [ ] **cli2.2.4: Phase Remove Command**
  - [ ] Implement `maestro phase remove <id>`
    - Prompt for confirmation
    - Check for dependent phases
    - Move to docs/done.md or delete
    - Remove docs/phases/<phase-id>.md if not started
  - [ ] Add `--force` to skip confirmation
  - [ ] Warn if other phases depend on this one

- [ ] **cli2.2.5: Phase Edit Command**
  - [ ] Implement `maestro phase <id> edit`
    - Open docs/phases/<phase-id>.md in $EDITOR
  - [ ] Validate markdown after editing
  - [ ] Sync changes back to docs/todo.md summary

- [ ] **cli2.2.6: Phase Task Navigation**
  - [ ] Implement `maestro phase <id> task`
    - Alias for `maestro task list --phase <id>`
  - [ ] Implement `maestro phase <id> task <task-id>`
    - Direct navigation to task within phase

### Task cli2.3: Task Commands

- *task_id*: *cli-tpt-2-3*
- *priority*: *P0*
- *estimated_hours*: 16

Implement `maestro task` command group.

- [ ] **cli2.3.1: Task List Command**
  - [ ] Implement `maestro task list`
    - Display all tasks from all phases
    - Show task ID, name, phase, status, priority
    - Format:
      ```
      Tasks:
        cli-tpt-1-1  [📋] Task 1.1: Parser Module (CLI1, P0)
        cli-tpt-1-2  [📋] Task 1.2: Writer Module (CLI1, P0)
        umk-1-1      [🚧] Task 1.1: Module Structure (Phase 1, P0)
      ```
  - [ ] Add `--phase <id>` to filter by phase
  - [ ] Add `--track <id>` to filter by track
  - [ ] Add `--priority <P0|P1|P2>` to filter by priority
  - [ ] Add `--status <status>` to filter by status
  - [ ] Add `--all` to include completed tasks
  - [ ] Add `--json` for machine-readable output

- [ ] **cli2.3.2: Task Show Command**
  - [ ] Implement `maestro task <id>` (alias for `maestro task <id> show`)
    - Display task details from docs/phases/*.md
    - Show: name, phase, track, priority, estimated hours
    - Show description and subtasks
    - Show completion status
  - [ ] Support both numeric index and task_id string
  - [ ] Add `--verbose` for full context (including phase details)

- [ ] **cli2.3.3: Task Add Command**
  - [ ] Implement `maestro task add <phase-id> <name>`
    - Prompt for task details (priority, description, subtasks)
    - Generate unique task_id
    - Add to docs/phases/<phase-id>.md
    - Update docs/todo.md summary if needed
  - [ ] Add `--priority <P0|P1|P2>` flag
  - [ ] Add `--hours <num>` for estimated hours
  - [ ] Add non-interactive mode with flags

- [ ] **cli2.3.4: Task Remove Command**
  - [ ] Implement `maestro task remove <id>`
    - Prompt for confirmation
    - Remove from docs/phases/<phase-id>.md
    - Update docs/todo.md or docs/done.md if needed
  - [ ] Add `--force` to skip confirmation

- [ ] **cli2.3.5: Task Edit Command**
  - [ ] Implement `maestro task <id> edit`
    - Open docs/phases/<phase-id>.md in $EDITOR at task location
    - Jump to task heading line
  - [ ] Validate markdown after editing

- [ ] **cli2.3.6: Task Status Management**
  - [ ] Implement `maestro task <id> start`
    - Mark task as in_progress
    - Update checkbox to `- [ ]` (in progress, not checked)
  - [ ] Implement `maestro task <id> done`
    - Mark task as completed
    - Update checkbox to `- [x]`
    - Move to docs/done.md if phase is complete
  - [ ] Implement `maestro task <id> block <reason>`
    - Mark task as blocked
    - Add blocker note to task

### Task cli2.4: Navigation and Aliases

- *task_id*: *cli-tpt-2-4*
- *priority*: *P1*
- *estimated_hours*: 4

Implement convenient navigation patterns and command aliases.

- [ ] **cli2.4.1: Numeric vs ID Access**
  - [ ] Support numeric indices from list commands
    - `maestro track 0` → first track in list
    - `maestro phase 5` → fifth phase in list
  - [ ] Support string IDs for direct access
    - `maestro track cli-tpt` → track by ID
    - `maestro phase cli-tpt-1` → phase by ID
  - [ ] Auto-detect which type is provided

- [ ] **cli2.4.2: Command Aliases**
  - [ ] `maestro t` → `maestro track`
  - [ ] `maestro p` → `maestro phase`
  - [ ] `maestro ts` → `maestro task`
  - [ ] Support all subcommands with aliases

- [ ] **cli2.4.3: Current Context**
  - [ ] Implement context tracking in docs/config.md
    - `current_track`, `current_phase`, `current_task`
  - [ ] Implement `maestro track <id> set`
    - Set current track context
  - [ ] Implement contextual commands:
    - `maestro phase list` (no args) → list phases in current track
    - `maestro task list` (no args) → list tasks in current phase

### Task cli2.5: Help System

- *task_id*: *cli-tpt-2-5*
- *priority*: *P1*
- *estimated_hours*: 4

Implement comprehensive help for all commands.

- [ ] **cli2.5.1: Track Help**
  - [ ] Implement `maestro track help`
    - Show all track subcommands with examples
    - Show navigation patterns
  - [ ] Add examples for common workflows

- [ ] **cli2.5.2: Phase Help**
  - [ ] Implement `maestro phase help`
    - Show all phase subcommands with examples

- [ ] **cli2.5.3: Task Help**
  - [ ] Implement `maestro task help`
    - Show all task subcommands with examples

- [ ] **cli2.5.4: Global Help Updates**
  - [ ] Update `maestro help` to include track/phase/task
  - [ ] Add navigation guide section

## Deliverables

- `maestro/commands/track.py` - Track command implementation
- `maestro/commands/phase.py` - Phase command implementation
- `maestro/commands/task.py` - Task command implementation
- `maestro/cli/navigation.py` - Navigation utilities
- `maestro/cli/context.py` - Context management
- `tests/commands/test_track.py` - Track command tests
- `tests/commands/test_phase.py` - Phase command tests
- `tests/commands/test_task.py` - Task command tests

## Test Criteria

- All CRUD operations work correctly
- Navigation between track/phase/task is seamless
- Both numeric and ID-based access work
- Markdown validation catches errors
- Help system is comprehensive and accurate
- Changes are properly synced between docs/todo.md and docs/phases/*.md

## Dependencies

- Phase CLI1 (Markdown Data Backend) must be complete

## Notes

- Commands should be idempotent where possible
- All destructive operations require confirmation (unless --force)
- Validation should happen after every edit
- Context management makes common operations faster

## Estimated Complexity: Medium-High (1-2 weeks total)

- Days 1-3: Track commands (2.1)
- Days 4-6: Phase commands (2.2)
- Days 7-9: Task commands (2.3)
- Days 10: Navigation, aliases, help (2.4, 2.5)

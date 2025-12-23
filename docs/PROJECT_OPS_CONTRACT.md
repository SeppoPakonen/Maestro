# Project Operations Contract

This document describes the contract for canonical ProjectOpsResult JSON used in Maestro's project automation pipeline.

## Overview

The Project Operations pipeline implements a strict rule-based control layer that processes a single canonical JSON object through a four-stage pipeline:
1. Accepts a canonical ProjectOpsResult JSON object
2. Validates the JSON against the schema
3. Translates validated intents into typed operations
4. Applies them to project files (docs/todo.md, docs/done.md, etc.) with dry-run preview and hard-stop behavior on any mismatch

## JSON Structure

### Canonical ProjectOpsResult (Maestro-facing)

The canonical ProjectOpsResult contains the operations:

```json
{
  "kind": "project_ops",
  "version": 1,
  "scope": "project",
  "actions": [
    {
      "action": "track_create",
      "title": "New Track Title"
    },
    {
      "action": "phase_create",
      "track": "New Track Title",
      "title": "New Phase Title"
    }
  ],
  "notes": "Optional notes about the operations"
}
```

**Fields:**
- `kind`: Must be `"project_ops"`
- `version`: Version number (string or integer)
- `scope`: Must be `"project"`
- `actions`: Array of action objects
- `notes`: Optional string notes (ignored by processor)

## Action Types

### `track_create`
Creates a new track.

```json
{
  "action": "track_create",
  "title": "Track Title"
}
```

### `phase_create`
Creates a new phase within a track.

```json
{
  "action": "phase_create",
  "track": "Track Title",
  "title": "Phase Title"
}
```

### `task_create`
Creates a new task within a phase of a track.

```json
{
  "action": "task_create",
  "track": "Track Title",
  "phase": "Phase Title",
  "title": "Task Title"
}
```

### `task_move_to_done`
Moves a task to done status.

```json
{
  "action": "task_move_to_done",
  "track": "Track Title",
  "phase": "Phase Title",
  "task": "Task Title"
}
```

### `context_set`
Sets the current context (optional).

```json
{
  "action": "context_set",
  "current_track": "Track Title",
  "current_phase": "Phase Title",
  "current_task": "Task Title"
}
```

## CLI Commands

### `maestro ops validate <jsonfile>`
Validates a project operations JSON file against schemas.

### `maestro ops preview <jsonfile>`
Shows a preview of changes that would be made by applying operations.

### `maestro ops apply <jsonfile>`
Applies the operations to the project files.

## Error Handling

The pipeline implements hard-stop behavior:
- Any schema violation causes immediate failure
- Any operation that cannot be completed causes immediate failure
- No partial commits are allowed

## Execution Substrate

This is the execution substrate for `plan explore` - the deterministic execution layer that will be used by the AI-powered planning feature to make safe, validated changes to the project structure.
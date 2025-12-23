# Plan Operations Contract

This document describes the contract for canonical PlanOpsResult JSON used in Maestro's plan automation pipeline.

## Overview

The Plan Operations pipeline implements a strict rule-based control layer that processes a single canonical JSON object through a four-stage pipeline:
1. Accepts a canonical PlanOpsResult JSON object
2. Validates the JSON against the schema
3. Translates validated intents into typed operations
4. Applies them via PlanStore with dry-run preview and hard-stop behavior on any mismatch

## JSON Structure

### Canonical PlanOpsResult (Maestro-facing)

The canonical PlanOpsResult contains the operations:

```json
{
  "kind": "plan_ops",
  "version": 1,
  "scope": "plan",
  "actions": [
    {
      "action": "plan_create",
      "title": "New Plan Title"
    },
    {
      "action": "plan_item_add",
      "selector": {
        "title": "Existing Plan"
      },
      "text": "New item text"
    }
  ],
  "notes": "Optional notes about the operations"
}
```

**Fields:**
- `kind`: Must be `"plan_ops"`
- `version`: Version number (string or integer)
- `scope`: Must be `"plan"`
- `actions`: Array of action objects
- `notes`: Optional string notes (ignored by processor)

## Action Types

### `plan_create`
Creates a new plan.

```json
{
  "action": "plan_create",
  "title": "Plan Title"
}
```

### `plan_delete`
Deletes an existing plan.

```json
{
  "action": "plan_delete",
  "selector": {
    "title": "Plan Title"  // Or "index": 1
  }
}
```

### `plan_item_add`
Adds an item to an existing plan.

```json
{
  "action": "plan_item_add",
  "selector": {
    "title": "Plan Title"  // Or "index": 1
  },
  "text": "Item text"
}
```

### `plan_item_remove`
Removes an item from an existing plan.

```json
{
  "action": "plan_item_remove",
  "selector": {
    "title": "Plan Title"  // Or "index": 1
  },
  "item_index": 2
}
```

### `commentary`
Provides commentary (ignored by executor).

```json
{
  "action": "commentary",
  "text": "This is a comment"
}
```

## Selector Format

Selectors identify a specific plan and can use either:
- `title`: Plan title (case-insensitive matching)
- `index`: 1-based index from `plan list` order

Selectors must have exactly one of these fields.

## CLI Commands

### `maestro plan ops validate <jsonfile>`
Validates a plan operations JSON file against schemas.

### `maestro plan ops preview <jsonfile>`
Shows a preview of changes that would be made by applying operations.

### `maestro plan ops apply <jsonfile>`
Applies the operations to the plan store.

## Error Handling

The pipeline implements hard-stop behavior:
- Any schema violation causes immediate failure
- Any invalid selector causes immediate failure
- Any operation that cannot be completed causes immediate failure
- No partial commits are allowed

## Plan Discuss Command

The `maestro plan discuss` command allows AI-driven plan editing:

```
maestro plan discuss <title|number>
```

This command:
1. Loads the specified plan from PlanStore
2. Starts an AI discussion session with the plan context
3. AI returns a canonical PlanOpsResult JSON
4. Validates the JSON strictly
5. Shows a preview of proposed changes
6. Asks for explicit user confirmation before applying
7. Executes changes through the Plan Ops pipeline

AI may modify plans **through Maestro**; validation is assertive; docs remain canonical.
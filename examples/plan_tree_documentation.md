# Plan Tree Structure Example for Codex

## Overview

This document provides a concrete example of the plan tree JSON structure used in the Maestro orchestration system. The plan tree enables branching workflows where multiple plan variations can coexist, with one active plan at a time.

## Complete JSON Example

```json
{
  "plans": [
    {
      "plan_id": "P1",
      "parent_plan_id": null,
      "label": "Initial Composition",
      "status": "inactive",
      "notes": "Original structure; replaced by later ideas.",
      "categories_snapshot": ["architecture", "backend", "tests"],
      "subtask_ids": ["S1", "S2"],
      "root_snapshot": "Build a web application with user authentication and dashboard"
    },
    {
      "plan_id": "P2",
      "parent_plan_id": "P1",
      "label": "Backend Variation",
      "status": "dead",
      "notes": "Discarded: too complex.",
      "categories_snapshot": ["backend"],
      "subtask_ids": ["S3", "S4"],
      "root_snapshot": "Build a web application with user authentication and dashboard"
    },
    {
      "plan_id": "P3",
      "parent_plan_id": "P1",
      "label": "Test-Driven Rewrite",
      "status": "active",
      "notes": "",
      "categories_snapshot": ["tests", "refactoring"],
      "subtask_ids": ["S5", "S6", "S7"],
      "root_snapshot": "Build a web application with user authentication and dashboard"
    }
  ],
  "active_plan_id": "P3"
}
```

## Field Explanations

- `plans`: Array of plan nodes forming the branching structure
- `plan_id`: Unique identifier for each plan branch
- `parent_plan_id`: ID of parent plan (null for root plans)
- `label`: Human-readable description of the plan
- `status`: One of "active" (current work), "inactive" (paused), or "dead" (discarded)
- `notes`: Additional information about the plan's purpose or state
- `categories_snapshot`: Categories from the root task at plan creation time
- `subtask_ids`: List of subtask IDs associated with this plan branch
- `root_snapshot`: Snapshot of the root task as it existed when this plan was created
- `active_plan_id`: ID of the currently active plan branch

## Status Meanings

- `active`: The current plan being worked on
- `inactive`: A plan that was paused but may be resumed later
- `dead`: A plan that was abandoned and will not be worked on further

## Usage Context

This plan tree structure enables:
1. Creating multiple approaches to a problem (branching)
2. Tracking which approach is currently active
3. Marking unsuccessful approaches as dead
4. Maintaining context through root and category snapshots
5. Associating subtasks with specific plan branches
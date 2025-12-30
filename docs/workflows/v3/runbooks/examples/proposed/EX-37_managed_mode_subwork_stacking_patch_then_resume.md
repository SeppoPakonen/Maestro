# EX-37: Managed Mode Subwork Stacking (Patch then Resume)

**Scope**: Managed-mode subwork stacking
**Tags**: work, subwork, wsession, managed-mode, handoff
**Status**: proposed
**Sprint**: P2 Sprint 4.8

## Goal

Demonstrate a parent work session spawning a subwork session, closing the child with a structured summary, and resuming the parent with a result breadcrumb.

## Context

Managed mode requires deterministic, non-AI lifecycle steps. This runbook uses `--simulate` to avoid invoking AI while still creating a work session.

## Prerequisites

- Repository initialized (`maestro init`)
- A real task ID to work on (replace `<TASK_ID>` below)

## Steps

### 1. Start a parent work session (simulate, no AI)

```bash
maestro work task <TASK_ID> --simulate
```

**Expected**:
- Work session created for the task
- Prompt printed (no AI run)

**Stores**:
- `docs/sessions/<PARENT_ID>/session.json`

---

### 2. Capture the parent session ID

```bash
maestro wsession list
```

**Expected**:
- Parent session appears as most recent running session
- Copy the `session_id` as `<PARENT_ID>`

---

### 3. Start subwork (pause parent)

```bash
maestro work subwork start <PARENT_ID> \
  --purpose "Diagnose failing tests" \
  --context task:<TASK_ID>
```

**Expected**:
- Child session created and printed
- Parent session state set to `paused`

**Stores**:
- `docs/sessions/<PARENT_ID>/<CHILD_ID>/session.json`

---

### 4. List subwork sessions

```bash
maestro work subwork list <PARENT_ID>
```

**Expected**:
- Child session listed with status `running`

---

### 5. Close child with summary + status

```bash
maestro work subwork close <CHILD_ID> \
  --summary "Tests fail in module X; missing fixture in test data." \
  --status ok
```

**Expected**:
- Child session closed
- Parent session resumed (unless other children remain open)
- Parent gets a `result` breadcrumb with tags `subwork`, `handoff`

**Stores**:
- `docs/sessions/<PARENT_ID>/breadcrumbs/.../<TIMESTAMP>.json`

---

### 6. Validate parent resume and breadcrumb

```bash
maestro wsession show <PARENT_ID>
maestro wsession tree
maestro wsession breadcrumbs <PARENT_ID> --summary
```

**Expected**:
- Parent status `running`
- Tree shows parent → child
- Breadcrumb summary includes the result entry

---

## Notes

- This flow is deterministic and non-AI.
- Replace `<TASK_ID>`, `<PARENT_ID>`, and `<CHILD_ID>` with real values from your repo.

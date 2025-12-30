# EX-38: Ops Doctor Detects Open Subwork and Guides Remediation

**Scope**: Ops doctor awareness of managed-mode subwork
**Tags**: ops, doctor, subwork, managed-mode, gates
**Status**: proposed
**Sprint**: P2 Sprint 4.8

## Goal

Show `maestro ops doctor` reporting open subwork sessions and guiding remediation commands.

## Prerequisites

- Repository initialized (`maestro init`)
- A real task ID to work on (replace `<TASK_ID>` below)

## Steps

### 1. Start a parent work session (simulate)

```bash
maestro work task <TASK_ID> --simulate
maestro wsession list
```

**Expected**:
- Parent session created
- Note the parent session ID as `<PARENT_ID>`

---

### 2. Start a child subwork

```bash
maestro work subwork start <PARENT_ID> \
  --purpose "Investigate build failure" \
  --context task:<TASK_ID>
```

**Expected**:
- Child session created and parent paused
- Capture `<CHILD_ID>`

---

### 3. Run ops doctor

```bash
maestro ops doctor
```

**Expected**:
- Finding: `SUBWORK_OPEN_CHILDREN`
- Details list parent + child IDs
- Recommended commands show `work subwork list` / `close`

---

### 4. Remediate by closing child

```bash
maestro work subwork close <CHILD_ID> \
  --summary "Build fails in target X; fix Makefile include path." \
  --status ok
```

**Expected**:
- Child session closed
- Parent resumed

---

### 5. Re-run ops doctor

```bash
maestro ops doctor
```

**Expected**:
- `SUBWORK_OPEN_CHILDREN` now reports OK

---

## Notes

- This flow is deterministic and non-AI.
- Replace `<TASK_ID>`, `<PARENT_ID>`, and `<CHILD_ID>` with real values from your repo.

# P2 Sprint 4.3 — Fail Repro: Task Metadata Parsing + Work Gate Linking

**Generated**: 2025-12-29
**Sprint**: P2 Sprint 4.3
**Objective**: Remove last 2 skiplist entries by implementing task metadata parsing + work gate linking

## Failing Tests

### Test 1: `tests/test_work_gates_blockers.py::TestWorkGates::test_blocker_with_linked_task_allows_work`

**Line**: 83-123
**Node ID**: `tests/test_work_gates_blockers.py::TestWorkGates::test_blocker_with_linked_task_allows_work`

**Expected Behavior**: Work gate should allow work when blocker issue is linked to an in_progress task

**Actual Behavior**: Work gate blocks work (returns False)

**Test Data**:
```python
# Issue linked to task "123"
link_issue_to_task(issue_id, "123", repo_root=temp_repo)

# Phase file created with:
phase_content = """# Phase test1: Test Phase

## Metadata
- track_id: testtrack
- status: in_progress

## Tasks

### Task 123: Fix segfault
- task_id: TASK-123
- status: in_progress
"""
```

**Root Cause**:
The task is linked by ID "123" but the phase markdown defines `task_id: TASK-123`. The work gate logic at `maestro/commands/work.py:258` checks:

```python
task_id = task.get("task_id") or task.get("task_number")
if task_id in issue.linked_tasks:
```

This uses `or` which means if `task_id` exists (as "TASK-123"), it never checks `task_number` (which is "123"). The match fails because "TASK-123" is not in the linked_tasks list (which contains "123").

**Fix Required**:
Check BOTH `task_id` and `task_number` fields against linked_tasks:

```python
task_id = task.get("task_id")
task_number = task.get("task_number")
# Check if either matches
if (task_id and task_id in issue.linked_tasks) or (task_number and task_number in issue.linked_tasks):
    # Task matches
```

**Failure Output**:
```
AssertionError: Work should proceed when blocker has linked in_progress task
assert False is True
```

---

### Test 2: `tests/test_work_gates_blockers.py::TestWorkGates::test_blocker_with_linked_todo_task_blocks_work`

**Line**: 125-170
**Node ID**: `tests/test_work_gates_blockers.py::TestWorkGates::test_blocker_with_linked_todo_task_blocks_work`

**Expected Behavior**: Work gate should block work when blocker issue is linked to a todo task (not in_progress)

**Actual Behavior**: Same matching issue as Test 1

**Test Data**:
```python
# Issue linked to task "124"
link_issue_to_task(issue_id, "124", repo_root=temp_repo)

# Phase file created with:
phase_content = """# Phase test2: Test Phase

## Metadata
- track_id: testtrack
- status: todo

## Tasks

### Task 124: Fix memory leak
- task_id: TASK-124
- status: todo
"""
```

**Root Cause**: Same as Test 1 - task_id/task_number matching logic

**Fix Required**: Same as Test 1

---

## Implementation Plan

### Phase B: Task Metadata Parsing

**Status**: ✅ Already implemented
**Location**: `maestro/data/markdown_parser.py`

The parser already correctly extracts:
- `task_number`: extracted from heading "### Task 123: Name" → "123"
- `task_id`: extracted from metadata "- task_id: TASK-123" → "TASK-123"
- `status`: extracted from metadata "- status: in_progress" → "in_progress"

No changes needed to parser.

---

### Phase C: Work Gate Linking Logic

**Status**: ❌ Needs fix
**Location**: `maestro/commands/work.py:245-274`

**Current Logic** (line 258):
```python
task_id = task.get("task_id") or task.get("task_number")
if task_id in issue.linked_tasks:
```

**Fixed Logic**:
```python
task_id = task.get("task_id")
task_number = task.get("task_number")
# Check if either task_id or task_number matches linked tasks
if (task_id and task_id in issue.linked_tasks) or (task_number and task_number in issue.linked_tasks):
```

**Files to Modify**:
- `maestro/commands/work.py` (1 line change, expand to 3-4 lines)

---

## Verification Commands

After fix:
```bash
# Run both failing tests
bash tools/test/run.sh -k "test_blocker_with_linked" -xvs

# Run all work gate tests
bash tools/test/run.sh -k "test_work_gates_blockers" -v

# Run full portable suite
bash tools/test/run.sh

# Verify portable subset
bash tools/test/verify_portable_subset.sh
```

---

## Summary

**Issue**: Task ID matching logic uses `or` instead of checking both fields
**Impact**: Tests expecting linked task detection fail
**Complexity**: Low (1 line fix)
**Risk**: Low (isolated change, covered by tests)
**Estimate**: 5 minutes to fix, 5 minutes to verify


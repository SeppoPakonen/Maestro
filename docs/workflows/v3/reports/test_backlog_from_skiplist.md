# Test Backlog from Skiplist Burndown

**Generated**: 2025-12-29
**Source**: tools/test/skiplist.txt analysis

This document tracks tests that are currently skipped because they require features that are not yet implemented. These tests represent future work items that should be addressed to expand test coverage.

## Summary

| Test | Feature Required | Priority | Estimate |
|------|-----------------|----------|----------|
| test_blocker_with_linked_task_allows_work | Task metadata parsing + gate linking | P2 | L |
| test_blocker_with_linked_todo_task_blocks_work | Task metadata parsing + gate linking | P2 | L |

## Feature 1: Task Metadata Parsing + Work Gate Linking

**Description**: The work gates blocker logic needs to understand task linkages. When a blocker issue is linked to an in-progress task, the gate should allow work to proceed. This requires:

1. Phase markdown parser enhancement to extract task metadata
2. Gate logic to query linked task status
3. Ledger support for task-to-issue linking

### Affected Tests

#### tests/test_work_gates_blockers.py::TestWorkGates::test_blocker_with_linked_task_allows_work

**File**: tests/test_work_gates_blockers.py:123

**Current Behavior**: Gate blocks work when any blocker issue exists, regardless of linked task status.

**Expected Behavior**: Gate should allow work to proceed if the blocker issue has a linked task in `in_progress` or `completed` status.

**Test Intent**:
```python
# Test creates a blocker issue ISSUE-001
# Links it to an in_progress task TASK-001
# Expects: work gate allows proceeding
assert result is True, "Work should proceed when blocker has linked in_progress task"
```

**Requirements**:
- Parser must extract task_id and status from phase markdown
- Gate logic must call `get_linked_tasks(issue_id)` → `[{task_id, status}, ...]`
- If any linked task has status in ['in_progress', 'completed'], gate passes

**Acceptance Criteria**:
1. Phase markdown with task metadata is parsed correctly
2. Gate logic queries task linkages
3. Gate allows work when blocker has active linked task
4. Test passes without modification

---

#### tests/test_work_gates_blockers.py::TestWorkGates::test_blocker_with_linked_todo_task_blocks_work

**File**: tests/test_work_gates_blockers.py:165

**Current Behavior**: Gate blocks work when any blocker issue exists.

**Expected Behavior**: Gate should block work if the blocker issue has only linked tasks in `todo` or `blocked` status (not yet started).

**Test Intent**:
```python
# Test creates a blocker issue ISSUE-001
# Links it to a todo task TASK-002
# Expects: work gate still blocks
assert result is False, "Work should be blocked when linked task is only in todo"
```

**Requirements**:
- Same parser and linking infrastructure as above
- Gate logic must check task status values
- If all linked tasks are in ['todo', 'blocked'], gate fails

**Acceptance Criteria**:
1. Phase markdown with task metadata is parsed correctly
2. Gate logic queries task linkages and status
3. Gate blocks work when blocker has only todo/blocked tasks
4. Test passes without modification

---

## Implementation Plan

### Phase 1: Extend Phase Markdown Parser (L)

**Files**:
- maestro/data/markdown_parser.py

**Tasks**:
1. Add support for task metadata fields in phase markdown:
   ```markdown
   ### phase_id — Phase Title

   **Task**: TASK-001
   **Status**: in_progress
   **Linked Issues**: ISSUE-001, ISSUE-002
   ```

2. Update `parse_todo_md()` to extract:
   - `task_id`: string (e.g., "TASK-001")
   - `status`: enum (todo, in_progress, completed, blocked)
   - `linked_issues`: list of issue IDs

3. Add parser tests to validate extraction

**Estimate**: 3-5 hours

---

### Phase 2: Extend Work Gates Logic (M)

**Files**:
- maestro/commands/work.py (check_work_gates function)

**Tasks**:
1. When blocker gate fails, query linked tasks for each blocker issue
2. For each blocker issue:
   - Query ledger: `get_linked_tasks(issue_id)` → `[(task_id, status), ...]`
   - If any linked task has status in ['in_progress', 'completed'], skip this blocker
   - If all linked tasks in ['todo', 'blocked'], keep blocker active

3. Update gate message to show linked task status

**Estimate**: 2-3 hours

---

### Phase 3: Add Ledger Task Linking Support (M)

**Files**:
- maestro/ledger.py (or equivalent)

**Tasks**:
1. Add `link_task_to_issue(task_id, issue_id)` API
2. Add `get_linked_tasks(issue_id) -> List[Tuple[str, str]]` query
3. Store linkages in ledger storage (could be phase markdown or separate index)

**Estimate**: 2-4 hours

---

### Phase 4: Enable Tests (S)

**Tasks**:
1. Remove both tests from skiplist.txt
2. Run tests to verify they pass
3. Update skiplist_burndown.md to mark as completed

**Estimate**: 30 minutes

---

## Total Estimate

**Total work**: 8-13 hours (L estimate)

## Priority Justification

**Priority**: P2

**Reasoning**:
- These tests validate important work gate behavior
- Feature would improve developer workflow (allows work when blockers are being addressed)
- Not critical for basic functionality (gates work, just conservatively)
- Should be addressed after higher-priority portable test fixes

## Related Work

- docs/workflows/v3/reports/skiplist_burndown.md (classification source)
- maestro/commands/work.py:check_work_gates() (gate implementation)
- maestro/data/markdown_parser.py:parse_todo_md() (parser)

## Notes

- These tests were originally added to validate the linking feature before it was implemented
- The tests are well-structured and should not need modification once features are implemented
- Consider whether task linking should be stored in:
  - Phase markdown metadata (inline with phase)
  - Separate ledger index (faster queries)
  - Or both (redundant but consistent)

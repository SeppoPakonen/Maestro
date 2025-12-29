# Skiplist Burndown Report

**Generated**: 2025-12-29
**Goal**: Make `tools/test/run.sh` green without default skiplist

## Classification Summary

| Category | Count | Action Required |
|----------|-------|----------------|
| REDUNDANT | 5 | Remove from skiplist (handled by conftest.py) |
| FIXED | 2 | Remove from skiplist (tests now pass) |
| NONPORTABLE | 4 | Mark as @pytest.mark.slow, remove from portable default |
| FIX_NOW | 3 | Fix test implementation |
| NEEDS_FEATURE | 2 | Convert to backlog items, document in test_backlog |

**Total skiplist entries**: 16

## Detailed Classification

### REDUNDANT — Already handled by conftest.py (5 entries)

These entries are redundant because `conftest.py` already excludes them via the `pytest_ignore_collect` hook.

| Entry | Reason | Action | Estimate |
|-------|--------|--------|----------|
| `tests/legacy` | Excluded by conftest.py line 89 | Remove from skiplist | S |
| `tests/test_acceptance_criteria.py` | Excluded by conftest.py line 93-99 | Remove from skiplist | S |
| `tests/test_comprehensive.py` | Excluded by conftest.py line 93-99 | Remove from skiplist | S |
| `tests/test_migration_check.py` | Excluded by conftest.py line 93-99 | Remove from skiplist | S |
| `tests/test_run_cli_engine.py` | Excluded by conftest.py line 93-99 | Remove from skiplist | S |

**Plan**: Simply remove these 5 lines from skiplist.txt

---

### FIXED — Tests now pass (2 entries)

These tests were skipped due to "subprocess timeouts" but now pass reliably.

| Entry | Status | Action | Estimate |
|-------|--------|--------|----------|
| `tests/test_cli_uniformity.py::TestHelpContract::test_repo_keyword_shows_help` | PASSES (1.96s) | Remove from skiplist | S |
| `tests/test_mc2_no_textual.py::test_mc2_runs_without_textual_import` | PASSES (2.17s) | Remove from skiplist | S |

**Plan**: Remove these 2 entries from skiplist.txt

**Evidence**:
```bash
$ .venv/bin/python -m pytest tests/test_cli_uniformity.py::TestHelpContract::test_repo_keyword_shows_help -v
tests/test_cli_uniformity.py::TestHelpContract::test_repo_keyword_shows_help PASSED

$ .venv/bin/python -m pytest tests/test_mc2_no_textual.py::test_mc2_runs_without_textual_import -v
tests/test_mc2_no_textual.py::test_mc2_runs_without_textual_import PASSED
```

---

### NONPORTABLE — Requires external data (4 entries)

These tests depend on `~/Dev/ai-upp` repository which is not in the test suite. They are already marked `@pytest.mark.slow` but should be excluded from the portable default.

| Entry | Reason | Action | Estimate |
|-------|--------|--------|----------|
| `tests/test_repo_resolve_ai_upp.py::test_scan_upp_repo_v2_integration` | Requires ~/Dev/ai-upp | Already marked slow, verify exclusion | S |
| `tests/test_repo_resolve_ai_upp.py::test_cli_json_output_integration` | Requires ~/Dev/ai-upp | Already marked slow, verify exclusion | S |
| `tests/test_repo_resolve_ai_upp.py::test_cli_init_resolve_e2e` | Requires ~/Dev/ai-upp | Already marked slow, verify exclusion | S |
| `tests/test_repo_workflow_ai_upp_e2e.py::test_repo_workflow_e2e` | Requires ~/Dev/ai-upp | Already marked slow, verify exclusion | S |

**Plan**:
1. Verify these tests are marked with `pytestmark = pytest.mark.slow` (already done at line 19 of test_repo_resolve_ai_upp.py)
2. Verify pytest.ini excludes slow tests by default (already done: `-m "not legacy and not slow"`)
3. Remove these 4 entries from skiplist.txt since they're already excluded by marker

**Note**: These tests use `pytest.skip()` if the repo doesn't exist, so they gracefully handle missing data.

---

### FIX_NOW — Can be fixed with small changes (3 entries)

#### 1. `tests/test_work_command.py::TestWorkCommand::test_parse_todo_md_empty`

**Issue**: Test tries to mock `Path.exists` and `Path.read_text`, but the actual code calls `open()` directly in `maestro/data/markdown_parser.py:800`.

**Error**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'docs/todo.md'
```

**Fix**: Use `tmp_path` fixture and create actual test file instead of mocking

**Estimate**: S

**Implementation**:
- Remove mock patches
- Use `tmp_path` fixture to create temporary docs/todo.md
- Update test to use actual file I/O

---

#### 2. `tests/test_work_command.py::TestWorkCommand::test_handle_work_any`

**Issue**: Test timeout due to async worker dependencies

**Estimate**: M (needs investigation of async behavior)

**Plan**:
- Run test in isolation with timeout to understand failure mode
- Check if async mocks are properly configured
- Consider if test needs refactoring or if code has race condition

---

#### 3. `tests/test_work_command.py::TestWorkCommand::test_handle_work_any_pick`

**Issue**: Test timeout due to async worker dependencies

**Estimate**: M (needs investigation of async behavior)

**Plan**:
- Same as test_handle_work_any
- Check if these tests can share fix

---

### NEEDS_FEATURE — Tests expect unimplemented features (2 entries)

These tests expect the issue/task linking feature to be implemented in the work gates blocker logic.

#### 1. `tests/test_work_gates_blockers.py::TestWorkGates::test_blocker_with_linked_task_allows_work`

**Feature**: Task metadata parsing in phase markdown + gate logic to check linked tasks

**Current behavior**: Gate blocks work when blocker issue exists, regardless of linked task status

**Expected behavior**: Gate should allow work if blocker issue has linked in_progress task

**Test assertion**:
```python
assert result is True, "Work should proceed when blocker has linked in_progress task"
```

**Estimate**: L (requires parser + gate logic enhancement)

**Dependencies**:
- Phase markdown parser must extract `task_id` and `status` fields
- Gate logic must query linked task status
- Ledger must support task linking

---

#### 2. `tests/test_work_gates_blockers.py::TestWorkGates::test_blocker_with_linked_todo_task_blocks_work`

**Feature**: Same as above

**Expected behavior**: Gate should block work if blocker issue has linked task that's only in todo state

**Estimate**: L (same feature as above)

---

## Action Plan by Phase

### Phase B: Fix FIX_NOW (3 tests)

1. Fix `test_parse_todo_md_empty`:
   - Use `tmp_path` fixture instead of mocks
   - Create actual test file
   - Update assertions

2. Investigate and fix `test_handle_work_any`:
   - Run with verbose timeout
   - Check async mock configuration
   - Fix or skip if requires extensive refactoring

3. Investigate and fix `test_handle_work_any_pick`:
   - Same approach as test_handle_work_any

### Phase C: Re-home NONPORTABLE (4 tests)

- Verify tests are already marked `@pytest.mark.slow` ✓
- Verify pytest.ini excludes slow tests ✓
- Remove 4 entries from skiplist.txt

### Phase D: Document NEEDS_FEATURE (2 tests)

- Create test_backlog_from_skiplist.md
- Link to v3 ledger or create new P2 items
- Describe required features (task metadata parsing + gate linking logic)
- Define acceptance criteria

### Phase E: Clean up REDUNDANT + FIXED (7 entries)

- Remove 5 REDUNDANT entries (handled by conftest.py)
- Remove 2 FIXED entries (tests now pass)

### Phase F: Make skiplist opt-in

- Update tools/test/run.sh to not use skiplist by default
- Add --skiplist flag for opt-in
- Add banner when skiplist is enabled

## Success Criteria

1. `bash tools/test/run.sh` passes without skiplist
2. `tools/test/skiplist.txt` is empty or contains only documented opt-in skips
3. All NONPORTABLE tests excluded via `@pytest.mark.slow`
4. All NEEDS_FEATURE tests documented in backlog
5. All FIX_NOW tests either fixed or moved to appropriate category

## Timeline

- Phase B (FIX_NOW): 2-4 hours
- Phase C (NONPORTABLE): 30 minutes
- Phase D (NEEDS_FEATURE): 1 hour
- Phase E (Cleanup): 15 minutes
- Phase F (Make opt-in): 30 minutes
- Phase G (Commits): 30 minutes

**Total estimate**: 5-7 hours

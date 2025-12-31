# Test Policy - P1 Sprint 2.0

## Objective
Make `pytest -q` reliable and green by default on a normal dev machine without extra installations.

## Test Execution Contract

All automated test runs must go through `tools/test/run.sh`. The runner creates
the global `~/venv/`, installs the minimal pytest dependencies, and executes
`python -m pytest -q` with any provided arguments.

## Changes Made

###  1. pytest.ini Configuration

Updated `pytest.ini` with the following policies:

**Default Test Path**:
- Only search in `tests/` directory by default
- Excludes `maestro/` to avoid legacy/experimental code with complex dependencies

**Default Options**:
```ini
addopts =
    -q                              # Quiet mode by default
    --tb=short                      # Short traceback format
    --strict-markers                # Fail on unknown markers
    -m "not legacy and not slow"    # Skip legacy and slow tests by default
```

**Markers Defined**:
- `legacy`: Deprecated code paths, skipped by default
- `pexpect`: Requires pexpect module (skipped if not installed)
- `slow`: Long-running tests (> 1s), skipped by default
- `medium`: Medium speed tests (< 1s but not fast)
- `fast`: Quick unit tests (< 0.1s typical)
- `integration`: Integration tests

### 2. Legacy Test Handling

**Renamed Legacy Tests** (prefix with `legacy_`):
- `test_acceptance_criteria.py` → `legacy_test_acceptance_criteria.py`
- `test_comprehensive.py` → `legacy_test_comprehensive.py`
- `test_migration_check.py` → `legacy_test_migration_check.py`
- `test_run_cli_engine.py` → `legacy_test_run_cli_engine.py`

**Reason**: These tests have missing dependencies (`session_model`, `engines`) and are not part of the current P0/P1 test suite.

**Renamed Interactive Test**:
- `maestro/qwen/test_interactive.py` → `maestro/qwen/interactive_test_manual.py`

**Reason**: This test waits indefinitely for keyboard input and should be run manually, not via pytest.

### 3. Directory Exclusions

Added to `norecursedirs`:
- `maestro/qwen` - Experimental/legacy code with interactive tests
- `maestro/wrap` - Codex wrapper with potential external dependencies
- `maestro/tui` - TUI tests with complex dependencies
- `maestro/tui_backup` - Backup TUI code

## Running Tests

### Default Run (Fast, CI-Friendly, Parallel)
```bash
bash tools/test/run.sh
```
Runs stable tests from `tests/` directory in parallel (cpu_count - 1 workers), skipping legacy and slow tests.

### Full Run (Including Slow Tests)
```bash
bash tools/test/run.sh --profile all
```
Runs all tests including slow ones, but still skips legacy.

### Speed Profiles

**Fast Profile** (Quick iteration during development):
```bash
bash tools/test/run.sh --profile fast
```
Runs only `@pytest.mark.fast` tests (< 0.1s typical).

**Medium Profile** (Balanced coverage):
```bash
bash tools/test/run.sh --profile medium
```
Runs `@pytest.mark.fast` and `@pytest.mark.medium` tests (< 1s typical).

**Slow Profile** (Integration and heavy I/O):
```bash
bash tools/test/run.sh --profile slow
```
Runs only `@pytest.mark.slow` tests (> 1s typical).

### Parallelism Control

```bash
# Use 4 workers
bash tools/test/run.sh -j 4

# Disable parallelism (serial execution)
bash tools/test/run.sh -j 1

# Set default via environment
MAESTRO_TEST_JOBS=8 bash tools/test/run.sh
```

### Checkpoint & Resume (Iterative Debugging)

When iterating on failing tests, use checkpoint/resume to skip already-passed tests:

```bash
# First run: fail fast
bash tools/test/run.sh -x --maxfail=1
# Checkpoint written: /tmp/maestro_pytest_checkpoint_20231215_120000_12345.txt

# Fix the failing test, then resume
bash tools/test/run.sh --resume-from /tmp/maestro_pytest_checkpoint_20231215_120000_12345.txt -x --maxfail=1
```

### Profiling Slow Tests

Identify slow tests for optimization:

```bash
bash tools/test/run.sh --profile-report
```

Shows timing report for slowest 25 tests.

### Legacy Tests
```bash
bash tools/test/run.sh tests/legacy_*.py
```
Run legacy tests explicitly if needed (may require additional setup).

### Integration Tests
```bash
bash tools/test/run.sh -m integration
```
Run only integration tests.

## Policy Goals Achieved

✅ `tools/test/run.sh` passes on normal dev machine without extra installs
✅ New P0/P1 gate/discuss tests run in default mode
✅ Legacy/slow/interactive tests excluded by default
✅ Clear markers and documentation for test categories
✅ Parallel execution by default (pytest-xdist)
✅ Speed profiles for fast iteration (fast/medium/slow/all)
✅ Checkpoint/resume for iterative debugging
✅ Profiling support to identify slow tests

## Test Development Guidelines

When writing new tests:

1. **Mark test speed appropriately**:
   - `@pytest.mark.fast`: Unit tests, no I/O, < 0.1s
   - `@pytest.mark.medium`: Some I/O or computation, < 1s
   - `@pytest.mark.slow`: Integration tests, heavy I/O, > 1s

2. **Ensure parallel safety**:
   - Avoid shared global state
   - Use fixtures for resource isolation
   - Use unique file paths (e.g., temp directories with test-specific names)

3. **Profile regularly**:
   ```bash
   bash tools/test/run.sh --profile-report
   ```
   Identify and optimize slow tests to keep the suite fast.

## Future Work

- Mark existing tests with speed markers (fast/medium/slow)
- Add `@pytest.mark.integration` for integration tests
- Consider migrating or removing legacy tests entirely
- Add `pytest.importorskip()` for optional dependencies instead of renaming files
- Generate automated slow-test optimization reports

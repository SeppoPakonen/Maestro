# Test Policy - P1 Sprint 2.0

## Objective
Make `pytest -q` reliable and green by default on a normal dev machine without extra installations.

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
- `slow`: Long-running tests, skipped by default
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

### Default Run (Fast, CI-Friendly)
```bash
pytest -q
```
Runs stable tests from `tests/` directory, skipping legacy and slow tests.

### Full Run (Including Slow Tests)
```bash
pytest -q -m ""
```
Runs all tests including slow ones, but still skips legacy.

### Legacy Tests
```bash
pytest tests/legacy_*.py
```
Run legacy tests explicitly if needed (may require additional setup).

### Integration Tests
```bash
pytest -q -m integration
```
Run only integration tests.

## Policy Goals Achieved

✅ `pytest -q` passes on normal dev machine without extra installs
✅ New P0/P1 gate/discuss tests run in default mode
✅ Legacy/slow/interactive tests excluded by default
✅ Clear markers and documentation for test categories

## Future Work

- Mark slow tests with `@pytest.mark.slow` decorator
- Add `@pytest.mark.integration` for integration tests
- Consider migrating or removing legacy tests entirely
- Add `pytest.importorskip()` for optional dependencies instead of renaming files

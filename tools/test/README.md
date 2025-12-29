# Maestro Test Runner

Canonical test runner for the Maestro project with support for parallel execution, speed profiles, and checkpoint/resume functionality.

## Why this exists

Maestro uses a repo-local `.venv/` so `pytest -q` does not depend on system Python packages. The canonical entrypoint is `tools/test/run.sh`, which creates the venv if needed, installs the minimal test dependencies, and runs pytest.

## Quick Start

```bash
# Run all tests with default settings (parallel, excludes legacy)
bash tools/test/run.sh

# Run with verbose output
bash tools/test/run.sh -v

# Show help
bash tools/test/run.sh --help
```

## Features

### 1. Parallel Execution

By default, tests run in parallel using `pytest-xdist` with `cpu_count - 1` workers.

```bash
# Use default parallelism (cpu_count - 1)
bash tools/test/run.sh

# Use 4 workers
bash tools/test/run.sh -j 4

# Disable parallelism (run serial)
bash tools/test/run.sh -j 1

# Set default via environment
MAESTRO_TEST_JOBS=8 bash tools/test/run.sh
```

### 2. Speed Profiles

Filter tests by execution speed to enable fast iteration or comprehensive testing.

```bash
# Run only fast tests (quick unit tests, minimal I/O)
bash tools/test/run.sh --profile fast

# Run fast + medium tests
bash tools/test/run.sh --profile medium

# Run only slow tests (integration tests, heavy I/O)
bash tools/test/run.sh --profile slow

# Run all tests (default, still excludes legacy)
bash tools/test/run.sh --profile all

# Set default via environment
MAESTRO_TEST_PROFILE=fast bash tools/test/run.sh
```

**Marker definitions:**
- `@pytest.mark.fast`: Quick unit tests, minimal I/O (< 0.1s typical)
- `@pytest.mark.medium`: Reasonable runtime, not fast but not slow (< 1s typical)
- `@pytest.mark.slow`: Integration tests, heavy I/O, subprocess calls (> 1s typical)
- Unmarked tests: Run in all profiles except when profile=fast or profile=slow

**Note:** Not all tests are currently marked. Contributors should add markers to new tests. See `pytest.ini` for marker definitions.

### 3. Checkpoint & Resume

The runner automatically writes a checkpoint file after each run containing all PASSED test nodeids. Use resume mode to skip previously passed tests when iterating on failures.

```bash
# First run: tests fail, checkpoint written
bash tools/test/run.sh -x --maxfail=1
# Output: Checkpoint written: /tmp/maestro_pytest_checkpoint_20231215_120000_12345.txt

# Fix the failing test, then resume (skips already-passed tests)
bash tools/test/run.sh --resume-from /tmp/maestro_pytest_checkpoint_20231215_120000_12345.txt -x --maxfail=1

# Custom checkpoint location
bash tools/test/run.sh --checkpoint /tmp/my_checkpoint.txt

# Set via environment
MAESTRO_TEST_CHECKPOINT=/tmp/my_checkpoint.txt bash tools/test/run.sh
```

**Use case:** Long test suites where you're iterating on a small number of failing tests. Resume mode skips the already-passing tests, saving significant time.

### 4. Profiling & Performance

Identify slow tests for optimization.

```bash
# Show timing report for slowest 25 tests
bash tools/test/run.sh --profile-report

# Combine with other options
bash tools/test/run.sh --profile medium --profile-report -j 8
```

## Common Workflows

### Fail-Fast Development

Run tests, stop on first failure, resume after fixing:

```bash
# Initial run
bash tools/test/run.sh -x --maxfail=1

# After fixing, resume from checkpoint shown in output
bash tools/test/run.sh --resume-from /tmp/maestro_pytest_checkpoint_YYYYMMDD_HHMMSS_PID.txt -x --maxfail=1
```

### Fast Iteration

Run only fast tests during active development:

```bash
bash tools/test/run.sh --profile fast -j 4
```

### Pre-Commit / CI

Run all tests with profiling report:

```bash
bash tools/test/run.sh --profile all --profile-report
```

### Debugging Slow Tests

Find and investigate slow tests:

```bash
# Get timing report
bash tools/test/run.sh --profile-report > timing_report.txt

# Run only slow tests to investigate
bash tools/test/run.sh --profile slow -v
```

## Pass-Through Arguments

All unrecognized arguments are passed directly to pytest:

```bash
# Stop on first failure
bash tools/test/run.sh -x

# Run specific test file
bash tools/test/run.sh tests/test_ai_cache.py

# Run specific test function
bash tools/test/run.sh tests/test_ai_cache.py::test_function_name

# Capture output (disable output capture)
bash tools/test/run.sh -s

# Show local variables on failure
bash tools/test/run.sh -l

# Run tests matching keyword
bash tools/test/run.sh -k work_command

# Run tests with explicit markers
bash tools/test/run.sh -m slow
```

## Skiplist Management

The runner supports skipping tests via a skiplist file containing patterns to ignore.

**Default behavior**: Uses `tools/test/skiplist.txt` which skips legacy tests and deprecated test files.

```bash
# Use default skiplist (tools/test/skiplist.txt)
bash tools/test/run.sh

# Use custom skiplist
bash tools/test/run.sh --skiplist my_custom_skiplist.txt

# Disable skiplist (run ALL tests, even legacy)
bash tools/test/run.sh --skiplist ""

# Set default via environment
MAESTRO_TEST_SKIPLIST=/path/to/skiplist.txt bash tools/test/run.sh
```

**Skiplist file format**: One pattern per line (passed to `pytest --ignore`). Lines starting with `#` or empty lines are ignored.

Example `skiplist.txt`:
```
# Legacy tests
tests/legacy

# Deprecated test files
tests/test_old_feature.py
```

## Environment Variables

- `MAESTRO_TEST_JOBS`: Default worker count (default: cpu_count - 1)
- `MAESTRO_TEST_PROFILE`: Default speed profile (default: all)
- `MAESTRO_TEST_CHECKPOINT`: Checkpoint file path (default: auto-generated in /tmp)
- `MAESTRO_TEST_RESUME_FROM`: Resume from this checkpoint file
- `MAESTRO_TEST_SKIPLIST`: Default skiplist file path (default: tools/test/skiplist.txt)
- `PYTHON_BIN`: Python binary to use (default: auto-detected python3 or python)

## Implementation Details

### Virtual Environment

The runner creates/uses a virtual environment at `.venv/` in the repo root. Dependencies are installed from `requirements-dev.txt`.

### Checkpoint Plugin

Checkpoint/resume functionality is implemented via a pytest plugin at `tools/test/pytest_checkpoint_plugin.py`. The plugin:

1. Collects PASSED test nodeids during execution
2. Writes them to the checkpoint file in `pytest_sessionfinish` hook
3. Filters test collection based on resume checkpoint in `pytest_collection_modifyitems` hook

### Speed Profile Implementation

Speed profiles are implemented using pytest markers and the `-m` marker expression flag:

- `--profile fast`: `-m "fast and not legacy"`
- `--profile medium`: `-m "(fast or medium) and not legacy"`
- `--profile slow`: `-m "slow and not legacy"`
- `--profile all`: `-m "not legacy"`

The default `pytest.ini` configuration excludes legacy and slow tests by default. The runner overrides this for different profiles.

## Troubleshooting

### xdist not available

If you see "Note: xdist not available; running serial", ensure `pytest-xdist` is installed:

```bash
.venv/bin/python -m pip install pytest-xdist
```

It should be installed automatically from `requirements-dev.txt`.

### No tests collected for fast/slow profile

If a profile collects no tests, it means no tests have that marker. This is expected if tests aren't marked yet. Add markers to tests:

```python
import pytest

@pytest.mark.fast
def test_quick_unit_test():
    assert 1 + 1 == 2

@pytest.mark.slow
def test_integration_with_filesystem():
    # ... heavy I/O test
    pass
```

### Checkpoint file not found

If resuming fails with "Resume checkpoint file not found", ensure the path is correct. The checkpoint path is printed in the test summary after each run.

## Upgrading pinned deps

1. Update the pytest pin in `requirements-dev.txt` (the runner reads it when present).
2. Re-run the tests. If you need a clean reinstall, delete `.venv/` and run `bash tools/test/run.sh` again.

## Contributing

When adding new tests:

1. Mark tests with appropriate speed markers (`@pytest.mark.fast`, `@pytest.mark.medium`, `@pytest.mark.slow`)
2. Use `@pytest.mark.legacy` for deprecated code paths
3. Ensure tests pass in parallel (avoid shared state, use fixtures for isolation)
4. Run with `--profile-report` periodically to identify slow tests

See `docs/workflows/v3/reports/test_policy.md` for full test policy guidance.

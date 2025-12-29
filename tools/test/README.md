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

### 2. Speed Profiles (Timing-Based)

Filter tests by execution speed using **actual timing data** from previous runs. The runner automatically saves timing data and uses it to classify tests.

```bash
# Run only fast tests (<0.1s based on last run)
bash tools/test/run.sh --profile fast

# Run fast + medium tests (<1.0s based on last run)
bash tools/test/run.sh --profile medium

# Run only slow tests (>1.0s based on last run)
bash tools/test/run.sh --profile slow

# Run all tests (default, still excludes legacy)
bash tools/test/run.sh --profile all

# Set default via environment
MAESTRO_TEST_PROFILE=fast bash tools/test/run.sh
```

**How it works:**
1. Every test run automatically saves timing data to `docs/workflows/v3/reports/test_timing_latest.txt`
2. Speed profiles use **actual measured performance** from the timing file:
   - `fast`: Tests that ran in <0.1s
   - `medium`: Tests that ran in 0.1s-1.0s
   - `slow`: Tests that ran in >1.0s
3. If no timing data exists yet, falls back to pytest markers (`@pytest.mark.fast`, etc.)

**Benefits:**
- No manual test marking required
- Automatically adapts to actual performance
- Tests are reclassified as code changes affect performance
- Timing data committed to git tracks performance trends

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

**Timing data is automatically saved on every test run** to `docs/workflows/v3/reports/test_timing_latest.txt`. This enables timing-based speed profiles and performance tracking.

```bash
# Every run saves timing data (default: top 10 slowest)
bash tools/test/run.sh

# Show more detail: top 25 slowest tests
bash tools/test/run.sh --profile-report

# Combine with other options
bash tools/test/run.sh --profile medium --profile-report -j 8

# Check the saved report
cat docs/workflows/v3/reports/test_timing_latest.txt
```

**Report includes:**
- Slowest test durations with relative paths (10 by default, 25 with --profile-report)
- Warnings for tests slower than 1.0s
- Test run metadata (timestamp, duration, workers, profile)
- Used by `--profile fast/medium/slow` to select tests

**Slowest-First Ordering:**

When timing data exists, tests are automatically run in slowest-first order. This helps detect failures in slow tests earlier (fail-fast strategy).

```bash
# When timing data exists, tests run slowest-first automatically
bash tools/test/run.sh --profile all

# Output shows: "Ordering: slowest first (N tests)"
```

This feature is enabled by default when timing data is available. Slowest tests are prioritized to surface failures sooner, saving development time.

### 5. Test Timeouts

Kill tests that run too long to prevent hanging test suites.

```bash
# Kill any test that runs longer than 5 seconds
bash tools/test/run.sh --timeout 5

# Combine with other options
bash tools/test/run.sh --timeout 10 --profile slow

# Set default via environment
MAESTRO_TEST_TIMEOUT=30 bash tools/test/run.sh
```

**How it works:**
- Uses `pytest-timeout` to enforce per-test time limits
- Timed-out tests are marked as FAILED
- Works with profiling - timeout is recorded in timing report
- Timeout method: thread-based (safe for most tests)

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

# Run ONLY the tests in the skiplist (inverse behavior)
bash tools/test/run.sh --skipped

# Set default via environment
MAESTRO_TEST_SKIPLIST=/path/to/skiplist.txt bash tools/test/run.sh
```

**Skiplist file format**: One pattern per line. Can be file paths, directories, or specific test nodeids. Lines starting with `#` or empty lines are ignored.

Example `skiplist.txt`:
```
# Legacy tests
tests/legacy

# Deprecated test files
tests/test_old_feature.py

# Specific tests that depend on external data
tests/test_integration.py::test_requires_external_data
```

### Running Skipped Tests Only

Use `--skipped` to run ONLY the tests listed in the skiplist (useful for testing non-portable or slow tests):

```bash
# Run only the tests normally skipped
bash tools/test/run.sh --skipped

# Combine with other options
bash tools/test/run.sh --skipped --timeout 60 -v
```

## Environment Variables

- `MAESTRO_TEST_JOBS`: Default worker count (default: cpu_count - 1)
- `MAESTRO_TEST_PROFILE`: Default speed profile (default: all)
- `MAESTRO_TEST_CHECKPOINT`: Checkpoint file path (default: auto-generated in /tmp)
- `MAESTRO_TEST_RESUME_FROM`: Resume from this checkpoint file
- `MAESTRO_TEST_SKIPLIST`: Default skiplist file path (default: tools/test/skiplist.txt)
- `MAESTRO_TEST_TIMEOUT`: Default test timeout in seconds (default: none)
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

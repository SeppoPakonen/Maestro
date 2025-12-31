# Maestro Test Runner

Canonical test runner for the Maestro project with support for parallel execution, speed profiles, and checkpoint/resume functionality.

## Why this exists

Maestro uses a global `~/venv/` so `pytest -q` does not depend on system Python packages. The canonical entrypoint is `tools/test/run.sh`, which creates the venv if needed, installs the minimal test dependencies, and runs pytest.

**Pytest direct invocation**: Running `pytest -q` directly should behave similarly to the runner for the default portable subset. Both exclude legacy and non-portable tests via `conftest.py` hooks and `pytest.ini` configuration. Use `bash tools/test/verify_portable_subset.sh` to verify alignment.

## Quick Start

```bash
# Run tests with default settings (parallel, excludes legacy/tui)
bash tools/test/run.sh

# Run with verbose output
bash tools/test/run.sh -v

# Show help
bash tools/test/run.sh --help
```

## Help Smoke Check

The CLI help smoke test ensures `--help` and bare keywords stay fast and non-interactive:

```bash
bash tools/smoke/help_fast_smoke.sh
```

## Features

### 1. Configuration Display

The runner prints a summary before running tests (Python, pytest, selection mode, profile, markers, workers, and checkpoint path). This makes it easy to verify defaults and selection logic.

To print the resolved pytest command without running tests:

```bash
bash tools/test/run.sh --print-pytest-cmd --fast tests/test_subwork_stack.py
```
### 2. Parallel Execution

By default, tests run in parallel using `pytest-xdist` with `cpu_count - 1` workers when available.

```bash
# Use default parallelism (cpu_count - 1)
bash tools/test/run.sh

# Use 4 workers
bash tools/test/run.sh -j 4

# Disable parallelism (run serial)
bash tools/test/run.sh -j 1
```

### 3. Serial-only Tests (No Concurrency)

Tests marked with `@pytest.mark.serial` must run after the main lane and are forced to run with `-n0`:

```python
@pytest.mark.serial
def test_some_global_state():
    ...
```

### 4. Speed Profiles (Marker-Based)

Speed profiles are marker expressions applied via `-m`:

- `--fast`: `not slow and not legacy and not tui and not integration`
- `--medium`: `not legacy and not tui` (default)
- `--slow`: `slow and not legacy and not tui`
- `--all`: `not legacy`

```bash
# Run only fast tests
bash tools/test/run.sh --fast

# Run medium (default) profile
bash tools/test/run.sh --medium

# Run only slow tests
bash tools/test/run.sh --slow

# Run all non-legacy tests
bash tools/test/run.sh --all
```

### 5. Checkpoint & Resume

The runner writes a checkpoint file after each run containing PASSED test nodeids and metadata. Use `--resume-from` to skip already-passed tests.

```bash
# First run
bash tools/test/run.sh -x --maxfail=1
# Output: Checkpoint written: /tmp/maestro_pytest_checkpoint_YYYYMMDD_HHMMSS.txt

# Resume (skips previously passed tests)
bash tools/test/run.sh --resume-from /tmp/maestro_pytest_checkpoint_YYYYMMDD_HHMMSS.txt -x --maxfail=1
```

Each run also saves a full pytest log and a failures list under `/tmp`:

- `/tmp/maestro_pytest_run_YYYYMMDD_HHMMSS.log`
- `/tmp/maestro_pytest_failures_YYYYMMDD_HHMMSS.txt`

Use the failures list to rerun just the failed tests:

```bash
bash tools/test/run.sh -q $(cat /tmp/maestro_pytest_failures_YYYYMMDD_HHMMSS.txt)
```

To self-check failure extraction, run a known failing nodeid and confirm it appears in the failures file.

### 6. Profiling & Slow-Test Report

Use `--profile` to capture pytest duration output and write reports:

- `docs/workflows/v3/reports/test_durations_latest.txt`
- `docs/workflows/v3/reports/test_slow_candidates.md`

```bash
bash tools/test/run.sh --profile tests/test_subwork_stack.py
```

### 7. Git Lock Preflight

The runner checks for `.git/index.lock` and exits with diagnostics if present. Override only if you know what you are doing:

```bash
bash tools/test/run.sh --ignore-git-lock
```

Use `--git-check` to include git metadata in the runner configuration output.
During test execution, the runner also detects newly created git index locks and reports the offending test. Disable with:

```bash
bash tools/test/run.sh --no-git-lock-detect
```

### 8. Git-Dependent Tests

Tests that execute git commands are opt-in. Enable them with:

```bash
MAESTRO_TEST_ALLOW_GIT=1 bash tools/test/run.sh
```

## Pass-Through Arguments

Unrecognized arguments are passed directly to pytest:

```bash
# Stop on first failure
bash tools/test/run.sh -x

# Run specific test file
bash tools/test/run.sh tests/test_ai_cache.py

# Run specific test function
bash tools/test/run.sh tests/test_ai_cache.py::test_function_name

# Run tests matching keyword
bash tools/test/run.sh -k work_command
```

Use `--` to separate runner options from pytest options if needed:

```bash
bash tools/test/run.sh --fast -- -k work_command
```

## Skiplist Management

The runner supports skipping tests via a skiplist file containing patterns to ignore.

```bash
# Use custom skiplist
bash tools/test/run.sh --skiplist my_custom_skiplist.txt

# Disable skiplist (run all tests except legacy/tui)
bash tools/test/run.sh --skiplist ""

# Run only the tests listed in the skiplist
bash tools/test/run.sh --skipped
```

## Environment Variables

- `MAESTRO_TEST_JOBS`: Default worker count
- `MAESTRO_TEST_PROFILE`: Default speed profile (fast|medium|slow|all, default: medium)
- `MAESTRO_TEST_CHECKPOINT`: Checkpoint file path (default: auto-generated in /tmp)
- `MAESTRO_TEST_RESUME_FROM`: Resume from this checkpoint file
- `MAESTRO_TEST_SKIPLIST`: Default skiplist file path
- `MAESTRO_TEST_TIMEOUT`: Default test timeout in seconds
- `MAESTRO_TEST_ALLOW_GIT`: Enable tests that perform git operations
- `MAESTRO_DEBUG_HANG`: Dump Python stack traces if CLI subprocesses hang (prints to stderr)
- `PYTHON_BIN`: Python binary to use (default: auto-detected python3 or python)

## Troubleshooting

### xdist not available

If you see "Note: xdist not available; running serial", ensure `pytest-xdist` is installed:

```bash
.venv/bin/python -m pip install pytest-xdist
```

### Resume file not found

If resuming fails with "Resume checkpoint file not found", ensure the path is correct. The checkpoint path is printed in the test summary after each run.

## Contributing

When adding new tests:

1. Mark tests with appropriate speed markers (`@pytest.mark.fast`, `@pytest.mark.medium`, `@pytest.mark.slow`)
2. Use `@pytest.mark.legacy` for deprecated code paths
3. Use `@pytest.mark.tui` for TUI-heavy tests
4. Avoid shared state; use fixtures for isolation

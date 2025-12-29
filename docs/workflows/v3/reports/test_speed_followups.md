# Test Speed Optimization Follow-ups

Generated: 2025-12-29

## Purpose

This report identifies opportunities to improve test execution speed in the Maestro test suite. With the new parallel test runner and speed profiles, optimizing slow tests will significantly improve development velocity.

## How to Profile Tests

To identify slow tests in your area:

```bash
# Get timing report for all tests
bash tools/test/run.sh --profile-report > timing_report.txt

# Profile specific test files
bash tools/test/run.sh --profile-report tests/test_*.py

# Profile only slow-marked tests
bash tools/test/run.sh --profile slow --profile-report
```

## General Optimization Strategies

### 1. Isolate Filesystem Usage

**Problem**: Tests that write to real filesystem locations are slow and can have race conditions in parallel execution.

**Solution**:
- Use `tmp_path` fixture (pytest built-in) for all test file operations
- Avoid writing to `docs/`, `maestro/`, or other repo directories during tests
- Use `monkeypatch` to redirect file operations to temp directories

**Example**:
```python
# Before (slow, not parallel-safe)
def test_config_file():
    with open("maestro/config.json", "w") as f:
        f.write('{"test": true}')
    # ... test code

# After (fast, parallel-safe)
def test_config_file(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text('{"test": true}')
    # ... test code
```

### 2. Reduce Subprocess Calls

**Problem**: Spawning subprocesses (CLI invocations, git commands, etc.) is expensive (100-500ms overhead per call).

**Solution**:
- Mock subprocess calls when testing business logic
- Use in-process function calls instead of CLI invocations where possible
- Share subprocess results across tests via fixtures with `scope="module"` or `scope="session"`
- For integration tests that must use subprocesses, mark with `@pytest.mark.slow`

**Example**:
```python
# Before (slow, spawns process every test)
def test_git_status():
    result = subprocess.run(["git", "status"], capture_output=True)
    assert result.returncode == 0

# After (fast, mocked)
def test_git_status(monkeypatch):
    mock_run = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr("subprocess.run", mock_run)
    # ... test code
```

### 3. Share Expensive Fixtures

**Problem**: Creating fixtures (databases, config files, parsed data) for every test is wasteful.

**Solution**:
- Use `scope="module"` or `scope="session"` for fixtures that don't mutate
- For mutable fixtures, use `scope="module"` and deep copy in each test
- Cache expensive operations (file parsing, AI model initialization) at module level

**Example**:
```python
# Before (parsed every test)
@pytest.fixture
def config_data():
    return yaml.safe_load(Path("test_config.yaml").read_text())

# After (parsed once per module)
@pytest.fixture(scope="module")
def config_data():
    return yaml.safe_load(Path("test_config.yaml").read_text())
```

### 4. Minimize AI/External Service Calls

**Problem**: Tests calling real AI APIs or external services are extremely slow (seconds per call) and flaky.

**Solution**:
- Use fake/mock implementations for AI runners in tests
- Record real API responses once, replay in tests (golden files)
- Mark tests requiring real API calls with `@pytest.mark.slow` and `@pytest.mark.integration`

**Example**:
```python
# Good: Use fake runner
def test_ai_manager(tmp_path):
    runner = FakeAIRunner(preset_response="test output")
    manager = AIManager(runner=runner, state_dir=tmp_path)
    result = manager.run_query("test")
    assert result == "test output"
```

### 5. Avoid Unnecessary Repo Scanning

**Problem**: Tests that scan the entire repo structure (`repo.scanner`, recursive glob, etc.) are slow (100-500ms).

**Solution**:
- Use minimal test fixture directories instead of full repo
- Mock scanner results for unit tests
- Mark integration tests that need full repo scan with `@pytest.mark.slow`

### 6. Parallelize-Safe State Management

**Problem**: Tests that share global state or write to shared locations fail in parallel mode.

**Solution**:
- Use unique temp directories per test: `tmp_path / f"test_{uuid.uuid4()}"`
- Avoid module-level state changes
- Use `monkeypatch` to isolate environment variables and global config

## Specific Test Categories Needing Optimization

### High Priority (> 1s per test)

These tests should be marked `@pytest.mark.slow` and optimized:

1. **AI integration tests** (`test_ai_manager_*.py`, `test_discuss_*.py`)
   - Use fake runners instead of real AI calls
   - Cache expensive setup (session fixtures)

2. **Repo hub tests** (`test_hub_integration.py`, `test_repo_workflow_*.py`)
   - Use minimal fixture repos, not full clones
   - Mock external hub operations

3. **TUI smoke tests** (`test_tui_smoke_*.py`)
   - Consider if TUI tests are needed in every run
   - May be candidates for manual/nightly only

### Medium Priority (0.1s - 1s per test)

Mark with `@pytest.mark.medium` if not already:

1. **File parsing tests** that read large files
   - Cache parsed results at module scope

2. **Subprocess-based tests** (git operations, CLI invocations)
   - Mock where possible, mark slow where not

### Low Priority (< 0.1s per test)

Mark with `@pytest.mark.fast` to enable fast iteration:

1. **Pure unit tests** (dataclass validation, string parsing, etc.)
2. **Mock-based tests** (no I/O)
3. **In-memory data structure tests**

## Action Items

1. **Mark existing tests** with speed markers:
   ```bash
   # Audit all tests
   grep -r "^def test_" tests/ | wc -l

   # Count currently marked tests
   grep -r "@pytest.mark.fast" tests/ | wc -l
   grep -r "@pytest.mark.slow" tests/ | wc -l
   ```

2. **Profile and optimize top 10 slowest tests**:
   ```bash
   bash tools/test/run.sh --profile-report | tee speed_report.txt
   # Review "slowest 25 durations" section
   # Target tests > 1s for optimization
   ```

3. **Verify parallel safety**:
   ```bash
   # Run tests multiple times to catch flaky parallel issues
   for i in {1..5}; do bash tools/test/run.sh -j 8; done
   ```

4. **Set up CI speed monitoring**:
   - Run `--profile-report` in CI
   - Fail if any unmarked test takes > 1s
   - Track total suite time over commits

## Success Metrics

Current baseline (to be measured):
- Total suite time (all tests): TBD
- Fast profile time (<0.1s tests only): TBD
- Slow test count: TBD

Target goals:
- Fast profile: < 10s for full run
- Medium profile: < 60s for full run
- All tests: < 5min for full run
- 90% of tests marked with speed markers within 2 sprints

## Resources

- Test runner documentation: `tools/test/README.md`
- Test policy: `docs/workflows/v3/reports/test_policy.md`
- pytest-xdist docs: https://pytest-xdist.readthedocs.io/
- pytest fixture scopes: https://docs.pytest.org/en/stable/how-to/fixtures.html#scope

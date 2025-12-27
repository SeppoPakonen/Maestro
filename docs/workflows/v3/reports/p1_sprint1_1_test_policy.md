# Maestro Test Policy

Version: P1 Sprint 1.1
Date: 2025-12-27

## Overview

This document defines the test execution policy for the Maestro project, ensuring that tests run reliably by default on any reasonable dev machine without requiring exotic dependencies.

## Test Markers

We use pytest markers to classify tests:

- `legacy`: Tests for deprecated/removed code paths (skipped by default)
- `pexpect`: Tests requiring the pexpect module (skipped if not installed)
- `slow`: Tests that take significant time to run
- `integration`: Integration tests (may require external resources)

## Default Test Execution

### Quick Run (Default)
```bash
pytest -q
```

**Behavior**:
- Runs all non-legacy tests
- Skips tests requiring pexpect if not installed
- Should complete quickly (< 10 seconds ideally)
- Should pass on a clean dev environment without exotic dependencies

### Run Including Legacy Tests
```bash
pytest -q -m ""
# or
pytest -q --deselect-marker=""
```

**Behavior**:
- Runs ALL tests including legacy
- Will fail if deprecated modules/functions are missing
- Use for validating migrations or understanding old behavior

### Run Only Legacy Tests
```bash
pytest -q -m "legacy"
```

**Behavior**:
- Runs only legacy tests
- Useful for determining which old tests need updating

### Run With Pexpect Tests
```bash
# Install pexpect first if needed
pip install pexpect

# Then run
pytest -q
```

**Behavior**:
- Automatically includes pexpect tests if pexpect is installed
- No special flags needed

## Test Organization

### Active Tests (Run by Default)

These are tests for current, maintained code paths:
- All v3 CLI tests
- Core functionality tests
- Regression tests for current features

**Location**: Primarily in `tests/` and package subdirectories
**Requirement**: Must run by default and pass

### Legacy Tests (Skipped by Default)

These are tests for deprecated/removed functionality:
- Old conversion pipeline tests
- Deprecated CLI command tests
- Tests for removed modules (orchestrator_cli, conversion_memory, etc.)

**Location**: Listed in `conftest.py:LEGACY_TEST_FILES`
**Requirement**: Skipped by default, may fail if run

### Optional Dependency Tests

Tests that require non-core dependencies:
- Codex wrapper tests (requires pexpect)
- TUI smoke tests (some require pexpect)

**Location**: Listed in `conftest.py:PEXPECT_TEST_PATTERNS`
**Requirement**: Skipped automatically if dependency missing

## Adding New Tests

### For Current Features
1. Write test in appropriate location
2. Ensure it runs with `pytest -q` (no special markers)
3. No extra dependencies unless absolutely necessary
4. Should be fast (< 1 second per test ideally)

### For Optional Features
1. Add appropriate marker (@pytest.mark.pexpect, etc.)
2. Use pytest.importorskip() for missing deps
3. Document in this file if adding new marker

### Updating Legacy Tests
1. If updating old test to work with new code:
   - Remove from `LEGACY_TEST_FILES` in conftest.py
   - Ensure it passes with current code
2. If test is truly obsolete:
   - Keep it marked as legacy
   - Or delete it entirely (preferred if no historical value)

## CI/CD Implications

### Pre-commit / Local Development
```bash
pytest -q
```
Should pass quickly on every commit.

### Full CI Pipeline
```bash
# Test default suite
pytest -q

# Optionally test with pexpect if available in CI
pip install pexpect
pytest -q

# Verify legacy tests are properly isolated
pytest -q -m "legacy" --co  # Collect only, verify they're marked
```

### Release Validation
Consider running full suite including legacy to catch regressions in migration paths:
```bash
pytest -q -m ""
```

## Configuration Files

- `pytest.ini`: Marker definitions and default options
- `conftest.py`: Automatic test marking logic
- This file: Test execution policy

## Future Improvements

1. Add `slow` marker for tests > 1 second
2. Add `integration` marker for tests requiring external resources
3. Consider separate `tests/legacy/` directory instead of marker
4. Add test coverage requirements
5. Add performance benchmarks for critical paths

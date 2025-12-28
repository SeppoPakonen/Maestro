# Test Command Truth Policy

## Overview

This document defines the policy for aligning the Maestro test suite with the **v3 runbook CLI command surface**. The goal is to ensure that tests enforce the current, documented CLI behavior and do not drive implementation toward legacy or deleted features.

## Canonical Source of Truth

The canonical source of allowed CLI commands is:

```
docs/workflows/v3/reports/allowed_commands.normalized.txt
```

This file is extracted from the v3 runbooks and represents the **complete, normalized CLI surface** that Maestro v3 is expected to support.

## Policy Rules

### 1. Test Command Compliance

**Tests must only reference CLI commands present in `allowed_commands.normalized.txt`.**

**Exception:** Unit tests of internal helpers that don't directly map to CLI commands (e.g., parser utilities, data structure tests) are exempt from this rule.

### 2. Handling Violations

When a test references a CLI command **not** in the allowed list:

1. **Preferred:** Mark the test with the `@pytest.mark.legacy` marker
2. **Alternative:** Rename the test file with a `legacy_` prefix
3. **If clearly obsolete:** Delete the test and document the rationale in the audit report

### 3. Legacy Test Isolation

Tests marked as `legacy` are **excluded from default test runs** via pytest configuration:

```ini
addopts = -m "not legacy and not slow"
```

This ensures that `pytest -q` only runs tests that align with the v3 CLI contract.

### 4. Test Discovery and Audit

An automated audit tool (`tools/test_audit/audit_tests_against_allowed_commands.sh`) scans the test suite for command compliance and generates a report:

```
docs/workflows/v3/reports/test_command_audit.md
```

## Rationale

**Problem:** Tests that reference deleted or non-existent commands can:
- Force reimplementation of features that were intentionally removed
- Create confusion about what the CLI should support
- Make the test suite unreliable and difficult to maintain

**Solution:** By anchoring tests to the runbook-extracted command truth, we ensure:
- Test failures indicate actual regressions in v3 behavior
- `pytest -q` becomes a meaningful, fast signal of system health
- No "feature resurrection" from legacy test expectations

## Workflow

1. **Extract commands from runbooks** → `allowed_commands.normalized.txt`
2. **Run audit tool** → identify non-compliant tests
3. **Quarantine/remove** → mark legacy or delete obsolete tests
4. **Verify** → `pytest -q` runs cleanly with only v3-aligned tests

## Maintenance

- When adding new CLI commands, update the runbooks first, then re-extract `allowed_commands.normalized.txt`
- Re-run the audit tool periodically (or in CI) to catch new violations
- Document any intentional exceptions in this policy document

---

**Last Updated:** 2025-12-28
**Policy Version:** 1.0

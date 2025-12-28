# CLI Command Deprecation Policy

**Last Updated:** 2025-12-28
**Policy Version:** 1.0

## Overview

This document defines the deprecation status of Maestro CLI commands that exist in the codebase but are not part of the v3 runbook command surface.

The canonical command surface is defined in:
```
docs/workflows/v3/reports/allowed_commands.normalized.txt
```

## Deprecated Commands

The following commands are marked as **LEGACY** and should not be used in new workflows or tests:

### 1. `maestro session` (LEGACY)

**Status:** Deprecated in favor of `maestro wsession`

**Reason:**
- The original `session` command was designed for task session management
- Replaced by the more comprehensive `wsession` (work session) command
- `wsession` provides better session tracking, breadcrumbs, timelines, and statistics

**Migration Path:**
- `maestro session list` → `maestro wsession list`
- `maestro session breadcrumbs <id>` → `maestro wsession breadcrumbs <id>`
- `maestro session timeline <id>` → `maestro wsession timeline <id>`
- `maestro session stats <id>` → `maestro wsession stats <id>`

**Code Status:**
- Command still registered in `maestro/modules/cli_parser.py` (line 230)
- Marked as "Legacy session management" in help text
- Handlers still functional but not recommended for new use

**Test Status:**
- Legacy tests moved to `tests/legacy/` directory
- Tests are excluded from default `pytest -q` runs via pytest.ini

---

### 2. `maestro understand` (LEGACY)

**Status:** Deprecated / Functionality absorbed into other commands

**Reason:**
- Original `understand` command was used for code understanding and dump generation
- Functionality merged into repo/runbook/workflow analysis commands
- Not part of v3 runbook command surface

**Migration Path:**
- `maestro understand dump` → Use `maestro repo show` or `maestro runbook export`
- Code understanding → Use `maestro ai qwen` or `maestro ai claude` for interactive analysis

**Code Status:**
- Command still registered via `add_understand_parser()` in CLI parser
- Handler: `maestro.commands.plan.handle_understand_dump()`
- Maintained for backward compatibility only

**Test Status:**
- `test_understand_dump.py` moved to `tests/legacy/`
- Excluded from default test runs

---

### 3. `maestro resume` (LEGACY)

**Status:** Deprecated / Functionality integrated into `maestro discuss`

**Reason:**
- The standalone `resume` command was used to resume AI discussion sessions
- Functionality now integrated into `maestro discuss --resume` flag
- Not a top-level command in v3 runbook structure

**Migration Path:**
- `maestro resume` → `maestro discuss --resume`

**Code Status:**
- Command registered in `maestro/modules/cli_parser.py` (line 282)
- No dedicated handler; likely redirects to discuss command

**Test Status:**
- No dedicated tests found (feature may be absorbed)

---

### 4. `maestro rules` (LEGACY)

**Status:** Deprecated / To be merged into runbook/workflow operations

**Reason:**
- Original `rules` command managed build/test rules
- Functionality being consolidated into runbook conventions and workflow operations
- Overlaps with `maestro repo conventions` and `maestro runbook` commands

**Current Use:**
- `maestro rules list` - List active rules
- `maestro rules edit` - Edit rules file

**Migration Path:**
- `maestro rules list` → `maestro repo conventions`
- `maestro rules edit` → Manual editing of repo configuration files

**Code Status:**
- Command still registered in `maestro/modules/cli_parser.py` (line 260)
- Handlers exist but not documented in v3 runbooks

**Test Status:**
- `test_reactive_rules.py` moved to `tests/legacy/`
- Excluded from default test runs

---

## Deprecation Timeline

**Current Status (2025-12-28):**
- All deprecated commands are still functional
- Marked as LEGACY in this documentation
- Tests quarantined to `tests/legacy/` directory
- Not documented in v3 runbooks

**Future Actions:**
1. **Phase 1 (Q1 2025):** Documentation and user migration support
   - Add deprecation warnings to command help text
   - Update all user-facing documentation
   - Provide migration examples in runbooks

2. **Phase 2 (Q2 2025):** Runtime warnings
   - Add console warnings when legacy commands are invoked
   - Log deprecation usage for monitoring

3. **Phase 3 (Q3 2025+):** Potential removal
   - Evaluate usage metrics
   - Consider complete removal if no active users
   - OR maintain as hidden commands with explicit opt-in

---

## Policy Enforcement

### For Tests
- Legacy command tests MUST be in `tests/legacy/` directory OR marked with `@pytest.mark.legacy`
- Default `pytest -q` excludes legacy tests via pytest.ini configuration
- See: `docs/workflows/v3/reports/test_command_truth_policy.md`

### For Code
- New features MUST NOT depend on deprecated commands
- Code reviews should flag usage of deprecated commands
- Existing code may continue using deprecated commands until formal removal

### For Documentation
- Runbooks and user guides MUST NOT reference deprecated commands
- Deprecated commands documented only in this DEPRECATION.md file
- Migration paths must be clearly documented

---

## Related Documents

- [Test Command Truth Policy](../reports/test_command_truth_policy.md)
- [CLI Surface Audit Report](../reports/cli_surface_audit.md)
- [Allowed Commands List](../reports/allowed_commands.normalized.txt)

---

## Questions / Feedback

For questions about command deprecation or migration support:
1. Check the migration paths documented above
2. Review the v3 runbooks for current command usage
3. Consult the CLI surface audit report for full command inventory

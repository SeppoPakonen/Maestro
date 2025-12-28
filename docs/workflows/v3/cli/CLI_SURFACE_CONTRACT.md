# CLI Surface Contract - v3 Canonical

**Last Updated:** 2025-12-28
**Policy Version:** 1.0
**Kill Switch:** `MAESTRO_ENABLE_LEGACY` environment variable

## Overview

This document is the **single source of truth** for the Maestro v3 CLI surface. It defines:

1. **Canonical commands** - Commands that should appear in normal mode (default behavior)
2. **Legacy commands** - Deprecated commands hidden by default, accessible via kill switch
3. **Migration paths** - How to transition from legacy to canonical commands
4. **Kill switch behavior** - How `MAESTRO_ENABLE_LEGACY` controls command visibility

### Purpose

- Ensure runbook-derived CLI commands are the **actual** primary interface
- Prevent accidental usage of deprecated commands in new workflows
- Provide clear migration guidance for existing code
- Lock the CLI contract via automated testing

### References

- Canonical commands extracted from: `docs/workflows/v3/reports/allowed_commands.normalized.txt`
- Audit report: `docs/workflows/v3/reports/cli_surface_audit.md`
- Audit tool: `tools/test_audit/audit_cli_surface_against_allowed_commands.py`
- Deprecation policy: `docs/workflows/v3/cli/DEPRECATION.md`

---

## Command Taxonomy

Commands are organized into 5 categories:

### 1. Core Namespace Commands

**Purpose:** Fundamental project structure and tracking.

- `maestro init` - Initialize Maestro project (repo truth under `./docs/maestro/`)
- `maestro track add` - Create new work track
- `maestro phase add` - Create new phase within track
- `maestro task add` - Create new task within phase
- `maestro plan` - Manage plans and plan operations

### 2. Workspace Commands

**Purpose:** Session management and AI interaction.

- `maestro work task` - Start work session for task
- `maestro work resume` - Resume work session
- `maestro work close` - Close work session
- `maestro wsession list` - List work sessions
- `maestro wsession show` - Show work session details
- `maestro wsession breadcrumb add` - Add breadcrumb to session (requires cookie)
- `maestro discuss` - AI discussion router (auto-detects context)
- `maestro discuss --context {task|phase|track|repo|issues|runbook|workflow|solutions|global}` - Explicit context
- `maestro discuss resume` - Resume previous discussion session

### 3. Repository & Build Commands

**Purpose:** Repository analysis, configuration, and build execution.

- `maestro repo resolve` - Resolve repository structure (lite or deep)
- `maestro repo show` - Show repository information (packages, entry-points, etc.)
- `maestro repo conf show` - Show repository configuration
- `maestro repo conf select-default-target` - Set default build target
- `maestro repo conventions check` - Check naming conventions
- `maestro repo hub find` - Find packages in hub
- `maestro make` - Execute build with repoconf context
- `maestro build` - Legacy alias for `make`

### 4. Authoring & Observability Commands

**Purpose:** Runbook/workflow authoring, issue tracking, logging.

**Runbook Authoring:**
- `maestro runbook add` - Create new runbook
- `maestro runbook step-add` - Add step to runbook
- `maestro runbook export` - Export runbook to Markdown/PlantUML

**Workflow Authoring:**
- `maestro workflow init` - Create workflow from runbook
- `maestro workflow node add` - Add node to workflow
- `maestro workflow edge add` - Add edge between nodes
- `maestro workflow validate` - Validate workflow structure
- `maestro workflow render` - Render workflow visualization

**Issues & Solutions:**
- `maestro issues list` - List issues
- `maestro issues add` - Add issue (from log scan or manual)
- `maestro issues accept` - Accept issue as valid
- `maestro issues ignore` - Ignore issue with reason
- `maestro solutions match` - Match solutions to issues

**Logging & Observability:**
- `maestro log scan` - Scan build/run logs for errors
- `maestro log list` - List log scans
- `maestro log show` - Show scan details

### 5. Auxiliary Commands

**Purpose:** AI engines, settings, caching, TU/AST operations.

**AI Engines:**
- `maestro ai qwen` - Qwen AI engine
- `maestro ai claude` - Claude AI engine
- `maestro ai gemini` - Gemini AI engine
- `maestro ai codex` - Codex AI engine

**Translation Units (TU/AST):**
- `maestro tu build` - Build translation units
- `maestro tu query` - Query AST (symbol lookup)
- `maestro tu autocomplete` - IDE autocomplete assistance
- `maestro tu refactor` - Refactor code (rename, extract)

**Settings & Cache:**
- `maestro settings set` - Set configuration values
- `maestro cache stats` - Show AI cache statistics
- `maestro cache show` - Show cache entry details
- `maestro cache prune` - Prune old cache entries

**Operations:**
- `maestro ops commit create` - Create commit from operations
- `maestro ops commit suggest` - Suggest commit message

---

## Kill Switch: MAESTRO_ENABLE_LEGACY

### Overview

The `MAESTRO_ENABLE_LEGACY` environment variable controls visibility and availability of deprecated legacy commands.

**Purpose:**
- Hide legacy commands by default (cleaner, forward-focused CLI)
- Provide backward compatibility for existing scripts/workflows
- Prevent accidental usage in new code
- Enable gradual migration with explicit opt-in

### Behavior

#### Default Mode (unset or `MAESTRO_ENABLE_LEGACY=0`)

**Commands:**
- Legacy commands **NOT** registered in parser
- `maestro session --help` fails with argparse error (command not found)
- `maestro --help` does NOT list legacy commands

**Error Message Example:**
```
$ maestro session list
Error: 'session' command is not available.
Use: maestro wsession instead.
To enable legacy commands: export MAESTRO_ENABLE_LEGACY=1
```

**Use Cases:**
- New projects starting with v3 runbooks
- CI/CD pipelines enforcing canonical commands only
- Developer onboarding (no exposure to deprecated commands)

#### Legacy Mode (`MAESTRO_ENABLE_LEGACY=1`)

**Commands:**
- Legacy commands registered with `[DEPRECATED]` markers
- All 5 legacy commands functional (session, understand, resume, rules, root)
- `maestro --help` lists legacy commands marked as deprecated

**Warning Banner Example:**
```
╔════════════════════════════════════════════════════════════════╗
║  DEPRECATED COMMAND: maestro session                          ║
╠════════════════════════════════════════════════════════════════╣
║  This command is deprecated and will be removed in a future   ║
║  release. Please use the replacement command instead:         ║
║                                                                ║
║  → maestro wsession                                           ║
╚════════════════════════════════════════════════════════════════╝
```

**Use Cases:**
- Backward compatibility for existing scripts
- Gradual migration from legacy to canonical commands
- Testing that new code doesn't depend on legacy commands

### Configuration

Set the environment variable before running maestro:

```bash
# Enable legacy commands (temporary)
export MAESTRO_ENABLE_LEGACY=1
maestro session list  # Works with deprecation warning

# Disable legacy commands (default)
unset MAESTRO_ENABLE_LEGACY
maestro session list  # Error: command not available

# Explicit disable
export MAESTRO_ENABLE_LEGACY=0
maestro session list  # Error: command not available
```

**Accepted values:**
- `1`, `true`, `yes` → Legacy enabled
- `0`, `false`, `no`, unset → Legacy disabled (default)

---

## Canonical Command List

Based on `allowed_commands.normalized.txt` (164 commands extracted from runbooks).

### Core Commands (28 aligned)

These commands appear in **both** runbooks and code implementation:

```
maestro ai {claude|codex|gemini|qwen}
maestro build
maestro convert {new|plan|run}
maestro discuss [--context <context>] [--resume <session>]
maestro init [--greenfield|--read-only]
maestro issues {add|accept|ignore|list}
maestro make [--with-hub-deps]
maestro ops commit {create|suggest}
maestro phase add <track-id> <phase-title>
maestro repo {conf|conventions|hub|resolve|show}
maestro rules {check|list}
maestro runbook {add|step-add|export}
maestro session log
maestro settings set
maestro solutions match
maestro task {add|complete}
maestro track add
maestro tu {autocomplete|build|query|refactor}
maestro work {task|resume|close|spawn}
maestro workflow {init|node|edge|validate|render|accept}
maestro wsession {breadcrumb|show}
```

### Command Details

**See canonical command list extracted from runbooks:**
- Full command inventory: `docs/workflows/v3/reports/allowed_commands.normalized.txt` (164 entries)
- Alignment report: `docs/workflows/v3/reports/cli_surface_audit.md`

**Note:** The full canonical command surface includes:
- 28 commands aligned in both runbooks and code
- 136 additional runbook-documented commands (flags, variants, subcommands)

---

## Hidden/Legacy Commands

These 5 commands are **hidden by default** (require `MAESTRO_ENABLE_LEGACY=1`):

### 1. `maestro session` → `maestro wsession`

**Status:** Deprecated in favor of work sessions (`wsession`)

**Migration:**
- `maestro session list` → `maestro wsession list`
- `maestro session breadcrumbs <id>` → `maestro wsession breadcrumb <id>`
- `maestro session timeline <id>` → `maestro wsession timeline <id>`
- `maestro session stats <id>` → `maestro wsession stats <id>`

**Reason:** Original session command was task-focused; replaced by comprehensive work session system with breadcrumbs, timelines, and better tracking.

### 2. `maestro understand` → `maestro repo resolve` + `maestro runbook`

**Status:** Deprecated / Functionality absorbed

**Migration:**
- `maestro understand dump` → Use `maestro repo show` or `maestro runbook export`
- Code understanding → Use `maestro ai qwen` or `maestro ai claude` for interactive analysis

**Reason:** Functionality merged into repo/runbook/workflow analysis commands; not part of v3 runbook surface.

### 3. `maestro resume` → `maestro discuss` or `maestro work resume`

**Status:** Deprecated / Functionality integrated

**Migration:**
- `maestro resume` (AI session) → `maestro discuss resume <session-id>`
- `maestro resume` (work session) → `maestro work resume <wsession-id>`

**Reason:** Standalone resume command was ambiguous; functionality now integrated into discuss and work commands with explicit context.

### 4. `maestro rules` → `maestro repo rules` or `maestro solutions`

**Status:** Deprecated / To be merged into runbook/workflow operations

**Migration:**
- `maestro rules list` → `maestro repo conventions` or `maestro solutions match`
- `maestro rules edit` → Manual editing of repo configuration files
- `maestro rules check` → `maestro repo conventions check`

**Reason:** Overlaps with `maestro repo conventions` and `maestro solutions`; being consolidated into runbook conventions and workflow operations.

### 5. `maestro root` → `maestro track` / `maestro phase` / `maestro task`

**Status:** Deprecated / Replaced by hierarchy

**Migration:**
- `maestro root set <task>` → `maestro track add` + `maestro phase add` + `maestro task add`
- `maestro root get` → `maestro track show` or `maestro phase show`
- `maestro root refine` → `maestro discuss --context track`
- `maestro root discuss` → `maestro discuss --context track`
- `maestro root show` → `maestro track show`

**Reason:** Flat "root task" model replaced by hierarchical track/phase/task structure for better project organization.

---

## Migration Playbook

### Strategy

1. **Identify legacy usage** - Search codebase for deprecated commands
2. **Replace incrementally** - Migrate one command at a time
3. **Test with legacy disabled** - Run tests with `MAESTRO_ENABLE_LEGACY=0` to catch dependencies
4. **Update documentation** - Ensure runbooks/docs only reference canonical commands

### Step-by-Step: Migrating from `session` to `wsession`

**Before (legacy):**
```bash
maestro session new --name "Sprint 1"
maestro session list
maestro session breadcrumbs session-001
```

**After (canonical):**
```bash
maestro work task task-001  # Creates work session automatically
maestro wsession list
maestro wsession breadcrumb session-001
```

**Key Differences:**
- Work sessions are task-focused (created via `maestro work task`)
- No explicit "new session" - sessions created implicitly when starting work
- More robust breadcrumb system with cookies for security

### Step-by-Step: Migrating from `understand` to `repo resolve`

**Before (legacy):**
```bash
maestro understand dump --output docs/UNDERSTANDING.md
```

**After (canonical):**
```bash
maestro repo resolve --level deep
maestro repo show packages
maestro runbook export <runbook-id> --format md --out docs/RUNBOOK.md
```

**Key Differences:**
- `repo resolve` scans repository structure (packages, assemblies, entry-points)
- `repo show` displays specific aspects (packages, entry-points, conventions)
- `runbook export` documents workflows/processes

### Step-by-Step: Migrating from `resume` to `discuss resume` / `work resume`

**Before (legacy):**
```bash
maestro resume  # Ambiguous - AI session or work session?
```

**After (canonical):**
```bash
# For AI discussion sessions:
maestro discuss resume session-20250126-001

# For work sessions:
maestro work resume wsession-abc123
```

**Key Differences:**
- Explicit context (discuss vs work)
- Session ID required (no ambiguity)
- `discuss resume` supports session replay with transcripts

### Step-by-Step: Migrating from `rules` to `repo conventions` / `solutions`

**Before (legacy):**
```bash
maestro rules list
maestro rules check
```

**After (canonical):**
```bash
# For naming conventions:
maestro repo conventions check

# For policy rules and solutions:
maestro solutions match --from-build-log
```

**Key Differences:**
- `repo conventions` focuses on naming/structure rules
- `solutions` focuses on issue resolution policies
- Better separation of concerns

### Step-by-Step: Migrating from `root` to `track/phase/task`

**Before (legacy):**
```bash
maestro root set "Implement user authentication"
maestro root refine
maestro root show
```

**After (canonical):**
```bash
# Create hierarchical structure:
maestro track add "Sprint 1: Auth System" --start 2025-01-01
maestro phase add track-001 "P1: Core Auth"
maestro task add phase-001 "Implement login endpoint"

# Discuss at appropriate level:
maestro discuss --context task --task task-001
maestro discuss --context phase --phase phase-001

# Show details:
maestro task show task-001
maestro phase show phase-001
maestro track show track-001
```

**Key Differences:**
- Hierarchical organization (track → phase → task)
- Better project planning and tracking
- Explicit scoping for AI discussions

---

## Testing Contract

All canonical vs legacy behavior is locked via automated tests in:

**File:** `tests/test_cli_surface_contract.py`

**Test Classes:**
1. `TestLegacyKillSwitch` - Environment variable behavior
2. `TestParserStructure` - Parser construction validation
3. `TestLegacyWarnings` - Warning banner verification
4. `TestAliasNormalization` - Alias behavior with gate
5. `TestErrorMessages` - Helpful error messages
6. `TestCanonicalCommandsContinueToWork` - Integration tests

**Running Tests:**
```bash
# Run all CLI surface contract tests
pytest tests/test_cli_surface_contract.py -v

# Verify legacy disabled by default
MAESTRO_ENABLE_LEGACY=0 pytest tests/test_cli_surface_contract.py::TestLegacyKillSwitch::test_legacy_disabled_by_default

# Verify legacy enabled with env var
MAESTRO_ENABLE_LEGACY=1 pytest tests/test_cli_surface_contract.py::TestLegacyKillSwitch::test_legacy_enabled_with_1
```

---

## Enforcement Policy

### For New Code

- **MUST NOT** use legacy commands in new implementations
- **MUST NOT** reference legacy commands in new runbooks/documentation
- **MUST** use canonical v3 commands only
- Code reviews should flag usage of legacy commands

### For Existing Code

- May continue using legacy commands with `MAESTRO_ENABLE_LEGACY=1`
- Should migrate incrementally to canonical commands
- **MUST** add `MAESTRO_ENABLE_LEGACY=1` to scripts/CI if using legacy commands
- Existing code should not block new feature development

### For Tests

- New tests **MUST NOT** use legacy commands
- Legacy tests should be marked with `@pytest.mark.legacy` or moved to `tests/legacy/`
- Default `pytest -q` excludes legacy tests (via pytest.ini)
- See: `docs/workflows/v3/reports/test_command_truth_policy.md`

### For Documentation

- Runbooks and user guides **MUST NOT** reference legacy commands
- Legacy commands documented only in `DEPRECATION.md` and this contract
- Migration paths must be clearly documented
- All examples should use canonical commands

---

## Related Documents

- [Deprecation Policy](./DEPRECATION.md) - Detailed deprecation timeline and rationale
- [CLI Signatures](./SIGNATURES.md) - Canonical command signatures and verb standardization
- [CLI Tree](./TREE.md) - Visual command hierarchy
- [CLI Surface Audit](../reports/cli_surface_audit.md) - Alignment report (runbooks vs code)
- [Allowed Commands List](../reports/allowed_commands.normalized.txt) - Extracted canonical commands

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-28 | Initial CLI surface contract with legacy kill switch (P1 Sprint 3.4) |

---

## Questions / Feedback

For questions about the CLI surface contract or migration support:

1. Check migration playbook in this document
2. Review `DEPRECATION.md` for timeline and rationale
3. Consult CLI surface audit report for full command inventory
4. Run tests to verify expected behavior: `pytest tests/test_cli_surface_contract.py`

#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-17: CLI Alignment Drill — Resolve TODO_CMD and Create Ledger Entries

echo "=== CLI Alignment: Systematic Convergence from Runbooks to Implementation ==="
echo "Pipeline: Find TODOs → Check CLI → Resolve or Create Ledger Entry"

echo ""
echo "=== Step 1: Identify TODO_CMD Markers ==="

run grep -r "TODO_CMD:" docs/workflows/v2/runbooks/examples/proposed/
# EXPECT: Lists all TODO markers with file:line
# STORES_READ: (filesystem only)
# GATES: (none)

echo ""
echo "docs/workflows/v2/runbooks/examples/proposed/EX-13_repo_resolve_levels_and_repoconf_targets.md:87:| \`TODO_CMD: maestro repo resolve --level deep\` |"
echo "docs/workflows/v2/runbooks/examples/proposed/EX-13_repo_resolve_levels_and_repoconf_targets.md:121:| \`TODO_CMD: maestro build\` |"
echo "docs/workflows/v2/runbooks/examples/proposed/EX-14_tu_ast_refactor_autocomplete.md:67:| \`TODO_CMD: maestro tu build --target target-cmake-mathapp\` |"
echo "docs/workflows/v2/runbooks/examples/proposed/EX-14_tu_ast_refactor_autocomplete.md:86:| \`TODO_CMD: maestro tu query symbol --name calculateSum\` |"
echo "docs/workflows/v2/runbooks/examples/proposed/EX-15_convert_cross_repo_pipeline_from_ast.md:27:| \`TODO_CMD: maestro convert new cpp-to-python\` |"
echo "docs/workflows/v2/runbooks/examples/proposed/EX-16_rules_conventions_issues_tasks_overrides.md:107:| \`TODO_CMD: maestro repo resolve --level deep\` |"
echo "docs/workflows/v2/runbooks/examples/proposed/EX-16_rules_conventions_issues_tasks_overrides.md:145:| \`TODO_CMD: maestro issues list\` |"
echo "docs/workflows/v2/runbooks/examples/proposed/EX-16_rules_conventions_issues_tasks_overrides.md:168:| \`TODO_CMD: maestro rules list\` |"
echo ""
echo "Found 8 TODO_CMD markers across 4 runbook examples."

echo ""
echo "=== Step 2: Check CLI Help for Each TODO ==="

run maestro --help
# EXPECT: Shows available subcommands
# GATES: (none)

echo ""
echo "Usage: maestro [OPTIONS] COMMAND [ARGS]..."
echo ""
echo "Commands:"
echo "  init          Initialize Maestro in current repository"
echo "  repo          Repository discovery and configuration"
echo "  work          Work session management"
echo "  ops           Operations and maintenance"
echo "  settings      Configuration management"
echo ""
echo "Use \"maestro COMMAND --help\" for more information."

echo ""
run maestro repo --help
# EXPECT: Shows repo subcommand structure

echo ""
echo "Usage: maestro repo [OPTIONS] COMMAND [ARGS]..."
echo ""
echo "Commands:"
echo "  resolve       Discover build systems and targets"
echo "  conf          Configure default target"
echo ""
echo "Options:"
echo "  --help        Show this message and exit"

echo ""
run maestro repo resolve --help
# EXPECT: Check for --level flag

echo ""
echo "Usage: maestro repo resolve [OPTIONS]"
echo ""
echo "Options:"
echo "  --level [lite|deep]  Resolution depth (default: lite)"
echo "  --help              Show this message and exit"
echo ""
echo "✅ CONFIRMED: maestro repo resolve --level deep EXISTS"

echo ""
run maestro tu --help
# EXPECT: Command not found

echo ""
echo "Error: No such command \"tu\""
echo ""
echo "❌ MISSING: maestro tu subcommand does not exist"

echo ""
run maestro build --help
# EXPECT: Command not found

echo ""
echo "Error: No such command \"build\""
echo ""
echo "❌ MISSING: maestro build does not exist"

echo ""
run maestro convert --help
# EXPECT: Command not found

echo ""
echo "Error: No such command \"convert\""
echo ""
echo "❌ MISSING: maestro convert does not exist"

echo ""
run maestro issues --help
# EXPECT: Command not found

echo ""
echo "Error: No such command \"issues\""
echo ""
echo "❌ MISSING: maestro issues does not exist"

echo ""
run maestro rules --help
# EXPECT: Command not found

echo ""
echo "Error: No such command \"rules\""
echo ""
echo "❌ MISSING: maestro rules does not exist"

echo ""
echo "=== Step 3: Create Resolution Table ==="

echo ""
echo "| TODO_CMD                                          | Resolution      | Action                              |"
echo "|---------------------------------------------------|-----------------|-------------------------------------|"
echo "| maestro repo resolve --level deep                | ✅ EXISTS       | Remove TODO_CMD marker              |"
echo "| maestro build                                     | ❌ MISSING      | Create ledger entry                 |"
echo "| maestro tu build --target ...                     | ❌ MISSING      | Create ledger entry (TU tree)       |"
echo "| maestro tu query symbol --name ...                | ❌ MISSING      | Covered by TU ledger                |"
echo "| maestro tu refactor rename --symbol ...           | ❌ MISSING      | Covered by TU ledger                |"
echo "| maestro convert new <name>                        | ❌ MISSING      | Create ledger entry (convert)       |"
echo "| maestro issues list                               | ❌ MISSING      | Create ledger entry (issues)        |"
echo "| maestro rules list                                | ❌ MISSING      | Create ledger entry (rules)         |"
echo ""
echo "Summary: 1 resolved, 7 missing (grouped into 4 ledger entries)"

echo ""
echo "=== Step 4: Create Ledger Entries for Missing CLI ==="

echo ""
echo "Appending to docs/workflows/v2/IMPLEMENTATION_LEDGER.md..."
echo ""

echo "# Ledger Entry 1: maestro build"
echo ""
echo "### maestro build [OPTIONS] [TARGET]"
echo ""
echo "**Status**: proposed"
echo "**Priority**: high"
echo "**Required by**: EX-13, EX-14, WF-08 (build execution)"
echo ""
echo "**Description**:"
echo "Build the default target or specified target using the detected build system."
echo ""
echo "**Behavior**:"
echo "- Reads ./docs/maestro/repo.json to find default target"
echo "- Invokes appropriate build system (cmake, make, cargo, etc.)"
echo "- Writes build artifacts to standard locations"
echo "- Updates build status in repo truth"
echo ""
echo "**Options**:"
echo "- --target <target-id>: Override default target"
echo "- --clean: Clean before build"
echo "- --verbose: Show detailed build output"
echo ""
echo "**Gates**:"
echo "- REPOCONF_GATE: Default target must be set"
echo ""
echo "**Tests**:"
echo "- Test 1: Build with default target succeeds"
echo "- Test 2: Build with explicit target succeeds"
echo "- Test 3: Build fails gracefully when REPOCONF_GATE not satisfied"

echo ""
echo "# Ledger Entry 2: maestro tu (full subcommand tree)"
echo ""
echo "### maestro tu build --target <target-id>"
echo ""
echo "**Status**: proposed"
echo "**Priority**: medium"
echo "**Required by**: EX-14, EX-15 (AST operations)"
echo ""
echo "**Description**:"
echo "Build translation units (AST index) for a target by invoking compiler with AST dump flags."
echo ""
echo "**Gates**:"
echo "- REPOCONF_GATE"
echo "- BUILD_SUCCESS"
echo ""
echo "**Stores**:"
echo "- Read: REPO_TRUTH_DOCS_MAESTRO"
echo "- Write: TU_DATABASE (./docs/maestro/tu/)"

echo ""
echo "# Ledger Entry 3: maestro convert (pipeline commands)"
echo ""
echo "### maestro convert new <pipeline-name>"
echo "### maestro convert plan <pipeline-name>"
echo "### maestro convert run <pipeline-name> --out <target-path>"
echo ""
echo "**Status**: proposed"
echo "**Priority**: low"
echo "**Required by**: EX-15 (cross-repo conversion)"

echo ""
echo "# Ledger Entry 4: maestro issues and maestro rules"
echo ""
echo "### maestro issues list"
echo "### maestro issues show <issue-id>"
echo "### maestro issues ignore <issue-id> --reason <reason>"
echo ""
echo "### maestro rules list"
echo "### maestro rules check"
echo ""
echo "**Status**: proposed"
echo "**Priority**: medium"
echo "**Required by**: EX-16 (governance and conventions)"

echo ""
echo "Ledger entries created (4 total, covering 7 missing commands)."

echo ""
echo "=== Step 5: Update Runbooks with Resolved CLI ==="

echo ""
echo "Editing EX-13_repo_resolve_levels_and_repoconf_targets.md..."
echo ""
echo "Before:"
echo "  | \`TODO_CMD: maestro repo resolve --level deep\` | Run deep resolve | Detects violations |"
echo ""
echo "After:"
echo "  | \`maestro repo resolve --level deep\` | Run deep resolve | Detects violations |"
echo ""
echo "TODO_CMD marker removed."

echo ""
echo "=== Alternative Path: CLI Exists But API Differs ==="

run maestro repo resolve --help
# EXPECT: May show different flags than expected

echo ""
echo "Hypothetical output (alternative scenario):"
echo ""
echo "Usage: maestro repo resolve [OPTIONS]"
echo ""
echo "Options:"
echo "  --deep    Perform deep analysis (convention checking)"
echo "  --help    Show this message and exit"
echo ""
echo "Note: Flag is --deep, not --level deep"
echo ""
echo "Resolution: Update runbook to use --deep flag, optionally note inconsistency in ledger."

echo ""
echo "=== Outcome A: All TODOs Resolved from Existing CLI ==="
echo "Flow:"
echo "  1. Identify 8 TODO_CMD markers"
echo "  2. Check maestro --help and subcommand help"
echo "  3. Find all 8 commands already exist"
echo "  4. Update runbooks to remove TODO_CMD markers"
echo "  5. No ledger entries needed"
echo ""
echo "Artifacts:"
echo "  - Updated: EX-13.md, EX-14.md, EX-15.md, EX-16.md (TODO_CMD removed)"
echo "  - No ledger entries created"
echo ""
echo "Duration: ~10 minutes"

echo ""
echo "=== Outcome B: Mix of Resolved and Missing CLI ==="
echo "Flow:"
echo "  1. Identify 8 TODO_CMD markers"
echo "  2. Check help output"
echo "  3. Find 1 command exists (maestro repo resolve --level deep)"
echo "  4. Find 7 commands missing"
echo "  5. Update runbook to remove TODO for resolved command"
echo "  6. Create 4 ledger entries grouping missing commands"
echo ""
echo "Artifacts:"
echo "  - Updated: EX-13.md (1 TODO removed)"
echo "  - Created/appended: docs/workflows/v2/IMPLEMENTATION_LEDGER.md (4 entries)"
echo ""
echo "Duration: ~30 minutes"

echo ""
echo "=== Outcome C: CLI Exists But API Differs from Runbook ==="
echo "Flow:"
echo "  1. Identify TODO_CMD markers"
echo "  2. Check help, find command exists but with different flags"
echo "  3. Update runbook to match actual API"
echo "  4. Optionally create ledger entry noting API inconsistency"
echo ""
echo "Duration: ~15 minutes"

echo ""
echo "=== Key Insights ==="
echo "  - TODO_CMD markers indicate documentation ahead of implementation"
echo "  - Help output reveals actual CLI API (may differ from assumptions)"
echo "  - Group related missing commands into coherent ledger entries"
echo "  - Ledger entries include behavior, gates, stores, and test hints"
echo "  - Systematic resolution creates feedback loop: runbooks → CLI gaps → implementation priorities"

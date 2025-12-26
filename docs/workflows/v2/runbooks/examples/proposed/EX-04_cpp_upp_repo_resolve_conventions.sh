#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-04: Ultimate++ Packages — Deep Resolve, Convention Detection, Issues

# Step 1: Initialize Maestro
run maestro init
# EXPECT: Creates ./docs/maestro/** structure
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

# Step 2: Deep resolve for U++ packages
run maestro repo resolve --level deep
# EXPECT: Detects MyCore.upp, MyGui.upp, MyApp.upp
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_DEEP
# INTERNAL: UNKNOWN

# Step 3: Show detected packages
run maestro repo show packages  # TODO_CMD: exact syntax uncertain
# EXPECT: Lists MyCore, MyGui, MyApp with file counts
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)
# INTERNAL: UNKNOWN

# Step 4: Check conventions
run maestro repo conventions check  # TODO_CMD: convention validation command
# EXPECT: Detects missing header guard in MyCore/Core.h
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO (issues created)
# GATES: CONVENTIONS_GATE
# INTERNAL: UNKNOWN

# Step 5: List convention issues
run maestro issues list --type convention  # TODO_CMD: filter flag uncertain
# EXPECT: Shows issue: "Missing header guard: MyCore/Core.h"
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)
# INTERNAL: UNKNOWN

# Step 6: Accept issue for fixing
run maestro issues accept issue-001  # TODO_CMD: acceptance command uncertain
# EXPECT: Issue status → accepted
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE
# INTERNAL: UNKNOWN

echo ""
echo "EX-04 Outcome A: U++ packages scanned, convention violations documented"
echo "Issues: ./docs/maestro/issues/issue-001.json (type: convention)"
echo "Next: User fixes header guard or ignores issue"

#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-16: Rules + Conventions Enforcement — Issues, Tasks, Ignore/Override Policy

echo "=== Rules and Conventions: First-Class Governance ==="
echo "Principle: Violations always create issues (not silent failures)"
echo "Policy: Explicit ignore-with-reason or fix-with-task"

echo ""
echo "=== Minimal Project Skeleton (with Intentional Violation) ==="
echo "my-project/"
echo "├── CMakeLists.txt"
echo "├── src/"
echo "│   ├── main.cpp"
echo "│   └── utils.h  # VIOLATION: Header in src/ instead of include/"
echo "└── (no include/ directory)"
echo ""
echo "Convention violated: Headers should be in include/, sources in src/"

echo ""
echo "=== Step 1: Initialize Maestro ===\"

run maestro init
# EXPECT: Creates ./docs/maestro/**
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)

echo ""
echo "[INIT] Created ./docs/maestro/repo.json"
echo "[INIT] Initialized Maestro structure"

echo ""
echo "=== Step 2: Run Lite RepoResolve ===\"

run maestro repo resolve --level lite
# EXPECT: Discovers CMake, no convention checking
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_LITE

echo ""
echo "Detected packages:"
echo "  - pkg-001: MyProject (cmake)"
echo "    - target-cmake-myapp: myapp [executable]"
echo ""
echo "Single target detected. Auto-selected as default."
echo ""
echo "Note: Lite resolve does not check conventions. Run 'maestro repo resolve --level deep' for full analysis."

echo ""
echo "=== Step 3: Run Deep RepoResolve (Convention Checking) ===\"

run maestro repo resolve --level deep  # TODO_CMD
# EXPECT: Finds header in wrong location, creates issue
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO (issues added)
# GATES: REPO_RESOLVE_DEEP, CONVENTIONS_GATE
# INTERNAL: run_lite_resolve, check_conventions, create_issues

echo ""
echo "Running deep resolve..."
echo ""
echo "Lite resolve complete: 1 package, 1 target"
echo ""
echo "Checking conventions:"
echo "  - File layout rule: FAIL"
echo "    - Found header file: src/utils.h"
echo "    - Expected location: include/utils.h"
echo "    - Created issue: issue-001 \"Header file in wrong directory: src/utils.h\""
echo ""
echo "  - Naming conventions: OK"
echo "  - Directory structure: OK"
echo ""
echo "Deep resolve complete."
echo "Issues created: 1"
echo ""
echo "View issues: maestro issues list"

echo ""
echo "=== Step 4: List Issues ===\"

run maestro issues list  # TODO_CMD
# EXPECT: Shows convention violation issue
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none - read-only)

echo ""
echo "Open Issues:"
echo ""
echo "issue-001: Header file in wrong directory: src/utils.h"
echo "  Severity: warning"
echo "  Created by: repo_resolve_deep"
echo "  Description: Header file src/utils.h should be in include/ directory"
echo "  Status: open"
echo "  Created: 2025-01-26T14:30:00Z"
echo ""
echo "Total issues: 1"

echo ""
echo "=== Step 5: Check Rules ===\"

run maestro rules list  # TODO_CMD
# EXPECT: Lists enabled rules
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO (rules config)
# GATES: (none - read-only)

echo ""
echo "Active Rules:"
echo ""
echo "rule-001: File Layout Convention"
echo "  Description: Headers (.h, .hpp) must be in include/, sources in src/"
echo "  Severity: warning"
echo "  Enabled: yes"
echo ""
echo "rule-002: Naming Convention — Snake Case Headers"
echo "  Description: Header files should use snake_case naming"
echo "  Severity: info"
echo "  Enabled: yes"
echo ""
echo "rule-003: No Forbidden Patterns"
echo "  Description: Detect forbidden patterns (e.g., goto, global mutable state)"
echo "  Severity: error"
echo "  Enabled: yes"
echo ""
echo "Total rules: 3"

echo ""
echo "=== Step 6: Run Rules Check (Explicit) ===\"

run maestro rules check  # TODO_CMD
# EXPECT: Re-checks conventions, updates issues
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO (issues updated if new violations)
# GATES: CONVENTIONS_GATE
# INTERNAL: run_all_rules, update_issues

echo ""
echo "[RULES CHECK] Running all enabled rules..."
echo ""
echo "rule-001: File Layout Convention"
echo "  - FAIL: src/utils.h (expected: include/utils.h)"
echo "  - Issue already exists: issue-001"
echo ""
echo "rule-002: Naming Convention — Snake Case Headers"
echo "  - OK: utils.h (snake_case format)"
echo ""
echo "rule-003: No Forbidden Patterns"
echo "  - OK: No forbidden patterns found"
echo ""
echo "Rules check complete. 1 violation found."

echo ""
echo "=== Recovery Path A: Fix the Violation ===\"

run mkdir include
run mv src/utils.h include/
# EXPECT: Fixes file layout

echo ""
echo "# Update src/main.cpp to include from new location"
echo "# Change: #include \"utils.h\" → #include \"../include/utils.h\""

run maestro rules check  # TODO_CMD
# EXPECT: Violation resolved, issue auto-closes

echo ""
echo "[RULES CHECK] Running all enabled rules..."
echo ""
echo "rule-001: File Layout Convention"
echo "  - OK: include/utils.h (correct location)"
echo ""
echo "All rules passed."
echo ""
echo "Closed issues: issue-001 (violation resolved)"

echo ""
echo "=== Recovery Path B: Ignore the Violation (Explicit Override) ===\"

run maestro issues ignore issue-001 --reason "Legacy code - header will remain in src/ for backwards compatibility"  # TODO_CMD
# EXPECT: Issue status → ignored, reason tracked
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: (ignored issues do not block)

echo ""
echo "[ISSUES] Ignoring issue: issue-001"
echo ""
echo "Reason: Legacy code - header will remain in src/ for backwards compatibility"
echo ""
echo "Issue status: open → ignored"
echo "Issue will not block builds or gates."
echo ""
echo "Note: Ignored issues are tracked for audit purposes."

echo ""
echo "Artifact: ./docs/maestro/issues/issue-001.json updated with:"
echo "  - status: ignored"
echo "  - ignored_reason: \"Legacy code - header will remain in src/ for backwards compatibility\""
echo "  - ignored_at: 2025-01-26T14:45:00Z"

echo ""
echo "=== Recovery Path C: Create Task from Issue ===\"

run maestro task add --from-issue issue-001  # TODO_CMD
# EXPECT: Task created, linked to issue
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO (task added)
# INTERNAL: create_task_from_issue, link_issue_to_task

echo ""
echo "[TASK] Created task from issue: issue-001"
echo ""
echo "task-001: Fix header file location: src/utils.h"
echo "  Description: Move src/utils.h to include/utils.h"
echo "  Linked issue: issue-001"
echo "  Status: pending"
echo ""
echo "View task: maestro task show task-001"

echo ""
echo "User workflow:"
echo "  1. maestro work task task-001"
echo "  2. AI helps fix violation (move file, update includes)"
echo "  3. Mark task complete"
echo "  4. Issue auto-closes when violation resolved"

echo ""
echo "=== Outcome A: Violation Fixed → Issue Closed ===\"
echo "Flow (Path A):"
echo "  1. Deep resolve detects violation → creates issue-001"
echo "  2. User moves header file to include/"
echo "  3. Rules check verifies violation resolved"
echo "  4. Issue auto-closes"
echo ""
echo "Artifacts:"
echo "  - include/utils.h (moved from src/)"
echo "  - ./docs/maestro/issues/issue-001.json (status: closed)"
echo ""
echo "Duration: ~2 minutes"

echo ""
echo "=== Outcome B: Violation Ignored → Tracked with Reason ===\"
echo "Flow (Path B):"
echo "  1. Deep resolve detects violation → creates issue-001"
echo "  2. User decides to keep header in src/ (legacy code)"
echo "  3. User ignores issue with explicit reason"
echo "  4. Issue status → ignored, reason tracked for audit"
echo ""
echo "Artifacts:"
echo "  - src/utils.h remains in src/"
echo "  - ./docs/maestro/issues/issue-001.json (status: ignored, reason recorded)"
echo ""
echo "Key principle: Ignored issues do not block builds but are visible in audit logs"
echo ""
echo "Duration: ~30 seconds"

echo ""
echo "=== Outcome C: Task Created from Issue → Fix Tracked ===\"
echo "Flow (Path C):"
echo "  1. Deep resolve detects violation → creates issue-001"
echo "  2. User creates task from issue (task-001)"
echo "  3. User works on task with AI assistance"
echo "  4. Task completed → violation fixed → issue closes"
echo ""
echo "Artifacts:"
echo "  - ./docs/maestro/tasks/task-001.json (linked to issue-001)"
echo "  - include/utils.h (moved after task completion)"
echo "  - ./docs/maestro/issues/issue-001.json (status: closed)"
echo ""
echo "Duration: ~5 minutes (includes AI-assisted fix)"

echo ""
echo "=== Acceptance Gate Behavior ===\"
echo ""
echo "Severity levels and build blocking:"
echo ""
echo "| Severity | Blocks Build? | Can Be Ignored? |"
echo "|----------|---------------|-----------------|"
echo "| info     | No            | Yes             |"
echo "| warning  | No            | Yes             |"
echo "| error    | Yes           | Yes (explicit)  |"
echo ""
echo "Example:"
echo "  - File layout violation (warning) → creates issue, build proceeds"
echo "  - Forbidden goto usage (error) → creates issue, build blocked unless ignored"

echo ""
echo "=== Key Insights ===\"
echo "  - Conventions are checked during deep resolve (not lite)"
echo "  - Violations always create issues (not silent)"
echo "  - Issues can be fixed or explicitly ignored (with reason)"
echo "  - Ignored issues are tracked for audit (not deleted)"
echo "  - Tasks can be linked to issues for tracking fix work"
echo "  - Warning-level violations do not block builds by default"
echo "  - Error-level violations block builds unless explicitly overridden"

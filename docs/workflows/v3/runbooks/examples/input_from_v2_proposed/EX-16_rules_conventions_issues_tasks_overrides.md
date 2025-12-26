# EX-16: Rules + Conventions Enforcement — Issues, Tasks, Ignore/Override Policy

**Scope**: Rules and conventions as first-class governance
**Build System**: CMake
**Languages**: C++
**Outcome**: Demonstrate conventions and rules as enforced policies: detect violations during deep resolve, create issues, allow explicit override/ignore with tracked reasons, link issues to tasks

---

## Scenario Summary

Developer initializes Maestro in a C++ project with an intentional convention violation (header file in wrong directory). Running `maestro repo resolve --level deep` detects the violation and creates an issue. User can either fix the violation or explicitly ignore it with a reason. Issues can be linked to tasks for tracking fixes.

This demonstrates **rules and conventions as governance** with explicit acceptance gates and override policies.

---

## Preconditions

- C++ project with intentional convention violation
- Maestro not yet initialized

---

## Minimal Project Skeleton (with Intentional Violation)

```
my-project/
├── CMakeLists.txt
├── src/
│   ├── main.cpp
│   └── utils.h  # VIOLATION: Header file in src/ instead of include/
└── (no include/ directory)
```

**Convention violated**: Headers should be in `include/`, sources in `src/`

**CMakeLists.txt**:
```cmake
cmake_minimum_required(VERSION 3.10)
project(MyProject)
add_executable(myapp src/main.cpp)
```

**src/main.cpp**:
```cpp
#include "utils.h"
#include <iostream>

int main() {
    std::cout << "Hello from MyProject!" << std::endl;
    return 0;
}
```

**src/utils.h** (violation):
```cpp
#ifndef UTILS_H
#define UTILS_H
// Utility declarations here
#endif
```

---

## Runbook Steps

### Step 1: Initialize Maestro

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro init` | Initialize repo truth | Creates `./docs/maestro/**` |

**System Output**:
```
[INIT] Created ./docs/maestro/repo.json
[INIT] Initialized Maestro structure
```

**Gates**: (none)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO

### Step 2: Run Lite RepoResolve

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro repo resolve --level lite` | Detect build system and targets | Discovers CMake, no convention checking |

**System Output**:
```
Detected packages:
  - pkg-001: MyProject (cmake)
    - target-cmake-myapp: myapp [executable]

Single target detected. Auto-selected as default.

Note: Lite resolve does not check conventions. Run 'maestro repo resolve --level deep' for full analysis.
```

**Gates**: REPO_RESOLVE_LITE
**Stores write**: REPO_TRUTH_DOCS_MAESTRO

### Step 3: Run Deep RepoResolve (Convention Checking)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro repo resolve --level deep` | Detect violations, create issues | Finds header in wrong location, creates issue |

**Internal**:
- Runs lite resolve (packages, targets)
- Additionally checks conventions:
  - **File layout rule**: Headers (`.h`, `.hpp`) should be in `include/`, not `src/`
  - **Naming conventions**: Check file name patterns
  - **Directory structure**: Verify expected directories exist
- Creates issues for each violation found

**System Output**:
```
Running deep resolve...

Lite resolve complete: 1 package, 1 target

Checking conventions:
  - File layout rule: FAIL
    - Found header file: src/utils.h
    - Expected location: include/utils.h
    - Created issue: issue-001 "Header file in wrong directory: src/utils.h"

  - Naming conventions: OK
  - Directory structure: OK

Deep resolve complete.
Issues created: 1

View issues: maestro issues list
```

**Gates**: REPO_RESOLVE_DEEP, CONVENTIONS_GATE
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (issues added)

### Step 4: List Issues

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro issues list` | View all open issues | Shows convention violation issue |

**System Output**:
```
Open Issues:

issue-001: Header file in wrong directory: src/utils.h
  Severity: warning
  Created by: repo_resolve_deep
  Description: Header file src/utils.h should be in include/ directory
  Status: open
  Created: 2025-01-26T14:30:00Z

Total issues: 1
```

**Gates**: (none - read-only)
**Stores read**: REPO_TRUTH_DOCS_MAESTRO

### Step 5: Check Rules

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro rules list` | View active rules and conventions | Lists enabled rules |

**System Output**:
```
Active Rules:

rule-001: File Layout Convention
  Description: Headers (.h, .hpp) must be in include/, sources in src/
  Severity: warning
  Enabled: yes

rule-002: Naming Convention — Snake Case Headers
  Description: Header files should use snake_case naming
  Severity: info
  Enabled: yes

rule-003: No Forbidden Patterns
  Description: Detect forbidden patterns (e.g., goto, global mutable state)
  Severity: error
  Enabled: yes

Total rules: 3
```

**Gates**: (none - read-only)
**Stores read**: REPO_TRUTH_DOCS_MAESTRO (rules config)

### Step 6: Run Rules Check (Explicit)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro rules check` | Explicitly check all rules against current code | Re-checks conventions, updates issues |

**System Output**:
```
[RULES CHECK] Running all enabled rules...

rule-001: File Layout Convention
  - FAIL: src/utils.h (expected: include/utils.h)
  - Issue already exists: issue-001

rule-002: Naming Convention — Snake Case Headers
  - OK: utils.h (snake_case format)

rule-003: No Forbidden Patterns
  - OK: No forbidden patterns found

Rules check complete. 1 violation found.
```

**Gates**: CONVENTIONS_GATE
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (issues updated if new violations)

---

## Recovery Paths

### Path A: Fix the Violation

#### Step 7a: Fix Convention Violation

| Action | Intent | Expected |
|--------|--------|----------|
| `mkdir include && mv src/utils.h include/` | Move header to correct location | Fixes file layout |
| Update `src/main.cpp` to include from new location | Fix include path | Code compiles with new layout |
| `TODO_CMD: maestro rules check` | Verify violation resolved | Issue auto-closes |

**System Output (after fix)**:
```
[RULES CHECK] Running all enabled rules...

rule-001: File Layout Convention
  - OK: include/utils.h (correct location)

All rules passed.

Closed issues: issue-001 (violation resolved)
```

**Files modified**:
- `src/main.cpp`: `#include "utils.h"` → `#include "../include/utils.h"` (or adjust include paths)
- `include/utils.h` (moved from `src/utils.h`)

**Gates**: CONVENTIONS_GATE (now passes)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (issue closed)

---

### Path B: Ignore the Violation (Explicit Override)

#### Step 7b: Ignore Issue with Reason

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro issues ignore issue-001 --reason "Legacy code - header will remain in src/ for backwards compatibility"` | Mark issue as accepted deviation | Issue status → ignored, reason tracked |

**System Output**:
```
[ISSUES] Ignoring issue: issue-001

Reason: Legacy code - header will remain in src/ for backwards compatibility

Issue status: open → ignored
Issue will not block builds or gates.

Note: Ignored issues are tracked for audit purposes.
```

**Artifact**:
`./docs/maestro/issues/issue-001.json` updated:
```json
{
  "id": "issue-001",
  "title": "Header file in wrong directory: src/utils.h",
  "description": "Header file src/utils.h should be in include/ directory",
  "severity": "warning",
  "status": "ignored",
  "created_by": "repo_resolve_deep",
  "ignored_reason": "Legacy code - header will remain in src/ for backwards compatibility",
  "ignored_at": "2025-01-26T14:45:00Z"
}
```

**Gates**: CONVENTIONS_GATE (ignored issues do not block)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO

---

### Path C: Create Task from Issue

#### Step 7c: Link Issue to Task

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro task add --from-issue issue-001` | Create task to fix violation | Task created, linked to issue |

**System Output**:
```
[TASK] Created task from issue: issue-001

task-001: Fix header file location: src/utils.h
  Description: Move src/utils.h to include/utils.h
  Linked issue: issue-001
  Status: pending

View task: maestro task show task-001
```

**Artifact**:
`./docs/maestro/tasks/task-001.json`:
```json
{
  "id": "task-001",
  "title": "Fix header file location: src/utils.h",
  "description": "Move src/utils.h to include/utils.h to comply with file layout convention",
  "status": "pending",
  "linked_issue": "issue-001",
  "created_at": "2025-01-26T14:50:00Z"
}
```

**User workflow**:
1. Work on task: `maestro work task task-001`
2. AI helps fix violation (move file, update includes)
3. Mark task complete
4. Issue auto-closes when violation resolved

**Gates**: (none - task creation always allowed)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (task added)

---

## AI Perspective (Heuristic)

**What AI notices**:
- Deep resolve triggers convention checks beyond basic target detection
- Conventions are rules with severity levels (info, warning, error)
- Violations always create issues (not silent)
- Issues can be ignored (with reason) or fixed (closes issue)
- Tasks can be linked to issues for tracking fix work

**What AI tries**:
- Parse file tree to check layout conventions (headers in include/, sources in src/)
- Detect naming patterns (snake_case, camelCase, etc.)
- Check for forbidden patterns (goto, global vars, etc.)
- Suggest fixes based on rule type (e.g., "mv src/utils.h include/")
- Track ignored issues separately from open issues (for audit)

**Where AI tends to hallucinate**:
- May assume conventions are auto-fixed (they're not—user must approve)
- May confuse warning-level violations with error-level (warnings don't block builds by default)
- May assume ignored issues are deleted (they're tracked, not deleted)
- May suggest disabling rules instead of fixing violations (not recommended)
- May not account for legacy code exceptions (which is why ignore-with-reason exists)

---

## Outcomes

### Outcome A: Violation Fixed → Issue Closed

**Flow** (Path A):
1. Deep resolve detects violation → creates issue-001
2. User moves header file to include/
3. Rules check verifies violation resolved
4. Issue auto-closes

**Artifacts**:
- `include/utils.h` (moved from src/)
- `./docs/maestro/issues/issue-001.json` (status: closed)

**Duration**: ~2 minutes

### Outcome B: Violation Ignored → Tracked with Reason

**Flow** (Path B):
1. Deep resolve detects violation → creates issue-001
2. User decides to keep header in src/ (legacy code)
3. User ignores issue with explicit reason
4. Issue status → ignored, reason tracked for audit

**Artifacts**:
- `src/utils.h` remains in src/
- `./docs/maestro/issues/issue-001.json` (status: ignored, reason recorded)

**Key principle**: Ignored issues do not block builds but are visible in audit logs

**Duration**: ~30 seconds

### Outcome C: Task Created from Issue → Fix Tracked

**Flow** (Path C):
1. Deep resolve detects violation → creates issue-001
2. User creates task from issue (task-001)
3. User works on task with AI assistance
4. Task completed → violation fixed → issue closes

**Artifacts**:
- `./docs/maestro/tasks/task-001.json` (linked to issue-001)
- `include/utils.h` (moved after task completion)
- `./docs/maestro/issues/issue-001.json` (status: closed)

**Duration**: ~5 minutes (includes AI-assisted fix)

---

## Acceptance Gate Behavior

**Key principle**: Conventions are checked but do not block builds by default (severity: warning).

**Exception**: Error-level rules (e.g., "No forbidden patterns") DO block builds.

| Severity | Blocks Build? | Blocks Deep Resolve? | Can Be Ignored? |
|----------|---------------|----------------------|-----------------|
| info     | No            | No                   | Yes             |
| warning  | No            | No                   | Yes             |
| error    | Yes           | No (creates issue)   | Yes (with explicit override) |

**Example**:
- File layout violation (warning) → creates issue, build proceeds
- Forbidden goto usage (error) → creates issue, build blocked unless ignored

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "TODO_CMD: maestro repo resolve --level deep"
  - "TODO_CMD: maestro issues list"
  - "TODO_CMD: maestro issues show <issue-id>"
  - "TODO_CMD: maestro issues ignore <issue-id> --reason <reason>"
  - "TODO_CMD: maestro rules list"
  - "TODO_CMD: maestro rules check"
  - "TODO_CMD: maestro task add --from-issue <issue-id>"
  - "TODO_CMD: how rules are defined (config file? JSON?)"
  - "TODO_CMD: whether users can create custom rules"
  - "TODO_CMD: how ignored issues appear in audit logs"
  - "TODO_CMD: whether error-level rules can be overridden (and how)"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro repo resolve --level deep"
    intent: "Detect build system and check conventions"
    gates: ["REPO_RESOLVE_DEEP", "CONVENTIONS_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: []
    internal: ["run_lite_resolve", "check_conventions", "create_issues"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro issues list"
    intent: "View all open issues"
    gates: []
    stores_write: []
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["filter_issues_by_status"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro rules list"
    intent: "View active rules and conventions"
    gates: []
    stores_write: []
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["read_rules_config"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro rules check"
    intent: "Explicitly check all rules against current code"
    gates: ["CONVENTIONS_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["run_all_rules", "update_issues"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro issues ignore issue-001 --reason 'Legacy code'"
    intent: "Mark issue as accepted deviation with tracked reason"
    gates: []
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["update_issue_status", "record_ignore_reason"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro task add --from-issue issue-001"
    intent: "Create task linked to issue for tracking fix"
    gates: []
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["create_task_from_issue", "link_issue_to_task"]
    cli_confidence: "low"  # TODO_CMD
```

---

**Related:** Rules enforcement, convention checking, issue tracking, explicit overrides, governance policies
**Status:** Proposed

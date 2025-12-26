# EX-10: Tiny C++ Single-File Program + Makefile — Runbook→Workflow→Plan→Build→Run

**Scope**: Runbook-first C++ greenfield development with build system
**Build System**: Make (Makefile)
**Languages**: C++
**Outcome**: Model program in runbook, extract workflow, implement minimal C++ code, build with Makefile, handle compile errors

---

## Scenario Summary

Developer wants to create a minimal C++ program that prints a message. They start with a runbook to model the build and execution flow, extract a workflow showing manager intent→user intent→interface (CLI)→code→build, then implement the code. The example also demonstrates error handling when compilation fails (missing include).

This shows **runbook-first even for compiled languages** and integration with build systems.

---

## Preconditions

- Empty directory or new project
- C++ compiler (g++) available
- make utility available
- Maestro initialized (or will initialize)

---

## Minimal Project Skeleton (Final State)

```
hello-cpp/
├── docs/
│   └── maestro/
│       ├── runbooks/
│       │   └── hello-cpp-runbook.json
│       ├── workflows/
│       │   └── hello-cpp-workflow.json
│       ├── tracks/
│       │   └── track-001.json
│       ├── tasks/
│       │   └── task-001.json
│       └── issues/
│           └── issue-001.json (if compile error occurs)
├── main.cpp
└── Makefile
```

**main.cpp** (final implementation):
```cpp
#include <iostream>
#include <string>

int main() {
    std::string greeting = "Hello from C++!";
    std::cout << greeting << std::endl;
    return 0;
}
```

**Makefile**:
```makefile
CXX = g++
CXXFLAGS = -std=c++17 -Wall

hello: main.cpp
	$(CXX) $(CXXFLAGS) -o hello main.cpp

clean:
	rm -f hello

.PHONY: clean
```

---

## Runbook Steps

### Step 1: Initialize Maestro

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro init` | Create repo truth structure | `./docs/maestro/**` created |

### Step 2: Create Runbook

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook add --title "C++ Hello Program" --scope product --tag greenfield --tag cpp` | Create runbook | Runbook `c-hello-program.json` created |

### Step 3: Add Runbook Steps (Build & Execute Flow)

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook step-add c-hello-program --actor manager --action "Define goal: minimal C++ program that prints greeting" --expected "Goal documented"` | Manager intent | Step 1 added |
| `maestro runbook step-add c-hello-program --actor user --action "Run: make" --expected "Compiles successfully, creates ./hello binary"` | User intent (build) | Step 2 added |
| `maestro runbook step-add c-hello-program --actor user --action "Run: ./hello" --expected "Prints: Hello from C++!"` | User intent (execute) | Step 3 added |
| `maestro runbook step-add c-hello-program --actor system --action "Detect Makefile, invoke g++ with -std=c++17" --expected "Compilation successful"` | Interface layer (build) | Step 4 added |
| `maestro runbook step-add c-hello-program --actor ai --action "Write main.cpp with iostream, string" --expected "Code compiles cleanly"` | Code layer | Step 5 added |

### Step 4: Export Runbook

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook export c-hello-program --format md` | Review runbook | Markdown printed |

---

## Workflow Extraction (Runbook → Workflow)

### Step 5: Create Workflow from Runbook

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow init hello-cpp-workflow --from-runbook c-hello-program` | Extract workflow | Workflow JSON created |

### Step 6: Add Workflow Nodes (Layered)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow node add hello-cpp-workflow --layer manager_intent --label "Goal: minimal C++ greeting"` | Manager intent | Node added |
| `TODO_CMD: maestro workflow node add hello-cpp-workflow --layer user_intent --label "User runs make; then ./hello"` | User intent | Node added |
| `TODO_CMD: maestro workflow node add hello-cpp-workflow --layer interface --label "Build: Makefile + g++"` | Interface (build) | Node added |
| `TODO_CMD: maestro workflow node add hello-cpp-workflow --layer code --label "main.cpp: iostream + cout"` | Code | Node added |

### Step 7: Validate Workflow

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow validate hello-cpp-workflow` | Check graph | Validation passes |

---

## Plan Creation (Workflow → Track/Phase/Task)

### Step 8: Create Track

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro track add "Sprint 1: C++ Hello" --start 2025-01-01` | Create work track | Track `track-001` created |

### Step 9: Create Phase

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro phase add track-001 "P1: Implement and Build"` | Add phase | Phase `phase-001` created |

### Step 10: Create Task

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro task add phase-001 "Write main.cpp and Makefile"` | Add task | Task `task-001` created |

---

## Work Execution Loop (Plan → Implementation)

### Step 11: Resolve Repository (Detect Build System)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro repo resolve --level lite` | Detect Makefile-based C++ project | Build system: Make, Language: C++ |

**Gates:** REPO_RESOLVE_LITE
**Stores:** REPO_TRUTH_DOCS_MAESTRO

### Step 12: Start Work Session

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro work task task-001` | Start work with runbook/workflow context | Work session created |

### Step 13: AI Implements Code

AI generates:
1. `main.cpp` (initial version may have intentional error)
2. `Makefile`

**Intentional Error Example** (missing `#include <string>`):
```cpp
#include <iostream>
// Missing: #include <string>

int main() {
    std::string greeting = "Hello from C++!";  // Error: 'string' not declared
    std::cout << greeting << std::endl;
    return 0;
}
```

### Step 14: Build (First Attempt)

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro build` | Invoke detected build system | Compilation may fail if error present |

**Outcome if error:**
```
g++ -std=c++17 -Wall -o hello main.cpp
main.cpp:5:10: error: 'string' is not a member of 'std'
```

### Step 15: Match Solution (Error Recovery)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro solutions match --from-build-log` | Find solution for compile error | Suggests: "Add #include <string>" |

**Gates:** SOLUTIONS_GATE
**Stores:** REPO_TRUTH_DOCS_MAESTRO (issues created)

### Step 16: Create Issue

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro issues add --type build --desc "Missing include: <string>"` | Document error | Issue `issue-001` created |

### Step 17: Apply Fix

AI or user adds `#include <string>` to main.cpp.

### Step 18: Build (Retry)

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro build` | Rebuild after fix | Compilation succeeds, `./hello` created |

### Step 19: Test

| Command | Intent | Expected |
|---------|--------|----------|
| `./hello` | Run compiled binary | Prints: "Hello from C++!" |

### Step 20: Complete Task

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro task complete task-001` | Mark task done | Task status → completed |

---

## AI Perspective (Heuristic)

**What AI notices:**
- Runbook specifies Makefile → infer Make build system
- User steps show `make` then `./hello` → standard compile-then-run pattern
- Workflow interface layer is "Build: Makefile + g++" → not a runtime CLI

**What AI tries:**
- Generate minimal `main.cpp` with iostream
- Create simple Makefile with standard targets
- Detect common C++ errors (missing includes) and match solutions

**Where AI tends to hallucinate:**
- May generate complex Makefiles with unnecessary variables when simple is sufficient
- May add CMakeLists.txt even when Makefile is specified
- May include unnecessary headers like `<vector>` or `<algorithm>` when not needed

---

## Outcomes

### Outcome A: Success Path (Clean Build)

**Result:** `main.cpp` compiles successfully on first try

**Artifacts:**
- Runbook: `./docs/maestro/runbooks/c-hello-program.json`
- Workflow: `./docs/maestro/workflows/hello-cpp-workflow.json`
- Task: `./docs/maestro/tasks/task-001.json` (status: completed)
- Code: `main.cpp`, `Makefile`
- Binary: `./hello` (working)

### Outcome B: Compile Error → Solution Match → Fix → Success

**Result:** First build fails due to missing `#include <string>`

**Recovery Flow:**
1. Build fails with error
2. `maestro solutions match` identifies fix
3. Issue created: "Missing include: <string>"
4. Fix applied
5. Build succeeds
6. Task completed

**Artifacts:**
- Issue: `./docs/maestro/issues/issue-001.json` (status: resolved)
- All artifacts from Outcome A

### Outcome C: Missing Compiler

**Result:** `make` fails with "g++: command not found"

**Recovery:**
1. Create issue: "C++ compiler not found"
2. Create task: "Install g++"
3. Block until resolved

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "TODO_CMD: maestro workflow init <name> --from-runbook <id>"
  - "TODO_CMD: maestro workflow node add <id> --layer <layer> --label <text>"
  - "TODO_CMD: maestro workflow validate <id>"
  - "TODO_CMD: maestro repo resolve --level lite"
  - "TODO_CMD: maestro solutions match --from-build-log"
  - "TODO_CMD: maestro issues add --type build --desc <text>"
  - "TODO_CMD: maestro task complete <id>"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro runbook add --title 'C++ Hello Program' --scope product --tag cpp"
    intent: "Create narrative model for C++ build flow"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "high"

  - user: "maestro workflow init hello-cpp-workflow --from-runbook c-hello-program"
    intent: "Extract workflow from runbook"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro repo resolve --level lite"
    intent: "Detect Makefile and C++ language"
    gates: ["REPO_RESOLVE_LITE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro build"
    intent: "Invoke detected build system (make)"
    gates: ["READONLY_GUARD"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "high"

  - user: "maestro solutions match --from-build-log"
    intent: "Find solution for compile error"
    gates: ["SOLUTIONS_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro issues add --type build --desc 'Missing include: <string>'"
    intent: "Document build error as issue"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # TODO_CMD
```

---

**Related:** Build system integration, compile error recovery, runbook-first compiled languages
**Status:** Proposed

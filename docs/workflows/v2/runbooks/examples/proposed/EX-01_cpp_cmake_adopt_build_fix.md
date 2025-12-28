# EX-01: C++ CMake Existing Repo — Adopt, Build, Reactive Error, Solution Trial

**Scope**: WF-01 (Existing Repo Adopt) + WF-04 (Reactive Problem Solving)
**Build System**: CMake
**Languages**: C++17
**Outcome**: Demonstrate repo adoption, build failure detection, solution matching, and retry

---

## Scenario Summary

Developer inherits an existing C++ CMake project. They initialize Maestro, resolve the repo structure (detecting CMake), attempt to build, encounter a compile error (missing include), let Maestro's solution engine suggest a fix, apply it, and retry the build successfully.

---

## Minimal Project Skeleton

```
my-cpp-project/
├── CMakeLists.txt
├── src/
│   └── main.cpp
└── include/
    └── config.h
```

**CMakeLists.txt** (intentionally simple, will trigger build):
```cmake
cmake_minimum_required(VERSION 3.14)
project(MyCppApp VERSION 1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include_directories(${CMAKE_SOURCE_DIR}/include)

add_executable(my_app src/main.cpp)
```

**src/main.cpp** (intentional compile error: missing `#include <iostream>`):
```cpp
#include "config.h"

int main() {
    std::cout << "Hello from MyCppApp v" << APP_VERSION << std::endl;
    return 0;
}
```

**include/config.h**:
```cpp
#ifndef CONFIG_H
#define CONFIG_H
#define APP_VERSION "1.0"
#endif
```

The error: `main.cpp` uses `std::cout` without `#include <iostream>`.

---

## Runbook Steps

| Step | Command | Intent | Expected Outcome | Gates | Stores Written |
|------|---------|--------|------------------|-------|----------------|
| 1 | `maestro init` | Initialize Maestro in existing repo | Creates `./docs/maestro/**` structure | REPOCONF_GATE | REPO_TRUTH_DOCS_MAESTRO |
| 2 | `maestro repo resolve --level lite` | Detect build system, entry points, deps | Identifies CMakeLists.txt, C++ source files | REPO_RESOLVE_LITE | REPO_TRUTH_DOCS_MAESTRO |
| 3 | `maestro repo conf show` | Validate detected configuration | Displays build targets, detected compiler | REPOCONF_GATE | (read-only) |
| 4 | `maestro make` | Attempt to build using CMake | Build fails with compile error in `src/main.cpp:4` | READONLY_GUARD (fail) | (none - build fails) |
| 5 | `maestro solutions match --from-build-log` (proposed) | Match error against solution DB | Suggests "Missing include directive" solution | SOLUTIONS_GATE | REPO_TRUTH_DOCS_MAESTRO (issues) |
| 6 | `maestro issues add --from-solution <solution-id>` (proposed) | Create issue for missing include | Issue created: "Fix missing <iostream> include" | REPOCONF_GATE | REPO_TRUTH_DOCS_MAESTRO |
| 7 | `maestro task add --issue <issue-id> --action apply-solution` (proposed) | Create task to apply solution | Task created with action plan | REPOCONF_GATE | REPO_TRUTH_DOCS_MAESTRO |
| 8 | `maestro work start task <task-id>` | Apply solution (add `#include <iostream>`) | File modified, changes saved | READONLY_GUARD (write) | REPO_TRUTH_DOCS_MAESTRO |
| 9 | `maestro make` | Retry build | Build succeeds, binary created | READONLY_GUARD | REPO_TRUTH_DOCS_MAESTRO |

---

## AI Perspective (Heuristic)

**What the AI likely notices:**

- CMakeLists.txt detected → infer CMake build system
- `std::cout` usage without `<iostream>` include → common C++ pattern error
- Compile error message structure → maps to known solution pattern

**What the AI likely tries next:**

1. Parse compiler error output for file:line reference
2. Search solution database for "missing include" + "std::cout"
3. Propose solution: add `#include <iostream>` at top of `main.cpp`
4. If user accepts: edit file, insert include directive
5. Trigger rebuild automatically or suggest `maestro build` command

**Confidence heuristics:**

- High confidence: CMake detection (standard `CMakeLists.txt` signature)
- High confidence: Missing include error pattern (exact match in solutions DB)
- Medium confidence: Auto-fix location (may need user confirmation for multi-file projects)

**Caveats:**

- This is a heuristic approximation; actual AI behavior depends on implementation
- Error pattern matching may vary with compiler (g++, clang++, MSVC)

---

## Outcomes

### Outcome A: Auto-Solution Succeeds

1. Solution matched successfully from build log
2. Issue and task created automatically
3. User accepts solution via `maestro work task`
4. File edited, include added
5. Rebuild succeeds → binary in `build/my_app`
6. Task marked complete, issue closed

**Exit state:**

- Build passing
- `./docs/maestro/issues/<issue-id>.json` status: `resolved`
- `./docs/maestro/tasks/<task-id>.json` status: `completed`

### Outcome B: Auto-Solution Fails (Manual Investigation)

1. Solution matching returns multiple candidates or low confidence
2. Issue created but marked `needs-investigation`
3. Task created with manual action required
4. User must manually identify missing include
5. User edits `src/main.cpp` manually
6. Rebuild succeeds
7. Task marked complete with manual override

**Exit state:**

- Build passing after manual fix
- Issue status: `resolved-manual`
- Task annotated with "user-override: added include manually"

---

## CLI Gaps / TODOs

**Canonical commands (v3):**

- `maestro repo conf show` — canonical (SIGNATURES.md)
- `maestro make` — canonical; `build` is deprecated alias (SIGNATURES.md)
- `maestro work start task <id>` — canonical (SIGNATURES.md)

**Proposed commands (not yet implemented):**

- `maestro solutions match --from-build-log` — syntax for solution matching is proposed (GAP-0006)
- `maestro issues add --from-solution <id>` — linkage between solutions and issues proposed (GAP-0007)
- `maestro task add --issue <id> --action apply-solution` — task creation from solution proposed (GAP-0008)

**Clarifications needed:**

- Does `maestro init` auto-detect existing `./docs/maestro/` or always creates new?
- Does `repo resolve` trigger `REPOCONF_GATE` or is that separate validation?
- How does user confirm/reject a solution before task application?

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro init"
    intent: "Initialize Maestro in existing C++ CMake repo"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "high"

  - user: "maestro repo resolve --level lite"
    intent: "Detect CMake build system and source structure"
    gates: ["REPO_RESOLVE_LITE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "medium"

  - user: "maestro repo conf show"
    intent: "Display detected repository configuration"
    gates: ["REPOCONF_GATE"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "high"  # canonical command

  - user: "maestro make"
    intent: "Build project using detected CMake"
    gates: ["READONLY_GUARD"]
    stores_write: []  # fails before writing
    internal: ["UNKNOWN"]
    cli_confidence: "high"  # canonical command
    expected_result: "FAIL"  # compile error

  - user: "maestro solutions match --from-build-log"
    intent: "Match compile error to solution database"
    gates: ["SOLUTIONS_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]  # creates issue
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # proposed command (GAP-0006)

  - user: "maestro issues add --from-solution <solution-id>"
    intent: "Create issue for missing include fix"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # proposed command (GAP-0007)

  - user: "maestro task add --issue <issue-id> --action apply-solution"
    intent: "Create task to apply solution"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # proposed command (GAP-0008)

  - user: "maestro work start task <task-id>"
    intent: "Apply solution (add include directive)"
    gates: ["READONLY_GUARD"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "high"  # canonical command

  - user: "maestro make"
    intent: "Retry build after fix"
    gates: ["READONLY_GUARD"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "high"  # canonical command
    expected_result: "SUCCESS"
```

---

**Related Workflows:** WF-01, WF-04
**Status:** Proposed
**Acceptance Criteria:** CLI commands validated, solution matching implemented, ledger entry created

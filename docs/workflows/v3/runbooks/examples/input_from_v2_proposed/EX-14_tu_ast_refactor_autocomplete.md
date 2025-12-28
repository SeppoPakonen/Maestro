# EX-14: TU/AST Pipeline — Build Translation Units, Refactor Rename, Autocomplete Query

**Scope**: Translation Unit (TU) and Abstract Syntax Tree (AST) pipeline
**Build System**: CMake
**Languages**: C++
**Outcome**: Demonstrate the prerequisites and pipeline flow: RepoResolve + RepoConf → TU build → AST index → refactor operations (rename symbol) + autocomplete queries

---

## Scenario Summary

Developer has a small C++ project with two files. After initializing Maestro and resolving the repository (RepoResolve + RepoConf), they build translation units to create an AST index. Using this index, they perform a symbol rename refactor and query autocomplete suggestions. The pipeline shows how TU/AST operations depend on earlier gates.

This demonstrates **TU/AST as the foundation for refactoring and code intelligence**.

---

## Preconditions

- Small C++ project with CMakeLists.txt
- Two source files: `src/math.cpp` (defines `calculateSum`) and `src/main.cpp` (calls `calculateSum`)
- Maestro not yet initialized

---

## Minimal Project Skeleton

```
my-cpp-project/
├── CMakeLists.txt
├── src/
│   ├── math.cpp
│   └── main.cpp
```

**CMakeLists.txt**:
```cmake
cmake_minimum_required(VERSION 3.10)
project(MathApp)
add_executable(mathapp src/math.cpp src/main.cpp)
```

**src/math.cpp**:
```cpp
#include <iostream>

int calculateSum(int a, int b) {
    return a + b;
}
```

**src/main.cpp**:
```cpp
#include <iostream>

int calculateSum(int a, int b);  // Forward declaration

int main() {
    int result = calculateSum(5, 3);
    std::cout << "Result: " << result << std::endl;
    return 0;
}
```

---

## Runbook Steps

### Prerequisites Checklist

Before TU/AST operations can proceed, these gates must be satisfied:

| Gate | Command | Status |
|------|---------|--------|
| Maestro initialized | `maestro init` | Required |
| RepoResolve complete | `maestro repo resolve --level lite` | Required |
| RepoConf default target set | `maestro repo conf select-default-target <id>` | Required |
| Build succeeds | `maestro build` | Required |

**Why these prerequisites**:
- TU build requires knowing which files to compile (from RepoResolve)
- AST generation requires successful compilation (build must pass)
- Refactor operations require AST index (TU must be built)

### Step 1: Initialize and Resolve

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro init` | Initialize repo truth | Creates `./docs/maestro/**` |
| `maestro repo resolve --level lite` | Detect CMake build system | Discovers CMakeLists.txt, one target |
| `maestro repo conf select-default-target target-cmake-mathapp` | Set default target | RepoConf gate satisfied |

**System Output**:
```
Detected packages:
  - pkg-001: MathApp (cmake)
    - target-cmake-mathapp: mathapp [executable]

Single target detected. Auto-selected as default.
```

**Gates**: REPO_RESOLVE_LITE, REPOCONF_GATE
**Stores write**: REPO_TRUTH_DOCS_MAESTRO

### Step 2: Build Project

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro make` | Compile project, ensure no errors | Build succeeds |

**System Output**:
```
[BUILD] Using default target: target-cmake-mathapp
[BUILD] Running: cmake -S . -B build && cmake --build build
...
[BUILD] Success: mathapp executable created
```

**Gates**: REPOCONF_GATE
**Stores read**: REPO_TRUTH_DOCS_MAESTRO

### Step 3: Build Translation Units (TU)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro tu build --target target-cmake-mathapp` | Generate AST index from source files | Creates TU database with symbol information |

**Internal**:
- Invokes compiler with AST dump flags (e.g., `-Xclang -ast-dump` or clang tooling)
- Parses compiler output to extract:
  - Symbol definitions (functions, variables, classes)
  - Symbol references (call sites, usages)
  - Type information
  - Source locations (file, line, column)
- Writes AST index to `./docs/maestro/tu/target-cmake-mathapp.db` (hypothetical location)

**System Output**:
```
[TU BUILD] Building translation units for target: target-cmake-mathapp
[TU BUILD] Analyzing: src/math.cpp
[TU BUILD]   - Found function: calculateSum (line 3, col 5)
[TU BUILD] Analyzing: src/main.cpp
[TU BUILD]   - Found reference: calculateSum (line 6, col 18)
[TU BUILD] AST index created: ./docs/maestro/tu/target-cmake-mathapp.db
[TU BUILD] Total symbols: 2
```

**Gates**: REPOCONF_GATE (must have default target), BUILD_SUCCESS (must compile)
**Stores write**: TU_DATABASE (new storage: AST index)
**Stores read**: REPO_TRUTH_DOCS_MAESTRO

### Step 4: Query Symbol Information

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro tu query symbol --name calculateSum` | Look up symbol in AST index | Returns symbol ID, definitions, references |

**System Output**:
```
Symbol: calculateSum

Definitions:
  - symbol-001: calculateSum (function)
    File: src/math.cpp
    Line: 3, Column: 5
    Type: int(int, int)

References:
  - src/main.cpp:3:5 (forward declaration)
  - src/main.cpp:6:18 (call site)

Total references: 2
```

**Gates**: TU_BUILT (AST index must exist)
**Stores read**: TU_DATABASE

### Step 5: Refactor — Rename Symbol

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro tu refactor rename --symbol symbol-001 --to computeSum` | Rename function across all files | Updates definition and all references |

**Internal**:
- Looks up symbol-001 in AST index
- Identifies all definition and reference locations
- Checks for symbol collisions (does `computeSum` already exist?)
- If safe: rewrites source files
- If collision: aborts and creates issue

**System Output (success)**:
```
[REFACTOR] Renaming symbol: calculateSum → computeSum
[REFACTOR] Checking for collisions... OK
[REFACTOR] Updating 3 locations:
[REFACTOR]   - src/math.cpp:3:5 (definition)
[REFACTOR]   - src/main.cpp:3:5 (forward declaration)
[REFACTOR]   - src/main.cpp:6:18 (call site)
[REFACTOR] Rename complete.

Recommendation: Run 'maestro build' to verify changes compile.
```

**Files modified**:
- `src/math.cpp`: `int calculateSum(...)` → `int computeSum(...)`
- `src/main.cpp`: `calculateSum(...)` → `computeSum(...)` (both declaration and call)

**Gates**: TU_BUILT, SYMBOL_COLLISION_CHECK
**Stores read**: TU_DATABASE
**Stores write**: (source files modified)

### Step 6: Verify Refactor with Build

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro make` | Ensure refactored code compiles | Build succeeds |

**System Output**:
```
[BUILD] Using default target: target-cmake-mathapp
[BUILD] Running: cmake --build build
...
[BUILD] Success: mathapp executable created
```

### Step 7: Autocomplete Query

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro tu autocomplete --file src/main.cpp --line 6 --col 20` | Get autocomplete suggestions at cursor position | Returns available symbols in scope |

**Context**: Cursor is at `int result = computeSum(|5, 3);` (after opening paren)

**System Output**:
```
[AUTOCOMPLETE] File: src/main.cpp, Line: 6, Column: 20

Suggestions:
  - computeSum (function, int(int, int)) [current context]

Available in scope:
  - std::cout (object, std::ostream)
  - result (variable, int)
  - main (function, int())

No additional suggestions at this location.
```

**Gates**: TU_BUILT
**Stores read**: TU_DATABASE

---

## Alternative Path: Symbol Collision Detected

### Step 5b: Rename Fails Due to Collision

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro tu refactor rename --symbol symbol-001 --to std` | Try to rename to reserved/existing symbol | Fails with collision error |

**System Output**:
```
[REFACTOR] Renaming symbol: calculateSum → std
[REFACTOR] Checking for collisions...
ERROR: Symbol collision detected

Symbol 'std' already exists:
  - Namespace std (built-in, C++ standard library)

Rename aborted. No files modified.

Created issue: issue-001 "Symbol rename collision: calculateSum → std"
```

**Gates**: SYMBOL_COLLISION_CHECK (FAILED)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (issue created)

---

## AI Perspective (Heuristic)

**What AI notices**:
- TU build creates structured symbol database from compiler AST
- Symbol queries return file/line/column locations (precise navigation)
- Rename refactor is multi-file-aware (handles forward declarations, call sites)
- Collision detection prevents unsafe renames (reserved words, existing symbols)
- Autocomplete uses scope analysis from AST (local vars, functions, namespaces)

**What AI tries**:
- Parse compiler AST output to extract symbol graph
- Track symbol definitions vs references (def = 1, refs = many)
- Detect ambiguous symbols (same name, different scopes → requires disambiguation)
- Suggest rename targets based on naming conventions (camelCase → snake_case)
- Provide contextual autocomplete based on cursor position and scope

**Where AI tends to hallucinate**:
- May assume TU build works without successful compilation (it doesn't—build must pass first)
- May confuse symbol IDs across different TU builds (symbol-001 is target-specific)
- May suggest renaming symbols in header-only libraries (requires different strategy)
- May not account for macro-generated symbols (AST may not capture all macros)
- May assume autocomplete shows all symbols in project (it shows scope-limited symbols)

---

## Outcomes

### Outcome A: Rename Succeeds and Builds

**Flow** (as shown in main runbook):
1. Prerequisites satisfied (init, resolve, conf, build)
2. TU build creates AST index
3. Query identifies symbol with 3 locations
4. Rename checks for collisions (none found)
5. 3 locations updated across 2 files
6. Build verifies changes compile successfully

**Artifacts**:
- Modified source files: `src/math.cpp`, `src/main.cpp`
- TU database: `./docs/maestro/tu/target-cmake-mathapp.db`
- Build output confirms success

**Duration**: ~1 minute

### Outcome B: Ambiguity Detected — Symbol Collision Risk

**Flow**:
1. Prerequisites satisfied
2. TU build creates AST index
3. User attempts rename to existing symbol name
4. Collision check detects conflict (e.g., renaming to `std`)
5. Process aborts, no files modified
6. Issue created: `issue-001` with collision details

**Artifacts**:
- `./docs/maestro/issues/issue-001.json`:
  ```json
  {
    "id": "issue-001",
    "title": "Symbol rename collision: calculateSum → std",
    "description": "Attempted rename conflicts with existing symbol 'std' (namespace, C++ standard library)",
    "severity": "error",
    "status": "open",
    "created_by": "tu_refactor_rename"
  }
  ```

**User action**: Choose different rename target, or disambiguate with namespace

**Duration**: ~30 seconds (fast abort)

### Outcome C: TU Build Reveals Compilation Issues

**Flow**:
1. Prerequisites: init, resolve, conf complete
2. Build attempt fails (e.g., missing header)
3. TU build cannot proceed (requires successful compilation)
4. User fixes build errors
5. Retry: build succeeds, then TU build succeeds

**Example Error**:
```
[BUILD] ERROR: src/math.cpp:1:10: fatal error: missing_header.h: No such file or directory

TU build cannot proceed. Fix compilation errors first.
```

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "TODO_CMD: maestro build (exact syntax and options)"
  - "TODO_CMD: maestro tu build --target <target-id>"
  - "TODO_CMD: maestro tu query symbol --name <symbol-name>"
  - "TODO_CMD: maestro tu refactor rename --symbol <id> --to <new-name>"
  - "TODO_CMD: maestro tu autocomplete --file <path> --line <n> --col <n>"
  - "TODO_CMD: where TU database is stored (./docs/maestro/tu/ assumed)"
  - "TODO_CMD: whether TU build supports incremental updates (rebuild only changed files)"
  - "TODO_CMD: how symbol IDs are generated (symbol-001 format assumed)"
  - "TODO_CMD: whether autocomplete supports fuzzy matching or only prefix matching"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro tu build --target target-cmake-mathapp"
    intent: "Generate AST index from source files"
    gates: ["REPOCONF_GATE", "BUILD_SUCCESS"]
    stores_write: ["TU_DATABASE"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["invoke_compiler_ast", "parse_ast_output", "build_symbol_graph"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro tu query symbol --name calculateSum"
    intent: "Look up symbol in AST index"
    gates: ["TU_BUILT"]
    stores_write: []
    stores_read: ["TU_DATABASE"]
    internal: ["query_symbol_db"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro tu refactor rename --symbol symbol-001 --to computeSum"
    intent: "Rename symbol across all files"
    gates: ["TU_BUILT", "SYMBOL_COLLISION_CHECK"]
    stores_write: []  # Modifies source files directly
    stores_read: ["TU_DATABASE"]
    internal: ["check_collision", "find_all_references", "rewrite_source"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro tu autocomplete --file src/main.cpp --line 6 --col 20"
    intent: "Get autocomplete suggestions at cursor position"
    gates: ["TU_BUILT"]
    stores_write: []
    stores_read: ["TU_DATABASE"]
    internal: ["parse_scope_at_location", "filter_symbols_in_scope"]
    cli_confidence: "low"  # TODO_CMD

  - internal: "symbol collision check"
    intent: "Verify rename target doesn't conflict with existing symbols"
    gates: ["SYMBOL_COLLISION_CHECK"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]  # Creates issue if collision
    stores_read: ["TU_DATABASE"]
    result: "PASS or FAIL depending on collision detection"
    cli_confidence: "N/A"
```

---

**Related:** Translation units, AST indexing, symbol refactoring, code intelligence, autocomplete
**Status:** Proposed

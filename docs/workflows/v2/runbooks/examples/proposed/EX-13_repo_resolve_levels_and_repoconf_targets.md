# EX-13: RepoResolve Levels (Lite/Deep) + RepoConf Gating + Multi-Target Selection

**Scope**: Repository resolution mechanics, build system detection, target selection, RepoConf gate
**Build System**: CMake + Makefile (multi-target detection)
**Languages**: C++
**Outcome**: Demonstrate that "detect build system" is not a special case—it is the spine of `repo resolve`. Show lite vs deep resolution and how RepoConf gates further operations.

---

## Scenario Summary

Developer initializes Maestro in a repository with multiple build systems (CMakeLists.txt and Makefile). Running `maestro repo resolve --level lite` detects packages and targets. When multiple targets are found, user must select a default via RepoConf before build/TU operations can proceed. Deep resolution additionally checks conventions and creates issues for violations.

This demonstrates **RepoResolve as the foundation** for all downstream operations and **RepoConf as a required gate**.

---

## Preconditions

- Directory contains:
  - `CMakeLists.txt` (defines CMake project with executable target)
  - `Makefile` (defines make target)
  - `src/main.cpp` (minimal C++ source)
- Maestro not yet initialized

---

## Minimal Project Skeleton

```
my-app/
├── CMakeLists.txt
├── Makefile
└── src/
    └── main.cpp
```

**CMakeLists.txt**:
```cmake
cmake_minimum_required(VERSION 3.10)
project(MyApp)
add_executable(myapp src/main.cpp)
```

**Makefile**:
```make
all:
	g++ -o myapp src/main.cpp
```

**src/main.cpp**:
```cpp
#include <iostream>
int main() {
    std::cout << "Hello from MyApp!" << std::endl;
    return 0;
}
```

---

## Runbook Steps

### Step 1: Initialize Maestro

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro init` | Initialize repo truth | Creates `./docs/maestro/**` structure |

**Internal**:
- Creates `./docs/maestro/repo.json` with minimal metadata
- Creates empty directories for tasks/phases/tracks/workflows

**Gates**: (none - initialization always allowed)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO

### Step 2: Run Lite RepoResolve

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro repo resolve --level lite` | Detect build systems, packages, targets | Discovers CMake + Makefile, identifies 2 targets |

**Internal**:
- Scans repository for build files (CMakeLists.txt, Makefile, Cargo.toml, etc.)
- Parses build files to extract packages and targets
- Writes results to `./docs/maestro/repo.json`:
  ```json
  {
    "packages": [
      {
        "id": "pkg-001",
        "name": "MyApp",
        "build_system": "cmake",
        "targets": [
          {"id": "target-cmake-myapp", "name": "myapp", "type": "executable"}
        ]
      },
      {
        "id": "pkg-002",
        "name": "MyApp",
        "build_system": "make",
        "targets": [
          {"id": "target-make-myapp", "name": "myapp", "type": "executable"}
        ]
      }
    ],
    "repo_conf": {
      "default_target": null
    }
  }
  ```

**Gates**: REPO_RESOLVE_LITE
**Stores write**: REPO_TRUTH_DOCS_MAESTRO
**Stores read**: (filesystem - scans for build files)

**System Output**:
```
Scanning repository for build systems...
Found: CMakeLists.txt (cmake)
Found: Makefile (make)

Detected packages:
  - pkg-001: MyApp (cmake)
    - target-cmake-myapp: myapp [executable]
  - pkg-002: MyApp (make)
    - target-make-myapp: myapp [executable]

Multiple targets detected. Run 'maestro repo conf select-default-target <target-id>' to choose default.
```

### Step 3: Inspect RepoConf Status

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro repo conf show` | View current repo configuration | Shows default_target = null, lists available targets |

**System Output**:
```
Repository Configuration:

Default Target: (not set)

Available targets:
  - target-cmake-myapp (cmake: myapp)
  - target-make-myapp (make: myapp)

Note: Build and TU operations require a default target to be set.
Use: maestro repo conf select-default-target <target-id>
```

**Gates**: (none - read-only)
**Stores read**: REPO_TRUTH_DOCS_MAESTRO

### Step 4: Select Default Target

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro repo conf select-default-target target-cmake-myapp` | Set default target for build/TU operations | Updates repo.json with default_target |

**Internal**:
- Validates target exists in repo.json
- Updates `repo_conf.default_target` field
- Writes to `./docs/maestro/repo.json`

**System Output**:
```
Selected default target: target-cmake-myapp (cmake: myapp)

RepoConf gate now satisfied. Build and TU operations may proceed.
```

**Gates**: REPOCONF_GATE (now satisfied)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO

### Step 5: Attempt Build (RepoConf Gate Check)

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro make` | Build default target | Proceeds because RepoConf gate satisfied |

**Internal**:
- Checks REPOCONF_GATE: `repo_conf.default_target` must be non-null
- If satisfied: invokes build system (CMake in this case)
- If not satisfied: abort with error

**Gates**: REPOCONF_GATE (must pass before build)
**Stores read**: REPO_TRUTH_DOCS_MAESTRO

**System Output (if RepoConf satisfied)**:
```
[BUILD] Using default target: target-cmake-myapp
[BUILD] Build system: cmake
[BUILD] Running: cmake -S . -B build && cmake --build build
...
[BUILD] Success: myapp executable created
```

### Step 6: Run Deep RepoResolve (Optional)

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro repo refresh all` | Perform convention checking, advanced analysis | Checks file layout, naming conventions, creates issues for violations |

**Internal**:
- Runs all lite-level detection
- Additionally checks:
  - Naming conventions (e.g., headers in `include/`, sources in `src/`)
  - Directory structure conventions
  - File extensions and patterns
- Creates issues for any violations found

**System Output**:
```
Running deep resolve...

Lite resolve complete: 2 packages, 2 targets

Convention checks:
  - File layout: OK
  - Naming conventions: WARNING
    - Found header file src/main.cpp with no corresponding include/ directory
    - Created issue: issue-001 "Header/source separation convention violation"

Deep resolve complete.
Issues created: 1
View issues: maestro issues list
```

**Gates**: REPO_RESOLVE_DEEP, CONVENTIONS_GATE
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (issues added)

---

## Alternative Path: No Default Target Selected

### Step 4b: Attempt Build Without RepoConf

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro make` | Try to build without default target set | Fails at REPOCONF_GATE |

**System Output**:
```
ERROR: RepoConf gate not satisfied

No default target selected. Multiple targets available:
  - target-cmake-myapp (cmake: myapp)
  - target-make-myapp (make: myapp)

Select default target:
  maestro repo conf select-default-target <target-id>
```

**Gates**: REPOCONF_GATE (FAILED)

---

## AI Perspective (Heuristic)

**What AI notices**:
- Multiple build files present (CMakeLists.txt, Makefile) → multi-build-system project
- RepoConf gate blocks build/TU operations until default target chosen
- Deep resolve triggers convention checks beyond basic target detection
- Issue created for convention violation can be linked to task

**What AI tries**:
- Parse build files to extract target names and types
- Detect ambiguity when multiple targets exist with same name
- Suggest default target based on heuristics (e.g., prefer CMake over Makefile)
- Check file layout matches common conventions (headers in include/, sources in src/)

**Where AI tends to hallucinate**:
- May assume target-cmake-myapp and target-make-myapp are the same (they're not—different build systems)
- May suggest running build before RepoConf gate satisfied
- May confuse lite vs deep resolve capabilities (lite doesn't check conventions)
- May assume convention violations block build (they don't—they create issues but don't gate)

---

## Outcomes

### Outcome A: Single Target Auto-Selected

**Flow**:
1. Run `maestro repo resolve --level lite`
2. Only one target detected
3. Maestro auto-selects default target
4. RepoConf gate automatically satisfied
5. Build proceeds without manual selection

**Artifacts**:
- `./docs/maestro/repo.json` with `repo_conf.default_target` set
- No user intervention needed

### Outcome B: Multiple Targets Detected → User Chooses Default

**Flow** (as shown in main runbook):
1. Run `maestro repo resolve --level lite`
2. Two targets detected (cmake + make)
3. User runs `maestro repo conf select-default-target target-cmake-myapp`
4. RepoConf gate satisfied
5. Build proceeds with selected target

**Artifacts**:
- `./docs/maestro/repo.json` with chosen default target
- Other target still available but not default

### Outcome C: Deep Resolve Finds Convention Violations → Issues Created

**Flow**:
1. Run `maestro repo resolve --level deep`
2. Convention check detects layout violation (no include/ directory)
3. Issue created: `issue-001`
4. User can:
   - Fix violation (create include/ directory, move headers)
   - Ignore issue (mark as accepted deviation)
   - Create task from issue to track fix work

**Artifacts**:
- `./docs/maestro/issues/issue-001.json`:
  ```json
  {
    "id": "issue-001",
    "title": "Header/source separation convention violation",
    "description": "Found header files in src/ without corresponding include/ directory",
    "severity": "warning",
    "status": "open",
    "created_by": "repo_resolve_deep"
  }
  ```

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "TODO_CMD: maestro repo conf show"
  - "TODO_CMD: maestro repo conf select-default-target <target-id>"
  - "TODO_CMD: maestro build (syntax and options)"
  - "TODO_CMD: maestro repo resolve --level deep (current syntax for deep mode)"
  - "TODO_CMD: how auto-selection works for single-target repos"
  - "TODO_CMD: whether user can switch default target after initial selection"
  - "TODO_CMD: whether RepoConf stores other settings beyond default_target"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro init"
    intent: "Initialize Maestro repo truth"
    gates: []
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: []
    internal: ["create_repo_structure"]
    cli_confidence: "high"

  - user: "maestro repo resolve --level lite"
    intent: "Detect build systems, packages, targets"
    gates: ["REPO_RESOLVE_LITE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: []
    internal: ["scan_build_files", "parse_build_systems", "extract_targets"]
    cli_confidence: "medium"

  - user: "maestro repo conf show"
    intent: "View current repo configuration and available targets"
    gates: []
    stores_write: []
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["read_repo_conf"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro repo conf select-default-target target-cmake-myapp"
    intent: "Set default target for build/TU operations"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["validate_target_exists", "update_repo_conf"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro build"
    intent: "Build default target"
    gates: ["REPOCONF_GATE"]
    stores_write: []
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["check_repoconf_gate", "invoke_build_system"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro repo resolve --level deep"
    intent: "Perform deep analysis with convention checking"
    gates: ["REPO_RESOLVE_DEEP", "CONVENTIONS_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["run_lite_resolve", "check_conventions", "create_issues"]
    cli_confidence: "low"  # TODO_CMD
```

---

**Related:** RepoResolve mechanics, RepoConf gating, build system detection, multi-target selection, convention checking
**Status:** Proposed

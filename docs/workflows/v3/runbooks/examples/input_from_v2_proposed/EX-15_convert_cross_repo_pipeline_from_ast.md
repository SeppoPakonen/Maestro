# EX-15: Convert Cross-Repo Pipeline from AST — Export and Task Generation

**Scope**: Convert pipelines (cross-repository code export using AST as input)
**Build System**: CMake (source), Python Poetry (target)
**Languages**: C++ (source), Python (target)
**Outcome**: Demonstrate that convert is an export pipeline: source repo produces AST, target repo receives tasks and code artifacts. Show how conversion plans are discussed, approved, and executed.

---

## Scenario Summary

Developer has a C++ project with AST already indexed (from EX-14). They want to create a Python equivalent in a new repository. Using `maestro convert`, they create a conversion pipeline that exports AST-driven code artifacts to the target repo, where tasks are auto-generated for AI-assisted implementation.

This demonstrates **Convert as a cross-repo export mechanism** with AST as the structured input.

---

## Preconditions

- **Source repo** (`my-cpp-project/`):
  - Maestro initialized
  - AST index exists (from `maestro tu build`, see EX-14)
  - Contains `src/math.cpp` with `computeSum` function
- **Target repo** (`my-python-project/`):
  - Empty directory or minimal Python project structure
  - Maestro will be initialized during conversion

---

## Minimal Project Skeletons

### Source Repo (`my-cpp-project/`)

```
my-cpp-project/
├── docs/
│   └── maestro/
│       ├── repo.json
│       └── tu/
│           └── target-cmake-mathapp.db  # AST index from EX-14
├── CMakeLists.txt
└── src/
    ├── math.cpp
    └── main.cpp
```

**src/math.cpp** (already exists from EX-14, renamed symbol):
```cpp
#include <iostream>

int computeSum(int a, int b) {
    return a + b;
}
```

### Target Repo (`my-python-project/`)

Initial state: empty or minimal:
```
my-python-project/
└── (empty or pyproject.toml stub)
```

---

## Runbook Steps

### In Source Repo: Create Conversion Pipeline

#### Step 1: Create New Conversion Pipeline

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro convert add cpp-to-python` | Create new conversion pipeline | Pipeline created in `./docs/maestro/convert/cpp-to-python.json` |

**Internal**:
- Creates pipeline metadata file
- Initializes empty conversion plan
- Links to source AST (TU database)

**System Output**:
```
[CONVERT] Created conversion pipeline: cpp-to-python
[CONVERT] Pipeline file: ./docs/maestro/convert/cpp-to-python.json

Next steps:
  1. Plan conversion: maestro convert plan cpp-to-python
  2. Run conversion: maestro convert run cpp-to-python --out <target-path>
```

**Gates**: (none - creation always allowed)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (convert pipeline added)

#### Step 2: Plan Conversion (Optional AI Discussion)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro convert plan cpp-to-python` | Discuss conversion strategy with AI | AI suggests conversion tasks, user approves |

**AI Discussion**:
```
AI: I've analyzed the AST for this C++ project. Here's my suggested conversion plan for Python:

Conversion Tasks:
1. Create Python package structure (src/, pyproject.toml)
2. Convert computeSum function to Python:
   - Input: AST symbol-001 (computeSum, int(int,int))
   - Output: Python function with type hints
3. Create unit tests (pytest)
4. Generate documentation (docstrings)

Would you like me to add any additional conversion tasks?

User: Looks good, proceed.

AI: Plan saved. Run 'maestro convert run cpp-to-python --out ../my-python-project' to execute.
```

**Internal**:
- Reads AST from TU database
- Identifies symbols to convert (functions, classes, types)
- Proposes conversion mapping (C++ → Python equivalents)
- Saves plan to `./docs/maestro/convert/cpp-to-python.json`

**Gates**: TU_BUILT (AST must exist)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (conversion plan updated)
**Stores read**: TU_DATABASE

#### Step 3: Run Conversion Pipeline

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro convert run cpp-to-python --out ../my-python-project` | Execute conversion, export artifacts to target repo | Creates files in target, generates tasks |

**Internal**:
- Reads conversion plan
- For each planned task:
  - Generate code artifacts from AST (e.g., Python function stub from C++ function)
  - Write artifacts to target repo
  - Create task in target repo's Maestro structure
- Initialize Maestro in target repo if not already initialized

**System Output**:
```
[CONVERT] Running pipeline: cpp-to-python
[CONVERT] Target: ../my-python-project

[CONVERT] Task 1: Create Python package structure
[CONVERT]   - Created: ../my-python-project/src/
[CONVERT]   - Created: ../my-python-project/pyproject.toml
[CONVERT]   - Created task: task-001 "Set up Python package structure"

[CONVERT] Task 2: Convert computeSum function
[CONVERT]   - Reading AST: symbol-001 (computeSum)
[CONVERT]   - Generated Python stub: ../my-python-project/src/math.py
[CONVERT]   - Created task: task-002 "Implement computeSum in Python"

[CONVERT] Task 3: Create unit tests
[CONVERT]   - Created: ../my-python-project/tests/test_math.py (stub)
[CONVERT]   - Created task: task-003 "Write tests for computeSum"

[CONVERT] Conversion complete. 3 tasks created in target repo.
```

**Artifacts created in target repo**:
- `src/math.py` (stub generated from AST)
- `pyproject.toml` (minimal Python project config)
- `tests/test_math.py` (test stub)
- `docs/maestro/tasks/task-001.json`, `task-002.json`, `task-003.json`

**Gates**: TU_BUILT (source), CONVERT_PLAN_APPROVED
**Stores write**: (target repo) REPO_TRUTH_DOCS_MAESTRO
**Stores read**: (source repo) TU_DATABASE, REPO_TRUTH_DOCS_MAESTRO

---

### In Target Repo: Implement Conversion Tasks

#### Step 4: Initialize Target Repo (if not done by convert)

| Command | Intent | Expected |
|---------|--------|----------|
| `cd ../my-python-project && maestro init` | Initialize Maestro in target | Creates `./docs/maestro/**` (may be done automatically by convert) |

**System Output**:
```
Maestro already initialized (by convert pipeline).

Tasks imported from conversion:
  - task-001: Set up Python package structure
  - task-002: Implement computeSum in Python
  - task-003: Write tests for computeSum
```

#### Step 5: View Generated Code Stub

| Command | Intent | Expected |
|---------|--------|----------|
| `cat src/math.py` | View generated Python stub | Shows function signature with TODO comment |

**Generated `src/math.py`**:
```python
# Auto-generated from C++ source: src/math.cpp
# Original function: computeSum (int, int) -> int

def compute_sum(a: int, b: int) -> int:
    """
    Compute the sum of two integers.

    Converted from C++ function: computeSum
    """
    # TODO: Implement logic (original C++ returned a + b)
    raise NotImplementedError("Auto-generated stub - implementation needed")
```

#### Step 6: Work on Conversion Task

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro work task task-002` | Start AI-assisted work on task | AI helps implement Python function |

**Work Session**:
```
AI: I see this is a conversion task from C++. The original function returned a + b.
    Shall I implement the Python equivalent?

User: Yes, implement it.

AI: [Writes to src/math.py]:

def compute_sum(a: int, b: int) -> int:
    """
    Compute the sum of two integers.

    Converted from C++ function: computeSum
    """
    return a + b

Implementation complete. Would you like me to mark this task as done?

User: /done
```

**System Output**:
```
[WORK SESSION] Task task-002 marked as completed.
[WORK SESSION] Updated: ./docs/maestro/tasks/task-002.json
```

**Gates**: REPOCONF_GATE (target repo), TASK_EXISTS
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (target repo)

---

## Alternative Path: Conversion Plan Incomplete

### Step 3b: Conversion Plan Stays Proposed

**Scenario**: AI cannot auto-generate all artifacts from AST (e.g., complex C++ templates with no Python equivalent)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro convert run cpp-to-python --out ../my-python-project` | Attempt conversion with incomplete plan | Aborts, asks user to revise plan |

**System Output**:
```
[CONVERT] Running pipeline: cpp-to-python
[CONVERT] Checking conversion plan...

WARNING: Conversion plan has ambiguities:
  - Task 2: Cannot auto-convert C++ template <typename T> to Python
  - Suggestion: Create manual task for template conversion

Conversion aborted. Revise plan:
  maestro convert plan cpp-to-python --revise
```

**User Action**:
- Revise plan to mark template conversion as manual task
- Retry conversion with revised plan

---

## AI Perspective (Heuristic)

**What AI notices**:
- AST provides structured input (function signatures, types, call graphs)
- Conversion is language-pair-specific (C++ → Python different from C++ → Rust)
- Generated stubs preserve function signatures but require manual logic implementation
- Tasks in target repo guide AI on what to implement

**What AI tries**:
- Map C++ types to Python equivalents (int → int, std::string → str, etc.)
- Convert naming conventions (camelCase → snake_case for Python)
- Generate type hints in Python from C++ type signatures
- Create pytest stubs from C++ function names (test_compute_sum for computeSum)

**Where AI tends to hallucinate**:
- May assume complex C++ templates can be auto-converted (they often can't)
- May generate incorrect Python equivalents for C++ pointer/reference types
- May forget to handle C++ exceptions vs Python exceptions (different semantics)
- May assume conversion is bidirectional (Python → C++ is harder than C++ → Python)

---

## Outcomes

### Outcome A: Mechanical Conversion Creates Most Files, AI Fills Gaps

**Flow** (as shown in main runbook):
1. Source repo: AST exists, conversion pipeline created
2. Run conversion: 3 tasks + stubs generated in target repo
3. Target repo: AI works on task-002, implements Python function
4. User runs tests, marks task complete

**Artifacts**:
- Source repo: `./docs/maestro/convert/cpp-to-python.json`
- Target repo:
  - `src/math.py` (implemented)
  - `pyproject.toml`
  - `tests/test_math.py` (stub)
  - `./docs/maestro/tasks/` (3 tasks, 1 completed)

**Duration**: ~5 minutes (mostly automated)

### Outcome B: Conversion Plan Incomplete → Stays Proposed, User Revises

**Flow**:
1. Conversion plan created
2. AI identifies ambiguity (e.g., cannot convert C++ template)
3. Conversion aborted with warning
4. User revises plan: marks template task as manual
5. Retry: conversion succeeds, creates tasks including manual one

**Artifacts**:
- Conversion plan marked with manual tasks
- Target repo has mix of auto-generated stubs and manual task descriptions

**Duration**: ~10 minutes (includes revision)

### Outcome C: Conversion from AST Reveals Source Issues

**Flow**:
1. Conversion starts
2. AST analysis finds incomplete type information (e.g., missing function definitions)
3. Conversion creates issue in source repo: "Incomplete AST for symbol X"
4. User fixes source code, rebuilds TU
5. Retry conversion: succeeds

**Example Issue**:
```json
{
  "id": "issue-001",
  "title": "Incomplete AST for symbol computeAverage",
  "description": "Function computeAverage declared but not defined in TU. Cannot convert.",
  "severity": "error",
  "status": "open",
  "created_by": "convert_pipeline"
}
```

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "maestro convert add <pipeline-name>"
  - "TODO_CMD: maestro convert plan <pipeline> (with optional --revise)"
  - "TODO_CMD: maestro convert run <pipeline> --out <target-path>"
  - "TODO_CMD: how conversion plans are stored (format, location)"
  - "TODO_CMD: whether conversions can be templated (e.g., cpp-to-python as reusable template)"
  - "TODO_CMD: how AST symbols are referenced in conversion plans (symbol IDs?)"
  - "TODO_CMD: whether conversions support incremental updates (re-run on AST changes)"
  - "TODO_CMD: how target repo Maestro initialization is handled (auto vs manual)"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro convert new cpp-to-python"
    intent: "Create new conversion pipeline"
    gates: []
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: []
    internal: ["create_pipeline_metadata"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro convert plan cpp-to-python"
    intent: "Discuss and approve conversion strategy with AI"
    gates: ["TU_BUILT"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: ["TU_DATABASE", "REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["analyze_ast", "propose_conversion_tasks"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro convert run cpp-to-python --out ../my-python-project"
    intent: "Execute conversion pipeline, export artifacts to target repo"
    gates: ["TU_BUILT", "CONVERT_PLAN_APPROVED"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO (target)"]
    stores_read: ["TU_DATABASE", "REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["generate_code_stubs", "create_target_tasks", "init_target_maestro"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro work task task-002"
    intent: "Implement conversion task in target repo"
    gates: ["REPOCONF_GATE (target)", "TASK_EXISTS"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO (target)"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO (target)"]
    internal: ["load_task_context", "ai_assisted_implementation"]
    cli_confidence: "low"  # TODO_CMD
```

---

**Related:** Cross-repo conversion, AST-driven code generation, task export, conversion pipelines
**Status:** Proposed

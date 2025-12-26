#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-15: Convert Cross-Repo Pipeline from AST — Export and Task Generation

echo "=== Convert: Cross-Repo Export Mechanism with AST Input ==="
echo "Pipeline: Source repo AST → Conversion plan → Target repo tasks + stubs"

echo ""
echo "=== Preconditions ===\"
echo "Source repo (my-cpp-project/):"
echo "  - Maestro initialized"
echo "  - AST index exists (from EX-14)"
echo "  - Contains src/math.cpp with computeSum function"
echo ""
echo "Target repo (my-python-project/):"
echo "  - Empty directory or minimal Python structure"

echo ""
echo "=== In Source Repo: Create Conversion Pipeline ===\"

echo ""
echo "=== Step 1: Create New Conversion Pipeline ===\"

run maestro convert new cpp-to-python  # TODO_CMD
# EXPECT: Pipeline created in ./docs/maestro/convert/cpp-to-python.json
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)
# INTERNAL: create_pipeline_metadata

echo ""
echo "[CONVERT] Created conversion pipeline: cpp-to-python"
echo "[CONVERT] Pipeline file: ./docs/maestro/convert/cpp-to-python.json"
echo ""
echo "Next steps:"
echo "  1. Plan conversion: maestro convert plan cpp-to-python"
echo "  2. Run conversion: maestro convert run cpp-to-python --out <target-path>"

echo ""
echo "=== Step 2: Plan Conversion (Optional AI Discussion) ===\"

run maestro convert plan cpp-to-python  # TODO_CMD
# EXPECT: AI suggests conversion tasks, user approves
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO (conversion plan updated)
# STORES_READ: TU_DATABASE, REPO_TRUTH_DOCS_MAESTRO
# GATES: TU_BUILT
# INTERNAL: analyze_ast, propose_conversion_tasks

echo ""
echo "AI: I've analyzed the AST for this C++ project. Here's my suggested conversion plan for Python:"
echo ""
echo "Conversion Tasks:"
echo "1. Create Python package structure (src/, pyproject.toml)"
echo "2. Convert computeSum function to Python:"
echo "   - Input: AST symbol-001 (computeSum, int(int,int))"
echo "   - Output: Python function with type hints"
echo "3. Create unit tests (pytest)"
echo "4. Generate documentation (docstrings)"
echo ""
echo "Would you like me to add any additional conversion tasks?"
echo ""
echo "User: Looks good, proceed."
echo ""
echo "AI: Plan saved. Run 'maestro convert run cpp-to-python --out ../my-python-project' to execute."

echo ""
echo "=== Step 3: Run Conversion Pipeline ===\"

run maestro convert run cpp-to-python --out ../my-python-project  # TODO_CMD
# EXPECT: Creates files in target, generates tasks
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO (target repo)
# STORES_READ: TU_DATABASE, REPO_TRUTH_DOCS_MAESTRO (source repo)
# GATES: TU_BUILT, CONVERT_PLAN_APPROVED
# INTERNAL: generate_code_stubs, create_target_tasks, init_target_maestro

echo ""
echo "[CONVERT] Running pipeline: cpp-to-python"
echo "[CONVERT] Target: ../my-python-project"
echo ""
echo "[CONVERT] Task 1: Create Python package structure"
echo "[CONVERT]   - Created: ../my-python-project/src/"
echo "[CONVERT]   - Created: ../my-python-project/pyproject.toml"
echo "[CONVERT]   - Created task: task-001 \"Set up Python package structure\""
echo ""
echo "[CONVERT] Task 2: Convert computeSum function"
echo "[CONVERT]   - Reading AST: symbol-001 (computeSum)"
echo "[CONVERT]   - Generated Python stub: ../my-python-project/src/math.py"
echo "[CONVERT]   - Created task: task-002 \"Implement computeSum in Python\""
echo ""
echo "[CONVERT] Task 3: Create unit tests"
echo "[CONVERT]   - Created: ../my-python-project/tests/test_math.py (stub)"
echo "[CONVERT]   - Created task: task-003 \"Write tests for computeSum\""
echo ""
echo "[CONVERT] Conversion complete. 3 tasks created in target repo."

echo ""
echo "Artifacts created in target repo:"
echo "  - src/math.py (stub generated from AST)"
echo "  - pyproject.toml (minimal Python project config)"
echo "  - tests/test_math.py (test stub)"
echo "  - docs/maestro/tasks/task-001.json, task-002.json, task-003.json"

echo ""
echo "=== In Target Repo: Implement Conversion Tasks ===\"

echo ""
echo "=== Step 4: Initialize Target Repo (if not done by convert) ===\"

run cd ../my-python-project
run maestro init
# EXPECT: May already be initialized by convert pipeline
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO (target)

echo ""
echo "Maestro already initialized (by convert pipeline)."
echo ""
echo "Tasks imported from conversion:"
echo "  - task-001: Set up Python package structure"
echo "  - task-002: Implement computeSum in Python"
echo "  - task-003: Write tests for computeSum"

echo ""
echo "=== Step 5: View Generated Code Stub ===\"

run cat src/math.py

echo ""
echo "# Auto-generated from C++ source: src/math.cpp"
echo "# Original function: computeSum (int, int) -> int"
echo ""
echo "def compute_sum(a: int, b: int) -> int:"
echo "    \"\"\""
echo "    Compute the sum of two integers."
echo ""
echo "    Converted from C++ function: computeSum"
echo "    \"\"\""
echo "    # TODO: Implement logic (original C++ returned a + b)"
echo "    raise NotImplementedError(\"Auto-generated stub - implementation needed\")"

echo ""
echo "=== Step 6: Work on Conversion Task ===\"

run maestro work task task-002  # TODO_CMD
# EXPECT: AI helps implement Python function
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO (target)
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO (target)
# GATES: REPOCONF_GATE (target), TASK_EXISTS
# INTERNAL: load_task_context, ai_assisted_implementation

echo ""
echo "AI: I see this is a conversion task from C++. The original function returned a + b."
echo "    Shall I implement the Python equivalent?"
echo ""
echo "User: Yes, implement it."
echo ""
echo "AI: [Writes to src/math.py]:"
echo ""
echo "def compute_sum(a: int, b: int) -> int:"
echo "    \"\"\""
echo "    Compute the sum of two integers."
echo ""
echo "    Converted from C++ function: computeSum"
echo "    \"\"\""
echo "    return a + b"
echo ""
echo "Implementation complete. Would you like me to mark this task as done?"
echo ""
echo "User: /done"
echo ""
echo "[WORK SESSION] Task task-002 marked as completed."
echo "[WORK SESSION] Updated: ./docs/maestro/tasks/task-002.json"

echo ""
echo "=== Alternative Path: Conversion Plan Incomplete ===\"

run cd ../my-cpp-project  # Back to source repo
run maestro convert run cpp-to-python --out ../my-python-project  # TODO_CMD
# EXPECT: Aborts if plan has ambiguities
# STORES_WRITE: (none - aborted)

echo ""
echo "[CONVERT] Running pipeline: cpp-to-python"
echo "[CONVERT] Checking conversion plan..."
echo ""
echo "WARNING: Conversion plan has ambiguities:"
echo "  - Task 2: Cannot auto-convert C++ template <typename T> to Python"
echo "  - Suggestion: Create manual task for template conversion"
echo ""
echo "Conversion aborted. Revise plan:"
echo "  maestro convert plan cpp-to-python --revise"

echo ""
echo "=== Outcome A: Mechanical Conversion Creates Most Files, AI Fills Gaps ===\"
echo "Flow:"
echo "  1. Source repo: AST exists, conversion pipeline created"
echo "  2. Run conversion: 3 tasks + stubs generated in target repo"
echo "  3. Target repo: AI works on task-002, implements Python function"
echo "  4. User runs tests, marks task complete"
echo ""
echo "Artifacts:"
echo "  - Source: ./docs/maestro/convert/cpp-to-python.json"
echo "  - Target:"
echo "    - src/math.py (implemented)"
echo "    - pyproject.toml"
echo "    - tests/test_math.py (stub)"
echo "    - ./docs/maestro/tasks/ (3 tasks, 1 completed)"
echo ""
echo "Duration: ~5 minutes (mostly automated)"

echo ""
echo "=== Outcome B: Conversion Plan Incomplete → Stays Proposed, User Revises ===\"
echo "Flow:"
echo "  1. Conversion plan created"
echo "  2. AI identifies ambiguity (e.g., cannot convert C++ template)"
echo "  3. Conversion aborted with warning"
echo "  4. User revises plan: marks template task as manual"
echo "  5. Retry: conversion succeeds, creates tasks including manual one"
echo ""
echo "Duration: ~10 minutes (includes revision)"

echo ""
echo "=== Outcome C: Conversion from AST Reveals Source Issues ===\"
echo "Flow:"
echo "  1. Conversion starts"
echo "  2. AST analysis finds incomplete type information"
echo "  3. Conversion creates issue in source repo: \"Incomplete AST for symbol X\""
echo "  4. User fixes source code, rebuilds TU"
echo "  5. Retry conversion: succeeds"
echo ""
echo "Example Issue:"
echo "  issue-001: \"Incomplete AST for symbol computeAverage\""
echo "  Description: \"Function computeAverage declared but not defined in TU. Cannot convert.\""

echo ""
echo "=== Key Insights ===\"
echo "  - Convert is a cross-repo export mechanism (source → target)"
echo "  - AST provides structured input for conversion (types, signatures, call graphs)"
echo "  - Target repo receives tasks + code stubs (AI fills in logic)"
echo "  - Conversion plans can be discussed with AI before execution"
echo "  - Incomplete plans abort early (fail fast, not silent failures)"

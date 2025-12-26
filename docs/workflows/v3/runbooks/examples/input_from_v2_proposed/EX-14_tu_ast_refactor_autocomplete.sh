#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-14: TU/AST Pipeline — Build Translation Units, Refactor Rename, Autocomplete Query

echo "=== TU/AST: Foundation for Refactoring and Code Intelligence ==="
echo "Pipeline: RepoResolve + RepoConf → Build → TU Build → AST Index → Refactor/Query"

echo ""
echo "=== Minimal Project Skeleton ==="
echo "my-cpp-project/"
echo "├── CMakeLists.txt"
echo "├── src/"
echo "│   ├── math.cpp (defines calculateSum)"
echo "│   └── main.cpp (calls calculateSum)"

echo ""
echo "=== Prerequisites Checklist ===\"
echo "Before TU/AST operations:"
echo "  1. Maestro initialized"
echo "  2. RepoResolve complete"
echo "  3. RepoConf default target set"
echo "  4. Build succeeds"

echo ""
echo "=== Step 1: Initialize and Resolve ===\"

run maestro init
# EXPECT: Creates ./docs/maestro/**
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)

echo ""
echo "[INIT] Created ./docs/maestro/repo.json"

run maestro repo resolve --level lite
# EXPECT: Discovers CMakeLists.txt, one target
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_LITE

echo ""
echo "Detected packages:"
echo "  - pkg-001: MathApp (cmake)"
echo "    - target-cmake-mathapp: mathapp [executable]"
echo ""
echo "Single target detected. Auto-selected as default."

echo ""
echo "=== Step 2: Build Project ===\"

run maestro build  # TODO_CMD
# EXPECT: Build succeeds
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo ""
echo "[BUILD] Using default target: target-cmake-mathapp"
echo "[BUILD] Running: cmake -S . -B build && cmake --build build"
echo "..."
echo "[BUILD] Success: mathapp executable created"

echo ""
echo "=== Step 3: Build Translation Units (TU) ===\"

run maestro tu build --target target-cmake-mathapp  # TODO_CMD
# EXPECT: Creates AST index with symbol information
# STORES_WRITE: TU_DATABASE
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE, BUILD_SUCCESS
# INTERNAL: invoke_compiler_ast, parse_ast_output, build_symbol_graph

echo ""
echo "[TU BUILD] Building translation units for target: target-cmake-mathapp"
echo "[TU BUILD] Analyzing: src/math.cpp"
echo "[TU BUILD]   - Found function: calculateSum (line 3, col 5)"
echo "[TU BUILD] Analyzing: src/main.cpp"
echo "[TU BUILD]   - Found reference: calculateSum (line 6, col 18)"
echo "[TU BUILD] AST index created: ./docs/maestro/tu/target-cmake-mathapp.db"
echo "[TU BUILD] Total symbols: 2"

echo ""
echo "=== Step 4: Query Symbol Information ===\"

run maestro tu query symbol --name calculateSum  # TODO_CMD
# EXPECT: Returns symbol ID, definitions, references
# STORES_READ: TU_DATABASE
# GATES: TU_BUILT

echo ""
echo "Symbol: calculateSum"
echo ""
echo "Definitions:"
echo "  - symbol-001: calculateSum (function)"
echo "    File: src/math.cpp"
echo "    Line: 3, Column: 5"
echo "    Type: int(int, int)"
echo ""
echo "References:"
echo "  - src/main.cpp:3:5 (forward declaration)"
echo "  - src/main.cpp:6:18 (call site)"
echo ""
echo "Total references: 2"

echo ""
echo "=== Step 5: Refactor — Rename Symbol ===\"

run maestro tu refactor rename --symbol symbol-001 --to computeSum  # TODO_CMD
# EXPECT: Updates definition and all references
# STORES_READ: TU_DATABASE
# GATES: TU_BUILT, SYMBOL_COLLISION_CHECK
# INTERNAL: check_collision, find_all_references, rewrite_source

echo ""
echo "[REFACTOR] Renaming symbol: calculateSum → computeSum"
echo "[REFACTOR] Checking for collisions... OK"
echo "[REFACTOR] Updating 3 locations:"
echo "[REFACTOR]   - src/math.cpp:3:5 (definition)"
echo "[REFACTOR]   - src/main.cpp:3:5 (forward declaration)"
echo "[REFACTOR]   - src/main.cpp:6:18 (call site)"
echo "[REFACTOR] Rename complete."
echo ""
echo "Recommendation: Run 'maestro build' to verify changes compile."

echo ""
echo "Files modified:"
echo "  - src/math.cpp: int calculateSum(...) → int computeSum(...)"
echo "  - src/main.cpp: calculateSum(...) → computeSum(...)"

echo ""
echo "=== Step 6: Verify Refactor with Build ===\"

run maestro build  # TODO_CMD
# EXPECT: Build succeeds
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo ""
echo "[BUILD] Using default target: target-cmake-mathapp"
echo "[BUILD] Running: cmake --build build"
echo "..."
echo "[BUILD] Success: mathapp executable created"

echo ""
echo "=== Step 7: Autocomplete Query ===\"

run maestro tu autocomplete --file src/main.cpp --line 6 --col 20  # TODO_CMD
# EXPECT: Returns available symbols in scope
# STORES_READ: TU_DATABASE
# GATES: TU_BUILT
# INTERNAL: parse_scope_at_location, filter_symbols_in_scope

echo ""
echo "[AUTOCOMPLETE] File: src/main.cpp, Line: 6, Column: 20"
echo ""
echo "Suggestions:"
echo "  - computeSum (function, int(int, int)) [current context]"
echo ""
echo "Available in scope:"
echo "  - std::cout (object, std::ostream)"
echo "  - result (variable, int)"
echo "  - main (function, int())"
echo ""
echo "No additional suggestions at this location."

echo ""
echo "=== Alternative Path: Symbol Collision Detected ===\"

run maestro tu refactor rename --symbol symbol-001 --to std  # TODO_CMD
# EXPECT: Fails with collision error
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO (issue created)
# GATES: SYMBOL_COLLISION_CHECK (FAILED)

echo ""
echo "[REFACTOR] Renaming symbol: calculateSum → std"
echo "[REFACTOR] Checking for collisions..."
echo "ERROR: Symbol collision detected"
echo ""
echo "Symbol 'std' already exists:"
echo "  - Namespace std (built-in, C++ standard library)"
echo ""
echo "Rename aborted. No files modified."
echo ""
echo "Created issue: issue-001 \"Symbol rename collision: calculateSum → std\""

echo ""
echo "=== Outcome A: Rename Succeeds and Builds ===\"
echo "Flow:"
echo "  1. Prerequisites satisfied (init, resolve, conf, build)"
echo "  2. TU build creates AST index"
echo "  3. Query identifies symbol with 3 locations"
echo "  4. Rename checks for collisions (none found)"
echo "  5. 3 locations updated across 2 files"
echo "  6. Build verifies changes compile successfully"
echo ""
echo "Artifacts:"
echo "  - Modified: src/math.cpp, src/main.cpp"
echo "  - TU database: ./docs/maestro/tu/target-cmake-mathapp.db"
echo ""
echo "Duration: ~1 minute"

echo ""
echo "=== Outcome B: Ambiguity Detected — Symbol Collision Risk ===\"
echo "Flow:"
echo "  1. Prerequisites satisfied"
echo "  2. TU build creates AST index"
echo "  3. User attempts rename to existing symbol (e.g., 'std')"
echo "  4. Collision check detects conflict"
echo "  5. Process aborts, no files modified"
echo "  6. Issue created: issue-001 with collision details"
echo ""
echo "User action: Choose different rename target"
echo ""
echo "Duration: ~30 seconds (fast abort)"

echo ""
echo "=== Outcome C: TU Build Reveals Compilation Issues ===\"
echo "Flow:"
echo "  1. Prerequisites: init, resolve, conf complete"
echo "  2. Build attempt fails (e.g., missing header)"
echo "  3. TU build cannot proceed (requires successful compilation)"
echo "  4. User fixes build errors"
echo "  5. Retry: build succeeds, then TU build succeeds"
echo ""
echo "Example Error:"
echo "[BUILD] ERROR: src/math.cpp:1:10: fatal error: missing_header.h: No such file or directory"
echo ""
echo "TU build cannot proceed. Fix compilation errors first."

echo ""
echo "=== Key Insights ===\"
echo "  - TU build requires successful compilation (build must pass first)"
echo "  - AST index enables precise symbol navigation (file/line/col)"
echo "  - Rename is multi-file-aware (handles forward declarations, call sites)"
echo "  - Collision detection prevents unsafe renames (reserved words, existing symbols)"
echo "  - Autocomplete uses scope analysis from AST (context-aware suggestions)"

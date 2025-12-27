#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }
MAESTRO_BIN="${MAESTRO_BIN:-maestro}"

# EX-13: RepoResolve Levels (Lite/Deep) + RepoConf Gating + Multi-Target Selection

echo "=== RepoResolve: The Spine of Build System Detection ==="
echo "Principle: 'Detect build system' is not a special case—it IS repo resolve"
echo ""
echo "Levels:"
echo "  - lite:  detect build systems, packages, targets"
echo "  - deep:  + convention checking, issue creation"

echo ""
echo "=== Minimal Project Skeleton ==="
echo "my-app/"
echo "├── CMakeLists.txt"
echo "├── Makefile"
echo "└── src/"
echo "    └── main.cpp"

echo ""
echo "=== Step 1: Initialize Maestro ===\"

run "$MAESTRO_BIN" init
# EXPECT: Creates ./docs/maestro/** structure
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)

echo ""
echo "[INIT] Created ./docs/maestro/repo.json"
echo "[INIT] Created directories: tasks/, phases/, tracks/, workflows/"

echo ""
echo "=== Step 2: Run Lite RepoResolve ===\"

run "$MAESTRO_BIN" repo resolve
# EXPECT: Detects CMake + Makefile, identifies 2 targets
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# STORES_READ: (filesystem - scans for build files)
# GATES: REPO_RESOLVE_LITE
# INTERNAL: scan_build_files, parse_build_systems, extract_targets

echo ""
echo "Scanning repository for build systems..."
echo "Found: CMakeLists.txt (cmake)"
echo "Found: Makefile (make)"
echo ""
echo "Detected packages:"
echo "  - pkg-001: MyApp (cmake)"
echo "    - target-cmake-myapp: myapp [executable]"
echo "  - pkg-002: MyApp (make)"
echo "    - target-make-myapp: myapp [executable]"
echo ""
echo "Multiple targets detected. Run 'maestro repo conf select-default target <target-id>' to choose default."

echo ""
echo "=== Step 3: Inspect RepoConf Status ===\"

run "$MAESTRO_BIN" repo conf show
# EXPECT: Shows selected_target = null, lists available targets
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none - read-only)

echo ""
echo "Repository Configuration:"
echo ""
echo "Default Target: (not set)"
echo ""
echo "Available targets:"
echo "  - target-cmake-myapp (cmake: myapp)"
echo "  - target-make-myapp (make: myapp)"
echo ""
echo "Note: Build and TU operations require a default target to be set."
echo "Use: maestro repo conf select-default target <target-id>"

echo ""
echo "=== Step 4: Select Default Target ===\"

run "$MAESTRO_BIN" repo conf select-default target target-cmake-myapp
# EXPECT: Updates repoconf.json with selected_target
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE (now satisfied)
# INTERNAL: validate_target_exists, update_repo_conf

echo ""
echo "Selected default target: target-cmake-myapp (cmake: myapp)"
echo ""
echo "RepoConf gate now satisfied. Build and TU operations may proceed."

echo ""
echo "=== Step 5: Attempt Build (RepoConf Gate Check) ===\"

run "$MAESTRO_BIN" make
# EXPECT: Proceeds because RepoConf gate satisfied
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE (must pass)
# INTERNAL: check_repoconf_gate, invoke_build_system

echo ""
echo "[BUILD] Using default target: target-cmake-myapp"
echo "[BUILD] Build system: cmake"
echo "[BUILD] Running: cmake -S . -B build && cmake --build build"
echo "..."
echo "[BUILD] Success: myapp executable created"

echo ""
echo "=== Step 6: Run Deep RepoResolve (Optional) ===\"

run "$MAESTRO_BIN" repo refresh all
# EXPECT: Checks conventions, creates issues for violations
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO (issues added)
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPO_RESOLVE_DEEP, CONVENTIONS_GATE
# INTERNAL: run_lite_resolve, check_conventions, create_issues

echo ""
echo "Running deep resolve..."
echo ""
echo "Lite resolve complete: 2 packages, 2 targets"
echo ""
echo "Convention checks:"
echo "  - File layout: OK"
echo "  - Naming conventions: WARNING"
echo "    - Found header file src/main.cpp with no corresponding include/ directory"
echo "    - Created issue: issue-001 \"Header/source separation convention violation\""
echo ""
echo "Deep resolve complete."
echo "Issues created: 1"
echo "View issues: maestro issues list"

echo ""
echo "=== Alternative Path: No Default Target Selected ===\"

echo ""
echo "# If user tries to build without selecting default target:"
run "$MAESTRO_BIN" make
echo ""
echo "ERROR: RepoConf gate not satisfied"
echo ""
echo "No default target selected. Multiple targets available:"
echo "  - target-cmake-myapp (cmake: myapp)"
echo "  - target-make-myapp (make: myapp)"
echo ""
echo "Select default target:"
echo "  maestro repo conf select-default target <target-id>"

echo ""
echo "=== Outcome A: Single Target Auto-Selected ===\"
echo "Flow:"
echo "  1. Run repo resolve"
echo "  2. Only one target detected"
echo "  3. Maestro auto-selects default target"
echo "  4. RepoConf gate automatically satisfied"
echo "  5. Build proceeds without manual selection"

echo ""
echo "=== Outcome B: Multiple Targets → User Chooses Default ===\"
echo "Flow (as shown above):"
echo "  1. Run repo resolve"
echo "  2. Two targets detected (cmake + make)"
echo "  3. User selects: maestro repo conf select-default target target-cmake-myapp"
echo "  4. RepoConf gate satisfied"
echo "  5. Build proceeds with selected target"

echo ""
echo "=== Outcome C: Deep Resolve Finds Violations → Issues Created ===\"
echo "Flow:"
echo "  1. Run repo refresh all"
echo "  2. Convention check detects layout violation (no include/ directory)"
echo "  3. Issue created: issue-001"
echo "  4. User can:"
echo "     - Fix violation (create include/ dir, move headers)"
echo "     - Ignore issue (mark as accepted deviation)"
echo "     - Create task from issue to track fix work"
echo ""
echo "Artifacts:"
echo "  - ./docs/maestro/issues/issue-001.json (convention violation issue)"

echo ""
echo "=== Key Insights ===\"
echo "  - RepoResolve is THE mechanism for build system detection"
echo "  - Lite: packages + targets only"
echo "  - Deep: + conventions + issues"
echo "  - RepoConf gate blocks build/TU until default target chosen"
echo "  - Multi-build-system projects require explicit target selection"

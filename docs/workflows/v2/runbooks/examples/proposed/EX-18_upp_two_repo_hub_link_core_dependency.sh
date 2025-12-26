#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-18: U++ Two-Repo Hub Linking — custom-app Depends on ai-upp/Core

echo "=== U++ Hub Linking: Cross-Repo Dependency Discovery ==="
echo "Pipeline: Hub cache as cross-repo package index"

echo ""
echo "=== Minimal Project Skeletons ==="
echo "Repository 1 (ai-upp):"
echo "  ai-upp/"
echo "  └── Core/"
echo "      ├── Core.upp (package definition)"
echo "      ├── Core.h"
echo "      └── Core.cpp"
echo ""
echo "Repository 2 (custom-app):"
echo "  custom-app/"
echo "  └── App/"
echo "      ├── App.upp (depends on Core)"
echo "      └── main.cpp (#include <Core/Core.h>)"

echo ""
echo "=== In ai-upp: Optional Hub Registration ==="

echo ""
echo "=== Step 1a: Scan ai-upp to Populate Hub Cache (Read-Only Mode) ==="

run cd ~/Dev/ai-upp
run maestro init --read-only  # TODO_CMD
# EXPECT: Hub cache updated, no ./docs/maestro/ created
# STORES_WRITE: HOME_HUB_REPO
# GATES: (none)

echo ""
echo "[INIT] Read-only mode: No local Maestro structure created"
echo "[INIT] Scanning repository for packages..."
echo "[INIT] Found package: Core (Ultimate++ package)"
echo "[INIT] Writing fingerprint to hub: \$HOME/.maestro/hub/repo/<hash>/ai-upp.json"
echo "[INIT] Hub cache updated"

echo ""
echo "Alternative: Full initialization (if user wants to manage ai-upp with Maestro)"

run maestro init
# EXPECT: Creates ./docs/maestro/repo.json
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO, HOME_HUB_REPO
# GATES: (none)

echo ""
echo "[INIT] Created ./docs/maestro/repo.json"

run maestro repo resolve --level lite
# EXPECT: Detects Core package
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO, HOME_HUB_REPO
# GATES: REPO_RESOLVE_LITE

echo ""
echo "[REPO RESOLVE] Detecting Ultimate++ packages..."
echo "[REPO RESOLVE] Found package: Core"
echo "[REPO RESOLVE] Writing to hub cache: \$HOME/.maestro/hub/repo/<hash>/ai-upp.json"
echo ""
echo "Detected packages:"
echo "  - pkg-001: Core (upp)"
echo "    - No targets detected (library package)"

echo ""
echo "=== In custom-app: Dependency Discovery via Hub ==="

echo ""
echo "=== Step 2: Initialize custom-app ==="

run cd ~/Dev/custom-app
run maestro init
# EXPECT: Creates ./docs/maestro/repo.json
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)

echo ""
echo "[INIT] Created ./docs/maestro/repo.json"
echo "[INIT] Initialized Maestro structure"

echo ""
echo "=== Step 3: Resolve with Dependency Detection ==="

run maestro repo resolve --level lite
# EXPECT: Discovers App depends on Core, queries hub, resolves dependency
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# STORES_READ: HOME_HUB_REPO
# GATES: REPO_RESOLVE_LITE
# INTERNAL: parse_upp_dependencies, query_hub_cache, resolve_external_deps

echo ""
echo "[REPO RESOLVE] Detecting Ultimate++ packages..."
echo "[REPO RESOLVE] Found package: App"
echo "[REPO RESOLVE]   - Depends on: Core (not found locally)"
echo "[REPO RESOLVE] Querying hub for dependency: Core"
echo "[REPO RESOLVE] Hub query: Found Core in repository ai-upp (path: ~/Dev/ai-upp)"
echo "[REPO RESOLVE] Linked external dependency: Core → ~/Dev/ai-upp/Core"
echo ""
echo "Detected packages:"
echo "  - pkg-001: App (upp)"
echo "    - target-upp-app: App [executable]"
echo "    - Dependencies:"
echo "      - Core [EXTERNAL: ~/Dev/ai-upp/Core]"
echo ""
echo "Single target detected. Auto-selected as default."

echo ""
echo "Artifact: ./docs/maestro/repo.json excerpt:"
echo "{"
echo "  \"packages\": ["
echo "    {"
echo "      \"id\": \"pkg-001\","
echo "      \"name\": \"App\","
echo "      \"build_system\": \"upp\","
echo "      \"dependencies\": ["
echo "        {"
echo "          \"name\": \"Core\","
echo "          \"source\": \"external\","
echo "          \"resolved_path\": \"~/Dev/ai-upp/Core\","
echo "          \"resolved_from\": \"hub_cache\""
echo "        }"
echo "      ]"
echo "    }"
echo "  ]"
echo "}"

echo ""
echo "=== Step 4: Query Hub for Dependency Info ==="

run maestro repo hub find package Core  # TODO_CMD
# EXPECT: Returns path to ai-upp repository
# STORES_READ: HOME_HUB_REPO
# GATES: (none)

echo ""
echo "[HUB] Searching for package: Core"
echo "[HUB] Found in repository: ai-upp"
echo "[HUB]   Path: ~/Dev/ai-upp"
echo "[HUB]   Package path: ~/Dev/ai-upp/Core"
echo "[HUB]   Scanned: 2025-01-26T10:15:00Z"

echo ""
echo "=== Step 5: Build with Hub-Resolved Dependencies ==="

run maestro make --with-hub-deps  # TODO_CMD
# EXPECT: Build App using Core from ai-upp
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO, HOME_HUB_REPO
# GATES: REPOCONF_GATE, HUB_DEPS_RESOLVED
# INTERNAL: construct_umk_assembly_args, invoke_umk_build

echo ""
echo "[BUILD] Using default target: target-upp-app (App)"
echo "[BUILD] Resolved external dependencies from hub:"
echo "[BUILD]   - Core: ~/Dev/ai-upp/Core"
echo "[BUILD] Running: umk ~/Dev/custom-app/App ~/Dev/ai-upp GCC -ab"
echo "..."
echo "[BUILD] Compiling main.cpp"
echo "[BUILD] Linking App executable"
echo "[BUILD] Build succeeded: ./App/GCC.Release/App"

echo ""
echo "=== Step 6: Build TU with Hub Dependencies ==="

run maestro tu build --target target-upp-app --resolve-from-hub  # TODO_CMD
# EXPECT: AST index includes symbols from both App and Core
# STORES_WRITE: TU_DATABASE
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO, HOME_HUB_REPO
# GATES: REPOCONF_GATE, BUILD_SUCCESS, HUB_DEPS_RESOLVED
# INTERNAL: include_hub_deps_in_ast, parse_external_sources

echo ""
echo "[TU BUILD] Building translation units for target: target-upp-app"
echo "[TU BUILD] Including hub dependencies:"
echo "[TU BUILD]   - Core (~/Dev/ai-upp/Core)"
echo "[TU BUILD] Analyzing: App/main.cpp"
echo "[TU BUILD]   - Found reference: Core::GetVersion (line 5, col 35)"
echo "[TU BUILD] Analyzing: ~/Dev/ai-upp/Core/Core.cpp (hub dependency)"
echo "[TU BUILD]   - Found function: Core::GetVersion (line 4, col 5)"
echo "[TU BUILD] AST index created: ./docs/maestro/tu/target-upp-app.db"
echo "[TU BUILD] Total symbols: 12 (8 from App, 4 from Core)"

echo ""
echo "=== Alternative Path: Core Not Found in Hub ==="

run cd ~/Dev/custom-app
run maestro repo resolve --level lite
# EXPECT: Hub query fails, issue created

echo ""
echo "[REPO RESOLVE] Detecting Ultimate++ packages..."
echo "[REPO RESOLVE] Found package: App"
echo "[REPO RESOLVE]   - Depends on: Core (not found locally)"
echo "[REPO RESOLVE] Querying hub for dependency: Core"
echo "[REPO RESOLVE] Hub query: No match found for package \"Core\""
echo "[REPO RESOLVE] Created issue: issue-001 \"Unresolved dependency: Core\""
echo ""
echo "Detected packages:"
echo "  - pkg-001: App (upp)"
echo "    - target-upp-app: App [executable]"
echo "    - Dependencies:"
echo "      - Core [UNRESOLVED]"
echo ""
echo "Issues created: 1"
echo ""
echo "View issues: maestro issues list"

echo ""
echo "Issue created: ./docs/maestro/issues/issue-001.json"
echo "{"
echo "  \"id\": \"issue-001\","
echo "  \"title\": \"Unresolved dependency: Core\","
echo "  \"description\": \"Package 'App' depends on 'Core', but Core was not found locally or in hub cache. Scan the repository containing Core to populate hub cache.\","
echo "  \"severity\": \"error\","
echo "  \"status\": \"open\","
echo "  \"created_by\": \"repo_resolve\","
echo "  \"suggested_action\": \"Run 'maestro init --read-only' in the repository containing package Core\""
echo "}"

echo ""
echo "User action: Scan ai-upp to populate hub, then retry"

run cd ~/Dev/ai-upp
run maestro init --read-only  # TODO_CMD
echo ""
echo "[INIT] Hub cache updated with Core location"

run cd ~/Dev/custom-app
run maestro repo resolve --level lite
echo ""
echo "[REPO RESOLVE] Dependency Core now resolved from hub"
echo "[REPO RESOLVE] Closed issue: issue-001 (dependency resolved)"

echo ""
echo "=== Outcome A: Core Found in Hub → Build Succeeds ==="
echo "Flow:"
echo "  1. ai-upp previously scanned (hub cache populated)"
echo "  2. custom-app init and repo resolve"
echo "  3. Dependency on Core detected, hub query succeeds"
echo "  4. Build and TU operations include Core sources from ai-upp path"
echo "  5. Executable built successfully with linked dependency"
echo ""
echo "Artifacts:"
echo "  - custom-app/./docs/maestro/repo.json (with external dependency metadata)"
echo "  - \$HOME/.maestro/hub/repo/<hash>/ai-upp.json (hub cache entry)"
echo "  - custom-app/App/GCC.Release/App (built executable)"
echo "  - custom-app/./docs/maestro/tu/target-upp-app.db (AST index including Core symbols)"
echo ""
echo "Duration: ~2 minutes"

echo ""
echo "=== Outcome B: Core Not Found in Hub → Issue Created, User Scans ai-upp ==="
echo "Flow:"
echo "  1. custom-app init and repo resolve"
echo "  2. Hub query for Core fails"
echo "  3. Issue created with suggested action"
echo "  4. User navigates to ai-upp and runs 'maestro init --read-only'"
echo "  5. Hub cache updated with Core location"
echo "  6. User returns to custom-app and retries repo resolve"
echo "  7. Dependency now resolved, build proceeds"
echo ""
echo "Artifacts:"
echo "  - custom-app/./docs/maestro/issues/issue-001.json (initially)"
echo "  - \$HOME/.maestro/hub/repo/<hash>/ai-upp.json (created after scan)"
echo "  - custom-app/./docs/maestro/repo.json (updated with resolved dependency)"
echo "  - Issue auto-closes after successful resolution"
echo ""
echo "Duration: ~5 minutes (includes scanning ai-upp)"

echo ""
echo "=== Outcome C: Multiple Hub Matches → Disambiguation Required ==="
echo "Flow:"
echo "  1. custom-app resolves dependency on \"Core\""
echo "  2. Hub cache contains multiple packages named \"Core\""
echo "  3. Maestro prompts user to disambiguate"
echo "  4. User selects ai-upp/Core"
echo "  5. Build proceeds with selected dependency"
echo ""
echo "Hypothetical output:"
echo "[REPO RESOLVE] Querying hub for dependency: Core"
echo "[REPO RESOLVE] Found 2 matches for package \"Core\":"
echo "[REPO RESOLVE]   1. ai-upp/Core (scanned: 2025-01-26T10:15:00Z)"
echo "[REPO RESOLVE]   2. legacy-upp/Core (scanned: 2025-01-20T08:30:00Z)"
echo "[REPO RESOLVE] Select dependency source (1 or 2):"
echo ""
echo "Duration: ~3 minutes"

echo ""
echo "=== Key Insights ==="
echo "  - Hub cache acts as cross-repo index (package name → repository path)"
echo "  - U++ dependencies declared in .upp files (uses <package>;)"
echo "  - External dependencies require assembly path in umk build command"
echo "  - TU build includes hub dependency sources for complete AST"
echo "  - Hub cache is \$HOME-scoped (shared across all repos on system)"
echo "  - Unresolved dependencies create error-level issues with suggested actions"

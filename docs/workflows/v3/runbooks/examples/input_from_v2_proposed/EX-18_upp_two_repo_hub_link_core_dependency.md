# EX-18: U++ Two-Repo Hub Linking — custom-app Depends on ai-upp/Core

**Scope**: Cross-repository dependency resolution using hub cache
**Build System**: Ultimate++ (theide/umk)
**Languages**: C++
**Outcome**: Demonstrate that $HOME/.maestro/**/repo hub cache enables cross-repo discovery and linking for U++ packages, allowing build/TU operations to resolve dependencies from previously scanned repositories

---

## Scenario Summary

Developer has two U++ repositories:
- **ai-upp**: Contains the `Core` package (foundational library)
- **custom-app**: Contains the `App` package which depends on `Core`

When running `maestro repo resolve` in `custom-app`, Maestro detects the dependency on `Core` but doesn't find it locally. It queries the hub cache (`$HOME/.maestro/**/repo`) to locate `Core` in the `ai-upp` repository. Build and TU operations can then use this hub-resolved path to include `Core` sources.

This demonstrates **hub cache as cross-repo dependency discovery mechanism** for Ultimate++.

---

## Preconditions

- Two repositories exist:
  - `~/Dev/ai-upp/` (contains Core package)
  - `~/Dev/custom-app/` (contains App package depending on Core)
- Ultimate++ build tools installed (`theide` or `umk`)
- User has previously scanned or will scan `ai-upp` to populate hub cache

---

## Minimal Project Skeletons

### Repository 1: ai-upp

```
ai-upp/
├── Core/
│   ├── Core.upp
│   ├── Core.h
│   └── Core.cpp
└── (other packages...)
```

**Core/Core.upp** (U++ package definition):
```
description "Core utilities and data structures\377";

uses
	;

file
	Core.h,
	Core.cpp;
```

**Core/Core.h**:
```cpp
#ifndef _Core_Core_h_
#define _Core_Core_h_

#include <iostream>
#include <string>

namespace Core {
    std::string GetVersion();
}

#endif
```

**Core/Core.cpp**:
```cpp
#include "Core.h"

namespace Core {
    std::string GetVersion() {
        return "1.0.0";
    }
}
```

### Repository 2: custom-app

```
custom-app/
├── App/
│   ├── App.upp
│   └── main.cpp
└── (Maestro will initialize here)
```

**App/App.upp** (depends on Core):
```
description "Custom application\377";

uses
	Core;

file
	main.cpp;

mainconfig
	;
```

**App/main.cpp**:
```cpp
#include <Core/Core.h>
#include <iostream>

int main() {
    std::cout << "App version: " << Core::GetVersion() << std::endl;
    return 0;
}
```

---

## Runbook Steps

### In ai-upp: Optional Hub Registration

#### Step 1a: Scan ai-upp to Populate Hub Cache (Optional)

| Command | Intent | Expected |
|---------|--------|----------|
| `cd ~/Dev/ai-upp` | Navigate to Core repository | Working directory changed |
| `TODO_CMD: maestro init --read-only` | Initialize in read-only mode (hub fingerprint only) | Hub cache updated, no `./docs/maestro/` created |

**Alternative**: Full initialization if user wants to manage ai-upp with Maestro

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro init` | Full initialization | Creates `./docs/maestro/repo.json` |
| `maestro repo resolve --level lite` | Detect Core package | Writes package info to repo.json and hub cache |

**System Output (read-only mode)**:
```
[INIT] Read-only mode: No local Maestro structure created
[INIT] Scanning repository for packages...
[INIT] Found package: Core (Ultimate++ package)
[INIT] Writing fingerprint to hub: $HOME/.maestro/hub/repo/<hash>/ai-upp.json
[INIT] Hub cache updated
```

**System Output (full initialization)**:
```
[INIT] Created ./docs/maestro/repo.json
[REPO RESOLVE] Detecting Ultimate++ packages...
[REPO RESOLVE] Found package: Core
[REPO RESOLVE] Writing to hub cache: $HOME/.maestro/hub/repo/<hash>/ai-upp.json

Detected packages:
  - pkg-001: Core (upp)
    - No targets detected (library package)
```

**Gates**: (none for read-only init)
**Stores write**:
- HOME_HUB_REPO (`$HOME/.maestro/hub/repo/`)
- REPO_TRUTH_DOCS_MAESTRO (only if full init)

---

### In custom-app: Dependency Discovery via Hub

#### Step 2: Initialize custom-app

| Command | Intent | Expected |
|---------|--------|----------|
| `cd ~/Dev/custom-app` | Navigate to app repository | Working directory changed |
| `maestro init` | Initialize Maestro | Creates `./docs/maestro/repo.json` |

**System Output**:
```
[INIT] Created ./docs/maestro/repo.json
[INIT] Initialized Maestro structure
```

**Gates**: (none)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO

#### Step 3: Resolve with Dependency Detection

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro repo resolve --level lite` | Detect App package and dependencies | Discovers App depends on Core |

**Internal**:
- Parse `App/App.upp` to extract `uses Core;` dependency
- Check if Core exists locally (not found in custom-app/)
- Query hub cache: `$HOME/.maestro/hub/repo/` for package named "Core"
- If found in hub, record external dependency with path

**System Output**:
```
[REPO RESOLVE] Detecting Ultimate++ packages...
[REPO RESOLVE] Found package: App
[REPO RESOLVE]   - Depends on: Core (not found locally)
[REPO RESOLVE] Querying hub for dependency: Core
[REPO RESOLVE] Hub query: Found Core in repository ai-upp (path: ~/Dev/ai-upp)
[REPO RESOLVE] Linked external dependency: Core → ~/Dev/ai-upp/Core

Detected packages:
  - pkg-001: App (upp)
    - target-upp-app: App [executable]
    - Dependencies:
      - Core [EXTERNAL: ~/Dev/ai-upp/Core]

Single target detected. Auto-selected as default.
```

**Gates**: REPO_RESOLVE_LITE
**Stores write**: REPO_TRUTH_DOCS_MAESTRO
**Stores read**: HOME_HUB_REPO

**Artifact** (`./docs/maestro/repo.json` excerpt):
```json
{
  "packages": [
    {
      "id": "pkg-001",
      "name": "App",
      "build_system": "upp",
      "path": "App/",
      "targets": [
        {
          "id": "target-upp-app",
          "name": "App",
          "type": "executable"
        }
      ],
      "dependencies": [
        {
          "name": "Core",
          "source": "external",
          "resolved_path": "~/Dev/ai-upp/Core",
          "resolved_from": "hub_cache"
        }
      ]
    }
  ],
  "repo_conf": {
    "default_target": "target-upp-app"
  }
}
```

#### Step 4: Query Hub for Dependency Info

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro repo hub find package Core` | Explicitly query hub for Core | Returns path to ai-upp repository |

**System Output**:
```
[HUB] Searching for package: Core
[HUB] Found in repository: ai-upp
[HUB]   Path: ~/Dev/ai-upp
[HUB]   Package path: ~/Dev/ai-upp/Core
[HUB]   Scanned: 2025-01-26T10:15:00Z
```

**Gates**: (none - read-only query)
**Stores read**: HOME_HUB_REPO

#### Step 5: Build with Hub-Resolved Dependencies

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro make --with-hub-deps` | Build App using Core from ai-upp | Build succeeds with linked dependency |

**Internal**:
- Read `./docs/maestro/repo.json` to get default target (App)
- Find external dependency: Core → ~/Dev/ai-upp/Core
- Construct umk command with assembly path including ai-upp:
  - `umk ~/Dev/custom-app/App ~/Dev/ai-upp GCC -ab`
- Execute build

**System Output**:
```
[BUILD] Using default target: target-upp-app (App)
[BUILD] Resolved external dependencies from hub:
[BUILD]   - Core: ~/Dev/ai-upp/Core
[BUILD] Running: umk ~/Dev/custom-app/App ~/Dev/ai-upp GCC -ab
...
[BUILD] Compiling main.cpp
[BUILD] Linking App executable
[BUILD] Build succeeded: ./App/GCC.Release/App
```

**Gates**: REPOCONF_GATE, HUB_DEPS_RESOLVED
**Stores read**: REPO_TRUTH_DOCS_MAESTRO, HOME_HUB_REPO

#### Step 6: Build TU with Hub Dependencies

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro tu build --target target-upp-app --resolve-from-hub` | Build AST index including Core symbols | AST index includes symbols from both App and Core |

**Internal**:
- Invoke umk or compiler with AST dump flags
- Include assembly paths for hub dependencies (ai-upp)
- Parse AST from both App and Core sources
- Build unified symbol graph

**System Output**:
```
[TU BUILD] Building translation units for target: target-upp-app
[TU BUILD] Including hub dependencies:
[TU BUILD]   - Core (~/Dev/ai-upp/Core)
[TU BUILD] Analyzing: App/main.cpp
[TU BUILD]   - Found reference: Core::GetVersion (line 5, col 35)
[TU BUILD] Analyzing: ~/Dev/ai-upp/Core/Core.cpp (hub dependency)
[TU BUILD]   - Found function: Core::GetVersion (line 4, col 5)
[TU BUILD] AST index created: ./docs/maestro/tu/target-upp-app.db
[TU BUILD] Total symbols: 12 (8 from App, 4 from Core)
```

**Gates**: REPOCONF_GATE, BUILD_SUCCESS, HUB_DEPS_RESOLVED
**Stores write**: TU_DATABASE
**Stores read**: REPO_TRUTH_DOCS_MAESTRO, HOME_HUB_REPO

---

## Alternative Path: Core Not Found in Hub

### Step 3b: Hub Query Fails

**Scenario**: User has not scanned ai-upp, so Core is not in hub cache

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro repo resolve --level lite` | Detect App package | Dependency Core not resolved |

**System Output**:
```
[REPO RESOLVE] Detecting Ultimate++ packages...
[REPO RESOLVE] Found package: App
[REPO RESOLVE]   - Depends on: Core (not found locally)
[REPO RESOLVE] Querying hub for dependency: Core
[REPO RESOLVE] Hub query: No match found for package "Core"
[REPO RESOLVE] Created issue: issue-001 "Unresolved dependency: Core"

Detected packages:
  - pkg-001: App (upp)
    - target-upp-app: App [executable]
    - Dependencies:
      - Core [UNRESOLVED]

Issues created: 1

View issues: maestro issues list
```

**Issue Created** (`./docs/maestro/issues/issue-001.json`):
```json
{
  "id": "issue-001",
  "title": "Unresolved dependency: Core",
  "description": "Package 'App' depends on 'Core', but Core was not found locally or in hub cache. Scan the repository containing Core (e.g., ai-upp) to populate hub cache.",
  "severity": "error",
  "status": "open",
  "created_by": "repo_resolve",
  "suggested_action": "Run 'maestro init' or 'maestro init --read-only' in the repository containing package Core"
}
```

**Gates**: REPO_RESOLVE_LITE (completes, but with issue)
**Stores write**: REPO_TRUTH_DOCS_MAESTRO (with issue)

**User Action**:
1. Navigate to ai-upp: `cd ~/Dev/ai-upp`
2. Scan repository: `maestro init --read-only` (or full init)
3. Return to custom-app: `cd ~/Dev/custom-app`
4. Retry: `maestro repo resolve --level lite`
5. Dependency now resolved from hub

---

## AI Perspective (Heuristic)

**What AI notices**:
- U++ packages use `.upp` files with `uses <package>;` syntax for dependencies
- Hub cache acts as a cross-repo index: package name → repository path
- External dependencies require assembly path in umk build command
- TU build needs to include hub dependency sources for complete AST
- Hub cache is read-only from perspective of dependent repo (custom-app doesn't modify ai-upp's hub entry)

**What AI tries**:
- Parse `.upp` files to extract dependency list from `uses` section
- Query hub cache by package name (exact match or fuzzy)
- Construct umk assembly argument: `<main-package-path> <dependency-assembly-path> ...`
- Include external sources in AST analysis to resolve cross-package symbol references
- Suggest rescanning when hub query fails

**Where AI tends to hallucinate**:
- May assume hub cache auto-populates (user must explicitly scan repositories)
- May confuse hub cache with git submodules or CMake FetchContent (different mechanisms)
- May forget that hub cache is $HOME-scoped (shared across all repos on system, not per-repo)
- May assume versioning of dependencies in hub (hub stores latest scan, not multiple versions)
- May not account for stale hub cache (if ai-upp moves, hub entry may be outdated)

---

## Outcomes

### Outcome A: Core Found in Hub → Build Succeeds

**Flow** (as shown in main runbook):
1. ai-upp previously scanned (hub cache populated)
2. custom-app init and repo resolve
3. Dependency on Core detected, hub query succeeds
4. Build and TU operations include Core sources from ai-upp path
5. Executable built successfully with linked dependency

**Artifacts**:
- `custom-app/./docs/maestro/repo.json` (with external dependency metadata)
- `$HOME/.maestro/hub/repo/<hash>/ai-upp.json` (hub cache entry)
- `custom-app/App/GCC.Release/App` (built executable)
- `custom-app/./docs/maestro/tu/target-upp-app.db` (AST index including Core symbols)

**Duration**: ~2 minutes

### Outcome B: Core Not Found in Hub → Issue Created, User Scans ai-upp

**Flow**:
1. custom-app init and repo resolve
2. Hub query for Core fails
3. Issue created with suggested action
4. User navigates to ai-upp and runs `maestro init --read-only`
5. Hub cache updated with Core location
6. User returns to custom-app and retries repo resolve
7. Dependency now resolved, build proceeds

**Artifacts**:
- `custom-app/./docs/maestro/issues/issue-001.json` (initially)
- `$HOME/.maestro/hub/repo/<hash>/ai-upp.json` (created after scan)
- `custom-app/./docs/maestro/repo.json` (updated with resolved dependency)
- Issue auto-closes after successful resolution

**Duration**: ~5 minutes (includes scanning ai-upp)

### Outcome C: Multiple Hub Matches → Disambiguation Required

**Flow**:
1. custom-app resolves dependency on "Core"
2. Hub cache contains multiple packages named "Core" (e.g., from different U++ assembly paths)
3. Maestro prompts user to disambiguate:
   - `ai-upp/Core` (version 1.0.0)
   - `legacy-upp/Core` (version 0.9.5)
4. User selects `ai-upp/Core`
5. Build proceeds with selected dependency

**System Output (hypothetical)**:
```
[REPO RESOLVE] Querying hub for dependency: Core
[REPO RESOLVE] Found 2 matches for package "Core":
[REPO RESOLVE]   1. ai-upp/Core (scanned: 2025-01-26T10:15:00Z)
[REPO RESOLVE]   2. legacy-upp/Core (scanned: 2025-01-20T08:30:00Z)
[REPO RESOLVE] Select dependency source (1 or 2):
```

**Duration**: ~3 minutes

---

## Acceptance Gate Behavior

**HUB_DEPS_RESOLVED gate**:
- All external dependencies listed in `repo.json` must have valid `resolved_path`
- Paths must exist and be readable
- Blocks build/TU operations if unresolved dependencies exist

**Error-level issues**:
- Unresolved dependency creates error-level issue
- Can be ignored (override) if user wants to proceed with partial build

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "TODO_CMD: maestro init --read-only (hub fingerprint only, no local ./docs/maestro/)"
  - "TODO_CMD: maestro repo hub find package <name>"
  - "TODO_CMD: maestro repo hub list (show all packages in hub cache)"
  - "TODO_CMD: maestro make --with-hub-deps (or implicit behavior?)"
  - "TODO_CMD: maestro tu build --target <id> --resolve-from-hub (or implicit?)"
  - "Whether hub cache stores only package metadata or also includes version info"
  - "How hub cache handles package name collisions (disambiguation policy)"
  - "Whether hub cache can be manually edited or cleared"
  - "How stale hub entries are detected (moved repositories)"
  - "Policy for hub cache scope (per-user vs per-project)"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "cd ~/Dev/ai-upp && maestro init --read-only"
    intent: "Populate hub cache with Core package location"
    gates: []
    stores_write: ["HOME_HUB_REPO"]
    stores_read: []
    internal: ["scan_upp_packages", "write_hub_fingerprint"]
    cli_confidence: "low"  # TODO_CMD: --read-only flag

  - user: "cd ~/Dev/custom-app && maestro init"
    intent: "Initialize custom-app with Maestro"
    gates: []
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: []
    internal: []
    cli_confidence: "high"

  - user: "maestro repo resolve --level lite"
    intent: "Detect App package and resolve Core dependency via hub"
    gates: ["REPO_RESOLVE_LITE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    stores_read: ["HOME_HUB_REPO"]
    internal: ["parse_upp_dependencies", "query_hub_cache", "resolve_external_deps"]
    cli_confidence: "high"

  - user: "maestro repo hub find package Core"
    intent: "Explicitly query hub cache for Core package"
    gates: []
    stores_write: []
    stores_read: ["HOME_HUB_REPO"]
    internal: ["search_hub_by_package_name"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro make --with-hub-deps"
    intent: "Build App using Core from ai-upp (hub-resolved)"
    gates: ["REPOCONF_GATE", "HUB_DEPS_RESOLVED"]
    stores_write: []
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO", "HOME_HUB_REPO"]
    internal: ["construct_umk_assembly_args", "invoke_umk_build"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro tu build --target target-upp-app --resolve-from-hub"
    intent: "Build AST index including Core symbols from hub dependency"
    gates: ["REPOCONF_GATE", "BUILD_SUCCESS", "HUB_DEPS_RESOLVED"]
    stores_write: ["TU_DATABASE"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO", "HOME_HUB_REPO"]
    internal: ["include_hub_deps_in_ast", "parse_external_sources"]
    cli_confidence: "low"  # TODO_CMD
```

---

**Related:** Cross-repo dependencies, hub cache, Ultimate++ assembly paths, external package resolution
**Status:** Proposed

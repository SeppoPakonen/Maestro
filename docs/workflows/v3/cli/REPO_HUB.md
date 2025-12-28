# Repo Hub: Cross-Repository Package Discovery and Linking

**Last Updated:** 2025-12-28
**Version:** 1.0
**Status:** Implemented (P2 Sprint 4.1)

## Overview

The Repo Hub system enables Maestro to discover and link packages across multiple repositories on your local machine. This extends Maestro beyond single-repository operations to support cross-repo workflows common in modular development environments.

**Key Capabilities:**
- Discover packages in previously scanned repositories
- Create explicit links between packages across repos
- Deterministic package identification (stable IDs)
- Ambiguity detection and resolution
- Generic support for multiple build systems (U++, CMake, Cargo, Python, Maven, Gradle, etc.)

## Dual Hub Architecture

Maestro has two complementary hub systems:

### 1. Remote Package Hub (`maestro/hub/`)
**Purpose:** Download and manage packages from remote git registries

**Use Case:** Fetch public packages from online repositories (like U++ nests)

**Storage:** `~/.maestro/hub/.hub-cache.json` and cloned repositories

**Scope:** Network-based, remote repositories

### 2. Local Cross-Repo Hub (`maestro/repo/hub/`) - This System
**Purpose:** Discover and link packages across local repositories

**Use Case:** Link to packages in other repos on your local machine

**Storage:** `~/.maestro/hub/index.json` (global) and `./docs/maestro/repo/hub_links.json` (per-repo)

**Scope:** Local filesystem, previously scanned repos

## Key Concepts

### Hub Index

The global hub index at `~/.maestro/hub/index.json` tracks all previously scanned repositories:

- **Repo Records:** Path, git HEAD, last scan timestamp, package count
- **Package Index:** Fast lookup by package name across all repos
- **Deterministic IDs:** Stable fingerprints for repos and packages

### Hub Links

Per-repository link decisions stored at `./docs/maestro/repo/hub_links.json`:

- **Explicit Links:** User-confirmed package dependencies
- **Link Metadata:** When created, why, by whom
- **Overrides:** Manual resolutions for ambiguous packages

### Determinism

The hub system uses deterministic fingerprinting to ensure stable references:

**Repo ID Formula:**
```
repo_id = sha256(canonical_path + ":" + git_head_commit + ":" + toplevel_mtime)
```

**Package ID Formula:**
```
pkg_id = sha256(build_system + ":" + name + ":" + normalized_path)
```

**Stable Sorting:**
- Always alphabetical by package name
- Then by repo path
- Ensures consistent ordering across scans

### Ambiguity Handling

The hub system explicitly handles ambiguous package references:

- **Single Match:** Auto-linkable (with user confirmation)
- **Multiple Matches:** Requires explicit `--to <PKG_ID>` selection
- **Clear Errors:** Guides user through disambiguation process

## Storage Schema

### Global Index: `$HOME/.maestro/hub/index.json`

```json
{
  "version": "1.0",
  "updated_at": "2025-12-29T12:00:00Z",
  "repos": {
    "sha256:abc123...": {
      "path": "/home/user/dev/repo1",
      "git_head": "commit-sha-or-null",
      "last_scanned": "2025-12-29T11:00:00Z",
      "packages_count": 42,
      "link": "./repos/sha256-abc123.json"
    }
  },
  "packages_index": {
    "MyPackage": [
      {"repo_id": "sha256:abc123...", "pkg_id": "sha256:def456..."}
    ]
  }
}
```

**Fields:**
- `version`: Schema version (for future migrations)
- `updated_at`: Last index modification timestamp
- `repos`: Map of repo_id to repo metadata
  - `path`: Canonical absolute path to repository
  - `git_head`: Current git HEAD commit (null if not a git repo)
  - `last_scanned`: ISO8601 timestamp of last scan
  - `packages_count`: Number of packages in this repo
  - `link`: Relative path to detailed repo record file
- `packages_index`: Fast lookup map from package name to list of {repo_id, pkg_id}

### Repo Records: `$HOME/.maestro/hub/repos/<REPO_ID>.json`

```json
{
  "repo_id": "sha256:abc123...",
  "path": "/home/user/dev/repo1",
  "git_head": "commit-sha",
  "scan_timestamp": "2025-12-29T11:00:00Z",
  "packages": [
    {
      "pkg_id": "sha256:def456...",
      "name": "MyPackage",
      "build_system": "cmake",
      "dir": "/home/user/dev/repo1/packages/MyPackage",
      "dependencies": ["OtherPkg"],
      "metadata": {}
    }
  ]
}
```

**Fields:**
- `repo_id`: Deterministic repo fingerprint
- `path`: Canonical absolute path
- `git_head`: Git commit hash (or null)
- `scan_timestamp`: When this repo was scanned
- `packages`: Array of package records
  - `pkg_id`: Deterministic package fingerprint
  - `name`: Package name
  - `build_system`: Type (upp, cmake, cargo, python, maven, gradle, autoconf, msvs)
  - `dir`: Absolute path to package root
  - `dependencies`: List of dependency package names
  - `metadata`: Build system-specific metadata

### Link Store: `./docs/maestro/repo/hub_links.json`

```json
{
  "version": "1.0",
  "links": [
    {
      "link_id": "sha256:link123...",
      "from_package": "MyApp",
      "to_package_id": "sha256:def456...",
      "to_package_name": "MyLib",
      "to_repo_path": "/home/user/dev/repo2",
      "created_at": "2025-12-29T12:00:00Z",
      "reason": "explicit",
      "metadata": {}
    }
  ]
}
```

**Fields:**
- `version`: Schema version
- `links`: Array of link records
  - `link_id`: Deterministic link fingerprint
  - `from_package`: Local package name that depends on external package
  - `to_package_id`: Target package ID in hub index
  - `to_package_name`: Target package name (for readability)
  - `to_repo_path`: Path to repository containing target package
  - `created_at`: ISO8601 timestamp
  - `reason`: Why link was created (explicit, auto, inferred)
  - `metadata`: Additional link-specific data

## Command Reference

### `maestro repo hub scan [PATH]`

Scan a repository and add it to the hub index.

**Usage:**
```bash
maestro repo hub scan [PATH]
  [--verbose]
```

**Arguments:**
- `PATH`: Repository path to scan (default: current directory)
- `--verbose`: Show detailed scan progress

**Behavior:**
- Detects packages using existing multi-system scanner
- Computes deterministic repo and package IDs
- Adds or updates repo record in global hub index
- Updates package index for fast lookups
- Read-only safe (doesn't require `maestro init`)

**Example:**
```bash
# Scan current directory
maestro repo hub scan

# Scan specific repo
maestro repo hub scan /path/to/other-repo

# Verbose output
maestro repo hub scan --verbose
```

### `maestro repo hub list`

List all repositories in the hub index.

**Usage:**
```bash
maestro repo hub list
  [--json]
```

**Arguments:**
- `--json`: Output in JSON format

**Example:**
```bash
maestro repo hub list
```

**Output:**
```
HUB REPOSITORIES
sha256:abc123... - /home/user/dev/repo1 (15 packages)
sha256:def456... - /home/user/dev/repo2 (8 packages)
```

### `maestro repo hub show <REPO_ID>`

Show details about a specific repository.

**Usage:**
```bash
maestro repo hub show <REPO_ID>
  [--json]
```

**Arguments:**
- `REPO_ID`: Repository ID (from `hub list`)
- `--json`: Output in JSON format

**Example:**
```bash
maestro repo hub show sha256:abc123...
```

**Output:**
```
REPOSITORY: /home/user/dev/repo1
Repo ID: sha256:abc123...
Git HEAD: a1b2c3d4...
Last scanned: 2025-12-29T11:00:00Z
Packages: 15
  - MyPackage (cmake) - /home/user/dev/repo1/packages/MyPackage
  - OtherPackage (upp) - /home/user/dev/repo1/OtherPackage
  ...
```

### `maestro repo hub find package <NAME>`

Find all occurrences of a package across repos.

**Usage:**
```bash
maestro repo hub find package <NAME>
  [--json]
```

**Arguments:**
- `NAME`: Package name to search for
- `--json`: Output in JSON format

**Behavior:**
- Searches package index for exact name matches
- Returns sorted list of all matches
- Indicates if result is AMBIGUOUS (multiple matches)

**Example:**
```bash
maestro repo hub find package Core
```

**Output (Single Match):**
```
PACKAGE SEARCH: Core
Found 1 match:
  [sha256:xyz789...] Core (upp) - /home/user/dev/UppCore/Core
```

**Output (Ambiguous):**
```
PACKAGE SEARCH: Common
Found 2 matches (AMBIGUOUS - requires explicit selection):
  [sha256:aaa111...] Common (upp) - /home/user/dev/repo1/Common
  [sha256:bbb222...] Common (cmake) - /home/user/dev/repo3/lib/Common

To link to a specific package, use:
  maestro repo hub link package Common --to <PKG_ID>
```

### `maestro repo hub link package <NAME> --to <PKG_ID>`

Create an explicit link from local package to external package.

**Usage:**
```bash
maestro repo hub link package <NAME>
  --to <PKG_ID>
  [--reason <TEXT>]
```

**Arguments:**
- `NAME`: Local package name that needs the external dependency
- `--to`: Target package ID (from `hub find`)
- `--reason`: Optional reason for link (default: "explicit")

**Behavior:**
- Validates target package ID exists in hub index
- Creates link entry in `./docs/maestro/repo/hub_links.json`
- Computes deterministic link ID
- Updates existing link if already present

**Example:**
```bash
# Link MyApp to external Core package
maestro repo hub link package MyApp --to sha256:xyz789...
```

**Output:**
```
Created link: MyApp -> Core
Link ID: sha256:link123...
Target: /home/user/dev/UppCore/Core
```

**Next Steps:**
After linking, run:
```bash
maestro repo resolve       # Update repo model
maestro make build MyApp   # Build will use external package
```

### `maestro repo hub link show`

Show all hub links for current repository.

**Usage:**
```bash
maestro repo hub link show
  [--json]
```

**Arguments:**
- `--json`: Output in JSON format

**Example:**
```bash
maestro repo hub link show
```

**Output:**
```
HUB LINKS
MyApp -> Core
  Link ID: sha256:link123...
  Target: /home/user/dev/UppCore/Core
  Reason: explicit
```

### `maestro repo hub link remove <LINK_ID>`

Remove a hub link.

**Usage:**
```bash
maestro repo hub link remove <LINK_ID>
```

**Arguments:**
- `LINK_ID`: Link ID to remove (from `hub link show`)

**Example:**
```bash
maestro repo hub link remove sha256:link123...
```

**Output:**
```
Removed link: sha256:link123...
```

## Workflow Examples

### Basic Cross-Repo Linking

**Scenario:** You have two repos - `myapp` (your application) and `mylib` (a shared library). You want `myapp` to use packages from `mylib`.

**Steps:**

1. **Scan both repositories:**
```bash
cd ~/dev/mylib
maestro repo hub scan

cd ~/dev/myapp
maestro repo hub scan
```

2. **Find the package you need:**
```bash
cd ~/dev/myapp
maestro repo hub find package SharedLib
```

Output:
```
PACKAGE SEARCH: SharedLib
Found 1 match:
  [sha256:abc123...] SharedLib (cmake) - /home/user/dev/mylib/SharedLib
```

3. **Create the link:**
```bash
maestro repo hub link package MyApp --to sha256:abc123...
```

4. **Build your app:**
```bash
maestro repo resolve        # Updates repo model with external roots
maestro make build MyApp    # Build will include SharedLib
```

### Handling Ambiguous Packages

**Scenario:** Multiple repos have a package with the same name.

1. **Search for the package:**
```bash
maestro repo hub find package Utils
```

Output:
```
PACKAGE SEARCH: Utils
Found 3 matches (AMBIGUOUS - requires explicit selection):
  [sha256:111...] Utils (upp) - /home/user/dev/repo1/Utils
  [sha256:222...] Utils (cmake) - /home/user/dev/repo2/lib/Utils
  [sha256:333...] Utils (python) - /home/user/dev/repo3/utils
```

2. **Choose the correct package:**
```bash
# I want the CMake version
maestro repo hub link package MyApp --to sha256:222...
```

3. **Verify the link:**
```bash
maestro repo hub link show
```

### Updating Hub Index

**Scenario:** You've added new packages to a previously scanned repo.

```bash
# Re-scan the repo
cd ~/dev/mylib
maestro repo hub scan

# Index is automatically updated with new packages
maestro repo hub show <REPO_ID>
```

## Integration with Build Flow

The hub system integrates seamlessly with Maestro's build flow:

### 1. Repository Resolution

When you run `maestro repo resolve`, the hub index is optionally updated:

```bash
maestro repo resolve
# Scans current repo
# Updates hub index with discovered packages
# Writes docs/maestro/repo_model.json
```

### 2. Link Resolution

When you run `maestro make build`, hub links are loaded and resolved:

1. Load `./docs/maestro/repo/hub_links.json`
2. For each link, resolve package ID to directory path
3. Add external package roots to compiler include paths
4. Pass to builder (CMake, U++, etc.)

### 3. Translation Unit Analysis

When you run `maestro tu build`, the same external roots are used:

1. Load hub links
2. Resolve to package directories
3. Add to AST parser include paths
4. Ensures TU sees the same world as the compiler

## Deterministic Behavior

The hub system guarantees deterministic behavior:

### Stable IDs

- **Same repo state → same repo ID**
- **Same package location → same package ID**
- **Same link → same link ID**

### Stable Sorting

- Package search results always sorted: by name, then by repo path
- Link lists always sorted: by from_package, then by to_package_id
- Ensures predictable output across machines

### Reproducible Builds

Hub links are repo-local truth (`./docs/maestro/repo/hub_links.json`):

- Version controlled with your repo
- Same links on all developer machines
- Deterministic dependency resolution

## Read-Only Safety

Hub scanning is read-only safe:

- Can scan repositories without `maestro init`
- Doesn't modify scanned repository
- Only writes to global hub index (`~/.maestro/hub/`)
- Linking requires maestro-initialized repo (creates `./docs/maestro/repo/hub_links.json`)

## Build System Support

The hub system works with all build systems that Maestro supports:

- **U++** (.upp packages)
- **CMake** (CMakeLists.txt projects)
- **Autoconf** (configure.ac / Makefile.am)
- **Maven** (pom.xml projects)
- **Gradle** (build.gradle / settings.gradle)
- **Cargo** (Cargo.toml - future)
- **Python** (pyproject.toml / setup.cfg - future)
- **Visual Studio** (.sln / .vcxproj - future)

Package IDs include build system type for disambiguation.

## Error Handling

### Package Not Found

```bash
maestro repo hub find package NonExistent
```

Output:
```
Error: Package 'NonExistent' not found in hub index
```

**Solution:** Scan the repo containing the package:
```bash
maestro repo hub scan /path/to/repo-with-package
```

### Invalid Package ID

```bash
maestro repo hub link package MyApp --to sha256:invalid...
```

Output:
```
Error: Target package ID not found: sha256:invalid...
```

**Solution:** Use `hub find package` to get correct package ID.

### No Hub Index

If `~/.maestro/hub/index.json` doesn't exist, it's created automatically on first scan.

### Broken Links

If a linked repository is deleted or moved:

```bash
maestro make build MyApp
```

Output:
```
Warning: Hub link target not found: /old/path/to/repo2
Link ID: sha256:link123...
```

**Solution:** Remove broken link and re-link:
```bash
maestro repo hub link remove sha256:link123...
# Re-scan the repo if it moved
maestro repo hub scan /new/path/to/repo2
# Re-create the link
maestro repo hub link package MyApp --to <NEW_PKG_ID>
```

## Best Practices

### 1. Scan Early, Scan Often

Add all your repos to the hub index:

```bash
for repo in ~/dev/*; do
  cd "$repo"
  maestro repo hub scan
done
```

### 2. Use Explicit Reason

Document why you created a link:

```bash
maestro repo hub link package MyApp --to sha256:abc... --reason "Need latest Core 2024.1"
```

### 3. Version Control Links

Commit `./docs/maestro/repo/hub_links.json` to version control:

```bash
git add docs/maestro/repo/hub_links.json
git commit -m "Link to external SharedLib package"
```

### 4. Review Links Regularly

Periodically review and clean up links:

```bash
maestro repo hub link show
```

### 5. Disambiguate Clearly

When multiple packages match, choose carefully:

```bash
# Show all matches first
maestro repo hub find package Common

# Choose the right one based on build system, path, etc.
maestro repo hub link package MyApp --to <CORRECT_PKG_ID>
```

## Troubleshooting

### "Repo not found in hub index"

**Problem:** Trying to link to a package in a repo that hasn't been scanned.

**Solution:**
```bash
maestro repo hub scan /path/to/target-repo
```

### "Ambiguous package name"

**Problem:** Multiple packages with the same name exist in different repos.

**Solution:** Use `--to <PKG_ID>` to specify exact package:
```bash
maestro repo hub find package Common      # Shows all matches
maestro repo hub link package MyApp --to sha256:specific-id...
```

### "Hub index corrupted"

**Problem:** `~/.maestro/hub/index.json` is malformed.

**Solution:** Delete and rebuild:
```bash
rm -rf ~/.maestro/hub/
# Re-scan all repos
for repo in ~/dev/*; do maestro repo hub scan "$repo"; done
```

### "Link not working in build"

**Problem:** Linked package not found during build.

**Solution:** Ensure repo resolve ran after linking:
```bash
maestro repo resolve        # Reload hub links into repo model
maestro make build MyApp    # Should now work
```

## See Also

- [CLI Signatures](./SIGNATURES.md) - Full command syntax reference
- [EX-34: Cross-Repo Linking Example](../runbooks/examples/proposed/EX-34_hub_link_generic_cross_repo_dependency.md) - Complete workflow tutorial
- [EX-18: Repository Resolution](../runbooks/examples/EX-18_repo_resolution_comprehensive.md) - Basic repo scanning
- [Storage Contract](../../v1/scenario_09_storage_contract_repo_truth_vs_home_hub.md) - Storage architecture details

## Implementation Notes

**Files:**
- Hub index manager: `maestro/repo/hub/index.py`
- Link store manager: `maestro/repo/hub/link_store.py`
- Hub scanner: `maestro/repo/hub/scanner.py`
- Hub resolver: `maestro/repo/hub/resolver.py`
- CLI commands: `maestro/commands/hub.py`

**Storage Locations:**
- Global index: `$HOME/.maestro/hub/index.json`
- Repo records: `$HOME/.maestro/hub/repos/<REPO_ID>.json`
- Per-repo links: `./docs/maestro/repo/hub_links.json`

**No `.maestro` Usage:**
All storage uses canonical paths (`./docs/maestro/` for repo truth, `~/.maestro/` for user-global data). The deprecated `.maestro` path is forbidden.

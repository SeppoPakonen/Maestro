---
id: WF-05
title: Repo Resolve — packages, conventions, build targets, and derived issues/tasks
tags: [repo, resolve, detection, conventions, frameworks, build-targets, dependencies, issues, tasks]
entry_conditions: |
  - Git repository exists with source code
  - Maestro installed and accessible
  - Optional: .maestro/ directory exists (for cached results)
  - Optional: User configuration files in ~/.config/u++/ide/*.var (for Ultimate++ assemblies)
exit_conditions: |
  - Repository scan results produced in docs/maestro/repo/
  - Optional: Issues and Tasks created for convention violations
  - Optional: Repository hierarchy saved
artifacts_created: |
  - docs/maestro/repo/index.json: Full structured scan result
  - docs/maestro/repo/index.summary.txt: Human-readable summary
  - docs/maestro/repo/state.json: Repository state metadata
  - docs/maestro/repo/assemblies.json: Assembly information
  - docs/maestro/repo/hierarchy.json: Repository hierarchy (if generated)
  - Issue data files for convention violations (if any)
  - Task files for addressing violations (if policy allows)
failure_semantics: |
  - Hard stop: Repository not found or .maestro/ directory not found
  - Recoverable: Build system detection fails (continues with available info)
  - Recoverable: Some packages not recognized (continues with detected packages)
related_commands: [maestro repo resolve, maestro repo show, maestro repo pkg, maestro repo hier, maestro repo conventions, maestro repo rules]
links_to: [WF-01, WF-03, WF-04]
---

# Scenario WF-05: Repo Resolve — packages, conventions, build targets, and derived issues/tasks

## Overview

    This scenario documents the **canonical repository resolution mechanism** in Maestro, which serves as the integration spine for all other workflows. The `maestro repo resolve` command performs comprehensive repository analysis including:

    - Package/assembly discovery (including Ultimate++ `.upp` + assemblies)
    - Language detection
    - Build system detection (Make/CMake/Meson/Cargo/etc.)
    - Convention inference and rule set selection
    - Build target enumeration
    - Dependency graph derivation
    - Violation detection with Issue/Task creation

    This command is the **single source of truth** for repository structure and build system detection across all Maestro workflows.

    ## Branch Boundaries Note

    **Important**: Maestro operates strictly on the current Git branch. Switching branches during an active `maestro repo resolve` operation is **unsupported** and risks corrupting the internal state or producing inconsistent analysis results. This is an **operational rule**. Users must ensure they are on the desired branch before initiating repository resolution.
---

## Phase 1: Entry & Precondition Validation

### Precondition Checks

Before executing the repository resolution, Maestro validates:

- **Git repository exists**: Current directory or specified path is a valid git repository
- **.maestro/ directory exists**: Either in current directory or specified path (created via `maestro init`)
- **Read access**: Maestro has read access to the repository contents
- **Optional configuration**: User assembly configuration files in `~/.config/u++/ide/*.var` (if `--include-user-config` flag is used)

### Operator Intent

The Operator (human or AI runner) wants to:
- Understand the repository's package structure
- Identify build systems and configurations
- Detect naming conventions and framework usage
- Establish a baseline for other workflows
- Identify potential violations of established rules

---

## Phase 2: Package/Assembly Discovery

### Command: `maestro repo resolve`

**Purpose**: Perform comprehensive repository scan to identify packages and assemblies.

**Inputs**:
- `--path <path>`: Path to repository to scan (default: current directory)
- `--json`: Output results in JSON format
- `--no-write`: Skip writing artifacts to `docs/maestro/repo/`
- `--include-user-config`: Include user assemblies from `~/.config/u++/ide/*.var`
- `--verbose`: Show verbose scan information

**Process**:
1. **Ultimate++ Package Detection**:
   - Walk repository tree looking for `<Name>/<Name>.upp` files
   - For each valid package directory, collect source files based on extensions (`.cpp`, `.hpp`, `.c`, `.h`, etc.)
   - Parse `.upp` files to extract metadata, dependencies, and file groups

2. **Assembly Detection**:
   - Identify directories containing multiple package folders
   - Consider directories with 2+ packages as assemblies
   - Support nested package detection with ancestor path tracking

3. **Other Build System Detection**:
   - Use `detect_build_system()` to identify build systems present
   - Support CMake (`CMakeLists.txt`), Make (`Makefile`), Autoconf (`configure.ac`), Gradle (`build.gradle`), Maven (`pom.xml`), Visual Studio (`.sln`), and Ultimate++ (`.upp`)

4. **User Assembly Integration**:
   - Read user assembly configurations from `~/.config/u++/ide/*.var` (if enabled)
   - Link user assemblies to detected repository assemblies

**Outputs**:
- **stdout**: Human-readable summary of packages and assemblies found
- **JSON**: Structured output with detailed package/assembly information when `--json` flag used
- **Artifacts**: Repository scan results written to `docs/maestro/repo/` directory

**CLI Contract**:
```json
{
  "assemblies_detected": [
    {
      "name": "string",
      "root_path": "string",
      "package_folders": ["string"],
      "evidence_refs": ["string"],
      "assembly_type": "string",
      "packages": ["string"],
      "package_dirs": ["string"],
      "build_systems": ["string"],
      "metadata": {}
    }
  ],
  "packages_detected": [
    {
      "name": "string",
      "dir": "string",
      "upp_path": "string",
      "files": ["string"],
      "build_system": "string",
      "dependencies": ["string"],
      "groups": [
        {
          "name": "string",
          "files": ["string"],
          "readonly": boolean,
          "auto_generated": boolean
        }
      ],
      "ungrouped_files": ["string"]
    }
  ],
  "unknown_paths": [
    {
      "path": "string",
      "type": "file|dir",
      "guessed_kind": "string"
    }
  ],
  "internal_packages": [
    {
      "name": "string",
      "root_path": "string",
      "guessed_type": "string",
      "members": ["string"]
    }
  ]
}
```

---

## Phase 3: Language and Build System Detection

### Language Detection

**Process**:
- Analyze file extensions to identify programming languages
- Support common extensions: `.cpp`, `.hpp`, `.c`, `.h`, `.java`, `.py`, `.js`, `.ts`, `.go`, `.rs`, etc.
- Cross-reference with build system detection to confirm language usage

### Build System Detection

**Supported Build Systems**:
- **CMake**: Detect via `CMakeLists.txt`, parse for targets (executables/libraries)
- **Make**: Detect via `Makefile`, `GNUmakefile`, `makefile`
- **Autoconf**: Detect via `configure.ac`, `configure.in`, `Makefile.am`
- **Gradle**: Detect via `build.gradle`, `build.gradle.kts`, `settings.gradle`
- **Maven**: Detect via `pom.xml` files, parse for modules and dependencies
- **Visual Studio**: Detect via `.sln` files, parse for projects
- **Ultimate++**: Detect via `.upp` files

**Build Target Enumeration**:
- **CMake**: Extract `add_executable()` and `add_library()` targets
- **Gradle**: Extract modules from `settings.gradle`
- **Maven**: Extract modules from `<modules>` section
- **Autoconf**: Extract executables from `bin_PROGRAMS`, libraries from `lib_LTLIBRARIES`

---

## Phase 4: Convention Inference and Rule Set Selection

### Convention Inference

**Naming Convention Detection**:
- Analyze identifiers in source code to detect patterns:
  - camelCase
  - snake_case
  - UpperCamelCase
  - ALL_CAPS

**Directory Structure Patterns**:
- Identify common patterns like `src/`, `include/`, `test/`, `docs/`, `examples/`
- Detect framework-specific layouts (Qt, Ultimate++, etc.)

**Framework Fingerprinting**:
- **Ultimate++**: Presence of `.upp` files, U++-specific includes
- **Qt**: Qt-specific includes, `.ui` files, `moc_` generated files
- **Other frameworks**: Language-specific framework indicators

### Rule Set Selection

**Convention Libraries**:
- Identify the best-matching rule pack based on detected conventions
- Apply framework-specific rules (U++ conventions, Qt patterns, etc.)
- Store selected rule set in scan results

---

## Phase 5: Dependency Graph Derivation

### Package-to-Package Dependencies

**Ultimate++ Dependencies**:
- Parse `.upp` files for `uses` section to identify package dependencies
- Build dependency graph with conditional dependencies

**Other Build Systems**:
- **Gradle**: Extract project dependencies from `build.gradle`
- **Maven**: Extract dependencies from `pom.xml`
- **CMake**: Analyze target_link_libraries() calls
- **Autoconf**: Extract from linker flags and library specifications

### Shared Library Dependencies

**Process**:
- Identify system library dependencies
- Map to appropriate package-level dependencies
- Handle conditional dependencies based on build configurations

---

## Phase 6: Violation Detection and Issue/Task Creation

### Violation Detection

**File Naming Violations**:
- Check file names against detected naming conventions
- Identify files that don't follow established patterns

**Directory Layout Violations**:
- Verify directory structure against convention patterns
- Identify misplaced files or directories

**Co-location Rule Violations**:
- Detect files that should not be in the same directory
- Identify architectural violations

### Issue Creation

**Process**:
1. For each detected violation, create an Issue:
   - **Source**: "conventions/rules"
   - **ID**: Auto-generated (ISS-### format)
   - **Description**: Detailed explanation of the violation
   - **Location**: File path and line number (if applicable)

2. Store issue in `issue data*.md` format with structured metadata

**Issue Format**:
```markdown
# Issue ISS-001: Naming convention violation

**Source**: conventions/rules
**File**: src/core/utils.cpp
**Severity**: medium

## Description
File name 'src/core/utils.cpp' uses snake_case naming, but repository follows camelCase convention.

## Violation Details
- Expected: 'src/core/utils.cpp' should be 'src/core/utils.cpp' or similar
- Actual: 'src/core/utils.cpp'
- Convention detected: camelCase

## Suggested Fix
Rename file to follow camelCase convention: 'src/core/utils.cpp'
```

### Task Creation

**Policy-Driven Creation**:
- Tasks created based on repository policy settings
- Default: Create tasks for high-severity violations
- Optional: Create tasks for all violations

**Task Format**:
```json
{
  "id": "TASK-001",
  "title": "Fix naming convention violation in src/core/utils.cpp",
  "issue_id": "ISS-001",
  "status": "pending",
  "priority": "medium",
  "dependencies": [],
  "metadata": {
    "file": "src/core/utils.cpp",
    "violation_type": "naming_convention"
  }
}
```

---

## Phase 7: Output Generation and Artifact Storage

### Output Formats

**Human-Readable Summary**:
- Console output showing packages, assemblies, and scan statistics
- Summary of detected build systems and conventions
- Count of violations found (if any)

**JSON Output**:
- Structured JSON representation of complete scan results
- Compatible with downstream tools and automation

### Artifact Storage

**Location**: `docs/maestro/repo/` directory

**Files Created**:
- `index.json`: Complete scan results in structured format
- `index.summary.txt`: Human-readable summary of scan
- `state.json`: Scan metadata and repository state
- `assemblies.json`: Assembly-specific information
- `hierarchy.json`: Repository hierarchy (if generated)

---

## Phase 8: Integration with Other Workflows

### Integration Points

**WF-01 (Existing Repo Bootstrap)**:
- Instead of "Detect Build System", WF-01 now calls WF-05's Repo Resolve
- Uses scan results to inform build strategy and task creation

**WF-03 (Read-only Repo Inspection)**:
- Leverages Repo Resolve for comprehensive repository understanding
- Avoids duplicating detection logic

**WF-04 (Reactive Compile Error Solution)**:
- Uses resolved build targets and configurations to inform build process
- Relies on dependency graph for issue prioritization

### Cross-Workflow Dependencies

**Dependency Ranking**:
- Uses dependency graph to order tasks appropriately
- Ensures build dependencies are resolved before dependent packages

---

## Command Contracts Summary

| Command | Purpose | Inputs | Outputs | Hard Stops | Recoverable |
|---------|---------|--------|---------|-----------|-------------|
| `maestro repo resolve` | Scan repository for packages, assemblies, build systems | `--path`, `--json`, `--no-write`, `--include-user-config`, `--verbose` | JSON/human-readable scan results, artifacts in `docs/maestro/repo/` | Repository not found, .maestro/ directory missing | Build system detection fails, some packages not recognized |
| `maestro repo show` | Show repository scan results from `docs/maestro/repo/` | `--json`, `--path` | Scan results from stored artifacts | Index file not found | None |
| `maestro repo pkg list` | List all packages in repository | `--json`, `--path` | Package list with type info | None | None |
| `maestro repo pkg info <name>` | Show detailed package information | Package name, `--json`, `--path` | Package details with files and metadata | Package not found | None |
| `maestro repo hier` | Show repository hierarchy | `--json`, `--path`, `--show-files`, `--rebuild` | Hierarchy tree or JSON | Hierarchy not built, requires resolve first | None |
| `maestro repo conventions detect` | Detect naming conventions | `--path`, `--verbose` | Convention analysis | RepoRules.md not found | Convention detection incomplete |
| `maestro repo rules show` | Show repository rules | `--path` | Rules from RepoRules.md | RepoRules.md not found | None |

---

## Tests Implied by This Scenario

### Unit Tests

1. **Package Discovery**:
   - `test_scan_upp_packages_single()` - Verify single U++ package detection
   - `test_scan_upp_packages_nested()` - Verify nested package detection
   - `test_scan_multiple_build_systems()` - Verify detection of multiple build systems in one repo

2. **Language Detection**:
   - `test_detect_cpp_language()` - Verify C++ file extension detection
   - `test_detect_java_language()` - Verify Java file extension detection
   - `test_detect_mixed_languages()` - Verify multiple language detection

3. **Build System Detection**:
   - `test_detect_cmake_targets()` - Verify CMake target extraction
   - `test_detect_makefiles()` - Verify Makefile detection
   - `test_detect_gradle_modules()` - Verify Gradle module extraction
   - `test_detect_maven_modules()` - Verify Maven module detection

4. **Convention Inference**:
   - `test_infer_camel_case_naming()` - Verify camelCase detection
   - `test_infer_snake_case_naming()` - Verify snake_case detection
   - `test_infer_directory_patterns()` - Verify directory structure detection

5. **Violation Detection**:
   - `test_detect_naming_violations()` - Verify naming convention violations
   - `test_detect_layout_violations()` - Verify directory layout violations
   - `test_detect_co_location_violations()` - Verify co-location rule violations

6. **Issue/Task Creation**:
   - `test_create_issue_for_violation()` - Verify issue creation from violation
   - `test_create_task_for_violation()` - Verify task creation from violation
   - `test_issue_task_linking()` - Verify issue-task relationship

### Integration Tests

1. **Fixture Repositories**:
   - `fixture_cmake_repo`: CMake project with multiple targets
   - `fixture_maven_repo`: Multi-module Maven project
   - `fixture_gradle_repo`: Multi-module Gradle project
   - `fixture_upp_repo`: Ultimate++ project with assemblies
   - `fixture_mixed_repo`: Repository with multiple build systems
   - `fixture_violation_repo`: Repository with convention violations

2. **End-to-End Scenarios**:
   - `test_scenario_05_full_resolve()` - Run complete repo resolve on fixture, verify all artifacts created
   - `test_scenario_05_convention_detection()` - Verify convention detection works with various naming styles
   - `test_scenario_05_violation_workflow()` - Verify violations are detected and issues/tasks created

3. **Integration with Other Workflows**:
   - `test_wf01_uses_wf05()` - Verify WF-01 calls WF-05 for build system detection
   - `test_wf03_uses_wf05()` - Verify WF-03 uses WF-05 for repository understanding

### Golden Logs (Example Sessions)

1. **Golden Log: Clean Repository**:
   - Input: Repository with properly structured U++ packages
   - Expected output: Packages detected, no violations, artifacts created

2. **Golden Log: Mixed Build Systems**:
   - Input: Repository with CMake and Makefile projects
   - Expected output: Both build systems detected, targets enumerated, dependency graph created

3. **Golden Log: Convention Violations**:
   - Input: Repository with naming convention violations
   - Expected output: Violations detected, issues/tasks created with proper linking

---

## Linking & Terminology

### Relationship to Track/Phase/Task Model

- **Tracks**: Repo Resolve may inform multiple tracks:
  - `bootstrap` track: Initial repository understanding
  - `refactor` track: Convention violation fixes
  - `build` track: Build system configuration

- **Phases**: Each track may contain repo resolve phases:
  - `bootstrap` track:
    - Phase `bs1`: Repository structure analysis
    - Phase `bs2`: Convention detection
  - `refactor` track:
    - Phase `rf1`: Naming convention fixes
    - Phase `rf2`: Layout violations fixes

- **Tasks**: Generated from detected violations:
  - `TASK-001` in phase `rf1`: "Fix naming convention violation in src/core.cpp"

### Truth File Boundaries

- **Truth Files** (validated, protected):
  - `docs/maestro/repo/index.json`
  - `docs/maestro/repo/state.json`
  - `docs/maestro/repo/assemblies.json`
  - `issue data*.md` (structured front-matter required)
  - `docs/maestro/tasks/*.json`

- **Non-Truth Files**:
  - `docs/maestro/repo/index.summary.txt` (informational only)
  - `docs/maestro/repo/hierarchy.json` (derived from index.json)

### Integration Spine Role

**WF-05 as Integration Spine**:
- All other workflows that need repository structure information should call WF-05
- Eliminates duplicate detection logic across workflows
- Ensures consistency in repository understanding
- Provides single source of truth for packages, assemblies, and build systems

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-12-25 | Initial creation | Qwen Code |

---

## Related Documentation

- [index.md](index.md) - Scenario directory
- [README.md](README.md) - Workflow conventions
- [scenario_05_repo_resolve_packages_conventions_targets.puml](scenario_05_repo_resolve_packages_conventions_targets.puml) - Visual diagram
- [command_repo_resolve.md](command_repo_resolve.md) - Command-specific documentation
- [../CLAUDE.md](../CLAUDE.md) - Agent instructions and policy requirements
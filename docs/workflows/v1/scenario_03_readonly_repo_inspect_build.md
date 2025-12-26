# WF-03: Read-only repo inspection + build

## Metadata

```
id: WF-03
title: Read-only repo inspection + build
tags: [readonly, repo-scan, detection, build, make]
entry_conditions: 
  - Existing repository with build files (Makefile, CMakeLists.txt, etc.)
  - Required build tools installed (make, cmake, etc.)
  - No Maestro initialization required (read-only mode)
exit_conditions: 
  - Repository scan report produced
  - Build completed with success/failure status and diagnostics
artifacts_created: 
  - None by default (read-only mode)
  - Optional: scan reports in $HOME/.maestro/repo/ if scanning performed
failure_semantics: 
  - Build failures are recoverable with diagnostics reported
  - Hard stops only on critical toolchain issues
related_commands: 
  - maestro repo resolve (if available)
  - maestro make build
  - maestro repo list
notes_on_state: 
  - "Read-only mode: No docs/ or project state created by default"
  - "Transient scan data stored in $HOME/.maestro/repo/ if scanning performed"
```

## Core Workflow Narrative

This workflow describes how an Operator uses Maestro to discover repository structure and optionally build the project without adopting full Maestro task management or project state.

### 1. Repository Inspection

The Operator runs repository inspection commands to detect:
- Build files (Makefile, CMakeLists.txt, configure.ac, pom.xml, build.gradle, etc.)
- Programming languages used in the repository
- Project packages/assemblies (especially Ultimate++ .upp files)
- Unknown or untracked paths in the repository

### 2. Resolver Step

The Operator executes `maestro repo resolve` (WF-05) to perform comprehensive repository analysis:
- Package/assembly discovery (including Ultimate++ `.upp` + assemblies)
- Language detection
- Build system detection (Make/CMake/Meson/Cargo/etc.)
- Convention inference and rule set selection
- Build target enumeration
- Dependency graph derivation
- Violation detection with Issue/Task creation

### 3. Build Execution

The Operator runs the build step using Maestro's universal build orchestration:
- `maestro make build` to compile the project
- Build diagnostics (errors/warnings) are captured and reported
- Build success/failure status is returned to the Operator

### 4. Diagnostics Reporting

Build diagnostics are printed to stdout and optionally exported as reports (JSON/Markdown) without requiring tasks/issues:
- Compiler errors and warnings
- Linker errors
- Static analysis findings (if requested)
- Build performance metrics

## Branch Boundaries Note

**Important**: Maestro operates strictly on the current Git branch. Switching branches during `maestro repo` or build operations is **unsupported** and risks corrupting state or producing inconsistent results. This is an **operational rule**. Users must ensure they are on the desired branch before initiating repository inspection or build processes.

## Critical Ambiguity Resolution

### Does this scenario require `maestro init`?

**Answer: No, not required.** Maestro can operate in read-only mode for repository inspection and building:

- Repository scanning functionality can work without project state
- Scan results are stored in `$HOME/.maestro/repo/` (user-specific)
- Build operations work without project state if build system is detected
- No `docs/` directory creation required for basic operations

However, if the `maestro repo` command is not available (as appears to be the case in current implementation), the Operator may need to use alternative commands like `maestro make` directly.

## Command Contracts

### `maestro make build`
- **Purpose**: Build packages using detected or specified build method
- **Inputs**: 
  - Optional package name
  - Optional build method (`--method`)
  - Optional build configuration (`--config` for U++)
  - Parallel jobs (`--jobs` or `-j`)
- **Outputs**: 
  - Build success/failure status to stdout
  - Build artifacts in project-specific directories
  - Error logs if build fails
- **Exit codes**: 0 for success, 1 for failure
- **Hard-stop conditions**: Missing build tools, critical compilation errors

### `maestro make config detect`
- **Purpose**: Auto-detect and create build methods based on available tools
- **Inputs**: None
- **Outputs**: Created build method configurations
- **Exit codes**: 0 for success, 1 for failure
- **Hard-stop conditions**: None (non-critical operation)

### `maestro make analyze`
- **Purpose**: Run static analyzers and report findings
- **Inputs**: 
  - Optional analyzer tools (`--tools`)
  - Target path (`--path`)
- **Outputs**: 
  - Analyzer findings to stdout
  - Issues created in Maestro issue system (if available)
- **Exit codes**: 0 for success, 1 for failure
- **Hard-stop conditions**: Missing analyzer tools

## Test Mapping

### Unit Tests
- Repository detection parsing (build file detection)
- Build driver selection logic
- Make invocation string building
- Package detection algorithms

### Integration Fixtures
- Repository with Makefile + build success
- Repository with Makefile + compilation error
- Repository with multiple Makefiles / ambiguous driver
- Ultimate++ repository with .upp files
- Multi-language repository (C++, Java, Python)
- Repository with no build system (should fail gracefully)

## Implementation Notes

Based on codebase analysis, the `maestro repo` command appears to be missing from the CLI registration, though the underlying functionality exists in the codebase. The repository scanning functionality exists in the UI facade and TUI, but may not be accessible through the main CLI.

The read-only inspection functionality can still be accessed through:
- Direct use of `maestro make` commands for building
- Potential TUI access for repository scanning
- The underlying repository scanning functions via the API
# Phase umk12: Retroactive Fixes and Missing Components 🚧 **[CURRENT - Critical]**

**Reference**: `docs/PHASE7_IMPROVEMENTS.md`
**Duration**: 3-5 weeks
**Dependencies**: None (fixes issues in Phases 1-7)
**Status**: BLOCKING - Must complete before continuing other phases

**Objective**: Fix critical blockers and gaps identified in earlier phases that were skipped or incompletely implemented.

## Background
Phase 10+ work revealed critical missing infrastructure from Phases 1-7. These must be fixed retroactively to unblock development.

## Critical Blockers

- [ ] **umk12.1: Fix Broken Import Chain** (P0 - 1 day)
  - [ ] Fix `ModuleNotFoundError: No module named 'maestro.repo.package'`
  - [ ] Audit all imports in `maestro/builders/` and `maestro/commands/`
  - [ ] Create missing modules or fix incorrect import paths
  - [ ] **Blocker**: Entire `maestro` command is currently broken
  - Reference: PHASE7_IMPROVEMENTS.md Blocker 1

- [ ] **umk12.2: Package Metadata Bridge** (P0 - 2 days)
  - [ ] Create canonical `maestro/repo/package.py` with `PackageInfo` dataclass
  - [ ] Implement `PackageInfo.to_builder_package()` conversion method
  - [ ] Update `maestro/builders/base.py` Package class to work with PackageInfo
  - [ ] Fix all references to use canonical definition
  - [ ] Add validation tests for package conversion
  - **Blocker**: Can't bridge repo scanning to build system
  - **Reference**: PHASE7_IMPROVEMENTS.md Blocker 2

## Missing Phase Components

- [ ] **umk12.3: Phase 5.75 - Gradle Builder** (P1 - 1-2 weeks)
  - [ ] Create `maestro/builders/gradle.py` module
  - [ ] Implement `configure()` to detect gradle/gradlew
  - [ ] Implement `build_package()` with gradle command invocation
  - [ ] Support multi-module Gradle projects
  - [ ] Support Kotlin DSL (.gradle.kts) and Groovy (.gradle)
  - [ ] Support build flags: `--max-workers`, `-x test`, `--offline`
  - [ ] Integration test with `~/Dev/RainbowGame/trash`
  - **Gap**: Gradle packages are scanned (100%) but can't be built
  - **Reference**: PHASE7_IMPROVEMENTS.md Blocker 4

- [ ] **umk12.4: Phase 6.5 - Build Configuration Discovery** (P0 - 1-2 weeks)
  - [ ] **umk12.4.1: Configuration Extraction Infrastructure**
    - [ ] Create `maestro/builders/config_discovery.py` module
    - [ ] Define `BuildConfiguration` dataclass (compiler, flags, includes, defines)
    - [ ] Implement base `ConfigDiscoverer` abstract class

  - [ ] **umk12.4.2: CMake Config Extraction**
    - [ ] Run cmake in configure mode to generate compile_commands.json
    - [ ] Parse compile_commands.json for compiler flags
    - [ ] Extract from CMakeCache.txt as fallback

  - [ ] **umk12.4.3: Autotools Config Extraction**
    - [ ] Run `./configure --help` to discover options
    - [ ] Parse generated Makefile for CFLAGS/CXXFLAGS/LDFLAGS
    - [ ] Extract include paths and defines

  - [ ] **umk12.4.4: Gradle/Maven Config Extraction**
    - [ ] Parse build.gradle(.kts) for dependencies and compile options
    - [ ] Parse pom.xml for Maven configuration
    - [ ] Extract Java version, classpath, source directories

  - [ ] **umk12.4.5: U++ Config Resolution**
    - [ ] Parse .upp file (reuse existing parser)
    - [ ] Resolve `uses` dependencies to include paths
    - [ ] Resolve mainconfig flags (GUI, MT, etc.)

  - [ ] **umk12.4.6: CLI Implementation**
    - [ ] Implement `maestro repo conf [PACKAGE_ID]` command
    - [ ] Display formatted build configuration
    - [ ] Support JSON output: `maestro repo conf [ID] --json`
    - [ ] Cache configs in `.maestro/repo/configs/<package>.json`

  - **Blocker**: Can't build or generate AST without knowing compilation flags
  - **Reference**: PHASE7_IMPROVEMENTS.md Blocker 3

## Phase 7 Gaps (Retroactive)

- [ ] **umk12.5: Builder Selection Logic** (from Phase 7.3)
  - [ ] Implement `select_builder(package, config)` function
  - [ ] Support explicit builder selection via `--method` flag
  - [ ] Auto-detect builder from package type
  - [ ] Add fallback/error handling for unsupported types
  - [ ] Builder selection priority: explicit → package type → error
  - **Gap**: Phase 7 says "auto-detect" but doesn't specify HOW
  - **Reference**: PHASE7_IMPROVEMENTS.md Gap 1

- [ ] **umk12.6: Dependency Build Order** (from Phase 7.5)
  - [ ] Implement topological sort (Kahn's algorithm)
  - [ ] Build dependency graph from package metadata
  - [ ] Detect and report circular dependencies
  - [ ] Build packages in correct order
  - [ ] Add `--parallel` flag to build independent packages in parallel
  - **Gap**: Phase 7 says "build in dependency order" but no algorithm
  - **Reference**: PHASE7_IMPROVEMENTS.md Gap 2

- [ ] **umk12.7: Error Recovery and Build Sessions** (new for Phase 7)
  - [ ] Create `BuildSession` class to track build state
  - [ ] Persist session to `.maestro/build/session.json`
  - [ ] Track completed, failed, and skipped packages
  - [ ] Implement `--keep-going` flag (continue despite errors)
  - [ ] Implement `--resume` flag (resume from last failure)
  - [ ] Implement `--stop-on-error` (default behavior)
  - **Gap**: No error recovery when multi-package builds fail
  - **Reference**: PHASE7_IMPROVEMENTS.md Gap 3

- [ ] **umk12.8: Build Artifact Management** (from Phase 7.5)
  - [ ] Define artifact storage structure (`.maestro/build/<method>/<package>/`)
  - [ ] Create artifact registry `.maestro/build/artifacts.json`
  - [ ] Track built targets, timestamps, config hashes
  - [ ] Implement artifact lookup for dependent packages
  - [ ] Support `maestro make clean [PACKAGE]` vs `maestro make clean --all`
  - **Gap**: No specification of where outputs go or how to find them
  - **Reference**: PHASE7_IMPROVEMENTS.md Gap 4

## Integration and Testing

- [ ] **umk12.9: Fix Existing Tests**
  - [ ] Update all tests to use canonical PackageInfo
  - [ ] Fix broken imports in test files
  - [ ] Add tests for package conversion
  - [ ] Add tests for builder selection
  - [ ] Add tests for dependency ordering

- [ ] **umk12.10: Integration Test Suite**
  - [ ] Multi-package build test (U++ with dependencies)
  - [ ] Cross-build-system test (CMake → Autotools dependency)
  - [ ] Gradle project test (`~/Dev/RainbowGame/trash`)
  - [ ] Error recovery test (--keep-going, --resume)
  - [ ] Build artifact tracking test

## Deliverables:
- Working maestro command (fix broken imports)
- Canonical package representation with conversion
- Gradle builder implementation
- Build configuration discovery (`maestro repo conf`)
- Complete Phase 7 implementation with all gaps filled
- Comprehensive test suite

## Test Criteria:
- All maestro commands work without import errors
- Can build Gradle projects
- `maestro repo conf` shows correct build configuration
- Multi-package builds work in dependency order
- Error recovery works (--keep-going, --resume)
- Build artifacts are properly tracked

## Priority: P0 - BLOCKING
This phase must complete before any other development can continue.

## Estimated Complexity: High (3-5 weeks total)
- Week 1: Critical blockers (12.1, 12.2)
- Week 2-3: Missing components (12.3, 12.4)
- Week 4-5: Phase 7 gaps (12.5-12.8) + testing

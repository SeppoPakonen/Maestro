# Maestro Development TODO

> **Planning Document**: Comprehensive roadmap for Maestro development, covering universal build system integration, Portage integration, and external dependency management.

**Last Updated**: 2025-12-17 (added Phase 12: Retroactive Fixes - CURRENT BLOCKING PHASE)

---

## Table of Contents

1. [Phase Completion Status](#phase-completion-status)
2. [Primary Track: UMK Integration (Universal Build System)](#primary-track-umk-integration-universal-build-system)
3. [TU/AST Track: Translation Unit and AST Generation](#tuast-track-translation-unit-and-ast-generation)
4. [Extended Track: Additional Build Systems](#extended-track-additional-build-systems)
5. [Advanced Track: External Dependencies and Portage Integration](#advanced-track-external-dependencies-and-portage-integration)
6. [Integration and Testing](#integration-and-testing)

---

## Phase Completion Status

### Legend
- ✅ **Done**: Completed and tested
- 🚧 **In Progress**: Currently being worked on
- 📋 **Planned**: Specified and scheduled
- 💡 **Proposed**: Concept stage, needs refinement

### Current Status Overview

| Track | Phase | Status | Completion |
|-------|-------|--------|------------|
| **Repository Scanning** | | | |
| | U++ packages | ✅ Done | 100% |
| | CMake packages | ✅ Done | 100% |
| | Autoconf packages | ✅ Done | 100% |
| | Visual Studio packages | ✅ Done | 100% |
| | Maven packages | ✅ Done | 100% |
| | Gradle packages | ✅ Done | 100% |
| | Python packages | 📋 Planned | 0% |
| | Node.js packages | 📋 Planned | 0% |
| | Go packages | 📋 Planned | 0% |
| | pup packages | 📋 Planned | 0% |
| **Build System** | | | |
| | Core builder abstraction | 🚧 In Progress | 60% |
| | U++ builder | 🚧 In Progress | 40% |
| | CMake builder | 🚧 In Progress | 50% |
| | Autotools builder | 🚧 In Progress | 50% |
| | MSBuild builder | 🚧 In Progress | 40% |
| | Maven builder | 🚧 In Progress | 40% |
| | Gradle builder | 📋 Planned | 0% |
| | **Phase 12: Retroactive Fixes** | 🚧 **CURRENT** | **10%** |
| **TU/AST System** | | | |
| | Core AST infrastructure | 📋 Planned | 0% |
| | Incremental TU builder | 📋 Planned | 0% |
| | Symbol resolution | 📋 Planned | 0% |
| | Auto-completion | 📋 Planned | 0% |
| | Build integration | 📋 Planned | 0% |
| | Code transformation | 📋 Planned | 0% |
| **External Dependencies** | | | |
| | Git submodule handling | 📋 Planned | 0% |
| | Build script integration | 📋 Planned | 0% |
| | Portage integration | 💡 Proposed | 0% |
| | Host package recognition | 💡 Proposed | 0% |

---

## Primary Track: UMK Integration (Universal Build System)

This track implements all phases from `docs/umk.md`, creating a universal build orchestration system.

### Phase 1: Core Builder Abstraction ✅ **[Design Complete]** 📋 **[Implementation Planned]**

**Reference**: `docs/umk.md` Phase 1
**Duration**: 2-3 weeks
**Dependencies**: None

**Objective**: Create Python abstraction layer for universal build system support.

#### Tasks

- [ ] **1.1: Module Structure**
  - [ ] Create `maestro/builders/` module
  - [ ] Implement `base.py` with abstract `Builder` base class
  - [ ] Define builder interface methods:
    - `build_package(package, config)`
    - `link(linkfiles, linkoptions)`
    - `clean_package(package)`
    - `get_target_ext()`
  - [ ] Add type hints and docstrings

- [ ] **1.2: Build Method Configuration**
  - [ ] Design TOML/JSON format for build methods (see umk.md lines 657-703)
  - [ ] Implement method storage in `.maestro/methods/`
  - [ ] Create method parser and validator
  - [ ] Support method inheritance
  - [ ] Implement method auto-detection for system compilers

- [ ] **1.3: Host Abstraction**
  - [ ] Create `host.py` module
  - [ ] Support local builds
  - [ ] Design interface for remote builds (future)
  - [ ] Design interface for Docker builds (future)

- [ ] **1.4: Console Process Management**
  - [ ] Create `console.py` module
  - [ ] Implement parallel job execution using `multiprocessing`
  - [ ] Add process output capture and streaming
  - [ ] Implement error tracking and reporting
  - [ ] Add Ctrl+C handling and cleanup

- [ ] **1.5: Configuration System**
  - [ ] Create `config.py` module
  - [ ] Define `BuildConfig` dataclass
  - [ ] Implement platform detection
  - [ ] Support per-package overrides

**Deliverables**:
- Python builder framework with abstract base class
- Build method configuration system
- Host abstraction
- Console process management

**Test Criteria**:
- Unit tests for builder interface
- Config parsing tests
- Process management tests

---

### Phase 2: U++ Builder Implementation 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 2
**Duration**: 4-6 weeks
**Dependencies**: Phase 1

**Objective**: Build U++ packages using umk logic ported to Python.

#### Tasks

- [ ] **2.1: U++ Package Parser**
  - [ ] Extend existing `.upp` file parsing
  - [ ] Extract `uses`, `files`, `flags`, `mainconfig`
  - [ ] Resolve conditional options based on build flags
  - [ ] Create `Package` dataclass

- [ ] **2.2: Workspace Dependency Resolver**
  - [ ] Create `workspace.py` module
  - [ ] Port `Workspace::Scan()` logic
  - [ ] Build dependency graph
  - [ ] Determine build order (topological sort)
  - [ ] Detect circular dependencies

- [ ] **2.3: GCC/Clang Builder**
  - [ ] Create `gcc.py` module
  - [ ] Implement command-line construction
  - [ ] Add include path resolution
  - [ ] Add define/flag handling
  - [ ] Implement source compilation
  - [ ] Implement linking (executable, shared, static)

- [ ] **2.4: MSVC Builder**
  - [ ] Create `msvc.py` module
  - [ ] Port MSVC-specific logic
  - [ ] Implement cl.exe invocation
  - [ ] Implement link.exe invocation

- [ ] **2.5: Incremental Build Support**
  - [ ] Create `ppinfo.py` for dependency tracking
  - [ ] Implement file timestamp comparison
  - [ ] Create build cache in `.maestro/cache/`
  - [ ] Add header dependency tracking

- [ ] **2.6: Build Cache Management**
  - [ ] Create `cache.py` module
  - [ ] Store file-level dependencies (see umk.md lines 1103-1113)
  - [ ] Implement cache invalidation
  - [ ] Add cache statistics

**Deliverables**:
- Complete U++ builder
- Support for all mainconfig options
- Parallel build support
- Incremental builds with dependency tracking

**Test Repositories**:
- `~/Dev/ai-upp` (U++ framework)
- U++ sample applications

**Test Criteria**:
- Build ai-upp packages successfully
- Incremental builds work correctly
- Parallel builds produce correct output

---

### Phase 3: CMake Builder 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 3
**Duration**: 2-3 weeks
**Dependencies**: Phase 1

**Objective**: Build CMake packages detected by `maestro repo resolve`.

#### Tasks

- [ ] **3.1: CMake Builder Implementation**
  - [ ] Create `cmake.py` module
  - [ ] Implement `configure()` method
  - [ ] Implement `build_package()` method
  - [ ] Support CMake arguments: `-DCMAKE_BUILD_TYPE`, `-DCMAKE_INSTALL_PREFIX`

- [ ] **3.2: Configuration Mapping**
  - [ ] Map Maestro config → CMake variables
  - [ ] Support Debug/Release builds
  - [ ] Support compiler selection
  - [ ] Generate toolchain files for cross-compilation

- [ ] **3.3: Target Support**
  - [ ] Build specific targets
  - [ ] Support install targets
  - [ ] Support CPack package generation

- [ ] **3.4: Generator Support**
  - [ ] Support Unix Makefiles
  - [ ] Support Ninja
  - [ ] Support Visual Studio (multi-config)
  - [ ] Support Xcode (multi-config)

**Deliverables**:
- CMake builder
- Support for CMakePresets.json
- Cross-compilation support

**Test Repositories**:
- `~/Dev/pedigree` (CMake-based OS)

**Test Criteria**:
- Build pedigree successfully
- CMake configuration works
- Multi-config generators work

---

### Phase 4: Autotools Builder 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 4
**Duration**: 2-3 weeks
**Dependencies**: Phase 1

**Objective**: Build Autotools packages detected by `maestro repo resolve`.

#### Tasks

- [ ] **4.1: Autotools Builder Implementation**
  - [ ] Create `autotools.py` module
  - [ ] Implement `configure()` method
  - [ ] Run `autoreconf` if needed
  - [ ] Support `./configure` arguments

- [ ] **4.2: Configuration Options**
  - [ ] Map Maestro config → configure flags
  - [ ] Support `--prefix`, `--enable-debug`
  - [ ] Support custom `CFLAGS`, `CXXFLAGS`
  - [ ] Support cross-compilation (host/build/target)

- [ ] **4.3: Build Execution**
  - [ ] Implement parallel make (`-j`)
  - [ ] Support VPATH builds (out-of-source)
  - [ ] Handle GNU Make and BSD Make

**Deliverables**:
- Autotools builder
- Support for configure options
- Cross-compilation support

**Test Repositories**:
- Various Autotools-based projects

**Test Criteria**:
- Configure and build work
- Parallel builds work
- Cross-compilation works

---

### Phase 5: MSBuild / Visual Studio Builder 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 5
**Duration**: 2-3 weeks
**Dependencies**: Phase 1

**Objective**: Build Visual Studio projects detected by `maestro repo resolve`.

#### Tasks

- [ ] **5.1: MSBuild Builder Implementation**
  - [ ] Create `msbuild.py` module
  - [ ] Implement MSBuild invocation
  - [ ] Support Configuration selection (Debug/Release)
  - [ ] Support Platform selection (Win32/x64/ARM/ARM64)

- [ ] **5.2: Project Types**
  - [ ] Support `.vcxproj` (MSBuild C++)
  - [ ] Support `.csproj` (MSBuild C#)
  - [ ] Support `.vcproj` (legacy VCBuild)

- [ ] **5.3: Solution Builds**
  - [ ] Parse `.sln` files
  - [ ] Resolve project dependencies
  - [ ] Build projects in correct order

**Deliverables**:
- MSBuild builder
- Support for all configurations/platforms
- Solution-level builds

**Test Repositories**:
- `~/Dev/StuntCarStadium` (Unity/Visual Studio)

**Test Criteria**:
- Build Visual Studio projects
- Configuration selection works
- Solution builds work

---

### Phase 5.5: Maven Builder 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 5.5
**Duration**: 1-2 weeks
**Dependencies**: Phase 1

**Objective**: Build Maven projects detected by `maestro repo resolve`.

#### Tasks

- [ ] **5.5.1: Maven Builder Implementation**
  - [ ] Create `maven.py` module
  - [ ] Implement `build_package()` method
  - [ ] Support Maven lifecycle phases (clean, compile, test, package, install)
  - [ ] Support parallel module builds (`-T` flag)

- [ ] **5.5.2: Maven Features**
  - [ ] Profile activation (`-P` flag)
  - [ ] Offline mode (`--offline`)
  - [ ] Skip tests (`-DskipTests`)
  - [ ] Property overrides (`-D` flags)

- [ ] **5.5.3: Multi-Module Support**
  - [ ] Reactor builds
  - [ ] Module ordering
  - [ ] Partial reactor builds

- [ ] **5.5.4: Packaging Types**
  - [ ] JAR packaging
  - [ ] WAR packaging
  - [ ] AAR packaging (Android)
  - [ ] POM packaging (parent POMs)
  - [ ] Native module support (JNI)

**Deliverables**:
- Maven builder
- Multi-module reactor builds
- Profile and property configuration

**Test Repositories**:
- `~/Dev/TopGuitar` (Maven multi-module)

**Test Criteria**:
- Build TopGuitar successfully
- Reactor builds work
- Profile activation works

---

### Phase 6: Universal Build Configuration 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 6
**Duration**: 2-3 weeks
**Dependencies**: Phases 2-5.5

**Objective**: Unified configuration system for all build systems.

#### Tasks

- [ ] **6.1: Unified Configuration Format**
  - [ ] Design TOML format (see umk.md lines 657-703)
  - [ ] Support compiler settings
  - [ ] Support flags and options
  - [ ] Support platform settings

- [ ] **6.2: Method Auto-Detection**
  - [ ] Detect available compilers
  - [ ] Detect build tools
  - [ ] Generate default methods
  - [ ] Store in `.maestro/methods/`

- [ ] **6.3: Method Inheritance**
  - [ ] Implement inheritance mechanism
  - [ ] Support override of inherited values
  - [ ] Validate inherited configurations

- [ ] **6.4: Per-Package Overrides**
  - [ ] Store in `.maestro/packages/<package>/method.toml`
  - [ ] Support package-specific flags
  - [ ] Support builder selection per package

**Deliverables**:
- Unified build configuration
- Method auto-detection
- Method inheritance
- Per-package overrides

**Test Criteria**:
- Methods detected correctly
- Inheritance works
- Package overrides apply correctly

---

### Phase 7: CLI Integration 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 7
**Duration**: 3-4 weeks
**Dependencies**: Phases 2-6

**Objective**: Expose build functionality through `maestro make` command.

#### Tasks

- [ ] **7.1: Command Structure**
  - [ ] Implement `maestro make build` (see umk.md lines 723-735)
  - [ ] Implement `maestro make clean` (lines 736-737)
  - [ ] Implement `maestro make rebuild` (lines 739-741)
  - [ ] Implement `maestro make config` (lines 743-750)
  - [ ] Implement `maestro make export` (lines 752-758)
  - [ ] Implement `maestro make methods` (line 760-761)
  - [ ] Implement `maestro make android` (lines 763-773)
  - [ ] Implement `maestro make jar` (lines 775-782)

- [ ] **7.2: Package Selection**
  - [ ] By name: `maestro make build MyPackage`
  - [ ] By pattern: `maestro make build "core/*"`
  - [ ] Main package: `maestro make build` (from current dir)
  - [ ] Build all: `maestro make build --all`

- [ ] **7.3: Method Selection**
  - [ ] Auto-detect: Use package's native build system
  - [ ] Explicit: `maestro make build --method gcc-debug`
  - [ ] U++ config: `maestro make build --config "GUI MT"`

- [ ] **7.4: Output Formatting**
  - [ ] Progress indicator for parallel builds
  - [ ] Error highlighting
  - [ ] Warning/error count summary
  - [ ] Build time reporting

- [ ] **7.5: Repository Integration**
  - [ ] Load packages from `.maestro/repo/index.json`
  - [ ] Resolve dependencies using `repo pkg tree`
  - [ ] Build in dependency order

**Deliverables**:
- Complete `maestro make` CLI
- Integration with `maestro repo`
- User-friendly output

**Test Criteria**:
- All CLI commands work
- Package selection works
- Output is clear and helpful

---

### Phase 8: Advanced Features 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 8
**Duration**: 6-8 weeks
**Dependencies**: Phase 7

**Objective**: Port advanced umk features.

#### Tasks

- [ ] **8.1: Blitz Build (Unity Build)**
  - [ ] Create `blitz.py` module
  - [ ] Concatenate multiple .cpp files
  - [ ] Auto-generate blitz files
  - [ ] Detect blitz-safe files
  - [ ] Support per-file opt-out

- [ ] **8.2: Precompiled Headers (PCH)**
  - [ ] Implement PCH generation
  - [ ] Auto-detect frequently used headers
  - [ ] Support per-file PCH opt-out

- [ ] **8.3: Binary Resource Compilation (.brc)**
  - [ ] Embed binary files in executables
  - [ ] Generate C++ arrays from binary data
  - [ ] Support compression (gzip, bz2, lzma, zstd)

- [ ] **8.4: Android Builds** (see umk.md lines 836-881)
  - [ ] Create `android_sdk.py` module
  - [ ] Create `android_ndk.py` module
  - [ ] Create `android_manifest.py` module
  - [ ] Create `apk.py` module
  - [ ] Implement SDK detection and validation
  - [ ] Implement NDK integration
  - [ ] Implement multi-architecture builds
  - [ ] Implement APK packaging and signing
  - [ ] Implement resource compilation (aapt)
  - [ ] Implement DEX generation (d8/dx)

- [ ] **8.5: Java Builds** (see umk.md lines 883-916)
  - [ ] Create `jdk.py` module
  - [ ] Create `jar.py` module
  - [ ] Implement JDK detection
  - [ ] Implement Java compilation
  - [ ] Implement JAR packaging
  - [ ] Implement JNI support

- [ ] **8.6: Export Features**
  - [ ] Create `export.py` module
  - [ ] Generate Makefile from any package
  - [ ] Generate CMakeLists.txt from U++ package
  - [ ] Generate Visual Studio project from U++ package
  - [ ] Generate Ninja build file

- [ ] **8.7: Cross-Compilation**
  - [ ] Toolchain file support
  - [ ] Sysroot configuration
  - [ ] Host vs target tool selection

**Deliverables**:
- Advanced build features
- Export to multiple formats
- Cross-compilation support
- Android/Java support

**Test Criteria**:
- Blitz builds work
- PCH improves build times
- Android APKs build successfully
- JAR files build successfully
- Export generates valid build files

---

### Phase 9: TUI Integration 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 9
**Duration**: 3-4 weeks
**Dependencies**: Phase 7

**Objective**: Integrate build system into Maestro TUI.

#### Tasks

- [ ] **9.1: Build Pane**
  - [ ] Create build progress display
  - [ ] Show compiler output
  - [ ] Highlight errors and warnings
  - [ ] Enable navigation to error locations

- [ ] **9.2: Build Configuration UI**
  - [ ] Method selection widget
  - [ ] Package selection tree
  - [ ] Build options editor
  - [ ] Parallel job control

- [ ] **9.3: Interactive Build Features**
  - [ ] Stop/resume builds
  - [ ] Build selected packages
  - [ ] Jump to error in editor
  - [ ] Filter warnings/errors

**Deliverables**:
- TUI build interface
- Real-time build monitoring
- Error navigation

**Test Criteria**:
- TUI shows build progress
- Error navigation works
- Build control works

---

### Phase 10: Universal Hub System (MaestroHub) 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 10
**Duration**: 4-5 weeks
**Dependencies**: Phases 2-7

**Objective**: Universal package hub for automatic dependency resolution.

#### Tasks

- [ ] **10.1: Hub Metadata Format**
  - [ ] Define JSON schema for hub registries (see umk.md lines 260-292)
  - [ ] Support UppHub compatibility
  - [ ] Multi-build-system package metadata
  - [ ] Versioning and compatibility tracking

- [ ] **10.2: Hub Client**
  - [ ] Create `hub/client.py` module
  - [ ] Implement `load_hub(url)`
  - [ ] Implement `search_package(name)`
  - [ ] Implement `install_nest(name)`
  - [ ] Implement `auto_resolve(workspace)`

- [ ] **10.3: CLI Integration** (see umk.md lines 999-1020)
  - [ ] Implement `maestro hub list`
  - [ ] Implement `maestro hub search`
  - [ ] Implement `maestro hub install`
  - [ ] Implement `maestro hub update`
  - [ ] Implement `maestro hub add`
  - [ ] Implement `maestro hub sync`
  - [ ] Implement `maestro hub info`

- [ ] **10.4: Auto-Resolution**
  - [ ] Detect missing packages during build
  - [ ] Search registered hubs
  - [ ] Prompt user for installation
  - [ ] Clone repositories to `~/.maestro/hub/`
  - [ ] Recursive dependency resolution

- [ ] **10.5: Hub Registry Management**
  - [ ] Create official MaestroHub registry
  - [ ] Import existing UppHub
  - [ ] Support custom/private hubs
  - [ ] Support organization-specific hubs

- [ ] **10.6: Package Path Resolution**
  - [ ] Search order: local → hub → system
  - [ ] Package name disambiguation
  - [ ] Version conflict resolution

- [ ] **10.7: Integration with Package Managers**
  - [ ] Conan wrapper for C++ packages
  - [ ] vcpkg integration
  - [ ] npm/pip/cargo bridge (future)

**Deliverables**:
- Universal hub client
- CLI commands for hub management
- Auto-dependency resolution
- UppHub compatibility

**Test Criteria**:
- Hub metadata loads correctly
- Package search works
- Auto-resolution works
- Build + hub workflow works (see umk.md lines 1250-1274)

---

### Phase 11: Internal Package Groups 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 11
**Duration**: 2-3 weeks
**Dependencies**: Phase 7

**Objective**: Implement internal package grouping for better organization and navigation.

#### Background

U++ packages use **separators** to organize files into logical groups within a package. A separator is a file entry with the `separator` flag that acts as a group title. Files following a separator belong to that group until the next separator.

Example from `CtrlCore.upp`:
```
file
    Core readonly separator,        # Group: "Core"
    CtrlCore.h,                      # → belongs to "Core" group
    MKeys.h,
    Win32 readonly separator,        # Group: "Win32"
    Win32Gui.h,                      # → belongs to "Win32" group
    X11 readonly separator,          # Group: "X11"
    X11Gui.h,                        # → belongs to "X11" group
```

For misc packages (root files), auto-group by file type:
- Documentation: .md, .txt, .rst files
- Scripts: .sh, .py, .js files
- Build Files: Makefile, CMakeLists.txt, build.gradle, etc.
- Python/Java/C++: Language-specific groups
- Other: Catch-all for remaining files

#### Tasks

- [ ] **11.1: Group Representation**
  - [ ] Create `FileGroup` dataclass in package metadata
  - [ ] Add `groups` and `ungrouped_files` fields to `PackageInfo`
  - [ ] Support readonly flag on groups

- [ ] **11.2: U++ Separator Parsing**
  - [ ] Enhance `upp_parser.py` to extract separator names
  - [ ] Build group structure from separator markers
  - [ ] Handle multiple consecutive separators
  - [ ] Support quoted separator names with spaces

- [ ] **11.3: Auto-Grouping for Misc Packages**
  - [ ] Create `AutoGrouper` class
  - [ ] Define GROUP_RULES for file extensions
  - [ ] Implement pattern matching for file grouping
  - [ ] Group by extension and file patterns
  - [ ] Sort groups and files within groups

- [ ] **11.4: CLI Support**
  - [ ] Implement `maestro repo pkg [ID] --show-groups`
  - [ ] Implement `maestro repo pkg [ID] --group [GROUP]`
  - [ ] Display group headers with file counts
  - [ ] Support collapsed/expanded view

- [ ] **11.5: TUI Integration**
  - [ ] Show groups in package view (collapsible tree)
  - [ ] Navigate between groups (Tab/Shift+Tab)
  - [ ] Filter/search within group
  - [ ] Show group statistics (file count, LOC)
  - [ ] Syntax highlighting for group headers

- [ ] **11.6: Build Integration**
  - [ ] Implement `maestro make build [PACKAGE] --group [GROUP]`
  - [ ] Build specific group only (useful for platform-specific code)
  - [ ] Dependency tracking per group

- [ ] **11.7: Export Support**
  - [ ] Export groups to Visual Studio filters (.vcxproj.filters)
  - [ ] Export groups to CMake source_group()
  - [ ] Export groups to IntelliJ modules

**Deliverables**:
- Group representation in package metadata
- U++ separator parsing with group extraction
- Auto-grouping for misc packages
- CLI support for viewing and filtering groups
- TUI integration with collapsible group view
- Build support for group-specific compilation
- Export to IDE project structures

**Test Criteria**:
- U++ packages with separators parse correctly
- Groups display in CLI output
- Misc packages auto-group by extension
- Platform-specific group builds work (e.g., build only Win32 group)
- Export to IDE formats preserves group structure

---

### Phase 12: Retroactive Fixes and Missing Components 🚧 **[CURRENT - Critical]**

**Reference**: `docs/PHASE7_IMPROVEMENTS.md`
**Duration**: 3-5 weeks
**Dependencies**: None (fixes issues in Phases 1-7)
**Status**: BLOCKING - Must complete before continuing other phases

**Objective**: Fix critical blockers and gaps identified in earlier phases that were skipped or incompletely implemented.

**Background**: Phase 10+ work revealed critical missing infrastructure from Phases 1-7. These must be fixed retroactively to unblock development.

#### Critical Blockers

- [ ] **12.1: Fix Broken Import Chain** (P0 - 1 day)
  - [ ] Fix `ModuleNotFoundError: No module named 'maestro.repo.package'`
  - [ ] Audit all imports in `maestro/builders/` and `maestro/commands/`
  - [ ] Create missing modules or fix incorrect import paths
  - [ ] **Blocker**: Entire `maestro` command is currently broken
  - **Reference**: PHASE7_IMPROVEMENTS.md Blocker 1

- [ ] **12.2: Package Metadata Bridge** (P0 - 2 days)
  - [ ] Create canonical `maestro/repo/package.py` with `PackageInfo` dataclass
  - [ ] Implement `PackageInfo.to_builder_package()` conversion method
  - [ ] Update `maestro/builders/base.py` Package class to work with PackageInfo
  - [ ] Fix all references to use canonical definition
  - [ ] Add validation tests for package conversion
  - **Blocker**: Can't bridge repo scanning to build system
  - **Reference**: PHASE7_IMPROVEMENTS.md Blocker 2

#### Missing Phase Components

- [ ] **12.3: Phase 5.75 - Gradle Builder** (P1 - 1-2 weeks)
  - [ ] Create `maestro/builders/gradle.py` module
  - [ ] Implement `configure()` to detect gradle/gradlew
  - [ ] Implement `build_package()` with gradle command invocation
  - [ ] Support multi-module Gradle projects
  - [ ] Support Kotlin DSL (.gradle.kts) and Groovy (.gradle)
  - [ ] Support build flags: `--max-workers`, `-x test`, `--offline`
  - [ ] Integration test with `~/Dev/RainbowGame/trash`
  - **Gap**: Gradle packages are scanned (100%) but can't be built
  - **Reference**: PHASE7_IMPROVEMENTS.md Blocker 4

- [ ] **12.4: Phase 6.5 - Build Configuration Discovery** (P0 - 1-2 weeks)
  - [ ] **12.4.1: Configuration Extraction Infrastructure**
    - [ ] Create `maestro/builders/config_discovery.py` module
    - [ ] Define `BuildConfiguration` dataclass (compiler, flags, includes, defines)
    - [ ] Implement base `ConfigDiscoverer` abstract class

  - [ ] **12.4.2: CMake Config Extraction**
    - [ ] Run cmake in configure mode to generate compile_commands.json
    - [ ] Parse compile_commands.json for flags/includes
    - [ ] Extract from CMakeCache.txt as fallback

  - [ ] **12.4.3: Autotools Config Extraction**
    - [ ] Run `./configure --help` to discover options
    - [ ] Parse generated Makefile for CFLAGS/CXXFLAGS/LDFLAGS
    - [ ] Extract include paths and defines

  - [ ] **12.4.4: Gradle/Maven Config Extraction**
    - [ ] Parse build.gradle(.kts) for dependencies and compile options
    - [ ] Parse pom.xml for Maven configuration
    - [ ] Extract Java version, classpath, source directories

  - [ ] **12.4.5: U++ Config Resolution**
    - [ ] Parse .upp file (reuse existing parser)
    - [ ] Resolve `uses` dependencies to include paths
    - [ ] Resolve mainconfig flags (GUI, MT, etc.)

  - [ ] **12.4.6: CLI Implementation**
    - [ ] Implement `maestro repo conf [PACKAGE_ID]` command
    - [ ] Display formatted build configuration
    - [ ] Support JSON output: `maestro repo conf [ID] --json`
    - [ ] Cache configs in `.maestro/repo/configs/<package>.json`

  - **Blocker**: Can't build or generate AST without knowing compilation flags
  - **Reference**: PHASE7_IMPROVEMENTS.md Blocker 3

#### Phase 7 Gaps (Retroactive)

- [ ] **12.5: Builder Selection Logic** (from Phase 7.3)
  - [ ] Implement `select_builder(package, config)` function
  - [ ] Support explicit builder selection via `--method` flag
  - [ ] Auto-detect builder from package type
  - [ ] Add fallback/error handling for unsupported types
  - [ ] Builder selection priority: explicit → package type → error
  - **Gap**: Phase 7 says "auto-detect" but doesn't specify HOW
  - **Reference**: PHASE7_IMPROVEMENTS.md Gap 1

- [ ] **12.6: Dependency Build Order** (from Phase 7.5)
  - [ ] Implement topological sort (Kahn's algorithm)
  - [ ] Build dependency graph from package metadata
  - [ ] Detect and report circular dependencies
  - [ ] Build packages in correct order
  - [ ] Add `--parallel` flag to build independent packages in parallel
  - **Gap**: Phase 7 says "build in dependency order" but no algorithm
  - **Reference**: PHASE7_IMPROVEMENTS.md Gap 2

- [ ] **12.7: Error Recovery and Build Sessions** (new for Phase 7)
  - [ ] Create `BuildSession` class to track build state
  - [ ] Persist session to `.maestro/build/session.json`
  - [ ] Track completed, failed, and skipped packages
  - [ ] Implement `--keep-going` flag (continue despite errors)
  - [ ] Implement `--resume` flag (resume from last failure)
  - [ ] Implement `--stop-on-error` (default behavior)
  - **Gap**: No error recovery when multi-package builds fail
  - **Reference**: PHASE7_IMPROVEMENTS.md Gap 3

- [ ] **12.8: Build Artifact Management** (from Phase 7.5)
  - [ ] Define artifact storage structure (`.maestro/build/<method>/<package>/`)
  - [ ] Create artifact registry `.maestro/build/artifacts.json`
  - [ ] Track built targets, timestamps, config hashes
  - [ ] Implement artifact lookup for dependent packages
  - [ ] Support `maestro make clean [PACKAGE]` vs `maestro make clean --all`
  - **Gap**: No specification of where outputs go or how to find them
  - **Reference**: PHASE7_IMPROVEMENTS.md Gap 4

#### Integration and Testing

- [ ] **12.9: Fix Existing Tests**
  - [ ] Update all tests to use canonical PackageInfo
  - [ ] Fix broken imports in test files
  - [ ] Add tests for package conversion
  - [ ] Add tests for builder selection
  - [ ] Add tests for dependency ordering

- [ ] **12.10: Integration Test Suite**
  - [ ] Multi-package build test (U++ with dependencies)
  - [ ] Cross-build-system test (CMake → Autotools dependency)
  - [ ] Gradle project test (`~/Dev/RainbowGame/trash`)
  - [ ] Error recovery test (--keep-going, --resume)
  - [ ] Build artifact tracking test

**Deliverables**:
- Working maestro command (fix broken imports)
- Canonical package representation with conversion
- Gradle builder implementation
- Build configuration discovery (`maestro repo conf`)
- Complete Phase 7 implementation with all gaps filled
- Comprehensive test suite

**Test Criteria**:
- All maestro commands work without import errors
- Can build Gradle projects
- `maestro repo conf` shows correct build configuration
- Multi-package builds work in dependency order
- Error recovery works (--keep-going, --resume)
- Build artifacts are properly tracked

**Priority**: P0 - BLOCKING
This phase must complete before any other development can continue.

**Estimated Complexity**: High (3-5 weeks total)
- Week 1: Critical blockers (12.1, 12.2)
- Week 2-3: Missing components (12.3, 12.4)
- Week 4-5: Phase 7 gaps (12.5-12.8) + testing

---

## TU/AST Track: Translation Unit and AST Generation

This track implements Translation Unit (TU) and Abstract Syntax Tree (AST) generation for advanced code analysis, auto-completion, and code transformation.

**Reference**: `docs/ast.md`

### Strategic Context

The TU/AST system enables:
1. **Auto-completion**: Context-aware code completion based on visible symbols
2. **Code transformation**: Convert between coding conventions (standard C++ → U++)
3. **Order fixing**: Automatically reorder code to satisfy dependencies
4. **AI-assisted editing**: Provide AST context to AI for better understanding
5. **Build integration**: Share AST between `maestro repo conf`, `maestro build`, and AI workflows

**Key Insight**: Getting AST is very close to building. Both require:
- Finding all source files
- Resolving includes/imports
- Configuring compiler flags
- Processing in correct order

The difference: `maestro make` produces executables, `maestro tu` produces AST.

### Phase TU1: Core AST Infrastructure 📋 **[Planned]**

**Reference**: `docs/ast.md` Phase 1
**Duration**: 3-4 weeks
**Dependencies**: None

**Objective**: Build foundation for parsing and representing ASTs across multiple languages.

#### Tasks

- [ ] **TU1.1: Universal AST Node Representation**
  - [ ] Design language-agnostic AST node structure
  - [ ] Implement `ASTNode` dataclass with location tracking
  - [ ] Implement `SourceLocation` for file/line/column tracking
  - [ ] Implement `Symbol` dataclass for definitions/references

- [ ] **TU1.2: libclang-based C/C++ Parser**
  - [ ] Integrate libclang Python bindings
  - [ ] Implement `ClangParser` class
  - [ ] Convert clang AST to universal AST format
  - [ ] Handle preprocessor directives
  - [ ] Track include dependencies

- [ ] **TU1.3: Java/Kotlin Parser Integration**
  - [ ] Implement `JavaParser` using tree-sitter or JavaParser library
  - [ ] Implement `KotlinParser` using tree-sitter or kotlin-compiler
  - [ ] Support for Gradle projects

- [ ] **TU1.4: AST Serialization**
  - [ ] Design serialization format (JSON/MessagePack/Protobuf)
  - [ ] Implement `ASTSerializer` class
  - [ ] Support round-trip: parse → serialize → deserialize
  - [ ] Optimize for size and speed

**Deliverables**:
- Universal AST node representation
- C/C++ parser using libclang
- Java/Kotlin parsers (initial)
- AST serialization/deserialization

**Test Repository**:
- `~/Dev/RainbowGame/trash` (Gradle multi-module with Java/Kotlin)

**Test Criteria**:
- Parse simple C++ file with classes and functions
- Parse Java file from Gradle project
- Round-trip serialization works correctly
- Extract all symbols from parsed AST

---

### Phase TU2: Incremental TU Builder with File Hashing 📋 **[Planned]**

**Reference**: `docs/ast.md` Phase 2
**Duration**: 3-4 weeks
**Dependencies**: Phase TU1

**Objective**: Build translation units efficiently with incremental compilation tracking.

#### Tasks

- [ ] **TU2.1: File Hash Tracking**
  - [ ] Implement SHA-256-based file change detection
  - [ ] Create `FileHasher` class
  - [ ] Store hashes in `.maestro/tu/cache/file_hashes.json`
  - [ ] Detect changed files efficiently

- [ ] **TU2.2: AST Cache Management**
  - [ ] Create `.maestro/tu/cache/ast/` directory structure
  - [ ] Implement `ASTCache` class
  - [ ] Cache ASTs by file hash
  - [ ] Reuse cached ASTs for unchanged files

- [ ] **TU2.3: Translation Unit Builder**
  - [ ] Create `TUBuilder` class
  - [ ] Parse all source files in package
  - [ ] Build symbol table across files
  - [ ] Resolve cross-file references
  - [ ] Cache complete TU

- [ ] **TU2.4: Dependency Tracking**
  - [ ] Track file dependencies (includes/imports)
  - [ ] Track symbol dependencies
  - [ ] Invalidate cache when dependencies change
  - [ ] Store in `.maestro/tu/cache/ast/<hash>.meta`

**Deliverables**:
- File hash tracking system
- AST cache management
- Translation unit builder
- Dependency tracking
- Incremental rebuild (only re-parse changed files)

**Test Criteria**:
- Build TU for simple package (3-5 files)
- Modify one file, rebuild TU (only that file re-parsed)
- Verify cached ASTs are reused correctly
- Extract correct dependency graph

---

### Phase TU3: Symbol Resolution and Indexing 📋 **[Planned]**

**Reference**: `docs/ast.md` Phase 3
**Duration**: 3-4 weeks
**Dependencies**: Phase TU2

**Objective**: Build symbol table and index for fast queries.

#### Tasks

- [ ] **TU3.1: Symbol Table Construction**
  - [ ] Implement `SymbolTable` class
  - [ ] Support scoped symbol lookup
  - [ ] Handle overloaded symbols
  - [ ] Track symbol visibility (public/private/protected)

- [ ] **TU3.2: Cross-File Symbol Resolution**
  - [ ] Implement `SymbolResolver` class
  - [ ] Resolve symbols across files in TU
  - [ ] Handle forward declarations
  - [ ] Detect unresolved symbols

- [ ] **TU3.3: Symbol Index (SQLite)**
  - [ ] Create `.maestro/tu/analysis/symbols.db`
  - [ ] Implement `SymbolIndex` class
  - [ ] Store symbols in database for fast queries
  - [ ] Index by name, file, location
  - [ ] Support find-references queries

**Deliverables**:
- Symbol table construction
- Cross-file symbol resolution
- SQLite-based symbol index
- Symbol lookup and reference finding

**Test Criteria**:
- Build symbol table for multi-file package
- Lookup symbol definition by name
- Find all references to symbol
- Get visible symbols at cursor position

---

### Phase TU4: Auto-Completion Engine 📋 **[Planned]**

**Reference**: `docs/ast.md` Phase 4
**Duration**: 2-3 weeks
**Dependencies**: Phase TU3

**Objective**: Implement context-aware auto-completion.

#### Tasks

- [ ] **TU4.1: Completion Provider**
  - [ ] Implement `CompletionProvider` class
  - [ ] Provide completions at cursor location
  - [ ] Context-aware filtering (member access, scope resolution)
  - [ ] Support different completion triggers (`.`, `::`, `->`)

- [ ] **TU4.2: LSP Integration**
  - [ ] Implement `MaestroLSPServer` class
  - [ ] Handle `textDocument/completion` requests
  - [ ] Handle `textDocument/definition` (go-to-definition)
  - [ ] Handle `textDocument/references` (find-references)
  - [ ] Support incremental document updates

**Deliverables**:
- Completion provider with context awareness
- LSP server implementation
- Integration with editors (VS Code, Vim, Emacs)

**Test Criteria**:
- Provide completions at various locations
- Complete after `.` (member access)
- Complete after `::` (scope resolution)
- Complete local variables in function

---

### Phase TU5: Integration with Build System and CLI 📋 **[Planned]**

**Reference**: `docs/ast.md` Phase 5
**Duration**: 3-4 weeks
**Dependencies**: Phases TU2-TU4

**Objective**: Integrate TU/AST with existing Maestro workflows.

#### Tasks

- [ ] **TU5.1: Build Configuration Integration**
  - [ ] Reuse build configuration for TU generation
  - [ ] Create `TUConfigBuilder` class
  - [ ] Extract compile context from Gradle
  - [ ] Extract compile context from CMake
  - [ ] Extract compile context from U++

- [ ] **TU5.2: `maestro tu` CLI Implementation**
  - [ ] Implement `maestro tu build [PACKAGE]`
  - [ ] Implement `maestro tu info [PACKAGE]`
  - [ ] Implement `maestro tu query [PACKAGE]`
  - [ ] Implement `maestro tu complete [PACKAGE]`
  - [ ] Implement `maestro tu references [PACKAGE]`
  - [ ] Implement `maestro tu lsp`
  - [ ] Implement `maestro tu cache` commands

- [ ] **TU5.3: Integration with `maestro repo conf`**
  - [ ] Share configuration between TU and build
  - [ ] Store config in `.maestro/tu/config/<package>.json`

- [ ] **TU5.4: Integration with `maestro build` (AI workflow)**
  - [ ] Provide AST context to AI for build fixing
  - [ ] Include visible symbols in error context
  - [ ] Include AST structure around error location

**Deliverables**:
- `maestro tu` CLI with all subcommands
- Integration with build configuration
- Integration with AI build fixing workflow
- Documentation and examples

**Test Repository**:
- `~/Dev/RainbowGame/trash` (Gradle project)

**Test Criteria**:
- `maestro tu build` works for Gradle project
- `maestro tu complete` provides correct completions
- `maestro tu query` finds symbols
- `maestro tu lsp` works with VS Code

---

### Phase TU6: Code Transformation and Convention Enforcement 📋 **[Planned]**

**Reference**: `docs/ast.md` Phase 6
**Duration**: 3-4 weeks
**Dependencies**: Phases TU3-TU5

**Objective**: Implement code transformation and U++ convention enforcement.

#### Tasks

- [ ] **TU6.1: AST Transformation Framework**
  - [ ] Implement `ASTTransformer` base class
  - [ ] Support pluggable transformations
  - [ ] Preserve source locations during transformation

- [ ] **TU6.2: U++ Convention Enforcer**
  - [ ] Implement `UppConventionTransformer`
  - [ ] Build dependency graph from AST
  - [ ] Compute correct declaration order (topological sort)
  - [ ] Generate primary header with declarations in order
  - [ ] Update .cpp files to include only primary header
  - [ ] Add forward declarations where needed

- [ ] **TU6.3: Code Generation from AST**
  - [ ] Implement `CodeGenerator` class
  - [ ] Generate C++ code from AST
  - [ ] Generate Java code from AST
  - [ ] Preserve formatting and comments (optional)

**Deliverables**:
- AST transformation framework
- U++ convention enforcer
- Code generator from AST
- CLI: `maestro tu transform --to-upp PACKAGE`

**Test Criteria**:
- Transform simple C++ project to U++ conventions
- Verify generated code compiles
- Verify declaration order is correct
- Verify forward declarations added where needed

---

## Phase AS1 — Assemblies in Maestro Repository System

**Objective**: Organize packages into logical assemblies that represent cohesive units of code, rather than treating every directory as a potential package.

### Tasks

- [ ] **AS1.1: Assembly Concept Implementation**
  - [ ] Create `maestro repo asm` command group
  - [ ] Implement `maestro repo asm list` - List all assemblies in repository
  - [ ] Implement `maestro repo asm help` - Show help for assembly commands
  - [ ] Implement `maestro repo asm <asm>` - Operations on specific assembly
  - [ ] Add additional assembly-specific operations

- [ ] **AS1.2: Assembly Type Classification**
  - [ ] Implement U++ type assemblies: Have U++ package directories and are NOT package directories
  - [ ] Implement Programming language assemblies: For specific languages (Python, Java, etc.)
  - [ ] Implement Misc-type assembly: For other packages that don't fit specific language patterns
  - [ ] Plan Documentation-type assembly: (Future support) For documentation projects

- [ ] **AS1.3: Assembly Detection & Classification**
  - [ ] Implement U++ assembly detection: Detected by presence of multiple `.upp` files or structured package organization
  - [ ] Implement Python assembly detection: Detected by presence of setup.py files in subdirectories
  - [ ] Implement Java assembly detection: Detected by maven/gradle project structure
  - [ ] Implement other language assembly detection: Based on specific build files and directory structure

- [ ] **AS1.4: Assembly Examples Implementation**
  - [ ] Support Python assembly structure (directories with sub-directories containing setup.py)
  - [ ] Support Java assembly structure (e.g., `~/Dev/TopGuitar/desktop/`, `~/Dev/TopGuitar/common/`)
  - [ ] Handle multi-type assembly handling correctly

- [ ] **AS1.5: Multi-type Assembly Handling**
  - [ ] Ensure Gradle assembly correctly handles packages like `~/Dev/RainbowGame/trash/` (packages: desktop, core, ...)
  - [ ] Ensure U++ assembly correctly handles `~/Dev/RainbowGame/trash/uppsrc`
  - [ ] Implement proper system to apply appropriate build systems to appropriate assemblies
  - [ ] Handle dependencies between different assembly types correctly
  - [ ] Provide focused tooling for each assembly type

## Extended Track: Additional Build Systems

This track extends repository scanning and build support to additional ecosystems.

### Phase E1: Python Project Support 📋 **[Planned]**

**Duration**: 2-3 weeks
**Dependencies**: Phase 1 (Core Builder)

**Objective**: Support Python projects with pip, setuptools, poetry, etc.

#### Tasks

- [ ] **E1.1: Python Package Scanner**
  - [ ] Create `scan_python_packages()` in `build_systems.py`
  - [ ] Detect `setup.py`, `setup.cfg`, `pyproject.toml`
  - [ ] Parse package metadata
  - [ ] Extract dependencies from:
    - `setup.py` (`install_requires`)
    - `requirements.txt`
    - `pyproject.toml` (`dependencies`)
    - `Pipfile`, `poetry.lock`

- [ ] **E1.2: Python Builder**
  - [ ] Create `python.py` builder module
  - [ ] Support pip install modes
  - [ ] Support setuptools/distutils build
  - [ ] Support poetry build
  - [ ] Support wheel creation

- [ ] **E1.3: Virtual Environment Integration**
  - [ ] Detect existing venv
  - [ ] Create venv if needed
  - [ ] Activate venv during build
  - [ ] Support multiple Python versions

**Test Repository**:
- `~/Dev/Maestro` (itself!)

**Deliverables**:
- Python package scanner
- Python builder
- Virtual environment support

**Test Criteria**:
- Maestro can scan itself
- Python packages build successfully
- Dependencies resolve correctly

---

### Phase E2: Node.js / npm Project Support 📋 **[Planned]**

**Duration**: 2-3 weeks
**Dependencies**: Phase 1 (Core Builder)

**Objective**: Support Node.js projects with npm, yarn, pnpm.

#### Tasks

- [ ] **E2.1: Node.js Package Scanner**
  - [ ] Create `scan_nodejs_packages()` in `build_systems.py`
  - [ ] Detect `package.json`
  - [ ] Parse package metadata
  - [ ] Extract dependencies (`dependencies`, `devDependencies`)
  - [ ] Support workspaces / monorepo structure
  - [ ] Handle `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`

- [ ] **E2.2: Node.js Builder**
  - [ ] Create `nodejs.py` builder module
  - [ ] Support npm build scripts
  - [ ] Support yarn commands
  - [ ] Support pnpm commands
  - [ ] Implement `npm install` / `npm ci`
  - [ ] Implement `npm run build`
  - [ ] Support custom scripts

- [ ] **E2.3: TypeScript Support**
  - [ ] Detect `tsconfig.json`
  - [ ] Support TypeScript compilation (`tsc`)
  - [ ] Integration with build tools (webpack, vite, etc.)

**Test Repository**:
- `~/Dev/AgentManager` (npm monorepo)

**Deliverables**:
- Node.js package scanner
- npm/yarn/pnpm builder
- TypeScript support

**Test Criteria**:
- AgentManager scans successfully
- Monorepo structure detected
- Build scripts execute correctly

---

### Phase E3: Go Project Support 📋 **[Planned]**

**Duration**: 2-3 weeks
**Dependencies**: Phase 1 (Core Builder)

**Objective**: Support Go projects with go modules.

#### Tasks

- [ ] **E3.1: Go Package Scanner**
  - [ ] Create `scan_go_packages()` in `build_systems.py`
  - [ ] Detect `go.mod`, `go.sum`
  - [ ] Parse module path and dependencies
  - [ ] Scan Go source files (`.go`)
  - [ ] Detect package structure
  - [ ] Handle nested modules

- [ ] **E3.2: Go Builder**
  - [ ] Create `go.py` builder module
  - [ ] Implement `go build`
  - [ ] Implement `go install`
  - [ ] Implement `go test`
  - [ ] Support build tags
  - [ ] Support cross-compilation (GOOS, GOARCH)

- [ ] **E3.3: Go Module Management**
  - [ ] Implement `go mod download`
  - [ ] Handle replace directives
  - [ ] Support vendor directory

**Test Repository**:
- `~/Dev/BruceKeith/src/NeverScript/` (Go compiler)

**Deliverables**:
- Go package scanner
- Go builder
- Module management

**Test Criteria**:
- NeverScript scans successfully
- Go modules resolve
- Cross-compilation works

---

### Phase E4: Pedigree pup Package System Support 📋 **[Planned]**

**Duration**: 2-3 weeks
**Dependencies**: Phase 1 (Core Builder)

**Objective**: Support Pedigree pup package system, which is similar to Portage/ebuilds.

#### Background

Pedigree pup is a Python-based package system used by the Pedigree OS project. Each package is defined by a `package.py` file that:
- Inherits from `buildsystem.Package` base class
- Defines build phases: `download()`, `prebuild()`, `configure()`, `build()`, `deploy()`
- Specifies dependencies via `build_requires()` and `install_deps()`
- Supports patches and custom build steps

**Key Similarities to Portage**:
- Package-based dependency management
- Build phases (similar to ebuild functions)
- Patch application
- Build-time and runtime dependencies
- Deploy to staging directory before packaging

**Key Differences from Portage**:
- Python classes instead of bash scripts
- No USE flags (simpler configuration model)
- Cross-compilation focused (for Pedigree OS)
- Uses chroot for builds

#### Tasks

- [ ] **E4.1: pup Package Scanner**
  - [ ] Create `scan_pup_packages()` in `build_systems.py`
  - [ ] Detect `packages/*/package.py` files
  - [ ] Parse Python package definitions
  - [ ] Extract metadata:
    - `name()`, `version()`
    - `build_requires()`, `install_deps()`
    - `patches()`
  - [ ] Build dependency graph

- [ ] **E4.2: pup Builder**
  - [ ] Create `pup.py` builder module
  - [ ] Implement Python class instantiation
  - [ ] Execute build phases in order:
    1. `download()` - fetch source
    2. `patch()` - apply patches
    3. `prebuild()` - prepare build
    4. `configure()` - run configure
    5. `build()` - compile
    6. `deploy()` - install to staging
    7. `postdeploy()` - post-install steps
  - [ ] Support environment variables (`env` dict)
  - [ ] Support custom srcdir and deploydir

- [ ] **E4.3: pup Infrastructure Integration**
  - [ ] Use existing `support/buildsystem.py` base class
  - [ ] Use existing `support/steps.py` helper functions
  - [ ] Integration with Maestro's dependency resolution
  - [ ] Cross-compilation environment setup

**Test Repository**:
- `~/Dev/pedigree-apps` (pup package system)
- Test packages: bash, gcc, coreutils, etc.

**Deliverables**:
- pup package scanner
- pup builder
- Integration with pedigree-apps infrastructure

**Test Criteria**:
- Scan pedigree-apps packages successfully
- Build simple packages (bash, coreutils)
- Dependency resolution works
- Build phases execute in correct order

**Note**: This provides excellent preparation for Portage integration (Phase A2-A6), as pup shares similar concepts but is simpler to implement.

---

### Phase E5: Additional Build Systems (Future) 💡 **[Proposed]**

**Duration**: TBD
**Dependencies**: Phase 1 (Core Builder)

**Objective**: Support additional build systems as needed.

#### Potential Systems

- [ ] **Bazel Support**
- [ ] **Meson Support**
- [ ] **Gradle Support** (Java/Android)
- [ ] **Cargo Support** (Rust)
- [ ] **NuGet / MSBuild** (Extended .NET)

---

## Advanced Track: External Dependencies and Portage Integration

This track handles external dependencies, build scripts, and Gentoo Portage integration.

### Strategic Vision: Maestro as Universal Package Manager

**Core Principle**: Maestro must have a **base virtual class that can run ALL package management systems**:

1. **Portage** - Gentoo's powerful package manager (USE flags, shared libraries, binary packages)
2. **pup** - Pedigree's Python-based package system (simpler, cross-compilation focused)
3. **umk-fork** - Maestro's enhanced version of U++ umk (multi-config builds, static linking)
4. **Maestro Native** - Our own future package manager (best of all worlds)

**Why This Matters**:
- **No Lock-in**: Users can use any package system they prefer
- **Interoperability**: Mix packages from different systems (umk + Portage + pup)
- **Future-proof**: Easy to add new package managers
- **Learning Path**: Start simple (pup), progress to complex (Portage)
- **Competition**: Maestro Native can eventually compete with/replace Portage

**Design Philosophy**:
- **Maximum flexibility** in the base class - no assumptions about paradigms
- **Feature detection** via `supports_feature()` - query capabilities at runtime
- **Optional configuration** - `config` can be USE flags, build configs, or None
- **Zero duplicate code** - common logic in base, specifics in implementations
- **Extensibility first** - adding new systems should be trivial

**Implementation Strategy**:
1. Design base class abstractly (Phase A2.1) - **most critical step**
2. Implement simplest system first (pup - Phase E4) - validate design
3. Implement complex system (Portage - Phase A3) - stress test design
4. Implement multi-config system (umk - Phase 2) - different paradigm
5. Design native system (Maestro Native - Phase A5/future) - synthesis

**Portage Fork Strategy**:
Portage may not expose sufficient modularity for our needs. We should be prepared to:
- **Fork Gentoo Portage** if necessary to expose the APIs we need
- Fork would be maintained in a **separate repository** (not inside Maestro)
- After forking, the **Maestro repository would reference the fork as a git submodule**
- Fork would be at: `deps/portage/` (git submodule → our Portage fork)
- Upstream: `https://github.com/gentoo/portage` (original)
- Our fork: `https://github.com/sblo/portage` (hypothetical - with Maestro integration hooks)

**Benefits of Forking**:
- Full control over internal APIs
- Can add hooks for Maestro integration
- Can extend USE flag system if needed
- Can enhance multi-config support
- Can improve Python API surface

**Maintenance Strategy**:
- Keep fork in sync with upstream Gentoo Portage
- Contribute improvements back upstream when possible
- Document all Maestro-specific changes
- Use feature flags to toggle Maestro enhancements

This base class is **THE foundation** upon which all package management in Maestro is built.

### Phase A1: Git Submodule and Build Script Handling 💡 **[Proposed]**

**Duration**: 3-4 weeks
**Dependencies**: Phases 1-7 (Universal Build System)

**Objective**: Treat git submodules and build scripts as requirements to be managed uniformly.

#### Concept

Git submodules and custom build scripts are both external dependencies that must be handled practically. They represent similar challenges: fetching, building, and integrating external code.

#### Tasks

- [ ] **A1.1: Git Submodule Detection**
  - [ ] Detect `.gitmodules` file
  - [ ] Parse submodule configuration
  - [ ] Extract submodule URLs, paths, branches
  - [ ] Detect nested submodules

- [ ] **A1.2: Submodule Management**
  - [ ] Implement `git submodule init`
  - [ ] Implement `git submodule update`
  - [ ] Handle submodule recursive updates
  - [ ] Detect submodule build system
  - [ ] Integrate with `maestro repo resolve`

- [ ] **A1.3: Build Script Recognition**
  - [ ] Detect custom build scripts (`.sh`, `.py`, etc.)
  - [ ] Parse build script metadata (if available)
  - [ ] Create `BuildScript` package type
  - [ ] Integrate build scripts into dependency graph

- [ ] **A1.4: Unified External Dependency Model**
  - [ ] Abstract interface for external dependencies
  - [ ] Common operations: fetch, update, build, install
  - [ ] Integration with dependency resolution

**Deliverables**:
- Submodule support in `maestro repo resolve`
- Build script integration
- Unified external dependency handling

**Test Criteria**:
- Projects with submodules scan correctly
- Submodules can be built
- Build scripts integrate into workflow

---

### Phase A2: Gentoo Portage Integration - Design 💡 **[Proposed]**

**Duration**: 4-6 weeks (design phase)
**Dependencies**: Phase A1, Phase E4 (pup support recommended)

**Objective**: Design integration with Gentoo Portage as a subsystem for package management.

**Recommendation**: Implement Phase E4 (pup support) first, as it provides a simpler but similar package system to learn from before tackling Portage's complexity.

#### Concept

We want to use Gentoo Portage as a subsystem, integrating `emerge` functionality into Maestro. This requires finding a common superset between umk packages, ebuilds, and pup packages.

#### Key Design Challenges

1. **Common Interface**: umk, Portage, and pup have overlapping but not identical concepts
   - **USE flags**:
     - umk: Custom flags (GUI, MT, DEBUG) with multi-config builds
     - Portage: USE flags for conditional dependencies (one config per package)
     - pup: No USE flags (simpler model)
   - **Linking strategy**:
     - umk: Focuses on static linking, weak shared library support
     - Portage: Excels at shared libraries with SONAME tracking
     - pup: Cross-compilation focused, deploys to staging
   - **Build phases**:
     - umk: Workspace scan → compile → link
     - Portage: src_unpack → src_prepare → src_configure → src_compile → src_install
     - pup: download → patch → prebuild → configure → build → deploy
   - **Package format**:
     - umk: .upp files (custom format)
     - Portage: .ebuild files (bash scripts)
     - pup: package.py (Python classes)

2. **Virtual Base Class Design** (Critical Architecture Decision):

   **We must have a base virtual class that can run ALL package management systems**:
   - **Portage** (Gentoo's package manager)
   - **pup** (Pedigree's package manager)
   - **umk-fork** (Maestro's fork/extension of U++ umk)
   - **Maestro native** (possibly our own competitor to Portage)

   This base class is the **foundation of Maestro's universal package management**.

   ```python
   # Base virtual interface - the universal package manager abstraction
   # This must be flexible enough to support ALL package management paradigms

   class PackageManager(ABC):
       """Universal package manager interface.

       This base class must support:
       - Simple systems (pup - no USE flags)
       - Complex systems (Portage - USE flags, ebuilds)
       - Multi-config systems (umk - multiple build configurations)
       - Future systems (Maestro's own package manager)
       """

       @abstractmethod
       def scan_packages(self, repository_path):
           """Scan repository for packages and metadata."""
           pass

       @abstractmethod
       def resolve_dependencies(self, package, config=None):
           """Resolve package dependencies.

           Args:
               package: Package to resolve dependencies for
               config: Optional configuration (USE flags, build config, etc.)

           Returns:
               Dependency graph with resolved packages
           """
           pass

       @abstractmethod
       def build_package(self, package, config=None):
           """Build package with specific configuration.

           Args:
               package: Package to build
               config: Optional build configuration

           Returns:
               Build result with artifacts
           """
           pass

       @abstractmethod
       def install_package(self, package, destination):
           """Install built package to destination."""
           pass

       @abstractmethod
       def get_package_metadata(self, package):
           """Get package metadata (name, version, dependencies, etc.)."""
           pass

       @abstractmethod
       def supports_feature(self, feature):
           """Check if this package manager supports a feature.

           Features: 'use_flags', 'multi_config', 'binary_packages',
                    'shared_libraries', 'cross_compile', etc.
           """
           pass

   # Concrete implementations

   class PortageManager(PackageManager):
       """Gentoo Portage implementation.

       Features:
       - USE flags for conditional dependencies
       - ebuild format (bash scripts)
       - Single configuration per package
       - Excellent shared library support (SONAME tracking)
       - Binary package support (binpkgs)
       """
       def supports_feature(self, feature):
           return feature in ['use_flags', 'binary_packages', 'shared_libraries']

   class PupManager(PackageManager):
       """Pedigree pup implementation.

       Features:
       - Python package definitions
       - Build phases (download, patch, configure, build, deploy)
       - No USE flags (simpler model)
       - Cross-compilation focused
       """
       def supports_feature(self, feature):
           return feature in ['cross_compile']

   class UmkManager(PackageManager):
       """U++ package manager implementation (Maestro fork).

       Features:
       - .upp package format
       - Multi-configuration builds (multiple USE flag combinations)
       - Static linking focused
       - Blitz builds (unity builds)
       """
       def supports_feature(self, feature):
           return feature in ['multi_config', 'blitz_build']

   class MaestroNativeManager(PackageManager):
       """Maestro's native package manager (future).

       This is our potential competitor to Portage, combining:
       - Best of Portage: USE flags, shared library support
       - Best of umk: Multi-configuration builds
       - Best of pup: Python-based simplicity
       - New features: Better cross-compilation, modern tooling
       """
       def supports_feature(self, feature):
           return feature in ['use_flags', 'multi_config', 'shared_libraries',
                             'binary_packages', 'cross_compile', 'blitz_build']
   ```

   **Design Principles**:
   1. **Maximum Flexibility**: Base class must not assume any specific paradigm
   2. **Feature Detection**: Use `supports_feature()` to query capabilities
   3. **Optional Configuration**: `config` parameter can be USE flags, build configs, or None
   4. **Extensibility**: Easy to add new package managers without breaking existing ones
   5. **No Duplicate Code**: Common functionality in base class, specifics in implementations

3. **USE Flag Compatibility**:
   - Portage: One USE flag combination per package
   - umk: Can build multiple USE flag combinations simultaneously
   - **Design decision**: Support superset of both

4. **Shared Library Handling**:
   - Portage: Excellent shared library support (SONAME, dependencies)
   - umk: Weak shared library support, focuses on static linking
   - **Design decision**: Enhance umk with Portage-like shared library tracking

#### Tasks

- [ ] **A2.1: Base Class Design** (CRITICAL FIRST STEP)
  - [ ] Design universal `PackageManager` base class
    - Must support ALL four systems: Portage, pup, umk, Maestro-native
    - Must be flexible enough for future package managers
    - Must not favor any single paradigm
  - [ ] Define core interface methods:
    - `scan_packages()` - universal package discovery
    - `resolve_dependencies()` - with optional config (USE flags, etc.)
    - `build_package()` - with optional config
    - `install_package()` - to staging/final destination
    - `get_package_metadata()` - name, version, deps, etc.
    - `supports_feature()` - capability detection
  - [ ] Define feature flags:
    - `use_flags` - Portage-style USE flags
    - `multi_config` - umk-style multiple configurations
    - `binary_packages` - pre-built package support
    - `shared_libraries` - SONAME tracking
    - `cross_compile` - cross-compilation support
    - `blitz_build` - unity/blitz builds
  - [ ] Document design rationale and trade-offs

- [ ] **A2.2: Architecture Research**
  - [ ] Study Portage architecture: https://github.com/gentoo/portage
  - [ ] Study pup architecture: `~/Dev/pedigree-apps/support/`
  - [ ] Study umk architecture: `~/upp/uppsrc/umk/`
  - [ ] Identify key Portage components:
    - Package dependency resolution (emerge)
    - ebuild parsing and execution
    - USE flag system
    - Shared library tracking (NEEDED.ELF.2)
    - Binary package support (binpkgs)
  - [ ] Map Portage concepts to Maestro base class
  - [ ] Map pup concepts to Maestro base class
  - [ ] Map umk concepts to Maestro base class
  - [ ] Identify commonalities and differences

- [ ] **A2.3: USE Flag System Design**
  - [ ] Support Portage USE flags
  - [ ] Support umk flags (GUI, MT, etc.)
  - [ ] Design flag inheritance
  - [ ] Design conditional dependencies

- [ ] **A2.4: Multi-Configuration Support**
  - [ ] Design how to handle umk's multi-config builds
  - [ ] Design how to extend Portage beyond single-config
  - [ ] Design configuration selection interface

- [ ] **A2.5: Shared Library Enhancement**
  - [ ] Design shared library tracking for umk
  - [ ] Design SONAME handling
  - [ ] Design dependency tracking
  - [ ] Integration with Portage's shared library system

**Deliverables**:
- Architecture document for Portage integration
- Common interface specification
- USE flag system design
- Multi-configuration design

**Test Criteria**:
- Design covers both Portage and umk use cases
- Interface is extensible
- USE flags are compatible

---

### Phase A3: Portage Integration - Implementation 💡 **[Proposed]**

**Duration**: 6-8 weeks
**Dependencies**: Phase A2

**Objective**: Implement Portage integration into Maestro.

#### Tasks

- [ ] **A3.1: Portage Modularity Assessment**
  - [ ] Study Portage Python API: `https://github.com/gentoo/portage`
  - [ ] Evaluate API surface for Maestro integration:
    - Dependency resolution APIs
    - ebuild parsing and execution hooks
    - USE flag manipulation
    - Package metadata access
    - Install/uninstall hooks
  - [ ] Identify gaps in modularity:
    - What APIs are missing?
    - What internal functions need to be exposed?
    - What hooks are needed for Maestro integration?
  - [ ] **Decision point**: Use upstream Portage vs. fork
    - If APIs are sufficient → use upstream as-is
    - If APIs are insufficient → proceed with fork strategy

- [ ] **A3.2: Portage Fork (if needed)**
  - [ ] Create Portage fork in separate repository
  - [ ] Add Maestro integration hooks:
    - Package manager interface compatibility
    - Enhanced Python API
    - Multi-config support hooks (if extending USE flags)
  - [ ] Document all changes from upstream
  - [ ] Set up sync strategy with upstream
  - [ ] Add as git submodule: `deps/portage/`

- [ ] **A3.3: Portage Python API Integration**
  - [ ] Create `maestro/package_managers/portage.py` module
  - [ ] Implement `PortageManager(PackageManager)` class
  - [ ] Wrap Portage API calls
  - [ ] Handle Portage configuration
  - [ ] Integrate with Maestro's universal base class

- [ ] **A3.4: Ebuild Support**
  - [ ] Parse ebuild files
  - [ ] Extract metadata (DEPEND, RDEPEND, BDEPEND)
  - [ ] Extract USE flags
  - [ ] Map to Maestro package format

- [ ] **A3.5: emerge Integration**
  - [ ] Implement `maestro emerge` command
  - [ ] Integrate with dependency resolution
  - [ ] Support Portage features:
    - `--ask`, `--pretend`, `--verbose`
    - `--update`, `--deep`
    - `--newuse`, `--changed-use`

- [ ] **A3.6: USE Flag Integration**
  - [ ] Implement USE flag parsing
  - [ ] Support USE flag selection
  - [ ] Conditional dependency resolution

- [ ] **A3.7: Build Integration**
  - [ ] Call emerge for ebuild packages
  - [ ] Integrate with Maestro build system
  - [ ] Handle mixed builds (ebuilds + umk + cmake)

**Deliverables**:
- Portage integration module
- `maestro emerge` command
- ebuild support
- Mixed build support

**Test Criteria**:
- Can build Gentoo packages
- USE flags work correctly
- Integration with other build systems works

---

### Phase A4: Host System Package Recognition 💡 **[Proposed]**

**Duration**: 3-4 weeks
**Dependencies**: Phase A3

**Objective**: Recognize and integrate host system packages into Maestro's dependency model.

#### Concept

External dependencies may already be installed on the host system (via Portage, apt, pacman, etc.). We want to:
1. Recognize installed packages
2. Treat them as "installed ebuilds" with USE flags
3. Avoid rebuilding if satisfied
4. Handle version and USE flag compatibility

#### Key Challenges

1. **USE Flag Detection**: Installed packages have USE flags, but detecting them is hard
2. **Multiple Package Managers**: Support Portage, apt, pacman, etc.
3. **Version Compatibility**: Ensure installed version satisfies requirements
4. **Flexibility**: The superset must handle this early in design

#### Tasks

- [ ] **A4.1: Package Manager Detection**
  - [ ] Detect host package manager (Portage, apt, pacman, etc.)
  - [ ] Query installed packages
  - [ ] Extract package metadata

- [ ] **A4.2: Portage Package Query**
  - [ ] Query installed ebuilds
  - [ ] Extract USE flags from installed packages
  - [ ] Extract version information
  - [ ] Extract dependencies

- [ ] **A4.3: Generic Package Query (Non-Portage)**
  - [ ] Support apt (dpkg-query)
  - [ ] Support pacman
  - [ ] Support rpm/yum/dnf
  - [ ] Map to common format

- [ ] **A4.4: Integration with Dependency Resolution**
  - [ ] Check host packages before building
  - [ ] Version compatibility checking
  - [ ] USE flag compatibility checking (for Portage)
  - [ ] Prefer host packages when satisfied

- [ ] **A4.5: Fallback Strategy**
  - [ ] If host package doesn't satisfy requirements, build from source
  - [ ] Document limitations and workarounds

**Deliverables**:
- Host package recognition
- Multi-package-manager support
- Integration with dependency resolution

**Test Criteria**:
- Detects installed packages correctly
- Avoids unnecessary rebuilds
- Falls back to source builds when needed

---

### Phase A5: Portage Superset Integration 💡 **[Proposed]**

**Duration**: 4-6 weeks
**Dependencies**: Phases A2-A4

**Objective**: Create the glue code for the common superset of umk and Portage.

#### Concept

This phase creates the "integration glue" that handles:
1. Packages that can be built with either umk or Portage
2. Packages that use umk but depend on Portage packages
3. Packages that use Portage but depend on umk packages
4. Mixed USE flag environments

#### Key Design Principle

The superset must be flexible from the start. It needs to:
- Handle umk's multi-configuration builds
- Handle Portage's single-configuration builds
- Support shared libraries better than umk does natively
- Support static linking better than Portage does natively
- Recognize host system packages with their USE flags
- Allow building from source when host packages don't satisfy

#### Tasks

- [ ] **A5.1: Unified Package Model**
  - [ ] Create `UnifiedPackage` that represents both umk and ebuild packages
  - [ ] Common metadata format
  - [ ] Common dependency format
  - [ ] Common USE flag format

- [ ] **A5.2: Cross-Build-System Dependencies**
  - [ ] umk package depending on Portage package
  - [ ] Portage package depending on umk package
  - [ ] Mixed dependency chains

- [ ] **A5.3: USE Flag Unification**
  - [ ] Map umk flags to Portage USE flags
  - [ ] Map Portage USE flags to umk flags
  - [ ] Handle flag conflicts

- [ ] **A5.4: Library Linking Integration**
  - [ ] Link umk packages against Portage-installed shared libraries
  - [ ] Link Portage packages against umk-built static libraries
  - [ ] Handle SONAME and library versioning

- [ ] **A5.5: Multi-Configuration Support**
  - [ ] Extend Portage to support multiple configurations (if needed)
  - [ ] Build umk packages with multiple USE flag combinations
  - [ ] Installation and package management for multi-config builds

**Deliverables**:
- Unified package model
- Cross-build-system dependency support
- USE flag unification
- Multi-configuration support

**Test Criteria**:
- Can build mixed projects (umk + Portage)
- Dependencies resolve correctly
- USE flags work across systems
- Multi-configuration builds work

---

### Phase A6: External Dependency Workflow 💡 **[Proposed]**

**Duration**: 2-3 weeks
**Dependencies**: Phase A5

**Objective**: Complete workflow for external dependencies including submodules, build scripts, and Portage packages.

#### Tasks

- [ ] **A6.1: Unified External Dependency Model**
  - [ ] Abstract `ExternalDependency` interface
  - [ ] Implementations:
    - `GitSubmodule`
    - `BuildScript`
    - `PortagePackage`
    - `HostPackage`

- [ ] **A6.2: Dependency Resolution Strategy**
  - [ ] Check host system packages first
  - [ ] Check locally built packages
  - [ ] Check Portage
  - [ ] Check hub repositories
  - [ ] Fall back to building from source

- [ ] **A6.3: CLI Integration**
  - [ ] `maestro external list` - List external dependencies
  - [ ] `maestro external install` - Install external dependency
  - [ ] `maestro external update` - Update external dependencies
  - [ ] `maestro external info` - Show dependency info

- [ ] **A6.4: Workflow Documentation**
  - [ ] Document external dependency handling
  - [ ] Document Portage integration workflow
  - [ ] Document USE flag handling
  - [ ] Document multi-configuration builds

**Deliverables**:
- Complete external dependency workflow
- CLI commands
- Documentation

**Test Criteria**:
- External dependencies resolve correctly
- Workflow is intuitive
- Documentation is clear

---

## Integration and Testing

### Integration Test Plan

**Test Repositories Matrix**:

| Repository | Build Systems | Focus Area |
|------------|---------------|------------|
| `~/Dev/ai-upp` | U++ | U++ builder, workspace resolution |
| `~/Dev/TopGuitar` | Maven, U++ | Maven multi-module, mixed builds |
| `~/Dev/StuntCarStadium` | Unity, Visual Studio, CMake | MSBuild, multi-system |
| `~/Dev/Maestro` | Python (setuptools) | Python builder |
| `~/Dev/AgentManager` | npm (monorepo) | Node.js builder, workspaces |
| `~/Dev/BruceKeith/src/NeverScript` | Go modules | Go builder |
| `~/Dev/pedigree` | CMake | CMake builder, complex OS project |
| `~/Dev/pedigree-apps` | pup (Python packages) | pup builder, Portage-like system |

### Test Workflows

1. **Basic Build Test**:
   ```bash
   cd <repository>
   maestro repo resolve
   maestro make build
   ```

2. **Clean Build Test**:
   ```bash
   maestro make clean
   maestro make build
   ```

3. **Incremental Build Test**:
   ```bash
   # Modify source file
   maestro make build
   # Should rebuild only affected files
   ```

4. **Parallel Build Test**:
   ```bash
   maestro make build --jobs 8
   ```

5. **Mixed Build System Test**:
   ```bash
   cd ~/Dev/TopGuitar
   maestro make build  # Should build both Maven and U++ packages
   ```

6. **Hub Integration Test**:
   ```bash
   # Project with missing dependency
   maestro make build
   # Should prompt to install from hub
   ```

7. **External Dependency Test**:
   ```bash
   # Project with git submodules
   maestro make build
   # Should initialize and build submodules
   ```

### Continuous Testing Tasks

- [ ] **IT1.1: CI/CD Pipeline Setup**
  - [ ] Set up CI/CD pipeline
  - [ ] Configure automated testing
  - [ ] Set up build triggers

- [ ] **IT1.2: Multi-Platform Testing**
  - [ ] Test on Linux platforms
  - [ ] Test on Windows platforms
  - [ ] Test on macOS platforms
  - [ ] Test with different compiler versions

- [ ] **IT1.3: Regression Testing**
  - [ ] Implement regression testing for each phase
  - [ ] Automate test execution
  - [ ] Set up test reporting

## Phase IT2 — Notes and Considerations

### Tasks

- [ ] **IT2.1: Build Artifact Storage Implementation**
  - [ ] Implement storage of build artifacts in `.maestro/build/` directory
  - [ ] Create method-specific subdirectories (`.maestro/build/<method>/`)
  - [ ] Create package-specific directories (`.maestro/build/<method>/<package>/`)
  - [ ] Implement object file storage (`.maestro/build/<method>/<package>/obj/`)
  - [ ] Implement precompiled headers storage (`.maestro/build/<method>/<package>/pch/`)
  - [ ] Implement dependency tracking file storage (`.maestro/build/<method>/<package>/deps/`)
  - [ ] Implement cache directory structure (`.maestro/build/cache/`)

- [ ] **IT2.2: Dependency Tracking Implementation**
  - [ ] Implement two-level dependency system (package-level and file-level)
  - [ ] Support package-level dependencies using `maestro repo pkg tree`
  - [ ] Implement file-level dependency tracking for header/source dependencies
  - [ ] Store file-level dependencies in `.maestro/build/cache/deps/<package>.json`

- [ ] **IT2.3: Portage Integration Strategy Implementation**
  - [ ] Ensure Phase A2 (Design) gets architecture right before implementation
  - [ ] Start with minimal viable interface and expand as needed
  - [ ] Test with real ebuilds early to validate design decisions
  - [ ] Document limitations honestly
  - [ ] Focus on flexibility to ensure superset can handle future requirements

- [ ] **IT2.4: USE Flag System Implementation**
  - [ ] Support Portage-style USE flags (feature flags)
  - [ ] Support umk-style flags (GUI, MT, DEBUG)
  - [ ] Support multi-configuration builds (umk)
  - [ ] Support single-configuration builds (Portage)
  - [ ] Allow host package USE flag recognition

- [ ] **IT2.5: Development Priorities and Scheduling**
  - [ ] Prioritize Phases 1-7 (Core functionality - Universal Build System) as highest priority
  - [ ] Prioritize Phases TU1-TU6 (TU/AST system) as high priority
  - [ ] Implement TU1-TU3 (Core parsing and symbol resolution) for AI workflows MVP
  - [ ] Implement TU4-TU6 (Auto-completion and transformation) for enhanced IDE features
  - [ ] Prioritize Phase 10 (Hub system) as high priority
  - [ ] Prioritize Phases E1-E4 (Extended build systems) as medium priority
  - [ ] Prioritize Phase 8 (Advanced features) as medium priority
  - [ ] Prioritize Phase 9 (TUI integration) as medium priority
  - [ ] Handle Phases A1-A6 (Portage integration) as Research & Design Phase (requires E4 knowledge)

- [ ] **IT2.6: Learning Progression Setup**
  - [ ] Implement pup support (Phase E4) first: simpler Python-based package system, no USE flags
  - [ ] Progress to Portage (Phases A2-A6): Complex bash-based system with USE flags
  - [ ] Ensure pup provides similar concepts (build phases, dependencies, patches) without Portage's complexity

- [ ] **IT2.7: Parallel Development Tracking**
  - [ ] Support parallel development of UMK Integration and TU/AST
  - [ ] Ensure both use repository scanning (`maestro repo resolve`)
  - [ ] Ensure both need build configuration (`maestro repo conf`)
  - [ ] Ensure TU/AST provides context to AI for `maestro build` workflows

- [ ] **IT2.8: Timeline and Milestone Planning**
  - [ ] Plan Core Universal Build System (Phases 1-7): 17-25 weeks (~4-6 months)
  - [ ] Plan TU/AST System (Phases TU1-TU6): 17-23 weeks (~4-6 months)
  - [ ] Plan TU/AST MVP (TU1-TU3): 9-12 weeks (~2-3 months)
  - [ ] Plan Extended TU/AST (TU4-TU6): 8-11 weeks (~2-3 months)
  - [ ] Plan Extended Build Systems (E1-E4): 8-12 weeks (~2-3 months)
  - [ ] Plan Python (E1): 2-3 weeks
  - [ ] Plan Node.js (E2): 2-3 weeks
  - [ ] Plan Go (E3): 2-3 weeks
  - [ ] Plan pup (E4): 2-3 weeks
  - [ ] Plan Advanced Features (Phase 8): 6-8 weeks (~1.5-2 months)
  - [ ] Plan Hub System (Phase 10): 4-5 weeks (~1 month)
  - [ ] Plan Internal Package Groups (Phase 11): 2-3 weeks (~0.5 month)
  - [ ] Plan Portage Integration (A1-A6): 22-31 weeks (~5-7 months, includes research)
  - [ ] Plan Total Estimate: 76-107 weeks (~18-25 months for everything)
  - [ ] Plan MVP Timeline (Phases 1-7): 17-25 weeks (~4-6 months)
  - [ ] Plan TU/AST MVP (Phases TU1-TU3): 9-12 weeks (~2-3 months)

- [ ] **IT2.9: Development Path Implementation**
  - [ ] Begin with Core Build System (Phases 1-7): 17-25 weeks
  - [ ] Follow with TU/AST MVP (Phases TU1-TU3): 9-12 weeks ← Enables AI workflows
  - [ ] Follow with pup Support (Phase E4): 2-3 weeks ← Learn from simpler Portage-like system
  - [ ] Follow with TU/AST Full (Phases TU4-TU6): 8-11 weeks ← IDE features
  - [ ] Follow with Portage Integration (A1-A6): 22-31 weeks

---

## Phase IT3 — Next Steps

### Tasks

- [ ] **IT3.1: Immediate Actions**
  - [ ] Begin Phase 1: Core Builder Abstraction
  - [ ] Set up test infrastructure
  - [ ] Create initial test suite for builder interface
  - [ ] Document builder API
  - [ ] Start research for Portage integration (parallel to Phase 1)

- [ ] **IT3.2: First Deliverable Implementation**
  - [ ] Implement Python builder framework
  - [ ] Implement Build method configuration system
  - [ ] Create Initial test suite

**Document Status**: Planning phase complete, ready for implementation.
**Last Review**: 2025-12-17

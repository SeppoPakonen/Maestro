# Phase 7 Improvements and Gap Analysis

**Date**: 2025-12-17
**Status**: Critical issues identified before Phase 7 implementation

---

## Critical Blockers (Must Fix Before Phase 7)

### Blocker 1: Broken Import Chain

**Issue**: `ModuleNotFoundError: No module named 'maestro.repo.package'`

**Root Cause**: `maestro/builders/blitz.py` imports from non-existent module.

**Impact**: Entire maestro command is broken.

**Fix Required**:
1. Create `maestro/repo/package.py` with `PackageInfo` dataclass
2. OR fix imports in `blitz.py` to use correct path
3. Add import validation to test suite

**Priority**: P0 - Breaks everything

---

### Blocker 2: Missing Package Metadata Bridge

**Issue**: Three different package representations with no clear conversion:
- `PackageInfo` (from `maestro repo resolve`) - in memory, JSON serialized
- `Package` (in `maestro/builders/base.py`) - for builders
- Expected `PackageInfo` in `maestro/repo/package.py` - doesn't exist

**Current State**:
```python
# From repo scanning (maestro/repo/resolver.py or similar)
class PackageInfo:  # Where is this defined?
    name: str
    type: str  # 'upp', 'cmake', 'gradle', etc.
    root: str
    files: List[str]
    metadata: Dict[str, Any]

# From builders (maestro/builders/base.py)
class Package:
    name: str
    path: str
    metadata: Dict[str, Any]
    dependencies: List[str]
    files: List[str]
```

**Required Fix**:
1. Define canonical `PackageInfo` in `maestro/repo/package.py`
2. Create `PackageInfo.to_builder_package()` conversion method
3. Ensure builders can work with repo-scanned packages

**Example**:
```python
# maestro/repo/package.py
from dataclasses import dataclass
from typing import List, Dict, Any
from ..builders.base import Package as BuilderPackage

@dataclass
class PackageInfo:
    """Package metadata from repository scanning."""
    name: str
    type: str  # upp, cmake, gradle, maven, autoconf, msvs, misc
    root: str
    files: List[str]
    metadata: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)

    def to_builder_package(self) -> BuilderPackage:
        """Convert to builder-compatible package."""
        return BuilderPackage(
            name=self.name,
            path=self.root,
            metadata=self.metadata
        )
        # Note: Need to populate files, dependencies from metadata
```

**Priority**: P0 - Required for Phase 7.5

---

### Blocker 3: Missing `maestro repo conf` Command

**Issue**: Documentation references `maestro repo <pkg> conf` but it doesn't exist.

**Referenced in**:
- `docs/ast.md`: "Getting TU is tied to `maestro repo <pkg> conf`"
- `docs/todo.md`: TU/AST track needs build configuration

**What it should do**:
```bash
# Show build configuration for a package
maestro repo conf [PACKAGE_ID]

# Output: Compilation flags, include paths, defines, etc.
# This is needed to:
# 1. Build the package
# 2. Generate AST/TU (same flags needed)
# 3. Feed to AI for understanding

# For C++ package:
Compiler: g++
Flags: -std=c++17 -O2 -DNDEBUG
Includes:
  - /usr/include
  - ./include
  - ../CoreLib/include
Defines:
  - GUI
  - MT
  - PLATFORM_POSIX

# For Gradle package:
Java Version: 17
Classpath:
  - build/classes
  - libs/kotlin-stdlib.jar
Source Dirs:
  - src/main/java
  - src/main/kotlin
```

**Implementation Plan**:
Add as **Phase 6.5: Build Configuration Discovery**

**Tasks**:
1. **Extract CMake configuration**:
   - Run `cmake` in configure mode
   - Parse `compile_commands.json` (if exists)
   - Extract from CMakeCache.txt

2. **Extract Autotools configuration**:
   - Run `./configure --help` to see options
   - Parse Makefile after configure
   - Extract CFLAGS, CXXFLAGS, LDFLAGS

3. **Extract Gradle/Maven configuration**:
   - Parse `build.gradle(.kts)` or `pom.xml`
   - Extract dependencies, source dirs, compile options
   - Get Java version

4. **Extract U++ configuration**:
   - Parse `.upp` file (already done)
   - Resolve `uses` dependencies
   - Get mainconfig flags

5. **CLI Implementation**:
   ```python
   # maestro/commands/repo.py (extend existing)
   def cmd_conf(args):
       """Show build configuration for package."""
       pkg = load_package(args.package_id)
       config = discover_build_config(pkg)
       print_build_config(config)
   ```

**Priority**: P0 - Needed for Phase 7 and TU/AST

---

### Blocker 4: Missing Gradle Builder

**Issue**: Gradle packages are scanned (100% done) but no builder exists.

**Current Status**:
- ✅ Gradle scanning works (`maestro repo resolve` finds Gradle packages)
- ❌ No way to build them (`maestro make build` won't work)

**Why This Matters**:
- User's test project is Gradle (`~/Dev/RainbowGame/trash`)
- Phase 7 testing will fail without Gradle builder

**Required Addition**: **Phase 5.75: Gradle Builder**

**Tasks**:
```python
class GradleBuilder(Builder):
    """Build Gradle projects."""

    def configure(self, package, config):
        """Detect gradle vs gradlew."""
        self.gradle_cmd = self._find_gradle(package.path)

    def build_package(self, package, config):
        """Build using gradle/gradlew."""
        gradle_args = [self.gradle_cmd]

        # Build tasks
        if config.clean:
            gradle_args.append('clean')
        gradle_args.append('build')  # or assemble, compileJava, etc.

        # Configuration
        if config.skip_tests:
            gradle_args.append('-x test')

        # Parallel builds
        if config.jobs > 1:
            gradle_args.append(f'--max-workers={config.jobs}')

        # Offline mode
        if config.offline:
            gradle_args.append('--offline')

        # Execute
        return self.execute(gradle_args, cwd=package.path)
```

**Deliverables**:
- Gradle builder implementation
- Support for `gradlew` (Gradle wrapper)
- Support for multi-module projects
- Support for Kotlin DSL and Groovy DSL

**Duration**: 1-2 weeks

**Priority**: P1 - Needed for Phase 7 testing with real project

---

## Phase 7 Gaps (Should Add Before Implementation)

### Gap 1: Builder Selection Logic

**Issue**: Phase 7.3 says "Auto-detect: Use package's native build system" but doesn't explain HOW.

**Required**: Builder selection strategy in Phase 6 or 7.

**Implementation**:
```python
def select_builder(package: PackageInfo, config: BuildConfig) -> Builder:
    """Select appropriate builder for package.

    Priority:
    1. Explicit method from --method flag
    2. Package native build system
    3. Fallback to generic builder
    """
    # Explicit selection
    if config.method:
        return get_builder_by_name(config.method)

    # Auto-detect from package type
    builder_map = {
        'upp': UppBuilder,
        'cmake': CMakeBuilder,
        'autoconf': AutotoolsBuilder,
        'msvs': MSBuildBuilder,
        'maven': MavenBuilder,
        'gradle': GradleBuilder,
        'misc': None,  # Can't build misc packages
    }

    builder_class = builder_map.get(package.type)
    if not builder_class:
        raise ValueError(f"No builder for package type: {package.type}")

    return builder_class(config)
```

**Add to**: Phase 7.3 or create new sub-task 7.2.5

---

### Gap 2: Dependency Build Order

**Issue**: Phase 7.5 says "Build in dependency order" but doesn't specify algorithm.

**Required**: Topological sort implementation.

**Implementation**:
```python
def build_in_dependency_order(packages: List[PackageInfo],
                               builder_factory) -> bool:
    """Build packages in dependency order using topological sort."""

    # Build dependency graph
    graph = {}
    for pkg in packages:
        graph[pkg.name] = pkg.dependencies

    # Topological sort (Kahn's algorithm)
    build_order = topological_sort(graph)

    # Build each package in order
    for pkg_name in build_order:
        pkg = find_package(packages, pkg_name)
        builder = builder_factory.create(pkg)

        if not builder.build_package(pkg):
            print(f"Build failed: {pkg_name}")
            return False

    return True

def topological_sort(graph: Dict[str, List[str]]) -> List[str]:
    """Kahn's algorithm for topological sorting."""
    in_degree = {node: 0 for node in graph}
    for node in graph:
        for dep in graph[node]:
            in_degree[dep] = in_degree.get(dep, 0) + 1

    queue = [node for node in graph if in_degree[node] == 0]
    result = []

    while queue:
        node = queue.pop(0)
        result.append(node)

        for dep in graph[node]:
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)

    if len(result) != len(graph):
        raise ValueError("Circular dependency detected")

    return result
```

**Add to**: Phase 7.5

---

### Gap 3: Error Recovery and Partial Builds

**Issue**: No plan for what happens when a build fails mid-way through multi-package build.

**Scenarios**:
1. Package A builds successfully
2. Package B fails (depends on A)
3. Package C depends on B
4. What should `maestro make` do?

**Required Behavior**:
```
Options:
  --keep-going, -k      Continue building other packages even if some fail
  --stop-on-error       Stop immediately on first error (default)
  --resume              Resume from last failed package
```

**Implementation**:
```python
class BuildSession:
    """Track build session state for resumption."""

    def __init__(self, session_file='.maestro/build/session.json'):
        self.session_file = session_file
        self.completed = set()
        self.failed = set()

    def mark_completed(self, package_name):
        self.completed.add(package_name)
        self.save()

    def mark_failed(self, package_name):
        self.failed.add(package_name)
        self.save()

    def should_skip(self, package_name):
        return package_name in self.completed

    def save(self):
        data = {
            'completed': list(self.completed),
            'failed': list(self.failed),
            'timestamp': time.time(),
        }
        with open(self.session_file, 'w') as f:
            json.dump(data, f)
```

**Add to**: Phase 7.4 (Output Formatting) or create 7.6 (Error Handling)

---

### Gap 4: Build Artifact Management

**Issue**: No specification of where build outputs go and how they're tracked.

**Questions**:
- Where do compiled binaries go?
- How to find built libraries for dependent packages?
- How to clean all vs clean one package?

**Required**: Build artifact structure (already in umk.md but not in todo.md)

From umk.md:
```
.maestro/build/
├── <method>/
│   ├── <package>/
│   │   ├── obj/          # Object files
│   │   ├── <target>      # Final executable/library
```

**Should Add**:
- Artifact registry: `.maestro/build/artifacts.json`
- Track what was built, when, with what config
- Enable `maestro make clean --all` vs `maestro make clean [PACKAGE]`

**Example artifacts.json**:
```json
{
  "CoreLib": {
    "method": "gcc-debug",
    "target": ".maestro/build/gcc-debug/CoreLib/libCoreLib.a",
    "objects": [...],
    "timestamp": 1702834567,
    "config_hash": "abc123..."
  }
}
```

**Add to**: Phase 7.5 or Phase 6

---

## Recommended Phase Additions

### New Phase 6.5: Build Configuration Discovery

**Duration**: 1-2 weeks
**Dependencies**: Phases 1-5
**Insert Before**: Phase 7

**Objective**: Extract build configuration from existing build systems.

**Tasks**:
1. CMake config extraction (compile_commands.json, CMakeCache.txt)
2. Autotools config extraction (Makefile parsing)
3. Gradle/Maven config extraction (build file parsing)
4. U++ config resolution (uses, flags, mainconfig)
5. Implement `maestro repo conf [PACKAGE]` command
6. Store discovered configs in `.maestro/repo/configs/<package>.json`

**Deliverables**:
- Build config discovery for all build systems
- `maestro repo conf` CLI command
- Config caching and invalidation

---

### New Phase 5.75: Gradle Builder

**Duration**: 1-2 weeks
**Dependencies**: Phase 1
**Insert After**: Phase 5.5 (Maven)

**Objective**: Build Gradle projects detected by `maestro repo resolve`.

**Tasks**: (see Blocker 4 above)

---

## Updated Phase 7 Task List

### Phase 7.1: Fix Package Bridge (NEW)
- [ ] Create `maestro/repo/package.py` with canonical `PackageInfo`
- [ ] Implement `PackageInfo.to_builder_package()` conversion
- [ ] Update all imports to use canonical package definition
- [ ] Add validation tests for package conversion

### Phase 7.2: Package Selection
- [ ] By name: `maestro make build MyPackage`
- [ ] By pattern: `maestro make build "core/*"`
- [ ] Main package: `maestro make build` (from current dir)
- [ ] Build all: `maestro make build --all`
- [ ] **NEW**: Implement builder selection logic (see Gap 1)

### Phase 7.3: Method Selection
- [ ] Auto-detect: Use package's native build system
- [ ] Explicit: `maestro make build --method gcc-debug`
- [ ] U++ config: `maestro make build --config "GUI MT"`
- [ ] **NEW**: Fallback when no suitable builder found

### Phase 7.4: Output Formatting
- [ ] Progress indicator for parallel builds
- [ ] Error highlighting
- [ ] Warning/error count summary
- [ ] Build time reporting
- [ ] **NEW**: Build session tracking for resumption

### Phase 7.5: Repository Integration
- [ ] Load packages from `.maestro/repo/index.json`
- [ ] Resolve dependencies using `repo pkg tree`
- [ ] **NEW**: Implement topological sort for dependency order
- [ ] **NEW**: Build artifact registry
- [ ] **NEW**: Config loading from `maestro repo conf`

### Phase 7.6: Error Handling (NEW)
- [ ] --keep-going flag for partial builds
- [ ] --resume flag to continue from failure
- [ ] Build session persistence
- [ ] Error aggregation and reporting

---

## Testing Strategy Updates

### Integration Tests Required:
1. **Multi-package build** (U++ with dependencies)
2. **Cross-build-system** (CMake package depending on Autotools package)
3. **Gradle project** (RainbowGame/trash as test case)
4. **Error recovery** (intentionally break middle package, test --keep-going)
5. **Resume build** (kill build mid-way, test --resume)

### Test Projects:
- `~/Dev/ai-upp` - U++ packages
- `~/Dev/RainbowGame/trash` - Gradle project (REQUIRED for real testing)
- Create synthetic multi-build-system project

---

## Priority Order for Fixes

### Week 1: Critical Blockers
1. Fix ModuleNotFoundError (Blocker 1) - 1 day
2. Create canonical PackageInfo (Blocker 2) - 2 days
3. Implement Phase 6.5: `maestro repo conf` (Blocker 3) - 2 days

### Week 2-3: Phase 5.75
4. Implement Gradle builder (Blocker 4) - 1-2 weeks

### Week 4-6: Phase 7 Enhanced
5. Implement Phase 7 with all gaps filled - 3-4 weeks

---

## Updated Timeline

| Phase | Duration | Notes |
|-------|----------|-------|
| Fix Blockers | 1 week | CRITICAL |
| Phase 6.5: Build Config Discovery | 1-2 weeks | NEW |
| Phase 5.75: Gradle Builder | 1-2 weeks | NEW |
| Phase 7: CLI Integration (Enhanced) | 3-4 weeks | With gap fixes |

**New Phase 7 Start Date**: After blockers + 6.5 + 5.75 = 3-5 weeks from now

---

## Questions for User

1. **Gradle Priority**: Is Gradle builder critical for Phase 7, or can we defer to later?
2. **Error Recovery**: Should --keep-going be MVP or can it wait?
3. **Resume Builds**: Is build resumption needed for MVP?
4. **Test Projects**: Can we use RainbowGame/trash for integration testing?

---

**Status**: Draft for review
**Next Action**: Discuss priorities and get approval to proceed with fixes

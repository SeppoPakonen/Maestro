# `maestro repo resolve` Command Documentation

## Purpose

The `maestro repo resolve` command performs comprehensive repository analysis to identify packages, assemblies, build systems, conventions, and potential violations. This command serves as the canonical mechanism for repository understanding across all Maestro workflows.

## Implementation Location

**Core Implementation**: 
- `maestro/commands/repo.py` - Main command handler and CLI integration
- `maestro/repo/scanner.py` - Repository scanning logic (`scan_upp_repo_v2` function)
- `maestro/repo/build_systems.py` - Multi-build system detection

**Key Functions**:
- `handle_repo_command()` - Main command dispatcher
- `handle_repo_resolve()` - Specific resolve command handler
- `scan_upp_repo_v2()` - Core repository scanning function
- `scan_all_build_systems()` - Multi-build system detection
- `detect_assemblies()` - Assembly detection logic
- `infer_internal_packages()` - Internal package creation from unknown paths

## Command Contract

### `maestro repo resolve`

**Purpose**: Scan repository for packages across build systems and create comprehensive repository model.

**Inputs**:
- `--path <path>`: Path to repository to scan (default: current directory)
- `--json`: Output results in JSON format
- `--no-write`: Skip writing artifacts to `.maestro/repo/`
- `--find-root`: Find repository root with `.maestro` directory instead of scanning current directory
- `--include-user-config`: Include user assemblies from `~/.config/u++/ide/*.var` (default)
- `--no-user-config`: Skip reading user assembly config
- `--verbose`, `-v`: Show verbose scan information

**Outputs**:
- **stdout**: Human-readable summary of scan results
- **JSON**: Structured output when `--json` flag used
- **Artifacts**: Repository scan results written to `.maestro/repo/` directory:
  - `index.json`: Full structured scan result
  - `index.summary.txt`: Human-readable summary
  - `state.json`: Repository state metadata
  - `assemblies.json`: Assembly information

**Exit Codes**:
- `0`: Success - Repository scanned and artifacts created
- `1`: Failure - Repository not found, invalid path, or scan error

**Hard Stops**:
- Repository path does not exist
- Path is not a directory
- `.maestro/` directory not found (when using `--find-root`)

**Recoverable States**:
- Build system detection fails (continues with available info)
- Some packages not recognized (continues with detected packages)
- User assembly configuration not found (continues without user assemblies)

**CLI Contract Example**:
```bash
# Basic repository scan
maestro repo resolve

# Scan specific path with JSON output
maestro repo resolve --path /path/to/repo --json

# Verbose scan without writing artifacts
maestro repo resolve --verbose --no-write

# Find repository root and scan
maestro repo resolve --find-root --verbose
```

## Core Functionality

### Package Discovery
- **Ultimate++ Packages**: Detect via `<Name>/<Name>.upp` pattern
- **Other Build Systems**: CMake, Make, Autoconf, Gradle, Maven, Visual Studio
- **File Collection**: Gather source files based on language extensions
- **Metadata Parsing**: Extract dependencies, configurations from build files

### Assembly Detection
- **Multiple Package Directories**: Identify directories containing 2+ packages
- **Nested Package Support**: Handle packages within packages with ancestor path tracking
- **User Assembly Integration**: Include assemblies from `~/.config/u++/ide/*.var`

### Build System Detection
- **CMake**: `CMakeLists.txt` with target extraction
- **Make**: `Makefile`, `GNUmakefile`, `makefile`
- **Autoconf**: `configure.ac`, `configure.in`, `Makefile.am`
- **Gradle**: `build.gradle`, `build.gradle.kts`, `settings.gradle`
- **Maven**: `pom.xml` files with module detection
- **Visual Studio**: `.sln` files with project extraction
- **Ultimate++**: `.upp` files

### Convention Inference
- **Naming Patterns**: Detect camelCase, snake_case, UpperCamelCase, ALL_CAPS
- **Directory Structures**: Identify common patterns like `src/`, `include/`, `test/`
- **Framework Fingerprinting**: Ultimate++, Qt, and other framework detection

### Dependency Graph
- **Package-to-Package**: Extract dependencies from build files
- **Conditional Dependencies**: Handle build configuration dependencies
- **System Libraries**: Map system dependencies to packages

### Violation Detection
- **Naming Violations**: Files not following detected conventions
- **Layout Violations**: Directory structures not matching patterns
- **Co-location Rules**: Files that should not be together

## Data Structures

### PackageInfo
```python
@dataclass
class PackageInfo:
    name: str
    dir: str
    upp_path: str
    files: List[str]
    upp: Optional[dict]  # Parsed .upp content
    build_system: str    # 'upp', 'cmake', 'make', 'autoconf', 'maven', 'gradle', etc.
    dependencies: List[str]
    groups: List[FileGroup]
    ungrouped_files: List[str]
```

### AssemblyInfo
```python
@dataclass
class AssemblyInfo:
    name: str
    root_path: str
    package_folders: List[str]
    evidence_refs: List[str]
    assembly_type: str
    packages: List[str]
    package_dirs: List[str]
    build_systems: List[str]
    metadata: Dict[str, Any]
```

### FileGroup
```python
@dataclass
class FileGroup:
    name: str
    files: List[str]
    readonly: bool
    auto_generated: bool
```

## File Locations

**Source Code**:
- `maestro/commands/repo.py` - Command handlers
- `maestro/repo/scanner.py` - Core scanning logic
- `maestro/repo/build_systems.py` - Build system detection
- `maestro/repo/package.py` - Package data structures
- `maestro/repo/grouping.py` - Auto-grouping logic

**Output Artifacts**:
- `.maestro/repo/index.json` - Full scan results
- `.maestro/repo/index.summary.txt` - Human-readable summary
- `.maestro/repo/state.json` - Scan state metadata
- `.maestro/repo/assemblies.json` - Assembly information

## Related Commands

- `maestro repo show` - Display stored repository scan results
- `maestro repo pkg` - Query and inspect packages
- `maestro repo hier` - Show repository hierarchy
- `maestro repo conventions` - Show/detect naming conventions
- `maestro repo rules` - Show repository rules

## Cross-links

- **Related to**: [WF-05: Repo Resolve](scenario_05_repo_resolve_packages_conventions_targets.md)
- **Integration Spine**: Used by WF-01, WF-03, WF-04 for repository understanding
- **Implementation location**: Core functionality in `maestro/repo/` package
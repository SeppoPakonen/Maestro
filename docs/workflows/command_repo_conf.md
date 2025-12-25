# maestro repo conf - Repository Build Configuration Command

## Overview
The `maestro repo conf` command displays build configurations for packages across different build systems. It extracts and presents configuration data from various build systems including U++, CMake, Autotools, Gradle, Maven, and MSBuild.

## Purpose
This command serves as the bridge between repository structure discovery (`maestro repo resolve`) and actual build/analysis operations like `maestro tu`. It provides the necessary build configuration information (compile flags, include paths, dependencies) required for accurate AST generation and code analysis.

## Usage
```
maestro repo conf [PACKAGE_NAME] [OPTIONS]
```

## Options
- `--path` - Path to repository root (default: auto-detect via .maestro/)
- `--json` - Output results in JSON format

## Implementation Details

### Location
- Command handler: `maestro/commands/repo.py` (handle_repo_pkg_conf function)
- Configuration extraction: `maestro/repo/build_config.py` (get_package_config function)
- Package information: `maestro/repo/package.py`

### Build System Support
The command supports configuration extraction from multiple build systems:

#### U++ (Uppercase Plus Plus)
- Extracts from `.upp` files
- Information includes: uses, mainconfigs, file lists, descriptions
- Located in: `maestro/repo/upp_parser.py`

#### CMake
- Extracts from `CMakeLists.txt` and `compile_commands.json`
- Information includes: targets, definitions, include directories, compile options, dependencies
- Parses: `add_executable`, `add_library`, `include_directories`, `find_package` directives

#### Autotools
- Extracts from `configure.ac`/`configure.in` and `Makefile.am`/`Makefile`
- Information includes: project name, version, defines, includes, libraries, dependencies
- Parses: `AC_INIT`, `PKG_CHECK_MODULES`, `AC_CHECK_LIB` macros

#### Gradle
- Extracts from `build.gradle` and `build.gradle.kts`
- Information includes: plugins, dependencies, repositories, source sets
- Parses: plugins block, dependencies block, repository configurations

#### Maven
- Extracts from `pom.xml`
- Information includes: dependencies, plugins, properties, modules, repositories
- Uses XML parsing for Maven project structure

#### MSBuild
- Extracts from `.vcxproj`, `.csproj`, `.vbproj`, and `.sln` files
- Information includes: configurations, platforms, references, packages
- Uses XML parsing for MSBuild project structure

## Integration with TU Commands
The build configuration information from `maestro repo conf` is critical for `maestro tu` operations because:

1. **Compile Flags**: TU operations require the same compile flags used in the actual build to accurately parse the code
2. **Include Paths**: Proper include paths are necessary for resolving `#include` directives and imports
3. **Preprocessor Definitions**: Definitions affect how the code is parsed and analyzed
4. **Dependencies**: Understanding project dependencies helps with cross-reference analysis

## Output Format
The command provides both human-readable and JSON output formats:

### Human-readable format includes:
- Package name and build system
- Directory path
- Build configurations (varies by system)
- Dependencies and references
- Include directories and compile options

### JSON format includes:
- Complete configuration data structure
- All extracted metadata
- Machine-readable format for tool integration

## Relationship to Other Commands
- **Prerequisite**: `maestro repo resolve` must be run first to discover packages
- **Used by**: `maestro tu` commands to get necessary build flags for AST generation
- **Part of**: Repository analysis workflow (WF-05) that feeds into AST/TU workflows (WF-07)
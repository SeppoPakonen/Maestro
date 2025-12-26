# WF-12: RepoConf gate — required targets/configs for build, TU, and convert

## Metadata

```
id: WF-12
title: RepoConf gate — required targets/configs for build, TU, and convert
tags: [repo-conf, gate, build, tu, ast, convert, validation, targets, configs]
entry_conditions:
  - Repository exists with source code
  - Maestro initialized in repository
  - Repo model exists (from resolve or manual authoring per WF-11)
  - No valid RepoConf exists OR existing RepoConf is invalid/outdated
exit_conditions:
  - Valid RepoConf exists and is validated
  - Default target/config selected and locked
  - Build, TU, and convert operations can proceed
artifacts_created:
  - `./docs/maestro/repo/conf.json` (or per-package configs)
  - Validation reports/logs
  - Default target selection metadata
failure_semantics:
  - Missing RepoConf: Hard stop for build/TU/convert operations
  - Invalid RepoConf: Hard stop with validation error details
  - Inconsistent RepoConf vs repo model: Hard stop with inconsistency report
links_to: [WF-09, WF-10, WF-11]
related_commands: 
  - `maestro repo conf [PACKAGE]` (implemented in maestro/commands/repo.py)
  - `maestro repo conf target add <name> --type <exe|lib>` (proposed in WF-11)
  - `maestro repo conf set-default-target <name>` (proposed in WF-11)
  - `maestro build [TARGET]` (requires RepoConf for target selection)
  - `maestro tu [PACKAGE]` (requires RepoConf for compiler flags)
  - `maestro convert run` (requires RepoConf for buildable targets)
```

## Definition: What RepoConf contains

Based on the implementation in `maestro/repo/build_config.py`, RepoConf contains build configuration data for packages across multiple build systems. The minimal schema includes:

```json
{
  "package_name": "string",
  "build_system": "upp|cmake|autoconf|gradle|maven|msvs|...",
  "directory": "path/to/package",
  "targets": [
    {
      "name": "target_name",
      "type": "executable|library|test",
      "sources": ["path/to/source1.cpp", "path/to/source2.cpp"],
      "compiler_flags": ["-std=c++17", "-Wall"],
      "include_paths": ["/usr/include", "path/to/includes"],
      "definitions": ["DEBUG=1", "VERSION=2.0"],
      "language_standard": "c++17|c99|java8|...",
      "required_flags_for_ast": ["-fsyntax-only", "-Xclang -ast-dump"]
    }
  ],
  "default_target": "target_name",
  "configurations": {
    "debug": {
      "compiler_flags": ["-g", "-O0"],
      "definitions": ["DEBUG=1"]
    },
    "release": {
      "compiler_flags": ["-O2", "-DNDEBUG"],
      "definitions": ["NDEBUG=1"]
    }
  }
}
```

For different build systems, RepoConf includes:

- **U++**: Uses, mainconfigs, file lists from `.upp` files
- **CMake**: Targets, definitions, include directories from `CMakeLists.txt` and `compile_commands.json`
- **Autotools**: Defines, includes, libraries from `configure.ac` and Makefiles
- **Gradle/Maven**: Dependencies, plugins, source sets from build files
- **MSBuild**: Configurations, platforms, references from project files

## Hard gate rules

### RepoConf is mandatory for execution

The following operations cannot proceed without a valid RepoConf:

1. **`build/make` execution**
   - Cannot select a target to build without RepoConf
   - Cannot determine appropriate build driver without RepoConf
   - Hard stop: "No build configuration found. Run 'maestro repo resolve' or create manual configuration."

2. **`tu` / AST generation**
   - Cannot determine compiler invocation without complete flags from RepoConf
   - Cannot resolve include paths for accurate parsing without RepoConf
   - Hard stop: "No build configuration for AST generation. Run 'maestro repo conf' first."

3. **`convert run` prerequisites**
   - Cannot identify buildable targets without RepoConf
   - Source repo must have concrete buildable target/config for conversion
   - Hard stop: "No buildable targets found. Create build configuration with 'maestro repo conf'."

### Failure semantics

- **Missing RepoConf** → Hard stop with next steps:
  - Resolve deep/lite: `maestro repo resolve`
  - Manual authoring: Follow WF-11 procedures

- **Invalid RepoConf schema** → Hard stop with validation error details
  - Schema validation failure
  - Required fields missing
  - Invalid paths or configurations

- **Inconsistent RepoConf vs repo model** → Hard stop
  - Target points to missing package
  - Referenced paths don't exist
  - Build system mismatch between model and conf

## Creation paths

### From Resolve (WF-10)

1. **Repo Resolve (lite/deep) produces candidates**
   - `maestro repo resolve` scans repository and identifies packages
   - Build systems detected and analyzed
   - Configuration candidates generated

2. **RepoConf is generated or completed from those candidates**
   - Configuration extraction from build files (CMakeLists.txt, pom.xml, etc.)
   - Default target selection based on heuristics
   - Validation and storage in `./docs/maestro/repo/conf.json`

### Manual authoring (WF-11)

1. **Operator defines targets/configs explicitly**
   - Use proposed commands like `maestro repo conf target add`
   - Define build targets with sources, compiler flags, and dependencies
   - Set default target with `maestro repo conf set-default-target`

## Selection & lock-in

### How "default target/config" is selected

1. **Automatic selection** (during resolve):
   - Heuristic: If single executable target exists, make it default
   - Heuristic: If single library exists, make it default
   - Heuristic: If multiple targets, select main application target

2. **Manual selection** (during manual authoring):
   - Operator explicitly sets default with `maestro repo conf set-default-target <name>`
   - Selection stored in RepoConf metadata

### How selection is persisted (repo truth)

- Stored in `./docs/maestro/repo/conf.json` under `default_target` field
- Follows WF-09 storage contract (repo truth in `./docs/maestro/**`)

### Whether selection can be changed and what it invalidates

- **Selection can be changed**: Yes, with `maestro repo conf set-default-target`
- **Invalidation**: Changing default target may require:
  - TU index rebuild if compiler flags change
  - Rebuild of affected components
  - Update to dependent convert operations

## Validation & invariants

### Schema validity

- RepoConf must conform to the schema defined above
- Required fields: `package_name`, `build_system`, `directory`, `targets`
- Each target must have: `name`, `type`, `sources`

### Referenced paths exist

- All paths in `sources`, `include_paths` must exist in repository
- Allow generated files if specified as such in metadata

### Toolchain executable exists

- Compiler specified in configuration must be available
- Or defer with clear error message about missing toolchain

### For TU: compiler command is reproducible and deterministic

- AST generation command must produce consistent results
- Include paths and flags must be complete and deterministic
- No reliance on environment variables that may change

## Integration points

- **WF-05/WF-10 feed into RepoConf**: Repo Resolve provides package information that RepoConf builds upon
- **WF-07 (TU/AST) requires RepoConf**: AST generation needs complete compiler flags from RepoConf
- **WF-08 (Convert) requires RepoConf on source repo side**: Conversion needs buildable targets from RepoConf

## Tests implied by WF-12

### Unit tests

- Schema validation fails on missing fields
- Default target selection persisted correctly
- Consistency checks vs repo model

### Integration tests

- Minimal fixture repo with manual RepoConf → build OK
- Fixture with resolve-generated candidates → conf produced → TU OK
- Missing conf → build/TU hard stop with clear message
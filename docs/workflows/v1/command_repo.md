# `maestro repo` Command Documentation

## Status: MISSING/UNREGISTERED

**IMPORTANT: The `maestro repo` command is NOT currently available in the CLI, though the underlying functionality exists in the codebase.**

## Purpose

The `maestro repo` command is intended for repository inspection and detection functionality, allowing Operators to:
- Scan repositories for build files, packages, and assemblies
- Detect programming languages and project structure
- Resolve build dependencies and generate build plans
- Operate in read-only mode without creating Maestro project state

## Expected Inputs

Based on codebase analysis, the command would accept subcommands including:
- `resolve` - Scan repository and detect packages/assemblies
- `list` - List detected packages
- `show` - Show repository scan details
- `tree` - Show package dependency tree
- `scan` - Rescan repository
- `asm list` - List assemblies
- `asm show <name>` - Show assembly details

## Expected Outputs

- **stdout**: Repository scan results, package lists, dependency information
- **Files**: Scan artifacts in `$HOME/.maestro/repo/` (not in project directory)
- **$HOME/.maestro usage**: Repository scan cache and results stored in user's home directory

## Detection Logic Summary

The underlying repository scanning functionality (as found in the codebase) includes:

- **Build file detection**: Makefile, CMakeLists.txt, configure.ac, pom.xml, build.gradle, etc.
- **Language detection**: Based on file extensions and content
- **Ultimate++ assembly detection**: .upp files with package and assembly information
- **Package identification**: Grouping of related source files
- **Unknown path identification**: Files not belonging to any package

## Failure Semantics

- **Non-critical failures**: Missing build tools, unrecognized file types
- **Hard stops**: Critical errors in repository traversal or file system access
- **Recoverable**: Build system detection conflicts with user resolution

## Cross-links

- **Related to**: [WF-03: Read-only repo inspection + build](scenario_03_readonly_repo_inspect_build.md)
- **Implementation location**: Core functionality exists in `maestro/repo/` and `maestro/ui_facade/repo.py`
- **Missing registration**: Command is not registered in `maestro/modules/cli_parser.py`

## Current Gap Analysis

The repository scanning functionality exists in the Maestro codebase but is not accessible through the CLI:

1. **Functions exist**: `scan_upp_repo_v2`, `resolve_repository`, `list_repo_packages` functions are implemented
2. **UI facade exists**: `maestro/ui_facade/repo.py` contains the functionality
3. **TUI integration exists**: TUI has repo command actions
4. **Assembly commands exist**: `maestro/repo/assembly_commands.py` implements some repo asm subcommands
5. **CLI registration missing**: The main CLI parser and command handler don't register the `repo` command

## Recommended Action

The `maestro repo` command should be registered in the CLI by:
1. Adding `add_repo_parser` function in `maestro/commands/repo.py` or similar
2. Registering the parser in `maestro/modules/cli_parser.py`
3. Adding command handling in `maestro/main.py`
4. Testing the complete workflow as documented in WF-03
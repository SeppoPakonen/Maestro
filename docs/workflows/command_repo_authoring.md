# Command: Repo Authoring (`command_repo_authoring.md`)

**ID**: `command_repo_authoring`
**Status**: Target for `WF-11`

This document analyzes the current state of repository authoring commands in Maestro to ground the proposals in `WF-11`.

## 1. Analysis of Existing Commands

A search of the Maestro codebase reveals that there are **no existing high-level commands** for manually authoring or editing the repository model, such as `maestro repo package add` or `maestro repo conf target add`.

The primary interaction with the repository model is through the `maestro repo resolve` command, which is a discovery mechanism, not an authoring tool. The command infrastructure is located in `maestro/commands/`, but no files or functions correspond to manual repo model manipulation.

## 2. Identified Gap

There is a clear gap between the desired manual authoring workflow (`WF-11`) and the current implementation. To make Maestro usable on repositories where `resolve` fails or is insufficient, a suite of authoring commands is required.

## 3. Proposed Minimal Command Set

To satisfy the requirements of `WF-11`, the following commands are proposed. These contracts are designed to be implemented in the Maestro CLI.

### 3.1. Repo Model Commands (`maestro repo ...`)

These commands would manipulate the core repository model stored in `./docs/maestro/repo/model.json` (or similar).

| Proposed Command | Description | Handler Function (Proposed) |
| --- | --- | --- |
| `maestro repo package add <name> --path <dir>` | Adds a new package/module to the repo model. | `maestro.commands.repo.add_package` |
| `maestro repo package set-language <name> <lang>` | Sets the primary programming language for a package. | `maestro.commands.repo.set_package_language` |
| `maestro repo package set-driver <name> <driver>` | Sets the build system driver (e.g., `make`, `cmake`). | `maestro.commands.repo.set_package_driver` |

### 3.2. Repo Conf Commands (`maestro repo conf ...`)

These commands would manipulate the repository configuration, defining build targets and other specifics, stored in `./docs/maestro/repo/conf.json` (or similar).

| Proposed Command | Description | Handler Function (Proposed) |
| --- | --- | --- |
| `maestro repo conf target add <target_name> --type <exe\|lib> --package <pkg_name> --sources <files...>` | Defines a new build target. | `maestro.commands.repo_conf.add_target` |
| `maestro repo conf target set-compiler-flags <target_name> <flags...>` | Sets compiler flags for a specific target. | `maestro.commands.repo_conf.set_compiler_flags` |
| `maestro repo conf set-default-target <target_name>` | Selects the default target to be used by `maestro build` or `maestro tu`. | `maestro.commands.repo_conf.set_default_target` |

This analysis confirms that the commands required for `WF-11` are not yet implemented. The workflow document will present these as **Proposed Contracts**.

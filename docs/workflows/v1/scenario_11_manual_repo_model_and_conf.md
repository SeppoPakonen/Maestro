---
id: WF-11
title: Manual repo model + manual RepoConf (resolve optional)
tags: [repo, manual, repo-model, repo-conf, override, build, tu]
entry_conditions: A repository exists, but `repo resolve` may be incomplete or undesirable.
exit_conditions: A valid, hand-authored repository model and configuration exist, sufficient for `build` and `tu` to run.
artifacts_created:
  - `./docs/maestro/repo/model.json`
  - `./docs/maestro/repo/conf.json`
links_to: [WF-09, WF-10]
related_commands:
  - "Proposed: `maestro repo package add`"
  - "Proposed: `maestro repo package set-language`"
  - "Proposed: `maestro repo package set-driver`"
  - "Proposed: `maestro repo conf target add`"
  - "Proposed: `maestro repo conf set-default-target`"
---

# WF-11: Manual Repo Model and RepoConf

This workflow documents the "two-way" design principle for repository modeling in Maestro: everything that `repo resolve` can *discover*, the user or an AI agent must also be able to *author manually* via `maestro repo ...` commands.

## 1. Core Concept: Two-Way Repo Commands

Maestro's repository commands are designed to be a two-way street:

1.  **Discovery (`repo resolve`)**: The `resolve` command acts as a *scanner*. It inspects the codebase to automatically discover packages, build systems, and targets, creating a baseline repository model. This is ideal for standard project layouts.
2.  **Authoring (`repo ...` and `repo conf ...`)**: Manual authoring commands act as *editors*. They allow a user or agent to create, modify, or overwrite the repository model and configuration from scratch.

This duality is critical. It ensures Maestro is not a "black box" and can be guided to work with non-standard repositories, legacy projects, or in cases where automatic detection is insufficient. It makes `repo resolve` a helpful but **optional** step.

## 2. Minimal Model Required for Build/TU

To successfully run `maestro build`, `maestro tu`, or `maestro convert` prerequisites, a "minimum viable repo model" must be present in the `docs/maestro/repo/` directory. This model provides the necessary context about the codebase structure and build process.

The following schemas are **Proposed** as the minimal set of data required.

### Minimal `model.json` Schema

This file defines the high-level structure of the repository.

```json
{
  "packages": [
    {
      "name": "default-pkg",
      "path": ".",
      "language": "cpp",
      "driver": "make"
    }
  ]
}
```

-   **`packages`**: An array of objects, where each object represents a logical code module or package.
    -   `name`: A unique identifier for the package.
    -   `path`: The root directory of the package's source code.
    -   `language`: The primary programming language (e.g., `cpp`, `rust`, `python`).
    -   `driver`: The build system to be used (e.g., `make`, `cmake`, `cargo`).

### Minimal `conf.json` Schema

This file defines the specific build targets and configurations.

```json
{
  "targets": [
    {
      "name": "my_app",
      "package": "default-pkg",
      "type": "exe",
      "sources": ["src/main.cpp"],
      "compiler_flags": ["-Iinclude"]
    }
  ],
  "default_target": "my_app"
}
```

-   **`targets`**: An array of buildable entities.
    -   `name`: A unique name for the target.
    -   `package`: The name of the package this target belongs to.
    -   `type`: The type of output (`exe` for executable, `lib` for library).
    -   `sources`: A list of source files required to build the target.
    -   `compiler_flags`: (Optional) Inputs required for TU, such as include paths or defines.
-   **`default_target`**: The target that `maestro build` and `maestro tu` will use if no specific target is provided.

## 3. Manual Authoring Workflow

1.  **(Optional) Initialize**: Run `maestro init` to create the `./docs/maestro/` directory structure if it doesn't exist.
2.  **Create/Edit Repo Model**: Use the (Proposed) `maestro repo package ...` commands to define at least one package, its language, and its build driver. This populates `model.json`.
3.  **Create/Edit Repo Conf**: Use the (Proposed) `maestro repo conf ...` commands to define at least one build target and set it as the default. This populates `conf.json`.
4.  **Validate**: Before execution, Maestro will validate the schemas of `model.json` and `conf.json`. A dry-run command (`maestro build --dry-run`) would generate a build plan without executing it, serving as a final validation step.
5.  **Run**: Execute `maestro build` or `maestro tu`. These commands consume the hand-authored model and configuration to perform their tasks.

## 4. Precedence and Merge Rules

When both manually authored and resolved data exist, a clear precedence rule is required. The recommended and proposed strategy is:

**Manual overrides win.**

-   If a user manually sets a value, it takes precedence over any value discovered by `repo resolve`.
-   Resolved values are only used to fill in fields that have not been manually specified.
-   Conflicts are resolved in favor of the manual entry; there is no silent merge.

**Examples**:
-   `repo resolve` detects a `Makefile`, but the user runs `maestro repo package set-driver my_pkg cmake`. The build system for `my_pkg` is now considered `cmake`.
-   `repo resolve` discovers targets `A` and `B`. The user manually edits `conf.json` to only include target `A`. Only target `A` is now known to Maestro.

## 5. Storage Locations

This workflow adheres strictly to the storage rules defined in **WF-09**. All authored repository data is stored as human-readable files within the project's `docs/maestro/` directory.

-   **Repo Model**: `./docs/maestro/repo/model.json`
-   **Repo Configuration**: `./docs/maestro/repo/conf.json`

This state is part of the project's "truth store" and is intended to be version-controlled.

## 6. Command Contracts (Proposed)

As confirmed in `docs/workflows/command_repo_authoring.md`, the following commands **do not currently exist** and are proposed as the minimal set required to implement this workflow.

| Proposed Command | Description |
|---|---|
| `maestro repo package add <name> --path <dir>` | Adds a new package to `model.json`. |
| `maestro repo package set-language <name> <lang>`| Sets the language for a package. |
| `maestro repo package set-driver <name> <driver>`| Sets the build driver (`make`, `cmake`, etc.) for a package. |
| `maestro repo conf target add <name> --type <exe\|lib>` | Adds a new build target to `conf.json`. |
| `maestro repo conf set-default-target <name>` | Sets the default target for build and TU operations. |

## 7. Failure Semantics

-   **Missing Required Fields**: If a required field in `model.json` or `conf.json` is missing (e.g., `default_target`), Maestro will raise a validation error and stop.
-   **Unknown Driver/Toolchain**: If the `driver` specified is not supported, Maestro will stop before attempting a build or TU.
-   **Conflicting Edits**: The "manual overrides" rule prevents conflicts. The last manual edit is considered the source of truth.

## 8. Tests Implied by WF-11

-   **Unit Tests**:
    -   Test that the proposed `maestro repo` command writers produce parseable and valid JSON.
    -   Test that the validation logic correctly catches missing or invalid fields in `model.json` and `conf.json`.
    -   Test the precedence logic to ensure manual values deterministically override resolved values.
-   **Integration Tests**:
    -   Create a minimal "hello world" repository with only a `Makefile` and hand-authored `model.json` and `conf.json`. Verify that `maestro build` successfully builds the project.
    -   Create a repository where `repo resolve` would detect `make`, but manually override it with `cmake`. Verify that Maestro uses `cmake` for the build.

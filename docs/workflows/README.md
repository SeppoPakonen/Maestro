# Maestro Workflow Scenarios

## Purpose

This directory contains **scenario-based operational truth** for Maestro workflows. Each scenario is a complete, mergeable workflow unit that documents:

- Entry and exit conditions
- Step-by-step phased execution flow
- Command contracts (inputs, outputs, failure semantics)
- Human decision gates and validation points
- Artifact creation (issues, tasks, truth files)
- Test implications

Scenarios are designed to:

1. **Serve as runnable playbooks** for users and implementers
2. **Drive test generation** (unit, integration, fixture repos)
3. **Assemble into a single massive conditional workflow diagram** spanning all Maestro operations

This approach aligns with Maestro's "docs as truth / temporal model / track-phase-task" philosophy.

---

## Conventions

### Scenario Numbering

Scenarios use the ID format `WF-##`:

- `WF-01`: Existing repo, no Maestro yet; single main branch; compiled language
- `WF-02`: (Future) Existing repo with feature branches
- `WF-03`: (Future) New greenfield repo
- `WF-04`: (Future) Runtime error workflow
- `WF-05`: Repo Resolve — packages, conventions, build targets, and derived issues/tasks (Integration Spine)
- `WF-06`: AI-driven task execution with Work Sessions and multi-session resume
- `WF-07`: AST/TU workflows — rename, C++→JS transform, autocomplete (Engine Room)
- `WF-08`: Convert — cross-repo pipeline (New/Plan/Run)
- `WF-09`: Storage Contract — repo truth vs home hub (read-only rules)
- etc.

**Note on Resolve Depth**: Repo Resolve has multiple levels (Lite vs. Deep) defined in **WF-10**. Other workflows must reference WF-10 for its definitions rather than re-defining resolve depth.

**Note on Resolve Optionality**: Repo Resolve is optional when a repo model and conf are authored manually (**WF-11**).

IDs are stable and never change, even if scenarios are deprecated or superseded.

### File Naming

Each scenario has two files:

1. **Markdown**: `scenario_##_short_name.md` - Human-readable phased flow, command contracts, test mapping
2. **PlantUML**: `scenario_##_short_name.puml` - Visual swimlane diagram with gates and conditionals

### Metadata Schema

Every scenario Markdown file must include a **front-matter metadata block** at the top. This block uses strict `key: value` pairs (YAML-compatible):

```yaml
---
id: WF-##
title: Short descriptive title
tags: [tag1, tag2, tag3]
entry_conditions: |
  - Condition 1
  - Condition 2
exit_conditions: |
  - Success condition 1
  - Success condition 2
artifacts_created: |
  - docs/maestro/tracks/*.json
  - issue data*.md
failure_semantics: |
  - Hard stop: Invalid JSON from AI
  - Recoverable: Build errors (create issues/tasks)
follow_on_scenarios: [WF-05, WF-07]
---
```

**Required fields**:
- `id`: Scenario ID (WF-##)
- `title`: Short human-readable title
- `tags`: Array of relevant tags
- `entry_conditions`: Preconditions that must be true to enter this scenario
- `exit_conditions`: Success criteria for completing this scenario
- `artifacts_created`: Files/data structures produced
- `failure_semantics`: How failures are handled (hard stops vs recoverable)
- `follow_on_scenarios`: IDs of scenarios that may follow this one

---

## Diagram Strategy

### Individual Scenario Diagrams

Each `.puml` file:

- Includes `_shared.puml` for consistent styles and macros
- Uses **swimlanes** to show actor boundaries:
  - `User`
  - `Maestro CLI`
  - `AI Engine`
  - `Repo/Toolchain`
  - `Docs (truth)`
- Models **gates explicitly** using `GATE()` macro
- Models **hard stops** using `HARD_STOP()` macro
- Wraps the scenario as a **callable procedure**:

```plantuml
!include _shared.puml

!procedure WF_01()
  |User|
  :ENTRY_WF_01;
  :Run maestro init;
  |Maestro CLI|
  ... flow ...
  :EXIT_WF_01;
!endprocedure
```

### Merge-Friendly Design

To enable assembly into a single mega-diagram:

1. **Labeled entry/exit points**: Each scenario defines `ENTRY_WF_##` and `EXIT_WF_##`
2. **Procedure encapsulation**: Scenarios are wrapped in `!procedure WF_##()` ... `!endprocedure`
3. **Shared macro vocabulary**: All scenarios use the same `GATE()`, `HARD_STOP()`, `CREATE_ISSUE()`, etc.
4. **No global assumptions**: Scenarios do not hardcode "start/end only" assumptions; they are composable units

### Master Diagram Assembly

A future `master_workflow.puml` will:

```plantuml
!include _shared.puml
!include scenario_01_existing_repo_single_main.puml
!include scenario_02_feature_branches.puml
... etc ...

@startuml
(*) --> [start] Analyze_Repository

if "Maestro initialized?" then
  --> [no] WF_01()
  --> ENTRY_WF_05
else
  --> [yes] ENTRY_WF_04
endif

... conditional branches between scenarios ...

@enduml
```

This creates a single, massive conditional workflow spanning all Maestro operations.

---

## Command Contracts

Each scenario documents the **contracts** for commands used:

- **Purpose**: What the command does
- **Inputs**: Required state, flags, environment
- **Outputs**: Files created, state changes, side effects
- **Hard stops vs recoverable states**: Blocking failures vs retryable errors

### Example Command Contract

**Command**: `maestro init`

- **Purpose**: Bootstrap Maestro in an existing repo
- **Inputs**: Current directory must be a git repo
- **Outputs**:
  - Creates `docs/maestro/tracks/`, `docs/maestro/phases/`, `docs/maestro/tasks/`, `issue data`
  - Creates `docs/maestro/index.json` (empty scaffold)
- **Hard stops**: Not a git repo
- **Recoverable**: Already initialized (idempotent)

---

## Project State Boundaries

To avoid ambiguous safety claims, scenarios define **precise project state boundaries**:

### Truth Areas (Protected)

- `docs/maestro/tracks/*.json` - Track definitions
- `docs/maestro/phases/*.json` - Phase definitions
- `docs/maestro/tasks/*.json` - Task definitions
- `issue data*.md` - Issue reports
- `docs/maestro/index.json` - Current plan state
- `active tasks in JSON` - Active task list
- `completed tasks in JSON` - Completed task archive

**Protection mechanism**: Parsers validate structure; malformed writes are rejected (hard stop).

### Non-Truth Areas

- Source code files (unless explicitly in a task's change scope)
- Build artifacts
- Test outputs
- Logs (unless being parsed for issue generation)

### Actor Model: Operator (Human or AI)

**Critical Concept**: In Maestro workflows, there is **no separate AI workflow participant**. Instead, we use the **Operator** actor model:

- **Operator** = human user OR AI runner
- Both use the **same CLI command interface**
- Behavior is **identical at the command boundary**
- AI is **not a separate actor**; it's an execution mode

**What this means for diagrams**:
- Swimlanes show: `|Operator|`, `|Maestro CLI|`, `|Repo/Toolchain|`, `|Docs (truth)|`
- NO separate `|AI Engine|` lane
- Commands like `maestro discuss` or `maestro work` may invoke AI internally, but this is an **implementation detail** of the Maestro CLI, not a separate workflow step

### Engine Interaction Boundaries

Engines (AI or rule-based) operate **via Maestro-mediated channels**:

- Engines produce **JSON plans/responses** that must pass schema validation
- Invalid/non-JSON engine replies are a **blocking failure** (hard stop; operator may re-prompt explicitly)
- Engines may propose changes, but changes are applied through:
  - Maestro commands (e.g., `maestro task create`)
  - Validation/assert layers (rule-based, not AI-driven)
- Engines do **not** directly mutate project state; they operate through Maestro's command layer
- **Validation is rule-based**, not AI-driven (e.g., JSON schema checks, file existence checks)

---

## Test Mapping

Each scenario includes a **"Tests implied by this scenario"** section that identifies:

1. **Unit tests**: Command builders, parsers, dependency ordering logic
2. **Integration tests**: Fixture repos (compile fail, runtime error, warnings policy)
3. **Golden logs**: Example sessions with expected outputs

This ensures scenarios are testable and drive quality.

---

## Relationship to Tracks/Phases/Tasks

Scenarios document **operational workflows** (how a user and Maestro interact over time).

Tracks/Phases/Tasks document **project structure** (the work breakdown of a specific project).

**Relationship**:
- A scenario may span multiple tracks (e.g., "Bootstrap" track → "Bugfix" track)
- A scenario documents the commands that create/update tracks, phases, tasks
- Scenarios are **meta-level**: they describe how Maestro itself operates

Example:
- **Scenario WF-01**: "How to bootstrap Maestro in an existing repo" (operational workflow)
- **Track `bootstrap`**: "Maestro bootstrap work for Project X" (project work breakdown)

---

## Command Workflows

In addition to scenario workflows, this directory contains **command-specific workflow documentation** that describes the internal implementation and decision flow of individual Maestro commands.

### Purpose

Command workflows differ from scenarios:
- **Scenarios** document complete user journeys (e.g., "bootstrap existing repo")
- **Command workflows** document the internal logic of a single command (e.g., `maestro work`)

### Reactive Patterns

Workflows may include **fast rule-based remediation loops** before deeper analysis. These reactive patterns:
- Match specific error patterns against known solution rules
- Apply immediate fixes when patterns match
- Fall back to normal analysis if solutions fail
- Reduce time-to-first-correct-fix for repeated patterns
- Are implemented in scenarios like WF-04 (Reactive compile error solutions)

### Sessioned Workflows

Some workflows involve **persistent session management** where work spans multiple AI sessions but remains part of a single logical work session. These workflows:

- Maintain persistent context across AI session boundaries
- Track progress through breadcrumb updates
- Support resumption from interruption points
- Preserve audit trails for accountability
- Are implemented in scenarios like WF-06 (AI-driven task execution with Work Sessions and multi-session resume)

### Cross-Repo Workflows

Some workflows involve **operations across two separate repositories** where planning and execution occur in different repositories. These workflows:

- Maintain clear separation between source and target repositories
- Ensure source repository remains pristine during conversion
- Track conversion state and artifacts in both repositories
- Implement safety boundaries to prevent unintended cross-repo modifications
- Are implemented in scenarios like WF-08 (Convert — cross-repo pipeline)

### Format

Each command workflow includes:
- **Markdown documentation** (`command_<name>.md`):
  - Purpose and command syntax
  - Current implementation details (code-based, not aspirational)
  - Decision points and routing logic
  - State transitions and invariants
  - Validation & gating rules
  - Failure modes & recovery
  - Extension points
  - Test mapping
  - Example sessions
- **PlantUML diagram** (`command_<name>.puml`):
  - Command routing (subcommand dispatch)
  - Decision gates and branching logic
  - Engine invocation points
  - Validation steps
  - Error handling paths

### Current Command Workflows

| Command | Documentation | Diagram | Purpose |
|---------|---------------|---------|---------|
| `maestro work` | [command_work.md](command_work.md) | [command_work.puml](command_work.puml) | Work execution interface - select and execute work items (tracks, phases, issues, tasks) |
| `maestro solutions` | [command_solutions.md](command_solutions.md) | [command_solutions.puml](command_solutions.puml) | Solution management - create, list, match, and apply solution rules to issues |
| `maestro tu` | [command_tu.md](command_tu.md) | [command_tu.puml](command_tu.puml) | Translation Unit analysis - AST generation, indexing, refactoring, transformation, and completion |
| `maestro ast` | [command_ast.md](command_ast.md) | [command_ast.puml](command_ast.puml) | AST operations (conceptual, implemented via `maestro tu`) |
| `maestro repo conf` | [command_repo_conf.md](command_repo_conf.md) | [command_repo_conf.puml](command_repo_conf.puml) | Repository build configuration analysis |
| `maestro convert` | [command_convert.md](command_convert.md) | [command_convert.puml](command_convert.puml) | Conversion pipeline — transform code between languages/frameworks with cross-repo support |

### Relationship to Scenarios

Command workflows are referenced by scenarios:
- **Scenario WF-01** uses `maestro init`, `maestro discuss`, `maestro build`, etc.
- **Scenario WF-02** uses `maestro track add`, `maestro phase add`, `maestro task add`, `maestro work task`
- Command workflows document the **internal implementation** of these commands
- Scenarios document the **user-facing journey** that composes multiple commands

---

## How to Add a New Scenario

1. Assign the next ID: `WF-##`
2. Create `scenario_##_short_name.md`:
   - Front-matter metadata
   - Phased flow (Phase 0, 1, 2, ...)
   - Command contracts
   - Test mapping
3. Create `scenario_##_short_name.puml`:
   - Include `_shared.puml`
   - Wrap in `!procedure WF_##()`
   - Define entry/exit points
   - Use swimlanes and gates
4. Update `index.md` with new scenario row
5. Add cross-references from related scenarios (`follow_on_scenarios`)

---

## Versioning and Deprecation

- Scenarios are **append-only**: Once published, a scenario ID is permanent
- To update a scenario: Edit in place with clear changelog notes
- To deprecate a scenario: Add `deprecated: true` to metadata and link to replacement
- Breaking changes: Create a new scenario ID (e.g., `WF-01-v2`) if the flow fundamentally changes

---

## References

- `_shared.puml`: Shared PlantUML macros and styles
- `index.md`: Scenario directory and quick reference
- Project CLAUDE.md: Agent instructions and policy requirements

# Command Trace Glossary: AI Action Keys → CLI Commands → Internal Handlers → Stores

## Purpose

This glossary maps AI action keys (from AI JSON responses) to:

* the **CLI command(s)** Maestro would execute
* the **internal Python entrypoints/handlers** (functions/classes)
* the **stores** read/written (repo truth vs home hub vs IPC)
* the **gates/invariants** relevant to safely applying the action

This serves as the bridge to link AI JSON outputs to internal command flows and to v2 workflow diagrams.

**Note**: This is a spec-in-progress; entries can be `partial`.

**Reference**: WF-09 storage contract (repo truth is JSON under `./docs/maestro/**`)

**Discuss OPS contract**: `docs/workflows/v2/reports/discuss_ops_contract.md` defines the JSON envelope and the rule that OPS must map to action keys in this glossary.

## Store IDs

* `REPO_TRUTH_DOCS_MAESTRO` → `./docs/maestro/**`
* `HOME_HUB_REPO` → `$HOME/.maestro/**/registry`
* `IPC_MAILBOX` → file-based mailbox used by work/wsession (if present)

## Action Table (Top 20)

| Action key | Primary CLI | Primary internal entrypoint | Writes store(s) | Notes / Gates |
|------------|-------------|-----------------------------|-----------------|---------------|
| `wsession.breadcrumb.append` | `maestro wsession breadcrumbs` | `maestro/commands/work_session.py:handle_wsession_breadcrumbs` | `REPO_TRUTH_DOCS_MAESTRO` | `WSESSION_COOKIE_GATE` |
| `wsession.progress.update` | `maestro wsession show` | `maestro/commands/work_session.py:handle_wsession_show` | `REPO_TRUTH_DOCS_MAESTRO` | `WSESSION_COOKIE_GATE` |
| `wsession.note.append` | `maestro wsession show` | `maestro/commands/work_session.py:handle_wsession_show` | `REPO_TRUTH_DOCS_MAESTRO` | `WSESSION_COOKIE_GATE` |
| `issue.create` | `maestro issues` | `maestro/commands/issues.py:handle_issues_command` | `REPO_TRUTH_DOCS_MAESTRO` | `REPOCONF_GATE` |
| `issue.update` | `maestro issues state` | `maestro/commands/issues.py:handle_issues_command` | `REPO_TRUTH_DOCS_MAESTRO` | `REPOCONF_GATE` |
| `issue.link_task` | `maestro issues` | `maestro/commands/issues.py:handle_issues_command` | `REPO_TRUTH_DOCS_MAESTRO` | `REPOCONF_GATE` |
| `task.create` | `maestro task add` | `maestro/commands/task.py:add_task` | `REPO_TRUTH_DOCS_MAESTRO` | `REPOCONF_GATE` |
| `task.update` | `maestro task` | `maestro/commands/task.py:set_task_status` | `REPO_TRUTH_DOCS_MAESTRO` | `REPOCONF_GATE` |
| `task.mark_done` | `maestro task complete` | `maestro/commands/task.py:complete_task` | `REPO_TRUTH_DOCS_MAESTRO` | `REPOCONF_GATE` |
| `phase.create` | `maestro phase add` | `maestro/commands/phase.py:add_phase` | `REPO_TRUTH_DOCS_MAESTRO` | `REPOCONF_GATE` |
| `phase.update` | `maestro phase` | `maestro/commands/phase.py:set_phase_status` | `REPO_TRUTH_DOCS_MAESTRO` | `REPOCONF_GATE` |
| `phase.mark_done` | `maestro phase` | `maestro/commands/phase.py:set_phase_status` | `REPO_TRUTH_DOCS_MAESTRO` | `REPOCONF_GATE` |
| `track.create` | `maestro track add` | `maestro/commands/track.py:add_track` | `REPO_TRUTH_DOCS_MAESTRO` | `REPOCONF_GATE` |
| `track.update` | `maestro track` | `maestro/commands/track.py:set_track_status` | `REPO_TRUTH_DOCS_MAESTRO` | `REPOCONF_GATE` |
| `track.mark_done` | `maestro track` | `maestro/commands/track.py:set_track_status` | `REPO_TRUTH_DOCS_MAESTRO` | `REPOCONF_GATE` |
| `repo.resolve.lite` | `maestro repo resolve` | `maestro/commands/repo.py:handle_repo_resolve` | `REPO_TRUTH_DOCS_MAESTRO` | `REPO_RESOLVE_LITE` |
| `repo.resolve.deep` | `maestro repo resolve --deep` | `maestro/commands/repo.py:handle_repo_resolve` | `REPO_TRUTH_DOCS_MAESTRO` | `REPO_RESOLVE_LITE` |
| `repo.conf.select_default_target` | `maestro repo conf` | `maestro/commands/repo.py:handle_repo_conf` | `REPO_TRUTH_DOCS_MAESTRO` | `REPOCONF_GATE` |
| `build.run` | `maestro make build` | `maestro/commands/make.py:MakeCommand.build` | `REPO_TRUTH_DOCS_MAESTRO` | `READONLY_GUARD` |
| `tu.build_ast` | `maestro tu build` | `maestro/commands/tu.py:handle_tu_build_command` | `HOME_HUB_REPO` | `READONLY_GUARD` |
| `workflow.graph.create` | `maestro workflow init` | `UNKNOWN` | `REPO_TRUTH_DOCS_MAESTRO` | `REPO_TRUTH_IS_DOCS_MAESTRO` |
| `workflow.node.add` | `maestro workflow node add` | `UNKNOWN` | `REPO_TRUTH_DOCS_MAESTRO` | `REPO_TRUTH_FORMAT_IS_JSON` |
| `workflow.edge.add` | `maestro workflow edge add` | `UNKNOWN` | `REPO_TRUTH_DOCS_MAESTRO` | `REPO_TRUTH_FORMAT_IS_JSON` |
| `workflow.export.puml` | `maestro workflow export --format puml` | `UNKNOWN` | `REPO_TRUTH_DOCS_MAESTRO` | `REPO_TRUTH_IS_DOCS_MAESTRO` |
| `workflow.render.svg` | `maestro workflow render --format svg` | `UNKNOWN` | `REPO_TRUTH_DOCS_MAESTRO` | `REPO_TRUTH_IS_DOCS_MAESTRO` |

## Detailed Entries

### wsession.breadcrumb.append

**Action key**: wsession.breadcrumb.append

**Intent**: Add a breadcrumb to the current work session to track progress and decisions made during AI-assisted work

**CLI mapping**: `maestro wsession breadcrumbs <session_id>` or potentially `TODO` for direct append

**Internal mapping**: `maestro/commands/work_session.py:handle_wsession_breadcrumbs` or `UNKNOWN` if direct append function not found

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (docs/sessions/ subdirectory)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (session metadata)

**Gates**: `WSESSION_COOKIE_GATE`

**Failure semantics**: If validation fails, the breadcrumb is not added and the session may be marked as having an error state

**Evidence**: 
- `maestro/commands/work_session.py` - contains breadcrumb handling functions
- `maestro/breadcrumb.py` - contains breadcrumb data structures
- `docs/workflows/v1/internal/cmd_wsession.md` - documents wsession command workflow

### wsession.progress.update

**Action key**: wsession.progress.update

**Intent**: Update the progress status of the current work session

**CLI mapping**: `maestro wsession show <session_id>`

**Internal mapping**: `maestro/commands/work_session.py:handle_wsession_show`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (docs/sessions/ subdirectory)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (session metadata)

**Gates**: `WSESSION_COOKIE_GATE`

**Failure semantics**: If validation fails, the progress update is not applied and the session status remains unchanged

**Evidence**: 
- `maestro/commands/work_session.py` - contains session state management
- `docs/workflows/v1/internal/cmd_wsession.md` - documents wsession command workflow

### wsession.note.append

**Action key**: wsession.note.append

**Intent**: Append a note to the current work session

**CLI mapping**: `maestro wsession show <session_id>` (notes are part of session details)

**Internal mapping**: `maestro/commands/work_session.py:handle_wsession_show`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (docs/sessions/ subdirectory)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (session metadata)

**Gates**: `WSESSION_COOKIE_GATE`

**Failure semantics**: If validation fails, the note is not appended and the session remains unchanged

**Evidence**: 
- `maestro/commands/work_session.py` - contains session state management
- `docs/workflows/v1/internal/cmd_wsession.md` - documents wsession command workflow

### issue.create

**Action key**: issue.create

**Intent**: Create a new issue in the issue tracking system

**CLI mapping**: `maestro issues` (with subcommands for adding issues)

**Internal mapping**: `maestro/commands/issues.py:handle_issues_command`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (docs/issues/ subdirectory)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (issue metadata)

**Gates**: `REPOCONF_GATE`

**Failure semantics**: If validation fails, the issue is not created and an error is returned

**Evidence**: 
- `maestro/commands/issues.py` - contains issue management functions
- `docs/workflows/v1/internal/cmd_issues.md` - documents issues command workflow

### issue.update

**Action key**: issue.update

**Intent**: Update an existing issue's status or metadata

**CLI mapping**: `maestro issues state <issue_id> <state>`

**Internal mapping**: `maestro/commands/issues.py:handle_issues_command`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (docs/issues/ subdirectory)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (issue metadata)

**Gates**: `REPOCONF_GATE`

**Failure semantics**: If validation fails, the issue update is not applied and an error is returned

**Evidence**: 
- `maestro/commands/issues.py` - contains issue management functions
- `docs/workflows/v1/internal/cmd_issues.md` - documents issues command workflow

### issue.link_task

**Action key**: issue.link_task

**Intent**: Link an issue to a specific task

**CLI mapping**: `maestro issues` (with subcommands for linking)

**Internal mapping**: `maestro/commands/issues.py:handle_issues_command`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (docs/issues/ and docs/phases/ subdirectories)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (issue and task metadata)

**Gates**: `REPOCONF_GATE`

**Failure semantics**: If validation fails, the link is not created and an error is returned

**Evidence**: 
- `maestro/commands/issues.py` - contains issue management functions
- `docs/workflows/v1/internal/cmd_issues.md` - documents issues command workflow

### task.create

**Action key**: task.create

**Intent**: Create a new task within a phase

**CLI mapping**: `maestro task add <name> --phase <phase_id>`

**Internal mapping**: `maestro/commands/task.py:add_task`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (docs/phases/ subdirectory, JSON storage)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (phase metadata)

**Gates**: `REPOCONF_GATE`

**Failure semantics**: If validation fails, the task is not created and an error is returned

**Evidence**: 
- `maestro/commands/task.py` - contains task management functions
- `docs/workflows/v1/internal/cmd_task.md` - documents task command workflow

### task.update

**Action key**: task.update

**Intent**: Update a task's status or metadata

**CLI mapping**: `maestro task <task_id> --status <status>`

**Internal mapping**: `maestro/commands/task.py:set_task_status`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (docs/phases/ subdirectory, JSON storage)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (task metadata)

**Gates**: `REPOCONF_GATE`

**Failure semantics**: If validation fails, the task update is not applied and an error is returned

**Evidence**: 
- `maestro/commands/task.py` - contains task management functions
- `docs/workflows/v1/internal/cmd_task.md` - documents task command workflow

### task.mark_done

**Action key**: task.mark_done

**Intent**: Mark a task as completed

**CLI mapping**: `maestro task complete <task_id>`

**Internal mapping**: `maestro/commands/task.py:complete_task`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (docs/phases/ subdirectory, JSON storage)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (task metadata)

**Gates**: `REPOCONF_GATE`

**Failure semantics**: If validation fails, the task status is not changed and an error is returned

**Evidence**: 
- `maestro/commands/task.py` - contains task management functions
- `docs/workflows/v1/internal/cmd_task.md` - documents task command workflow

### phase.create

**Action key**: phase.create

**Intent**: Create a new phase within a track

**CLI mapping**: `maestro phase add <name> --track <track_id>`

**Internal mapping**: `maestro/commands/phase.py:add_phase`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (JSON storage in tracks/phases)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (track metadata)

**Gates**: `REPOCONF_GATE`

**Failure semantics**: If validation fails, the phase is not created and an error is returned

**Evidence**: 
- `maestro/commands/phase.py` - contains phase management functions
- `docs/workflows/v1/internal/cmd_phase.md` - documents phase command workflow (not available, inferred from pattern)

### phase.update

**Action key**: phase.update

**Intent**: Update a phase's status or metadata

**CLI mapping**: `maestro phase <phase_id> --status <status>`

**Internal mapping**: `maestro/commands/phase.py:set_phase_status`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (JSON storage in tracks/phases)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (phase metadata)

**Gates**: `REPOCONF_GATE`

**Failure semantics**: If validation fails, the phase update is not applied and an error is returned

**Evidence**: 
- `maestro/commands/phase.py` - contains phase management functions
- `docs/workflows/v1/internal/cmd_phase.md` - documents phase command workflow (not available, inferred from pattern)

### phase.mark_done

**Action key**: phase.mark_done

**Intent**: Mark a phase as completed

**CLI mapping**: `maestro phase <phase_id> --status done`

**Internal mapping**: `maestro/commands/phase.py:set_phase_status`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (JSON storage in tracks/phases)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (phase metadata)

**Gates**: `REPOCONF_GATE`

**Failure semantics**: If validation fails, the phase status is not changed and an error is returned

**Evidence**: 
- `maestro/commands/phase.py` - contains phase management functions
- `docs/workflows/v1/internal/cmd_phase.md` - documents phase command workflow (not available, inferred from pattern)

### track.create

**Action key**: track.create

**Intent**: Create a new track

**CLI mapping**: `maestro track add <name>`

**Internal mapping**: `maestro/commands/track.py:add_track`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (JSON storage in tracks)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (track metadata)

**Gates**: `REPOCONF_GATE`

**Failure semantics**: If validation fails, the track is not created and an error is returned

**Evidence**: 
- `maestro/commands/track.py` - contains track management functions
- `docs/workflows/v1/internal/cmd_track.md` - documents track command workflow (not available, inferred from pattern)

### track.update

**Action key**: track.update

**Intent**: Update a track's status or metadata

**CLI mapping**: `maestro track <track_id> --status <status>`

**Internal mapping**: `maestro/commands/track.py:set_track_status`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (JSON storage in tracks)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (track metadata)

**Gates**: `REPOCONF_GATE`

**Failure semantics**: If validation fails, the track update is not applied and an error is returned

**Evidence**: 
- `maestro/commands/track.py` - contains track management functions
- `docs/workflows/v1/internal/cmd_track.md` - documents track command workflow (not available, inferred from pattern)

### track.mark_done

**Action key**: track.mark_done

**Intent**: Mark a track as completed

**CLI mapping**: `maestro track <track_id> --status done`

**Internal mapping**: `maestro/commands/track.py:set_track_status`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (JSON storage in tracks)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (track metadata)

**Gates**: `REPOCONF_GATE`

**Failure semantics**: If validation fails, the track status is not changed and an error is returned

**Evidence**: 
- `maestro/commands/track.py` - contains track management functions
- `docs/workflows/v1/internal/cmd_track.md` - documents track command workflow (not available, inferred from pattern)

### repo.resolve.lite

**Action key**: repo.resolve.lite

**Intent**: Perform a lightweight repository resolution to discover basic project structure

**CLI mapping**: `maestro repo resolve`

**Internal mapping**: `maestro/commands/repo.py:handle_repo_resolve` (TODO: exact function name to be confirmed)

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (JSON storage in .maestro/repo/)
- Reads: Repository filesystem structure

**Gates**: `REPO_RESOLVE_LITE`

**Failure semantics**: If validation fails, the resolution process stops and no repository metadata is updated

**Evidence**: 
- `maestro/commands/repo.py` - contains repository analysis functions
- `docs/workflows/v1/internal/cmd_repo.md` - documents repo command workflow

### repo.resolve.deep

**Action key**: repo.resolve.deep

**Intent**: Perform a deep repository resolution to discover detailed project structure, dependencies, and conventions

**CLI mapping**: `maestro repo resolve --deep` (TODO: exact flag to be confirmed)

**Internal mapping**: `maestro/commands/repo.py:handle_repo_resolve` (TODO: exact function name to be confirmed)

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (JSON storage in .maestro/repo/)
- Reads: Repository filesystem structure, configuration files

**Gates**: `REPO_RESOLVE_LITE`

**Failure semantics**: If validation fails, the deep resolution process stops and no detailed repository metadata is updated

**Evidence**: 
- `maestro/commands/repo.py` - contains repository analysis functions
- `docs/workflows/v1/internal/cmd_repo.md` - documents repo command workflow

### repo.conf.select_default_target

**Action key**: repo.conf.select_default_target

**Intent**: Select or configure the default build target for the repository

**CLI mapping**: `maestro repo conf` (TODO: exact subcommand to be confirmed)

**Internal mapping**: `maestro/commands/repo.py:handle_repo_conf` (TODO: exact function name to be confirmed)

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (repo_conf.json)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (repo_model.json)

**Gates**: `REPOCONF_GATE`

**Failure semantics**: If validation fails, the configuration is not changed and an error is returned

**Evidence**: 
- `maestro/commands/repo.py` - contains repository configuration functions
- `docs/workflows/v1/internal/cmd_repo.md` - documents repo command workflow

### build.run

**Action key**: build.run

**Intent**: Execute the build process for the project

**CLI mapping**: `maestro make build`

**Internal mapping**: `maestro/commands/make.py:MakeCommand.build`

**Reads/Writes**: 
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (build logs, status)
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (build configuration)

**Gates**: `READONLY_GUARD`

**Failure semantics**: If validation fails, the build is not executed and an error is returned

**Evidence**: 
- `maestro/commands/make.py` - contains build orchestration functions
- `docs/workflows/v1/internal/cmd_make.md` - documents make command workflow (not available, inferred from pattern)

### tu.build_ast

**Action key**: tu.build_ast

**Intent**: Build the Abstract Syntax Tree (AST) for translation units in the project

**CLI mapping**: `maestro tu build`

**Internal mapping**: `maestro/commands/tu.py:handle_tu_build_command`

**Reads/Writes**: 
- Writes: `HOME_HUB_REPO` (AST cache in .maestro/tu/cache)
- Reads: Source code files

**Gates**: `READONLY_GUARD`

**Failure semantics**: If validation fails, the AST is not built and an error is returned

**Evidence**: 
- `maestro/commands/tu.py` - contains AST building functions
- `docs/workflows/v1/internal/cmd_tu.md` - documents tu command workflow

### workflow.graph.create

**Action key**: workflow.graph.create

**Intent**: Create a new workflow graph in repo truth

**CLI mapping**: `maestro workflow init <name>`

**Internal mapping**: `UNKNOWN`

**Reads/Writes**:
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (docs/maestro/workflows/<name>.json)

**Gates**: `REPO_TRUTH_IS_DOCS_MAESTRO`, `REPO_TRUTH_FORMAT_IS_JSON`

**Failure semantics**: If the graph name is invalid or already exists, the create fails without writing

**Evidence**:
- `docs/workflows/v2/commands/cmd_workflow.md`

### workflow.node.add

**Action key**: workflow.node.add

**Intent**: Add a node to a workflow graph

**CLI mapping**: `maestro workflow node add`

**Internal mapping**: `UNKNOWN`

**Reads/Writes**:
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (docs/maestro/workflows/<name>.json)

**Gates**: `REPO_TRUTH_IS_DOCS_MAESTRO`, `REPO_TRUTH_FORMAT_IS_JSON`

**Failure semantics**: If node IDs collide or layer is invalid, the mutation is rejected

**Evidence**:
- `docs/workflows/v2/commands/cmd_workflow.md`

### workflow.edge.add

**Action key**: workflow.edge.add

**Intent**: Add an edge between nodes in a workflow graph

**CLI mapping**: `maestro workflow edge add`

**Internal mapping**: `UNKNOWN`

**Reads/Writes**:
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (docs/maestro/workflows/<name>.json)

**Gates**: `REPO_TRUTH_IS_DOCS_MAESTRO`, `REPO_TRUTH_FORMAT_IS_JSON`

**Failure semantics**: If nodes are missing or an edge is invalid, the mutation is rejected

**Evidence**:
- `docs/workflows/v2/commands/cmd_workflow.md`

### workflow.export.puml

**Action key**: workflow.export.puml

**Intent**: Export a workflow graph to PlantUML

**CLI mapping**: `maestro workflow export --format puml`

**Internal mapping**: `UNKNOWN`

**Reads/Writes**:
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (workflow graph)
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (PlantUML export)

**Gates**: `REPO_TRUTH_IS_DOCS_MAESTRO`, `REPO_TRUTH_FORMAT_IS_JSON`

**Failure semantics**: If export fails, repo truth JSON remains unchanged

**Evidence**:
- `docs/workflows/v2/commands/cmd_workflow.md`

### workflow.render.svg

**Action key**: workflow.render.svg

**Intent**: Render a PlantUML export to SVG

**CLI mapping**: `maestro workflow render --format svg`

**Internal mapping**: `UNKNOWN`

**Reads/Writes**:
- Reads: `REPO_TRUTH_DOCS_MAESTRO` (PlantUML export)
- Writes: `REPO_TRUTH_DOCS_MAESTRO` (SVG render)

**Gates**: `REPO_TRUTH_IS_DOCS_MAESTRO`

**Failure semantics**: If PlantUML fails, render artifacts are not updated

**Evidence**:
- `docs/workflows/v2/commands/cmd_workflow.md`

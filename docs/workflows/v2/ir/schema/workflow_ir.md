# Maestro Workflow YAML IR Schema

## Overview

This document defines the YAML Intermediate Representation (IR) format for Maestro workflows. The IR is the **source of truth** for v2 workflow specifications, from which all diagrams and documentation are generated.

## Design Principles

1. **Human-editable**: YAML is readable and writable by humans
2. **Machine-parseable**: Structured format enables automated generation
3. **Layer-specific**: Separate files for intent, CLI, code, and observed layers
4. **Evidence-linked**: References to v1 diagrams and source code
5. **Invariant-aware**: Captures architectural constraints

## File Naming Convention

Each workflow is described by **up to 4 YAML files**:

- `WF-XX.intent.yaml` — LOD0: User-facing conceptual flow
- `WF-XX.cli.yaml` — LOD1: CLI command structure
- `WF-XX.code.yaml` — LOD2: Code implementation topology
- `WF-XX.observed.yaml` — (Optional) Observed behavior from v1 internal/deep

Where `XX` is the workflow number (01, 02, ..., 17, or MEGA suffix for composite workflows).

## Top-Level Fields

### Required Fields

```yaml
wf_id: string           # Workflow identifier (e.g., "WF-09")
layer: enum             # LOD level: "intent" | "cli" | "code" | "observed"
title: string           # Human-readable title
status: enum            # Correctness state: "correct" | "incorrect" | "partial" | "ignore"
confidence: enum        # Confidence level: "low" | "medium" | "high"
storage_backend: enum   # "json" | "markdown" | "mixed" | "unknown"
nodes: array            # List of workflow nodes (see below)
edges: array            # List of connections between nodes (see below)
```

### Optional Fields

```yaml
gates: array            # Validation gates (see Gates section)
stores: array           # Data stores (see Stores section)
commands: array         # CLI commands involved (list of strings)
evidence: array         # Paths to supporting files (see Evidence section)
ledger_hints: array     # Notes about spec→code contradictions (list of strings)
invariants: array       # Architectural invariants enforced (see Invariants section)
description: string     # Long-form description (markdown)
```

## Enums

### layer
- `intent`: LOD0, user-facing conceptual flow
- `cli`: LOD1, CLI command structure
- `code`: LOD2, code implementation topology
- `observed`: Extracted from v1 internal/deep (current code behavior)

### status
- `correct`: This workflow accurately represents the intended/implemented behavior
- `incorrect`: This workflow is known to be wrong and needs revision
- `partial`: Parts are correct, parts are incomplete or wrong
- `ignore`: This workflow is deprecated or out of scope

### confidence
- `low`: Speculative or unverified
- `medium`: Partially verified or inferred from code
- `high`: Verified against code and/or user requirements

### storage_backend
- `json`: Persistent data stored in JSON files under `./docs/maestro/`
- `markdown`: Persistent data stored in Markdown files (violates `REPO_TRUTH_FORMAT_IS_JSON`)
- `mixed`: Some JSON, some Markdown (transitional state, should be resolved)
- `unknown`: Storage backend not yet determined

## Nodes

Each node represents a step, decision, gate, or actor in the workflow.

```yaml
nodes:
  - id: string              # Unique identifier (e.g., "start", "gate_repo_conf", "func_load_session")
    type: enum              # Node type (see Node Types)
    label: string           # Display label
    module: string          # (Optional) Python module (e.g., "maestro.modules.command_handlers")
    function: string        # (Optional) Function name (e.g., "handle_repo_conf")
    class: string           # (Optional) Class name (e.g., "Session")
    stereotype: string      # (Optional) PlantUML stereotype (e.g., "<<Function>>", "<<Gate>>")
    color: string           # (Optional) Color code for diagram generation (e.g., "#Red", "#LightGreen")
    description: string     # (Optional) Long-form description
```

### Node Types

#### Intent Layer (LOD0)
- `start`: Workflow entry point
- `end`: Workflow exit point (success or failure)
- `action`: User or system action
- `decision`: Branching point
- `gate`: Validation gate (may block progress)
- `hard_stop`: Fatal error or forbidden operation

#### CLI Layer (LOD1)
- `command`: CLI command invocation
- `subcommand`: Sub-command within a command group
- `argparse`: Argument parsing step
- `validation`: Input validation
- `handler`: Command handler function
- `gate`: Validation gate
- `hard_stop`: Hard stop error

#### Code Layer (LOD2)
- `function`: Python function
- `class`: Python class
- `module`: Python module/package
- `component`: Larger component or subsystem
- `datastore`: Data store (file, directory, database)
- `actor`: External actor (file system, subprocess, user's $EDITOR)
- `gate`: Validation gate
- `hard_stop`: Hard stop error

## Edges

Each edge represents a connection between nodes (control flow, data flow, or call relationship).

```yaml
edges:
  - from: string          # Source node ID
    to: string            # Target node ID
    label: string         # (Optional) Edge label (e.g., "if valid", "calls")
    type: enum            # (Optional) Edge type: "control" | "data" | "call" | "depends"
    condition: string     # (Optional) Condition for this edge (e.g., "if repo_conf.json exists")
```

### Edge Types

- `control`: Control flow (e.g., sequential execution, branching)
- `data`: Data flow (e.g., function returns value)
- `call`: Function/method call
- `depends`: Dependency relationship (e.g., "requires X to have run first")

## Gates

Gates are validation points that may block workflow progress. They enforce invariants and prerequisites.

```yaml
gates:
  - id: string            # Gate identifier (e.g., "gate_repo_conf")
    type: enum            # Gate type (see Gate Types)
    condition: string     # Condition checked by gate
    error_message: string # Error message if gate fails
    recovery: string      # (Optional) Suggested recovery action
```

### Gate Types

- `validation_gate`: General validation (e.g., "file exists", "JSON is valid")
- `hard_stop`: Fatal error, no recovery
- `repo_conf_gate`: Requires `repo_conf.json` to exist and be valid
- `repo_resolve_gate`: Requires `repo_model.json` to exist (from `maestro repo resolve`)
- `wsession_gate`: Requires active work session cookie
- `branch_guard`: Prevents branch switch during work session
- `convention_acceptance_gate`: User must accept detected conventions (WF-10)

## Stores

Data stores are persistent storage locations (files, directories, databases).

```yaml
stores:
  - id: string            # Store identifier (e.g., "repo_truth", "home_hub")
    type: enum            # Store type (see Store Types)
    path: string          # File path or directory (may contain placeholders like <repo_root>)
    format: enum          # "json" | "markdown" | "yaml" | "binary"
    description: string   # (Optional) Store description
```

### Store Types

- `repo_truth`: Repository truth under `./docs/maestro/`
- `home_hub`: Home registry under `~/.maestro/registry/`
- `session_store`: Session data (repo truth or home hub depending on mode)
- `wsession_cookie`: Work session cookie file
- `cache`: Temporary cache (e.g., AST cache, build artifacts)
- `file`: Generic file
- `directory`: Generic directory

## Evidence

Evidence links the IR to supporting files (v1 diagrams, source code, docs).

```yaml
evidence:
  - type: enum            # Evidence type: "v1_diagram" | "source_code" | "documentation"
    path: string          # Path relative to project root
    description: string   # (Optional) What this evidence shows
```

Example:

```yaml
evidence:
  - type: v1_diagram
    path: v1/scenario_09_storage_contract_repo_truth_vs_home_hub.md
    description: Original v1 storage contract workflow
  - type: source_code
    path: maestro/session_model.py
    description: Session model implementation
```

## Invariants

Invariants are architectural constraints enforced by the workflow.

```yaml
invariants:
  - id: string            # Invariant ID (e.g., "FORBID_REPO_DOT_MAESTRO")
    description: string   # Human-readable description
    enforcement: enum     # "gate" | "hard_stop" | "test" | "documentation"
```

### Standard Invariants

The following invariants are commonly used across workflows:

1. **`FORBID_REPO_DOT_MAESTRO`** — `./.maestro` must not exist
2. **`REPO_TRUTH_IS_DOCS_MAESTRO`** — Repository truth is `./docs/maestro/**`
3. **`REPO_TRUTH_FORMAT_IS_JSON`** — Persistent data is JSON, not Markdown
4. **`HOME_HUB_ALLOWED_IN_READONLY`** — Home registry can be used in readonly repos
5. **`REPO_RESOLVE_IS_DETECTION_SPINE`** — Repo resolve is the detection backbone
6. **`REPOCONF_REQUIRED_FOR_BUILD_TU_CONVERT`** — `repo_conf.json` gates build/TU/convert
7. **`BRANCH_SWITCH_FORBIDDEN_DURING_WORK`** — Cannot switch branches during `work` session
8. **`WSESSION_COOKIE_REQUIRED`** — Work sessions require cookie/token mechanism
9. **`WSESSION_IPC_FILE_BASED`** — Work session IPC uses file-based protocol
10. **`CONVENTION_ACCEPTANCE_GATE`** — (WF-10) User accepts detected conventions
11. **`WSESSION_MUTATION_MODE_OPTIN`** — (WF-16) Mutations require explicit opt-in

## Complete Example

See `ir/wf/WF-09.intent.yaml` for a minimal but complete example.

Abbreviated structure:

```yaml
wf_id: WF-09
layer: intent
title: Storage Contract — Repo Truth vs Home Hub
status: correct
confidence: high
storage_backend: json

nodes:
  - id: start
    type: start
    label: User runs Maestro command

  - id: check_repo_truth
    type: decision
    label: Check if ./docs/maestro/ exists

  - id: use_repo_truth
    type: action
    label: Use repo truth storage

  - id: use_home_hub
    type: action
    label: Use home hub storage

  - id: gate_forbid_dot_maestro
    type: hard_stop
    label: Error if ./.maestro exists
    color: "#Red"

  - id: end_success
    type: end
    label: Command executes successfully

edges:
  - from: start
    to: gate_forbid_dot_maestro

  - from: gate_forbid_dot_maestro
    to: check_repo_truth
    label: ./.maestro does not exist

  - from: check_repo_truth
    to: use_repo_truth
    label: ./docs/maestro/ exists

  - from: check_repo_truth
    to: use_home_hub
    label: ./docs/maestro/ does not exist

  - from: use_repo_truth
    to: end_success

  - from: use_home_hub
    to: end_success

gates:
  - id: gate_forbid_dot_maestro
    type: hard_stop
    condition: ./.maestro directory exists
    error_message: "Forbidden: ./.maestro directory detected. Repository truth must be in ./docs/maestro/"
    recovery: "Remove ./.maestro and migrate to ./docs/maestro/"

stores:
  - id: repo_truth
    type: repo_truth
    path: ./docs/maestro/
    format: json
    description: Repository-local truth (repo_model.json, repo_conf.json, etc.)

  - id: home_hub
    type: home_hub
    path: ~/.maestro/registry/
    format: json
    description: Home-level registry for readonly repos or cross-repo data

invariants:
  - id: FORBID_REPO_DOT_MAESTRO
    description: ./.maestro must not exist
    enforcement: hard_stop

  - id: REPO_TRUTH_IS_DOCS_MAESTRO
    description: Repository truth is ./docs/maestro/**
    enforcement: gate

  - id: REPO_TRUTH_FORMAT_IS_JSON
    description: Persistent data is JSON, not Markdown
    enforcement: test

evidence:
  - type: v1_diagram
    path: v1/scenario_09_storage_contract_repo_truth_vs_home_hub.md
    description: Original v1 storage contract workflow

  - type: source_code
    path: maestro/modules/utils.py
    description: Storage backend detection functions
```

## Validation

IR files can be validated using a JSON Schema or custom Python validator (future work).

Minimal validation rules:

1. All required top-level fields present
2. `wf_id` matches filename pattern
3. `layer` is valid enum value
4. All `nodes[].id` are unique within file
5. All `edges[].from` and `edges[].to` reference existing node IDs
6. `storage_backend` is not "markdown" or "mixed" for status "correct" workflows (enforce `REPO_TRUTH_FORMAT_IS_JSON`)

## Generation

Future tooling will generate PlantUML and SVG from IR files:

```bash
# Generate PlantUML from IR
python3 scripts/ir_to_puml.py ir/wf/WF-09.intent.yaml -o generated/puml/WF-09_LOD0.puml

# Generate SVG from PlantUML
plantuml generated/puml/WF-09_LOD0.puml -tsvg -o ../svg/
```

## Extensions

The IR schema can be extended with additional fields as needed:

- **Timing constraints**: SLAs, expected execution time
- **Cost annotations**: Computational cost estimates
- **Security notes**: Authentication/authorization requirements
- **Migration paths**: How to transition from v1 to v2

---

**Version**: 1.0
**Last Updated**: 2025-12-26

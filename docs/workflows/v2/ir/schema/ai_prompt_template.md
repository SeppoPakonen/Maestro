# AI Extraction Prompt Template for YAML IR

## Instructions for AI Agent

You are tasked with extracting structured workflow information from Maestro v1 documentation and converting it to **strict YAML format** following the Maestro Workflow IR Schema.

**CRITICAL RULES:**

1. **Output YAML ONLY** — No prose, no explanations, no markdown blocks. Pure YAML starting with `wf_id:`.
2. **Follow the schema exactly** — See `workflow_ir.md` for complete specification.
3. **Detect storage backend** — Look for mentions of `DataMarkdown`, `*.md files`, JSON persistence, etc.
4. **Generate ledger hints** — When you detect contradictions between observed behavior and expected spec, emit ledger hints.

---

## Required Fields

```yaml
wf_id: string           # e.g., "WF-09"
layer: enum             # "intent" | "cli" | "code" | "observed"
title: string           # Human-readable title
status: enum            # "correct" | "incorrect" | "partial" | "ignore"
confidence: enum        # "low" | "medium" | "high"
storage_backend: enum   # "json" | "markdown" | "mixed" | "unknown"
nodes: array            # List of workflow nodes (see below)
edges: array            # List of connections between nodes
```

## Optional Fields

```yaml
gates: array            # Validation gates
stores: array           # Data stores
commands: array         # CLI commands involved
evidence: array         # Paths to supporting files
ledger_hints: array     # Spec→code contradictions (list of strings)
invariants: array       # Architectural invariants enforced
description: string     # Long-form description (markdown)
```

---

## Node Structure

Nodes represent steps, decisions, gates, or actors in the workflow.

```yaml
nodes:
  - id: string              # Unique identifier (e.g., "start", "gate_repo_conf")
    type: enum              # Node type (see Node Types below)
    label: string           # Display label
    module: string          # (Optional) Python module
    function: string        # (Optional) Function name
    class: string           # (Optional) Class name
    stereotype: string      # (Optional) PlantUML stereotype
    color: string           # (Optional) Color code (e.g., "#Red")
    description: string     # (Optional) Long-form description
```

### Node Types by Layer

**Intent Layer (LOD0):**
- `start` — Workflow entry point
- `end` — Workflow exit point
- `action` — User or system action
- `decision` — Branching point
- `gate` — Validation gate
- `hard_stop` — Fatal error

**CLI Layer (LOD1):**
- `command` — CLI command invocation
- `subcommand` — Sub-command
- `argparse` — Argument parsing
- `validation` — Input validation
- `handler` — Command handler function
- `gate` — Validation gate
- `hard_stop` — Hard stop error

**Code Layer (LOD2):**
- `function` — Python function
- `class` — Python class
- `module` — Python module/package
- `component` — Larger component or subsystem
- `datastore` — Data store (file, directory, database)
- `actor` — External actor (file system, subprocess, $EDITOR)
- `gate` — Validation gate
- `hard_stop` — Hard stop error

---

## Edge Structure

Edges represent connections between nodes.

```yaml
edges:
  - from: string          # Source node ID
    to: string            # Target node ID
    label: string         # (Optional) Edge label
    type: enum            # (Optional) "control" | "data" | "call" | "depends"
    condition: string     # (Optional) Condition for this edge
```

---

## Gates

Gates are validation points that may block workflow progress.

```yaml
gates:
  - id: string            # Gate identifier (e.g., "gate_repo_conf")
    type: enum            # "validation_gate" | "hard_stop" | "repo_conf_gate" | etc.
    condition: string     # Condition checked by gate
    error_message: string # Error message if gate fails
    recovery: string      # (Optional) Suggested recovery action
```

### Standard Gate Types

- `validation_gate` — General validation
- `hard_stop` — Fatal error, no recovery
- `repo_conf_gate` — Requires `repo_conf.json`
- `repo_resolve_gate` — Requires `repo_model.json`
- `wsession_gate` — Requires active work session cookie
- `branch_guard` — Prevents branch switch during work session
- `convention_acceptance_gate` — User must accept detected conventions

---

## Stores

Data stores are persistent storage locations.

```yaml
stores:
  - id: string            # Store identifier (e.g., "repo_truth")
    type: enum            # Store type (see Store Types below)
    path: string          # File path or directory
    format: enum          # "json" | "markdown" | "yaml" | "binary"
    description: string   # (Optional) Store description
```

### Standard Store Types

- `repo_truth` — Repository truth under `./docs/maestro/`
- `home_hub` — Home registry under `~/.maestro/registry/`
- `session_store` — Session data
- `wsession_cookie` — Work session cookie file
- `cache` — Temporary cache
- `file` — Generic file
- `directory` — Generic directory

---

## Evidence

Evidence links the IR to supporting files.

```yaml
evidence:
  - type: enum            # "v1_diagram" | "source_code" | "documentation"
    path: string          # Path relative to project root
    description: string   # (Optional) What this evidence shows
```

---

## Invariants

Invariants are architectural constraints enforced by the workflow.

```yaml
invariants:
  - id: string            # Invariant ID (e.g., "FORBID_REPO_DOT_MAESTRO")
    description: string   # Human-readable description
    enforcement: enum     # "gate" | "hard_stop" | "test" | "documentation"
```

### Standard Invariants

1. `FORBID_REPO_DOT_MAESTRO` — `./.maestro` must not exist
2. `REPO_TRUTH_IS_DOCS_MAESTRO` — Repository truth is `./docs/maestro/**`
3. `REPO_TRUTH_FORMAT_IS_JSON` — Persistent data is JSON, not Markdown
4. `HOME_HUB_ALLOWED_IN_READONLY` — Home registry can be used in readonly repos
5. `REPO_RESOLVE_IS_DETECTION_SPINE` — Repo resolve is the detection backbone
6. `REPOCONF_REQUIRED_FOR_BUILD_TU_CONVERT` — `repo_conf.json` gates build/TU/convert
7. `BRANCH_SWITCH_FORBIDDEN_DURING_WORK` — Cannot switch branches during `work` session
8. `WSESSION_COOKIE_REQUIRED` — Work sessions require cookie/token mechanism
9. `WSESSION_IPC_FILE_BASED` — Work session IPC uses file-based protocol
10. `CONVENTION_ACCEPTANCE_GATE` — User accepts detected conventions
11. `WSESSION_MUTATION_MODE_OPTIN` — Mutations require explicit opt-in

---

## Status Detection Rules

Based on the input documentation, assign one of these statuses:

- **`correct`** — Workflow accurately represents intended/implemented behavior
- **`incorrect`** — Workflow is known to be wrong and needs revision
- **`partial`** — Parts are correct, parts are incomplete or wrong
- **`ignore`** — Workflow is deprecated or out of scope

### Guidelines

- If v1 diagram shows clear, complete flow with no obvious errors → `correct`
- If v1 diagram contradicts source code or has missing steps → `incorrect` or `partial`
- If v1 diagram is marked "WIP" or "draft" → `partial`
- If workflow is superseded or marked deprecated → `ignore`

---

## Confidence Detection Rules

Based on the quality and completeness of input documentation:

- **`low`** — Speculative or unverified; minimal documentation
- **`medium`** — Partially verified or inferred from code
- **`high`** — Verified against code and/or user requirements; complete documentation

### Guidelines

- If v1 has both diagram + internal/deep + source code references → `high`
- If v1 has diagram only, no code verification → `medium`
- If v1 is incomplete or marked as draft → `low`

---

## Storage Backend Detection Rules

**CRITICAL:** Maestro v2 spec mandates **JSON-only storage** in `./docs/maestro/**`.

Look for these indicators in v1 documentation:

### Indicates `json`
- Mentions of `repo_model.json`, `repo_conf.json`, `tasks.json`, `issues.json`
- References to `./docs/maestro/` directory
- Code snippets showing `json.load()`, `json.dump()`

### Indicates `markdown`
- Mentions of `DataMarkdown`, `*.md files` for persistence
- References to `.maestro/*.md` (forbidden pattern)
- Code snippets showing markdown file writes for data storage

### Indicates `mixed`
- Both JSON and Markdown mentioned as storage formats
- Transitional state documentation

### Indicates `unknown`
- No clear storage backend mentioned
- Workflow doesn't involve persistence

**IMPORTANT:** If you detect `markdown` or `mixed` storage backend, you MUST add a ledger hint.

---

## Ledger Hints — Contradiction Detection

When you detect contradictions between v1 observed behavior and v2 spec, emit ledger hints.

### Example Contradictions

1. **Storage backend mismatch:**
   - v1 mentions `DataMarkdown` or `*.md` for persistence
   - v2 spec requires JSON
   - **Emit:** `"Observed DataMarkdown usage in v1; violates REPO_TRUTH_FORMAT_IS_JSON invariant; replace with JSON"`

2. **Forbidden ./.maestro directory:**
   - v1 shows `./.maestro` directory usage
   - v2 forbids this (must be `./docs/maestro/`)
   - **Emit:** `"Observed ./.maestro directory in v1; violates FORBID_REPO_DOT_MAESTRO invariant; migrate to ./docs/maestro/"`

3. **Missing repo_conf gate:**
   - v1 shows `maestro build` running without `repo_conf.json`
   - v2 requires `repo_conf.json` to exist (WF-12)
   - **Emit:** `"Build command in v1 lacks repo_conf gate; violates REPOCONF_REQUIRED_FOR_BUILD_TU_CONVERT"`

4. **Branch switching during work:**
   - v1 allows git branch operations during work sessions
   - v2 forbids branch switching (WF-14)
   - **Emit:** `"No branch safety check in v1; violates BRANCH_SWITCH_FORBIDDEN_DURING_WORK"`

### Ledger Hint Format

```yaml
ledger_hints:
  - "Brief description of contradiction; invariant violated; suggested fix"
  - "Another contradiction if present"
```

---

## Extraction Task Specification

You will be given one or more v1 files:

1. **Intent layer:** `v1/scenario_XX_title.md` and `v1/scenario_XX_title.puml`
2. **CLI layer:** `v1/command_surface/cmd_*.md`
3. **Code layer:** `v1/internal/deep/cmd_*_deep.puml` or module documentation
4. **Observed layer:** `v1/internal/deep/cmd_*_deep.puml`

Your task:

1. **Identify the workflow ID** (WF-XX) from filename or content
2. **Determine the layer** (intent, cli, code, observed) based on which file you're processing
3. **Extract nodes and edges** from diagrams and prose
4. **Detect storage backend** using rules above
5. **Assign status and confidence** using rules above
6. **Generate ledger hints** for any contradictions
7. **Output strict YAML** with no additional commentary

---

## Example Output

```yaml
wf_id: WF-09
layer: intent
title: Storage Contract — Repo Truth vs Home Hub
status: correct
confidence: high
storage_backend: json

description: |
  This workflow defines the storage contract for Maestro. Persistent project data
  is stored in JSON format under ./docs/maestro/ (repo truth) or ~/.maestro/registry/
  (home hub) for readonly repos.

nodes:
  - id: start
    type: start
    label: User runs Maestro command

  - id: gate_forbid_dot_maestro
    type: hard_stop
    label: Hard Stop if ./.maestro exists
    color: "#Red"

  - id: check_repo_truth
    type: decision
    label: Check if ./docs/maestro/ exists

  - id: use_repo_truth
    type: action
    label: Use Repo Truth Storage

  - id: use_home_hub
    type: action
    label: Use Home Hub Storage

  - id: end_success
    type: end
    label: Command executes successfully

edges:
  - from: start
    to: gate_forbid_dot_maestro
    type: control

  - from: gate_forbid_dot_maestro
    to: check_repo_truth
    label: ./.maestro does not exist
    type: control

  - from: check_repo_truth
    to: use_repo_truth
    label: ./docs/maestro/ exists
    type: control

  - from: check_repo_truth
    to: use_home_hub
    label: ./docs/maestro/ does not exist
    type: control

  - from: use_repo_truth
    to: end_success
    type: control

  - from: use_home_hub
    to: end_success
    type: control

gates:
  - id: gate_forbid_dot_maestro
    type: hard_stop
    condition: ./.maestro directory exists
    error_message: "FORBIDDEN: ./.maestro directory detected. Use ./docs/maestro/"
    recovery: "Remove ./.maestro and run maestro repo adopt"

stores:
  - id: repo_truth
    type: repo_truth
    path: ./docs/maestro/
    format: json

  - id: home_hub
    type: home_hub
    path: ~/.maestro/registry/
    format: json

invariants:
  - id: FORBID_REPO_DOT_MAESTRO
    description: ./.maestro must not exist
    enforcement: hard_stop

  - id: REPO_TRUTH_FORMAT_IS_JSON
    description: Persistent data is JSON, not Markdown
    enforcement: test

evidence:
  - type: v1_diagram
    path: v1/scenario_09_storage_contract_repo_truth_vs_home_hub.md

commands:
  - maestro repo adopt
  - maestro repo resolve
  - maestro build

ledger_hints: []
```

---

## Final Reminder

**OUTPUT YAML ONLY.** No explanations, no markdown fences, no commentary. Just valid YAML starting with `wf_id:`.

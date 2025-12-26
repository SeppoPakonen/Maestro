# Maestro Workflows v2 — Canonical Specification Pipeline

## Overview

This directory contains the **v2 canonical specification** for Maestro workflows. Unlike v1, which was primarily documentation-as-diagrams, v2 is **source-of-truth driven** with structured YAML as the Intermediate Representation (IR).

### v1 vs v2

#### v1 (Archive)
- **Location**: `docs/workflows/v1/`
- **Status**: Legacy archive (frozen)
- **Content**:
  - Original workflow diagrams (PlantUML)
  - `internal/deep/` subdirectory containing observed current code topology
  - Mixed correctness states (some diagrams correct, some incorrect, some partial)
- **Purpose**: Historical reference and evidence base for v2

#### v2 (Canonical Specification)
- **Location**: `docs/workflows/v2/`
- **Status**: Active specification pipeline (in progress)
- **Content**:
  - YAML IR files (source of truth)
  - Generated diagrams (PlantUML → SVG)
  - Implementation ledger tracking spec→code deltas
  - Reports and analysis
- **Purpose**: Define and maintain the canonical workflow specification

## Philosophy

### Structured Data as Source of Truth

**v2 principle**: The IR (YAML) is the single source of truth. All diagrams and documentation are **generated** from the IR.

- YAML IR files are human-editable and machine-readable
- PlantUML/SVG generation is automated from IR
- Changes to workflows flow: IR edit → regenerate diagrams → review → commit

### Storage Backend Reality

**Critical invariant**: Persistent project data in Maestro is **JSON**, not Markdown.

Repository truth is stored under `./docs/maestro/**` in JSON format:
- `repo_model.json` — repository structure and metadata
- `repo_conf.json` — configuration and conventions
- `packages.json` — package definitions
- `tasks.json`, `issues.json` — task and issue tracking

**Forbidden**: `./.maestro` directory must not exist (hard stop).

### Level of Detail (LOD) Strategy

v2 supports **multiple representations at different detail levels**:

- **LOD0**: Intent/conceptual layer (user-facing workflow)
- **LOD1**: CLI command layer (argparse, handlers, validation gates)
- **LOD2**: Code implementation layer (functions, classes, modules, data stores)

For each workflow, we generate **multiple SVG variants** so different audiences can consume appropriate detail:
- `WF-XX_LOD0.svg` — conceptual flow
- `WF-XX_LOD1.svg` — CLI command flow
- `WF-XX_LOD2.svg` — code implementation flow

This prevents the "forgotten detail" problem where important implementation details are lost.

### Implementation Ledger

The `IMPLEMENTATION_LEDGER.md` tracks **spec→code deltas**:
- What the spec says SHOULD happen
- What the code (v1 internal/deep) DOES happen
- Required code changes to align with spec
- Status tracking (proposed, accepted, implemented, verified)

This ensures v2 is not just aspirational documentation but a living contract between specification and implementation.

## Directory Structure

```
v2/
├── README.md                    # This file
├── index.md                     # Workflow catalog (WF-01..WF-17, MEGA workflows)
├── IMPLEMENTATION_LEDGER.md     # Spec→code delta tracking
├── ir/
│   ├── schema/
│   │   └── workflow_ir.md       # YAML IR schema definition
│   └── wf/
│       ├── WF-01.intent.yaml    # LOD0: Intent layer
│       ├── WF-01.cli.yaml       # LOD1: CLI layer
│       ├── WF-01.code.yaml      # LOD2: Code layer
│       ├── WF-01.observed.yaml  # Optional: v1 internal/deep extraction
│       └── ...
├── generated/
│   ├── puml/                    # Generated PlantUML files
│   └── svg/                     # Generated SVG diagrams
└── reports/                     # Analysis reports
```

## YAML IR Files

Each workflow is described by **up to 4 YAML files**:

1. **`WF-XX.intent.yaml`** — LOD0: User-facing conceptual flow
2. **`WF-XX.cli.yaml`** — LOD1: CLI command structure
3. **`WF-XX.code.yaml`** — LOD2: Code implementation topology
4. **`WF-XX.observed.yaml`** — (Optional) Observed behavior from v1 internal/deep

Required fields in all IR files:
- `wf_id`: Workflow identifier (e.g., "WF-09")
- `layer`: LOD level (intent|cli|code|observed)
- `title`: Human-readable title
- `status`: Correctness state (correct|incorrect|partial|ignore)
- `confidence`: Confidence level (low|medium|high)
- `storage_backend`: json|markdown|mixed|unknown (CRITICAL for storage contract)
- `nodes`: List of workflow nodes
- `edges`: List of connections
- `gates`: Validation gates (enum)
- `stores`: Data stores (enum)
- `commands`: CLI commands involved
- `evidence`: Paths to v1 files supporting this workflow
- `ledger_hints`: (Optional) Notes about spec→code contradictions

See `ir/schema/workflow_ir.md` for full schema specification.

## Invariants Enforced

The following architectural invariants are baked into v2 IR:

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

These invariants appear in IR files as validation gates, hard stops, or data store constraints.

## Workflow Catalog

See `index.md` for the complete list of workflows (WF-01 through WF-17, plus MEGA workflows).

## Generation Pipeline

**Future**: Automated generation from IR to diagrams:

```bash
# Generate PlantUML from IR
python3 scripts/ir_to_puml.py ir/wf/WF-09.intent.yaml -o generated/puml/WF-09_LOD0.puml

# Generate SVG from PlantUML
plantuml generated/puml/WF-09_LOD0.puml -tsvg -o ../svg/
```

For now, diagrams are manually created but should follow the IR structure.

## Contributing

When adding or modifying workflows:

1. **Edit the IR** — Update or create YAML files in `ir/wf/`
2. **Update the ledger** — Add spec→code delta entries to `IMPLEMENTATION_LEDGER.md`
3. **Regenerate diagrams** — (Manual for now) Create corresponding PlantUML/SVG
4. **Verify invariants** — Ensure all architectural invariants are respected
5. **Commit** — Include IR, diagrams, and ledger updates in a single commit

## License

Same as parent Maestro project.

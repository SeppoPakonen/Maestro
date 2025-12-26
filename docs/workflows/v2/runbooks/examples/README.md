# Maestro Runbook Examples

This directory contains **walkable narrative examples** demonstrating Maestro workflows across different project types, build systems, and usage scenarios.

## Purpose

Runbook examples serve as:

1. **Canonical usage stories**: Realistic end-to-end scenarios showing how users interact with Maestro
2. **CLI alignment material**: Feed into command surface design by exposing gaps and uncertainties
3. **Acceptance test templates**: Proposed examples can become acceptance tests once CLI is finalized
4. **Ledger triggers**: Validated examples enter the ledger and drive v3 iterations

## Directory Structure

```
examples/
├── README.md           # This file
├── proposed/           # New examples awaiting review and validation
│   ├── EX-*.md        # Markdown narrative with minimal code, AI perspective
│   └── EX-*.sh        # Shell script mirror with dry-run helpers
└── approved/           # Validated examples (CLI confirmed, ledger entries exist)
    ├── EX-*.md
    └── EX-*.sh
```

## Lifecycle: Proposed → Approved

### Proposed Examples

Located in `proposed/`, these examples:

- May contain **TODO_CMD markers** where exact command syntax is uncertain
- Include **heuristic AI perspective** (what AI likely thinks/does, not guaranteed exact behavior)
- Use **minimal code snippets** (inline, tiny) just enough to convey build system/repo type
- Define **explicit outcomes** with success/failure branches
- Include **trace YAML blocks** for future automation

### Approval Criteria

An example moves to `approved/` when:

1. CLI commands are validated (either implemented or officially spec'd)
2. Gates and stores are confirmed in the architecture
3. Acceptance test can be automated (or manually validated)
4. Ledger entry created documenting the workflow pattern

### TODO Command Markers

Examples use consistent markers for uncertain CLI:

```bash
# Known command (from current maestro)
maestro init

# Uncertain syntax - marked with TODO_CMD
# TODO_CMD: maestro repo config --show
run maestro repo config --show

# Completely unknown command - explicit TODO
# TODO: Determine correct command for convention validation
# run maestro [unknown]
```

In shell scripts, use inline comments:
```bash
run maestro build  # TODO_CMD: confirm if 'build' vs 'make'
```

## Example Format (Mandatory Sections)

Each `.md` example must include:

1. **Title + Scope** (EX-##: descriptive title)
2. **Scenario Summary** (2-3 sentences)
3. **Minimal Project Skeleton** (inline code blocks, keep tiny)
4. **Runbook Steps** (table format):
   - Step number
   - Command
   - Intent
   - Expected outcome
   - Gates passed
   - Stores written
5. **AI Perspective (Heuristic)**:
   - Bullet list: "What AI likely notices" + "What it tries next"
   - Labeled as heuristic approximation, not exact
6. **Outcomes** (at least 2 branches: success path, failure/alternate path)
7. **CLI Gaps / TODOs** (list every uncertain command with marker)
8. **Trace Block (YAML)** for automation:
   ```yaml
   trace:
     - user: "maestro init"
       intent: "Initialize maestro in existing repo"
       gates: ["REPOCONF_GATE"]
       stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
       internal: ["UNKNOWN"]
       cli_confidence: "high"
   ```

Each `.sh` file must:

- Use `run()` helper for dry-run (`run() { echo "+ $*"; }`)
- Include EXPECT, STORES_WRITE/READ, GATES, INTERNAL comments
- Mirror the command sequence from the `.md`
- Use TODO_CMD comments consistently

## Storage Conventions

Examples must respect Maestro storage architecture:

- **Repo truth**: `./docs/maestro/**` (JSON authoritative)
  - Never mention `./.maestro` (old convention)
- **Home hub/cache**: `$HOME/.maestro/**/repo` (read-only caches, hub metadata)
- **IPC mailbox**: `$HOME/.maestro/ipc/<session-id>/` (temp inter-process communication)

## Standard Store IDs

Use these consistent identifiers in trace blocks and comments:

- `REPO_TRUTH_DOCS_MAESTRO`: `./docs/maestro/**` JSON files
- `HOME_HUB_REPO`: `$HOME/.maestro/hub/repo/<repo-id>/`
- `IPC_MAILBOX`: `$HOME/.maestro/ipc/<session>/`

## Example Scope Coverage

Current proposed examples:

**Build System Integration (EX-01..EX-04)**:
- **EX-01**: C++ CMake existing repo, adopt → resolve → build → reactive error → solution
- **EX-02**: Rust Cargo greenfield, workflow-first → skeleton → build → work session
- **EX-03**: Python Poetry read-only inspection, no repo writes
- **EX-04**: Ultimate++ packages → deep resolve → convention detection → issues

**Runbook→Workflow→Plan Complete Cycles (EX-09..EX-12)**:
- **EX-09**: Python CLI Hello tool — runbook-first → workflow extraction → track/phase/task → implemented argparse code
- **EX-10**: C++ single-file + Makefile — runbook → workflow → build system detection → compile error → solution match → recovery
- **EX-11**: GUI menu modeling (no code) — runbook → workflow interface layer → demonstrates modeling before implementation
- **EX-12**: Text adventure game loop — runbook → workflow (interface=game loop) → minimal playable Python game

Future examples may cover:

- AI/discuss pipeline decomposition (EX-05..EX-08 planned)
- Multi-repo orchestration
- CI/CD integration scenarios
- Migration from other build systems
- Large-scale monorepo patterns

## Acceptance and Ledger Integration

Once an example is **approved**:

1. Create ledger entry: `docs/ledger/v2/accepted/<EX-##>.md`
2. Link to workflow diagrams (if applicable)
3. Tag commits that implement the commands
4. Reference in v3 planning

## Quality Bar

- **Readability**: ~80-160 lines per `.md` max
- **Minimal code**: Only what's necessary to convey build system/repo type
- **No overclaiming**: Flag all uncertain CLI with TODO markers
- **No sudo**: Examples never use sudo in shell snippets
- **Explicit unknowns**: INTERNAL: UNKNOWN rather than guessing implementation

## Contributing

To propose a new example:

1. Create `EX-##_short_title.md` and `EX-##_short_title.sh` in `proposed/`
2. Follow the mandatory format (see above)
3. Use TODO_CMD markers liberally for uncertain syntax
4. Include AI perspective as heuristic bullets
5. Define at least 2 outcome branches
6. Submit PR with label `runbook-example`

Examples will be reviewed for:

- Scenario realism and value
- Completeness of sections
- Appropriate use of TODO markers
- Alignment with Maestro architecture (gates, stores)

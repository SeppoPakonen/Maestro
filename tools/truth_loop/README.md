# Truth Loop - CLI Surface and Runbook Alignment

This toolset implements a "truth loop" to continuously align:

1. **Runbook Truth** - What commands runbooks actually use
2. **CLI Surface Truth** - What the CLI actually exposes
3. **Canonical Standards** - What we want to standardize (keyword-first, canonical verbs)

## Modules

### `normalize.py`

Command normalization module that canonicalizes command strings from various sources.

**Features:**
- Strips wrappers: `MAESTRO_BIN=...`, `./maestro.py`, `python -m maestro`, etc.
- Normalizes verb aliases: `build → make`, `ls → list`, `sh → show`, `new → add`
- Applies special normalization rules: `--level deep → refresh all`
- Extracts signatures with flag placeholders: `--reason <ARG>`

**Usage:**
```python
from tools.truth_loop.normalize import normalize_command

normalized, tokens, signature = normalize_command("maestro build default")
# normalized: "make default"
# tokens: ["make", "default"]
# signature: "make default"
```

### `extract_cli_surface.py`

CLI surface extractor that walks the argparse tree and emits all reachable commands.

**Outputs:**
- `docs/workflows/v3/reports/cli_surface.default.json` - JSON format
- `docs/workflows/v3/reports/cli_surface.default.txt` - One command per line
- `docs/workflows/v3/reports/cli_surface.legacy.json` - With legacy commands enabled
- `docs/workflows/v3/reports/cli_surface.legacy.txt`

**Usage:**
```bash
python tools/truth_loop/extract_cli_surface.py
```

### `extract_runbook_commands.py`

Runbook command extractor that scans example runbooks and extracts actual command usage.

**Scans:**
- `docs/workflows/v3/runbooks/examples/input_from_v2_proposed/**/*.sh`
- `docs/workflows/v3/runbooks/examples/proposed/**/*.sh`

**Outputs:**
- `docs/workflows/v3/reports/runbook_commands.raw.txt` - Raw extracted commands
- `docs/workflows/v3/reports/runbook_commands.normalized.txt` - Normalized commands
- `docs/workflows/v3/reports/runbook_commands.freq.csv` - Frequency analysis

**Usage:**
```bash
python tools/truth_loop/extract_runbook_commands.py
```

### `compare.py`

Truth loop comparator that diffs runbook commands vs CLI surface.

**Inputs:**
- `runbook_commands.normalized.txt`
- `cli_surface.default.txt`
- Legacy mapping from `docs/workflows/v3/cli/LEGACY_MAPPING.md`

**Outputs:**
- `docs/workflows/v3/reports/truth_loop_diff.md` - Human-readable diff report
- `docs/workflows/v3/reports/truth_loop_diff.json` - Machine-readable diff

**Report Sections:**
1. Summary counts
2. Runbook-only commands
3. CLI-only commands
4. Alias coverage status
5. Suggested runbook additions
6. Suggested CLI changes
7. Debt table (TODO_CMD, deprecated usage)

**Usage:**
```bash
python tools/truth_loop/compare.py
```

### `snippet.py`

Runbook snippet emitter that generates runbook-ready code blocks.

**Usage:**
```bash
# Generate snippet for a specific command
python tools/truth_loop/snippet.py "repo resolve"

# Generate snippets for all commands missing examples
python tools/truth_loop/snippet.py --all-missing-examples
```

**Output Format:**
```bash
run maestro repo resolve
# EXPECT: <description>
# STORES: <store names>
# GATES: <gate names>
# NOTES: <TODOs if ambiguous>
```

### `suggest_next.py`

Command suggestion tool for runbook authoring and gap analysis.

**Usage:**
```bash
# Suggest next commands after a specific command
python tools/truth_loop/suggest_next.py "repo resolve"

# Analyze a runbook file and suggest next commands
python tools/truth_loop/suggest_next.py --file docs/workflows/v3/runbooks/examples/proposed/EX-01.sh
```

**Features:**
- Adjacency heuristics based on common command sequences
- Prerequisite gate checking
- Top 5 next command suggestions

## Report Categories

The truth loop uses the following categories for analysis:

- **both_ok** - Command appears in both runbooks and CLI surface (aligned)
- **runbook_only** - Command appears in runbooks but not in CLI surface (needs implementation)
- **cli_only** - Command appears in CLI surface but not in runbooks (needs examples)
- **needs_alias** - Command used in runbooks via alias (verify alias exists)
- **needs_docs** - CLI exists but runbooks missing examples
- **needs_runbook_fix** - Runbooks reference TODO_CMD or deprecated forms

## Workflow

### Full Truth Loop Cycle

```bash
# 1. Extract CLI surface
python tools/truth_loop/extract_cli_surface.py

# 2. Extract runbook commands
python tools/truth_loop/extract_runbook_commands.py

# 3. Compare and generate diff report
python tools/truth_loop/compare.py

# 4. Review diff report
cat docs/workflows/v3/reports/truth_loop_diff.md

# 5. Generate snippets for missing examples
python tools/truth_loop/snippet.py --all-missing-examples > new_examples.sh

# 6. Verify determinism (should produce no diff)
python tools/truth_loop/compare.py
git diff docs/workflows/v3/reports/truth_loop_diff.md
```

### Continuous Integration

The truth loop can be integrated into CI to ensure CLI and runbooks stay aligned:

```bash
# In CI pipeline
python tools/truth_loop/extract_cli_surface.py
python tools/truth_loop/extract_runbook_commands.py
python tools/truth_loop/compare.py

# Check for drift
if [ -n "$(git diff docs/workflows/v3/reports/truth_loop_diff.md)" ]; then
    echo "ERROR: Truth loop drift detected!"
    exit 1
fi
```

## Design Principles

1. **Deterministic** - Same inputs always produce same outputs
2. **Normalization-first** - All commands normalized before comparison
3. **Respect kill-switch** - Default mode excludes legacy commands (MAESTRO_ENABLE_LEGACY=0)
4. **No web dependencies** - Purely local filesystem scanning
5. **Minimal parsing** - Pragmatic extraction, not full AST analysis
6. **Reviewable** - Human-readable reports with clear action items

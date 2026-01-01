# maestro plan decompose

Decompose freeform requests into structured WorkGraph plans with verifiable Definitions-of-Done (DoD).

## Overview

The `maestro plan decompose` command uses AI to convert a freeform natural language request into a structured WorkGraph JSON artifact. This artifact contains:

- **Tracks**: High-level work streams
- **Phases**: Logical groupings of tasks within a track
- **Tasks**: Individual units of work with machine-verifiable DoDs
- **Stop Conditions**: Gates for handling blockers

This is v1 (decomposition only) - execution/apply functionality comes in a later sprint.

## Usage

```bash
maestro plan decompose [OPTIONS] <freeform>
maestro plan decompose -e [OPTIONS]  # Read from stdin
```

### Arguments

- `<freeform>` - Freeform request text (optional if using `-e`)

### Options

- `-e`, `--eval` - Read freeform input from stdin instead of argument
- `--engine ENGINE` - AI engine to use (default: planner role engine)
- `--profile PROFILE` - Planning profile: `default`, `investor`, or `purpose` (default: `default`)
- `--domain DOMAIN` - Domain for decomposition: `runbook`, `issues`, `workflow`, `convert`, `repo`, or `general` (default: `general`)
- `--json` - Output full WorkGraph JSON to stdout
- `--out PATH` - Write WorkGraph JSON to custom path (default: `docs/maestro/plans/workgraphs/{id}.json`)
- `-v`, `--verbose` - Show evidence summary, engine, and validation summary
- `-vv`, `--very-verbose` - Also print AI prompt and response

## Examples

### Basic Decomposition

```bash
maestro plan decompose "Add user authentication to the app"
```

Output:
```
WorkGraph created: wg-20260101-a3f5b8c2
Domain: general
Profile: default
Track: User Authentication
Phases: 2
Tasks: 5
Saved to: docs/maestro/plans/workgraphs/wg-20260101-a3f5b8c2.json
```

### From Stdin

```bash
echo "Optimize database queries" | maestro plan decompose -e
```

### With Custom Domain and Profile

```bash
maestro plan decompose --domain runbook --profile investor "Create runbooks for all commands"
```

### JSON Output

```bash
maestro plan decompose --json "Add dark mode" > plan.json
```

### Custom Output Path

```bash
maestro plan decompose --out custom/path.json "Add feature X"
```

### Verbose Mode

```bash
# Show summary
maestro plan decompose -v "Add tests"

# Show AI prompt and response
maestro plan decompose -vv "Add tests"
```

## How It Works

1. **Discovery**: Gathers repo evidence (READMEs, build files, binary --help text)
   - Budget-enforced: max 40 files, 200KB
   - No hardcoded assumptions about repo structure

2. **AI Generation**: Uses configured planner engine to create WorkGraph JSON
   - Strong system prompt demanding exact schema
   - Auto-repair: 1 retry on validation failure

3. **Validation**: Enforces hard gate - all tasks must have executable DoD
   - No "meta-runbook tasks" (e.g., "Organize documentation" without commands)
   - Every task must have `kind="command"` or `kind="file"` DoD

4. **Storage**: Saves to `docs/maestro/plans/workgraphs/` with atomic writes
   - Index maintained at `docs/maestro/plans/workgraphs/index.json`
   - Deterministic IDs: `wg-YYYYMMDD-<shortsha>`

## WorkGraph Schema (v1)

```json
{
  "schema_version": "v1",
  "id": "wg-YYYYMMDD-<shortsha>",
  "domain": "runbook|issues|workflow|convert|repo|general",
  "profile": "default|investor|purpose",
  "goal": "High-level goal of this plan",
  "repo_discovery": {
    "evidence": [
      {"kind": "file", "path": "README.md", "summary": "..."},
      {"kind": "command", "cmd": "./build/bss --help", "summary": "..."}
    ],
    "warnings": ["..."],
    "budget": {"max_files": 40, "max_bytes": 200000}
  },
  "track": {
    "id": "TRK-001",
    "name": "Track name",
    "goal": "Track goal"
  },
  "phases": [
    {
      "id": "PH-001",
      "name": "Phase name",
      "tasks": [
        {
          "id": "TASK-001",
          "title": "Task title",
          "intent": "What this task accomplishes",
          "definition_of_done": [
            {"kind": "command", "cmd": "maestro runbook list", "expect": "exit 0"},
            {"kind": "file", "path": "docs/maestro/runbooks/index.json", "expect": "contains xyz"}
          ],
          "verification": [
            {"kind": "command", "cmd": "bash tools/test/run.sh -q test_file.py", "expect": "exit 0"}
          ],
          "inputs": ["List of input artifacts"],
          "outputs": ["List of output artifacts"],
          "risk": {"level": "low|med|high", "notes": "Risk description"}
        }
      ]
    }
  ],
  "stop_conditions": [
    {"when": "Condition description", "action": "create_issue|abort|replan", "notes": "What to do"}
  ]
}
```

### Key Fields

- **definition_of_done**: Machine-checkable conditions (commands to run, files to check)
- **verification**: Additional verification steps (usually tests)
- **inputs/outputs**: Artifact dependencies
- **risk**: Risk assessment and mitigation notes
- **stop_conditions**: Blocker handling gates

## Profiles

- **default**: Standard decomposition for general-purpose planning
- **investor**: Focus on business value tracking and ROI
- **purpose**: Purpose-driven planning emphasizing alignment with mission/vision

## Domains

- **runbook**: Runbook generation tasks (maestro runbook commands)
- **issues**: Issue triage and tracking (maestro issues commands)
- **workflow**: Workflow automation
- **convert**: Format conversion tasks
- **repo**: Repository management
- **general**: General-purpose planning

## Discovery Protocol

The repo discovery phase is repo-agnostic and makes no assumptions about:
- Presence of specific directories (e.g., `docs/commands/`)
- Project language or build system
- Repository structure conventions

Instead, it uses heuristics and hard budgets:

1. **README files** (deterministic order): `README.md`, `docs/README.md`, `docs/index.md`
2. **Top-level structure**: Lists entries (capped at 200)
3. **Build systems**: Detects `CMakeLists.txt`, `Makefile`, `package.json`, `pyproject.toml`, etc.
4. **Binary help text**: Runs `--help` on executables in `build/`, `bin/`, `target/release/` (with 5s timeout)

**Budgets**:
- Max 40 files processed
- Max 200KB total bytes collected
- Max 5s timeout per binary

## Validation & Hard Gates

The validator enforces strict rules:

1. ✅ Every task must have at least one `definition_of_done`
2. ✅ Each DoD must have `kind="command"` OR `kind="file"`
3. ✅ Command DoDs must have `cmd` field
4. ✅ File DoDs must have `path` field
5. ❌ No "meta-runbook tasks" (tasks without executable DoD)

**Example of INVALID task** (will fail validation):
```json
{
  "title": "Organize documentation",
  "intent": "Make docs easier to find",
  "definition_of_done": []  // ❌ FAILS: No DoD!
}
```

**Example of VALID task**:
```json
{
  "title": "Organize documentation",
  "intent": "Make docs easier to find",
  "definition_of_done": [
    {"kind": "file", "path": "docs/index.md", "expect": "exists"}  // ✅ PASSES
  ]
}
```

## Integration with Other Commands

WorkGraphs can be consumed by:
- Future execution engines (Sprint 4.10)
- CI/CD pipelines
- Project tracking tools
- Compliance/audit systems

## Troubleshooting

### "Failed to generate WorkGraph: validation failed after retry"

The AI generated tasks without executable DoD. Try:
1. Use `-vv` to see the AI prompt and response
2. Provide more specific request with command examples
3. Try a different `--engine` or `--profile`

### "Error selecting engine"

No AI engine is configured. Ensure you have:
- `qwen`, `claude`, `codex`, or `gemini` CLI tools installed
- Engine configuration in maestro settings

### "Reached max_files budget"

Discovery hit the 40-file limit. This is normal for large repos. The warning is informational - decomposition will still work with collected evidence.

## See Also

- [CLI SIGNATURES](./SIGNATURES.md) - Full command signature reference
- [CLI TREE](./TREE.md) - Command hierarchy
- [CLI INVARIANTS](./INVARIANTS.md) - WorkGraph storage invariants

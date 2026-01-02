# Runbook Actionability Contract

## Problem

`maestro runbook resolve` sometimes generates "meta-runbooks" containing steps like:
- "Parse the documentation and group commands logically"
- "Create a document outlining the structure"
- "Organize the runbook into sections"

These meta-steps **describe how to create** a runbook, rather than providing **executable steps** for completing work. This fails to scale for real-world repositories where users need actionable commands.

## Definition: Actionable Runbook

A runbook is considered **actionable** when it meets these criteria:

### 1. Each step must be executable

Every step must contain at least one of:
- `command` (string) - A single shell command to execute
- `commands` (list of strings) - Multiple shell commands to execute sequentially

**Valid examples:**
```json
{
  "n": 1,
  "actor": "dev",
  "action": "Verify BSS CLI help is available",
  "expected": "Help text displays available commands",
  "command": "./build_maestro/bss --help"
}
```

```json
{
  "n": 2,
  "actor": "dev",
  "action": "Run BSS command documentation tests",
  "expected": "All tests pass",
  "commands": [
    "./build_maestro/bss list",
    "./build_maestro/bss show example"
  ]
}
```

**Invalid (meta-step without executable command):**
```json
{
  "n": 1,
  "actor": "dev",
  "action": "Parse docs/commands/ and organize into logical groups",
  "expected": "Commands are organized by category"
  // ❌ No command field
}
```

### 2. Placeholders are allowed

Steps may use placeholder variables for paths that vary by environment:

**Common placeholders:**
- `<REPO_ROOT>` - Repository root directory
- `<BSS_BIN>` - Path to BatchScriptShell binary
- `<DOCS_DIR>` - Documentation directory
- `<BUILD_DIR>` - Build output directory

**Example with placeholders:**
```json
{
  "n": 1,
  "actor": "dev",
  "action": "Build the project",
  "expected": "Build succeeds with no errors",
  "command": "cd <REPO_ROOT> && make build"
}
```

### 3. Meta-steps are rejected

Steps that describe documentation or organization tasks without executable commands are **rejected**:

**Examples of rejected meta-steps:**
- "Review the documentation and create a summary"
- "Analyze the code structure"
- "Group commands by functionality"
- "Create a runbook outline"

If these tasks are genuinely needed, they must include specific executable commands:

**Acceptable transformation:**
```json
{
  "n": 1,
  "actor": "dev",
  "action": "Extract command list from documentation",
  "expected": "commands.txt contains all available commands",
  "command": "grep -h '^##' docs/commands/*.md | sed 's/^## //' > commands.txt"
}
```

## Enforcement

### --actionable flag

The `--actionable` flag enforces the actionability contract:

```bash
maestro runbook resolve --actionable "Create runbook for BSS command verification"
```

**Behavior:**
1. AI generates runbook JSON
2. Schema validation runs (existing)
3. **Actionability validation runs** (new)
   - Checks each step has `command` or `commands` field
   - Rejects meta-steps without executable directives
4. If actionability fails:
   - Falls back to WorkGraph generation
   - Outputs: `maestro plan enact <workgraph-id>` for next step

### Without --actionable flag (backward compatible)

Runbook generation works as before:
- Meta-steps are allowed
- No actionability validation

## Variable Hints (Evidence-Pack Driven)

When evidence pack includes CLI help candidates, the AI prompt includes resolved variable hints:

**Example hints section in prompt:**
```
RESOLVED VARIABLE HINTS (use these in your commands):
- <BSS_BIN>: ./build_maestro/bss
- <DOCS_COMMANDS_DIR>: docs/commands/
- <REPO_ROOT>: (use this placeholder for repo root)
```

**Note:** Hints are derived from evidence pack discovery, not hardcoded.

## Examples

### Actionable Runbook (passes validation)

```json
{
  "id": "rb-bss-verify-abc123",
  "title": "Verify BSS command docs match executable help",
  "goal": "Ensure all documented commands are present in --help output",
  "steps": [
    {
      "n": 1,
      "actor": "dev",
      "action": "Extract commands from documentation",
      "expected": "commands.txt contains all documented commands",
      "command": "grep -h '^## ' docs/commands/*.md | sed 's/^## //' > /tmp/documented_commands.txt"
    },
    {
      "n": 2,
      "actor": "dev",
      "action": "Get BSS help output",
      "expected": "help.txt contains BSS command list",
      "command": "<BSS_BIN> --help > /tmp/bss_help.txt"
    },
    {
      "n": 3,
      "actor": "dev",
      "action": "Compare documented vs actual commands",
      "expected": "No missing commands",
      "command": "diff /tmp/documented_commands.txt <(grep -oP '\\w+' /tmp/bss_help.txt | sort -u)"
    }
  ]
}
```

### Meta-Runbook (fails validation with --actionable)

```json
{
  "id": "rb-meta-example",
  "title": "Organize BSS commands",
  "goal": "Create logical command groupings",
  "steps": [
    {
      "n": 1,
      "actor": "dev",
      "action": "Review all command documentation files",
      "expected": "Understand command purposes"
      // ❌ No command field - meta-step
    },
    {
      "n": 2,
      "actor": "dev",
      "action": "Group commands by category",
      "expected": "Commands are organized logically"
      // ❌ No command field - meta-step
    }
  ]
}
```

**With --actionable flag:** Falls back to WorkGraph

## Validation Output

### Verbose mode (-v)

```
Actionability validation: FAILED
  Step 1: Missing command/commands field
  Step 2: Missing command/commands field
Falling back to WorkGraph generation...
```

### Very verbose mode (-vv)

Shows bounded AI prompt and response (first 2000 chars each) plus actionability failure reasons.

## See Also

- [INVARIANTS.md](./INVARIANTS.md) - Contains actionability invariants
- [EVIDENCE_PACKS.md](./EVIDENCE_PACKS.md) - Evidence collection for variable hints
- [PLAN_ENACT.md](./PLAN_ENACT.md) - WorkGraph materialization (fallback target)

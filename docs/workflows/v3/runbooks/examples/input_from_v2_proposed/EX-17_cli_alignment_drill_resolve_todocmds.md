# EX-17: CLI Alignment Drill — Resolve TODO_CMD and Create Ledger Entries

**Scope**: Systematic CLI convergence from runbook documentation to implementation
**Build System**: N/A (meta-example for documentation maintenance)
**Languages**: N/A
**Outcome**: Demonstrate how to eliminate TODO_CMD markers by either finding existing CLI or creating ledger entries for missing functionality

---

## Scenario Summary

Developer reviews existing runbook examples (EX-13..EX-16) and finds multiple `TODO_CMD:` markers. They systematically check `maestro --help` and subcommand help to determine if the CLI already exists. When found, they update the runbook. When missing, they create a ledger entry in `docs/workflows/v2/IMPLEMENTATION_LEDGER.md` to track the gap.

This demonstrates **runbooks as a disciplined pipeline for CLI convergence**.

---

## Preconditions

- Existing runbook examples contain TODO_CMD markers (e.g., EX-13..EX-16)
- Maestro CLI is accessible for help queries
- `docs/workflows/v2/IMPLEMENTATION_LEDGER.md` exists (or will be created)

---

## Minimal Project Skeleton

Not applicable (this is a documentation maintenance example).

**Sample TODO_CMD markers** (from EX-14):
```markdown
| `TODO_CMD: maestro tu build --target target-cmake-mathapp` | Build translation units for target | Creates AST index |
| `TODO_CMD: maestro tu query symbol --name calculateSum` | Query symbol information | Returns definitions and references |
| `TODO_CMD: maestro tu refactor rename --symbol symbol-001 --to computeSum` | Rename symbol | Updates all references |
```

---

## Runbook Steps

### Step 1: Identify TODO_CMD Markers

| Command | Intent | Expected |
|---------|--------|----------|
| `grep -r "TODO_CMD:" docs/workflows/v2/runbooks/examples/proposed/` | Find all uncertain CLI commands | Lists all TODO markers with file:line |

**System Output**:
```
docs/workflows/v2/runbooks/examples/proposed/EX-13_repo_resolve_levels_and_repoconf_targets.md:87:| `maestro repo refresh all` | Run deep resolve with convention checking | Detects violations, creates issues |
docs/workflows/v2/runbooks/examples/proposed/EX-13_repo_resolve_levels_and_repoconf_targets.md:121:| `maestro make` | Build default target | Build succeeds |
docs/workflows/v2/runbooks/examples/proposed/EX-14_tu_ast_refactor_autocomplete.md:67:| `TODO_CMD: maestro tu build --target target-cmake-mathapp` | Build translation units | Creates AST index |
docs/workflows/v2/runbooks/examples/proposed/EX-14_tu_ast_refactor_autocomplete.md:86:| `TODO_CMD: maestro tu query symbol --name calculateSum` | Query symbol | Returns symbol info |
docs/workflows/v2/runbooks/examples/proposed/EX-15_convert_cross_repo_pipeline_from_ast.md:27:| `maestro convert add cpp-to-python` | Create conversion pipeline | Pipeline created |
docs/workflows/v2/runbooks/examples/proposed/EX-16_rules_conventions_issues_tasks_overrides.md:107:| `maestro repo refresh all` | Deep resolve with conventions | Creates issues |
docs/workflows/v2/runbooks/examples/proposed/EX-16_rules_conventions_issues_tasks_overrides.md:145:| `maestro issues list` | List open issues | Shows violations |
docs/workflows/v2/runbooks/examples/proposed/EX-16_rules_conventions_issues_tasks_overrides.md:168:| `maestro solutions list` | List active rules | Shows enabled rules |
```

**Gates**: (none - read-only query)
**Stores read**: (filesystem only)

### Step 2: Check CLI Help for Each TODO

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro --help` | Get top-level command list | Shows available subcommands |
| `maestro repo --help` | Check repo subcommand | Shows resolve, etc. |
| `maestro tu --help` | Check TU subcommand | May not exist yet |

**System Output (maestro --help)**:
```
Usage: maestro [OPTIONS] COMMAND [ARGS]...

Commands:
  init          Initialize Maestro in current repository
  repo          Repository discovery and configuration
  work          Work session management
  ops           Operations and maintenance
  settings      Configuration management

Use "maestro COMMAND --help" for more information.
```

**System Output (maestro repo --help)**:
```
Usage: maestro repo [OPTIONS] COMMAND [ARGS]...

Commands:
  resolve       Discover build systems and targets
  conf          Configure default target

Options:
  --help        Show this message and exit
```

**System Output (maestro tu --help)**:
```
Error: No such command "tu"
```

**Gates**: (none - CLI introspection)
**Stores read**: (none)

### Step 3: Create Resolution Table

| TODO_CMD | Resolution | Action |
|----------|-----------|--------|
| `maestro repo resolve --level deep` | ✅ EXISTS (check if `--level` flag exists) | Need to verify flag support |
| `maestro build` | ❌ MISSING | Create ledger entry: "Add build command" |
| `maestro tu build --target ...` | ❌ MISSING | Create ledger entry: "Add TU subcommand tree" |
| `maestro tu query symbol --name ...` | ❌ MISSING | Covered by TU ledger entry |
| `maestro tu refactor rename --symbol ...` | ❌ MISSING | Covered by TU ledger entry |
| `maestro convert new <name>` | ❌ MISSING | Create ledger entry: "Add convert pipeline commands" |
| `maestro issues list` | ❌ MISSING | Create ledger entry: "Add issues subcommand" |
| `maestro rules list` | ❌ MISSING | Create ledger entry: "Add rules subcommand" |

**Internal**:
- Group related missing commands into single ledger entries
- TU subcommand tree includes: build, query, refactor, autocomplete
- Convert pipeline includes: new, plan, run

### Step 4: Verify Existing CLI Flags

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro repo resolve --help` | Check for --level flag | May or may not exist |

**System Output**:
```
Usage: maestro repo resolve [OPTIONS]

Options:
  --level [lite|deep]  Resolution depth (default: lite)
  --help              Show this message and exit
```

**Resolution**:
- ✅ `maestro repo resolve --level deep` → CONFIRMED, remove TODO_CMD marker

**Gates**: (none)

### Step 5: Create Ledger Entries for Missing CLI

| Command | Intent | Expected |
|---------|--------|----------|
| Append to `docs/workflows/v2/IMPLEMENTATION_LEDGER.md` | Track missing CLI gaps | Ledger entries created |

**Ledger Entry Example (maestro build)**:
```markdown
### maestro build [OPTIONS] [TARGET]

**Status**: proposed
**Priority**: high
**Required by**: EX-13, EX-14, WF-08 (build execution)

**Description**:
Build the default target or specified target using the detected build system.

**Behavior**:
- Reads `./docs/maestro/repo.json` to find default target
- Invokes appropriate build system (cmake, make, cargo, etc.)
- Writes build artifacts to standard locations
- Updates build status in repo truth

**Options**:
- `--target <target-id>`: Override default target
- `--clean`: Clean before build
- `--verbose`: Show detailed build output

**Gates**:
- REPOCONF_GATE: Default target must be set

**Stores**:
- Read: REPO_TRUTH_DOCS_MAESTRO
- Write: (build artifacts, not Maestro-managed)

**Tests**:
- Test 1: Build with default target succeeds
- Test 2: Build with explicit target succeeds
- Test 3: Build fails gracefully when REPOCONF_GATE not satisfied
- Test 4: Clean build removes artifacts
```

**Ledger Entry Example (maestro tu [build|query|refactor|autocomplete])**:
```markdown
### maestro tu build --target <target-id>

**Status**: proposed
**Priority**: medium
**Required by**: EX-14, EX-15 (AST operations)

**Description**:
Build translation units (AST index) for a target by invoking compiler with AST dump flags.

**Behavior**:
- Requires successful build first (BUILD_SUCCESS gate)
- Invokes compiler for each translation unit
- Parses AST output to extract symbol graph
- Writes AST index to `./docs/maestro/tu/<target-id>.db`

**Options**:
- `--target <target-id>`: Target to build TU for (required)
- `--force`: Rebuild even if index exists

**Gates**:
- REPOCONF_GATE
- BUILD_SUCCESS

**Stores**:
- Read: REPO_TRUTH_DOCS_MAESTRO
- Write: TU_DATABASE (`./docs/maestro/tu/`)

**Tests**:
- Test 1: TU build creates AST index with symbols
- Test 2: TU build fails when build not successful
- Test 3: TU build updates existing index incrementally
```

**Gates**: (none - documentation only)
**Stores write**: (filesystem - ledger file)

### Step 6: Update Runbooks with Resolved CLI

| Command | Intent | Expected |
|---------|--------|----------|
| Edit EX-13..EX-16 to remove TODO_CMD where resolved | Update documentation | TODO markers removed for confirmed CLI |

**Before** (EX-13):
```markdown
| `maestro repo refresh all` | Run deep resolve | Detects violations |
```

**After** (EX-13):
```markdown
| `maestro repo resolve --level deep` | Run deep resolve | Detects violations |
```

**Gates**: (none)

---

## Alternative Path: CLI Partially Exists

### Step 3b: CLI Exists But Flags Don't Match

**Scenario**: `maestro repo resolve` exists but `--level` flag doesn't

| Action | Intent | Expected |
|--------|--------|----------|
| Check actual flags with `--help` | Discover true API | May differ from runbook assumption |

**System Output**:
```
Usage: maestro repo resolve [OPTIONS]

Options:
  --deep    Perform deep analysis (convention checking)
  --help    Show this message and exit
```

**Resolution**:
- Update runbook to use `--deep` flag instead of `--level deep`
- Create ledger entry to note API inconsistency: "Consider --level flag for consistency"

---

## AI Perspective (Heuristic)

**What AI notices**:
- TODO_CMD markers indicate documentation ahead of implementation
- Some commands have clear patterns (subcommand trees like `tu build|query|refactor`)
- Missing CLI can be grouped into coherent ledger entries
- Help output reveals actual API (which may differ from runbook assumptions)

**What AI tries**:
- Parse `--help` output to extract command structure and flags
- Group related missing commands into single ledger entries (e.g., all `tu` subcommands)
- Infer required behavior from runbook context (gates, stores, expected output)
- Generate ledger entries with test hints based on runbook outcomes

**Where AI tends to hallucinate**:
- May assume commands exist when only top-level command exists (`maestro repo` exists ≠ `maestro repo resolve` exists)
- May not account for flag naming inconsistencies (--level vs --deep)
- May create overly detailed ledger entries beyond what's needed
- May assume all TODO_CMD can be resolved (some represent genuinely missing features)
- May forget to check subcommand help (stops at `maestro --help`)

---

## Outcomes

### Outcome A: All TODOs Resolved from Existing CLI

**Flow**:
1. Identify 8 TODO_CMD markers across EX-13..EX-16
2. Check `maestro --help` and subcommand help
3. Find all 8 commands already exist
4. Update runbooks to remove TODO_CMD markers
5. No ledger entries needed

**Artifacts**:
- Updated: EX-13.md, EX-14.md, EX-15.md, EX-16.md (TODO_CMD removed)
- No ledger entries created

**Duration**: ~10 minutes

### Outcome B: Mix of Resolved and Missing CLI

**Flow** (as shown in main runbook):
1. Identify 8 TODO_CMD markers
2. Check help output
3. Find 1 command exists (`maestro repo resolve --level deep`)
4. Find 7 commands missing (`maestro build`, `maestro tu *`, `maestro convert *`, `maestro issues *`, `maestro rules *`)
5. Update runbook to remove TODO for resolved command
6. Create 4 ledger entries grouping missing commands:
   - "Add build command"
   - "Add TU subcommand tree (build, query, refactor, autocomplete)"
   - "Add convert pipeline commands (new, plan, run)"
   - "Add issues and rules subcommands"

**Artifacts**:
- Updated: EX-13.md (1 TODO removed)
- Created/appended: `docs/workflows/v2/IMPLEMENTATION_LEDGER.md` (4 entries)

**Duration**: ~30 minutes

### Outcome C: CLI Exists But API Differs from Runbook

**Flow**:
1. Identify TODO_CMD markers
2. Check help, find command exists but with different flags
3. Update runbook to match actual API
4. Optionally create ledger entry noting API inconsistency for future consideration

**Artifacts**:
- Updated: runbooks with corrected flags
- Optional: ledger entry for API harmonization

**Duration**: ~15 minutes

---

## Acceptance Gate Behavior

This is a documentation maintenance process with no runtime gates.

**Quality checks**:
- All TODO_CMD markers either resolved or ledger entries created
- Ledger entries include: status, priority, description, behavior, options, gates, stores, tests
- Updated runbooks reflect actual CLI API

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "maestro build [OPTIONS] [TARGET]"
  - "maestro tu build --target <target-id>"
  - "maestro tu query symbol --name <name>"
  - "maestro tu refactor rename --symbol <symbol-id> --to <new-name>"
  - "maestro tu autocomplete --file <file> --line <line> --col <col>"
  - "maestro convert new <pipeline-name>"
  - "maestro convert plan <pipeline-name>"
  - "maestro convert run <pipeline-name> --out <target-path>"
  - "maestro issues list"
  - "maestro issues show <issue-id>"
  - "maestro issues ignore <issue-id> --reason <reason>"
  - "maestro rules list"
  - "maestro rules check"
  - "maestro task add --from-issue <issue-id>"
  - "How to structure IMPLEMENTATION_LEDGER.md (format, sections)"
  - "Whether ledger entries should be auto-generated from runbooks"
  - "Policy for when to group vs split ledger entries"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "grep -r 'TODO_CMD:' docs/workflows/v2/runbooks/examples/proposed/"
    intent: "Find all uncertain CLI commands in runbooks"
    gates: []
    stores_write: []
    stores_read: []
    internal: ["filesystem_search"]
    cli_confidence: "high"  # Standard grep

  - user: "maestro --help"
    intent: "Get top-level command list"
    gates: []
    stores_write: []
    stores_read: []
    internal: []
    cli_confidence: "high"

  - user: "maestro repo --help"
    intent: "Check repo subcommand structure"
    gates: []
    stores_write: []
    stores_read: []
    internal: []
    cli_confidence: "high"

  - user: "maestro repo resolve --help"
    intent: "Verify --level flag exists"
    gates: []
    stores_write: []
    stores_read: []
    internal: []
    cli_confidence: "medium"  # Flag may or may not exist

  - user: "maestro tu --help"
    intent: "Check if TU subcommand exists"
    gates: []
    stores_write: []
    stores_read: []
    internal: []
    cli_confidence: "low"  # Likely missing

  - user: "Append ledger entries to docs/workflows/v2/IMPLEMENTATION_LEDGER.md"
    intent: "Track missing CLI gaps for future implementation"
    gates: []
    stores_write: []
    stores_read: []
    internal: ["ledger_update"]
    cli_confidence: "high"  # Manual edit
```

---

**Related:** Documentation maintenance, CLI convergence, implementation tracking, runbook accuracy
**Status:** Proposed

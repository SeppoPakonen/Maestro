# EX-09: Greenfield "Hello CLI" in Python — Runbook→Workflow→Plan→Implemented Code

**Scope**: Runbook-first greenfield development
**Build System**: None (single Python file)
**Languages**: Python 3.11+
**Outcome**: Create a tiny CLI tool using runbook-first approach, extract workflow, create plan, implement minimal code

---

## Scenario Summary

Developer wants to create a simple CLI greeting tool. Instead of jumping straight to code, they start with a runbook to model the user experience, extract a workflow graph showing the intent→interface→code layers, create a track/phase/task plan, then implement the minimal code using `maestro work`.

This demonstrates the **runbook-first** value: start with narrative, formalize progressively.

---

## Preconditions

- Empty directory or new project
- Python 3.11+ available
- Maestro initialized (or will initialize)

---

## Minimal Project Skeleton (Final State)

```
hello-cli/
├── docs/
│   └── maestro/
│       ├── runbooks/
│       │   └── hello-cli-runbook.json
│       ├── workflows/
│       │   └── hello-cli-workflow.json
│       ├── tracks/
│       │   └── track-001.json
│       └── tasks/
│           └── task-001.json
└── hello.py
```

**hello.py** (final implementation):
```python
#!/usr/bin/env python3
import argparse

def main():
    parser = argparse.ArgumentParser(description='Simple greeting CLI')
    parser.add_argument('--name', default='World', help='Name to greet')
    args = parser.parse_args()

    print(f"Hello, {args.name}!")

if __name__ == '__main__':
    main()
```

---

## Runbook Steps

### Step 1: Initialize Maestro

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro init` | Create repo truth structure | `./docs/maestro/**` created |

### Step 2: Create Runbook (Narrative First)

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook add --title "Hello CLI Tool" --scope product --tag greenfield` | Create runbook | Runbook `hello-cli-tool.json` created |

### Step 3: Add Runbook Steps (User Journey)

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook step-add hello-cli-tool --actor manager --action "Define product goal: simple greeting CLI" --expected "Goal documented"` | Manager intent | Step 1 added |
| `maestro runbook step-add hello-cli-tool --actor user --action "Run: hello --name Alice" --expected "Prints: Hello, Alice!"` | User intent | Step 2 added |
| `maestro runbook step-add hello-cli-tool --actor user --action "Run: hello (no args)" --expected "Prints: Hello, World!"` | Default behavior | Step 3 added |
| `maestro runbook step-add hello-cli-tool --actor system --action "Parse CLI args using argparse" --expected "Arguments extracted"` | Interface layer | Step 4 added |
| `maestro runbook step-add hello-cli-tool --actor ai --action "Implement hello.py with argparse" --expected "Code written and tested"` | Code layer | Step 5 added |

### Step 4: Export Runbook to Markdown

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook export hello-cli-tool --format md` | Review runbook | Markdown document printed |

---

## Workflow Extraction (Runbook → Workflow)

### Step 5: Create Workflow Graph from Runbook

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow init hello-cli-workflow --from-runbook hello-cli-tool` | Extract workflow graph | Workflow JSON created with nodes per layer |

### Step 6: Add Workflow Nodes (Explicit Layering)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow node add hello-cli-workflow --layer manager_intent --label "Product goal: greeting CLI"` | Manager intent node | Node added |
| `TODO_CMD: maestro workflow node add hello-cli-workflow --layer user_intent --label "User runs hello --name X"` | User intent node | Node added |
| `TODO_CMD: maestro workflow node add hello-cli-workflow --layer interface --label "CLI: argparse parser"` | Interface node | Node added |
| `TODO_CMD: maestro workflow node add hello-cli-workflow --layer code --label "hello.py main()"` | Code node | Node added |

### Step 7: Add Workflow Edges

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow edge add hello-cli-workflow --from manager_intent_001 --to user_intent_001` | Link layers | Edge added |
| `TODO_CMD: maestro workflow edge add hello-cli-workflow --from user_intent_001 --to interface_001` | Link to interface | Edge added |
| `TODO_CMD: maestro workflow edge add hello-cli-workflow --from interface_001 --to code_001` | Link to code | Edge added |

### Step 8: Validate and Render Workflow

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow validate hello-cli-workflow` | Check graph consistency | Validation passes |
| `TODO_CMD: maestro workflow render hello-cli-workflow --format puml` | Generate PlantUML | `.puml` and `.svg` created |

---

## Plan Creation (Workflow → Track/Phase/Task)

### Step 9: Create Track

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro track add "Sprint 1: Hello CLI" --start 2025-01-01` | Create work track | Track `track-001` created |

### Step 10: Create Phase

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro phase add track-001 "P1: Implement Core"` | Add phase to track | Phase `phase-001` created |

### Step 11: Create Task

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro task add phase-001 "Implement hello.py with argparse"` | Add task | Task `task-001` created |

---

## Work Execution Loop (Plan → Implementation)

### Step 12: Start Work Session

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro work task task-001` | Start AI-assisted work | Work session cookie created, AI context loaded |

**Internal:** Maestro creates:
- Session cookie: `$HOME/.maestro/ipc/<session-id>/cookie`
- Breadcrumb file: `$HOME/.maestro/ipc/<session-id>/breadcrumbs.json`

### Step 13: AI Implements Code (Simulated)

During work session, AI would:

1. Read runbook context
2. Read workflow graph
3. Generate `hello.py`
4. Update breadcrumbs: `TODO_CMD: maestro wsession breadcrumb task-001 --cookie <cookie> --status "Implementing argparse parser"`

### Step 14: Test Implementation

| Command | Intent | Expected |
|---------|--------|----------|
| `python hello.py --name Alice` | Test with name | Prints: "Hello, Alice!" |
| `python hello.py` | Test default | Prints: "Hello, World!" |

### Step 15: Complete Task

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro task complete task-001` | Mark task done | Task status → completed |

---

## AI Perspective (Heuristic)

**What AI notices:**
- Runbook contains clear actor sequence: manager → user → system → ai
- User steps show expected CLI invocations: `hello --name X`
- Workflow graph confirms interface layer is CLI (not GUI/TUI)

**What AI tries:**
- Generate minimal argparse-based CLI matching runbook expectations
- Preserve exact output format from runbook: "Hello, {name}!"
- Avoid over-engineering (no config files, no logging, just core function)

**Where AI tends to hallucinate:**
- May add unnecessary features like `--verbose` or `--version` if not constrained by runbook
- May create multi-file structure when single file is sufficient
- May use click/typer instead of argparse if not guided

---

## Outcomes

### Outcome A: Success Path

**Result:** `hello.py` implemented, tested, task completed

**Artifacts:**
- Runbook: `./docs/maestro/runbooks/hello-cli-tool.json`
- Workflow: `./docs/maestro/workflows/hello-cli-workflow.json`
- Task: `./docs/maestro/tasks/task-001.json` (status: completed)
- Code: `hello.py` (working)

### Outcome B: Failure — Missing Python

**Result:** `python hello.py` fails with "command not found"

**Recovery:**
1. Create issue: `TODO_CMD: maestro issues add --type environment --desc "Python 3.11+ not found"`
2. Create task: "Install Python 3.11"
3. Retry after resolution

### Outcome C: Failure — Wrong Shebang

**Result:** `./hello.py` fails if shebang is `#!/usr/bin/python` instead of `#!/usr/bin/env python3`

**Recovery:**
1. Runbook revised: add step "Verify shebang uses env python3"
2. Issue created for incorrect shebang pattern
3. Fix applied, task re-tested

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "TODO_CMD: maestro workflow init <name> --from-runbook <id>"
  - "TODO_CMD: maestro workflow node add <id> --layer <layer> --label <text>"
  - "TODO_CMD: maestro workflow edge add <id> --from <node> --to <node>"
  - "TODO_CMD: maestro workflow validate <id>"
  - "TODO_CMD: maestro workflow render <id> --format puml"
  - "TODO_CMD: maestro wsession breadcrumb <task> --cookie <cookie> --status <msg>"
  - "TODO_CMD: maestro task complete <id>"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro runbook add --title 'Hello CLI Tool' --scope product"
    intent: "Create narrative model before code"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "high"

  - user: "maestro runbook step-add hello-cli-tool --actor manager ..."
    intent: "Add manager intent step to runbook"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "high"

  - user: "maestro workflow init hello-cli-workflow --from-runbook hello-cli-tool"
    intent: "Extract workflow graph from runbook narrative"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro track add 'Sprint 1: Hello CLI'"
    intent: "Create work track for planning"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "high"

  - user: "maestro work task task-001"
    intent: "Start AI-assisted work session with runbook/workflow context"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO", "IPC_MAILBOX"]
    internal: ["UNKNOWN"]
    cli_confidence: "medium"

  - user: "maestro wsession breadcrumb task-001 --cookie <cookie> --status 'Implementing argparse parser'"
    intent: "AI updates progress breadcrumbs during work"
    gates: []
    stores_write: ["IPC_MAILBOX"]
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # TODO_CMD
```

---

**Related:** Runbook-first greenfield development pattern
**Status:** Proposed

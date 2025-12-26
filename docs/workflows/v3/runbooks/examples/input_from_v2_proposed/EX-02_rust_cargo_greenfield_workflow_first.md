# EX-02: Rust Cargo Greenfield — Workflow-First, Generate Skeleton, Build, Work Session

**Scope**: WF-02 (Greenfield Workflow-First)
**Build System**: Cargo (Rust)
**Languages**: Rust
**Outcome**: Demonstrate workflow-first approach, skeleton generation, build, and work session start

---

## Scenario Summary

Product manager starts a new Rust project using workflow-first approach. They model user intent → interface → code layers as workflow nodes before writing code. Maestro generates a minimal Cargo skeleton, builds it, then they create tracks/phases/tasks and start a work session.

---

## Minimal Project Skeleton

Initially empty. After workflow → skeleton generation:

```
my-rust-service/
├── Cargo.toml
└── src/
    └── main.rs
```

**Cargo.toml** (generated):
```toml
[package]
name = "my-rust-service"
version = "0.1.0"
edition = "2021"

[dependencies]
```

**src/main.rs** (generated):
```rust
fn main() {
    println!("Hello from my-rust-service v0.1.0");
}
```

---

## Runbook Steps

| Step | Command | Intent | Expected Outcome | Gates | Stores Written |
|------|---------|--------|------------------|-------|----------------|
| 1 | `maestro init --greenfield` | Initialize new project | Creates `./docs/maestro/**` | REPOCONF_GATE | REPO_TRUTH_DOCS_MAESTRO |
| 2 | `TODO_CMD: maestro workflow init user-auth-service` | Create new workflow graph | Workflow template created | REPOCONF_GATE | REPO_TRUTH_DOCS_MAESTRO |
| 3 | `TODO_CMD: maestro workflow node add manager-intent "User can log in securely"` | Add manager perspective node | Node added to workflow | REPOCONF_GATE | REPO_TRUTH_DOCS_MAESTRO |
| 4 | `TODO_CMD: maestro workflow node add user-action "Submit login form"` | Add user action node | Node added | REPOCONF_GATE | REPO_TRUTH_DOCS_MAESTRO |
| 5 | `TODO_CMD: maestro workflow render --format puml` | Export workflow as PlantUML | Generated `.puml` and `.svg` | (read-only) | (exports dir) |
| 6 | `TODO_CMD: maestro workflow accept user-auth-service` | Accept workflow, generate skeleton | Cargo.toml + src/main.rs created | REPOCONF_GATE | REPO_TRUTH_DOCS_MAESTRO + files |
| 7 | `maestro build` | Build Rust skeleton | Cargo build succeeds, binary created | READONLY_GUARD | REPO_TRUTH_DOCS_MAESTRO |
| 8 | `maestro track add "Sprint 1" --start 2025-01-01` | Create development track | Track created | REPOCONF_GATE | REPO_TRUTH_DOCS_MAESTRO |
| 9 | `maestro phase add track-001 "P1: Core Auth"` | Add phase to track | Phase created | REPOCONF_GATE | REPO_TRUTH_DOCS_MAESTRO |
| 10 | `maestro task add phase-001 "Implement login endpoint"` | Add task to phase | Task created | REPOCONF_GATE | REPO_TRUTH_DOCS_MAESTRO |
| 11 | `maestro work task task-001` | Start work session on task | Work session cookie created, AI context loaded | REPOCONF_GATE | REPO_TRUTH_DOCS_MAESTRO + IPC_MAILBOX |

---

## AI Perspective (Heuristic)

**What the AI likely notices:**

- Workflow nodes defined before code → infer design-first intent
- Rust ecosystem detected (Cargo.toml signature)
- No existing code → greenfield scenario, safe to generate skeleton

**What the AI likely tries next:**

1. Translate workflow nodes into code structure hints
2. Generate minimal `Cargo.toml` with project name from workflow
3. Create `src/main.rs` with basic entry point
4. Run `cargo build` to validate skeleton
5. Set up work session context with workflow goals in prompt

**Confidence heuristics:**

- High confidence: Cargo skeleton generation (standard Rust template)
- Medium confidence: Workflow-to-code mapping (depends on node types)
- Low confidence: Auto-linking workflow goals to code TODOs

---

## Outcomes

### Outcome A: Workflow Accepted, Code Generation Succeeds

1. Workflow nodes model manager/user/interface/code layers
2. User accepts workflow via `maestro workflow accept`
3. Cargo skeleton generated successfully
4. Build passes
5. Work session starts with workflow context in AI prompt

**Exit state:**

- `./docs/maestro/workflows/user-auth-service.json` status: `accepted`
- `Cargo.toml` and `src/main.rs` exist and build
- Work session active, AI has workflow goals in context

### Outcome B: Workflow Unclear, Remains Proposed

1. Workflow nodes too vague or conflicting
2. User marks workflow as `proposed` (not yet accepted)
3. No code generation triggered
4. User refines workflow nodes iteratively
5. Later accepts after clarification

**Exit state:**

- Workflow status: `proposed`
- No code files generated yet
- User continues workflow design phase

---

## CLI Gaps / TODOs

**Unknown exact commands:**

- `TODO_CMD: maestro workflow init <name>` — spec-level, not implemented
- `TODO_CMD: maestro workflow node add <type> <description>` — node management unclear
- `TODO_CMD: maestro workflow render --format puml` — export mechanism TBD
- `TODO_CMD: maestro workflow accept <workflow-id>` — acceptance trigger unknown
- `maestro build` — may be `maestro make` or detect `cargo build` automatically

**Clarifications needed:**

- Does workflow acceptance auto-generate code or require separate command?
- How are workflow node types mapped to code structure?
- Is `--greenfield` flag needed for `maestro init` or auto-detected?

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro init --greenfield"
    intent: "Initialize greenfield Rust project"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "medium"

  - user: "maestro workflow init user-auth-service"
    intent: "Create new workflow graph for user authentication"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # spec-level command

  - user: "maestro workflow accept user-auth-service"
    intent: "Accept workflow design, trigger skeleton generation"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # spec-level command

  - user: "maestro build"
    intent: "Build Rust project using Cargo"
    gates: ["READONLY_GUARD"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "medium"

  - user: "maestro work task task-001"
    intent: "Start work session with workflow context"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO", "IPC_MAILBOX"]
    internal: ["UNKNOWN"]
    cli_confidence: "medium"
```

---

**Related Workflows:** WF-02
**Status:** Proposed
**Acceptance Criteria:** Workflow command surface designed, skeleton generation implemented, ledger entry created

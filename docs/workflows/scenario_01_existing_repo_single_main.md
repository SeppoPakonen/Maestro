---
id: WF-01
title: Existing Repo Bootstrap (Single Main, Compiled Language)
tags: [bootstrap, retrofit, compile, issues, tasks, ai-discuss]
entry_conditions: |
  - Existing git repository (initialized)
  - Single main branch (or primary development branch)
  - Compiled language project (e.g., Rust, Go, C++, Java)
  - Maestro not yet initialized
  - User has working development environment (compiler, build tools)
exit_conditions: |
  - Maestro directory structure created (docs/maestro/tracks/, docs/maestro/phases/, docs/maestro/tasks/, issue data)
  - docs/maestro/index.json initialized
  - Past work reconstructed (either git-driven or snapshot-based)
  - Build attempted and analyzed
  - Clean build achieved OR build errors captured as issues/tasks with dependency ranking
  - (Optional) Runtime attempted; errors captured as issues/tasks
artifacts_created: |
  - docs/maestro/tracks/*.json (initial tracks, e.g., bootstrap, bugfix)
  - docs/maestro/phases/*.json (phases within tracks)
  - docs/maestro/tasks/*.json (tasks with metadata, dependencies)
  - issue data*.md (issues from build errors, warnings, runtime errors)
  - docs/maestro/index.json (initial plan scaffold or AI-generated plan)
  - active tasks in JSON (active task list)
  - completed tasks in JSON (reconstructed past work)
failure_semantics: |
  - Hard stop: Not a git repository
  - Hard stop: Invalid JSON from engine (blocks continuation; operator may re-prompt)
  - Hard stop: Malformed truth file write (parser validation fails)
  - Recoverable: Already initialized (idempotent behavior)
  - Recoverable: Build errors (captured as issues/tasks; work loop begins)
  - Recoverable: Runtime errors (captured as issues/tasks)
follow_on_scenarios: [WF-05, WF-08, WF-04]
---

# Scenario WF-01: Existing Repo Bootstrap (Single Main, Compiled Language)

## Actor Model Note

**Important**: In Maestro, there is no separate "AI" workflow participant. The **Operator** (either a human user or an AI runner) interacts with Maestro via the same CLI command interface. Commands like `maestro discuss` or `maestro work task` may internally invoke an AI engine, but this is an execution mode of the Maestro CLI itself, not a separate actor. Therefore:
- Operator = human OR AI runner
- Both use identical CLI commands
- Behavior is the same at the command boundary

## Overview

This scenario documents the **initial bootstrap process** when an Operator adds Maestro to an **existing codebase** with:
- A single main branch (or primary development branch)
- A compiled language requiring build steps
- No prior Maestro initialization

The workflow covers:
1. Maestro initialization
2. Engine-driven codebase understanding (via `maestro discuss`)
3. Past work reconstruction
4. Build analysis and error capture
5. Issue/task generation with dependency ranking
6. Work loop (fix → rebuild → iterate)

---

## Phase 0: Entry & Preconditions

### Preconditions

Before entering this scenario, the following must be true:

- **Git repository exists**: The current directory is a valid git repository
  - Verify: `git rev-parse --git-dir` succeeds
- **Single branch workflow**: The project uses a single primary branch (e.g., `main`, `master`)
  - Multi-branch workflows use **WF-02** instead
- **Compiled language**: The project requires a build step (compile, link, etc.)
  - Interpreted languages may use a simplified variant of this scenario
- **Development environment ready**: User has necessary compilers, build tools, dependencies installed
- **Maestro not initialized**: No `docs/maestro/tracks/`, `docs/maestro/index.json`, etc. exist yet

### Operator Intent

The Operator (human or AI runner) wants to:
- Start using Maestro for task tracking and engine-assisted development
- Understand the current state of the codebase
- Identify and fix any build or runtime issues
- Establish a baseline for future work

---

## Phase 1: Maestro Initialization

### Command: `maestro init`

**Purpose**: Bootstrap Maestro's directory structure and initial state files.

**Inputs**:
- Current directory (must be a git repo)
- Optional flags:
  - `--force`: Reinitialize even if already initialized
  - `--strategy <git|snapshot>`: Choose reconstruction strategy (default: auto-detect)

**Outputs**:
- Creates directory structure:
  ```
  docs/
    tracks/
    phases/
    tasks/
    issues/
    plan.json       (empty scaffold: {"tracks": [], "version": "1.0"})
    todo.md         (empty: "# TODO\n")
    done.md         (empty: "# DONE\n")
  ```
- Writes `.maestro/config.json` (or similar) with:
  - Initialization timestamp
  - Detected language/build system
  - Default engine preferences

**Failure Modes**:
- **Hard stop**: Not a git repository
  - Error: "Current directory is not a git repository. Run `git init` first."
- **Idempotent**: Already initialized
  - Warning: "Maestro already initialized. Use `--force` to reinitialize."
  - Exit with success code (no-op)

**State Change**:
- Project state: `uninitialized` → `initialized`
- Truth files created: `docs/maestro/index.json`, `active tasks in JSON`, `completed tasks in JSON`

---

## Phase 2: Understand Codebase (Operator-Initiated)

### Command: `maestro discuss "Analyze codebase structure and purpose"`

**Purpose**: Use Maestro's configured engine (AI or rule-based) to understand the codebase's architecture, dependencies, and current state.

**Inputs**:
- Codebase files (read via code exploration)
- Git history (optional: for context)
- Operator prompt: "Analyze codebase structure and purpose"

**Outputs**:
- Discussion output (streamed to Operator)
- **CLI Contract**: Engine returns structured JSON:
  ```json
  {
    "understanding": {
      "language": "Rust",
      "build_system": "Cargo",
      "primary_modules": ["core", "api", "cli"],
      "dependencies": ["serde", "tokio", "clap"],
      "architecture_pattern": "Layered (CLI → API → Core)"
    },
    "questions": [
      "Is this project intended for production use?",
      "Are there known issues or TODOs?"
    ]
  }
  ```

**Validation**:
- Engine response must be valid JSON
- If engine returns non-JSON or malformed JSON:
  - **Hard stop**: Display error: "Invalid JSON from engine. Please retry with a clearer prompt."
  - Operator may re-prompt explicitly

**Operator Validation Gate**:
- Maestro displays engine's understanding
- Prompts Operator: "Does this understanding look correct? (yes/no/edit)"
  - **Yes**: Proceed to Phase 3
  - **No**: Return to `maestro discuss` with corrections
  - **Edit**: Operator provides clarifications, Maestro re-prompts engine

**Failure Modes**:
- **Hard stop**: Invalid JSON from engine
- **Recoverable**: Engine misunderstands codebase (operator corrects via discussion)

**State Change**:
- Project understanding captured (may be stored in `docs/context.json` or similar)

---

## Phase 3: Reconstruct Past Work (Inferred DONE)

### Purpose

Capture completed work from the project's history to establish a baseline in `completed tasks in JSON`.

### Strategy 1: Git-Driven Reconstruction

**Proposed CLI Contract**: `maestro reconstruct --strategy=git`

**Process**:
1. Parse git log: `git log --oneline --reverse`
2. Group commits by semantic purpose (AI-assisted):
   - Feature additions
   - Bug fixes
   - Refactorings
   - Dependency updates
3. Generate `completed tasks in JSON` entries:
   ```markdown
   # DONE

   ## Phase: Initial Development (Track: bootstrap)
   - [x] Set up Cargo project structure (commit: a1b2c3d)
   - [x] Implement core parser (commit: e4f5g6h)
   - [x] Add CLI argument handling (commit: i7j8k9l)

   ## Phase: API Development (Track: bootstrap)
   - [x] Design REST API endpoints (commit: m1n2o3p)
   - [x] Implement request handlers (commit: q4r5s6t)
   ```

**Failure Modes**:
- **Recoverable**: Ambiguous commit messages (AI does best-effort grouping; user reviews)
- **Recoverable**: No git history (fall back to Strategy 2)

### Strategy 2: Snapshot/Context-Window Reconstruction

**Proposed CLI Contract**: `maestro reconstruct --strategy=snapshot`

**Process**:
1. AI reads current codebase state
2. Infers completed work from:
   - Existing features (function definitions, modules)
   - Code comments with "TODO" vs "DONE" markers
   - Test coverage (tests imply implemented features)
3. Generates `completed tasks in JSON` entries:
   ```markdown
   # DONE

   ## Phase: Inferred Completed Work (Track: bootstrap)
   - [x] Core library implemented (modules: core, utils)
   - [x] CLI interface implemented (clap argument parsing)
   - [x] Basic API endpoints (GET /status, POST /process)
   ```

**Failure Modes**:
- **Recoverable**: AI over-infers or under-infers work (user reviews and edits `completed tasks in JSON`)

### Human Review Gate

After reconstruction:
- Maestro displays `completed tasks in JSON`
- Prompts: "Review completed work. Edit completed tasks in JSON if needed, then confirm. (continue/edit)"
  - **Continue**: Proceed to Phase 4
  - **Edit**: User manually edits `completed tasks in JSON`, then re-runs `maestro reconstruct --confirm`

**State Change**:
- `completed tasks in JSON` populated with past work
- Baseline established for future task tracking

---

## Phase 4: Build Attempt → Error Capture → Issue/Task Generation

### Step 4.1: Attempt Build

**Proposed CLI Contract**: `maestro build`

**Purpose**: Trigger the project's build process and capture output.

**Process**:
1. Run Repo Resolve (WF-05) to detect build system and packages:
   - Execute `maestro repo resolve` to identify packages and build systems
   - Use resolved build targets and configurations for build attempt
   - Leverage dependency graph for proper build order
2. Run build command with full output capture
3. Parse build output for:
   - **Errors**: Compilation failures, linking errors
   - **Warnings**: Compiler warnings, linter issues
   - **Metadata**: File paths, line numbers, error codes

**Outputs**:
- Build log: `docs/build.log` (timestamped)
- Parsed errors/warnings: Structured data (JSON or internal format)

**Success Case**:
- Build succeeds (exit code 0, no errors)
  - Proceed to **Phase 6** (optional runtime attempt)

**Failure Case**:
- Build fails (exit code non-zero, errors present)
  - Proceed to **Step 4.2**

### Step 4.2: Parse Errors and Create Issues

**Proposed CLI Contract**: `maestro build --create-issues`

**Process**:
1. Parse build errors using regex or structured parsers:
   - Rust: Parse `error[E0xyz]: message` format
   - Go: Parse `file.go:123:45: message` format
   - GCC/Clang: Parse `file.c:10:5: error: message` format

2. Group errors by:
   - **File/module**: Errors in the same file
   - **Error type**: Type errors, missing symbols, syntax errors
   - **Root cause** (AI-assisted): Related errors stemming from a single root issue

3. Create issues in `issue data`:
   ```markdown
   # Issue ISS-001: Undefined symbol `process_data`

   **Source**: Build error
   **File**: src/core.rs:45
   **Error Code**: E0425

   ## Description
   Function `process_data` is called but not defined in scope.

   ## Error Message
   ```
   error[E0425]: cannot find function `process_data` in this scope
     --> src/core.rs:45:12
      |
   45 |     let result = process_data(input);
      |                  ^^^^^^^^^^^^ not found in this scope
   ```

   ## Proposed Fix
   Define `process_data` function or import from another module.

   ## Related Issues
   - ISS-002 (may be caused by missing import)
   ```

**Outputs**:
- `issue dataISS-001.md`, `ISS-002.md`, etc.
- Issue metadata (JSON or front-matter):
  ```yaml
  id: ISS-001
  source: build_error
  file: src/core.rs
  line: 45
  severity: error
  status: open
  ```

### Step 4.3: Create Tasks from Issues

**Proposed CLI Contract**: `maestro task create --from-issues`

**Process**:
1. For each issue, create a corresponding task:
   ```json
   {
     "id": "TASK-001",
     "title": "Fix undefined symbol `process_data`",
     "issue_id": "ISS-001",
     "status": "pending",
     "priority": "high",
     "dependencies": [],
     "metadata": {
       "file": "src/core.rs",
       "line": 45
     }
   }
   ```

2. Write to `docs/maestro/tasks/TASK-001.json`

**Outputs**:
- `docs/maestro/tasks/TASK-001.json`, `TASK-002.json`, etc.

### Step 4.4: Dependency Ranking

**Proposed CLI Contract**: `maestro task rank-dependencies`

**Purpose**: Determine task execution order based on error dependencies.

**Process**:
1. Analyze error relationships:
   - If error A is "missing import" and error B is "undefined symbol from A", then `TASK-A` → `TASK-B`
   - Use AI to infer non-obvious dependencies (e.g., "type error in struct definition affects all usages")

2. Build dependency graph:
   ```
   TASK-001 (define process_data)
     ↓
   TASK-002 (fix call to process_data)
     ↓
   TASK-003 (fix downstream type error)
   ```

3. Update task metadata with dependencies:
   ```json
   {
     "id": "TASK-002",
     "dependencies": ["TASK-001"]
   }
   ```

4. Generate `active tasks in JSON` with ranked task list:
   ```markdown
   # TODO

   ## Phase: Build Fixes (Track: bugfix)
   - [ ] TASK-001: Fix undefined symbol `process_data` (no dependencies)
   - [ ] TASK-002: Fix call to process_data (depends: TASK-001)
   - [ ] TASK-003: Fix downstream type error (depends: TASK-002)
   ```

**Outputs**:
- Updated task JSON files with `dependencies` field
- `active tasks in JSON` with ranked task order

**Failure Modes**:
- **Recoverable**: Circular dependencies detected (AI or user must resolve)
- **Recoverable**: Ambiguous dependencies (AI makes best guess; user reviews)

**State Change**:
- Tasks ranked and ready for work loop

---

## Phase 5: Work Loop (Fix → Rebuild → Iterate)

### Overview

This phase is an iterative loop:
1. Pick highest-priority task from `active tasks in JSON`
2. Fix the issue (human or AI-assisted)
3. Rebuild
4. If new errors appear, create new issues/tasks
5. Repeat until clean build

### Step 5.1: Pick Task

**Proposed CLI Contract**: `maestro task next`

**Process**:
- Read `active tasks in JSON`
- Select the first task with no unsatisfied dependencies
- Display task details to user

**Output**:
```
Next task: TASK-001
Title: Fix undefined symbol `process_data`
Issue: ISS-001
File: src/core.rs:45
```

### Step 5.2: Fix Task (Human or AI)

**Manual Fix**:
- User edits files directly
- Marks task as complete: `maestro task complete TASK-001`

**AI-Assisted Fix** (Proposed CLI Contract): `maestro task fix TASK-001`

**Process**:
1. AI reads task details and issue context
2. AI proposes code changes (via Maestro-mediated channels):
   ```json
   {
     "task_id": "TASK-001",
     "changes": [
       {
         "file": "src/core.rs",
         "action": "insert",
         "line": 40,
         "content": "fn process_data(input: &str) -> Result<Data, Error> { ... }"
       }
     ]
   }
   ```
3. Maestro validates changes:
   - File exists
   - Line numbers are valid
   - Syntax is valid (pre-check via parser)
4. If validation passes, apply changes
5. If validation fails: **Hard stop** with error message

**Failure Modes**:
- **Hard stop**: AI proposes invalid JSON
- **Hard stop**: Validation fails (malformed code, non-existent file)
- **Recoverable**: Fix doesn't resolve issue (rebuild will detect; create new task)

### Step 5.3: Rebuild

**Command**: `maestro build --create-issues`

**Process**:
- Same as **Phase 4.1**
- If build succeeds: Exit loop, proceed to **Phase 6**
- If new errors appear: Create new issues/tasks, update `active tasks in JSON`, continue loop

### Step 5.4: Update Task Status

**Command**: `maestro task complete TASK-001`

**Process**:
1. Move task from `active tasks in JSON` to `completed tasks in JSON`:
   ```markdown
   # DONE
   ...
   ## Phase: Build Fixes (Track: bugfix)
   - [x] TASK-001: Fix undefined symbol `process_data` (completed: 2025-12-25)
   ```
2. Update task JSON status: `"status": "completed"`

**Policy Enforcement** (per CLAUDE.md):
- **Mandatory Task Lifecycle Rule**: At the end of a phase, completed tasks MUST be moved from `active tasks in JSON` to `completed tasks in JSON`

### Loop Exit Conditions

Exit the loop when:
- Build succeeds with no errors (clean build)
- OR User manually exits (partial fix; remaining tasks stay in `active tasks in JSON`)

---

## Phase 6: Runtime Attempt → Log Scan → Issues/Tasks (Optional)

### Step 6.1: Run Application

**Proposed CLI Contract**: `maestro run`

**Purpose**: Execute the built application and capture runtime output.

**Process**:
1. Detect run command:
   - Rust: `cargo run`
   - Go: `./binary`
   - Java: `java -jar app.jar`
2. Run with output capture
3. Log output to `docs/runtime.log`

**Success Case**:
- Application runs without errors
  - Exit scenario with success

**Failure Case**:
- Runtime errors detected (panics, exceptions, crashes)
  - Proceed to **Step 6.2**

### Step 6.2: Parse Runtime Errors and Create Issues

**Proposed CLI Contract**: `maestro run --create-issues`

**Process**:
1. Parse runtime logs for:
   - Panics/crashes with stack traces
   - Exceptions with file/line numbers
   - Assertion failures
   - Segmentation faults

2. Create issues in `issue data`:
   ```markdown
   # Issue ISS-010: Panic: index out of bounds

   **Source**: Runtime error
   **File**: src/utils.rs:78
   **Timestamp**: 2025-12-25 14:32:01

   ## Stack Trace
   ```
   thread 'main' panicked at 'index out of bounds: the len is 5 but the index is 10',
   src/utils.rs:78:9
   ```

   ## Proposed Fix
   Add bounds checking before array access.
   ```

3. Create tasks from issues (same process as **Phase 4.3**)

4. Update `active tasks in JSON` with new runtime-fix tasks

### Step 6.3: Runtime Work Loop

- Same loop as **Phase 5**: fix → re-run → iterate
- Exit when application runs cleanly

---

## Exit Criteria

This scenario successfully exits when:

1. **Maestro initialized**: `docs/` structure exists
2. **Past work reconstructed**: `completed tasks in JSON` populated
3. **Build attempted**: At least one build attempt made
4. **Clean build OR tasks created**:
   - Clean build: Application compiles with no errors
   - OR: Errors captured as issues/tasks in `active tasks in JSON` with dependency ranking
5. **(Optional) Runtime attempted**: If applicable, runtime errors captured or app runs cleanly

**Follow-On Scenarios**:
- **WF-05**: Feature Request Workflow (user requests new functionality)
- **WF-08**: Test Failure Workflow (if tests exist and fail)
- **WF-04**: Runtime Error Workflow (if ongoing runtime issues detected)

---

## Command Contracts Summary

| Command | Purpose | Inputs | Outputs | Hard Stops | Recoverable |
|---------|---------|--------|---------|-----------|-------------|
| `maestro init` | Bootstrap Maestro | Current dir (git repo) | `docs/` structure, `plan.json`, `todo.md`, `done.md` | Not a git repo | Already initialized |
| `maestro discuss <prompt>` | AI codebase analysis | User prompt, codebase files | AI discussion output, structured JSON | Invalid JSON from AI | AI misunderstands (user corrects) |
| `maestro reconstruct --strategy=<git\|snapshot>` | Reconstruct past work | Git log OR codebase snapshot | `completed tasks in JSON` populated | None | Ambiguous history (user reviews) |
| `maestro build` | Trigger build, capture output | Build system config | Build log, parsed errors/warnings | None | Build fails (expected; creates issues) |
| `maestro build --create-issues` | Build + generate issues/tasks | Build errors | `issue data*.md`, `docs/maestro/tasks/*.json` | None | No errors to parse |
| `maestro task rank-dependencies` | Order tasks by dependencies | Task set with error context | Updated tasks with `dependencies` field, ranked `todo.md` | Unresolvable circular deps | Ambiguous deps (AI guesses) |
| `maestro task next` | Get next actionable task | `active tasks in JSON` | Task ID and details | None | No tasks available |
| `maestro task fix <task-id>` | AI-assisted fix | Task ID, issue context | Proposed code changes (JSON), applied changes | Invalid JSON from AI, validation fails | Fix doesn't resolve issue (rebuild detects) |
| `maestro task complete <task-id>` | Mark task done | Task ID | Task moved to `completed tasks in JSON`, status updated | Task not found | None |
| `maestro run` | Execute app, capture logs | Built application | Runtime log | None | Runtime errors (expected; creates issues) |
| `maestro run --create-issues` | Run + generate issues/tasks | Runtime errors | `issue data*.md`, `docs/maestro/tasks/*.json` | None | No errors to parse |

---

## Tests Implied by This Scenario

### Unit Tests

1. **Command Builders**:
   - `test_init_creates_directory_structure()`
   - `test_init_fails_if_not_git_repo()`
   - `test_init_idempotent_if_already_initialized()`

2. **Parsers**:
   - `test_parse_rust_cargo_errors()`
   - `test_parse_go_build_errors()`
   - `test_parse_gcc_clang_errors()`
   - `test_parse_runtime_panic_stack_traces()`

3. **Dependency Ordering**:
   - `test_rank_tasks_simple_chain()`
   - `test_rank_tasks_diamond_dependencies()`
   - `test_detect_circular_dependencies()`

4. **JSON Validation**:
   - `test_ai_json_response_valid()`
   - `test_ai_json_response_invalid_hard_stop()`

### Integration Tests

1. **Fixture Repos**:
   - `fixture_rust_compile_fail`: Rust project with deliberate compile errors
   - `fixture_go_missing_imports`: Go project with missing imports
   - `fixture_cpp_linking_error`: C++ project with linking issues
   - `fixture_runtime_panic`: Rust project that panics at runtime

2. **End-to-End Scenarios**:
   - `test_scenario_01_full_workflow()`: Run entire WF-01 on fixture repo, verify:
     - `docs/` structure created
     - Errors parsed into issues
     - Tasks created with dependencies
     - `active tasks in JSON` and `completed tasks in JSON` populated correctly

3. **Warnings Policy**:
   - `test_warnings_threshold_enforced()`: Verify warnings above threshold create issues
   - `test_warnings_below_threshold_ignored()`: Verify minor warnings are logged but not issues

### Golden Logs (Example Sessions)

1. **Golden Log: Rust Compile Fail**:
   - Input: Fixture repo with 3 compile errors
   - Expected output:
     - 3 issues created
     - 3 tasks created with dependency ranking
     - `active tasks in JSON` shows correct order

2. **Golden Log: Clean Build**:
   - Input: Fixture repo with no errors
   - Expected output:
     - Build log shows success
     - No issues/tasks created
     - Scenario exits at Phase 4

3. **Golden Log: Runtime Panic**:
   - Input: Fixture repo that compiles but panics
   - Expected output:
     - Build succeeds
     - Runtime error captured
     - Issue created from panic stack trace

---

## Linking & Terminology

### Relationship to Track/Phase/Task Model

- **Tracks**: This scenario may create multiple tracks:
  - `bootstrap` track (initial setup)
  - `bugfix` track (fixing build errors)

- **Phases**: Each track contains phases:
  - `bootstrap` track:
    - Phase `bs1`: Maestro initialization
    - Phase `bs2`: Codebase understanding
    - Phase `bs3`: Past work reconstruction
  - `bugfix` track:
    - Phase `bf1`: Build error fixes
    - Phase `bf2`: Runtime error fixes

- **Tasks**: Atomic units of work within phases:
  - `TASK-001` in phase `bf1`: "Fix undefined symbol `process_data`"

### Truth File Boundaries

- **Truth Files** (validated, protected):
  - `docs/maestro/index.json`
  - `docs/maestro/tracks/*.json`
  - `docs/maestro/phases/*.json`
  - `docs/maestro/tasks/*.json`
  - `issue data*.md` (structured front-matter required)
  - `active tasks in JSON` (specific format enforced)
  - `completed tasks in JSON` (specific format enforced)

- **Non-Truth Files**:
  - Build logs: `docs/build.log`, `docs/runtime.log` (informational only)
  - AI context: `docs/context.json` (may be regenerated)

### AI Interaction Boundaries

- AI operates **via Maestro-mediated channels**:
  - AI produces structured JSON (plans, task fixes, understanding)
  - Maestro validates JSON schema before accepting
  - Invalid JSON is a **hard stop** (blocks continuation)
  - AI may propose changes, but changes are applied through:
    - Maestro's validation layer (syntax checks, file existence checks)
    - Rule-based asserts (not AI-driven decisions)

- AI does **not** directly mutate project state:
  - AI does not write files directly
  - All mutations go through Maestro commands (e.g., `maestro task create`, `maestro build --create-issues`)

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-12-25 | Initial creation | Claude Sonnet 4.5 |

---

## Related Documentation

- [index.md](index.md) - Scenario directory
- [README.md](README.md) - Workflow conventions
- [scenario_01_existing_repo_single_main.puml](scenario_01_existing_repo_single_main.puml) - Visual diagram
- [../CLAUDE.md](../CLAUDE.md) - Agent instructions and policy requirements

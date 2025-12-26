# EX-05: `maestro discuss` Pipeline Decomposed — Context→Prompt→Stream→Parse→Apply

**Scope**: AI/discuss layer internals
**Build System**: N/A (AI pipeline mechanics)
**Languages**: N/A (conceptual)
**Outcome**: Document the multi-stage pipeline of `maestro discuss` showing how it conceptually works from user input to repo truth mutation

---

## Scenario Summary

Developer runs `maestro discuss` in a task context. Maestro internally executes a multi-stage pipeline: select context → build prompt with JSON contract → stream AI responses → detect `/done` → request final JSON → validate schema → apply actions to repo truth → persist session logs. This example decomposes each stage as a conceptual "what AI commands do" runbook.

This demonstrates **discuss as a testable pipeline** rather than a black box.

---

## Preconditions

- Maestro initialized (`./docs/maestro/**` exists)
- At least one track/phase/task exists (or discuss runs in repo context)
- AI engine available (e.g., Qwen, Gemini, Claude, Codex)

---

## Pipeline Stages (Conceptual Decomposition)

### Stage 1: Select Context

**Conceptual function**: `select_context()`

**What happens**:
- Determine current context: repo / track / phase / task
- Load relevant JSON files from `./docs/maestro/**`
- If task context: load task, phase, track, workflow (if linked), runbook (if linked)
- Build context object with metadata

**Gates**: (none - read-only)
**Stores read**: REPO_TRUTH_DOCS_MAESTRO

### Stage 2: Build Prompt

**Conceptual function**: `build_prompt(context, contract_schema, cookies)`

**What happens**:
- Construct system prompt with:
  - Context summary (task goal, related workflow nodes, runbook steps)
  - JSON contract schema (what fields AI must return)
  - Work session cookie (if in `maestro work` mode)
  - Instructions for `/done` and `/quit`
- Add user message or conversation history

**Gates**: (none - preparation)
**Stores read**: REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX (for cookies)

### Stage 3: Run Engine

**Conceptual function**: `run_ai_engine(prompt, engine_name, session_id)`

**What happens**:
- Invoke AI engine manager (see EX-06 for details)
- Pass prompt via stdin or temp file (Claude uses stdin, others use temp files)
- Engine streams JSON events + assistant text
- Session ID allows resume

**Gates**: (none - external call)
**Stores write**: (temp session files)

### Stage 4: Stream Events

**Conceptual function**: `stream_and_display(engine_output)`

**What happens**:
- Read streamed output line-by-line
- Display assistant messages to user in real-time
- Buffer JSON fragments (may be interleaved with text)
- Detect end conditions: `/done` (user), `/quit` (user), or stream EOF

**Gates**: (none - display only)
**Stores write**: (buffer in memory)

### Stage 5: Detect End Condition and Request Final JSON

**Conceptual function**: `on_done_request_json()`

**What happens**:
- User types `/done` → trigger final JSON request
- Send follow-up prompt: "Please provide your response in the following JSON format: {...schema...}"
- AI responds with JSON block
- If user types `/quit`: abort without applying changes

**Gates**: (none - interaction)
**Stores write**: (none yet)

### Stage 6: Extract and Parse JSON

**Conceptual function**: `extract_json_from_response(response_text)`

**What happens**:
- Search response for JSON block (usually in ```json...``` code fence)
- Extract JSON string
- Attempt `json.loads()`
- If parse fails → go to Stage 10 (error handling)

**Gates**: **JSON_CONTRACT_GATE** (hard fail if invalid)
**Stores write**: (none)

### Stage 7: Validate Schema

**Conceptual function**: `validate_against_schema(json_obj, contract_schema)`

**What happens**:
- Check required fields present
- Validate field types (string, array, object, etc.)
- If validation fails → go to Stage 10 (error handling)

**Gates**: **JSON_CONTRACT_GATE** (hard fail if invalid)
**Stores write**: (none)

### Stage 8: Apply Actions to Repo Truth

**Conceptual function**: `apply_actions_to_repo_truth(validated_json)`

**What happens**:
- For each action in JSON (e.g., `create_task`, `update_phase`, `add_issue`):
  - Write/update corresponding JSON file in `./docs/maestro/**`
  - Update indices if needed
- Atomic: all actions succeed or none applied (transaction-like)

**Gates**: REPOCONF_GATE
**Stores write**: REPO_TRUTH_DOCS_MAESTRO

### Stage 9: Persist Logs and Breadcrumbs

**Conceptual function**: `persist_session(session_id, stream_log, breadcrumbs)`

**What happens**:
- Write full conversation stream to session log (for resume)
- Append breadcrumbs to IPC mailbox (if work session active)
- Store session metadata

**Gates**: (none)
**Stores write**: IPC_MAILBOX (breadcrumbs), session logs (somewhere in HOME or repo)

### Stage 10: Error Handling (Invalid JSON or Schema Failure)

**Conceptual function**: `handle_json_error(error_msg)`

**What happens**:
- Display error to user: "Invalid JSON response from AI"
- Abort mutation (no repo truth changes)
- Offer options:
  - Resume session and retry (`TODO_CMD: maestro discuss --resume <session>`)
  - Switch engine
  - Manually fix and retry

**Gates**: (aborted at JSON_CONTRACT_GATE)
**Stores write**: (none - rollback)

---

## Runbook Steps (User Perspective)

### Step 1: Start Discuss Session

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro discuss` | Start AI discussion in current context (repo/task) | Discuss session begins, AI responds |

**Internal**: Stages 1-4 execute (select context → build prompt → run engine → stream events)

### Step 2: User Interacts with AI

| User Input | Intent | Expected |
|------------|--------|----------|
| "Help me plan next steps for this task" | Ask AI for planning | AI responds with suggestions |

**Internal**: Stage 4 (stream events) continues

### Step 3: User Signals Completion

| User Input | Intent | Expected |
|------------|--------|----------|
| `/done` | Signal AI to finalize and return JSON | AI receives "final JSON request" prompt |

**Internal**: Stage 5 (detect end condition and request final JSON)

### Step 4: AI Returns JSON

**AI Response** (example):
```json
{
  "actions": [
    {"type": "create_task", "phase_id": "phase-001", "title": "Implement feature X"},
    {"type": "update_task", "task_id": "task-001", "status": "in_progress"}
  ],
  "summary": "Created 1 task, updated 1 task status"
}
```

**Internal**: Stages 6-7 (extract/parse → validate schema)

### Step 5: Actions Applied

**System Output**: "Applied 2 actions. Updated repo truth."

**Internal**: Stage 8 (apply actions to repo truth)

### Step 6: Session Persisted

**Internal**: Stage 9 (persist logs and breadcrumbs)

---

## AI Perspective (Heuristic)

**What AI notices**:
- System prompt includes JSON schema contract → must return structured data
- `/done` command triggers → time to synthesize final response as JSON
- Work session cookie present → append breadcrumbs via `maestro wsession breadcrumb`

**What AI tries**:
- Generate helpful suggestions during interactive phase
- When `/done` received, format all actions as valid JSON matching schema
- Avoid returning malformed JSON (will cause hard fail)

**Where AI tends to hallucinate**:
- May return JSON with extra fields not in schema (usually tolerated if required fields present)
- May forget to wrap JSON in code fence (extraction may fail)
- May return empty `actions: []` when it should have at least one action

---

## Outcomes

### Outcome A: Success — Valid JSON, Actions Applied

**Flow**:
1. User runs `maestro discuss`
2. AI interaction completes
3. User types `/done`
4. AI returns valid JSON
5. Schema validates
6. Actions applied to `./docs/maestro/**`
7. Session persisted

**Artifacts**:
- Updated JSON files in `./docs/maestro/tasks/`, `./docs/maestro/phases/`, etc.
- Session log (for resume)
- Breadcrumbs in IPC mailbox (if work session)

### Outcome B: Invalid JSON — Hard Fail, Abort, Retry

**Flow**:
1. User runs `maestro discuss`
2. User types `/done`
3. AI returns malformed JSON (syntax error)
4. Stage 6 fails: `json.loads()` throws exception
5. System aborts: "Invalid JSON response from AI"
6. No repo truth mutation
7. User options:
   - `TODO_CMD: maestro discuss --resume <session>` and retry
   - Switch to different engine
   - Manually inspect session log and debug

**Artifacts**:
- Session log preserved (for debugging)
- No changes to `./docs/maestro/**`

### Outcome C: Invalid Schema — Hard Fail, Missing Required Fields

**Flow**:
1. AI returns syntactically valid JSON
2. Stage 7 fails: required field `actions` missing
3. System aborts: "JSON schema validation failed: missing required field 'actions'"
4. No repo truth mutation
5. User retries with clearer prompt

### Outcome D: User Quits Early

**Flow**:
1. User types `/quit` instead of `/done`
2. Session aborts without requesting final JSON
3. No actions applied
4. Session log saved (conversation preserved)

---

## Conceptual "What AI Commands Do" Sub-Runbooks

### `select_context()`

**Purpose**: Determine where in the Maestro hierarchy we are (repo / track / phase / task)

**Steps**:
1. Check current working directory for `./docs/maestro/`
2. If current shell/session has task context → load task JSON
3. If task has `phase_id` → load phase JSON
4. If phase has `track_id` → load track JSON
5. If task has `workflow_id` → load workflow JSON
6. Return context object with all loaded metadata

### `build_prompt(context, contract_schema, cookies)`

**Purpose**: Construct the full AI prompt with context and contract

**Steps**:
1. Start with system message template
2. Inject context summary: "You are helping with task-001: 'Implement login endpoint'"
3. Append JSON contract schema definition
4. Add instructions: "When user types /done, return JSON with these fields: {schema}"
5. If work session cookie exists: "You may call `maestro wsession breadcrumb` with cookie: <cookie>"
6. Return complete prompt

### `extract_json_from_response(response_text)`

**Purpose**: Pull JSON block from AI's text response

**Steps**:
1. Search for ```json...``` code fence
2. If found: extract content between fence markers
3. If not found: search for raw JSON (starts with `{`, ends with `}`)
4. Return extracted JSON string or raise error

### `validate_against_schema(json_obj, contract_schema)`

**Purpose**: Ensure AI's JSON matches required contract

**Steps**:
1. For each required field in schema: check `field in json_obj`
2. For each field: check type matches (string, array, etc.)
3. If validation fails: raise error with details
4. Return validated JSON object

### `apply_actions_to_repo_truth(validated_json)`

**Purpose**: Mutate `./docs/maestro/**` based on AI's actions

**Steps**:
1. Begin transaction (track all file writes for potential rollback)
2. For each action in `validated_json['actions']`:
   - `create_task`: generate task ID, write `./docs/maestro/tasks/task-<id>.json`
   - `update_task`: load existing task JSON, merge updates, write back
   - `create_issue`: write to `./docs/maestro/issues/`
3. Update indices (task lists, phase membership, etc.)
4. Commit transaction (all writes succeed) or rollback on error

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "TODO_CMD: maestro discuss --resume <session-id>"
  - "TODO_CMD: maestro discuss --context task <task-id>"
  - "TODO_CMD: exact format of JSON contract schema"
  - "TODO_CMD: how session IDs are generated and stored"
  - "TODO_CMD: whether discuss supports --engine <name> flag"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro discuss"
    intent: "Start AI discussion in current context"
    gates: ["JSON_CONTRACT_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO", "IPC_MAILBOX"]
    stores_read: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["select_context", "build_prompt", "run_ai_engine", "stream_and_display"]
    cli_confidence: "low"  # TODO_CMD for exact flags

  - user: "/done"
    intent: "User signals completion, triggers final JSON request"
    gates: ["JSON_CONTRACT_GATE"]
    stores_write: []
    stores_read: []
    internal: ["on_done_request_json"]
    cli_confidence: "medium"  # /done is standard but may vary

  - internal: "extract_json_from_response(response)"
    intent: "Parse AI's JSON response"
    gates: ["JSON_CONTRACT_GATE"]
    stores_write: []
    internal: ["json.loads", "validate_against_schema"]
    cli_confidence: "N/A"  # internal function

  - internal: "apply_actions_to_repo_truth(validated_json)"
    intent: "Mutate repo truth files based on validated actions"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["write task JSON", "update indices"]
    cli_confidence: "N/A"  # internal function
```

---

**Related:** AI/discuss mechanics, JSON contract enforcement, pipeline decomposition
**Status:** Proposed

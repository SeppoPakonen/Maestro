# EX-08: JSON Contract Hard-Fail — Reprompt & Recover Path

**Scope**: JSON contract enforcement and error recovery
**Build System**: N/A (error handling mechanics)
**Languages**: N/A (conceptual)
**Outcome**: Document the "hard gate" behavior when AI returns invalid JSON, showing how Maestro aborts operations and user can retry/recover

---

## Scenario Summary

Developer runs `maestro discuss` and the AI returns invalid JSON (syntax error or missing required fields). Maestro **hard-fails** at the JSON_CONTRACT_GATE, aborts the operation without mutating repo truth, and provides recovery options (resume session, reprompt, switch engine).

This demonstrates **JSON contract as a hard gate** rather than a tolerated failure.

---

## Preconditions

- Maestro initialized
- Task context exists
- AI engine available (prone to returning malformed JSON for this example)

---

## The JSON Contract Hard-Fail Principle

**Key rule**: If AI returns invalid JSON or JSON that fails schema validation, Maestro **aborts the entire operation**. No partial state mutation occurs.

**Why hard-fail**:
- Prevents corrupt repo truth from bad AI responses
- Forces explicit retry/recovery rather than silent failure
- Makes contract violations visible to user

**Not tolerated**: Malformed JSON is never "fixed automatically" or ignored.

---

## Runbook Steps

### Step 1: Start Discuss Session

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro discuss` | Start AI discussion in current context | AI session begins |

**Internal**: Context loaded, prompt built with JSON contract schema.

### Step 2: User Interacts, Signals /done

| User Input | Intent | Expected |
|------------|--------|----------|
| "Help me create 3 subtasks for this feature" | Ask AI for planning | AI responds with suggestions |
| `/done` | Signal completion, request final JSON | AI returns JSON... |

### Step 3: AI Returns Invalid JSON (Syntax Error)

**AI Response**:
```
Sure! Here's my suggested plan:

```json
{
  "actions": [
    {"type": "create_task", "title": "Design API endpoint",  # <- SYNTAX ERROR: trailing comma
    {"type": "create_task", "title": "Implement auth"},
    {"type": "create_task", "title": "Write tests"}
  ],
  "summary": "Created 3 subtasks"
}
```
```

**Problem**: Extra comma after first action → invalid JSON

### Step 4: Maestro Detects JSON Parse Failure

**Internal**: `extract_json_from_response(response)` → `json.loads()` throws `JSONDecodeError`

**System Output**:
```
ERROR: Invalid JSON response from AI

Parse failed at line 3, column 60:
  Expecting ',' delimiter

Raw JSON:
{
  "actions": [
    {"type": "create_task", "title": "Design API endpoint",
    {"type": "create_task", "title": "Implement auth"},
    ...
```

### Step 5: Operation Aborted (No Repo Truth Mutation)

**System Output**:
```
Operation ABORTED at JSON_CONTRACT_GATE

No changes applied to ./docs/maestro/**

Session preserved: session-20250126-001
```

**Gates**: JSON_CONTRACT_GATE (FAILED)
**Stores write**: (none - rollback)

### Step 6: User Chooses Recovery Path

**Option A: Resume and Retry**

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro discuss resume session-20250126-001` | Continue previous session | Session restored, user can reprompt |

**User action**:
- User sends clearer prompt: "Please return valid JSON with no syntax errors"
- AI retries with correct JSON

**Option B: Switch Engine**

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro discuss --engine gemini` | Retry with different AI engine | Gemini session starts |

**Rationale**: Maybe Qwen is prone to JSON errors, try Gemini instead.

**Option C: Manual Inspection and Debug**

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro session log session-20250126-001` | View full conversation log | See exactly what AI returned |

**User inspects** raw AI response, identifies syntax error, provides feedback to AI.

---

## Alternative Failure: Invalid Schema (Missing Required Fields)

### Step 3b: AI Returns Syntactically Valid JSON, But Missing Fields

**AI Response**:
```json
{
  "summary": "Created 3 subtasks"
}
```

**Problem**: Missing required field `actions`

### Step 4b: Maestro Detects Schema Validation Failure

**Internal**: `validate_against_schema(json_obj, contract_schema)` → raises error

**System Output**:
```
ERROR: JSON schema validation failed

Missing required field: 'actions'

Expected schema:
{
  "actions": [array of action objects],
  "summary": "string"
}

Received:
{
  "summary": "Created 3 subtasks"
}

Operation ABORTED at JSON_CONTRACT_GATE
```

**Gates**: JSON_CONTRACT_GATE (FAILED)
**Stores write**: (none - rollback)

---

## Recovery Workflow (Quick Recovery Path)

### Scenario: AI Re-Answers Correctly on Retry

**Flow**:
1. First attempt: AI returns invalid JSON → hard-fail
2. User resumes: `maestro discuss --resume session-20250126-001`
3. User says: "The JSON was invalid. Please try again with correct syntax."
4. AI returns valid JSON
5. Schema validation passes
6. Actions applied to repo truth

**Artifacts**:
- Session log shows both attempts (failed + successful)
- Final repo truth mutation only from successful attempt

---

## AI Perspective (Heuristic)

**What AI notices**:
- JSON contract schema in system prompt → must match exactly
- Parse errors cause hard-fail → be careful with syntax
- Missing required fields cause validation failure → include all fields

**What AI tries**:
- Generate JSON matching the exact schema provided
- Avoid trailing commas, unclosed brackets, quote mismatches
- Include all required fields, even if empty arrays

**Where AI tends to hallucinate**:
- May add extra fields not in schema (usually tolerated if required fields present)
- May use wrong JSON types (string vs array)
- May forget code fence markers (``json) around JSON

---

## Outcomes

### Outcome A: Quick Recovery — AI Re-Answers Correctly

**Flow**:
1. Invalid JSON → hard-fail
2. User resumes session
3. AI returns valid JSON
4. Actions applied

**Duration**: ~30 seconds

### Outcome B: Repeated Failure — User Switches Engine

**Flow**:
1. Invalid JSON from Qwen → hard-fail
2. User resumes, reprompts
3. Invalid JSON again (Qwen struggling)
4. User switches to Gemini: `maestro discuss --engine gemini`
5. Gemini returns valid JSON
6. Success

**Duration**: ~2 minutes

### Outcome C: Manual Debug — User Inspects Session Log

**Flow**:
1. Invalid JSON → hard-fail
2. User views session log: `maestro session log session-20250126-001`
3. User sees AI returned JSON with trailing comma
4. User provides specific feedback: "Remove the comma after 'Design API endpoint'"
5. AI fixes and returns valid JSON
6. Success

---

## No Partial State Mutation (Critical Principle)

**Guaranteed**: If JSON contract fails, **no actions are applied**.

**Example**:
- AI returns JSON with 5 actions
- 4th action has a syntax error
- Result: **0 actions applied** (not 3 out of 5)

**Reason**: Atomic transaction model — all or nothing.

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "maestro discuss resume <session-id>"
  - "TODO_CMD: maestro discuss --engine <engine-name>"
  - "TODO_CMD: maestro session log <session-id>"
  - "TODO_CMD: exact JSON schema definition for discuss contract"
  - "TODO_CMD: whether there's a --force-apply flag (probably shouldn't exist)"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "/done (in maestro discuss)"
    intent: "User signals completion, AI should return JSON"
    gates: ["JSON_CONTRACT_GATE"]
    stores_write: []  # No writes yet, pending JSON validation
    internal: ["on_done_request_json"]
    cli_confidence: "medium"

  - internal: "extract_json_from_response(response)"
    intent: "Parse AI's JSON response"
    gates: ["JSON_CONTRACT_GATE"]
    stores_write: []
    internal: ["json.loads"]
    result: "FAIL: JSONDecodeError"
    cli_confidence: "N/A"

  - system: "Operation ABORTED at JSON_CONTRACT_GATE"
    intent: "Hard-fail on invalid JSON, no repo truth mutation"
    gates: ["JSON_CONTRACT_GATE"]
    stores_write: []  # Rollback
    internal: ["abort_transaction"]
    cli_confidence: "N/A"

  - user: "maestro discuss --resume session-20250126-001"
    intent: "Resume session and retry after JSON failure"
    gates: ["JSON_CONTRACT_GATE"]
    stores_read: ["SESSION_STORAGE"]
    internal: ["load_session", "retry_prompt"]
    cli_confidence: "low"  # TODO_CMD

  - internal: "validate_against_schema(json_obj)"
    intent: "Validate JSON against contract schema"
    gates: ["JSON_CONTRACT_GATE"]
    result: "SUCCESS or FAIL depending on schema match"
    cli_confidence: "N/A"
```

---

**Related:** JSON contract enforcement, hard-fail gates, error recovery, atomic transactions
**Status:** Proposed

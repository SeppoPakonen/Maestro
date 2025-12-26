# EX-06: `maestro ai <engine>` and Engine Manager — Non-Interactive, Resume, Stream-JSON

**Scope**: AI engine infrastructure layer
**Build System**: N/A (AI engine mechanics)
**Languages**: N/A (conceptual)
**Outcome**: Document the "AI is four instruments" model, engine adapter behavior, resume mechanics, verbose vs non-verbose modes

---

## Scenario Summary

Developer runs `maestro ai qwen` to interact directly with an AI engine (bypassing `maestro discuss` orchestration). Maestro's engine manager selects the Qwen adapter, invokes the external binary, handles stdin/temp-file differences between engines, supports session resume, and offers verbose mode for debugging.

This demonstrates **AI engines as pluggable adapters** with consistent interface despite different underlying behaviors.

---

## Preconditions

- At least one AI engine binary available:
  - `qwen-code` (in `$HOME/Dev/Maestro/external/ai-agents/qwen-code/`)
  - `gemini-cli` (in `$HOME/Dev/Maestro/external/ai-agents/gemini-cli/`)
  - `claude` (system-wide or in PATH)
  - `codex` (TODO: exact path uncertain)

---

## The "Four Instruments" Model

Maestro supports four AI engines as interchangeable adapters:

| Engine | Binary | Stdin/TempFile | Resume | Stream | Notes |
|--------|--------|----------------|--------|--------|-------|
| **Qwen** | `qwen-code` | temp-file | Yes | JSON events | Local/offline-capable |
| **Gemini** | `gemini-cli` | temp-file | Yes | JSON events | Cloud API |
| **Claude** | `claude` | **stdin** | Yes | Text stream | Anthropic's official CLI (stdin special case) |
| **Codex** | `codex` | temp-file | Yes | JSON events | OpenAI (if available) |

**Key Difference**: Claude reads from stdin, others read from temp file.

---

## Engine Manager Conceptual Architecture

**Conceptual function**: `engine_manager.run(engine_name, prompt, session_id=None)`

**What it does**:
1. Validate engine availability (check binary exists)
2. Select adapter based on `engine_name`
3. Prepare prompt (stdin vs temp-file)
4. Invoke engine binary
5. Stream output (JSON events or text)
6. Handle resume if `session_id` provided

---

## Runbook Steps

### Step 1: Run AI Engine Directly (Non-Interactive)

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro ai qwen` | Start Qwen engine in interactive mode | Qwen prompt appears, user can chat |

**Internal**:
- Engine manager selects Qwen adapter
- Writes prompt to temp file: `/tmp/maestro-qwen-<session>.txt`
- Invokes: `qwen-code --session <session> --input /tmp/maestro-qwen-<session>.txt`
- Streams JSON events to stdout

**Gates**: (none)
**Stores**: (temp session files)

### Step 2: Run with Specific Prompt (Non-Interactive)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro ai qwen --prompt "Explain how to use argparse"` | Send single prompt, get response | Qwen responds, exits |

**Internal**:
- Non-interactive mode
- Write prompt to temp file
- Invoke engine
- Display response
- Exit

### Step 3: Resume Previous Session

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro ai qwen --resume <session-id>` | Continue previous conversation | Session restored, user can continue |

**Internal**:
- Load session state from `$HOME/.maestro/sessions/<session-id>/`
- Append new prompt to conversation history
- Invoke engine with full history

**Gates**: (none)
**Stores read**: Session storage (HOME or repo)

### Step 4: Verbose Mode (Show Engine Command)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro ai qwen --verbose` | Show actual engine invocation | Prints command before execution |

**Output example**:
```
[VERBOSE] Running: /home/user/Dev/Maestro/external/ai-agents/qwen-code/qwen-code --session abc123 --input /tmp/maestro-qwen-abc123.txt
[VERBOSE] Streaming JSON events...
```

### Step 5: Switch Engine (Compare Behavior)

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro ai gemini` | Switch to Gemini engine | Gemini responds with same interface |

**Internal**:
- Engine manager selects Gemini adapter
- Same temp-file behavior as Qwen
- Different underlying API (cloud vs local)

### Step 6: Claude Special Case (Stdin)

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro ai claude` | Use Claude engine | Claude reads from stdin, not temp file |

**Internal**:
- Engine manager selects Claude adapter
- Pipes prompt via stdin: `echo "$PROMPT" | claude`
- Streams text output (not JSON events)

---

## AI Engine Adapter Implementations (Conceptual)

### Qwen Adapter

**Conceptual class**: `QwenAdapter`

**Methods**:
```python
def prepare_input(prompt: str, session_id: str) -> str:
    temp_file = f"/tmp/maestro-qwen-{session_id}.txt"
    write_file(temp_file, prompt)
    return temp_file

def invoke(input_file: str, session_id: str) -> subprocess.Popen:
    cmd = [QWEN_BIN, "--session", session_id, "--input", input_file]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def stream_output(process: subprocess.Popen):
    for line in process.stdout:
        event = json.loads(line)  # Qwen outputs JSON events
        if event['type'] == 'message':
            print(event['content'])
```

### Claude Adapter

**Conceptual class**: `ClaudeAdapter`

**Methods**:
```python
def prepare_input(prompt: str, session_id: str) -> str:
    return prompt  # No temp file, return prompt directly

def invoke(prompt: str, session_id: str) -> subprocess.Popen:
    cmd = ["claude"]  # Claude binary
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    process.stdin.write(prompt.encode())
    process.stdin.close()
    return process

def stream_output(process: subprocess.Popen):
    for line in process.stdout:
        print(line.decode(), end='')  # Claude streams text, not JSON
```

---

## AI Stacking Mode (Managed vs Handsoff)

**Concept**: Maestro can operate in two AI stacking modes (policy setting):

| Mode | Behavior | JSON Contract | Usage |
|------|----------|---------------|-------|
| **managed** | AI must return structured JSON | Enforced via JSON_CONTRACT_GATE | Default for `maestro discuss` |
| **handsoff** | AI can return freeform text | No contract enforcement | Used for `maestro ai <engine>` direct calls |

**When mode matters**:
- `maestro discuss` → **managed mode** → expects JSON with actions
- `maestro ai qwen` → **handsoff mode** → accepts any response

---

## AI Perspective (Heuristic)

**What AI notices**:
- Engine invocation via adapter → different binaries, same interface
- Resume flag → session state loaded, conversation continues
- Verbose mode → see actual command executed (useful for debugging)

**What AI tries**:
- Generate response based on prompt
- If in managed mode: return JSON matching contract
- If in handsoff mode: return freeform text

**Where AI tends to hallucinate**:
- May assume all engines support the same flags (they don't - adapters normalize)
- May forget Claude uses stdin (not temp file)

---

## Outcomes

### Outcome A: Success — Qwen Responds

**Flow**:
1. User runs `maestro ai qwen`
2. Engine manager validates `qwen-code` binary exists
3. Creates temp file with prompt
4. Invokes Qwen
5. Streams JSON events, displays messages
6. Session saved for resume

**Artifacts**:
- Session state: `$HOME/.maestro/sessions/<session-id>/`

### Outcome B: Engine Missing → Graceful Error

**Flow**:
1. User runs `maestro ai codex`
2. Engine manager checks for `codex` binary
3. Binary not found
4. Error: "Engine 'codex' not available. Please install codex or use a different engine."
5. Suggests available engines: qwen, gemini, claude

### Outcome C: Resume Works → Continue Conversation

**Flow**:
1. User had previous session `session-abc123` with Qwen
2. User runs `maestro ai qwen --resume session-abc123`
3. Engine manager loads session history
4. User adds new message
5. Qwen responds with full context from previous session

---

## Permissions and Safety

**Note**: The original task mentioned "dangerously skip permissions" flag. This is a policy mention without deep security implementation:

- **Concept**: Some engines may require API keys or auth
- **Skip flag**: `--dangerously-skip-permissions` (if it exists) bypasses auth checks
- **Use case**: Trusted environments, testing, offline engines
- **Not covered deeply here**: Security is acknowledged but not the focus

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "TODO_CMD: maestro ai <engine> --prompt <text>"
  - "TODO_CMD: maestro ai <engine> --resume <session-id>"
  - "TODO_CMD: maestro ai <engine> --verbose"
  - "TODO_CMD: exact binary paths for all engines"
  - "TODO_CMD: how session IDs are generated"
  - "TODO_CMD: where session state is stored (HOME vs repo)"
  - "TODO_CMD: --dangerously-skip-permissions flag (if exists)"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro ai qwen"
    intent: "Run Qwen AI engine directly (handsoff mode)"
    gates: []
    stores_write: ["SESSION_STORAGE"]
    stores_read: []
    internal: ["engine_manager.select_adapter", "QwenAdapter.invoke", "stream_output"]
    cli_confidence: "low"  # TODO_CMD for exact flags

  - user: "maestro ai qwen --resume session-abc123"
    intent: "Resume previous Qwen session"
    gates: []
    stores_write: ["SESSION_STORAGE"]
    stores_read: ["SESSION_STORAGE"]
    internal: ["engine_manager.load_session", "QwenAdapter.invoke"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro ai claude"
    intent: "Run Claude engine (stdin special case)"
    gates: []
    stores_write: ["SESSION_STORAGE"]
    internal: ["engine_manager.select_adapter", "ClaudeAdapter.invoke_stdin"]
    cli_confidence: "low"  # TODO_CMD
```

---

**Related:** AI engine infrastructure, adapter pattern, stdin vs temp-file, session resume
**Status:** Proposed

#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-05: `maestro discuss` Pipeline Decomposed — Context→Prompt→Stream→Parse→Apply

# Conceptual Pipeline (Internal Stages)

echo "=== Stage 1: Select Context ==="
# INTERNAL: select_context()
# Determines current context (repo/track/phase/task)
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: (none)

echo "Current context: task-001 (in phase-001, track-001)"
echo "Loaded: task.json, phase.json, track.json"

echo ""
echo "=== Stage 2: Build Prompt ==="
# INTERNAL: build_prompt(context, contract_schema, cookies)
# Constructs AI prompt with JSON contract
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO, IPC_MAILBOX (cookies)
# GATES: (none)

echo "Prompt built with:"
echo "  - Context summary: task-001 'Implement login endpoint'"
echo "  - JSON contract schema: {actions: [...], summary: string}"
echo "  - Work session cookie: <cookie-abc123>"

echo ""
echo "=== Stage 3: Run Engine ==="
# INTERNAL: run_ai_engine(prompt, engine_name, session_id)
# Invokes AI engine manager
# STORES_WRITE: (temp session files)
# GATES: (none)

echo "Running AI engine: qwen"
echo "Session ID: session-20250126-001"

echo ""
echo "=== User Interaction Begins ==="

# Step 1: Start Discuss Session
run maestro discuss
# EXPECT: AI responds, stream starts
# STORES_WRITE: IPC_MAILBOX (session state)
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: JSON_CONTRACT_GATE (eventual)
# INTERNAL: Stages 1-4 (select context → build prompt → run engine → stream events)

echo ""
echo "AI: Hello! I see you're working on task-001: 'Implement login endpoint'."
echo "AI: How can I help you plan this task?"

# Step 2: User Interacts
echo ""
echo "User: Help me break this down into subtasks"
echo ""
echo "AI: I suggest creating these subtasks:"
echo "AI: 1. Design API endpoint schema"
echo "AI: 2. Implement password hashing"
echo "AI: 3. Add JWT token generation"
echo "AI: 4. Write unit tests"

# Step 3: User Signals Completion
echo ""
echo "User: /done"
# EXPECT: AI receives final JSON request prompt
# INTERNAL: Stage 5 (detect end condition and request final JSON)

echo ""
echo "=== Stage 5: Detect End Condition and Request Final JSON ==="
# INTERNAL: on_done_request_json()
# Sends follow-up prompt requesting JSON
# GATES: (none)

echo "System sends to AI: 'Please provide your response in JSON format with schema: {...}'"

# Step 4: AI Returns JSON
echo ""
echo "=== AI Response (with JSON) ==="
echo "AI: Here's my suggested plan in JSON format:"
echo ""
echo '```json'
echo '{'
echo '  "actions": ['
echo '    {"type": "create_task", "phase_id": "phase-001", "title": "Design API endpoint schema"},'
echo '    {"type": "create_task", "phase_id": "phase-001", "title": "Implement password hashing"},'
echo '    {"type": "create_task", "phase_id": "phase-001", "title": "Add JWT token generation"},'
echo '    {"type": "create_task", "phase_id": "phase-001", "title": "Write unit tests"}'
echo '  ],'
echo '  "summary": "Created 4 subtasks for login endpoint implementation"'
echo '}'
echo '```'

echo ""
echo "=== Stage 6: Extract and Parse JSON ==="
# INTERNAL: extract_json_from_response(response_text)
# Parses JSON from AI response
# GATES: JSON_CONTRACT_GATE (hard fail if invalid)

echo "Extracting JSON from code fence..."
echo "Parsing with json.loads()..."
echo "Parse successful!"

echo ""
echo "=== Stage 7: Validate Schema ==="
# INTERNAL: validate_against_schema(json_obj, contract_schema)
# Validates required fields and types
# GATES: JSON_CONTRACT_GATE (hard fail if invalid)

echo "Validating required fields: 'actions', 'summary'..."
echo "Validating types: actions is array, summary is string..."
echo "Schema validation passed!"

# Step 5: Actions Applied
echo ""
echo "=== Stage 8: Apply Actions to Repo Truth ==="
# INTERNAL: apply_actions_to_repo_truth(validated_json)
# Mutates ./docs/maestro/** files
# STORES_WRITE: REPO_TRUTH_DOCS_MAESTRO
# GATES: REPOCONF_GATE

echo "Applying 4 actions:"
echo "  - create_task: task-002 'Design API endpoint schema'"
echo "  - create_task: task-003 'Implement password hashing'"
echo "  - create_task: task-004 'Add JWT token generation'"
echo "  - create_task: task-005 'Write unit tests'"
echo "Writing ./docs/maestro/tasks/task-{002,003,004,005}.json..."
echo "Updating phase-001 task list..."
echo "All actions applied successfully!"

echo ""
echo "System: Applied 4 actions. Updated repo truth."

# Step 6: Session Persisted
echo ""
echo "=== Stage 9: Persist Logs and Breadcrumbs ==="
# INTERNAL: persist_session(session_id, stream_log, breadcrumbs)
# Saves session for potential resume
# STORES_WRITE: IPC_MAILBOX (breadcrumbs), session logs

echo "Writing session log: ./session-20250126-001.log"
echo "Appending breadcrumbs to IPC mailbox (if work session active)"
echo "Session persisted."

echo ""
echo "=== EX-05 Outcome A: Success — Valid JSON, Actions Applied ==="
echo "Artifacts:"
echo "  - ./docs/maestro/tasks/task-{002,003,004,005}.json (created)"
echo "  - ./docs/maestro/phases/phase-001.json (updated task list)"
echo "  - Session log preserved for resume"

echo ""
echo "=== Alternative: Outcome B — Invalid JSON (Hard Fail) ==="
echo "# If AI had returned malformed JSON:"
echo "# System: ERROR: Invalid JSON response from AI"
echo "# System: Parse failed at line 3: unexpected token"
echo "# System: No changes applied to repo truth"
echo "# User can retry with: maestro discuss --resume session-20250126-001"  # TODO_CMD

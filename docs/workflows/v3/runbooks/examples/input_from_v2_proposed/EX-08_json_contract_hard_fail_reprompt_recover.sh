#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-08: JSON Contract Hard-Fail — Reprompt & Recover Path

echo "=== JSON Contract Hard-Fail Principle ==="
echo "If AI returns invalid JSON → Maestro ABORTS operation"
echo "No partial state mutation occurs"
echo "User must explicitly retry/recover"

echo ""
echo "=== Step 1: Start Discuss Session ==="

run maestro discuss
# EXPECT: AI session begins
# STORES_READ: REPO_TRUTH_DOCS_MAESTRO
# GATES: JSON_CONTRACT_GATE (eventual)

echo ""
echo "AI: Hello! I can help you plan this task. What would you like to do?"

echo ""
echo "=== Step 2: User Interacts, Signals /done ==="

echo ""
echo "User: Help me create 3 subtasks for this feature"
echo ""
echo "AI: Great! I suggest these subtasks:"
echo "AI: 1. Design API endpoint"
echo "AI: 2. Implement auth"
echo "AI: 3. Write tests"
echo ""
echo "User: /done"

echo ""
echo "=== Step 3: AI Returns Invalid JSON (Syntax Error) ==="

echo ""
echo "AI: Here's my suggested plan:"
echo ""
echo '```json'
echo '{'
echo '  "actions": ['
echo '    {"type": "create_task", "title": "Design API endpoint",'  # SYNTAX ERROR: trailing comma
echo '    {"type": "create_task", "title": "Implement auth"},'
echo '    {"type": "create_task", "title": "Write tests"}'
echo '  ],'
echo '  "summary": "Created 3 subtasks"'
echo '}'
echo '```'

echo ""
echo "=== Step 4: Maestro Detects JSON Parse Failure ==="

echo ""
echo "[INTERNAL] Extracting JSON from AI response..."
echo "[INTERNAL] Calling json.loads()..."
echo ""
echo "ERROR: Invalid JSON response from AI"
echo ""
echo "Parse failed at line 3, column 60:"
echo "  Expecting ',' delimiter (found extra comma after first action)"
echo ""
echo "Raw JSON:"
echo '{'
echo '  "actions": ['
echo '    {"type": "create_task", "title": "Design API endpoint",'
echo '    {"type": "create_task", "title": "Implement auth"},'
echo '    ...'

echo ""
echo "=== Step 5: Operation Aborted (No Repo Truth Mutation) ==="

echo ""
echo "Operation ABORTED at JSON_CONTRACT_GATE"
echo ""
echo "No changes applied to ./docs/maestro/**"
echo ""
echo "Session preserved: session-20250126-001"
echo "Conversation history saved for resume"

echo ""
echo "GATES: JSON_CONTRACT_GATE → FAILED"
echo "STORES_WRITE: (none - rollback)"

echo ""
echo "=== Step 6: User Chooses Recovery Path ==="

echo ""
echo "--- Option A: Resume and Retry ---"

run maestro discuss --resume session-20250126-001  # TODO_CMD
# EXPECT: Session restored, user can reprompt
# STORES_READ: SESSION_STORAGE, REPO_TRUTH_DOCS_MAESTRO
# GATES: JSON_CONTRACT_GATE (retry)

echo ""
echo "[SESSION] Resuming session-20250126-001"
echo "[SESSION] Loaded conversation history (4 messages)"
echo ""
echo "AI: Welcome back! It looks like my previous JSON response had a syntax error. Let me try again."
echo ""
echo "User: Please return valid JSON with no syntax errors this time."
echo ""
echo "AI: Here's the corrected plan:"
echo ""
echo '```json'
echo '{'
echo '  "actions": ['
echo '    {"type": "create_task", "title": "Design API endpoint"},'
echo '    {"type": "create_task", "title": "Implement auth"},'
echo '    {"type": "create_task", "title": "Write tests"}'
echo '  ],'
echo '  "summary": "Created 3 subtasks"'
echo '}'
echo '```'

echo ""
echo "[INTERNAL] Parsing JSON... SUCCESS"
echo "[INTERNAL] Validating schema... SUCCESS"
echo "[INTERNAL] Applying 3 actions to repo truth..."
echo ""
echo "Applied 3 actions. Updated ./docs/maestro/**"

echo ""
echo "--- Option B: Switch Engine ---"

run maestro discuss --engine gemini  # TODO_CMD
# EXPECT: Gemini session starts (fresh or resumed)
# Rationale: Maybe Qwen is prone to JSON errors, try Gemini

echo ""
echo "[ENGINE MANAGER] Switching to engine: gemini"
echo "Gemini: Hello! How can I help you?"

echo ""
echo "--- Option C: Manual Inspection and Debug ---"

run maestro session log session-20250126-001  # TODO_CMD
# EXPECT: View full conversation log
# User inspects raw AI response to debug

echo ""
echo "=== Session Log: session-20250126-001 ==="
echo "[14:30:01] User: Help me create 3 subtasks"
echo "[14:30:15] AI: (suggestions)"
echo "[14:31:00] User: /done"
echo "[14:31:05] AI: (returned invalid JSON with trailing comma)"
echo "[14:31:06] System: JSON parse failed - operation aborted"
echo ""
echo "User identifies trailing comma issue, provides specific feedback to AI"

echo ""
echo "=== Alternative Failure: Invalid Schema (Missing Required Fields) ==="

echo ""
echo "# If AI had returned syntactically valid JSON but missing 'actions' field:"
echo ""
echo 'AI Response:'
echo '{'
echo '  "summary": "Created 3 subtasks"'
echo '}'
echo ""
echo "System: ERROR: JSON schema validation failed"
echo "System: Missing required field: 'actions'"
echo ""
echo "Expected schema:"
echo '{'
echo '  "actions": [array of action objects],'
echo '  "summary": "string"'
echo '}'
echo ""
echo "Operation ABORTED at JSON_CONTRACT_GATE"

echo ""
echo "=== No Partial State Mutation (Critical Principle) ==="

echo ""
echo "Guaranteed: If JSON contract fails, NO actions are applied"
echo ""
echo "Example:"
echo "  - AI returns JSON with 5 actions"
echo "  - 4th action has a syntax error"
echo "  - Result: 0 actions applied (not 3 out of 5)"
echo ""
echo "Reason: Atomic transaction model — all or nothing"

echo ""
echo "=== EX-08 Outcome A: Quick Recovery — AI Re-Answers Correctly ==="
echo "Flow:"
echo "  1. Invalid JSON → hard-fail"
echo "  2. User resumes session"
echo "  3. AI returns valid JSON"
echo "  4. Actions applied"
echo ""
echo "Duration: ~30 seconds"

echo ""
echo "=== EX-08 Outcome B: Repeated Failure — User Switches Engine ==="
echo "Flow:"
echo "  1. Invalid JSON from Qwen → hard-fail"
echo "  2. User resumes, reprompts"
echo "  3. Invalid JSON again (Qwen struggling)"
echo "  4. User switches to Gemini"
echo "  5. Gemini returns valid JSON"
echo "  6. Success"
echo ""
echo "Duration: ~2 minutes"

echo ""
echo "=== Key Takeaway ==="
echo "JSON contract is a HARD GATE, not a tolerated failure"
echo "Prevents corrupt repo truth from bad AI responses"
echo "Forces explicit retry/recovery"

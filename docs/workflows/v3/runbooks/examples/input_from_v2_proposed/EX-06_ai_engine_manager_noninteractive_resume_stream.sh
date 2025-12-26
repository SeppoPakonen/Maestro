#!/usr/bin/env bash
set -euo pipefail

run() { echo "+ $*"; }

# EX-06: `maestro ai <engine>` and Engine Manager — Non-Interactive, Resume, Stream-JSON

echo "=== The Four Instruments Model ==="
echo "Available AI engines:"
echo "  - qwen (local, temp-file, JSON events)"
echo "  - gemini (cloud, temp-file, JSON events)"
echo "  - claude (stdin special case, text stream)"
echo "  - codex (temp-file, JSON events, if available)"

echo ""
echo "=== Step 1: Run AI Engine Directly (Qwen) ==="

run maestro ai qwen
# EXPECT: Qwen prompt appears, user can chat
# STORES_WRITE: SESSION_STORAGE (temp session files)
# GATES: (none - handsoff mode)
# INTERNAL: engine_manager.select_adapter(Qwen), QwenAdapter.invoke()

echo ""
echo "[ENGINE MANAGER] Selected adapter: Qwen"
echo "[ENGINE MANAGER] Writing prompt to: /tmp/maestro-qwen-session-001.txt"
echo "[ENGINE MANAGER] Invoking: /home/user/Dev/Maestro/external/ai-agents/qwen-code/qwen-code --session session-001 --input /tmp/maestro-qwen-session-001.txt"
echo ""
echo "Qwen: Hello! How can I help you today?"
echo ""
echo "User: Explain Python's argparse module"
echo ""
echo "Qwen: The argparse module in Python is used for parsing command-line arguments..."
echo "(conversation continues)"

echo ""
echo "=== Step 2: Run with Specific Prompt (Non-Interactive) ==="

run maestro ai qwen --prompt "Explain how to use argparse"  # TODO_CMD
# EXPECT: Qwen responds to prompt, then exits
# STORES_WRITE: SESSION_STORAGE
# GATES: (none)

echo ""
echo "[ENGINE MANAGER] Non-interactive mode"
echo "Qwen: The argparse module provides a way to write user-friendly command-line interfaces..."
echo "[ENGINE MANAGER] Response complete. Exiting."

echo ""
echo "=== Step 3: Resume Previous Session ==="

run maestro ai qwen --resume session-001  # TODO_CMD
# EXPECT: Session restored, conversation continues
# STORES_READ: SESSION_STORAGE (load previous state)
# STORES_WRITE: SESSION_STORAGE (append new messages)
# GATES: (none)

echo ""
echo "[ENGINE MANAGER] Loading session: session-001"
echo "[ENGINE MANAGER] Restored 4 previous messages"
echo ""
echo "Qwen: Welcome back! Last we spoke about Python's argparse module. What else can I help with?"

echo ""
echo "=== Step 4: Verbose Mode (Show Engine Command) ==="

run maestro ai qwen --verbose  # TODO_CMD
# EXPECT: Shows actual engine invocation command
# STORES_WRITE: SESSION_STORAGE
# GATES: (none)

echo ""
echo "[VERBOSE] Engine: qwen"
echo "[VERBOSE] Binary: /home/user/Dev/Maestro/external/ai-agents/qwen-code/qwen-code"
echo "[VERBOSE] Temp file: /tmp/maestro-qwen-session-002.txt"
echo "[VERBOSE] Command: /home/user/Dev/Maestro/external/ai-agents/qwen-code/qwen-code --session session-002 --input /tmp/maestro-qwen-session-002.txt"
echo "[VERBOSE] Streaming JSON events..."
echo ""
echo "Qwen: (response here)"

echo ""
echo "=== Step 5: Switch Engine (Gemini) ==="

run maestro ai gemini
# EXPECT: Gemini responds with same interface
# STORES_WRITE: SESSION_STORAGE
# GATES: (none)

echo ""
echo "[ENGINE MANAGER] Selected adapter: Gemini"
echo "[ENGINE MANAGER] Writing prompt to: /tmp/maestro-gemini-session-003.txt"
echo "[ENGINE MANAGER] Invoking: /home/user/Dev/Maestro/external/ai-agents/gemini-cli/gemini-cli --session session-003 --input /tmp/maestro-gemini-session-003.txt"
echo ""
echo "Gemini: Hello! I'm Gemini. How can I assist?"

echo ""
echo "=== Step 6: Claude Special Case (Stdin) ==="

run maestro ai claude
# EXPECT: Claude reads from stdin, not temp file
# STORES_WRITE: SESSION_STORAGE
# GATES: (none)

echo ""
echo "[ENGINE MANAGER] Selected adapter: Claude"
echo "[ENGINE MANAGER] Using stdin mode (Claude special case)"
echo "[ENGINE MANAGER] Invoking: echo \"\$PROMPT\" | claude"
echo ""
echo "Claude: Hi, I'm Claude. What would you like to know?"

echo ""
echo "=== Conceptual: AI Stacking Modes ==="
echo ""
echo "Mode comparison:"
echo "  - maestro discuss   → managed mode   → JSON contract enforced"
echo "  - maestro ai qwen   → handsoff mode  → accepts any response"
echo ""
echo "Handsoff mode: AI can return freeform text, no JSON requirement"

echo ""
echo "=== Outcome B: Engine Missing → Graceful Error ==="

run maestro ai codex
# EXPECT: Error if codex binary not found
# STORES_WRITE: (none)
# GATES: (none)

echo ""
echo "[ENGINE MANAGER] Checking for engine: codex"
echo "[ENGINE MANAGER] Binary not found: codex"
echo "ERROR: Engine 'codex' not available. Please install codex or use a different engine."
echo "Available engines: qwen, gemini, claude"

echo ""
echo "=== EX-06 Outcome A: Engine Responds Successfully ==="
echo "Artifacts:"
echo "  - Session state: \$HOME/.maestro/sessions/session-001/"
echo "  - Conversation preserved for resume"

echo ""
echo "=== EX-06 Key Insights ==="
echo "  - Four engines: qwen, gemini, claude, codex"
echo "  - Claude uses stdin, others use temp files"
echo "  - All engines support resume via session IDs"
echo "  - Verbose mode shows actual command execution"
echo "  - Handsoff mode = no JSON contract enforcement"

# Command: `ai`

## 1. Command Surface

*   **Command:** `ai`
*   **Aliases:** None
*   **Handler Binding:** `maestro.main.main` dispatches to `maestro.commands.ai.handle_ai_sync`, `handle_ai_qwen`, `handle_ai_gemini`, `handle_ai_codex`, `handle_ai_claude` based on the subcommand.

## 2. Entrypoint(s)

*   **Primary Dispatcher:** `maestro.commands.ai.handle_ai_sync(args: argparse.Namespace)`, `handle_ai_qwen(args: argparse.Namespace)`, `handle_ai_gemini(args: argparse.Namespace)`, `handle_ai_codex(args: argparse.Namespace)`, `handle_ai_claude(args: argparse.Namespace)`.
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/commands/ai.py`

## 3. Call Chain (ordered)

The `handle_ai_command` (implied by `maestro.main.main`'s dispatch, though not a single function name here) routes to specific `handle_ai_*` functions based on the subcommand.

### `maestro ai sync`

1.  `maestro.main.main()` → `maestro.commands.ai.handle_ai_sync(args)`
2.  `(If --watch)` `maestro.commands.ai._watch_ai_sync(args)`
    *   **Purpose:** Enters a polling loop to monitor `docs/ai_sync.json` for changes.
3.  `maestro.commands.ai._resolve_session(args)`
    *   **Purpose:** Determines the active `WorkSession` to synchronize.
    *   **Internal Call Chain:** `maestro.ai.task_sync.load_sync_state()`, `maestro.work_session.list_sessions()`, `load_session()`.
4.  `maestro.ai.task_sync.load_sync_state()`
    *   **Purpose:** Loads the current synchronization state from `docs/ai_sync.json`.
5.  `maestro.ai.task_sync.find_task_context(task_id)`
    *   **Purpose:** Retrieves details for the current/next task.
6.  `maestro.ai.task_sync.build_task_queue(phase)`
    *   **Purpose:** Builds the queue of tasks for the current phase.
7.  `maestro.commands.ai._select_next_task(task_queue, phase, current_task_id)`
    *   **Purpose:** Identifies the next pending task in the queue.
8.  `maestro.ai.task_sync.build_task_prompt(next_task_id, next_context["task"], next_context["phase"], ...)`
    *   **Purpose:** Generates the AI prompt for the next task.
9.  `maestro.work_session.save_session(session, session_path)`
10. `maestro.ai.task_sync.write_sync_state(session, task_queue, next_task_id)`
11. `maestro.commands.ai._write_sync_breadcrumb(session, prompt)`
    *   **Purpose:** Records the sync action as a breadcrumb.
    *   **Internal Call Chain:** `maestro.breadcrumb.create_breadcrumb()`, `write_breadcrumb()`, `estimate_tokens()`.
12. `print(prompt)` (outputs the AI prompt to stdout).

### `maestro ai <engine_name>` (e.g., `maestro ai qwen`, `maestro ai gemini`, etc.)

1.  `maestro.main.main()` → `maestro.commands.ai.handle_ai_qwen(args)` (or `handle_ai_gemini`, etc.)
2.  `maestro.ai.manager.AiEngineManager()`
    *   **Purpose:** Initializes the AI engine manager.
3.  `maestro.config.settings.get_settings()` (to get `ai_dangerously_skip_permissions`).
4.  `maestro.ai.types.RunOpts(...)` (constructs run options from args and settings).
5.  **(If `--stdin`)** `sys.stdin.read()`
    *   **Purpose:** Reads the prompt from standard input.
6.  `maestro.ai.types.PromptRef(source=prompt_text, is_stdin=True)` (constructs prompt reference).
7.  **(If `--one-shot`)** `maestro.ai.run_one_shot(manager, engine, one_shot_text, opts)`
    *   **Purpose:** Runs a single AI interaction.
    *   **Internal Call Chain:** `manager.run_once(...)` (from `maestro.ai.manager`).
8.  **(If interactive mode, default)** `maestro.ai.run_interactive_chat(manager, engine, opts)`
    *   **Purpose:** Starts an interactive AI chat.
    *   **Internal Call Chain:** Repeated calls to `manager.run_once(...)`.

### `maestro ai qwen-old` (Legacy Qwen server/TUI)

1.  `maestro.main.main()` → `maestro.commands.ai.handle_ai_qwen(args)` (specifically for the `qwen-old` subcommand branch).
2.  `maestro.commands.ai._resolve_qwen_script(args, repo_root)` (locates Qwen script).
3.  **(If `mode == "server"`)** `maestro.commands.ai._run_qwen_server(qwen_script, repo_root, host, port, verbose)`.
    *   **Internal Call Chain:** `subprocess.call()`.
4.  **(If `mode == "tui"` and not `--attach`)** `maestro.commands.ai._run_qwen_stdin_chat(qwen_script, repo_root, verbose, initial_prompt)`.
    *   **Purpose:** Runs an interactive chat via stdin/stdout, directly using `maestro.qwen.client`.
    *   **Internal Call Chain:** `maestro.qwen.client.QwenClient()`, `client.start()`, `client.send_user_input()`, `threading.Thread()`, `input()`, `client.stop()`.
5.  **(If `mode == "tui"` and `--attach`)** `maestro.commands.ai._run_qwen_tui(host, port, prompt)`.
    *   **Internal Call Chain:** `maestro.qwen.tui.run_tui()`.

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   `docs/ai_sync.json`: Stores the state for AI synchronization.
    *   `docs/sessions/session.json` or `docs/sessions/<session-id>/session.json`: Stores `WorkSession` data.
    *   `docs/phases/`: For task context during AI sync.
    *   `settings.json`: For global AI settings (`ai_dangerously_skip_permissions`, Qwen transport modes).
*   **Writes:**
    *   `docs/ai_sync.json`: Updated with the latest sync state.
    *   `docs/sessions/session.json` or `docs/sessions/<session-id>/session.json`: Updated with `WorkSession` metadata (task queue, current task, last sync).
    *   `docs/sessions/<session-id>/breadcrumbs.jsonl`: New breadcrumb entries are appended.
*   **Schema:** `docs/ai_sync.json` uses a simple JSON dict. `WorkSession` has its own JSON schema.

## 5. Configuration & Globals

*   `maestro.config.settings.get_settings()`: Accesses global AI-related settings.
*   `docs/ai_sync.json`: Canonical file for AI sync state.
*   `maestro.ai.manager.AiEngineManager`: Centralizes AI engine interactions.
*   `$EDITOR`, `$VISUAL`: Used by legacy Qwen TUI.

## 6. Validation & Assertion Gates

*   **Session/Task Existence:** Checks if `WorkSession` and tasks exist before proceeding with sync.
*   **`_select_next_task`:** Logic to ensure a valid next task is chosen.
*   **AI Engine Capabilities:** `AiEngineManager` (implicitly) ensures the requested operation is supported by the engine.
*   **`--no-danger` flag:** Overrides `ai_dangerously_skip_permissions` setting.
*   Legacy Qwen: `qwen-code.sh` script path validation.

## 7. Side Effects

*   Invokes external AI engine binaries or internal client processes.
*   Modifies local sync state files (`docs/ai_sync.json`).
*   Modifies `WorkSession` files and creates breadcrumbs.
*   Prints AI generated content and prompts to console.
*   Starts background Qwen server process (legacy `qwen-old server`).

## 8. Error Semantics

*   `print()` messages for errors, `sys.exit(1)` for critical failures (e.g., session/task not found, Qwen script not found).
*   `subprocess.call`/`Popen` exceptions for external commands.
*   Graceful handling of `KeyboardInterrupt` in watch mode and interactive chat.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/commands/test_ai.py` should cover all subcommands.
    *   Tests for `ai sync` logic, including `_select_next_task`, `_write_sync_breadcrumb`, `_watch_ai_sync`.
    *   Tests for one-shot and interactive AI interactions for each engine (mocking `AiEngineManager`).
    *   Tests for resume functionality (`--resume latest`, `--resume <id>`).
    *   Tests for legacy Qwen server/TUI functionality (if still supported).
    *   Tests for prompt building logic.
*   **Coverage Gaps:**
    *   Comprehensive testing of all possible filter and argument combinations for `ai sync`.
    *   Integration tests for `_watch_ai_sync` with file system change simulations.
    *   Robustness testing for malformed sync state JSON.
    *   Concurrency testing for `qwen-old` server/TUI mode.
    *   Testing AI interaction failures and error propagation.

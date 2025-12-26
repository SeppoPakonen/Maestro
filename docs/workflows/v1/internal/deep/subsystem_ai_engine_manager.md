# Subsystem Deep Dive: AI Engine Manager

The AI Engine Manager is responsible for standardizing the interaction with various AI models (Qwen, Gemini, Claude, Codex), handling command building, execution, output streaming, and session management. It acts as a central abstraction layer for AI integration.

## 1. Adapter Dispatch

The system employs a robust adapter pattern to integrate different AI engines, ensuring a consistent interface despite varying command-line options and output formats.

*   **`AiEngineSpec` Protocol (`maestro/ai/types.py`):** This is the core interface definition. Each AI engine implementation must conform to this protocol, specifying:
    *   `name`: Unique identifier for the engine (e.g., "qwen", "gemini").
    *   `binary`: The name of the executable command for the engine.
    *   `capabilities`: An `EngineCapabilities` object detailing features like `supports_stdin`, `supports_resume`, `supports_stream_json`, `supports_model_select`, `supports_permissions_bypass`.
    *   `get_config()`: Method to retrieve engine-specific configuration.
    *   `build_base_cmd(opts: RunOpts)`: Builds the foundational command-line arguments.
    *   `build_prompt_args(prompt: PromptRef, opts: RunOpts)`: Builds arguments related to the AI prompt.
    *   `build_resume_args(opts: RunOpts)`: Builds arguments for resuming a session.
    *   `validate()`: Performs validation of the engine's setup.

*   **Concrete Engine Implementations (`maestro/ai/engines/*.py`):**
    *   `maestro/ai/engines/qwen.py` (and similar for `gemini.py`, `claude.py`, `codex.py`) provides the actual `AiEngineSpec` implementation for each supported AI. These files define how to translate generic `RunOpts` into engine-specific command-line flags and how to handle prompts.

*   **`get_spec` Factory (`maestro/ai/engines/__init__.py`):**
    *   Acts as a central dispatcher. It imports `get_spec` functions from individual engine modules.
    *   Its own `get_spec(engine_name)` function looks up the appropriate engine and returns an instance of its `AiEngineSpec` implementation.

*   **`AiEngineManager.build_command` (`maestro/ai/manager.py`):**
    *   Retrieves the correct `AiEngineSpec` using the `get_spec` factory.
    *   Uses the `build_base_cmd`, `build_resume_args`, and `build_prompt_args` methods of the `AiEngineSpec` instance to assemble the complete command-line `argv` list.
    *   Includes special handling for Qwen's non-command-line transport modes (`_build_qwen_command`), which are routed differently at the execution layer.

*   **`run_engine_command` Execution Dispatch (`maestro/ai/runner.py`):**
    *   Takes the `argv` and delegates execution to a subprocess.
    *   For Qwen using "stdio" or "tcp" transport, it uses `_run_qwen_transport`, which calls an internal Qwen client rather than a direct subprocess command. This is another layer of dispatch based on transport mode.

*   **Event Normalization (`maestro/ai/runner._normalize_event`):**
    *   Converts raw JSON events received from different AI engines (which might have varied structures) into a standardized `AiStreamEvent` object. This ensures downstream components can process events uniformly.

## 2. Stream-JSON Capture Path

The system is designed to efficiently capture and process streaming JSON output from AI engines.

*   **`RunOpts.stream_json` (`maestro/ai/types.py`):** A boolean flag to enable streaming JSON output.
*   **`AiEngineManager.run_once` (`maestro/ai/manager.py`):** Passes the `stream_json` option to `run_engine_command`.
*   **`_run_subprocess_command` (`maestro/ai/runner.py`):** This function is responsible for the low-level streaming.
    *   It starts the AI engine as a `subprocess.Popen` with `stdout=subprocess.PIPE`.
    *   It continuously reads `stdout` line by line (or chunk by chunk), accumulating it into a `json_buffer`.
    *   **`_parse_json_events(buffer: str)` (`maestro/ai/runner.py`):** This key function attempts to parse each line in the buffer as a complete JSON object. It is robust to partial JSON lines, leaving incomplete segments in the buffer.
    *   **`_get_remaining_buffer(buffer: str)` (`maestro/ai/runner.py`):** Helps manage the `json_buffer` by extracting and returning any content that couldn't be parsed as a complete JSON event.
    *   **`StreamRenderer` (`maestro/ai/stream_render.py`):** Processes the parsed `AiStreamEvent` objects, rendering them to the user's console in real-time, often applying styling and filtering based on `quiet` and `verbose` options.
*   **`_run_qwen_transport` (`maestro/ai/runner.py`):** This (currently mock) function would also be responsible for capturing and potentially parsing streaming output from Qwen's internal client when stdio/tcp transports are used.

## 3. Final JSON Validation Path

Validation of AI-generated JSON output occurs at multiple stages:

*   **Basic JSON Validity (`maestro/ai/runner._parse_json_events`):** The `json.loads()` function inherently validates that each received "event" is well-formed JSON. If parsing fails, the line is considered invalid JSON for event purposes.
*   **Structural Validation (Example uses):**
    *   **`maestro/ai/discuss_router.py`:** Uses a `json_contract.validation_func` to check if AI-generated JSON in discussion contexts adheres to expected schema or structure (e.g., specific keys and value types for tool calls or decisions).
    *   **`maestro/ai/stacking_enforcer.py`:** Checks for the presence of high-level keys like `'tasks'` or `'plan'` in parsed AI output to ensure it aligns with expected operational structures.
    *   **`maestro/convert/realize_worker.py`:** Its `parse_ai_output` function specifically looks for a `'files'` key in the JSON output, indicating a structural expectation for file modification tasks.
*   **Application-Specific Logic:** Beyond generic JSON parsing, individual command handlers or worker modules that consume AI output will often implement their own domain-specific checks to ensure the AI's response is semantically correct and actionable within the application's context.

## 4. Retry / Resume Behavior

The system provides mechanisms to resume AI sessions, crucial for long-running or interrupted interactions.

*   **`RunOpts.continue_latest` & `RunOpts.resume_id` (`maestro/ai/types.py`):** These options control whether a session should be continued automatically or by a specific ID.
*   **`AiEngineSpec.build_resume_args` (`maestro/ai/engines/*.py`):** Each engine's specification defines how these resume options are translated into command-line arguments (e.g., Qwen uses `-c` or `-c <session_id>`).
*   **Session ID Extraction (`maestro/ai/runner._extract_session_id_from_events`, `maestro/ai/session_manager.extract_session_id`):** These functions diligently search the streamed AI output or final JSON results for a session ID, using various common key names.
*   **`AISessionManager` (`maestro/ai/session_manager.py`):**
    *   **Persistence:** Stores the last used `session_id`, `model`, `danger_mode`, and `updated_at` for each AI engine in `docs/state/ai_sessions.json`.
    *   **Retrieval:** `get_last_session_id(engine)` fetches the most recently recorded session ID for an engine, enabling automatic "continue latest" functionality.
    *   **Update:** `update_session(...)` is called by `AiEngineManager.run_once` to record the details of a new or continued session, ensuring the state is saved for future resumption.
*   **`maestro.main.handle_resume_session` (conceptual):** The top-level `maestro resume` command would likely interact with `AISessionManager` to fetch the last session ID and then invoke the appropriate AI command with resume arguments.

## 5. Configuration & Globals

*   `maestro.config.settings.get_settings()`: Accesses global settings, including `ai_qwen_transport` to determine Qwen's communication mode.
*   `docs/state/ai_sessions.json`: The persistent storage location for AI session metadata managed by `AISessionManager`.
*   `docs/logs/ai/<engine>/`: Directory where AI engine stdout, stderr, and parsed events are logged.

## 6. Validation & Assertion Gates

*   **Engine Support:** `maestro/ai/engines/__init__.py:get_spec` raises `ValueError` for unsupported engine names.
*   **Capability Check:** `AiEngineManager.build_command` checks `spec.capabilities` (e.g., `supports_stdin`) before building commands, raising `ValueError` if a requested operation is not supported by the engine.
*   **JSON Parsing:** `json.loads` can raise `json.JSONDecodeError` if AI output is not valid JSON.
*   **`AiEngineSpec.validate()`:** Each engine can implement its own pre-run validation checks (e.g., binary existence, API key configuration).

## 7. Side Effects

*   Invocation of external AI engine binaries or internal clients (`subprocess.Popen` or direct Python calls).
*   Creation/modification of log files (`docs/logs/ai/<engine>/<timestamp>_*.txt/jsonl`).
*   Modification of the AI session state file (`docs/state/ai_sessions.json`).
*   Real-time output to console (stdout/stderr) via `StreamRenderer`.

## 8. Error Semantics

*   `RunResult.exit_code`: Captures the exit code of the AI process, indicating success or failure.
*   `FileNotFoundError`: Raised if the AI engine binary is not found.
*   `KeyboardInterrupt`: Handled gracefully by `_run_subprocess_command`, attempting to terminate the child process and reporting a specific exit code (130).
*   `ValueError`, `NotImplementedError`: Can be raised during command building or dispatch if unsupported options or transports are encountered.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/ai/` directory (e.g., `test_runner.py`, `test_engines.py`, `test_session_manager.py`, `test_manager.py`) should contain unit and integration tests.
    *   Tests should cover streaming, JSON parsing, error handling, session management, and specific engine command building.
    *   Tests for different engine capabilities and their appropriate handling.
*   **Coverage Gaps:**
    *   Comprehensive testing of `_run_qwen_transport` once its internal client communication is fully implemented beyond the mock.
    *   Robustness tests for malformed or unexpected AI output during streaming.
    *   Testing edge cases for session ID extraction from complex event structures.
    *   Cross-platform testing for subprocess handling nuances (e.g., `select` on Windows).

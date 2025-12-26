# Command: `root`

## 1. Command Surface

*   **Command:** `root`
*   **Aliases:** None
*   **Handler Binding:** `maestro.main.main` dispatches to various `maestro.modules.command_handlers.handle_root_*` functions.

## 2. Entrypoint(s)

*   **Primary Dispatchers:** `maestro.modules.command_handlers.handle_root_set`, `handle_root_get`, `handle_root_refine`, `handle_root_discuss`, `handle_root_show`.
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/modules/command_handlers.py`

## 3. Call Chain (ordered)

The `handle_root_*` functions manage the root task of a Maestro session, including setting, getting, refining with AI, discussing with AI, and showing details.

### Common Flow for most `root` subcommands

1.  `maestro.main.main()` → `maestro.modules.command_handlers.handle_root_* (args)`
    *   **Purpose:** Entry point for various `root` subcommands.
2.  `maestro.session_model.load_session(session_path)`
    *   **Purpose:** Loads the `Session` object, which contains the root task and its refined versions.
    *   **Error Handling:** Catches `FileNotFoundError` or other exceptions for missing/corrupted session files.
3.  `maestro.modules.command_handlers.update_subtask_summary_paths(session, session_path)`
    *   **Purpose:** Backward compatibility for session files.

### `maestro root set [text]`

1.  ... → `maestro.modules.command_handlers.handle_root_set(session_path, text, verbose)`
2.  Gets root task text from `text` argument or `sys.stdin`.
3.  Updates `session.root_task`, `session.root_task_raw`. Clears `root_task_clean`, `root_task_summary`, `root_task_categories`.
4.  `maestro.session_model.save_session(session, session_path)`.

### `maestro root get [--clean]`

1.  ... → `maestro.modules.command_handlers.handle_root_get(session_path, clean, verbose)`
2.  Prints `session.root_task_clean` if `--clean` is specified and available, otherwise `session.root_task_raw` (or `session.root_task`).

### `maestro root show`

1.  ... → `maestro.modules.command_handlers.handle_root_show(session_path, verbose)`
2.  Prints detailed fields: `root_task_raw`, `root_task_clean`, `root_task_summary`, `root_task_categories`, `root_history`.

### `maestro root refine`

1.  ... → `maestro.modules.command_handlers.handle_root_refine(session_path, verbose, planner_order)`
2.  Delegates to `handle_refine_root(session_path, verbose, planner_order)` (imported from `maestro.modules.utils`).
    *   **Purpose:** Refines the root task using an AI planner.

### `maestro root discuss`

1.  ... → `maestro.modules.command_handlers.handle_root_discuss(session_path, verbose, stream_ai_output, print_ai_prompts, planner_order)`
2.  Initializes an interactive AI conversation (`planner_conversation`) with the root task.
3.  `maestro.modules.command_handlers.get_maestro_dir(session_path)`
    *   **Purpose:** Creates a directory for conversation transcripts (`.maestro/conversations/`).
4.  Interactive Loop:
    *   `get_multiline_input("> ")` for user input.
    *   `maestro.engines.get_engine(model_name + "_planner")` to get AI response.
    *   `print_ai_response(assistant_response)`.
    *   Conversation appended with user/assistant messages.
5.  On `/done` or `/plan`: Constructs a final prompt to AI for JSON output of refined root task (clean_text, raw_summary, categories).
6.  `maestro.engines.get_engine(...)` to get final JSON response from AI.
7.  Parses and validates AI's JSON response.
8.  Updates `session.root_task_clean`, `session.root_task_summary`, `session.root_task_categories` in the `Session` object.
9.  Appends conversation history to `session.root_history`.
10. `maestro.session_model.save_session(session, session_path)`.
11. Saves conversation transcript to `.maestro/conversations/`.

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   `docs/sessions/<session-name>/session.json`: Contains the `Session` object with `root_task`, `root_task_raw`, `root_task_clean`, `root_task_summary`, `root_task_categories`, `root_history`.
*   **Writes:**
    *   `docs/sessions/<session-name>/session.json`: Updated with new root task details, refined data, and conversation history.
    *   `.maestro/conversations/*.txt`: Conversation transcripts are saved.
*   **Schema:** The `Session` object adheres to the schema defined in `maestro.session_model.py`. The AI-generated JSON for root task refinement adheres to a specific schema defined by the prompt.

## 5. Configuration & Globals

*   `planner_order` (CLI argument for `handle_root_refine`, `handle_root_discuss`): Specifies AI planner preference.
*   `get_maestro_dir()`: Used to locate session's base directory.

## 6. Validation & Assertion Gates

*   Session file existence.
*   `session.root_task` must not be empty for planning/refinement.
*   AI response JSON validation for `handle_root_discuss`.
*   User input for interactive discussions.

## 7. Side Effects

*   Loads and saves `Session` objects.
*   Creates conversation transcripts.
*   Interacts with AI for refinement and discussion.
*   Prints formatted output and interactive prompts.

## 8. Error Semantics

*   `print_error` for errors, `sys.exit(1)` for critical failures (e.g., session not found, empty root task).
*   `KeyboardInterrupt` handled gracefully during interactive discussion.
*   `PlannerError` for AI planner failures.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   Unit/integration tests for each `handle_root_*` command.
    *   Tests for AI interaction (mocking AI engines and responses, especially JSON parsing).
    *   Tests for conversation history logging.
    *   Tests for `root_task_raw`, `root_task_clean`, `root_task_summary`, `root_task_categories` updates.
*   **Coverage Gaps:**
    *   Robustness testing for malformed AI responses during root task refinement.
    *   Comprehensive testing of interactive discussion flow (e.g., user input variations, exit conditions).
    *   Ensure all fields of `root_history` are correctly populated.
    *   Testing AI planner preference handling.

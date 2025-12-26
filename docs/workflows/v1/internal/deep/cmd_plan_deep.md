# Command: `plan`

## 1. Command Surface

*   **Command:** `plan`
*   **Aliases:** `pl`
*   **Handler Binding:** `maestro.main.main` dispatches to various `handle_plan_*` functions within `maestro/commands/plan.py` based on subcommands.

## 2. Entrypoint(s)

The `plan` command uses a dispatch pattern within `maestro.main.main`. The primary handler for plan-related operations is `maestro.commands.plan.add_plan_parser` which sets up the subparsers, and then specific `handle_plan_*` functions serve as entry points for each subcommand.

*   **Primary Dispatcher:** `maestro.commands.plan.handle_plan_add`, `handle_plan_list`, `handle_plan_remove`, `handle_plan_show`, `handle_plan_add_item`, `handle_plan_remove_item`, `handle_plan_discuss`, `handle_plan_explore`.
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/commands/plan.py`
*   **Subcommand Ops Entrypoint:** `maestro.plan_ops.commands.add_plan_ops_parser` (sets up `validate`, `preview`, `apply` for `plan ops`).
    *   **File Path:** `/home/sblo/Dev/Maestro/maestro/plan_ops/commands.py`

## 3. Call Chain (ordered)

### General Plan Management (`add`, `list`, `remove`, `show`, `add-item`, `remove-item`)

1.  `maestro.main.main()` → `maestro.commands.plan.handle_plan_* (args)`
2.  `maestro.plans.PlanStore()`
    *   **Purpose:** Initializes the plan store, defaulting to `docs/plans.md`.
3.  `PlanStore.load()` / `PlanStore.save(plans)`
    *   **Purpose:** Loads all plans from or saves all plans to `docs/plans.md`.
    *   **Internal Call Chain:** `PlanStore._parse_content()` (for load) or `PlanStore._format_content()` (for save).
4.  `PlanStore.add_plan(title)`, `PlanStore.remove_plan(title)`, `PlanStore.get_plan(title_or_number)`, `PlanStore.add_item_to_plan(...)`, `PlanStore.remove_item_from_plan(...)`
    *   **Purpose:** Performs the specific CRUD operation on the in-memory list of `Plan` objects.
5.  `maestro.modules.utils.print_header(...)`, `print_success(...)`, `print_error(...)`, `print_info(...)`, `styled_print(...)`
    *   **Purpose:** Provides formatted console output.

### `maestro plan ops validate <file.json>`

1.  `maestro.main.main()` → `maestro.commands.plan.add_plan_parser()` → `maestro.plan_ops.commands.add_plan_ops_parser()` → `maestro.plan_ops.commands.handle_plan_ops_validate(json_file, ...)`
2.  `pathlib.Path.exists()`, `pathlib.Path.read_text(encoding='utf-8')`
    *   **Purpose:** Reads the JSON file content.
3.  `maestro.plan_ops.decoder.decode_plan_ops_json(content)`
    *   **Purpose:** Parses and strictly validates the JSON content against the `PlanOpsResult` schema.
    *   **Internal Call Chain:** `maestro.plan_ops.schemas.validate_plan_ops_result(content_dict)`.
4.  `maestro.modules.utils.print_success(...)`, `print_error(...)`

### `maestro plan ops preview <file.json>`

1.  `maestro.main.main()` → `maestro.commands.plan.add_plan_parser()` → `maestro.plan_ops.commands.add_plan_ops_parser()` → `maestro.plan_ops.commands.handle_plan_ops_preview(json_file, ...)`
2.  `maestro.plan_ops.decoder.decode_plan_ops_json(content)`
3.  `maestro.plan_ops.translator.actions_to_ops(plan_ops_result)`
    *   **Purpose:** Converts the validated JSON actions into a list of strongly-typed `maestro.plan_ops.operations` objects.
4.  `maestro.plan_ops.executor.PlanOpsExecutor()`
    *   **Purpose:** Initializes the executor.
5.  `PlanOpsExecutor.preview_ops(ops)`
    *   **Purpose:** Simulates applying the operations without modifying the actual `PlanStore`.
    *   **Internal Call Chain:** `PlanStore.load()` → `copy.deepcopy()` → `PlanOpsExecutor._apply_*` (simulated).
6.  `maestro.modules.utils.print_header(...)`, `styled_print(...)`

### `maestro plan ops apply <file.json>`

1.  `maestro.main.main()` → `maestro.commands.plan.add_plan_parser()` → `maestro.plan_ops.commands.add_plan_ops_parser()` → `maestro.plan_ops.commands.handle_plan_ops_apply(json_file, ...)`
2.  `maestro.plan_ops.decoder.decode_plan_ops_json(content)`
3.  `maestro.plan_ops.translator.actions_to_ops(plan_ops_result)`
4.  `maestro.plan_ops.executor.PlanOpsExecutor()`
5.  `PlanOpsExecutor.apply_ops(ops, dry_run=False)`
    *   **Purpose:** Applies the operations, modifying the `PlanStore`.
    *   **Internal Call Chain:** `PlanStore.load()` → `PlanOpsExecutor._apply_*` (direct modification) → `PlanStore.save(plans)`.
6.  `maestro.modules.utils.print_success(...)`

### `maestro plan discuss`

1.  `maestro.main.main()` → `maestro.commands.plan.handle_plan_discuss(title_or_number, ..., prompt)`
2.  `maestro.plans.PlanStore()`
3.  `PlanStore.load()` / `PlanStore.get_plan(title_or_number)`
4.  `maestro.plan_ops.prompt_contract.get_plan_discuss_prompt(plan_context['title'], plan_context['items'])`
    *   **Purpose:** Generates a system prompt for the AI based on the current plan.
5.  `maestro.ai.manager.AiEngineManager()`
    *   **Purpose:** Initializes AI engine manager.
6.  **(If no `--prompt` - Interactive Mode):** `maestro.ai.chat.run_interactive_chat(manager, 'qwen', opts, initial_prompt=interactive_prompt)`
    *   **Purpose:** Starts an interactive AI conversation.
7.  **(If `--prompt` - One-Shot Mode):**
    *   `maestro.ai.manager.AiEngineManager.run_once("qwen", prompt_ref, opts)`
        *   **Purpose:** Invokes the AI engine to get a response.
        *   **Internal Call Chain:** (See `subsystem_ai_engine_manager`)
    *   Read AI response from `result.stdout_path`.
    *   Strip Markdown code block wrappers.
    *   `maestro.plan_ops.decoder.decode_plan_ops_json(cleaned_response)` (with retry logic on failure).
    *   `maestro.plan_ops.translator.actions_to_ops(plan_ops_result)`
    *   `maestro.plan_ops.executor.PlanOpsExecutor()`
    *   `PlanOpsExecutor.preview_ops(ops)`
    *   User confirmation (`input()`) or auto-apply (`apply_ops`).
    *   `PlanOpsExecutor.apply_ops(ops, dry_run=False)`.

### `maestro plan explore` (Iterative AI Planning)

1.  `maestro.main.main()` → `maestro.commands.plan.handle_plan_explore(...)`
2.  `signal.signal(signal.SIGINT, signal_handler)` (for graceful Ctrl+C handling).
3.  **Session Management:**
    *   `maestro.plan_explore.session.create_explore_session(...)` or `resume_explore_session(session_id)`
    *   **Internal Call Chain:** `pathlib.Path.mkdir` → `maestro.work_session.create_session` → `save_explore_session`.
4.  `maestro.plans.PlanStore()` (to load/manage selected plans).
5.  `maestro.ai.manager.AiEngineManager()`
6.  **Iterative Loop (`while iteration_count < max_iterations`):**
    *   `maestro.data.markdown_parser.parse_todo_md("docs/todo.md")` (to get current project state).
    *   `maestro.commands.plan.create_explore_prompt(plans_context, tracks_summary)`
        *   **Purpose:** Generates the dynamic prompt for the AI in each iteration.
    *   `maestro.ai.manager.AiEngineManager.run_once(engine, prompt_ref, opts)`
    *   Read AI response from `result.stdout_path`.
    *   `maestro.project_ops.decoder.decode_project_ops_json(ai_response)` (with retry logic).
        *   **Purpose:** Validates AI-generated project-level operations.
    *   `maestro.project_ops.translator.actions_to_ops(project_ops_result)`
        *   **Purpose:** Translates JSON actions into strongly-typed `maestro.project_ops.operations` objects.
    *   `maestro.project_ops.executor.ProjectOpsExecutor()`
    *   `ProjectOpsExecutor.preview_ops(ops)`
    *   User confirmation (`input()`) or auto-apply.
    *   `ProjectOpsExecutor.apply_ops(ops, dry_run=False)`
        *   **Purpose:** Modifies tracks, phases, tasks in the project.
    *   `maestro.plan_explore.session.add_iteration_to_session(...)`
    *   `maestro.plan_explore.session.save_explore_session(...)`
7.  `maestro.plan_explore.session.complete_explore_session(...)` or `interrupt_explore_session(...)`

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   `docs/plans.md`: Main storage for plans.
    *   `docs/todo.md`: For current project state during plan exploration.
    *   `docs/sessions/explore/<session-id>/explore_session.json`: For resuming explore sessions.
    *   JSON files for `PlanOpsResult` or `ProjectOpsResult` (`handle_plan_ops_*` commands).
    *   Maestro global settings for AI configuration.
*   **Writes:**
    *   `docs/plans.md`: Modified by plan CRUD operations and `PlanOpsExecutor.apply_ops`.
    *   `docs/sessions/explore/<session-id>/explore_session.json`: Created and updated during plan exploration.
    *   Project files (e.g., `docs/tracks/*.md`, `docs/phases/*.md`, `.maestro/tracks/*.json`) are modified indirectly by `ProjectOpsExecutor.apply_ops`.
*   **Schema:**
    *   Plans are stored in a custom Markdown format enforced by `maestro.plans.PlanStore`.
    *   AI responses for `discuss` adhere to the `PlanOpsResult` JSON schema (`maestro.plan_ops.schemas.py`).
    *   AI responses for `explore` adhere to the `ProjectOpsResult` JSON schema (`maestro.project_ops.schemas.py` - assumed to be similar to `plan_ops`).

## 5. Configuration & Globals

*   `maestro.config.settings.get_settings()`: Accesses various AI-related and other settings.
*   `docs/plans.md`: Canonical file path for plan storage.
*   `docs/sessions/explore/`: Base directory for explore session data.
*   `maestro.ai.manager.AiEngineManager`: Provides unified AI interaction.

## 6. Validation & Assertion Gates

*   **PlanStore Validation:** Duplicate plan titles, invalid item numbers.
*   **AI Response JSON Validation:** Strict schema validation for `PlanOpsResult` and `ProjectOpsResult` using `decode_plan_ops_json` and `decode_project_ops_json`.
*   **Retry Logic:** Automatically retries AI calls if initial JSON validation fails.
*   **PlanOpsExecutor/ProjectOpsExecutor Validation:** Ensures operations are valid against the current state of plans/project before application.
*   **User Confirmation:** Optional interactive confirmation for applying changes.
*   **Argument Validation:** CLI arguments are validated by `argparse` and within handlers (e.g., plan number range).

## 7. Side Effects

*   Direct modification of `docs/plans.md`.
*   Creation and modification of explore session files.
*   Invokes AI engines (Qwen, etc.) via subprocess.
*   Modifies project structure (tracks, phases, tasks) through `ProjectOpsExecutor`.
*   Prints extensive console output including headers, infos, successes, and errors.

## 8. Error Semantics

*   `ValueError` and `DecodeError` are raised for invalid plan operations or AI responses.
*   `SystemExit` (via `sys.exit(1)`) on critical errors like plan not found, invalid input, or persistent AI response failures.
*   Graceful handling of `KeyboardInterrupt` during `plan explore` to save session state.
*   Retry mechanism for transient AI output errors.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/commands/test_plan.py` for CLI command behavior.
    *   `maestro/tests/plans/test_plan_store.py` for plan persistence and parsing.
    *   `maestro/tests/plan_ops/` for decoder, translator, executor, and schemas.
    *   `maestro/tests/plan_explore/` for session management and iterative logic.
    *   Integration tests involving AI calls (potentially mocked or against real engines).
*   **Coverage Gaps:**
    *   Full scenario testing for `plan discuss` and `plan explore` covering all retry paths, user interactions, and edge cases for AI responses.
    *   Testing the robustness of Markdown parsing/formatting in `PlanStore` for unusual plan content.
    *   Ensuring atomicity and consistency of project modifications by `PlanOpsExecutor` and `ProjectOpsExecutor`.

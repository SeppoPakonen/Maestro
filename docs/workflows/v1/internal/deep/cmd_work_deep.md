# Command: `work`

## 1. Command Surface

*   **Command:** `work`
*   **Aliases:** `wk`
*   **Handler Binding:** `maestro.main.main` dispatches to specific `handle_work_*` functions within `maestro/commands/work.py` based on subcommands. Many handlers are `async`.

## 2. Entrypoint(s)

*   **Primary Dispatcher:** `maestro.commands.work.handle_work_any`, `handle_work_any_pick`, `handle_work_track`, `handle_work_phase`, `handle_work_issue`, `handle_work_task`, `handle_work_discuss`, `handle_work_analyze`, `handle_work_fix`.
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/commands/work.py`

## 3. Call Chain (ordered)

The `handle_work_*` functions serve as entry points for each subcommand, orchestrating AI interactions and work session management. Most directly interact with the AI through `_run_ai_interaction_with_breadcrumb`.

### Common Flow for most `work` subcommands

1.  `maestro.main.main()` → `maestro.commands.work.handle_work_* (args)` (often `async`)
    *   **Purpose:** Entry point for various `work` subcommands.
2.  `maestro.commands.work.load_available_work()`
    *   **Purpose:** Gathers tracks, phases, and issues that are currently "to do" from `docs/todo.md` and `docs/issues/`.
    *   **Internal Call Chain:** `maestro.data.parse_todo_md()`, `maestro.commands.work.load_issues()`.
3.  `maestro.work_session.create_session(...)`
    *   **Purpose:** Creates a new `WorkSession` to track the current work activity.
4.  `maestro.commands.work._run_ai_interaction_with_breadcrumb(session, prompt, ...)`
    *   **Purpose:** Sends a prompt to an AI and records the interaction.
    *   **Internal Call Chain:**
        *   `maestro.commands.work._safe_generate(prompt, model_used)` → `maestro.engines.get_engine(model_used).generate(prompt)`.
        *   `maestro.breadcrumb.create_breadcrumb()`, `write_breadcrumb()`, `estimate_tokens()`, `calculate_cost()`.
5.  `maestro.work_session.complete_session(session)`
    *   **Purpose:** Marks the `WorkSession` as completed.

### `maestro work any`

1.  ... → `maestro.commands.work.handle_work_any(args)`
2.  `maestro.commands.work.ai_select_work_items(all_items, mode="best")`
    *   **Purpose:** Uses AI to determine the single best item to work on.
3.  `maestro.work_session.create_session(session_type=f"work_{selected_item['type']}", ...)`
4.  Dynamic import and call to worker functions: `maestro.workers.track_worker.execute_track_work`, `maestro.workers.phase_worker.execute_phase_work`, `maestro.workers.issue_worker.execute_issue_work`.

### `maestro work any pick`

1.  ... → `maestro.commands.work.handle_work_any_pick(args)`
2.  `maestro.commands.work.ai_select_work_items(all_items, mode="top_n")`
    *   **Purpose:** Uses AI to recommend top 3 work items.
3.  Interactive user input (`input()`) for selection.
4.  `maestro.work_session.create_session(...)`
5.  Dynamic import and call to worker functions (same as `handle_work_any`).

### `maestro work track <id>`, `maestro work phase <id>`, `maestro work issue <id>`, `maestro work task <id>`

1.  ... → (e.g., `handle_work_track(args)`)
2.  (If `args.id` is not provided) Displays available items, optionally uses `ai_select_work_items(..., mode="top_n")` for recommendations, and prompts user for selection.
3.  `maestro.work_session.create_session(...)`.
4.  Dynamic import and call to worker functions (e.g., `maestro.workers.track_worker.execute_track_work(track_id, session)`).
5.  **(For `handle_work_task`):** `maestro.ai.task_sync.find_task_context(task_id)`, `build_task_queue(phase)`, `write_sync_state(session, task_queue, task_id)`.

### `maestro work discuss <entity_type> <entity_id>`

1.  ... → `maestro.commands.work.handle_work_discuss(args)`
2.  Delegates to `maestro.commands.discuss.handle_track_discuss`, `handle_phase_discuss`, or `handle_task_discuss`.

### `maestro work analyze [target]`

1.  ... → `maestro.commands.work.handle_work_analyze(args)`
2.  `maestro.work_session.create_session(session_type="analyze", ...)` (unless `simulate`).
3.  Conditional prompt generation based on `args.target` (file, directory, track, phase, issue ID, or general repo state).
4.  **(If `simulate`)** `print()` statements describing simulated actions and AI output. Otherwise, `_run_ai_interaction_with_breadcrumb(session, prompt)`.

### `maestro work fix [target] [--issue <id>]`

1.  ... → `maestro.commands.work.handle_work_fix(args)`
2.  `maestro.work_session.create_session(session_type="fix", ...)` (unless `simulate`).
3.  **(If `args.issue` is provided)** A 4-phase AI-driven workflow:
    *   **Phase 1: Analyze Issue:** Creates sub-session (`analyze_issue`), generates prompt, `_run_ai_interaction_with_breadcrumb()`.
    *   **Phase 2: Decide on Fix:** Creates sub-session (`decide_fix`), generates prompt, `_run_ai_interaction_with_breadcrumb()`.
    *   **Phase 3: Implement Fix:** Creates sub-session (`implement_fix`), generates prompt, `_run_ai_interaction_with_breadcrumb()`.
    *   **Phase 4: Verify Fix:** Creates sub-session (`verify_fix`), generates prompt, `_run_ai_interaction_with_breadcrumb()`.
4.  **(If no `args.issue`)** Direct fix of a target. Generates prompt based on file/directory content.
5.  `_run_ai_interaction_with_breadcrumb(session, prompt)`.

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   `docs/todo.md`: For tracks and phases.
    *   `docs/issues/*.md`: For issues (via `load_issues`).
    *   `docs/phases/*.md`: For tasks (via `_load_task_entries`).
    *   `docs/ai_sync.json`: Sync state.
    *   `docs/sessions/*.json`: Work session data.
    *   `.git` directory: For recent changes in `handle_work_analyze`.
*   **Writes:**
    *   `docs/sessions/*.json`: New work sessions created, updated.
    *   `docs/sessions/<session_id>/breadcrumbs.jsonl`: Detailed breadcrumb records.
    *   `docs/ai_sync.json`: Sync state updated by `write_sync_state`.
*   **Schema:** Work sessions, breadcrumbs, and sync state are stored in JSON. Tracks, phases, issues, and tasks have Markdown and/or JSON schemas.

## 5. Configuration & Globals

*   AI engine configuration implicitly managed by `get_engine()`.
*   Breadcrumb enablement settings from `maestro.work_session.is_breadcrumb_enabled()`.
*   Git status (for analysis context).

## 6. Validation & Assertion Gates

*   **Work Item Availability:** Checks if any work items are available before AI selection.
*   **AI Selection Fallback:** `simple_priority_sort()` acts as a fallback if AI selection fails.
*   **Work Item Type Validation:** Ensures selected work item type is supported.
*   **Task/Phase/Issue Existence:** Checks if IDs refer to existing items.
*   **`simulate` mode:** Prevents actual file modifications or session creations.
*   User input validation for item selection (`handle_work_any_pick`).

## 7. Side Effects

*   Creates detailed `WorkSession` records, often in a hierarchical parent-child structure.
*   Records detailed breadcrumbs for each AI interaction.
*   Invokes AI engines for selection, analysis, planning, and fixing.
*   Dynamically imports and executes worker modules.
*   Modifies `docs/ai_sync.json`.
*   Prints extensive, formatted output to the console.

## 8. Error Semantics

*   `print()` and `logging.error` for errors, `SystemExit` implicitly via unhandled exceptions.
*   Graceful fallback for AI engine failures (`simple_priority_sort`, simulated responses).
*   `ImportError` for missing worker modules.
*   Stack traces printed for verbose mode or unhandled exceptions.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/commands/test_work.py` should cover all subcommands.
    *   Tests for `load_available_work` with various `docs/todo.md` and `docs/issues/` states.
    *   Tests for `ai_select_work_items` (mocking AI responses and testing `simple_priority_sort`).
    *   Tests for work session creation, breadcrumb logging, and completion.
    *   Extensive integration tests for `handle_work_any`, `handle_work_any_pick`, and the specific `handle_work_track/phase/issue/task`.
    *   Tests for `handle_work_analyze` and `handle_work_fix`, including simulation mode and the 4-phase workflow.
    *   Tests for `_select_next_task` logic.
*   **Coverage Gaps:**
    *   Comprehensive end-to-end integration tests for AI-driven modifications performed by the dynamically imported worker modules.
    *   Robustness testing for malformed `docs/todo.md` or `docs/issues/*.md` files when loading work.
    *   Testing with various AI engine failures and how `_safe_generate` handles them.
    *   Testing the behavior under different breadcrumb settings (enabled/disabled).
    *   Thorough validation of dynamically loaded worker modules.
    *   Testing the parent-child relationships between work sessions created in `handle_work_fix`.

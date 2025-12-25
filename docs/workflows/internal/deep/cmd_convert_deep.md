# Command: `convert/c`

## 1. Command Surface

*   **Command:** `convert`
*   **Aliases:** `c`
*   **Handler Binding:** `maestro.main.main` dispatches to various `handle_convert_*` functions based on the subcommand, which are registered by `maestro.commands.convert.add_convert_parser`.

## 2. Entrypoint(s)

*   **Primary Dispatcher:** `maestro.commands.convert.handle_convert_new`, `handle_convert_plan`, `handle_convert_run`, `handle_convert_status`, `handle_convert_show`, `handle_convert_reset`, `handle_convert_batch`.
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/commands/convert.py`

## 3. Call Chain (ordered)

The `handle_convert_*` functions serve as entry points for each subcommand, delegating the core logic to specialized modules in `maestro.convert.*` and `maestro.ui_facade.convert`.

### Common Flow for `convert` subcommands

1.  `maestro.main.main()` → `maestro.commands.convert.add_convert_parser()`
    *   **Purpose:** Registers the `convert` command and its many subcommands.
2.  `maestro.main.main()` → (dispatches to specific `handle_convert_*` function based on `args.convert_subcommand`)
    *   **Purpose:** Executes the logic for the respective `convert` subcommand.
3.  `print()` statements provide user feedback and progress.

### `maestro convert new [name]`

1.  ... → `maestro.commands.convert.handle_convert_new(args)`
2.  `maestro.convert.convert_orchestrator.create_new_pipeline(pipeline_name)`
    *   **Purpose:** Initializes and persists a new conversion pipeline definition.

### `maestro convert plan <id>`

1.  ... → `maestro.commands.convert.handle_convert_plan(args)`
2.  `maestro.convert.planner.plan_conversion(pipeline_id, verbose=args.verbose)`
    *   **Purpose:** Generates a detailed plan for the conversion.

### `maestro convert run <id>`

1.  ... → `maestro.commands.convert.handle_convert_run(args)`
2.  `maestro.convert.execution_engine.run_conversion_pipeline(pipeline_id, verbose=args.verbose)`
    *   **Purpose:** Executes the conversion plan.

### `maestro convert status <id>` and `maestro convert show <id>`

1.  ... → `maestro.commands.convert.handle_convert_status(args)` or `handle_convert_show(args)`
2.  `maestro.ui_facade.convert.get_pipeline_status(pipeline_id)`
    *   **Purpose:** Retrieves and formats the current status and detailed information about the pipeline stages.

### `maestro convert reset <id>`

1.  ... → `maestro.commands.convert.handle_convert_reset(args)`
2.  `maestro.convert.convert_orchestrator.reset_pipeline(pipeline_id)`
    *   **Purpose:** Clears the state of a conversion pipeline.

### `maestro convert batch [subcommand]`

1.  ... → `maestro.commands.convert.handle_convert_batch(args)`
2.  Contains placeholder `print()` statements for `run`, `status`, `show`, `report` subcommands.

## 4. Core Data Model Touchpoints

*   **Reads:** Underlying conversion modules (orchestrator, planner, execution_engine, ui_facade) will read pipeline definitions and state from persistent storage (likely `.maestro/convert/`).
*   **Writes:** Underlying conversion modules will write new pipeline definitions, update pipeline state, and potentially modify codebase files during execution.
*   **Schema:** Conversion pipelines likely have an internal JSON or YAML schema, managed by the `maestro.convert.convert_orchestrator` and related modules.

## 5. Configuration & Globals

*   The underlying conversion modules will rely on project configuration and settings.
*   `ImportError` handling for conversion-specific dependencies suggests modularity.

## 6. Validation & Assertion Gates

*   **`pipeline_id` requirement:** Most subcommands require a `pipeline_id`.
*   **`ImportError` handling:** Graceful messages if conversion functionality is not fully available.
*   **Execution results:** Return codes from underlying functions (`create_new_pipeline`, `plan_conversion`, etc.) determine success/failure.

## 7. Side Effects

*   **Orchestration:** Initiates complex conversion workflows, which involve reading, analyzing, and potentially modifying project files.
*   **Persistent State:** Underlying modules manage the persistent state of conversion pipelines.
*   **Console Output:** Prints status, progress, and results to the user.

## 8. Error Semantics

*   `print()` messages for errors, `sys.exit(1)` for critical failures.
*   `ImportError` is caught and a user-friendly message is displayed for missing conversion dependencies.
*   Errors from underlying conversion modules are caught and reported.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/commands/test_convert.py` should cover all `handle_convert_*` functions, ensuring correct delegation.
    *   Integration tests for `create_new_pipeline`, `plan_conversion`, `run_conversion_pipeline`, `reset_pipeline` (in `maestro/convert/`).
    *   Integration tests for `get_pipeline_status` (in `maestro/ui_facade/convert`).
    *   Tests for error handling, especially `ImportError`.
*   **Coverage Gaps:**
    *   Full implementation and testing of `handle_convert_batch` subcommands.
    *   Comprehensive end-to-end testing of entire conversion pipelines with various codebases and transformations.
    *   Robustness testing for invalid `pipeline_id`s or corrupted pipeline state.
    *   Testing across different project setups and build systems.

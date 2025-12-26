# Subsystem Deep Dive: Session Store

## 1. Session File Schema

The session data model is primarily defined in `maestro/session_model.py` through the `Session`, `Subtask`, and `PlanNode` Python classes. These classes include `to_dict` and `from_dict` methods for serialization to and deserialization from JSON.

### `Session` Object Schema

The top-level session object stored in JSON contains the following keys:

*   **`id`** (string): Unique identifier for the session (UUID format).
*   **`created_at`** (string): ISO format timestamp of session creation.
*   **`updated_at`** (string): ISO format timestamp of last session update.
*   **`root_task`** (string): The initial, high-level task for the session.
*   **`subtasks`** (array of `Subtask` objects): A list of subtasks associated with the session.
*   **`rules_path`** (string, optional): Path to the rules file used for the session.
*   **`status`** (string): Current status of the session. Valid statuses are: `new`, `planned`, `in_progress`, `interrupted`, `failed`, `done`.
*   **`root_task_raw`** (string, optional): The raw, uncleaned root task text.
*   **`root_task_clean`** (string, optional): A cleaned version of the root task text.
*   **`root_task_summary`** (string, optional): A summary of the root task.
*   **`root_task_categories`** (array of strings, optional): Categories associated with the root task.
*   **`root_history`** (array of dictionaries, optional): Historical changes or refinements to the root task.
*   **`plans`** (array of `PlanNode` objects, optional): A list of plan nodes for managing branching plans.
*   **`active_plan_id`** (string, optional): The ID of the currently active plan node.

### `Subtask` Object Schema

Each subtask within the `subtasks` array has the following structure:

*   **`id`** (string): Unique identifier for the subtask.
*   **`title`** (string): Short title of the subtask.
*   **`description`** (string): Detailed description of the subtask.
*   **`planner_model`** (string): AI model used for planning this subtask.
*   **`worker_model`** (string): AI model used for executing this subtask.
*   **`status`** (string): Current status of the subtask. Valid statuses are: `pending`, `in_progress`, `done`, `error`, `interrupted`.
*   **`summary_file`** (string): Path to a file containing the summary or output of the subtask.
*   **`categories`** (array of strings, optional): Categories assigned to the subtask.
*   **`root_excerpt`** (string, optional): An excerpt from the root task relevant to this subtask.
*   **`plan_id`** (string, optional): The ID of the plan node this subtask belongs to.

### `PlanNode` Object Schema

Each plan node within the `plans` array has the following structure:

*   **`plan_id`** (string): Unique identifier for the plan node.
*   **`parent_plan_id`** (string, optional): ID of the parent plan node, if applicable.
*   **`created_at`** (string): ISO format timestamp of plan node creation.
*   **`label`** (string): A descriptive label for the plan node.
*   **`status`** (string): Status of the plan node. Valid statuses: `"active", "inactive", "dead"`.
*   **`notes`** (string, optional): Any notes associated with the plan.
*   **`root_snapshot`** (string): A snapshot of the root task relevant to this plan.
*   **`root_task_snapshot`** (string, optional): Legacy field, consolidated into `root_snapshot`.
*   **`root_clean_snapshot`** (string, optional): Legacy field, consolidated into `root_snapshot`.
*   **`categories_snapshot`** (array of strings, optional): Categories snapshot for the plan.
*   **`subtask_ids`** (array of strings, optional): IDs of subtasks belonging to this plan.

## 2. Loader/Writer Functions

*   **`maestro.session_model.load_session(path: str) -> Session`**
    *   **Purpose:** Reads a JSON file from the given `path`, parses it, and constructs a `Session` object.
    *   **Call Chain:** `json.load(f)` → `Session.from_dict(data)` → `Subtask.from_dict(...)` and `PlanNode.from_dict(...)`.
    *   **File Path:** `/home/sblo/Dev/Maestro/maestro/session_model.py`
*   **`maestro.session_model.save_session(session: Session, path: str) -> None`**
    *   **Purpose:** Takes a `Session` object, converts it to a dictionary, and writes it as JSON to the given `path`.
    *   **Call Chain:** `session.to_dict()` → `subtask.to_dict()` and `plan.to_dict()` → `json.dump(..., f, indent=2)`.
    *   **File Path:** `/home/sblo/Dev/Maestro/maestro/session_model.py`

## 3. How Resume Tokens are Stored

The entire session JSON file acts as the resume token. The `status` field of the `Session` and `Subtask` objects, along with the detailed `subtasks` list and `plans` array, contain all the necessary information to resume work from a specific point. The `id` field uniquely identifies a session. When a session is loaded, the `Session` object is fully reconstructed, allowing the CLI to pick up where it left off.

## 4. Validation Gates

Validation is primarily handled during the deserialization (`from_dict`) process within `maestro/session_model.py`.

*   **Implicit Key Presence Checks:** The `from_dict` methods for `Session`, `Subtask`, and `PlanNode` implicitly expect certain keys to be present in the input dictionary. Missing critical keys would lead to `KeyError`.
*   **Backward Compatibility:** Both `Session.from_dict` and `PlanNode.from_dict` include logic to handle older session file formats (e.g., missing fields or renamed fields like `root_task_raw`, `root_task_clean`, `root_task_snapshot`). This acts as a soft validation and migration mechanism.
*   **JSON Parsing Errors:** `maestro.session_model.load_session` can raise `json.JSONDecodeError` if the session file is not valid JSON.
*   **File System Errors:** `load_session` can raise `FileNotFoundError` if the specified path does not exist.
*   **Status Enforcement:** `SESSION_STATUSES` and `SUBTASK_STATUSES` (sets of strings) define allowed states, though enforcement is typically done by code interacting with these models rather than within `from_dict` itself.

## 5. Configuration & Globals

*   `json`: Standard Python library for JSON serialization/deserialization.
*   `uuid`: Standard Python library for generating unique IDs.
*   `datetime`: Standard Python library for handling timestamps.
*   `dataclasses`: Standard Python library used for `PlanNode`.
*   `SESSION_STATUSES` (set of strings): Defined in `maestro/session_model.py`, specifies valid session states.
*   `SUBTASK_STATUSES` (set of strings): Defined in `maestro/session_model.py`, specifies valid subtask states.

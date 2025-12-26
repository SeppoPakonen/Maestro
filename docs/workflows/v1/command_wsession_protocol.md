# Command: `maestro wsession` Protocol (Current Implementation)

This document details the current implementation of the `maestro wsession` command, focusing on how work session identity is tracked, data is stored, and breadcrumbs are managed. It serves as a grounding document for the proposed WF-15 "Work ↔ wsession Cookie Protocol."

## 1. Session Identity (The "Cookie")

Work sessions are identified by a unique `session_id`. This `session_id` acts as the "cookie" or run-id, distinguishing one work-run from another.

*   **Generation**: The `session_id` is generated as a `uuid.UUID4` string when a new session is created via `maestro.work_session.create_session`.
*   **Usage**: It is used to identify the specific session directory on disk and link breadcrumbs to their parent session.
*   **Special Identifiers**: The `maestro wsession` CLI supports "latest" as a special `session_id` argument to refer to the most recently modified session.

**Key Data Structure**: `maestro.work_session.WorkSession` (dataclass)
```python
@dataclass
class WorkSession:
    session_id: str  # UUID or timestamp-based ID
    session_type: str  # e.g., work_track, work_phase, work_task
    parent_session_id: Optional[str] = None
    status: str = SessionStatus.RUNNING.value
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    modified: str = field(default_factory=lambda: datetime.now().isoformat())
    related_entity: Dict[str, Any] = field(default_factory=dict)
    breadcrumbs_dir: str = ""  # Path to breadcrumbs subdirectory
    metadata: Dict[str, Any] = field(default_factory=dict)
```

## 2. Work-Run Data Storage (File Layout & IPC Mailbox)

All work session data, including session metadata and breadcrumbs, is stored on the local filesystem. This file-based approach inherently supports IPC through polling.

*   **Base Path**: All sessions are stored under the `docs/sessions/` directory, relative to the project root.
    *   **Reference**: `maestro.work_session.py`, `base_path = Path("docs") / "sessions"`
*   **Session Directory Structure**:
    *   **Top-level Session**: `docs/sessions/<session_id>/`
    *   **Nested (Child) Session**: `docs/sessions/<parent_session_id>/<session_id>/`
    *   **Reference**: `maestro.work_session.create_session`
*   **Session Metadata File**: Each session directory contains a `session.json` file storing the `WorkSession` metadata.
    *   **Example Path**: `docs/sessions/<session_id>/session.json`
*   **Breadcrumbs Directory**: Within each session directory, a dedicated `breadcrumbs/` subdirectory exists, further organized by `depth_level`.
    *   **Example Path**: `docs/sessions/<session_id>/breadcrumbs/<depth_level>/`
    *   **Reference**: `WorkSession.breadcrumbs_dir` attribute.
*   **Breadcrumb Files**: Individual breadcrumbs are stored as JSON files within their respective `depth_level` directory, named after their timestamp.
    *   **Example Path**: `docs/sessions/<session_id>/breadcrumbs/<depth_level>/<timestamp>.json`

### File Operations and Multi-process Safety

*   **Atomic Writes**: Both `session.json` and breadcrumb files are written using an atomic write mechanism (write to a temporary file, then `os.replace` to the target file). This ensures data integrity and is safe for concurrent writes from multiple processes attempting to update the same logical file (though not the same physical file for breadcrumbs due to unique timestamps).
    *   **Reference**: `maestro.work_session.save_session`, `maestro.breadcrumb.write_breadcrumb`

## 3. Breadcrumb Message Schema

Breadcrumbs record individual AI interactions and system actions. Their schema is strictly defined by the `maestro.breadcrumb.Breadcrumb` dataclass.

**Key Data Structure**: `maestro.breadcrumb.Breadcrumb` (dataclass)
```python
@dataclass
class Breadcrumb:
    timestamp: str       # ISO 8601 timestamp (YYYYMMDD_HHMMSS_microseconds format)
    breadcrumb_id: str   # Unique ID for this breadcrumb (UUID)

    prompt: str          # Input prompt text
    response: str        # AI response (can be JSON)
    tools_called: List[Dict[str, Any]] # List of tool invocations with args and results
    files_modified: List[Dict[str, Any]] # List of {path, diff, operation}

    parent_session_id: Optional[str] # Reference if this is a sub-worker
    depth_level: int     # Depth in session tree (0 for top-level)

    model_used: str      # AI model name (sonnet, opus, haiku)
    token_count: Dict[str, int] # {input: N, output: M}
    cost: Optional[float] # Estimated cost in USD
    error: Optional[str] # Error message if operation failed
```

*   **`tools_called` Schema Example**:
    ```json
    {
        "tool": "tool_name",
        "args": {"arg1": "value1", "arg2": "value2"},
        "result": "tool_output",
        "error": null,
        "timestamp": "ISO_TIMESTAMP"
    }
    ```
*   **`files_modified` Schema Example**:
    ```json
    {
        "path": "/path/to/file.txt",
        "operation": "modify", // "create", "modify", "delete"
        "diff": "--- a/file.txt\n+++ b/file.txt\n...",
        "timestamp": "ISO_TIMESTAMP",
        "size": 1234
    }
    ```

## 4. How `maestro wsession` Interacts (Reading/Writing)

The `maestro wsession` command and its subcommands (e.g., `list`, `show`, `breadcrumbs`, `timeline`, `stats`) primarily interact by reading existing session and breadcrumb files.

*   **Reading Sessions**:
    *   `maestro.work_session.list_sessions`: Iterates through `docs/sessions/` and its subdirectories to find and load `session.json` files.
    *   `maestro.work_session.load_session`: Reads a specific `session.json` file into a `WorkSession` object.
*   **Writing Sessions**:
    *   `maestro.work_session.create_session`: Creates the session directory structure and writes the initial `session.json`.
    *   `maestro.work_session.save_session`: Updates an existing `session.json` (e.g., changing status or modified timestamp).
*   **Reading Breadcrumbs**:
    *   `maestro.breadcrumb.list_breadcrumbs`: Scans the `breadcrumbs/<depth_level>/` directories within a given `session_id`'s path, loading individual `<timestamp>.json` files into `Breadcrumb` objects. The list is sorted by timestamp.
    *   `maestro.breadcrumb.load_breadcrumb`: Reads a specific breadcrumb JSON file.
*   **Writing Breadcrumbs**:
    *   `maestro.breadcrumb.write_breadcrumb`: Takes a `Breadcrumb` object and writes it to the appropriate `docs/sessions/<session_id>/breadcrumbs/<depth_level>/<timestamp>.json` file.

## 5. Polling/Consumption (Current Gap)

The current `maestro wsession` command functions are reactive readers of the session and breadcrumb data. They do not implement an active polling mechanism themselves. The responsibility for "maestro work polls for updates and applies them to the Work Session log" (as stated in the WF-15 requirements) lies with the `maestro work` command, which is external to `maestro/commands/work_session.py` and `maestro/breadcrumb.py`.

**Current Gap**: The explicit polling logic for `maestro work` to consume breadcrumbs (messages) from the `docs/sessions/<session_id>/breadcrumbs/` mailbox is not found in the examined `maestro.work_session` or `maestro.breadcrumb` modules. This mechanism would need to read the newly written breadcrumb files, process them, and potentially move/archive them to ensure "exactly once" processing, or rely on sorting and tracking already-processed files.

## 6. Key Functions and Classes

*   **`maestro/work_session.py`**:
    *   `WorkSession` (dataclass): Defines the structure of a work session.
    *   `create_session(session_type, ...)`: Creates a new work session, including directory structure and initial `session.json`.
    *   `load_session(session_path)`: Loads a `WorkSession` object from a `session.json` file.
    *   `save_session(session, session_path)`: Saves (updates) a `WorkSession` object to `session.json` using atomic write.
    *   `list_sessions(...)`: Discovers and loads all work sessions, with optional filtering.
*   **`maestro/breadcrumb.py`**:
    *   `Breadcrumb` (dataclass): Defines the structure of an AI interaction breadcrumb.
    *   `create_breadcrumb(...)`: Factory function to create a new `Breadcrumb` object.
    *   `write_breadcrumb(breadcrumb, session_id, ...)`: Writes a `Breadcrumb` object to a JSON file in the session's breadcrumbs directory using atomic write.
    *   `load_breadcrumb(filepath)`: Loads a `Breadcrumb` object from its JSON file.
    *   `list_breadcrumbs(session_id, ...)`: Discovers and loads all breadcrumbs for a given session, with optional filtering.

## 7. Dead/Unused Code Paths

None identified in the context of the `wsession` command's core functionality for session and breadcrumb management.

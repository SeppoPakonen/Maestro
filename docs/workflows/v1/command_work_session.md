# Work Session Management Commands

## Overview

Work sessions provide a structured way to track AI interactions with hierarchical tracking for tasks, phases, and tracks. Each work session maintains a persistent context that can span multiple AI sessions and includes breadcrumb tracking for auditability.

## Data Model and Storage

### WorkSession Data Model

The `WorkSession` dataclass (in `maestro/work_session.py`) contains:

```python
@dataclass
class WorkSession:
    session_id: str                    # UUID or timestamp-based ID
    session_type: str                  # work_track, work_phase, work_issue, discussion, analyze, fix
    parent_session_id: Optional[str]   # Link to parent if this is a sub-worker
    status: str                        # running, paused, completed, interrupted, failed
    created: str                       # ISO 8601 timestamp
    modified: str                      # ISO 8601 timestamp
    related_entity: Dict[str, Any]     # {track_id: ..., phase_id: ..., issue_id: ..., etc.}
    breadcrumbs_dir: str               # Path to breadcrumbs subdirectory
    metadata: Dict[str, Any]           # Additional flexible metadata
```

### Storage Structure

Work sessions are stored in `docs/sessions/` with the following directory structure:

```
docs/sessions/
├── <session_id>/
│   ├── session.json              # Session metadata
│   └── breadcrumbs/
│       ├── 0/                    # Depth level 0 breadcrumbs
│       │   ├── <timestamp>.json
│       │   └── ...
│       ├── 1/                    # Depth level 1 breadcrumbs (sub-workers)
│       │   ├── <timestamp>.json
│       │   └── ...
│       └── ...
└── <parent_session_id>/
    ├── <child_session_id>/
    │   ├── session.json
    │   └── breadcrumbs/
    │       └── ...
    └── ...
```

### Session Status Enum

```python
class SessionStatus(Enum):
    RUNNING = "running"
    PAUSED = "paused" 
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
```

### Session Type Enum

```python
class SessionType(Enum):
    WORK_TRACK = "work_track"
    WORK_PHASE = "work_phase"
    WORK_TASK = "work_task"
    WORK_ISSUE = "work_issue"
    DISCUSSION = "discussion"
    ANALYZE = "analyze"
    FIX = "fix"
```

## CLI Router Entries

### Work Session Commands

The work session commands are defined in `maestro/commands/work_session.py` and registered in the main parser in `maestro/main.py`.

### Available Commands

#### `maestro wsession list` (aliases: `ws ls`, `ws l`)

Lists all work sessions with optional filtering.

**Usage:**
```
maestro wsession list [--type TYPE] [--status STATUS] [--since TIMESTAMP] 
                      [--entity ENTITY] [--sort-by FIELD] [--reverse]
```

**Options:**
- `--type`: Filter by session type (work_task, work_phase, etc.)
- `--status`: Filter by session status (running, completed, etc.)
- `--since`: Filter by created timestamp (ISO format YYYY-MM-DD...)
- `--entity`: Filter by related entity value
- `--sort-by`: Sort field (created, modified, status, type)
- `--reverse`: Reverse sort order

**Example:**
```
maestro wsession list --type work_task --status running
```

#### `maestro wsession show` (aliases: `ws sh`)

Shows detailed information about a specific work session.

**Usage:**
```
maestro wsession show <session_id> [--all] [--export-json PATH] [--export-md PATH]
```

**Arguments:**
- `session_id`: Session ID (or prefix) or "latest"

**Options:**
- `--all`: Show all breadcrumbs instead of limited view
- `--export-json`: Export session JSON to file
- `--export-md`: Export session Markdown to file

**Example:**
```
maestro wsession show latest
```

#### `maestro wsession tree` (aliases: `ws tr`)

Shows the hierarchical tree of sessions.

**Usage:**
```
maestro wsession tree [--depth DEPTH] [--status STATUS] [--show-breadcrumbs]
```

**Options:**
- `--depth`: Max depth to display
- `--status`: Filter by session status
- `--show-breadcrumbs`: Show breadcrumb counts

**Example:**
```
maestro wsession tree --show-breadcrumbs
```

#### `maestro wsession breadcrumbs`

Shows breadcrumbs for a specific session.

**Usage:**
```
maestro wsession breadcrumbs <session_id> [--summary] [--depth DEPTH] [--limit LIMIT]
```

**Arguments:**
- `session_id`: Session ID (or prefix) or "latest"

**Options:**
- `--summary`: Show summary only
- `--depth`: Depth level to include
- `--limit`: Limit number of breadcrumbs displayed

**Example:**
```
maestro wsession breadcrumbs latest --limit 5
```

#### `maestro wsession timeline`

Shows chronological timeline for a session.

**Usage:**
```
maestro wsession timeline <session_id>
```

**Arguments:**
- `session_id`: Session ID (or prefix) or "latest"

**Example:**
```
maestro wsession timeline latest
```

#### `maestro wsession stats`

Shows statistics for a session.

**Usage:**
```
maestro wsession stats [session_id] [--tree]
```

**Arguments:**
- `session_id`: Session ID (or prefix) or "latest" (optional, shows all if omitted)

**Options:**
- `--tree`: Include child sessions in statistics

**Example:**
```
maestro wsession stats latest --tree
```

## Session Lifecycle

### Create
- `create_session()` function in `maestro/work_session.py`
- Generates unique UUID for session ID
- Creates directory structure: `docs/sessions/<session_id>/`
- Initializes `session.json` with initial metadata
- Creates `breadcrumbs/` subdirectory
- Sets initial status to "running"

### Open
- `load_session()` function loads existing session from `session.json`
- Validates required fields
- Updates session with latest metadata

### Append (Breadcrumbs)
- `create_breadcrumb()` creates structured breadcrumb object
- `write_breadcrumb()` writes to appropriate depth directory
- Each breadcrumb is stored as timestamped JSON file

### Close
- `complete_session()` marks session as completed
- Updates modified timestamp
- Saves updated session metadata

## Breadcrumb Schema

Each breadcrumb follows the `Breadcrumb` dataclass:

```python
@dataclass
class Breadcrumb:
    timestamp: str                    # ISO 8601 timestamp
    breadcrumb_id: str                # Unique ID for this breadcrumb
    prompt: str                       # Input prompt text
    response: str                     # AI response (can be JSON)
    tools_called: List[Dict[str, Any]] # List of tool invocations with args and results
    files_modified: List[Dict[str, Any]] # List of {path, diff, operation}
    parent_session_id: Optional[str]  # Reference if this is a sub-worker
    depth_level: int                  # Directory depth in session tree
    model_used: str                   # AI model name (sonnet, opus, haiku)
    token_count: Dict[str, int]       # {input: N, output: M}
    cost: Optional[float]             # Estimated cost in USD
    error: Optional[str]              # Error message if operation failed
```

## Indexing and Search

Currently, there is no explicit indexing or search functionality for work sessions beyond file system organization by session ID and depth level. However, the hierarchical structure allows for:

- Session filtering by type, status, or creation time
- Breadcrumb retrieval by session and depth
- Timeline reconstruction by chronological sorting of breadcrumbs

## Retention Policy

Work sessions are stored in the repository's `docs/sessions/` directory, meaning they are version-controlled along with the project. There is currently no automated retention policy - sessions remain until manually deleted.

Some session metadata may also be stored in `$HOME/.maestro` for cross-project coordination, but the primary session data remains in the repository.

## Key Functions and Classes

### Core Session Functions (maestro/work_session.py)
- `create_session()` - Create new work session
- `load_session()` - Load existing session from disk
- `save_session()` - Save session updates to disk
- `list_sessions()` - List all sessions with optional filtering
- `get_session_hierarchy()` - Get parent-child session tree
- `complete_session()` - Mark a session as completed
- `interrupt_session()` - Handle interruption of a session

### Core Breadcrumb Functions (maestro/breadcrumb.py)
- `create_breadcrumb()` - Create a new breadcrumb with auto-generated timestamp and ID
- `write_breadcrumb()` - Write breadcrumb to disk
- `load_breadcrumb()` - Load a single breadcrumb from file
- `list_breadcrumbs()` - List all breadcrumbs for a session
- `reconstruct_session_timeline()` - Build full session history by loading all breadcrumbs
- `get_breadcrumb_summary()` - Summarize breadcrumbs for a session

### Session Management Commands (maestro/commands/work_session.py)
- `handle_wsession_list()` - Handle the 'wsession list' command
- `handle_wsession_show()` - Handle the 'wsession show' command
- `handle_wsession_tree()` - Handle the 'wsession tree' command
- `handle_wsession_breadcrumbs()` - Handle the 'wsession breadcrumbs' command
- `handle_wsession_timeline()` - Handle the 'wsession timeline' command
- `handle_wsession_stats()` - Handle the 'wsession stats' command

## Existing Tests

Tests for work sessions and breadcrumbs would likely be located in the test directories of the project. Key areas that would be tested include:

- Session creation and loading
- Breadcrumb creation and persistence
- Session hierarchy and parent-child relationships
- Session status transitions
- Breadcrumb filtering and timeline reconstruction
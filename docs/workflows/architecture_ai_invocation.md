# Architecture: AI Invocation Model

## Overview

This document describes the AI invocation model in Maestro, specifically addressing whether the AI calls Maestro again (nested CLI) or if the outer Maestro mediates everything.

## Current Implementation: Hybrid Model

The current implementation uses a **hybrid model** that combines both approaches:

1. **Outer Maestro orchestrates AI sessions** - The main Maestro process manages the work session lifecycle and coordinates with AI engines
2. **Direct AI engine subprocesses** - AI engines run as subprocesses of the main Maestro process
3. **Inner Maestro invocation for task synchronization** - When AI completes a task, it calls `maestro ai sync` which is a nested Maestro invocation

## Process Topology

### 1. Outer Maestro Process (Orchestrator)
- Main CLI process that coordinates work sessions
- Manages session lifecycle and state
- Coordinates with AI engines via subprocess communication
- Handles final validation and state updates

### 2. AI Engine Process
- Individual AI engine subprocess (Claude, Qwen, Gemini, Codex)
- Handles actual AI interaction and streaming
- Communicates with outer Maestro via subprocess pipes
- Produces stream-JSON events

### 3. Inner Maestro Invocation (Task Sync)
- When AI completes a task, it calls `maestro ai sync`
- This triggers a nested Maestro invocation to get the next task
- Uses shared memory or file-based coordination
- Maintains session continuity

## Communication Mechanisms

### Subprocess Communication
- **Pipes**: Used for communication between outer Maestro and AI engines
- **File-based coordination**: `docs/ai_sync.json` for task synchronization
- **Shared memory**: Used for fast sync state between processes (when available)

### Shared Memory Implementation
The `maestro/ai/task_sync.py` module implements shared memory for fast coordination:

```python
SHARED_SYNC_NAME = "maestro_ai_sync"
SHARED_SYNC_SIZE = 65536

def _read_shared_sync_state() -> Optional[Dict[str, Any]]:
    if shared_memory is None:
        return None
    # ... implementation using multiprocessing.shared_memory

def _write_shared_sync_state(payload: Dict[str, Any]) -> None:
    if shared_memory is None:
        return
    # ... implementation using multiprocessing.shared_memory
```

### File-based Fallback
When shared memory is not available, the system falls back to file-based coordination:

```python
def load_sync_state() -> Dict[str, Any]:
    shared_state = _read_shared_sync_state()  # Try shared memory first
    if shared_state is not None:
        return shared_state
    # Fallback to file-based coordination
    path = Path("docs/ai_sync.json")
    # ... read from file
```

## Design Intent vs Implementation

### Intended Design
The original design intended for a more distributed model where AI agents could independently coordinate with Maestro for task synchronization.

### Actual Implementation
The current implementation is more centralized:
- Outer Maestro manages the overall session
- AI engines run as controlled subprocesses
- Task synchronization happens via nested Maestro invocation
- Coordination uses shared memory (with file fallback) for performance

## IPC/Communication Channels

1. **Subprocess Pipes**: For real-time AI interaction
2. **Shared Memory**: For fast sync state between outer Maestro and AI sync operations
3. **File System**: For persistent state (session.json, breadcrumbs, sync state)
4. **Log Files**: For transcript storage and debugging

## Deviation from Intended Design

There is a notable deviation from the originally intended fully distributed model:

- **Intended**: AI agents would independently communicate with Maestro for task coordination
- **Implemented**: AI agents are subprocesses of Maestro with tight coupling via shared memory/file coordination

This implementation provides better reliability and state management but with less autonomy for the AI agents than originally intended.

## Key Files and Functions

### Core Architecture Files
- `maestro/ai/task_sync.py` - Task synchronization with shared memory
- `maestro/ai/runner.py` - AI engine subprocess management
- `maestro/ai/manager.py` - Unified AI engine management
- `maestro/commands/ai.py` - AI command handlers including sync
- `maestro/work_session.py` - Work session management

### Key Functions
- `run_engine_command()` in `runner.py` - Subprocess execution of AI engines
- `handle_ai_sync()` in `ai.py` - Inner Maestro invocation for task sync
- `_read_shared_sync_state()` and `_write_shared_sync_state()` in `task_sync.py` - Shared memory coordination
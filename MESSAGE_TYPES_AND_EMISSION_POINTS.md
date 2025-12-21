# Message Types and Emission Points for AI CLI Live Tool Protocol

## Overview

This document details the specific message types defined in the AI CLI Live Tool Protocol and when/where they should be emitted during AI agent operations.

## Message Types and Emission Points

### 1. Tool Events

#### 1.1 `tool_call_request`
**Purpose**: Emitted when a tool call is initiated by the AI agent.

**When Emitted**:
- Right before executing any tool operation (read_file, write_file, edit_file, execute_command, etc.)
- Before any file system modification
- Before any command execution

**Where Emitted**:
- In `maestro/main.py` before file operations in `apply_fix_plan_operations()`
- In `maestro/ai/actions.py` before action execution
- In `maestro/engines.py` before external command execution

**Payload Example**:
```json
{
  "type": "tool_call_request",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "call-67890",
  "data": {
    "call_id": "read_file-12345",
    "name": "read_file",
    "args": {
      "file_path": "/path/to/file.txt"
    },
    "is_client_initiated": false
  }
}
```

#### 1.2 `tool_call_confirmation`
**Purpose**: Emitted when a tool requires confirmation before execution.

**When Emitted**:
- Before executing potentially destructive operations (file deletion, system commands, etc.)
- When operating in approval mode
- Before operations that modify important system files

**Where Emitted**:
- In `maestro/ai/actions.py` before modifying todo.md or phase files
- In `maestro/main.py` before file system operations
- In `maestro/engines.py` before running external commands

**Payload Example**:
```json
{
  "type": "tool_call_confirmation",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "call-67890",
  "data": {
    "request": {
      "callId": "edit_file-12345",
      "name": "edit_file",
      "args": {
        "file_path": "/path/to/file.txt",
        "content": "new content"
      },
      "isClientInitiated": false,
      "prompt_id": "prompt-12345",
      "response_id": "response-67890"
    },
    "details": {
      "type": "edit",
      "title": "File Edit Confirmation",
      "onConfirm": "function reference",
      "fileName": "file.txt",
      "filePath": "/path/to/file.txt",
      "fileDiff": "@@ -1,3 +1,3 @@\n-old content\n+new content\n unchanged line",
      "originalContent": "old content\nunchanged line",
      "newContent": "new content\nunchanged line",
      "isModifying": true
    }
  }
}
```

#### 1.3 `tool_call_response`
**Purpose**: Emitted when a tool call completes and returns a result.

**When Emitted**:
- Immediately after a tool operation completes (success or failure)
- After receiving results from external commands
- After file operations complete

**Where Emitted**:
- In `maestro/main.py` after file operations in `apply_fix_plan_operations()`
- In `maestro/ai/actions.py` after action execution
- In `maestro/engines.py` after external command execution

**Payload Example**:
```json
{
  "type": "tool_call_response",
  "timestamp": "2025-01-10T12:00:00.100Z",
  "session_id": "session-12345",
  "correlation_id": "call-67890",
  "data": {
    "call_id": "read_file-12345",
    "responseParts": [
      {
        "text": "File content here..."
      }
    ],
    "resultDisplay": "File content: Hello, World!",
    "error": null,
    "errorType": null,
    "outputFile": null,
    "contentLength": 13
  }
}
```

#### 1.4 `tool_execution_status`
**Purpose**: Periodic status updates during tool execution.

**When Emitted**:
- During long-running operations
- At regular intervals during complex operations
- When progress can be reported

**Where Emitted**:
- In long-running functions in `maestro/main.py`
- In build/pipeline execution functions
- In file processing functions

### 2. Stream Events

#### 2.1 `message_start`
**Purpose**: Indicates start of an assistant message.

**When Emitted**:
- When the AI begins generating a response
- At the start of any AI-generated message

**Where Emitted**:
- In `maestro/engines.py` in `stream_message()` function
- In AI interaction functions in `maestro/commands/work.py`

**Payload Example**:
```json
{
  "type": "message_start",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "message": {
    "id": "msg-12345",
    "role": "assistant",
    "model": "claude-sonnet"
  }
}
```

#### 2.2 `content_block_start`
**Purpose**: Indicates start of a content block.

**When Emitted**:
- When starting to generate a new content block (text, tool use, etc.)
- Before starting to process a new part of the AI response

**Where Emitted**:
- In streaming response functions in `maestro/engines.py`
- In AI response parsing functions

**Payload Example**:
```json
{
  "type": "content_block_start",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "index": 0,
  "content_block": {
    "type": "tool_use",
    "id": "toolu-12345",
    "name": "read_file",
    "input": {
      "file_path": "/path/to/file.txt"
    }
  }
}
```

#### 2.3 `content_block_delta`
**Purpose**: Streaming update to a content block.

**When Emitted**:
- As content is being generated and streamed
- For each chunk of content received from the AI

**Where Emitted**:
- In streaming response functions in `maestro/engines.py`
- During AI response processing

**Payload Example**:
```json
{
  "type": "content_block_delta",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "index": 0,
  "delta": {
    "type": "input_json_delta",
    "partial_json": "{\"file_path\": \"/path/to/"
  }
}
```

#### 2.4 `content_block_stop`
**Purpose**: Indicates end of a content block.

**When Emitted**:
- When a content block is complete
- After all content for a block has been received

**Where Emitted**:
- In streaming response functions in `maestro/engines.py`
- After completing content block processing

**Payload Example**:
```json
{
  "type": "content_block_stop",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "index": 0
}
```

#### 2.5 `message_stop`
**Purpose**: Indicates end of an assistant message.

**When Emitted**:
- When the AI response is complete
- At the end of any AI-generated message

**Where Emitted**:
- In streaming response functions in `maestro/engines.py`
- At the end of AI interaction functions

**Payload Example**:
```json
{
  "type": "message_stop",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345"
}
```

### 3. Control Events

#### 3.1 `user_input`
**Purpose**: User input sent to the agent.

**When Emitted**:
- When user provides input to the AI agent
- When processing user commands

**Where Emitted**:
- In command processing functions in `maestro/main.py`
- In TUI interaction functions in `maestro/tui/`

#### 3.2 `interrupt`
**Purpose**: Interrupt signal to stop current processing.

**When Emitted**:
- When user interrupts AI processing (Ctrl+C)
- When external interruption occurs

**Where Emitted**:
- In signal handling functions
- In interruption detection functions

#### 3.3 `status_update`
**Purpose**: System status updates.

**When Emitted**:
- Periodically to report system status
- When significant state changes occur

**Where Emitted**:
- In status reporting functions
- In monitoring functions

#### 3.4 `error`
**Purpose**: Error notifications.

**When Emitted**:
- When any error occurs during operation
- When tool execution fails
- When communication fails

**Where Emitted**:
- In error handling blocks throughout the codebase
- In `maestro/main.py` for operation errors
- In `maestro/engines.py` for engine errors
- In `maestro/commands/work.py` for work session errors

### 4. Session Events

#### 4.1 `session_start`
**Purpose**: Session initialization.

**When Emitted**:
- When a new AI interaction session begins
- When starting any new work session

**Where Emitted**:
- In `create_session()` in `maestro/work_session.py`

#### 4.2 `session_end`
**Purpose**: Session termination.

**When Emitted**:
- When an AI interaction session ends
- When completing any work session

**Where Emitted**:
- In `complete_session()` in `maestro/work_session.py`

#### 4.3 `session_state`
**Purpose**: Current session state snapshot.

**When Emitted**:
- When session state changes significantly
- Periodically during long sessions
- When requested by external systems

**Where Emitted**:
- In `save_session()` in `maestro/work_session.py`
- In state change functions

## Priority Levels for Messages

The protocol defines priority levels for messages:

- **P0 (Critical)**: Error messages, interrupt signals, session termination
- **P1 (High)**: Tool confirmation requests, user input responses
- **P2 (Normal)**: Tool call responses, status updates
- **P3 (Low)**: Content streaming, logging messages

## Transport Mechanisms

Messages should be sent using the configured transport mechanism:
- STDIO (default for subprocess communication)
- TCP (for network-based scenarios)
- Named Pipes (for local IPC)

## Message Framing

All messages use newline-delimited JSON (NDJSON) format with each message being a complete, self-contained JSON object terminated by a newline character (`\n`).
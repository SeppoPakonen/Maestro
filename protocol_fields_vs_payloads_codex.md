# Protocol Fields vs Current Payloads - Codex Integration Analysis

## Overview
This document compares the required fields for the AI CLI Live Tool Protocol with the current payload structures in the Maestro system. This analysis is part of Task aicli5-1: Codex Integration Plan.

## Protocol Requirements (AI CLI Live Tool Protocol Specification)

### Basic Message Structure
All messages in the protocol follow this structure:
```json
{
  "type": "message_type",
  "timestamp": "ISO 8601 timestamp",
  "session_id": "unique session identifier",
  "correlation_id": "optional correlation identifier for request/response matching",
  "data": { /* message-specific payload */ }
}
```

### Required Message Types and Their Fields

#### 1. Tool Events
- **`tool_call_request`**
  - Required fields in `data`:
    - `call_id`: Unique identifier for the call
    - `name`: Name of the tool being called
    - `args`: Arguments passed to the tool
    - `is_client_initiated`: Boolean indicating if call was initiated by client

- **`tool_call_response`**
  - Required fields in `data`:
    - `call_id`: Matching ID from the request
    - `result` or `error`: Either the result or error information
    - `execution_time_ms`: Execution time in milliseconds

- **`tool_call_confirmation`**
  - Required fields in `data`:
    - `call_id`: Matching ID from the request
    - `name`: Name of the tool requiring confirmation
    - `args`: Arguments that will be passed to the tool
    - Confirmation request details

- **`tool_execution_status`**
  - Required fields in `data`:
    - `call_id`: Matching ID from the request
    - `status`: Execution status (e.g., "in_progress", "completed")
    - Progress or status information

#### 2. Stream Events
- **`message_start`**
  - Required fields in `data`:
    - `message`: Message object with id, role, model

- **`content_block_start`**
  - Required fields in `data`:
    - `content_block_id`: Unique identifier for the content block
    - `content_type`: Type of content (e.g., "text", "code")

- **`content_block_delta`**
  - Required fields in `data`:
    - `content_block_id`: Matching ID from start event
    - `delta`: Delta object with type and content

- **`content_block_stop`**
  - Required fields in `data`:
    - `content_block_id`: Matching ID from start event

- **`message_stop`**
  - No specific required fields in `data`

#### 3. Control Events
- **`user_input`**
  - Required fields in `data`:
    - `content`: The actual user input content

- **`interrupt`**
  - Required fields in `data`:
    - Context or reason for the interrupt

- **`status_update`**
  - Required fields in `data`:
    - `status`: The status information

- **`error`**
  - Required fields in `data`:
    - `error_code`: Standardized error code
    - `message`: Human-readable error message
    - `severity`: Error severity level (fatal, error, warning)
    - `retriable`: Boolean indicating if operation is retriable

#### 4. Session Events
- **`session_start`**
  - Required fields in `data`:
    - Session configuration and initialization parameters

- **`session_end`**
  - Required fields in `data`:
    - Session summary and termination reason

- **`session_state`**
  - Required fields in `data`:
    - Complete snapshot of current session state

## Current Payload Structures in Maestro System

Based on analysis of the Maestro codebase, here are the current payload structures that need to be mapped to the protocol:

### 1. File Operation Payloads
Currently, operations like WriteFileOperation contain:
- `path`: The target file path
- `content`: The content to write
- `op`: Operation type

**Mapping to Protocol**:
- `WriteFileOperation` → `tool_call_request` with `name: "write_file"`
- Args: `{"file_path": path, "content": content}`

### 2. Rename Operation Payloads
Currently, RenameOperation contains:
- `from_path`: Source path
- `to_path`: Destination path
- `op`: Operation type

**Mapping to Protocol**:
- `RenameOperation` → `tool_call_request` with `name: "rename_file"`
- Args: `{"from_path": from_path, "to_path": to_path}`

### 3. Session Data
Currently, session tracking contains:
- `session_id`: Unique identifier
- `status`: Session status
- `subtasks`: List of related subtasks

**Mapping to Protocol**:
- Session data → `session_start`, `session_state`, `session_end` messages

### 4. AI Interaction Payloads
Currently, AI interactions contain:
- Conversation history with role and content
- Context information
- Model information

**Mapping to Protocol**:
- AI responses → `content_block_start`, `content_block_delta`, `content_block_stop`
- Conversation updates → Appropriate stream events

## Gaps Analysis

### 1. Missing Fields
- **Correlation IDs**: The current system doesn't track correlation IDs for matching requests/responses
- **Execution Time Tracking**: Need to implement timing mechanisms to capture execution_time_ms
- **Structured Error Handling**: Need to map current exceptions to protocol error format

### 2. Field Transformation Requirements
- **Timestamp Format**: Current timestamps need to be converted to ISO 8601 format
- **Payload Restructuring**: Current data structures need to be restructured to match protocol requirements
- **Session Context**: Need to enhance session context tracking to include protocol session ID

### 3. Implementation Considerations
- **Backward Compatibility**: Maintain current functionality while adding protocol support
- **Performance Impact**: Ensure protocol implementation doesn't significantly impact performance
- **Error Recovery**: Implement proper error handling and recovery mechanisms

## Implementation Recommendations

### 1. Protocol Emitter Module
Create a dedicated module for protocol message emission that:
- Generates proper message structures with all required fields
- Handles correlation ID management
- Provides timing utilities
- Includes proper error formatting

### 2. Session Context Enhancement
Enhance current session tracking to include:
- Protocol session ID generation and management
- Correlation ID tracking
- Timestamp generation in proper format

### 3. Event Interceptors
Implement interceptors at key points in the existing codebase to:
- Capture operation requests and convert to tool_call_request
- Capture operation responses and convert to tool_call_response
- Capture streaming content and convert to stream events
- Capture errors and convert to error messages

## Conclusion

Successfully identified gaps between required protocol fields and current payload structures. The main implementation tasks involve:

1. Adding correlation ID tracking
2. Implementing proper timestamp formatting
3. Creating structured error messages
4. Developing event interceptors for existing operations
5. Enhancing session management with protocol requirements

The Maestro system can be enhanced to support the AI CLI Live Tool Protocol by implementing these mapping requirements while maintaining existing functionality.
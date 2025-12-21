# Protocol Fields vs Current Payloads - Claude-Code Integration Analysis

## Overview
This document compares the required fields for the AI CLI Live Tool Protocol with the current payload structures specific to the Claude-Code integration. This analysis is part of Task aicli5-2: Claude-Code Integration Plan.

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

### Required Message Types and Their Fields for Claude-Code

#### 1. Tool Events
- **`tool_call_request`** (for Claude API calls)
  - Required fields in `data`:
    - `call_id`: Unique identifier for the Claude call
    - `name`: "claude_planner" or similar
    - `args`: Arguments passed to Claude (prompt, parameters)
    - `is_client_initiated`: Boolean indicating if call was initiated by client

- **`tool_call_response`** (for Claude responses)
  - Required fields in `data`:
    - `call_id`: Matching ID from the request
    - `result`: The Claude response content
    - `execution_time_ms`: Execution time in milliseconds

- **`tool_call_confirmation`** (for user confirmations)
  - Required fields in `data`:
    - `call_id`: Matching ID from the request
    - `name`: Name of the action requiring confirmation
    - `args`: Arguments that will be executed
    - Confirmation request details

- **`tool_execution_status`** (for processing updates)
  - Required fields in `data`:
    - `call_id`: Matching ID from the request
    - `status`: Execution status (e.g., "running", "completed")
    - Progress or status information

#### 2. Stream Events (for Claude's streaming responses)
- **`message_start`**
  - Required fields in `data`:
    - `message`: Message object with id, role, model

- **`content_block_start`**
  - Required fields in `data`:
    - `content_block_id`: Unique identifier for the content block
    - `content_type`: Type of content (e.g., "text", "tool_use")

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
    - `input_type`: Type of input (menu_selection, discussion_reply, etc.)

- **`error`**
  - Required fields in `data`:
    - `error_code`: Standardized error code
    - `message`: Human-readable error message
    - `severity`: Error severity level (fatal, error, warning)
    - `retriable`: Boolean indicating if operation is retriable

#### 4. Session Events
- **`session_start`**
  - Required fields in `data`:
    - `session_type`: "claude_planning", "claude_discussion", etc.
    - Session configuration parameters

- **`session_end`**
  - Required fields in `data`:
    - Session summary and termination reason

- **`session_state`**
  - Required fields in `data`:
    - Complete snapshot of current Claude session state

## Current Claude-Code Payload Structures

Based on analysis of the Maestro codebase, Claude-Code currently operates with these structures:

### 1. ClaudePlannerEngine Requests
Currently, Claude-Code requests contain:
- `prompt`: The text prompt being sent to Claude
- `base_args`: Additional arguments for the Claude CLI
- `binary`: Claude binary name ("claude")

**Mapping to Protocol**:
- Claude call → `tool_call_request` with `name: "claude_planner"`
- Args: `{"prompt": prompt, "base_args": base_args}`

### 2. Claude Response Structures
Currently, Claude responses contain:
- `stdout`: Claude's response text
- `stderr`: Error output if any
- `exit_code`: Process exit status

**Mapping to Protocol**:
- Claude response → `tool_call_response` 
- Result: `{"response": stdout, "error": stderr if exit_code != 0}`

### 3. Claude Session Data
Currently, Claude sessions use the general session tracking:
- `session_id`: From general session management
- `status`: Session status
- Conversation history with Claude

**Mapping to Protocol**:
- Claude session data → `session_start`, `session_state`, `session_end` messages

### 4. Claude Streaming Content
Currently, Claude responses are captured as complete text blocks rather than streaming.

**Mapping to Protocol**:
- Claude responses → `content_block_start`, `content_block_delta`, `content_block_stop` when streaming is enabled

## Gaps Analysis for Claude-Code

### 1. Missing Fields
- **Correlation IDs**: Current Claude interaction doesn't track correlation IDs for matching requests/responses
- **Execution Time Tracking**: Need to implement timing mechanisms to capture execution_time_ms
- **Structured Error Handling**: Need to map Claude-specific errors to protocol error format
- **Streaming Support**: Current Claude integration is not streaming-based, which is required for full protocol compliance

### 2. Claude-Specific Protocol Considerations
- **Model Information**: Claude responses should include model information (e.g., "claude-3-5-sonnet-20250205")
- **Tool Use Detection**: Claude might return tool use JSON that needs special handling
- **Content Types**: Claude responses may include different content types (text, tool_use) that need to be identified

### 3. Field Transformation Requirements
- **Timestamp Format**: Current timestamps need to be converted to ISO 8601 format
- **Payload Restructuring**: Claude's response data needs to be restructured to match protocol requirements
- **Session Context**: Need to enhance Claude session context tracking to include protocol session ID

## Claude-Code Implementation Recommendations

### 1. Streaming Claude Engine
Create a streaming version of the ClaudePlannerEngine that:
- Processes Claude responses in real-time
- Emits content_block events as text is received
- Handles Claude's potential tool_use responses

### 2. Claude-Specific Protocol Emitter
Create Claude-specific message generation that:
- Maps Claude's response format to protocol messages
- Handles Claude-specific errors (rate limits, model errors, etc.)
- Tracks conversation state for proper session management

### 3. Session Context Enhancement
Enhance Claude session tracking to include:
- Protocol session ID generation and management
- Correlation ID tracking for Claude requests/responses
- Claude-specific state tracking (conversation history, context window, etc.)

### 4. Claude Tool Integration
Implement support for Claude's potential tool use:
- Detect when Claude returns tool_use JSON
- Convert to appropriate protocol messages
- Handle tool response loops if Claude uses multiple tools

## Claude-Code Protocol Mapping Examples

### Claude Request Example:
**Current**:
```python
prompt = "Write a Python function to calculate fibonacci"
result = run_cli_engine(config, prompt)
```

**Protocol Mapping**:
```python
call_id = f"claude-{timestamp}"
correlation_id = f"corr-{call_id}"

# Emit tool_call_request
emit_protocol_message({
    "type": "tool_call_request",
    "timestamp": iso_timestamp(),
    "session_id": session_id,
    "correlation_id": correlation_id,
    "data": {
        "call_id": call_id,
        "name": "claude_planner",
        "args": {"prompt": prompt},
        "is_client_initiated": False
    }
})

# Execute Claude call
result = run_cli_engine(config, prompt)

# Emit tool_call_response
emit_protocol_message({
    "type": "tool_call_response",
    "timestamp": iso_timestamp(),
    "session_id": session_id,
    "correlation_id": correlation_id,
    "data": {
        "call_id": call_id,
        "result": result.stdout,
        "error": result.stderr if result.exit_code != 0 else None,
        "execution_time_ms": execution_time
    }
})
```

### Claude Streaming Example:
**Current**: Claude responses are not streamed

**Protocol Mapping**:
```python
def stream_claude_response(prompt, session_id):
    # Emit message_start
    emit_protocol_message({
        "type": "message_start",
        "timestamp": iso_timestamp(),
        "session_id": session_id,
        "message": {
            "id": generate_message_id(),
            "role": "assistant",
            "model": "claude-3-5-sonnet-20250205"
        }
    })

    # Emit content_block_start
    block_id = generate_content_block_id()
    emit_protocol_message({
        "type": "content_block_start",
        "timestamp": iso_timestamp(),
        "session_id": session_id,
        "index": 0,
        "content_block": {
            "type": "text",
            "text": ""
        }
    })

    # Stream response and emit deltas
    for chunk in stream_claude_output(prompt):
        emit_protocol_message({
            "type": "content_block_delta",
            "timestamp": iso_timestamp(),
            "session_id": session_id,
            "index": 0,
            "delta": {
                "type": "text_delta",
                "text": chunk
            }
        })
        yield chunk

    # Emit content_block_stop
    emit_protocol_message({
        "type": "content_block_stop",
        "timestamp": iso_timestamp(),
        "session_id": session_id,
        "index": 0
    })

    # Emit message_stop
    emit_protocol_message({
        "type": "message_stop",
        "timestamp": iso_timestamp(),
        "session_id": session_id
    })
```

## Implementation Priority for Claude-Code

1. **High Priority**: Add correlation ID tracking for Claude requests/responses
2. **High Priority**: Implement proper timestamp formatting for Claude interactions
3. **Medium Priority**: Add Claude-specific error handling and mapping
4. **Low Priority**: Implement full Claude streaming support (requires changes to Claude CLI interaction)

## Conclusion

Successfully identified gaps between required protocol fields and current Claude-Code payload structures. The main implementation tasks for Claude-Code integration involve:

1. Adding correlation ID tracking for Claude interactions
2. Implementing proper timestamp formatting
3. Creating Claude-specific error mapping
4. Potentially adding streaming support for Claude responses
5. Enhancing session management to include Claude-specific context

The Claude-Code integration can be enhanced to fully support the AI CLI Live Tool Protocol by implementing these mapping requirements while maintaining the existing functionality.
# Protocol Fields vs Current Payloads - Copilot-CLI Integration Analysis

## Overview
This document compares the required fields for the AI CLI Live Tool Protocol with the current payload structures specific to the Copilot-CLI integration. This analysis is part of Task aicli5-3: Copilot-CLI Integration Plan.

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

### Required Message Types and Their Fields for Copilot-CLI

#### 1. Tool Events
- **`tool_call_request`** (for Copilot tool invocations)
  - Required fields in `data`:
    - `call_id`: Unique identifier for the Copilot tool call
    - `name`: Tool name being called (e.g., "create_file", "edit_code", "review_code")
    - `args`: Arguments passed to the tool
    - `is_client_initiated`: Boolean indicating if call was initiated by client

- **`tool_call_response`** (for Copilot tool results)
  - Required fields in `data`:
    - `call_id`: Matching ID from the request
    - `result` or `error`: Either the result or error information
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
    - `status`: Execution status (e.g., "in_progress", "completed", "failed")
    - Progress or status information

#### 2. Stream Events (for Copilot's streaming responses)
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
    - `input_type`: Type of input (command_parameters, ai_prompt, etc.)

- **`error`**
  - Required fields in `data`:
    - `error_code`: Standardized error code
    - `message`: Human-readable error message
    - `details`: Additional error-specific information
    - `severity`: Error severity level (fatal, error, warning)
    - `retriable`: Boolean indicating if operation is retriable

#### 4. Session Events
- **`session_start`**
  - Required fields in `data`:
    - `session_type`: "copilot_planning", "copilot_discussion", "copilot_tool_execution"
    - Session configuration parameters

- **`session_end`**
  - Required fields in `data`:
    - Session summary and termination reason

- **`session_state`**
  - Required fields in `data`:
    - Complete snapshot of current Copilot session state

## Current Copilot-CLI Payload Structures (Hypothetical)

Since Copilot-CLI would be a separate system, I'll analyze based on typical AI CLI architectures:

### 1. Copilot Command Requests
Currently, Copilot CLI commands might contain:
- `command`: The command being executed (e.g., "suggest", "review", "fix")
- `parameters`: Command parameters
- `context`: Context information for the task

**Mapping to Protocol**:
- Copilot command → `tool_call_request` with `name: "copilot_command"`
- Args: `{"command": command, "parameters": parameters, "context": context}`

### 2. Copilot Tool Responses
Currently, Copilot responses might contain:
- `result`: The Copilot-generated content
- `suggestions`: List of suggestions or recommendations
- `status`: Execution status of the request

**Mapping to Protocol**:
- Copilot response → `tool_call_response`
- Result: `{"result": result, "suggestions": suggestions, "status": status}`

### 3. Copilot Session Data
Currently, Copilot sessions would use general session tracking:
- `session_id`: From general session management
- `status`: Session status
- Interaction history with Copilot

**Mapping to Protocol**:
- Copilot session data → `session_start`, `session_state`, `session_end` messages

### 4. Copilot Streaming Content
Currently, Copilot responses might be either complete blocks or streaming:
- `content_type`: Type of content being streamed
- `content_chunk`: The actual content chunk

**Mapping to Protocol**:
- Copilot responses → `content_block_start`, `content_block_delta`, `content_block_stop` for streaming content

## Gaps Analysis for Copilot-CLI

### 1. Missing Fields
- **Correlation IDs**: Current Copilot interactions don't track correlation IDs for matching requests/responses
- **Execution Time Tracking**: Need to implement timing mechanisms to capture execution_time_ms
- **Structured Error Handling**: Need to map Copilot-specific errors to protocol error format
- **Detailed Status Information**: Current status may not include all required progress information

### 2. Copilot-Specific Protocol Considerations
- **AI Model Information**: Copilot responses should include model information
- **Code-Specific Content Types**: Copilot might generate code-specific content that needs special handling
- **File-Specific Tool Types**: Copilot often works with file operations that need specialized tool handling

### 3. Field Transformation Requirements
- **Timestamp Format**: Current timestamps need to be converted to ISO 8601 format
- **Payload Restructuring**: Copilot's response data needs to be restructured to match protocol requirements
- **Session Context**: Need to enhance Copilot session context tracking to include protocol session ID

## Copilot-CLI Implementation Recommendations

### 1. Copilot-Specific Protocol Emitter
Create Copilot-specific message generation that:
- Maps Copilot's response format to protocol messages
- Handles Copilot-specific errors (authentication, rate limits, etc.)
- Tracks conversation state for proper session management

### 2. Code-Aware Content Handling
Implement support for Copilot's code-specific content:
- Detect when Copilot returns code blocks
- Format code-specific protocol messages
- Handle language-specific tool usage

### 3. Session Context Enhancement
Enhance Copilot session tracking to include:
- Protocol session ID generation and management
- Correlation ID tracking for Copilot requests/responses
- Copilot-specific state tracking (context window, file history, etc.)

### 4. File Operation Integration
Implement proper mapping for Copilot's file operations:
- Convert Copilot's file suggestions to tool call requests
- Handle file modification confirmations
- Track file state changes throughout sessions

## Copilot-CLI Protocol Mapping Examples

### Copilot Request Example:
**Current** (hypothetical):
```python
command = "suggest"
parameters = {"file_path": "src/main.py", "problem": "optimize function"}
result = execute_copilot_command(command, parameters)
```

**Protocol Mapping**:
```python
call_id = f"copilot-{timestamp}"
correlation_id = f"corr-{call_id}"

# Emit tool_call_request
emit_protocol_message({
    "type": "tool_call_request",
    "timestamp": iso_timestamp(),
    "session_id": session_id,
    "correlation_id": correlation_id,
    "data": {
        "call_id": call_id,
        "name": "copilot_suggest",
        "args": parameters,
        "is_client_initiated": False
    }
})

# Execute Copilot command
result = execute_copilot_command(command, parameters)

# Emit tool_call_response
emit_protocol_message({
    "type": "tool_call_response",
    "timestamp": iso_timestamp(),
    "session_id": session_id,
    "correlation_id": correlation_id,
    "data": {
        "call_id": call_id,
        "result": result.result,
        "error": result.error if result.error else None,
        "execution_time_ms": result.execution_time
    }
})
```

### Copilot Streaming Example:
**Current**: Copilot responses may be streaming

**Protocol Mapping**:
```python
def stream_copilot_response(command, params, session_id):
    # Emit message_start
    emit_protocol_message({
        "type": "message_start",
        "timestamp": iso_timestamp(),
        "session_id": session_id,
        "message": {
            "id": generate_message_id(),
            "role": "assistant",
            "model": "copilot"
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
    for chunk in stream_copilot_output(command, params):
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

## Implementation Priority for Copilot-CLI

1. **High Priority**: Add correlation ID tracking for Copilot requests/responses
2. **High Priority**: Implement proper timestamp formatting for Copilot interactions
3. **Medium Priority**: Add Copilot-specific error handling and mapping
4. **Medium Priority**: Implement proper code/file operation mapping to tools
5. **Low Priority**: Implement full Copilot streaming support (if not already present)

## Conclusion

Successfully identified gaps between required protocol fields and current Copilot-CLI payload structures. The main implementation tasks for Copilot-CLI integration involve:

1. Adding correlation ID tracking for Copilot interactions
2. Implementing proper timestamp formatting
3. Creating Copilot-specific error mapping
4. Enhancing session management to include Copilot-specific context
5. Implementing proper mapping of Copilot's code-specific operations to protocol tool calls

The Copilot-CLI integration can be enhanced to fully support the AI CLI Live Tool Protocol by implementing these mapping requirements while maintaining the existing functionality.
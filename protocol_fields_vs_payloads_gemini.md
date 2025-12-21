# Protocol Fields vs Current Payloads - Gemini-CLI Integration Analysis

## Overview
This document compares the required fields for the AI CLI Live Tool Protocol with the current payload structures specific to the Gemini-CLI integration. This analysis is part of Task aicli5-4: Gemini-CLI Integration Plan.

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

### Required Message Types and Their Fields for Gemini-CLI

#### 1. Tool Events
- **`tool_call_request`** (for Gemini API calls)
  - Required fields in `data`:
    - `call_id`: Unique identifier for the Gemini call
    - `name`: Tool name being called (e.g., "gemini_pro", "gemini_flash", etc.)
    - `args`: Arguments passed to the tool (prompt, parameters, context)
    - `is_client_initiated`: Boolean indicating if call was initiated by client

- **`tool_call_response`** (for Gemini responses)
  - Required fields in `data`:
    - `call_id`: Matching ID from the request
    - `result`: The Gemini response content
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
    - `status`: Execution status (e.g., "running", "completed", "failed")
    - Progress or status information

#### 2. Stream Events (for Gemini's streaming responses)
- **`message_start`**
  - Required fields in `data`:
    - `message`: Message object with id, role, model

- **`content_block_start`**
  - Required fields in `data`:
    - `content_block_id`: Unique identifier for the content block
    - `content_type`: Type of content (e.g., "text", "code", "suggestion")

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
    - `session_type`: "gemini_planning", "gemini_discussion", "gemini_tool_execution"
    - Session configuration parameters

- **`session_end`**
  - Required fields in `data`:
    - Session summary and termination reason

- **`session_state`**
  - Required fields in `data`:
    - Complete snapshot of current Gemini session state

## Current Gemini-CLI Payload Structures

Since Gemini-CLI would follow the modular architecture similar to other agents in the Maestro system:

### 1. Gemini Engine Requests
Currently, Gemini CLI requests contain:
- `prompt`: The text prompt being sent to Gemini
- `parameters`: Additional parameters for the Gemini API
- `binary`: Gemini binary name (or API endpoint)

**Mapping to Protocol**:
- Gemini call → `tool_call_request` with `name: "gemini_pro"` (or appropriate model)
- Args: `{"prompt": prompt, "parameters": parameters}`

### 2. Gemini Response Structures
Currently, Gemini responses contain:
- `result`: Gemini's response text or structured data
- `metadata`: Information about the response (token usage, model, etc.)
- `status`: Response status (success, error, etc.)

**Mapping to Protocol**:
- Gemini response → `tool_call_response` 
- Result: `{"response": result, "metadata": metadata, "status": status}`

### 3. Gemini Session Data
Currently, Gemini sessions use the general session tracking:
- `session_id`: From general session management
- `status`: Session status
- Conversation history with Gemini

**Mapping to Protocol**:
- Gemini session data → `session_start`, `session_state`, `session_end` messages

### 4. Gemini Streaming Content
Currently, Gemini responses could be streaming through the `run_cli_engine` function with streaming support:
- `content_chunk`: The individual chunks of content being streamed
- `stream_id`: Identifier for the current stream

**Mapping to Protocol**:
- Gemini responses → `content_block_start`, `content_block_delta`, `content_block_stop` for streaming content

## Gaps Analysis for Gemini-CLI

### 1. Missing Fields
- **Correlation IDs**: Current Gemini interaction doesn't track correlation IDs for matching requests/responses
- **Execution Time Tracking**: Need to implement timing mechanisms to capture execution_time_ms
- **Structured Error Handling**: Need to map Gemini-specific errors to protocol error format
- **Metadata Mapping**: Current Gemini responses have metadata that needs to be mapped to protocol fields

### 2. Gemini-Specific Protocol Considerations
- **Model Information**: Gemini responses should include model information (e.g., "gemini-pro", "gemini-flash")
- **Token Usage**: Gemini responses often include token usage information that should be captured
- **Safety Attributes**: Gemini may return safety ratings that need protocol mapping

### 3. Field Transformation Requirements
- **Timestamp Format**: Current timestamps need to be converted to ISO 8601 format
- **Payload Restructuring**: Gemini's response data needs to be restructured to match protocol requirements
- **Session Context**: Need to enhance Gemini session context tracking to include protocol session ID

## Gemini-CLI Implementation Recommendations

### 1. Gemini-Specific Protocol Emitter
Create Gemini-specific message generation that:
- Maps Gemini's response format to protocol messages
- Handles Gemini-specific errors (rate limits, safety filters, etc.)
- Tracks conversation state for proper session management

### 2. Gemini Content Type Detection
Implement support for Gemini's content types:
- Detect when Gemini returns code blocks
- Format appropriate protocol messages for different content types
- Handle Gemini's potential tool use responses

### 3. Session Context Enhancement
Enhance Gemini session tracking to include:
- Protocol session ID generation and management
- Correlation ID tracking for Gemini requests/responses
- Gemini-specific state tracking (conversation history, context window, etc.)

### 4. API Parameter Mapping
Implement proper mapping for Gemini's API parameters:
- Convert Gemini's request parameters to protocol tool call arguments
- Handle Gemini's response metadata in protocol messages
- Track model-specific features in session state

## Gemini-CLI Protocol Mapping Examples

### Gemini Request Example:
**Current** (hypothetical):
```python
prompt = "Explain how to implement a binary search algorithm"
parameters = {"temperature": 0.7, "max_tokens": 1000, "model": "gemini-pro"}
result = execute_gemini_request(prompt, parameters)
```

**Protocol Mapping**:
```python
call_id = f"gemini-{timestamp}"
correlation_id = f"corr-{call_id}"

# Emit tool_call_request
emit_protocol_message({
    "type": "tool_call_request",
    "timestamp": iso_timestamp(),
    "session_id": session_id,
    "correlation_id": correlation_id,
    "data": {
        "call_id": call_id,
        "name": "gemini_pro",
        "args": {
            "prompt": prompt,
            "parameters": parameters
        },
        "is_client_initiated": False
    }
})

# Execute Gemini request
result = execute_gemini_request(prompt, parameters)

# Emit tool_call_response
emit_protocol_message({
    "type": "tool_call_response",
    "timestamp": iso_timestamp(),
    "session_id": session_id,
    "correlation_id": correlation_id,
    "data": {
        "call_id": call_id,
        "result": result.text,
        "metadata": {
            "model": result.model,
            "token_usage": result.token_usage,
            "safety_ratings": result.safety_ratings
        },
        "execution_time_ms": result.execution_time
    }
})
```

### Gemini Streaming Example:
**Current**: Gemini responses can be streaming

**Protocol Mapping**:
```python
def stream_gemini_response(prompt, params, session_id):
    # Emit message_start
    emit_protocol_message({
        "type": "message_start",
        "timestamp": iso_timestamp(),
        "session_id": session_id,
        "message": {
            "id": generate_message_id(),
            "role": "assistant",
            "model": "gemini-pro"
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
    for chunk in stream_gemini_output(prompt, params):
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

## Implementation Priority for Gemini-CLI

1. **High Priority**: Add correlation ID tracking for Gemini requests/responses
2. **High Priority**: Implement proper timestamp formatting for Gemini interactions
3. **Medium Priority**: Add Gemini-specific error handling and mapping
4. **Medium Priority**: Implement proper metadata mapping from Gemini responses
5. **Low Priority**: Implement full Gemini streaming support (if not already present)

## Conclusion

Successfully identified gaps between required protocol fields and current Gemini-CLI payload structures. The main implementation tasks for Gemini-CLI integration involve:

1. Adding correlation ID tracking for Gemini interactions
2. Implementing proper timestamp formatting
3. Creating Gemini-specific error mapping
4. Enhancing session management to include Gemini-specific context
5. Implementing proper mapping of Gemini's API parameters and metadata to protocol messages

The Gemini-CLI integration can be enhanced to fully support the AI CLI Live Tool Protocol by implementing these mapping requirements while maintaining the existing functionality.
# Error and Disconnect Handling Specification

## Overview

This document defines the comprehensive strategy for error handling and disconnect recovery within the Maestro system. It covers error response schemas, error codes taxonomy, disconnect recovery rules, and logging/diagnostics expectations across all components of the system.

## 1. Error Response Schema

### 1.1 Standard Error Message Format

All errors in the Maestro system follow a standardized JSON format:

```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "ERROR_CODE_CONSTANT",
    "message": "Human-readable error description",
    "details": {
      /* error-specific details */
    },
    "severity": "fatal|error|warning|info",
    "retriable": true|false,
    "component": "component_generating_error",
    "trace_id": "optional_trace_id_for_distributed_tracing"
  }
}
```

### 1.2 Error Message Fields

- **type** (required): Always "error" for error messages
- **timestamp** (required): ISO 8601 formatted timestamp of when error occurred
- **session_id** (required): Session identifier for context
- **correlation_id** (optional): Links error to a specific request or operation
- **data** (required): Container for error-specific information
  - **error_code** (required): Machine-readable error code (uppercase with underscores)
  - **message** (required): Human-readable description of the error
  - **details** (optional): Structured data with specific error context
  - **severity** (required): Impact level of the error (see section 1.3)
  - **retriable** (required): Whether the operation can be safely retried
  - **component** (required): ComNow let me update the todo list and move to the next section:

Perfect! I've created a comprehensive error and disconnect handling specification for the Maestro system. The specification includes:

1. A detailed error response schema with standardized formats and fields
2. A comprehensive taxonomy of error codes organized by category
3. Specific disconnect recovery rules with both automatic and manual strategies
4. Logging and diagnostics expectations with required data structures
5. Implementation guidelines and testing requirements

The specification covers all the requested aspects: error response schema, error codes, disconnect recovery rules, and logging/diagnostics expectations. The document is based on the existing patterns found in the Maestro codebase while providing a more structured and comprehensive approach to error handling and recovery.
ceived_message_type",
    "problematic_field": "field_name",
    "received_value": "received_value",
    "expected_format": "expected_format"
  }
}
```

#### 1.4.3 Tool Execution Errors
```json
{
  "details": {
    "tool_name": "tool_name",
    "exit_code": 1,
    "stderr_output": "command error output",
    "execution_time_ms": 5000,
    "command": ["command", "with", "args"]
  }
}
```

## 2. Error Codes Taxonomy

### 2.1 Connection Errors
- `CONNECTION_LOST`: Connection interrupted during communication
- `CONNECTION_TIMEOUT`: Connection attempt timed out
- `CONNECTION_REFUSED`: Connection refused by remote host
- `STDIO_BROKEN_PIPE`: STDIO pipe broken during communication
- `STDIO_STREAM_CLOSED`: STDIO streams closed by sender/receiver
- `NAMED_PIPE_DISCONNECTED`: Named pipe disconnected during communication
- `NAMED_PIPE_CREATION_FAILED`: Unable to create or access named pipe

### 2.2 Protocol Errors
- `INVALID_JSON_FORMAT`: Invalid JSON in received message
- `MISSING_REQUIRED_FIELD`: Required field missing from message
- `UNKNOWN_MESSAGE_TYPE`: Unrecognized message type received
- `INVALID_NDJSON_FORMAT`: Message not properly formatted as newline-delimited JSON
- `SESSION_COLLISION`: Attempt to create session with already-used ID
- `SESSION_TIMEOUT`: Session inactive beyond timeout period
- `CAPACITY_EXHAUSTED`: Buffer capacity exceeded during high message volume
- `FLOW_CONTROL_TIMEOUT`: Failure to receive flow control update within timeout

### 2.3 Tool Execution Errors
- `TOOL_EXECUTION_FAILED`: Tool execution resulted in runtime error
- `TOOL_TIMEOUT`: Tool execution exceeded configured timeout
- `PERMISSION_DENIED`: Tool execution denied by permission policy
- `RESOURCE_EXHAUSTED`: Insufficient resources to complete tool execution
- `INVALID_TOOL_ARGUMENTS`: Tool arguments do not match expected schema
- `UNSUPPORTED_TOOL`: Requested tool is not available in the system

### 2.4 Input Injection Errors
- `INVALID_INPUT_FORMAT`: Injected input does not conform to expected format
- `INPUT_INJECTION_RESTRICTED`: Attempt to inject input during restricted session state
- `INPUT_PROCESSING_TIMEOUT`: Input injection takes too long to process
- `INPUT_BUFFER_OVERFLOW`: Input injection causes buffer to exceed capacity
- `INTERRUPT_PROCESSING_FAILED`: Failed to process interrupt signal properly
- `INTERRUPT_ACK_TIMEOUT`: Interrupt signal not acknowledged within timeout

### 2.5 System Errors
- `CONFIGURATION_ERROR`: Invalid system configuration
- `RESOURCE_NOT_FOUND`: Requested resource does not exist
- `ACCESS_DENIED`: Insufficient permissions for requested operation
- `INTERNAL_ERROR`: Unhandled internal system error

## 3. Disconnect Recovery Rules

### 3.1 Detection of Disconnects

The system detects disconnects through multiple mechanisms:
- **Transport level**: TCP connection reset, broken pipes, stream closures
- **Protocol level**: Missing heartbeat messages, invalid message formats
- **Application level**: Explicit session termination signals from remote party

### 3.2 Automatic Recovery Strategies

#### 3.2.1 Connection Recovery
- **Strategy**: Implement exponential backoff for reconnection attempts
- **Applies To**: `CONNECTION_LOST`, `CONNECTION_TIMEOUT`, `STDIO_BROKEN_PIPE`
- **Parameters**:
  - Initial delay: 1 second
  - Maximum delay: 60 seconds
  - Maximum attempts: 10 (configurable)
- **Process**: Close current connection, wait calculated delay, attempt reconnection

#### 3.2.2 Message Replay
- **Strategy**: Replay unacknowledged messages after successful reconnection
- **Applies To**: Messages with `ack_required: true` after connection recovery
- **Process**: Maintain queue of unacked messages, replay in order after reconnection
- **Timeout**: Acknowledgments must arrive within 30 seconds (configurable) or message is replayed

#### 3.2.3 Session State Recovery
- **Strategy**: Resume from last known good state after reconnection
- **Applies To**: Sessions with persistent state that can be serialized
- **Process**: 
  1. Request last known state from remote party after reconnection
  2. Compare with local state snapshot
  3. Determine appropriate recovery point based on state consistency
  4. Resynchronize any missing state changes

### 3.3 Manual Recovery Strategies

#### 3.3.1 Session Restart
- **Trigger**: Critical failures with `retriable: false`
- **Process**: Terminate current session, create new session with fresh state
- **Applies To**: `SESSION_COLLISION`, `STDIO_STREAM_CLOSED`, `PERMISSION_DENIED`

#### 3.3.2 Partial Rollback
- **Trigger**: Non-critical failures affecting part of session
- **Process**: Undo operations since last known good state
- **Applies To**: Tool execution failures during multi-step operations

#### 3.3.3 Build Session Recovery
- **Trigger**: Build failures that should continue with other packages
- **Process**: 
  1. Mark failed package in build session state
  2. Continue with remaining packages if `continue_on_error` is true
  3. Allow resumption from specific packages via `--resume-from` flag
- **State Persistence**: Build session state is saved to disk periodically with `save_session_state()`

### 3.4 Recovery State Management

#### 3.4.1 Recovery Context
Each recovery attempt maintains context information:
```json
{
  "recovery_id": "unique_recovery_attempt_id",
  "original_error": {
    "error_code": "ERROR_CODE",
    "timestamp": "timestamp_of_original_error"
  },
  "recovery_attempt_count": 3,
  "recovery_strategy": "connection_recovery",
  "recovery_start_time": "timestamp_recovery_started",
  "recovery_result": "success|failure|timeout"
}
```

#### 3.4.2 Recovery Timeout
- Default recovery timeout: 300 seconds (configurable)
- Recovery attempts that exceed timeout are marked as failed
- Subsequent attempts follow exponential backoff rules

## 4. Logging and Diagnostics Expectations

### 4.1 Logging Levels and Categories

#### 4.1.1 Log Levels
- **DEBUG**: Detailed system information for diagnostic purposes
- **INFO**: General system events and operations
- **WARNING**: Unexpected but non-critical situations
- **ERROR**: Errors that prevent specific operations from completing
- **CRITICAL**: Serious errors that may require immediate attention

#### 4.1.2 Log Categories
- **protocol**: Message framing, parsing, validation
- **transport**: Connection management, data transmission
- **session**: Session lifecycle, state changes
- **tool**: Tool execution, results, errors
- **recovery**: Connection recovery, retry attempts, state restoration
- **build**: Build operations, package management, error handling

### 4.2 Required Diagnostic Information

#### 4.2.1 Error Events
When logging errors, the following information must be captured:
- Error timestamp (with millisecond precision)
- Session ID and correlation ID
- Component that generated the error
- Error code and message
- Stack trace (for internal errors)
- Relevant context (e.g., connection details, tool arguments)

#### 4.2.2 Recovery Events
When logging recovery attempts, the following information must be captured:
- Recovery attempt start/end time
- Type of recovery strategy employed
- Number of retry attempts
- Success/failure status
- Time taken for recovery
- Any state differences detected

### 4.3 Diagnostic Data Structures

#### 4.3.1 Diagnostic Event Format
```json
{
  "event_type": "error|recovery_attempt|connection_event|tool_event",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "component": "component_name",
  "severity": "debug|info|warning|error|critical",
  "code": "DIAGNOSTIC_CODE",
  "message": "Human-readable description",
  "data": {
    /* Context-specific diagnostic data */
  },
  "tags": ["tag1", "tag2"]
}
```

#### 4.3.2 Build System Diagnostics
For build operations, diagnostics follow the structured format:
```json
{
  "event_type": "build_diagnostic",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "build-session-12345",
  "component": "build_system",
  "severity": "error|warning",
  "raw": "Raw diagnostic message from build tool",
  "signature": "Stable diagnostic signature for grouping",
  "file": "file_path",
  "line": 123,
  "col": 45,
  "level": "error|warning|note",
  "tool": "build_tool_name",
  "tags": ["category1", "category2"]
}
```

### 4.4 Diagnostic Collection and Storage

#### 4.4.1 Log Storage Location
- Main logs: `.maestro/logs/` directory
- Session-specific logs: `.maestro/sessions/{session_id}/logs/`
- Build diagnostics: `.maestro/builds/{build_id}/diagnostics.json`

#### 4.4.2 Log Rotation Policy
- Rotate logs when they reach 10MB
- Keep last 10 log files
- Compress rotated logs after 24 hours
- Automatically clean logs older than 30 days

### 4.5 Diagnostic APIs

#### 4.5.1 Diagnostic Retrieval
Components must expose diagnostic information via standard API endpoints:
- `get_diagnostics(session_id, target_id=None, include_samples=True)` - retrieve diagnostics for session
- `list_diagnostics_sources()` - list available diagnostic sources
- `save_diagnostics_for_fix_run(diagnostics, fix_run_id, session_path, phase)` - save diagnostics for fix runs

## 5. Implementation Guidelines

### 5.1 Error Handling Best Practices

1. **Consistent Error Codes**: Use standardized error codes across all components
2. **Context Preservation**: Include relevant context in error details
3. **Appropriate Severity**: Assign correct severity level based on impact
4. **Traceability**: Link related errors using correlation IDs
5. **Resource Cleanup**: Ensure proper resource cleanup even when errors occur

### 5.2 Recovery Implementation Considerations

1. **State Consistency**: Verify state consistency after recovery
2. **Idempotent Operations**: Design operations to be safe for repeated execution
3. **Progress Tracking**: Track recovery progress to prevent infinite loops
4. **Configurable Parameters**: Make retry counts and timeouts configurable
5. **Monitoring**: Monitor recovery success rates and time to recovery

### 5.3 Testing Requirements

Each error handling and recovery mechanism must have:
- Unit tests for error generation and response
- Integration tests for recovery scenarios
- Load tests to verify error handling under stress
- Chaos engineering tests to validate resilience
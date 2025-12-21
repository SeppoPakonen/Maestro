I'll create detailed documentation identifying expected failure modes and error payloads based on the AI CLI Live Tool Protocol specification, test plan, and success criteria provided. This will cover all the requirements mentioned.

# AI CLI Live Tool Protocol - Failure Modes and Error Payload Documentation

## Overview

This document provides comprehensive coverage of failure modes, error payloads, and recovery strategies for the AI CLI Live Tool Protocol. It addresses protocol-level, transport-level, tool execution, and input injection failure scenarios as outlined in the specification and test plans.

## 1. Protocol-Level Failure Modes

### 1.1 Message Format Failures

#### 1.1.1 Invalid JSON Format
- **Description**: Messages that do not conform to valid JSON format
- **Trigger Condition**: Malformed JSON objects received
- **Detection Method**: JSON parsing failure during message processing
- **Error Code**: `INVALID_JSON_FORMAT`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "INVALID_JSON_FORMAT",
    "message": "Invalid JSON format in received message",
    "details": {
      "raw_message": "malformed json string",
      "parse_error": "Unexpected token at position X"
    },
    "severity": "error",
    "retriable": true
  }
}
```

#### 1.1.2 Missing Required Fields
- **Description**: Messages missing required protocol fields
- **Trigger Condition**: Required fields (`type`, `timestamp`, `session_id`, `data`) absent
- **Detection Method**: Field validation during message processing
- **Error Code**: `MISSING_REQUIRED_FIELD`
- **Severity**: `error`
- **Retriable**: `false`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "MISSING_REQUIRED_FIELD",
    "message": "Required field missing in message",
    "details": {
      "missing_field": "field_name",
      "received_fields": ["type", "timestamp"],
      "expected_fields": ["type", "timestamp", "session_id", "data"]
    },
    "severity": "error",
    "retriable": false
  }
}
```

#### 1.1.3 Invalid Message Type
- **Description**: Unknown or unsupported message type received
- **Trigger Condition**: `type` field contains unrecognized message type
- **Detection Method**: Message type validation
- **Error Code**: `UNKNOWN_MESSAGE_TYPE`
- **Severity**: `error`
- **Retriable**: `false`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "UNKNOWN_MESSAGE_TYPE",
    "message": "Unrecognized message type received",
    "details": {
      "received_type": "invalid_type",
      "supported_types": ["tool_call_request", "tool_call_response", "user_input", "error", "session_start", "session_end"]
    },
    "severity": "error",
    "retriable": false
  }
}
```

#### 1.1.4 NDJSON Format Violations
- **Description**: Message not properly formatted as newline-delimited JSON
- **Trigger Condition**: Message lacks terminating newline or multiple messages in single line
- **Detection Method**: Line-by-line processing validation
- **Error Code**: `INVALID_NDJSON_FORMAT`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "INVALID_NDJSON_FORMAT",
    "message": "Message not properly formatted as newline-delimited JSON",
    "details": {
      "problematic_line": "the problematic line content",
      "issue": "missing newline at end of message"
    },
    "severity": "error",
    "retriable": true
  }
}
```

### 1.2 Session Management Failures

#### 1.2.1 Session Collision
- **Description**: Attempt to create a session with an already-used session ID
- **Trigger Condition**: Duplicate session ID detected
- **Detection Method**: Session ID uniqueness validation
- **Error Code**: `SESSION_COLLISION`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "SESSION_COLLISION",
    "message": "Session ID already in use",
    "details": {
      "conflicting_session_id": "session-12345",
      "existing_session_info": {
        "created_at": "2025-01-10T11:30:00.000Z",
        "status": "active"
      }
    },
    "severity": "error",
    "retriable": true
  }
}
```

#### 1.2.2 Session Timeout
- **Description**: Session becomes inactive beyond configured timeout period
- **Trigger Condition**: No activity within timeout window
- **Detection Method**: Session activity monitoring
- **Error Code**: `SESSION_TIMEOUT`
- **Severity**: `warning`
- **Retriable**: `false`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "SESSION_TIMEOUT",
    "message": "Session timed out due to inactivity",
    "details": {
      "timeout_duration_seconds": 1800,
      "last_activity_timestamp": "2025-01-10T11:30:00.000Z"
    },
    "severity": "warning",
    "retriable": false
  }
}
```

### 1.3 Flow Control Failures

#### 1.3.1 Capacity Exhaustion
- **Description**: Buffer capacity exceeded during high message volume
- **Trigger Condition**: Buffer reaches maximum capacity
- **Detection Method**: Buffer capacity monitoring
- **Error Code**: `CAPACITY_EXHAUSTED`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "CAPACITY_EXHAUSTED",
    "message": "Message buffer capacity exhausted",
    "details": {
      "current_capacity": 0,
      "max_capacity": 10,
      "pending_messages": 15,
      "backpressure_duration_ms": 2000
    },
    "severity": "error",
    "retriable": true
  }
}
```

#### 1.3.2 Flow Control Timeout
- **Description**: Failure to receive flow control update within timeout
- **Trigger Condition**: No flow control message received within timeout
- **Detection Method**: Flow control monitoring
- **Error Code**: `FLOW_CONTROL_TIMEOUT`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "FLOW_CONTROL_TIMEOUT",
    "message": "Flow control update timeout",
    "details": {
      "timeout_threshold_ms": 5000,
      "last_flow_control_update": "2025-01-10T11:59:00.000Z"
    },
    "severity": "error",
    "retriable": true
  }
}
```

## 2. Transport-Level Failure Modes

### 2.1 STDIO Transport Failures

#### 2.1.1 Broken Pipe Error
- **Description**: STDIO pipe closed unexpectedly during transmission
- **Trigger Condition**: Write to closed pipe or read from closed pipe
- **Detection Method**: System error when accessing STDIO
- **Error Code**: `STDIO_BROKEN_PIPE`
- **Severity**: `fatal`
- **Retriable**: `false`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "STDIO_BROKEN_PIPE",
    "message": "STDIO pipe broken during communication",
    "details": {
      "direction": "stdout", // or "stdin"
      "bytes_processed": 1024,
      "operation": "write"
    },
    "severity": "fatal",
    "retriable": false
  }
}
```

#### 2.1.2 STDIO Stream Closure
- **Description**: STDIO streams closed by sender/receiver
- **Trigger Condition**: EOF reached on input stream
- **Detection Method**: Read returns EOF
- **Error Code**: `STDIO_STREAM_CLOSED`
- **Severity**: `fatal`
- **Retriable**: `false`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "STDIO_STREAM_CLOSED",
    "message": "STDIO stream closed unexpectedly",
    "details": {
      "stream_type": "stdin",
      "position": 2048,
      "last_message_processed": "message_id_123"
    },
    "severity": "fatal",
    "retriable": false
  }
}
```

### 2.2 TCP Transport Failures

#### 2.2.1 Connection Lost
- **Description**: TCP connection interrupted during communication
- **Trigger Condition**: Connection reset, timeout, or network interruption
- **Detection Method**: Socket error detection
- **Error Code**: `CONNECTION_LOST`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "CONNECTION_LOST",
    "message": "TCP connection lost during communication",
    "details": {
      "remote_address": "127.0.0.1:8080",
      "last_activity_timestamp": "2025-01-10T11:59:59.000Z",
      "connection_duration_ms": 60000
    },
    "severity": "error",
    "retriable": true
  }
}
```

#### 2.2.2 Connection Timeout
- **Description**: Unable to establish TCP connection within timeout period
- **Trigger Condition**: Connection attempt exceeds timeout
- **Detection Method**: Connection timeout
- **Error Code**: `CONNECTION_TIMEOUT`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "CONNECTION_TIMEOUT",
    "message": "TCP connection attempt timed out",
    "details": {
      "target_address": "127.0.0.1:8080",
      "timeout_duration_ms": 5000,
      "retry_count": 3
    },
    "severity": "error",
    "retriable": true
  }
}
```

#### 2.2.3 Connection Refused
- **Description**: TCP connection refused by remote host
- **Trigger Condition**: Remote host actively refuses connection
- **Detection Method**: Connection refused error
- **Error Code**: `CONNECTION_REFUSED`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "CONNECTION_REFUSED",
    "message": "TCP connection refused by remote host",
    "details": {
      "target_address": "127.0.0.1:8080",
      "retry_count": 0
    },
    "severity": "error",
    "retriable": true
  }
}
```

### 2.3 Named Pipes Transport Failures

#### 2.3.1 Pipe Disconnection
- **Description**: Named pipe disconnected during communication
- **Trigger Condition**: Remote end closes the pipe
- **Detection Method**: Pipe read/write error
- **Error Code**: `NAMED_PIPE_DISCONNECTED`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "NAMED_PIPE_DISCONNECTED",
    "message": "Named pipe disconnected during communication",
    "details": {
      "pipe_path": "/tmp/maestro_pipe",
      "last_operation": "read",
      "last_successful_message": "msg_12345"
    },
    "severity": "error",
    "retriable": true
  }
}
```

#### 2.3.2 Pipe Creation Failure
- **Description**: Unable to create or access named pipe
- **Trigger Condition**: Permission denied or system resource issue
- **Detection Method**: Pipe creation/open failure
- **Error Code**: `NAMED_PIPE_CREATION_FAILED`
- **Severity**: `fatal`
- **Retriable**: `false`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "NAMED_PIPE_CREATION_FAILED",
    "message": "Failed to create or access named pipe",
    "details": {
      "pipe_path": "/tmp/maestro_pipe",
      "error_code": "EACCES",
      "error_message": "Permission denied"
    },
    "severity": "fatal",
    "retriable": false
  }
}
```

## 3. Tool Execution Failure Modes

### 3.1 Tool Execution Failures

#### 3.1.1 Tool Execution Failed
- **Description**: Tool execution resulted in runtime error
- **Trigger Condition**: Tool process exits with non-zero status
- **Detection Method**: Process exit code or exception handling
- **Error Code**: `TOOL_EXECUTION_FAILED`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure (as tool_call_response):**
```json
{
  "type": "tool_call_response",
  "timestamp": "2025-01-10T12:00:00.100Z",
  "session_id": "session-12345",
  "correlation_id": "call-67890",
  "data": {
    "call_id": "read_file-12345",
    "result": null,
    "error": {
      "error_code": "TOOL_EXECUTION_FAILED",
      "message": "Command failed with exit code 1",
      "details": {
        "exit_code": 1,
        "stderr_output": "File not found: /path/to/file.txt",
        "execution_time_ms": 50,
        "command": ["read_file", "/path/to/file.txt"]
      }
    },
    "execution_time_ms": 50
  }
}
```

#### 3.1.2 Tool Timeout
- **Description**: Tool execution exceeded configured timeout
- **Trigger Condition**: Tool execution time exceeds timeout limit
- **Detection Method**: Timeout timer expiration
- **Error Code**: `TOOL_TIMEOUT`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure (as tool_call_response):**
```json
{
  "type": "tool_call_response",
  "timestamp": "2025-01-10T12:00:00.100Z",
  "session_id": "session-12345",
  "correlation_id": "call-67890",
  "data": {
    "call_id": "long_running_tool-12345",
    "result": null,
    "error": {
      "error_code": "TOOL_TIMEOUT",
      "message": "Tool execution exceeded timeout",
      "details": {
        "configured_timeout_ms": 30000,
        "actual_execution_time_ms": 35000,
        "command": ["long_running_tool", "--param", "value"]
      }
    },
    "execution_time_ms": 35000
  }
}
```

#### 3.1.3 Permission Denied
- **Description**: Tool execution denied by permission policy
- **Trigger Condition**: Tool access restricted by security controls
- **Detection Method**: Permission check failure
- **Error Code**: `PERMISSION_DENIED`
- **Severity**: `error`
- **Retriable**: `false`

**Error Payload Structure (as tool_call_response):**
```json
{
  "type": "tool_call_response",
  "timestamp": "2025-01-10T12:00:00.100Z",
  "session_id": "session-12345",
  "correlation_id": "call-67890",
  "data": {
    "call_id": "delete_file-12345",
    "result": null,
    "error": {
      "error_code": "PERMISSION_DENIED",
      "message": "Access to tool is denied by policy",
      "details": {
        "tool_name": "delete_file",
        "requested_path": "/protected/system/file.txt",
        "policy_violation": "Deletion of system files prohibited"
      }
    },
    "execution_time_ms": 10
  }
}
```

#### 3.1.4 Resource Exhausted
- **Description**: Insufficient resources to complete tool execution
- **Trigger Condition**: Memory, disk, or CPU limits exceeded
- **Detection Method**: Resource allocation failure
- **Error Code**: `RESOURCE_EXHAUSTED`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure (as tool_call_response):**
```json
{
  "type": "tool_call_response",
  "timestamp": "2025-01-10T12:00:00.100Z",
  "session_id": "session-12345",
  "correlation_id": "call-67890",
  "data": {
    "call_id": "process_large_file-12345",
    "result": null,
    "error": {
      "error_code": "RESOURCE_EXHAUSTED",
      "message": "Insufficient memory to complete operation",
      "details": {
        "resource_type": "memory",
        "available_bytes": 104857600,
        "required_bytes": 524288000,
        "command": ["process_large_file", "/large/input.json"]
      }
    },
    "execution_time_ms": 2000
  }
}
```

### 3.2 Tool Call Validation Failures

#### 3.2.1 Invalid Tool Arguments
- **Description**: Tool arguments do not match expected schema
- **Trigger Condition**: Arguments fail validation against tool schema
- **Detection Method**: Schema validation failure
- **Error Code**: `INVALID_TOOL_ARGUMENTS`
- **Severity**: `error`
- **Retriable**: `false`

**Error Payload Structure (as tool_call_response):**
```json
{
  "type": "tool_call_response",
  "timestamp": "2025-01-10T12:00:00.100Z",
  "session_id": "session-12345",
  "correlation_id": "call-67890",
  "data": {
    "call_id": "read_file-12345",
    "result": null,
    "error": {
      "error_code": "INVALID_TOOL_ARGUMENTS",
      "message": "Invalid arguments provided to tool",
      "details": {
        "tool_name": "read_file",
        "validation_errors": [
          {
            "field": "file_path",
            "issue": "Value is not a valid file path",
            "received_value": "../../etc/passwd"
          }
        ],
        "received_arguments": {
          "file_path": "../../etc/passwd"
        }
      }
    },
    "execution_time_ms": 5
  }
}
```

#### 3.2.2 Unsupported Tool
- **Description**: Requested tool is not available in the system
- **Trigger Condition**: Tool name not found in registered tools
- **Detection Method**: Tool lookup failure
- **Error Code**: `UNSUPPORTED_TOOL`
- **Severity**: `error`
- **Retriable**: `false`

**Error Payload Structure (as tool_call_response):**
```json
{
  "type": "tool_call_response",
  "timestamp": "2025-01-10T12:00:00.100Z",
  "session_id": "session-12345",
  "correlation_id": "call-67890",
  "data": {
    "call_id": "unknown_tool_call-12345",
    "result": null,
    "error": {
      "error_code": "UNSUPPORTED_TOOL",
      "message": "Requested tool is not supported",
      "details": {
        "requested_tool": "nonexistent_tool",
        "available_tools": [
          "read_file", "write_file", "execute_command", "list_directory"
        ]
      }
    },
    "execution_time_ms": 2
  }
}
```

## 4. Input Injection Failure Modes

### 4.1 Input Validation Failures

#### 4.1.1 Invalid Input Format
- **Description**: Injected input does not conform to expected format
- **Trigger Condition**: Input fails validation against expected format
- **Detection Method**: Input validation failure
- **Error Code**: `INVALID_INPUT_FORMAT`
- **Severity**: `error`
- **Retriable**: `false`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "INVALID_INPUT_FORMAT",
    "message": "Injected input does not match expected format",
    "details": {
      "received_input_length": 2048,
      "validation_rule": "Maximum 1000 characters allowed",
      "input_preview": "very long input string that exceeds limits..."
    },
    "severity": "error",
    "retriable": false
  }
}
```

#### 4.1.2 Input Injection During Restricted State
- **Description**: Attempt to inject input during restricted session state
- **Trigger Condition**: Input injected when system is in non-receptive state
- **Detection Method**: State validation before processing input
- **Error Code**: `INPUT_INJECTION_RESTRICTED`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "INPUT_INJECTION_RESTRICTED",
    "message": "Input injection is restricted in current session state",
    "details": {
      "current_state": "terminating",
      "allowed_states": ["active", "paused"],
      "attempted_input_type": "user_input",
      "session_phase": "shutdown_sequence"
    },
    "severity": "error",
    "retriable": true
  }
}
```

### 4.2 Input Processing Failures

#### 4.2.1 Input Processing Timeout
- **Description**: Input injection takes too long to process
- **Trigger Condition**: Input processing exceeds timeout threshold
- **Detection Method**: Processing timer expiration
- **Error Code**: `INPUT_PROCESSING_TIMEOUT`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "INPUT_PROCESSING_TIMEOUT",
    "message": "Input processing timed out",
    "details": {
      "timeout_duration_ms": 1000,
      "input_size_bytes": 10240,
      "processing_stage": "content_validation",
      "partial_processing_completed": false
    },
    "severity": "error",
    "retriable": true
  }
}
```

#### 4.2.2 Input Buffer Overflow
- **Description**: Input injection causes buffer to exceed capacity
- **Trigger Condition**: Input size exceeds buffer capacity
- **Detection Method**: Buffer size monitoring during input processing
- **Error Code**: `INPUT_BUFFER_OVERFLOW`
- **Severity**: `error`
- **Retriable**: `false`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "INPUT_BUFFER_OVERFLOW",
    "message": "Input exceeds buffer capacity",
    "details": {
      "input_size_bytes": 2097152,
      "max_buffer_size_bytes": 1048576,
      "buffer_utilization_percent": 200,
      "overflow_amount_bytes": 1048576
    },
    "severity": "error",
    "retriable": false
  }
}
```

### 4.3 Interrupt Handling Failures

#### 4.3.1 Interrupt Processing Failed
- **Description**: Failed to process interrupt signal properly
- **Trigger Condition**: Error during interrupt handling process
- **Detection Method**: Exception during interrupt handler execution
- **Error Code**: `INTERRUPT_PROCESSING_FAILED`
- **Severity**: `error`
- **Retriable**: `false`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "INTERRUPT_PROCESSING_FAILED",
    "message": "Failed to process interrupt signal",
    "details": {
      "interrupt_signal": "SIGINT",
      "interruption_target": "running_tool_process",
      "failure_reason": "Process lock prevented signal delivery",
      "recovery_attempted": true,
      "recovery_success": false
    },
    "severity": "error",
    "retriable": false
  }
}
```

#### 4.3.2 Interrupt Acknowledgment Timeout
- **Description**: Interrupt signal not acknowledged within timeout
- **Trigger Condition**: No acknowledgment received within timeout period
- **Detection Method**: Timer expiration waiting for interrupt acknowledgment
- **Error Code**: `INTERRUPT_ACK_TIMEOUT`
- **Severity**: `error`
- **Retriable**: `true`

**Error Payload Structure:**
```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "INTERRUPT_ACK_TIMEOUT",
    "message": "Interrupt acknowledgment timeout",
    "details": {
      "interrupt_id": "int-12345",
      "timeout_duration_ms": 5000,
      "awaited_acknowledgment": "graceful_shutdown_started",
      "action_taken": "forceful_termination_initiated"
    },
    "severity": "error",
    "retriable": true
  }
}
```

## 5. Error Payload Structures Summary

### 5.1 Standard Error Payload Format
All error messages conform to the following structure:

```json
{
  "type": "error",
  "timestamp": "ISO 8601 timestamp",
  "session_id": "session identifier",
  "correlation_id": "optional correlation identifier",
  "data": {
    "error_code": "ERROR_CODE_CONSTANT",
    "message": "Human-readable error description",
    "details": { /* error-specific details */ },
    "severity": "fatal|error|warning",
    "retriable": true|false
  }
}
```

### 5.2 Tool-Specific Error Payload
Tool execution errors use the `tool_call_response` message type:

```json
{
  "type": "tool_call_response",
  "timestamp": "ISO 8601 timestamp",
  "session_id": "session identifier",
  "correlation_id": "correlation identifier",
  "data": {
    "call_id": "tool call identifier",
    "result": null,  // Always null for errors
    "error": {       // Error object following standard format
      "error_code": "ERROR_CODE_CONSTANT",
      "message": "Human-readable error description",
      "details": { /* error-specific details */ },
      "severity": "fatal|error|warning",
      "retriable": true|false
    },
    "execution_time_ms": execution_time_in_milliseconds
  }
}
```

## 6. Recovery Strategies

### 6.1 Automatic Recovery Strategies

#### 6.1.1 Connection Recovery
- **Strategy**: Implement exponential backoff for reconnection attempts
- **Applies To**: `CONNECTION_LOST`, `CONNECTION_TIMEOUT`, `STDIO_BROKEN_PIPE`
- **Parameters**: 
  - Initial delay: 1 second
  - Maximum delay: 60 seconds
  - Maximum attempts: 10
- **Process**: Close current connection, wait calculated delay, attempt reconnection

#### 6.1.2 Message Replay
- **Strategy**: Replay unacknowledged messages after successful reconnection
- **Applies To**: Messages with `ack_required: true` after connection recovery
- **Process**: Maintain queue of unacked messages, replay in order after reconnection

#### 6.1.3 Tool Retry with Exponential Backoff
- **Strategy**: Retry failed tool executions with increasing delays
- **Applies To**: Tool execution failures where `retriable: true`
- **Parameters**:
  - Initial delay: 100ms
  - Maximum delay: 5 seconds
  - Maximum attempts: 3
- **Process**: Wait calculated delay, then re-execute tool with same parameters

### 6.2 Manual Recovery Strategies

#### 6.2.1 Session Restart
- **Trigger**: Critical failures with `retriable: false`
- **Process**: Terminate current session, create new session with fresh state
- **Applies To**: `SESSION_COLLISION`, `STDIO_STREAM_CLOSED`, `PERMISSION_DENIED`

#### 6.2.2 Partial Rollback
- **Trigger**: Non-critical failures affecting part of session
- **Process**: Undo operations since last known good state
- **Applies To**: Tool execution failures during multi-step operations

### 6.3 Error Prevention Strategies

#### 6.3.1 Input Validation
- **Prevents**: Invalid input causing downstream issues
- **Implementation**: Validate all input before processing
- **Scope**: All user inputs and system-generated inputs

#### 6.3.2 Resource Monitoring
- **Prevents**: `RESOURCE_EXHAUSTED` errors
- **Implementation**: Monitor resource usage before tool execution
- **Scope**: Memory, disk space, and processing power

#### 6.3.3 Timeout Management
- **Prevents**: Hanging operations
- **Implementation**: Set appropriate timeouts for all operations
- **Scope**: Tool execution, input processing, connection attempts

This comprehensive documentation provides detailed failure mode analysis, error payload definitions, and recovery strategies for the AI CLI Live Tool Protocol implementation. It covers all aspects of the protocol including message framing, transport mechanisms, tool execution, and input injection as specified in the original requirements.

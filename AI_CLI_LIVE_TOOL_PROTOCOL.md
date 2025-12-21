# AI CLI Live Tool Protocol Specification

## Overview

The AI CLI Live Tool Protocol defines a standardized communication interface between AI agents and CLI tools that enables real-time tool usage events, live output streaming, and bidirectional communication. This protocol is designed to support the Maestro orchestration system's needs for monitoring and controlling AI agent interactions.

## 1. Message Framing

### 1.1 Framing Mechanism

The protocol uses **newline-delimited JSON (NDJSON)** as the primary framing mechanism. Each message is a complete, self-contained JSON object terminated by a newline character (`\n`).

```
{ "type": "message_type", "field": "value" }\n
{ "type": "another_message", "data": "more_values" }\n
```

### 1.2 Message Structure

All messages follow this basic structure:

```json
{
  "type": "message_type",
  "timestamp": "ISO 8601 timestamp",
  "session_id": "unique session identifier",
  "correlation_id": "optional correlation identifier for request/response matching",
  "data": { /* message-specific payload */ }
}
```

### 1.3 Message Types

#### 1.3.1 Tool Events
- `tool_call_request`: Emitted when a tool call is initiated
- `tool_call_confirmation`: Emitted when a tool requires confirmation
- `tool_call_response`: Emitted when a tool call completes
- `tool_execution_status`: Periodic status updates during tool execution

#### 1.3.2 Stream Events
- `message_start`: Indicates start of an assistant message
- `content_block_start`: Indicates start of a content block
- `content_block_delta`: Streaming update to a content block
- `content_block_stop`: Indicates end of a content block
- `message_stop`: Indicates end of an assistant message

#### 1.3.3 Control Events
- `user_input`: User input sent to the agent
- `interrupt`: Interrupt signal to stop current processing
- `status_update`: System status updates
- `error`: Error notifications

#### 1.3.4 Session Events
- `session_start`: Session initialization
- `session_end`: Session termination
- `session_state`: Current session state snapshot

### 1.4 Message Format Examples

**Tool Call Request:**
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

**Tool Call Response:**
```json
{
  "type": "tool_call_response",
  "timestamp": "2025-01-10T12:00:00.100Z",
  "session_id": "session-12345",
  "correlation_id": "call-67890",
  "data": {
    "call_id": "read_file-12345",
    "result": "File content here...",
    "error": null,
    "execution_time_ms": 100
  }
}
```

## 2. Backpressure Handling

### 2.1 Flow Control Mechanism

The protocol implements a credit-based flow control system where the receiver advertises its capacity to handle messages.

#### 2.1.1 Capacity Advertisement
- Receivers periodically send `flow_control` messages indicating available buffer capacity
- Default initial capacity: 10 messages
- Capacity is replenished as messages are processed

#### 2.1.2 Flow Control Message
```json
{
  "type": "flow_control",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "data": {
    "available_capacity": 7,
    "requested_capacity": 10
  }
}
```

### 2.2 Backpressure Response

When the sender detects low capacity or receives explicit backpressure signals:

1. **Throttle sending rate**: Reduce message emission frequency
2. **Buffer messages**: Queue outgoing messages in sender's internal buffer
3. **Apply priority**: Higher priority messages (errors, interrupts) bypass flow control
4. **Timeout handling**: If capacity doesn't improve within timeout period, send `backpressure_alert`

### 2.3 Priority Levels

Messages are categorized by priority:
- **P0 (Critical)**: Error messages, interrupt signals, session termination
- **P1 (High)**: Tool confirmation requests, user input responses
- **P2 (Normal)**: Tool call responses, status updates
- **P3 (Low)**: Content streaming, logging messages

## 3. Error Handling and Recovery

### 3.1 Error Message Format

```json
{
  "type": "error",
  "timestamp": "2025-01-10T12:00:00.000Z",
  "session_id": "session-12345",
  "correlation_id": "optional_correlation_id",
  "data": {
    "error_code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": { /* optional error-specific details */ },
    "severity": "fatal|error|warning",
    "retriable": true|false
  }
}
```

### 3.2 Error Categories

#### 3.2.1 Connection Errors
- `CONNECTION_LOST`: Connection to agent was interrupted
- `CONNECTION_TIMEOUT`: Connection attempt timed out
- `CONNECTION_REFUSED`: Connection refused by agent

#### 3.2.2 Protocol Errors
- `INVALID_MESSAGE_FORMAT`: Message doesn't conform to protocol
- `MISSING_REQUIRED_FIELD`: Required field missing from message
- `UNKNOWN_MESSAGE_TYPE`: Unrecognized message type received

#### 3.2.3 Application Errors
- `TOOL_EXECUTION_FAILED`: Tool execution resulted in error
- `PERMISSION_DENIED`: Tool execution denied by policy
- `RESOURCE_EXHAUSTED`: Insufficient resources to complete operation

### 3.3 Recovery Strategies

#### 3.3.1 Automatic Recovery
- **Reconnection**: Attempt to reestablish connection with exponential backoff
- **Message replay**: Replay unacknowledged messages after reconnection
- **Session resumption**: Resume from last known good state

#### 3.3.2 Manual Recovery
- **Session restart**: Begin new session after critical failures
- **Partial rollback**: Rollback to last consistent state for non-critical failures

### 3.4 Error Acknowledgment

For reliable delivery, critical messages support acknowledgment:
- Sender includes `ack_required: true` in message
- Receiver responds with `ack` message upon successful processing
- Sender retransmits unacknowledged messages after timeout

## 4. Transport Mechanisms

### 4.1 STDIO Transport

The protocol supports communication via standard input/output streams.

#### 4.1.1 STDIO Characteristics
- Messages written to stdout by sender
- Messages read from stdin by receiver
- Unidirectional per stream, bidirectional with separate streams
- Suitable for subprocess communication

#### 4.1.2 STDIO Implementation Requirements
- Use unbuffered output to prevent message delays
- Handle stream closure gracefully
- Implement proper error handling for broken pipes

### 4.2 TCP Transport

The protocol supports TCP socket communication for network-based scenarios.

#### 4.2.1 TCP Characteristics
- Connection-oriented communication
- Supports persistent connections
- Enables remote agent communication
- Provides built-in flow control

#### 4.2.2 TCP Implementation Requirements
- Implement connection timeout handling
- Support TLS encryption for secure communication
- Handle connection interruptions gracefully
- Implement proper socket cleanup

### 4.3 Named Pipes Transport

The protocol supports named pipes for inter-process communication on the same host.

#### 4.3.1 Named Pipes Characteristics
- Filesystem-based communication channels
- Platform-specific implementation (FIFO on Unix, Named Pipes on Windows)
- Efficient for local process communication

#### 4.3.2 Named Pipes Implementation Requirements
- Proper pipe creation and cleanup
- Handle pipe disconnections
- Implement appropriate access controls

## 5. Reliability Requirements

### 5.1 Delivery Guarantees

#### 5.1.1 At-least-once Delivery
- Critical messages are acknowledged by receiver
- Unacknowledged messages are retransmitted
- May result in duplicate messages which must be handled idempotently

#### 5.1.2 Ordering Requirements
- Messages within a session maintain causal ordering
- Request-response pairs maintain sequence integrity
- Time-sensitive messages may bypass ordering requirements

### 5.2 Message Integrity

#### 5.2.1 Validation
- All messages validated against schema before processing
- Invalid messages trigger protocol error
- Malformed messages are logged and discarded

#### 5.2.2 Checksums
- Optional checksums for message integrity verification
- Implementation-dependent based on transport reliability

### 5.3 Session Management

#### 5.3.1 Session State
- Maintain session context across message exchanges
- Implement session timeout for inactive sessions
- Support session state serialization for persistence

#### 5.3.2 Heartbeat Mechanism
- Periodic heartbeat messages to verify connection health
- Configurable heartbeat interval (default: 30 seconds)
- Connection termination after missed heartbeats (default: 3)

## 6. Implementation Guidelines

### 6.1 Protocol Compliance

Implementations must:
- Adhere to message format specifications
- Implement required error handling
- Support all transport mechanisms appropriate to the environment
- Maintain message ordering within sessions

### 6.2 Performance Considerations

- Minimize message serialization overhead
- Implement efficient message buffering
- Use appropriate compression for large payloads
- Optimize for low-latency scenarios where required

### 6.3 Security Considerations

- Validate all incoming message content
- Implement rate limiting to prevent flooding
- Use encrypted transport for sensitive communications
- Sanitize message content to prevent injection attacks
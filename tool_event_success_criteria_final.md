I'll create detailed, specific, and measurable success criteria for tool event capture based on the AI CLI Live Tool Protocol specification and the test plan provided. Let me start with the first task.

# AI CLI Live Tool Event Capture Success Criteria

## 1. Message Types Validation

### 1.1 Basic Message Structure Validation
- **Requirement M1.1**: Every captured message MUST contain all required top-level fields (`type`, `timestamp`, `session_id`, `data`)
- **Requirement M1.2**: Each message's `type` field MUST match one of the protocol-defined message types exactly (case-sensitive)
- **Requirement M1.3**: The `timestamp` field MUST be formatted as ISO 8601 with millisecond precision (YYYY-MM-DDTHH:mm:ss.SSSZ)
- **Requirement M1.4**: The `session_id` field MUST be consistent across all messages within a single session
- **Requirement M1.5**: The `data` field MUST be a valid JSON object containing message-specific payload

### 1.2 Tool Event Capturing Validation
- **Requirement M1.6**: `tool_call_request` messages MUST include `call_id`, `name`, and `args` in the data payload
- **Requirement M1.7**: `tool_call_response` messages MUST include `call_id`, `result` or `error`, and `execution_time_ms` in the data payload
- **Requirement M1.8**: `tool_call_confirmation` messages MUST include `call_id`, `name`, `args`, and confirmation requirements in the data payload
- **Requirement M1.9**: `tool_execution_status` messages MUST include `call_id`, `status`, and optional progress information in the data payload

### 1.3 Stream Event Capturing Validation
- **Requirement M1.10**: `message_start` messages MUST precede all content block events in a message sequence
- **Requirement M1.11**: `content_block_start` messages MUST include a unique `content_block_id` in the data payload
- **Requirement M1.12**: `content_block_delta` messages MUST include `content_block_id` and `delta_text` in the data payload
- **Requirement M1.13**: `content_block_stop` messages MUST include the corresponding `content_block_id` in the data payload
- **Requirement M1.14**: `message_stop` messages MUST conclude a message sequence with proper session association

### 1.4 Control Event Capturing Validation
- **Requirement M1.15**: `user_input` messages MUST capture the complete input content in the data payload
- **Requirement M1.16**: `interrupt` messages MUST include the reason/context for interruption in the data payload
- **Requirement M1.17**: `error` messages MUST include `error_code`, `message`, `severity`, and `retriable` fields in the data payload
- **Requirement M1.18**: `status_update` messages MUST contain current system status information in the data payload

### 1.5 Session Event Capturing Validation
- **Requirement M1.19**: `session_start` messages MUST include session configuration and initialization parameters in the data payload
- **Requirement M1.20**: `session_end` messages MUST include session summary and termination reason in the data payload
- **Requirement M1.21**: `session_state` messages MUST contain a complete snapshot of current session state in the data payload

### 1.6 Message Formatting Validation
- **Requirement M1.22**: All captured messages MUST be properly formatted as NDJSON (newline-delimited JSON) with each message on a separate line
- **Requirement M1.23**: Each message line MUST end with exactly one newline character (`\n`)
- **Requirement M1.24**: All JSON objects MUST be syntactically valid and parseable using standard JSON parsers
- **Requirement M1.25**: Message size MUST NOT exceed implementation-defined limits (default: 1MB per message)

## 2. Content Accuracy Requirements

### 2.1 Tool Argument Preservation
- **Requirement C2.1**: Tool arguments in `tool_call_request` messages MUST exactly match the arguments passed to the tool execution function
- **Requirement C2.2**: Sensitive data in tool arguments (e.g., credentials, tokens) MUST be redacted or masked in captured events
- **Requirement C2.3**: File paths in tool arguments MUST be properly normalized and not contain relative path traversal sequences
- **Requirement C2.4**: All numeric values in tool arguments MUST maintain their original precision and type (integer vs float)

### 2.2 Tool Result Content Accuracy
- **Requirement C2.5**: Tool output in `tool_call_response` messages MUST match the actual output from the executed tool
- **Requirement C2.6**: Large tool outputs MUST be truncated at implementation-defined boundaries (default: 100KB) with appropriate indicators
- **Requirement C2.7**: Binary data or non-text results MUST be base64 encoded for transmission while maintaining data integrity
- **Requirement C2.8**: Error messages from tools MUST be preserved verbatim including stack traces if applicable

### 2.3 User Input Content Preservation
- **Requirement C2.9**: User input text in `user_input` messages MUST preserve all Unicode characters and whitespace exactly as entered
- **Requirement C2.10**: Multi-line user inputs MUST maintain line breaks and formatting in captured events
- **Requirement C2.11**: Special input characters (control characters, escape sequences) MUST be properly escaped in JSON output
- **Requirement C2.12**: Input metadata (timestamp, input source) MUST be accurately captured alongside the raw input content

### 2.4 Session State Content Accuracy
- **Requirement C2.13**: Session variables and context information MUST be captured with complete accuracy in `session_state` messages
- **Requirement C2.14**: Active tool call information in session state MUST reflect current execution status and parameters
- **Requirement C2.15**: All pending operations and queued messages MUST be accurately represented in session state snapshots
- **Requirement C2.16**: Historical interaction data captured in session state MUST be ordered chronologically and complete

### 2.5 Content Integrity Checks
- **Requirement C2.17**: All captured content MUST pass round-trip serialization validation (can be parsed and reconstructed)
- **Requirement C2.18**: Character encoding MUST be preserved consistently (UTF-8 assumed unless otherwise specified)
- **Requirement C2.19**: Content length measurements MUST match actual byte count of the original data
- **Requirement C2.20**: Checksums or hash values (when implemented) MUST verify content integrity between capture and verification points

### 2.6 Content Privacy and Security
- **Requirement C2.21**: Personal Identifiable Information (PII) MUST be removed or anonymized from captured content
- **Requirement C2.22**: Authentication tokens, passwords, and secret keys MUST be stripped from all captured events
- **Requirement C2.23**: File content containing sensitive data SHOULD be filtered by content inspection before capture
- **Requirement C2.24**: Compliance with applicable privacy regulations (GDPR, CCPA, etc.) MUST be maintained in all captured content

## 3. Timing Requirements

### 3.1 Message Timestamp Accuracy
- **Requirement T3.1**: Message timestamps MUST be recorded at the moment of event occurrence with millisecond precision
- **Requirement T3.2**: Clock synchronization between sender and receiver systems SHOULD be maintained within 100ms tolerance
- **Requirement T3.3**: Sequential events within the same session MUST have timestamps that reflect chronological order
- **Requirement T3.4**: Timestamp accuracy MUST be verified against system monotonic clock when possible to prevent backwards time jumps

### 3.2 Tool Execution Timing
- **Requirement T3.5**: `tool_call_request` messages MUST be emitted before tool execution begins (within 10ms of initiation)
- **Requirement T3.6**: `tool_call_response` messages MUST be emitted within 100ms after tool execution completes
- **Requirement T3.7**: `tool_execution_status` updates MUST be emitted at intervals not exceeding 1000ms during long-running operations (>5s)
- **Requirement T3.8**: Execution time measurements in `tool_call_response` MUST correlate with actual wall-clock execution time within 10%

### 3.3 Event Sequencing Timing
- **Requirement T3.9**: Request/response pairs MUST maintain causality (response timestamp >= request timestamp)
- **Requirement T3.10**: Session events MUST follow proper temporal sequence: `session_start` → tool events → `session_end`
- **Requirement T3.11**: Content block events within a message MUST maintain strict temporal order: `start` → `delta(s)` → `stop`
- **Requirement T3.12**: Interrupt signals MUST be processed and their effects reflected in subsequent events within 100ms

### 3.4 Flow Control Timing
- **Requirement T3.13**: `flow_control` messages MUST be emitted within 1000ms when buffer capacity falls below 20% of maximum
- **Requirement T3.14**: Senders MUST respond to flow control signals within 50ms by adjusting message emission rate
- **Requirement T3.15**: Backpressure alerts MUST be triggered within 5000ms of sustained high buffer usage
- **Requirement T3.16**: Credit replenishment announcements MUST occur within 100ms of buffer space becoming available

### 3.5 Heartbeat and Timeout Timing
- **Requirement T3.17**: Heartbeat messages MUST be emitted at configurable intervals (default: every 30±1 seconds)
- **Requirement T3.18**: Connection timeouts MUST occur after 3 consecutive missed heartbeats (default: 90±3 seconds)
- **Requirement T3.19**: Reconnection attempts MUST follow exponential backoff: 1s, 2s, 4s, 8s, max 60s intervals
- **Requirement T3.20**: Message acknowledgment timeouts MUST occur within 30 seconds for messages marked as `ack_required`

### 3.6 Session Timing Constraints
- **Requirement T3.21**: Idle sessions MUST be terminated after configurable inactivity period (default: 30 minutes)
- **Requirement T3.22**: Session initialization process MUST complete within 10 seconds of connection establishment
- **Requirement T3.23**: Session cleanup operations MUST complete within 5 seconds of session termination request
- **Requirement T3.24**: Time-sensitive operations (like user confirmations) MUST have configurable expiration times (default: 5 minutes)

## 4. Correlation Validation

### 4.1 Request-Response Pairing
- **Requirement CR4.1**: Every `tool_call_request` message MUST have a corresponding `tool_call_response` message with matching `correlation_id`
- **Requirement CR4.2**: Multiple requests MUST NOT share the same `correlation_id`; each request-response pair MUST have a unique identifier
- **Requirement CR4.3**: `tool_call_response` messages MUST reference the same `call_id` as the originating `tool_call_request`
- **Requirement CR4.4**: Unmatched requests/responses (due to timeouts or errors) MUST be flagged with appropriate error events

### 4.2 Session Association
- **Requirement CR4.5**: All events within a session MUST share the same `session_id` value throughout the session lifecycle
- **Requirement CR4.6**: Cross-session events (messages referencing multiple sessions) MUST be explicitly identified and handled appropriately
- **Requirement CR4.7**: Session boundary violations (events with mismatched session IDs) MUST trigger error detection protocols
- **Requirement CR4.8**: Concurrent session events MUST be clearly separated by unique `session_id` values

### 4.3 Content Block Correlation
- **Requirement CR4.9**: All events related to a specific content block (start, delta, stop) MUST share the same `content_block_id`
- **Requirement CR4.10**: Content block IDs MUST be unique within the scope of a single message or assistant response
- **Requirement CR4.11**: Missing or duplicated content block events MUST be detected and reported as protocol violations
- **Requirement CR4.12**: Content block sequences MUST maintain logical continuity (no gaps in delta sequences when applicable)

### 4.4 Operation Chaining
- **Requirement CR4.13**: Dependent tool calls initiated from previous results MUST maintain traceability through correlation mechanisms
- **Requirement CR4.14**: Tool call chains MUST preserve parent-child relationships using appropriate correlation identifiers
- **Requirement CR4.15**: Interrupted operation chains MUST preserve context to enable proper state recovery
- **Requirement CR4.16**: Parallel operations initiated from the same source MUST maintain distinct correlation paths

### 4.5 Error Correlation
- **Requirement CR4.17**: Error messages MUST reference the related `correlation_id` or `session_id` of the failed operation
- **Requirement CR4.18**: Cascade errors (errors caused by earlier errors) MUST maintain traceability to the root cause
- **Requirement CR4.19**: Error recovery events MUST correlate with the original error event that triggered recovery
- **Requirement CR4.20**: Multiple related errors MUST be grouped or correlated to provide meaningful debugging context

### 4.6 Cross-Component Correlation
- **Requirement CR4.21**: Events spanning multiple system components MUST maintain consistent correlation identifiers
- **Requirement CR4.22**: Distributed tracing IDs (when implemented) MUST align with session and correlation IDs where applicable
- **Requirement CR4.23**: External system interactions captured in events MUST maintain correlation with originating requests
- **Requirement CR4.24**: Asynchronous event processing MUST preserve correlation through all processing stages regardless of execution order

I've completed all the tasks for creating detailed, specific, and measurable success criteria for tool event capture as part of Task aicli4-1: Protocol Test Plan. The success criteria document has been created with four main sections:

1. Message Types Validation - with 25 specific requirements covering basic message structure, tool events, stream events, control events, session events, and message formatting validation.

2. Content Accuracy Requirements - with 24 specific requirements covering tool argument preservation, result content accuracy, user input preservation, session state accuracy, content integrity checks, and privacy/security considerations.

3. Timing Requirements - with 24 specific requirements covering message timestamp accuracy, tool execution timing, event sequencing, flow control timing, heartbeat timeouts, and session timing constraints.

4. Correlation Validation - with 24 specific requirements covering request-response pairing, session association, content block correlation, operation chaining, error correlation, and cross-component correlation.

Each requirement is specific enough to be validated through testing and provides measurable criteria for determining whether tool events are captured correctly in the AI CLI Live Tool Protocol.

# Agent-Side Hooks and Emission Points for AI CLI Live Tool Protocol

## Overview

This document outlines the required agent-side hooks and emission points for implementing the AI CLI Live Tool Protocol in the Maestro system. The protocol defines standardized communication between AI agents and CLI tools, enabling real-time tool usage events, live output streaming, and bidirectional communication.

## Required Agent-Side Hooks

### 1. Tool Call Request Hook

**Purpose**: Emitted when a tool call is initiated by the AI agent.

**Hook Location**: Should be placed in the AI agent's tool invocation mechanism, right before the actual tool execution.

**Message Type**: `tool_call_request`

**Required Fields**:
- `type`: "tool_call_request"
- `timestamp`: ISO 8601 timestamp
- `session_id`: Unique session identifier
- `correlation_id`: Correlation identifier for request/response matching
- `data.call_id`: Unique identifier for this tool call
- `data.name`: Name of the tool being called
- `data.args`: Arguments for the tool call
- `data.is_client_initiated`: Boolean indicating if call was initiated by client

### 2. Tool Call Confirmation Hook

**Purpose**: Emitted when a tool requires confirmation before execution.

**Hook Location**: Should be placed where the agent checks for user confirmation before executing potentially dangerous operations.

**Message Type**: `tool_call_confirmation`

**Required Fields**:
- `type`: "tool_call_confirmation"
- `timestamp`: ISO 8601 timestamp
- `session_id`: Unique session identifier
- `correlation_id`: Correlation identifier for request/response matching
- `data.request`: The original tool call request
- `data.details`: Confirmation details including type, title, and confirmation function

### 3. Tool Call Response Hook

**Purpose**: Emitted when a tool call completes and returns a result.

**Hook Location**: Should be placed immediately after the tool execution completes, whether successfully or with an error.

**Message Type**: `tool_call_response`

**Required Fields**:
- `type`: "tool_call_response"
- `timestamp`: ISO 8601 timestamp
- `session_id`: Unique session identifier
- `correlation_id`: Correlation identifier for request/response matching
- `data.call_id`: ID of the call this is a response to
- `data.responseParts`: Array of response parts
- `data.resultDisplay`: Display representation of the result
- `data.error`: Error message if the tool call failed (null if successful)
- `data.errorType`: Type of error (optional)
- `data.outputFile`: Path to an output file if generated (optional)
- `data.contentLength`: Length of the content returned (optional)

### 4. Flow Control Hook

**Purpose**: Emitted periodically to indicate available buffer capacity for flow control.

**Hook Location**: Should be placed in the message sending mechanism to track and report buffer capacity.

**Message Type**: `flow_control`

**Required Fields**:
- `type`: "flow_control"
- `timestamp`: ISO 8601 timestamp
- `session_id`: Unique session identifier
- `data.available_capacity`: Number of messages the receiver can handle
- `data.requested_capacity`: Requested capacity from sender

### 5. Error Notification Hook

**Purpose**: Emitted when an error occurs during tool execution or communication.

**Hook Location**: Should be placed in error handling mechanisms throughout the agent code.

**Message Type**: `error`

**Required Fields**:
- `type`: "error"
- `timestamp`: ISO 8601 timestamp
- `session_id`: Unique session identifier
- `correlation_id`: Correlation identifier for request/response matching (optional)
- `data.error_code`: Error code identifier
- `data.message`: Human-readable error message
- `data.details`: Optional error-specific details
- `data.severity`: Error severity level ("fatal", "error", "warning")
- `data.retriable`: Boolean indicating if the error is retriable

### 6. Session Management Hooks

**Purpose**: Emitted to manage session lifecycle.

**Hook Locations**:
- Session start: When a new AI interaction session begins
- Session end: When an AI interaction session ends
- Session state: When session state changes significantly

**Message Types**:
- `session_start`
- `session_end`
- `session_state`

**Required Fields**:
- `type`: Session event type
- `timestamp`: ISO 8601 timestamp
- `session_id`: Unique session identifier
- `data`: Session-specific data

### 7. Stream Event Hooks

**Purpose**: Emitted to handle streaming content during AI interactions.

**Hook Locations**:
- Message start: When an assistant message begins
- Content block start: When a content block begins
- Content block delta: When content block receives updates
- Content block stop: When a content block ends
- Message stop: When an assistant message ends

**Message Types**:
- `message_start`
- `content_block_start`
- `content_block_delta`
- `content_block_stop`
- `message_stop`

**Required Fields**: Vary by message type (see protocol specification)
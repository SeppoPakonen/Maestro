# Cross-Agent Delta Table: Transport Differences and Integration Analysis

## Overview
This document provides a comprehensive comparison of transport differences across various AI agents (Codex, Claude-Code, Copilot-CLI, and Gemini-CLI) for the AI CLI Live Tool Protocol integration. This analysis is part of Task aicli5-5: Cross-Agent Delta Table.

## Agent Comparison Table

| Aspect | Codex | Claude-Code | Copilot-CLI | Gemini-CLI |
|--------|-------|-------------|-------------|------------|
| **Transport Mechanism** | CLI via stdin/stdout | CLI via stdin/stdout | API via HTTP/CLI | API via HTTP/CLI |
| **Primary Transport** | Standard I/O (stdio) | Standard I/O (stdio) | Mixed (API + CLI) | API (HTTP REST/gRPC) |
| **Protocol Format** | Raw text | Raw text | Mixed formats | JSON responses |
| **Streaming Support** | Yes | Yes | Partial | Yes |
| **Connection Type** | Stateless | Stateless | Mixed | Stateless |
| **Authentication** | Token-based | Token-based | Token-based | Token-based |
| **Timeout Handling** | Process-based | Process-based | API timeouts | API timeouts |
| **Error Reporting** | Exit codes + stderr | Exit codes + stderr | Mixed | Structured JSON |
| **Message Framing** | Line-based | Line-based | Custom | JSON-based |
| **Session Management** | File-based context | File-based context | In-memory | API-managed |

## Detailed Transport Differences

### 1. Transport Mechanism Differences

#### Codex
- **Mechanism**: Standard input/output streams
- **Implementation**: Runs as external process, communicates via stdin/stdout
- **Advantages**: Simple process-based communication, low overhead
- **Challenges**: Requires careful handling of stdin/stdout, potential buffering issues

#### Claude-Code
- **Mechanism**: Standard input/output streams
- **Implementation**: Similar to Codex, runs as external process
- **Advantages**: Consistent with other CLI-based agents
- **Challenges**: Same as Codex, requires stdin/stdout management

#### Copilot-CLI
- **Mechanism**: Mixed approach (API and CLI)
- **Implementation**: Can use GitHub Copilot's API or CLI interface
- **Advantages**: More structured communication, better error handling
- **Challenges**: More complex setup, requires API key management

#### Gemini-CLI
- **Mechanism**: API-based (HTTP REST or gRPC)
- **Implementation**: Uses Gemini API endpoints
- **Advantages**: More robust error handling, structured responses
- **Challenges**: Network dependency, rate limiting considerations

### 2. Data Format Differences

#### Codex and Claude-Code
- **Format**: Raw text input/output
- **Structure**: Line-by-line processing
- **Protocol**: Simple text-based protocol
- **Serialization**: Direct to/from text

#### Copilot-CLI
- **Format**: Mixed (text and structured data)
- **Structure**: Can handle both raw text and structured responses
- **Protocol**: Flexible based on interface used
- **Serialization**: Varies by interface

#### Gemini-CLI
- **Format**: JSON-based responses
- **Structure**: Well-defined JSON objects
- **Protocol**: Structured JSON protocol
- **Serialization**: JSON serialization/deserialization

### 3. Streaming Behavior Differences

| Agent | Stream Initiation | Stream Format | Stream Control | Buffering |
|-------|------------------|---------------|----------------|-----------|
| Codex | Process execution | Line-by-line | Process-based | OS-level buffering |
| Claude-Code | Process execution | Line-by-line | Process-based | OS-level buffering |
| Copilot-CLI | API request | Chunked | API-managed | Application-level |
| Gemini-CLI | API request | JSON chunks | API-managed | Application-level |

### 4. Error Handling Differences

#### Codex and Claude-Code
- **Error Format**: Text-based error messages in stderr
- **Error Codes**: Process exit codes
- **Recovery**: Process restart or retry
- **Logging**: Direct to stderr

#### Copilot-CLI 
- **Error Format**: Mixed (text and structured)
- **Error Codes**: API response codes + exit codes
- **Recovery**: API retry with backoff
- **Logging**: Structured logging

#### Gemini-CLI
- **Error Format**: JSON-based error responses
- **Error Codes**: HTTP status codes + Gemini error codes
- **Recovery**: API retry with exponential backoff
- **Logging**: Structured JSON logging

## Tool Event Granularity Gaps

### 1. Request/Response Timing Differences
- **CLI-based agents (Codex, Claude-Code)**: Tool call events occur around process execution
- **API-based agents (Copilot-CLI, Gemini-CLI)**: Tool call events can be more granular with API request/response boundaries

### 2. Streaming Event Differences
- **CLI-based agents**: Stream events tied to line-by-line output
- **API-based agents**: Stream events can be tied to API response chunks

### 3. Error Capture Differences
- **CLI-based agents**: Errors captured when process exits with error code
- **API-based agents**: Errors captured immediately when API returns error response

## Shared Helper Candidates

### 1. Protocol Emitter Base Class
**Purpose**: Common interface for emitting protocol messages across all agents
**Benefits**: 
- Consistent message format across agents
- Centralized validation and error handling
- Common transport abstraction

```python
class ProtocolEmitter:
    def emit_message(self, message: dict):
        # Common validation and formatting
        pass
    
    def connect_transport(self, transport_config: dict):
        # Generic transport connection
        pass
```

### 2. Session Context Manager
**Purpose**: Manage session state consistently across all agents
**Benefits**:
- Unified session ID management
- Consistent correlation ID handling
- Centralized session lifecycle management

### 3. Standard Message Builder
**Purpose**: Create protocol-compliant messages from agent-specific data
**Benefits**:
- Convert agent-specific formats to protocol format
- Handle timestamp generation consistently
- Ensure required fields are present

### 4. Transport Adapter Abstract Base
**Purpose**: Provide common interface for different transport mechanisms
**Benefits**:
- Same protocol emitter can work with different transports
- Easier testing with mock transports
- Consistent error handling across transports

## Recommendations

### 1. Transport Abstraction Layer
Implement a transport abstraction layer that allows the same protocol handling logic to work with different transport mechanisms. This would include:

- Common interfaces for message emission
- Abstract classes for transport operations
- Standardized error handling across transport types

### 2. Agent-Specific Protocol Adapters
Create agent-specific adapters that handle the differences in:
- Message serialization/deserialization
- Streaming behavior
- Error handling and reporting

### 3. Standardized Configuration
Establish a standardized configuration format that works for both CLI and API-based agents, covering:

- Authentication settings
- Transport parameters
- Timeout settings
- Retry policies

### 4. Shared Utilities
Develop shared utilities for common operations:
- ID generation (session, correlation, call IDs)
- Timestamp formatting
- Message validation
- Logging and monitoring

## Implementation Strategy

### Phase 1: Core Protocol Framework
1. Develop the ProtocolEmitter base class
2. Create transport abstraction interfaces
3. Implement basic message builders

### Phase 2: Agent-Specific Adapters
1. Create Claude-Code protocol adapter
2. Create Gemini-CLI protocol adapter
3. Create Copilot-CLI protocol adapter
4. Create Codex protocol adapter

### Phase 3: Integration
1. Integrate adapters with existing agent implementations
2. Test transport abstraction with all agents
3. Validate protocol compliance across agents

This cross-agent delta table highlights the significant differences in transport mechanisms, data formats, and error handling approaches between the different AI agents, while identifying commonalities that can be leveraged to create shared components and tools.
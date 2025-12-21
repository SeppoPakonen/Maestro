# Cross-Agent Delta Table: Shared Helper Candidates Analysis

## Overview
This document identifies candidates for shared helpers that can be used across multiple AI agents (Codex, Claude-Code, Copilot-CLI, and Gemini-CLI) for the AI CLI Live Tool Protocol integration. This analysis is part of Task aicli5-5: Cross-Agent Delta Table - Identify candidates for shared helpers.

## Shared Helper Categories

### 1. Protocol Message Management Helpers

#### A. Protocol Message Validator
**Purpose**: Validate protocol messages against the AI CLI Live Tool Protocol specification
**Agents Served**: All agents (Codex, Claude-Code, Copilot-CLI, Gemini-CLI)
**Functionality**:
- Verify required fields are present
- Validate timestamp format
- Check message structure integrity
- Validate session ID format
- Ensure proper correlation IDs

```python
def validate_protocol_message(message: dict) -> bool:
    required_fields = ['type', 'timestamp', 'session_id', 'data']
    return all(field in message for field in required_fields)
```

#### B. Message ID Generator
**Purpose**: Generate unique IDs for different message types (session, call, correlation)
**Agents Served**: All agents
**Functionality**:
- Generate unique session IDs
- Generate unique call IDs
- Generate unique correlation IDs
- Maintain ID uniqueness across sessions

```python
def generate_session_id() -> str:
    return f"session_{uuid.uuid4().hex[:12]}_{int(time.time())}"

def generate_call_id() -> str:
    return f"call_{uuid.uuid4().hex[:8]}_{int(time.time() * 1000)}"
```

#### C. Timestamp Formatter
**Purpose**: Format timestamps consistently across all agents
**Agents Served**: All agents
**Functionality**:
- Convert timestamps to ISO 8601 format
- Ensure millisecond precision
- Handle different input timestamp formats

```python
def format_iso_timestamp(timestamp: Optional[datetime] = None) -> str:
    if timestamp is None:
        timestamp = datetime.utcnow()
    return timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3]  # Truncate to milliseconds
```

### 2. Transport Abstraction Helpers

#### A. Transport Adapter Interface
**Purpose**: Provide a common interface for different transport mechanisms
**Agents Served**: All agents (with varying transport needs)
**Functionality**:
- Abstract transport layer differences
- Provide consistent send/receive methods
- Handle transport-specific error conditions

```python
class TransportAdapter(ABC):
    @abstractmethod
    def connect(self, config: dict):
        pass
    
    @abstractmethod
    def send_message(self, message: str):
        pass
    
    @abstractmethod
    def receive_message(self) -> str:
        pass
```

#### B. Standard I/O Transport Helper
**Purpose**: Handle stdio transport for CLI-based agents
**Agents Served**: Codex, Claude-Code
**Functionality**:
- Manage stdin/stdout communication
- Handle buffering issues
- Implement NDJSON framing

```python
class StdioTransportAdapter(TransportAdapter):
    def send_message(self, message: str):
        print(message, file=sys.stdout, flush=True)
    
    def receive_message(self) -> str:
        return sys.stdin.readline().strip()
```

#### C. HTTP Transport Helper
**Purpose**: Handle HTTP communication for API-based agents
**Agents Served**: Copilot-CLI, Gemini-CLI
**Functionality**:
- Manage HTTP connections
- Handle authentication
- Process API responses

```python
class HttpTransportAdapter(TransportAdapter):
    def __init__(self, base_url: str, headers: dict):
        self.base_url = base_url
        self.headers = headers
        self.session = requests.Session()
```

### 3. Session Management Helpers

#### A. Session Context Manager
**Purpose**: Manage session state consistently across agents
**Agents Served**: All agents
**Functionality**:
- Track active session information
- Maintain correlation between related messages
- Handle session lifecycle events

```python
class SessionContextManager:
    def __init__(self):
        self.active_sessions = {}
    
    def create_session(self, session_type: str) -> str:
        session_id = generate_session_id()
        self.active_sessions[session_id] = {
            'type': session_type,
            'created_at': time.time(),
            'correlation_map': {}
        }
        return session_id
```

#### B. Correlation Tracker
**Purpose**: Track correlations between request and response messages
**Agents Served**: All agents
**Functionality**:
- Map request IDs to response IDs
- Maintain correlation state
- Handle timeout scenarios

```python
class CorrelationTracker:
    def __init__(self, timeout: int = 30):
        self.pending_requests = {}
        self.timeout = timeout
    
    def register_request(self, correlation_id: str, request_type: str):
        self.pending_requests[correlation_id] = {
            'type': request_type,
            'timestamp': time.time()
        }
    
    def resolve_correlation(self, correlation_id: str) -> Optional[dict]:
        return self.pending_requests.pop(correlation_id, None)
```

### 4. Error Handling Helpers

#### A. Protocol Error Formatter
**Purpose**: Format errors consistently across agents for the protocol
**Agents Served**: All agents
**Functionality**:
- Convert internal errors to protocol format
- Assign appropriate error codes
- Set proper severity levels

```python
def format_protocol_error(error: Exception, error_code: str = "GENERAL_ERROR") -> dict:
    return {
        "type": "error",
        "timestamp": format_iso_timestamp(),
        "session_id": get_current_session_id(),
        "data": {
            "error_code": error_code,
            "message": str(error),
            "details": {"error_type": type(error).__name__},
            "severity": "error",
            "retriable": True
        }
    }
```

#### B. Retry Handler
**Purpose**: Implement consistent retry logic for all agents
**Agents Served**: All agents
**Functionality**:
- Handle retryable errors
- Implement exponential backoff
- Track retry attempts

```python
def with_retry(func, max_retries: int = 3, backoff_base: float = 1.0):
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries:
                raise e
            sleep_time = backoff_base * (2 ** attempt)
            time.sleep(sleep_time)
```

### 5. Configuration Management Helpers

#### A. Agent Configuration Loader
**Purpose**: Load and validate agent-specific configurations
**Agents Served**: All agents
**Functionality**:
- Parse configuration files
- Validate required parameters
- Provide default values

```python
def load_agent_config(agent_name: str, config_file: Optional[str] = None) -> dict:
    # Load config from file or defaults
    config = load_config_file(config_file) if config_file else {}
    
    # Validate required fields
    required_fields = get_required_fields(agent_name)
    validate_config(config, required_fields)
    
    return config
```

#### B. Transport Configuration Normalizer
**Purpose**: Normalize transport configurations across different agents
**Agents Served**: All agents
**Functionality**:
- Convert agent-specific config to transport-agnostic format
- Handle different auth methods
- Normalize endpoint URLs

```python
def normalize_transport_config(config: dict) -> dict:
    transport_config = {
        'type': config.get('transport_type', 'stdio'),
        'endpoint': config.get('endpoint', ''),
        'auth': {
            'type': config.get('auth_type', 'none'),
            'token': config.get('token', ''),
            'headers': config.get('headers', {})
        }
    }
    return transport_config
```

### 6. Data Processing Helpers

#### A. Response Parser
**Purpose**: Parse agent responses into protocol-compatible formats
**Agents Served**: All agents
**Functionality**:
- Parse different response formats
- Extract relevant information
- Structure data according to protocol

```python
def parse_agent_response(response: str, response_format: str) -> dict:
    if response_format == 'json':
        return json.loads(response)
    elif response_format == 'text':
        return {'content': response}
    # Additional formats as needed
```

#### B. Content Streamer
**Purpose**: Handle streaming content consistently across agents
**Agents Served**: All agents with streaming capability
**Functionality**:
- Manage streaming event generation
- Handle chunked content
- Provide consistent streaming interface

```python
def create_content_streamer(content: str, chunk_size: int = 1024) -> Iterator[str]:
    for i in range(0, len(content), chunk_size):
        yield content[i:i + chunk_size]
```

## Implementation Priority and Dependencies

### Priority 1: Core Protocol Helpers
1. Protocol Message Validator
2. Message ID Generator
3. Timestamp Formatter
4. Session Context Manager

### Priority 2: Transport Helpers
1. Transport Adapter Interface
2. Standard I/O Transport Helper
3. HTTP Transport Helper
4. Transport Configuration Normalizer

### Priority 3: Advanced Helpers
1. Correlation Tracker
2. Protocol Error Formatter
3. Retry Handler
4. Response Parser
5. Content Streamer

## Benefits of Shared Helpers

### 1. Code Reusability
- Reduce code duplication across agents
- Maintain consistent implementation
- Simplify maintenance and updates

### 2. Protocol Compliance
- Ensure consistent protocol implementation
- Centralize validation logic
- Reduce protocol-related bugs

### 3. Easier Integration
- Simplified onboarding for new agents
- Consistent interfaces and patterns
- Reduced learning curve for developers

### 4. Testing Efficiency
- Centralized testing for common functionality
- Reusable test cases across agents
- Improved coverage with less effort

## Recommended Implementation Approach

### Phase 1: Core Framework
- Implement basic protocol message helpers
- Create session management utilities
- Establish transport abstraction layer

### Phase 2: Transport Integration
- Implement specific transport adapters
- Create configuration normalization
- Add error handling utilities

### Phase 3: Advanced Features
- Add correlation tracking
- Implement advanced data processing
- Create specialized streamers and parsers

By implementing these shared helpers, the AI CLI Live Tool Protocol can be consistently applied across all agents while reducing duplication and maintenance overhead.
# Gemini-CLI Input Injection Entry Points Analysis

## Overview
This document identifies and analyzes input injection entry points specific to the Gemini-CLI integration within the AI CLI Live Tool Protocol. This analysis is part of Task aicli5-4: Gemini-CLI Integration Plan.

## Protocol Context
The AI CLI Live Tool Protocol defines `user_input` messages to capture user input during active sessions. These messages follow the structure:

```json
{
  "type": "user_input",
  "timestamp": "ISO 8601 timestamp",
  "session_id": "unique session identifier",
  "correlation_id": "optional correlation identifier",
  "data": {
    "content": "actual user input content",
    "input_type": "type of input (text, selection, etc.)",
    "context": "context of the input"
  }
}
```

## Gemini-CLI Input Injection Points

### 1. Interactive Command Execution
**Location**: `maestro/main.py` in command handling functions
**Context**: When users interact with Gemini-CLI commands
**Entry Point**: When command parameters are accepted from the user

**Implementation**:
```python
def handle_interactive_command():
    # ... existing code ...
    
    # Input injection point when user provides command parameters
    command_params = input("Enter command parameters for Gemini: ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": current_session_id,
        "data": {
            "content": command_params,
            "input_type": "command_parameters",
            "context": "interactive_command_execution"
        }
    })
```

### 2. AI Interaction Prompts
**Location**: `maestro/engines.py` in AI interaction functions
**Context**: When users provide prompts to Gemini
**Entry Point**: When user enters AI prompts

**Implementation**:
```python
def handle_ai_interaction():
    # ... existing code ...
    
    # Input injection point when user provides AI prompt
    user_prompt = input("Enter your prompt for Gemini: ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": current_session_id,
        "data": {
            "content": user_prompt,
            "input_type": "ai_prompt",
            "context": "gemini_ai_interaction"
        }
    })
```

### 3. File Operation Confirmation
**Location**: `maestro/main.py` in file operation functions
**Context**: When Gemini suggests file modifications
**Entry Point**: When user confirms or denies suggested operations

**Implementation**:
```python
def confirm_file_operation():
    # ... existing code ...
    
    # Input injection point when user confirms file operation
    confirmation = input("Do you want to proceed with this operation? (y/n): ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": current_session_id,
        "data": {
            "content": confirmation,
            "input_type": "operation_confirmation",
            "context": "file_operation_approval"
        }
    })
```

### 4. Session Configuration
**Location**: `maestro/work_session.py` in session creation functions
**Context**: When users configure Gemini-CLI sessions
**Entry Point**: When user provides session configuration

**Implementation**:
```python
def create_gemini_session():
    # ... existing code ...
    
    # Input injection point when user configures session
    session_config = input("Enter Gemini session configuration: ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": new_session_id,
        "data": {
            "content": session_config,
            "input_type": "session_configuration",
            "context": "session_setup"
        }
    })
```

### 5. Tool Selection Menu
**Location**: `maestro/main.py` in tool selection functions
**Context**: When users choose from Gemini-CLI tool options
**Entry Point**: When user selects a tool from the menu

**Implementation**:
```python
def show_tool_menu():
    # ... existing code ...
    tools = ["write_file", "read_file", "edit_file", "list_directory"]
    for i, tool in enumerate(tools):
        print(f"{i+1}. {tool}")
    
    # Input injection point when user selects tool
    selection = input("Select a tool for Gemini: ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": current_session_id,
        "data": {
            "content": selection,
            "input_type": "tool_selection",
            "context": "tool_menu_interaction"
        }
    })
```

### 6. Multiline Input for Complex Requests
**Location**: `maestro/editor.py` in multiline input functions
**Context**: When users need to provide longer input to Gemini
**Entry Point**: When user completes multiline input

**Implementation**:
```python
def get_multiline_gemini_input():
    # ... existing implementation ...
    lines = []
    
    while True:
        line = input()
        if line.strip() == END_MARKER:
            break
        lines.append(line)
    
    full_input = "\n".join(lines)
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": current_session_id,
        "data": {
            "content": full_input,
            "input_type": "multiline_request",
            "context": "complex_request_input"
        }
    })
    
    return full_input
```

### 7. Context and Settings Modification
**Location**: `maestro/commands/work.py` in context management functions
**Context**: When users modify Gemini-CLI settings or context
**Entry Point**: When user provides new settings or context

**Implementation**:
```python
def modify_context():
    # ... existing code ...
    
    # Input injection point when user modifies context
    new_context = input("Enter new context for Gemini: ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": current_session_id,
        "data": {
            "content": new_context,
            "input_type": "context_modification",
            "context": "context_update"
        }
    })
```

### 8. Real-time Interaction Mode
**Location**: `maestro/commands/work.py` in continuous interaction functions
**Context**: When users engage in ongoing conversation with Gemini
**Entry Point**: At each prompt in continuous interaction

**Implementation**:
```python
def handle_continuous_interaction():
    # ... existing code ...
    
    while True:
        # Input injection point in continuous interaction
        user_input = input("Gemini> ")
        
        # Check for exit conditions
        if user_input.lower() in ['exit', 'quit', 'q']:
            break
            
        # Emit user_input message
        protocol_emitter.emit_message({
            "type": "user_input",
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": current_session_id,
            "data": {
                "content": user_input,
                "input_type": "continuous_interaction",
                "context": "ongoing_conversation"
            }
        })
```

## Injection During Active Tool Execution

### 9. Mid-Operation Input Injection
**Location**: Signal handlers or interrupt mechanisms
**Context**: When user needs to inject input during active Gemini operations
**Entry Point**: Through interrupt signals or alternative input channels

**Implementation**:
```python
import signal
import threading

class GeminiInputInjectionHandler:
    def __init__(self, protocol_emitter):
        self.protocol_emitter = protocol_emitter
        self.session_id = None
        self.injection_queue = []
        self.lock = threading.Lock()
    
    def set_session_id(self, session_id):
        self.session_id = session_id
    
    def inject_input(self, content, input_type="injected"):
        """Method for injecting input during active operations."""
        with self.lock:
            input_message = {
                "type": "user_input",
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": self.session_id,
                "data": {
                    "content": content,
                    "input_type": input_type,
                    "context": "mid_operation_injection"
                }
            }
            self.protocol_emitter.emit_message(input_message)
            self.injection_queue.append(input_message)
    
    def signal_handler(self, signum, frame):
        """Handle interrupt signals for input injection."""
        print("\nInput injection mode activated. Type your input:")
        injected_content = input(">> ")
        
        self.inject_input(injected_content, "interrupt_injected")
```

## Gemini-Specific Input Injection Points

### 10. Gemini API Configuration
**Location**: In Gemini-specific engine configuration
**Context**: When users configure Gemini-specific parameters
**Entry Point**: When user provides Gemini API-specific settings

**Implementation**:
```python
def configure_gemini_api():
    # ... existing code ...
    
    # Input injection point when user configures Gemini API
    api_key = input("Enter Gemini API key: ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": current_session_id,
        "data": {
            "content": "API key configured",
            "input_type": "api_configuration",
            "context": "gemini_api_setup"
        }
    })
```

### 11. Model Selection
**Location**: In model selection functions
**Context**: When users select Gemini model
**Entry Point**: When user chooses a specific Gemini model

**Implementation**:
```python
def select_gemini_model():
    # ... existing code ...
    
    # Input injection point when user selects model
    model_choice = input("Select Gemini model: ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": current_session_id,
        "data": {
            "content": model_choice,
            "input_type": "model_selection",
            "context": "model_configuration"
        }
    })
```

### 12. Prompt Engineering
**Location**: In prompt engineering functions
**Context**: When users provide advanced prompts for Gemini
**Entry Point**: When user defines custom prompts for specific tasks

**Implementation**:
```python
def define_custom_prompt():
    # ... existing code ...
    
    # Input injection point when user defines custom prompt
    custom_prompt = input("Enter custom prompt for Gemini: ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": current_session_id,
        "data": {
            "content": custom_prompt,
            "input_type": "custom_prompt",
            "context": "prompt_engineering"
        }
    })
```

## Security and Validation Considerations

### Input Validation
Each input injection point should validate the input according to the protocol:

1. **Length validation**: Ensure input doesn't exceed protocol limits
2. **Content validation**: Sanitize input to prevent injection attacks
3. **Context validation**: Verify input is appropriate for the current session context

### Session Association
All input injection points must maintain proper session correlation:
- Use the correct `session_id` for the active session
- Generate appropriate `correlation_id` if needed for request/response matching
- Maintain chronological ordering with proper timestamps

## Implementation Requirements

### 1. Protocol Emitter Integration
Each input injection point must be connected to a protocol emitter instance that can send messages via the appropriate transport mechanism.

### 2. Session Context Management
Input injection points must have access to the current session context to include the correct `session_id` in messages.

### 3. Error Handling
Robust error handling must be in place in case message emission fails, without disrupting the core application functionality.

## Testing Strategy

### 1. Unit Testing
Test each input injection point individually to ensure proper message generation and emission.

### 2. Integration Testing
Test the complete flow from user input to protocol message emission with various input types and contexts.

### 3. End-to-End Testing
Test full Gemini-CLI interactions with input injection to ensure proper session flow and message sequencing.

This comprehensive analysis identifies all the major input injection entry points for Gemini-CLI integration with the AI CLI Live Tool Protocol, providing implementation guidance for each point while maintaining security and validation standards.
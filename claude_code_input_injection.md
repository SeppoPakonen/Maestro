# Claude-Code Input Injection Entry Points Analysis

## Overview
This document identifies and analyzes input injection entry points specific to the Claude-Code integration within the AI CLI Live Tool Protocol. This analysis is part of Task aicli5-2: Claude-Code Integration Plan.

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

## Claude-Code Input Injection Points

### 1. Interactive Planning Sessions
**Location**: `maestro/main.py` in the `interactive_plan_session` function
**Context**: When users are working with Claude-Code to plan operations
**Entry Point**: When user selects options from the menu

**Implementation**:
```python
def interactive_plan_session(session_path, ...):
    # ... existing code ...
    for idx, option in enumerate(options):
        print(f"{idx+1}. {option}")
    
    # Input injection point
    choice = input("\nSelect an option (or 's' to skip): ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": session.session_id,
        "data": {
            "content": choice,
            "input_type": "menu_selection",
            "context": "interactive_planning_session"
        }
    })
```

### 2. Build Target Configuration
**Location**: `maestro/main.py` in functions that interact with Claude-Code for build planning
**Context**: When Claude-Code requests specific build targets or configurations
**Entry Point**: When users respond to Claude's requests for specific information

**Implementation**:
```python
def handle_build_planning():
    # ... existing code ...
    
    # Input injection point when user specifies build targets
    build_target = input("Specify build target (or 'default' for default build): ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": current_session_id,
        "data": {
            "content": build_target,
            "input_type": "build_target",
            "context": "claude_code_build_planning"
        }
    })
```

### 3. Root Task Discussion
**Location**: `maestro/main.py` in the `discuss_root_task` function
**Context**: When users are discussing the main task with Claude-Code
**Entry Point**: When user provides input during the discussion

**Implementation**:
```python
def discuss_root_task():
    # ... existing code ...
    
    # Input injection point when user responds to Claude
    user_response = input(f"{get_user_prefix()}: ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": current_session_id,
        "data": {
            "content": user_response,
            "input_type": "discussion_reply",
            "context": "root_task_discussion"
        }
    })
```

### 4. Rulebook Planning
**Location**: `maestro/main.py` in rulebook-related functions
**Context**: When Claude-Code is helping to plan or modify rulebooks
**Entry Point**: When user provides rule modifications or confirms changes

**Implementation**:
```python
def handle_rulebook_planning():
    # ... existing code ...
    
    # Input injection point when user provides rule input
    rule_input = input("Enter new rule or 'confirm' to accept: ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": current_session_id,
        "data": {
            "content": rule_input,
            "input_type": "rule_definition",
            "context": "rulebook_planning"
        }
    })
```

### 5. Session Configuration
**Location**: `maestro/work_session.py` in session creation/modification functions
**Context**: When creating or modifying Claude-Code sessions
**Entry Point**: When user configures session parameters

**Implementation**:
```python
def create_session():
    # ... existing code ...
    
    # Input injection point when configuring session
    session_name = input("Enter session name: ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": new_session_id,
        "data": {
            "content": session_name,
            "input_type": "session_config",
            "context": "session_creation"
        }
    })
```

### 6. Multiline Input for Complex Prompts
**Location**: `maestro/editor.py` in the `get_multiline_input` function
**Context**: When users need to provide multi-line input for Claude-Code
**Entry Point**: When user finishes input with the end marker

**Implementation**:
```python
def get_multiline_input():
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
            "input_type": "multiline_text",
            "context": "complex_prompt_input"
        }
    })
    
    return full_input
```

### 7. Tool Confirmation and Approval
**Location**: `maestro/main.py` in file operation confirmation functions
**Context**: When Claude-Code proposes changes that require user approval
**Entry Point**: When user confirms or denies tool usage

**Implementation**:
```python
def confirm_file_operation():
    # ... existing code ...
    
    # Input injection point when user confirms tool usage
    confirmation = input("Do you want to proceed? (y/n): ")
    
    # Emit user_input message
    protocol_emitter.emit_message({
        "type": "user_input",
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": current_session_id,
        "data": {
            "content": confirmation,
            "input_type": "tool_confirmation",
            "context": "file_operation_approval"
        }
    })
```

### 8. Terminal/Editor Discussion Mode
**Location**: `maestro/commands/work.py` in the `handle_work_discuss` function
**Context**: When user is in a continuous discussion with Claude-Code
**Entry Point**: At each user input prompt in the discussion loop

**Implementation**:
```python
def handle_work_discuss():
    # ... existing code ...
    
    while True:
        # Input injection point in continuous discussion
        user_input = input(f"{get_user_prefix()}: ")
        
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
                "input_type": "continuous_discussion",
                "context": "work_discussion_mode"
            }
        })
```

## Injection During Active Tool Execution

### 9. Mid-Operation Input Injection
**Location**: Signal handlers or interrupt mechanisms
**Context**: When user needs to inject input during active Claude-Code operations
**Entry Point**: Through interrupt signals (Ctrl+C) or alternative input channels

**Implementation**:
```python
import signal
import threading

class InputInjectionHandler:
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
Test full Claude-Code interactions with input injection to ensure proper session flow and message sequencing.

This comprehensive analysis identifies all the major input injection entry points for Claude-Code integration with the AI CLI Live Tool Protocol, providing implementation guidance for each point while maintaining security and validation standards.
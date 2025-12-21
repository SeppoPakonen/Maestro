# Implementation Guide: Agent-Side Hooks Placement

## Overview

This document details the specific locations in the Maestro codebase where the AI CLI Live Tool Protocol hooks should be implemented.

## Codebase Analysis

Based on analysis of the Maestro codebase, the following files and locations are relevant for implementing the protocol hooks:

### 1. Tool Call Request Hook Implementation

**Location**: `maestro/main.py` - In the operation execution functions

**Specific Functions**:
- `apply_fix_plan_operations()` - This function executes various operations like `WriteFileOperation`, `EditFileOperation`, etc.
- Should be placed right before the actual file operations execute

**Code Example**:
```python
# In apply_fix_plan_operations function, before actual operation
if isinstance(op, WriteFileOperation):
    # Emit tool_call_request
    emit_protocol_message({
        "type": "tool_call_request",
        "timestamp": iso_timestamp(),
        "session_id": session_id,
        "correlation_id": generate_correlation_id(),
        "data": {
            "call_id": generate_call_id(),
            "name": "write_file",
            "args": {"path": op.path, "content": op.content},
            "is_client_initiated": False
        }
    })
    
    # Ensure directory exists
    dest_dir = os.path.dirname(op.path)
    os.makedirs(dest_dir, exist_ok=True)
    with open(op.path, 'w', encoding='utf-8') as f:
        f.write(op.content)
    print_success(f"Written: {op.path}", 2)
```

### 2. Tool Call Response Hook Implementation

**Location**: `maestro/main.py` - In the operation execution functions

**Specific Functions**:
- `apply_fix_plan_operations()` - After each operation completes
- Should be placed immediately after the operation completes (success or failure)

**Code Example**:
```python
# In apply_fix_plan_operations function, after operation
if isinstance(op, WriteFileOperation):
    try:
        # Ensure directory exists
        dest_dir = os.path.dirname(op.path)
        os.makedirs(dest_dir, exist_ok=True)
        with open(op.path, 'w', encoding='utf-8') as f:
            f.write(op.content)
        print_success(f"Written: {op.path}", 2)
        
        # Emit tool_call_response for success
        emit_protocol_message({
            "type": "tool_call_response",
            "timestamp": iso_timestamp(),
            "session_id": session_id,
            "correlation_id": correlation_id,  # From the request
            "data": {
                "call_id": call_id,  # From the request
                "responseParts": [{"text": f"Successfully wrote file: {op.path}"}],
                "resultDisplay": f"File {op.path} written successfully",
                "error": None,
                "contentLength": len(op.content)
            }
        })
    except Exception as e:
        # Emit tool_call_response for error
        emit_protocol_message({
            "type": "tool_call_response",
            "timestamp": iso_timestamp(),
            "session_id": session_id,
            "correlation_id": correlation_id,  # From the request
            "data": {
                "call_id": call_id,  # From the request
                "responseParts": [],
                "resultDisplay": f"Error writing file: {op.path}",
                "error": str(e),
                "errorType": type(e).__name__
            }
        })
```

### 3. Tool Call Confirmation Hook Implementation

**Location**: `maestro/ai/actions.py` - In action validation and execution functions

**Specific Functions**:
- `_apply_track_add`, `_apply_track_edit`, `_apply_track_remove`, etc.
- Any function that modifies the system state

**Code Example**:
```python
def _apply_track_add(self, data: Dict[str, Any]) -> str:
    # Emit tool_call_confirmation before making changes
    confirmation_needed = emit_protocol_message({
        "type": "tool_call_confirmation",
        "timestamp": iso_timestamp(),
        "session_id": session_id,
        "data": {
            "request": {
                "callId": generate_call_id(),
                "name": "add_track",
                "args": data,
                "isClientInitiated": False,
                "prompt_id": current_prompt_id,
                "response_id": current_response_id
            },
            "details": {
                "type": "edit",
                "title": "Track Addition Confirmation",
                "onConfirm": "function reference",
                "fileName": "docs/todo.md",
                "filePath": "docs/todo.md",
                "fileDiff": generate_diff_preview(data),
                "originalContent": "",
                "newContent": generate_new_track_content(data),
                "isModifying": True
            }
        }
    })
    
    # Wait for confirmation or proceed based on approval mode
    if confirmation_needed:
        wait_for_user_confirmation()
    
    # Proceed with the actual operation
    name = data.get("name")
    # ... rest of the operation
```

### 4. Error Notification Hook Implementation

**Location**: Throughout the codebase in error handling blocks

**Specific Locations**:
- `maestro/main.py` - In `apply_fix_plan_operations()` for file operation errors
- `maestro/engines.py` - In engine execution functions
- `maestro/commands/work.py` - In AI interaction functions
- `maestro/breadcrumb.py` - In breadcrumb creation functions

**Code Example**:
```python
# In apply_fix_plan_operations function, in exception blocks
except Exception as e:
    emit_protocol_message({
        "type": "error",
        "timestamp": iso_timestamp(),
        "session_id": session_id,
        "correlation_id": correlation_id,
        "data": {
            "error_code": "OPERATION_FAILED",
            "message": f"Operation failed: {str(e)}",
            "details": {"operation_type": op.op, "operation_path": getattr(op, 'path', 'unknown')},
            "severity": "error",
            "retriable": False
        }
    })
    raise e
```

### 5. Session Management Hook Implementation

**Location**: `maestro/work_session.py` - In session creation and completion functions

**Specific Functions**:
- `create_session()` - Emit `session_start`
- `complete_session()` - Emit `session_end`
- `save_session()` - Emit `session_state`

**Code Example**:
```python
def create_session(session_type, related_entity=None, metadata=None, parent_session_id=None):
    # ... existing session creation logic ...
    
    # Emit session_start event
    emit_protocol_message({
        "type": "session_start",
        "timestamp": iso_timestamp(),
        "session_id": session.session_id,
        "data": {
            "session_type": session_type,
            "related_entity": related_entity,
            "metadata": metadata or {},
            "parent_session_id": parent_session_id
        }
    })
    
    return session

def complete_session(session):
    # ... existing session completion logic ...
    
    # Emit session_end event
    emit_protocol_message({
        "type": "session_end",
        "timestamp": iso_timestamp(),
        "session_id": session.session_id,
        "data": {
            "status": session.status,
            "completion_reason": "completed"
        }
    })
```

### 6. Stream Event Hook Implementation

**Location**: `maestro/engines.py` - In streaming response functions

**Specific Functions**:
- `stream_message()` in `ExternalCommandClient`
- Any function that handles streaming AI responses

**Code Example**:
```python
def stream_message(self, messages: List[Dict[str, str]], context: str) -> Iterator[str]:
    # Emit message_start
    emit_protocol_message({
        "type": "message_start",
        "timestamp": iso_timestamp(),
        "session_id": current_session_id,
        "message": {
            "id": generate_message_id(),
            "role": "assistant",
            "model": self.provider
        }
    })
    
    prompt = self._build_prompt(messages, context)
    process = subprocess.Popen(
        self.command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(prompt)
    process.stdin.close()
    
    for line in process.stdout:
        # Emit content_block_delta for each chunk
        emit_protocol_message({
            "type": "content_block_delta",
            "timestamp": iso_timestamp(),
            "session_id": current_session_id,
            "index": 0,
            "delta": {
                "type": "text_delta",
                "text": line
            }
        })
        yield line
    
    process.wait()
    
    # Emit message_stop
    emit_protocol_message({
        "type": "message_stop",
        "timestamp": iso_timestamp(),
        "session_id": current_session_id
    })
    
    if process.returncode != 0:
        stderr = process.stderr.read() if process.stderr else ""
        raise RuntimeError(stderr.strip() or "AI command failed.")
```

### 7. Flow Control Hook Implementation

**Location**: `maestro/main.py` - In the message emission system

**Specific Functions**:
- A new function to manage message flow and capacity
- Should be called periodically during high-volume message transmission

**Code Example**:
```python
def manage_flow_control():
    # Track available capacity
    available_capacity = get_available_capacity()
    
    # Emit flow_control message if capacity is low
    if available_capacity < THRESHOLD:
        emit_protocol_message({
            "type": "flow_control",
            "timestamp": iso_timestamp(),
            "session_id": current_session_id,
            "data": {
                "available_capacity": available_capacity,
                "requested_capacity": DESIRED_CAPACITY
            }
        })
```

## Implementation Priority

1. **High Priority**: Tool call request/response hooks in operation execution functions
2. **Medium Priority**: Session management hooks in session creation/completion functions
3. **Medium Priority**: Error notification hooks in error handling blocks
4. **Low Priority**: Flow control and stream event hooks (for advanced features)
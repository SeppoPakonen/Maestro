# Qwen Python Implementation for Maestro

This package provides a Python implementation of the Qwen functionality that was originally implemented in C++ and Node.js. It enables communication with the Qwen AI service using various communication modes.

## Components

- `server.py`: Implements server functionality supporting stdin/stdout, named pipes, and TCP communication
- `client.py`: Implements client functionality to connect to the actual Qwen service
- `main.py`: Combines server and client functionality in a QwenManager class
- `example_usage.py`: Demonstrates how to use the implementation

## Communication Modes

The server supports three communication modes:

1. **Stdin/Stdout**: Line-buffered JSON communication via standard input/output
2. **Named Pipes**: Bidirectional communication via filesystem pipes
3. **TCP**: Network-based communication over TCP

## Usage

### Running the Server

```bash
# Stdin mode (default)
python3 -m maestro.qwen.main --mode stdin

# TCP mode
python3 -m maestro.qwen.main --mode tcp --tcp-port 8080

# Named pipe mode
python3 -m maestro.qwen.main --mode pipe --pipe-path /tmp/qwen_pipe
```

### Example Usage

```python
from maestro.qwen.main import QwenManager

# Create and start a manager
manager = QwenManager()
manager.start(mode='tcp', tcp_port=8080)

# The server will now listen for connections and forward messages
# to the Qwen service

# Stop when done
manager.stop()
```

## Protocol

The server implements a JSON-based protocol for communication:

### Server to Client (Messages from Qwen service)
- `init`: Initialization message with version, workspace, and model info
- `conversation`: User or assistant messages
- `tool_group`: Tool execution requests and results
- `status`: Status updates (idle, responding, waiting for confirmation)
- `info`: Informational messages
- `error`: Error messages
- `completion_stats`: Token usage statistics

### Client to Server (Commands to Qwen service)
- `user_input`: User input to send to the Qwen service
- `tool_approval`: Approval or rejection of tool execution
- `interrupt`: Interrupt the current operation
- `model_switch`: Switch to a different model

## Dependencies

- Python 3.7+
- Node.js and npm (for the underlying Qwen service)
- The `qwen-code` package (installed via npm)

## Testing

Run the tests with:
```bash
python3 -m maestro.qwen.test_qwen
```
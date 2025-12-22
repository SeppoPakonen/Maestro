# Codex Wrapper for Maestro

This module provides an automated wrapper around the codex CLI application, enabling programmatic interaction with the codex AI system.

## Features

- **Virtual Terminal**: Runs codex in a virtual terminal with 200+ character width for better display
- **Turing Machine**: Implements a state machine to model UI usage patterns
- **Command Handling**: Special handling for commands like `/compact`, `/new`, `/quit`, `/model`
- **Input/Output Parsing**: Separates user prompts from AI responses
- **Tool Usage Detection**: Identifies and extracts tool usage from AI output
- **JSON Encoding**: Encodes all data as JSON for client communication
- **Socket Communication**: Provides Unix domain socket interface for client interaction

## Architecture

The implementation consists of several key components:

- `wrapper.py`: Main wrapper that manages the codex process in a virtual terminal
- `parser.py`: Handles parsing of input prompts, AI outputs, and tool usage
- `client.py`: Example client implementation for interacting with the wrapper
- Turing Machine: State machine to model and track UI usage patterns

## Usage

### Running the Wrapper

```bash
python -m maestro.wrap.codex.wrapper --socket-path /tmp/codex_wrapper.sock --width 240
```

### Using the Client

```bash
python -m maestro.wrap.codex.client --socket-path /tmp/codex_wrapper.sock
```

## State Machine

The Turing machine tracks these states:
- `IDLE`: Waiting for user input
- `PROMPTING`: Capturing user prompt
- `AWAITING_RESPONSE`: Waiting for AI response
- `PROCESSING_TOOLS`: Handling tool usage in AI output
- `COMMAND_MODE`: Processing special commands
- `QUITTING`: Shutting down the application

## Protocol

The wrapper communicates with clients via JSON messages through a Unix domain socket:

- Input: `{"type": "input", "content": "user prompt"}`
- Command: `{"type": "command", "content": "/command"}`
- Status: `{"type": "status"}`

The wrapper responds with structured JSON containing parsed inputs, outputs, and tool usage.

## Dependencies

- `pexpect`: For controlling the codex process in a pseudo-terminal
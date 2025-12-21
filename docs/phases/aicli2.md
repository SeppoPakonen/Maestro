# Phase aicli2: Qwen-Code Baseline Analysis ✅ **[Done]**

- *phase_id*: *aicli2*
- *track*: *AI CLI Live Tool Protocol*
- *track_id*: *ai-cli-protocol*
- *status*: *done*
- *completion*: 100
- *status_summary*: *Baseline analysis complete*
- *status_changed*: *2025-12-21T16:41:54*

## Tasks

### Task aicli2.1: Entry Point Inventory ✅ **[Done]**

- *task_id*: *aicli2-1*
- *priority*: *P0*
- *estimated_hours*: 3
- *status*: *done*
- *status_summary*: *Documented NodeJS/C++ entry points*
- *status_changed*: *2025-12-21T16:32:48*

Identify qwen-code fork entrypoints for the NodeJS CLI runtime and the C++ client.

Expected output: a short list of files/binaries with their roles and call graph notes.

### Task aicli2.2: NodeJS Event Flow Map ✅ **[Done]**

- *task_id*: *aicli2-2*
- *priority*: *P0*
- *estimated_hours*: 4
- *status*: *done*
- *status_summary*: *Mapped non-interactive event flow*
- *status_changed*: *2025-12-21T16:32:52*

Map the NodeJS runtime flow for streaming output, tool events, and session state.

Expected output: a flow diagram (textual) listing hook points and event emitters.

### Task aicli2.3: Tool Event Payload Capture ✅ **[Done]**

- *task_id*: *aicli2-3*
- *priority*: *P0*
- *estimated_hours*: 4
- *status*: *done*
- *status_summary*: *Captured JSON/stream payloads*
- *status_changed*: *2025-12-21T16:32:58*

Extract tool usage event payloads (start/end/updates) and record sample JSON.

Expected output: sample JSON messages and a field list with required/optional tags.

### Task aicli2.4: C++ Transport and Framing ✅ **[Done]**

- *task_id*: *aicli2-4*
- *priority*: *P0*
- *estimated_hours*: 4
- *status*: *done*
- *status_summary*: *Documented C++ transport/framing*
- *status_changed*: *2025-12-21T16:38:46*

Inspect the C++ client transport mechanism and framing rules.

Expected output: transport type (TCP/stdio), framing details, and handshake steps.

### Task aicli2.5: Input Injection Path ✅ **[Done]**

- *task_id*: *aicli2-5*
- *priority*: *P0*
- *estimated_hours*: 3
- *status*: *done*
- *status_summary*: *Documented input injection path*
- *status_changed*: *2025-12-21T16:38:52*

Trace how the client injects user input into active sessions.

Expected output: message type(s), required fields, and timing constraints.

### Task aicli2.6: As-Is Protocol Map ✅ **[Done]**

- *task_id*: *aicli2-6*
- *priority*: *P0*
- *estimated_hours*: 3
- *status*: *done*
- *status_summary*: *Added as-is protocol map*
- *status_changed*: *2025-12-21T16:41:31*

Consolidate findings into an "as-is" protocol map for qwen-code.

Expected output: a message catalog with types, directions, and example payloads.

### Task aicli2.7: Uniform Protocol Gap Review ✅ **[Done]**

- *task_id*: *aicli2-7*
- *priority*: *P0*
- *estimated_hours*: 3
- *status*: *done*
- *status_summary*: *Logged evidence-based protocol gaps*
- *status_changed*: *2025-12-21T16:41:37*

Compare qwen-code behavior to the desired uniform protocol and list gaps.

Expected output: a change list with recommended adjustments for qwen-code alignment.

## Notes

### NodeJS TCP server (structured server mode)

- **Location**: `external/ai-agents/qwen-code/packages/cli/src/structuredServerMode.ts`
- **Lifecycle**: `TCPServer.start()` creates a `net.Server`, listens on `tcpPort` (default 7777), and stores a single active socket; `stop()` closes client and server.
- **Framing**: newline-delimited JSON; incoming data is buffered until `\n`, then parsed per line.
- **Accepted commands**: `user_input`, `tool_approval`, `interrupt`, `model_switch`; invalid JSON or unknown `type` is logged and dropped.
- **Outbound messages**: serialized `QwenStateMessage` objects (see `external/ai-agents/qwen-code/packages/cli/src/qwenStateSerializer.ts`) written as JSON + `\n`.
- **Gaps**: single-client only (new connection overwrites previous); no backpressure handling or buffer size limits; no heartbeat/ping for liveness.

### Entry points (NodeJS CLI + C++ client)

- **NodeJS CLI bin**: `packages/cli/package.json` declares `qwen` -> `dist/index.js` (compiled entry).
- **Interactive UI source**: `external/ai-agents/qwen-code/packages/cli/src/gemini.tsx` wires Ink UI and initialization.
- **Non-interactive runtime**: `external/ai-agents/qwen-code/packages/cli/src/nonInteractiveCli.ts` handles JSON/STREAM_JSON request/response flow.
- **Structured server**: `external/ai-agents/qwen-code/packages/cli/src/structuredServerMode.ts` exposes TCP server that wraps `runNonInteractive`.
- **C++ entry**: `external/ai-agents/qwen-code/uppsrc/Qwen/QwenMain.cpp` defines `CONSOLE_APP_MAIN` and calls `QwenCmd::cmd_qwen`.
- **C++ CLI args**: `external/ai-agents/qwen-code/uppsrc/Qwen/CmdQwen.cpp` parses flags like `--server-mode`, `--tcp-port`, `--attach`, `--new`, `--manager`, `--yolo`.

### NodeJS non-interactive event flow (JSON/STREAM_JSON)

- `runNonInteractive()` selects output adapter by `OutputFormat` and emits a system message.
- It sends the initial user content to `geminiClient.sendMessageStream()` and calls `adapter.startAssistantMessage()`.
- For each stream event, `adapter.processEvent()` updates content blocks and collects `ToolCallRequestInfo`.
- After stream ends, `adapter.finalizeAssistantMessage()` emits the assistant message.
- If tool calls exist: `executeToolCall()` runs each tool, `adapter.emitToolResult()` emits tool_result messages, and tool response parts are fed back into the next loop.
- If no tool calls: `adapter.emitResult()` emits a final result message and returns.
- In structured server mode, `TCPServer.handleMessage()` parses newline JSON, and uses `StreamJsonOutputAdapter` with partial messages enabled to send responses via `sendResponse()`.

### Tool event payloads (stdout JSON/STREAM_JSON)

- **JSON mode**: `JsonOutputAdapter` collects `CLIMessage[]` and emits one JSON array at end of turn.
- **STREAM_JSON mode**: `StreamJsonOutputAdapter` emits each `CLIMessage` as a JSON line immediately, plus `stream_event` messages.
- **Assistant message** (type `assistant`): includes `message.id`, `message.role`, `message.model`, `message.content[]` and `usage`; `stop_reason` may be present.
- **Tool result** (type `user` with `tool_result` block): `tool_use_id`, `content` optional, `is_error` optional.
- **Stream events** (type `stream_event`): include `event.type` of `message_start`, `content_block_start`, `content_block_delta`, `content_block_stop`, or `message_stop`; once message has started, `message_id` is added to the event payload.
- **Result** (type `result`): `subtype`, `is_error`, durations, `num_turns`, `usage`, optional `error` object, and `permission_denials`.

Example assistant message:
```json
{
  "type": "assistant",
  "uuid": "uuid",
  "session_id": "session",
  "parent_tool_use_id": null,
  "message": {
    "id": "msg-id",
    "type": "message",
    "role": "assistant",
    "model": "model-name",
    "content": [{ "type": "text", "text": "..." }],
    "usage": { "input_tokens": 0, "output_tokens": 0 }
  }
}
```

Example tool result message:
```json
{
  "type": "user",
  "uuid": "uuid",
  "session_id": "session",
  "parent_tool_use_id": null,
  "message": {
    "role": "user",
    "content": [
      { "type": "tool_result", "tool_use_id": "call-id", "is_error": false }
    ]
  }
}
```

Example stream event (content block delta):
```json
{
  "type": "stream_event",
  "uuid": "uuid",
  "session_id": "session",
  "parent_tool_use_id": null,
  "event": {
    "type": "content_block_delta",
    "index": 0,
    "delta": { "type": "text_delta", "text": "chunk" },
    "message_id": "msg-id"
  }
}
```

Example result message:
```json
{
  "type": "result",
  "subtype": "success",
  "uuid": "uuid",
  "session_id": "session",
  "is_error": false,
  "duration_ms": 1234,
  "duration_api_ms": 1000,
  "num_turns": 1,
  "result": "summary text",
  "usage": { "input_tokens": 0, "output_tokens": 0 },
  "permission_denials": []
}
```

### C++ transport + framing (uppsrc/Qwen)

- **Transports**: `STDIN_STDOUT` (subprocess pipes) and `TCP` socket are implemented; `NAMED_PIPE` is defined but not implemented (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenClient.h`, `external/ai-agents/qwen-code/uppsrc/Qwen/QwenClient.cpp`).
- **Subprocess mode**: forks a child, execs `qwen` with `--server-mode stdin`, and wires stdin/stdout pipes; stderr redirected to `/dev/null` unless verbose (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenClient.cpp`).
- **TCP mode**: connects to `tcp_host`/`tcp_port` (defaults `localhost:8765`) and uses the socket for both reads and writes (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenClient.h`, `external/ai-agents/qwen-code/uppsrc/Qwen/QwenClient.cpp`).
- **Framing**: newline-delimited JSON; sender appends `\n`, receiver buffers and splits on `\n` (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenClient.cpp`).
- **Server wrapper**: `QwenTCPServer` spawns a `QwenClient` in `STDIN_STDOUT` mode and also accepts TCP clients that send newline JSON (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenTCPServer.cpp`).

### C++ input injection path (user + tool approval + model switch)

- **User input**: `QwenClient::send_user_input()` -> `ProtocolParser::create_user_input()` -> `serialize_command()` -> write JSON + `\n` to stdin/socket (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenClient.cpp`, `external/ai-agents/qwen-code/uppsrc/Qwen/QwenProtocol.cpp`).
- **Tool approval**: `send_tool_approval(tool_id, approved)` emits `{ "type":"tool_approval", "tool_id":"...", "approved":true|false }` (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenProtocol.cpp`).
- **Model switch**: `send_model_switch(model_id)` emits `{ "type":"model_switch", "model_id":"..." }` (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenProtocol.cpp`).
- **Interrupt**: `send_interrupt()` emits `{ "type":"interrupt" }` (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenProtocol.cpp`).
- **TCP server entry**: `QwenTCPServer::handle_client_message()` accepts `type` of `user_input` and `tool_approval` from TCP clients and forwards via `QwenClient` (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenTCPServer.cpp`).

### As-is protocol map (message catalog)

- **NodeJS structured server (TCP, newline JSON)**: accepts `CLIMessage` payloads with `type` of `user`, `control_request`, or `control_response`; runs `runNonInteractive()` and sends back `CLIMessage` or `CLIControlResponse` as JSON lines (`external/ai-agents/qwen-code/packages/cli/src/structuredServerMode.ts`, `external/ai-agents/qwen-code/packages/cli/src/nonInteractive/types.ts`).
- **NodeJS non-interactive stdout (JSON array)**: outputs `[CLIMessage...]` at end of turn; common sequence: `system` -> `assistant` -> `user` (tool_result) -> `result` (`external/ai-agents/qwen-code/packages/cli/src/nonInteractive/io/JsonOutputAdapter.ts`, `external/ai-agents/qwen-code/packages/cli/src/nonInteractive/types.ts`).
- **NodeJS non-interactive stdout (STREAM_JSON)**: emits each `CLIMessage` line as it becomes available; also emits `stream_event` messages for `message_start`, `content_block_start`, `content_block_delta`, `content_block_stop`, `message_stop` (`external/ai-agents/qwen-code/packages/cli/src/nonInteractive/io/StreamJsonOutputAdapter.ts`, `external/ai-agents/qwen-code/packages/cli/src/nonInteractive/types.ts`).
- **C++ client commands (stdin/stdout or TCP, newline JSON)**: `user_input` (content), `tool_approval` (tool_id, approved), `interrupt`, `model_switch` (model_id) (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenProtocol.cpp`).
- **C++ client responses (newline JSON)**: `init`, `conversation` (role, content, id, isStreaming), `tool_group` (id, tools[]), `status` (state, message?, thought?), `info`, `error`, `completion_stats` (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenProtocol.h`, `external/ai-agents/qwen-code/uppsrc/Qwen/QwenProtocol.cpp`).
- **C++ TCP server**: accepts TCP client messages `{ "type":"user_input", "content":"..." }` and `{ "type":"tool_approval", "tool_id":"...", "approved":true|false }`, forwards via `QwenClient` (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenTCPServer.cpp`).

### Uniform protocol gap review (evidence-based)

- **Structured server single-client**: NodeJS `TCPServer` stores one active socket; new connections overwrite previous (`external/ai-agents/qwen-code/packages/cli/src/structuredServerMode.ts`).
- **No backpressure/limits**: NodeJS server and C++ client buffer newline data without size limits; no backpressure or max message size enforcement (`external/ai-agents/qwen-code/packages/cli/src/structuredServerMode.ts`, `external/ai-agents/qwen-code/uppsrc/Qwen/QwenClient.cpp`).
- **C++ named-pipe mode missing**: `NAMED_PIPE` exists in config but returns not implemented (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenClient.h`, `external/ai-agents/qwen-code/uppsrc/Qwen/QwenClient.cpp`).
- **Protocol mismatch (NodeJS vs C++)**: NodeJS structured server expects `CLIMessage` (`user`, `control_request`, `control_response`) while the C++ TCP server expects `user_input`/`tool_approval` and the C++ client expects `init`/`conversation`/`tool_group`/`status` response shapes; these are different wire formats with no explicit translation layer in the snippets.
- **Unsupported commands in C++ TCP server**: `interrupt` and `model_switch` are defined in C++ protocol but not handled by `QwenTCPServer::handle_client_message()` (`external/ai-agents/qwen-code/uppsrc/Qwen/QwenTCPServer.cpp`).
- **Uniform protocol alignment**: deeper gaps (required ids, timestamps, error schemas, reliability rules) are blocked until `aicli3` defines the uniform protocol spec.

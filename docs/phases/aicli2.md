# Phase aicli2: Qwen-Code Baseline Analysis

- *phase_id*: *aicli2*
- *track*: *AI CLI Live Tool Protocol*
- *track_id*: *ai-cli-protocol*
- *status*: *planned*
- *completion*: 0

## Tasks

### Task aicli2.1: Entry Point Inventory

- *task_id*: *aicli2-1*
- *priority*: *P0*
- *estimated_hours*: 3

Identify qwen-code fork entrypoints for the NodeJS CLI runtime and the C++ client.

Expected output: a short list of files/binaries with their roles and call graph notes.

### Task aicli2.2: NodeJS Event Flow Map

- *task_id*: *aicli2-2*
- *priority*: *P0*
- *estimated_hours*: 4

Map the NodeJS runtime flow for streaming output, tool events, and session state.

Expected output: a flow diagram (textual) listing hook points and event emitters.

### Task aicli2.3: Tool Event Payload Capture

- *task_id*: *aicli2-3*
- *priority*: *P0*
- *estimated_hours*: 4

Extract tool usage event payloads (start/end/updates) and record sample JSON.

Expected output: sample JSON messages and a field list with required/optional tags.

### Task aicli2.4: C++ Transport and Framing

- *task_id*: *aicli2-4*
- *priority*: *P0*
- *estimated_hours*: 4

Inspect the C++ client transport mechanism and framing rules.

Expected output: transport type (TCP/stdio), framing details, and handshake steps.

### Task aicli2.5: Input Injection Path

- *task_id*: *aicli2-5*
- *priority*: *P0*
- *estimated_hours*: 3

Trace how the client injects user input into active sessions.

Expected output: message type(s), required fields, and timing constraints.

### Task aicli2.6: As-Is Protocol Map

- *task_id*: *aicli2-6*
- *priority*: *P0*
- *estimated_hours*: 3

Consolidate findings into an "as-is" protocol map for qwen-code.

Expected output: a message catalog with types, directions, and example payloads.

### Task aicli2.7: Uniform Protocol Gap Review

- *task_id*: *aicli2-7*
- *priority*: *P0*
- *estimated_hours*: 3

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

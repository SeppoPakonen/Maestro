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

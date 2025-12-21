# Phase aicli3: Protocol & TCP Server Spec ✅ **[Done]**

- *phase_id*: *aicli3*
- *track*: *AI CLI Live Tool Protocol*
- *track_id*: *ai-cli-protocol*
- *status*: *done*
- *completion*: 100
- *status_summary*: *Protocol spec draft complete*
- *status_changed*: *2025-12-21T16:46:12*

## Tasks

### Task aicli3.1: Protocol Goals and Constraints ✅ **[Done]**

- *task_id*: *aicli3-1*
- *priority*: *P0*
- *estimated_hours*: 2
- *status*: *done*
- *status_summary*: *Drafted protocol goals/constraints*
- *status_changed*: *2025-12-21T16:45:45*

Define the uniform JSON protocol goals before any agent implementation.

- [ ] Document required message types (tool, output, input, status, error)
- [ ] Define required fields and correlations (ids, timestamps, session ids)
- [ ] Capture non-goals or deferred features

### Task aicli3.2: Message Framing and Reliability ✅ **[Done]**

- *task_id*: *aicli3-2*
- *priority*: *P0*
- *estimated_hours*: 3
- *status*: *done*
- *status_summary*: *Defined framing and reliability rules*
- *status_changed*: *2025-12-21T16:45:51*

Define message framing, backpressure, and error handling for the protocol.

- [ ] Frame format (newline JSON vs length-prefix)
- [ ] Error response schema
- [ ] Connection drop/retry behavior

### Task aicli3.3: Agent-Side Capability Contract ✅ **[Done]**

- *task_id*: *aicli3-3*
- *priority*: *P0*
- *estimated_hours*: 3
- *status*: *done*
- *status_summary*: *Captured agent capability contract*
- *status_changed*: *2025-12-21T16:46:00*

Document required agent-side hooks and emission points.

- [ ] Tool event capture points
- [ ] Output streaming boundaries
- [ ] Input injection entry points

### Task aicli3.4: Qwen-Code Alignment Plan ✅ **[Done]**

- *task_id*: *aicli3-4*
- *priority*: *P0*
- *estimated_hours*: 3
- *status*: *done*
- *status_summary*: *Outlined qwen-code alignment plan*
- *status_changed*: *2025-12-21T16:46:05*

Plan qwen-code adjustments needed to align with the uniform protocol.

- [ ] List protocol mismatches
- [ ] Propose minimal changes to C++ client and Node runtime
- [ ] Decide on compatibility fallbacks

## Notes

### Protocol goals and constraints

- **Goal**: single uniform JSON protocol across agents that supports streaming, tool calls, and control signals with consistent envelopes and IDs.
- **Goal**: allow transports over TCP and stdio without changing message shapes.
- **Goal**: make tool events first-class (start/update/end) with explicit correlation IDs.
- **Constraint**: messages must be line-delimited JSON for streaming simplicity and human inspection.
- **Constraint**: keep payloads ASCII-safe and backward-compatible where feasible.
- **Non-goal**: UI rendering schema, provider-specific auth/config, or agent-internal prompt formats.

### Message framing and reliability

- **Frame format**: newline-delimited JSON per message; reject frames exceeding a max size and emit an error message.
- **Correlation**: require `session_id` + `message_id` + `tool_use_id` in envelopes that carry tool or stream events.
- **Error schema**: standard `error` message type with machine-readable code + human message.
- **Connection handling**: define server-side behavior for disconnects (drain, retry policy, or session termination).
- **Backpressure**: mandate bounded buffers and expose a `slow_consumer` error when limits are exceeded.

### Agent-side capability contract

- **Input injection**: `user_input`, `tool_approval`, `interrupt`, `model_switch` supported at minimum.
- **Output streaming**: `message_start`, content deltas, and `message_stop` boundaries.
- **Tool events**: `tool_call_start`, `tool_call_update`, `tool_call_result` with shared IDs.
- **Status**: `status` updates for `idle/responding/waiting` and optional `thought`/`message` fields.

### Qwen-code alignment plan (based on aicli2 gaps)

- Add a translation layer between NodeJS `CLIMessage` shapes and C++ protocol fields, or converge both on the uniform envelope.
- Extend Qwen TCP server to accept `interrupt` and `model_switch` commands.
- Implement backpressure + max frame size limits in NodeJS structured server and C++ client readers.
- Decide on single-client vs multi-client behavior; if single-client, reject new connections with an error frame.

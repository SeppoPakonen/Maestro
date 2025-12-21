# Phase aicli4: Validation & Testing 🚧 **[In Progress]**

- *phase_id*: *aicli4*
- *track*: *AI CLI Live Tool Protocol*
- *track_id*: *ai-cli-protocol*
- *status*: *in_progress*
- *completion*: 25
- *status_changed*: *2025-12-21T16:57:40*
- *status_summary*: *Started validation planning*

## Tasks

### Task aicli4.1: Protocol Test Plan ✅ **[Done]**

- *task_id*: *aicli4-1*
- *priority*: *P1*
- *estimated_hours*: 2
- *status*: *done*
- *status_summary*: *Documented test plan and success criteria*
- *status_changed*: *2025-12-21T16:56:54*

Create a test plan for live tool events and input injection.

- [x] Define success criteria for tool event capture
- [x] Define success criteria for input injection timing
- [x] Identify expected failure modes and error payloads

### Task aicli4.2: Maestro Qwen Chat Validation

- *task_id*: *aicli4-2*
- *priority*: *P1*
- *estimated_hours*: 3

Test with `maestro qwen chat` (or equivalent) using live tool events.

- [ ] Capture example session transcript
- [ ] Verify tool_start/tool_end appear with ids and payloads
- [ ] Confirm JSON framing is valid and ordered

### Task aicli4.3: Input Injection Validation

- *task_id*: *aicli4-3*
- *priority*: *P1*
- *estimated_hours*: 3

Validate input injection during active sessions.

- [ ] Inject input mid-stream and verify handling
- [ ] Confirm acknowledgement or error messages

### Task aicli4.4: End-to-End Smoke Test

- *task_id*: *aicli4-4*
- *priority*: *P1*
- *estimated_hours*: 2

Run a smoke test that exercises tool events + input injection in one session.

- [ ] Record a minimal test script or command sequence
- [ ] Capture expected JSON message flow

## Notes

### Execution blockers

- `external/ai-agents/qwen-code/bin/Qwen --help` fails with "CPU ISA level is lower than required" on this host.
- NodeJS CLI bundle now built at `external/ai-agents/qwen-code/packages/cli/dist`, but live tool validation still needs working auth + model access.
- `node external/ai-agents/qwen-code/packages/cli/dist/index.js --output-format stream-json --prompt "hello"` emits init then aborts with `OpenAI API Streaming Error: Request was aborted`, so tool events and content streaming cannot be validated without auth.

### Test plan

1. Verify live tool events emit proper JSON frames with `message_id`, `tool_use_id`, and correct event types (`tool_call_start`, `tool_call_update`, `tool_call_result`)
2. Validate input injection handles `user_input`, `tool_approval`, `interrupt`, `model_switch` with appropriate ack/error responses
3. Confirm message framing order: `message_start` -> `content_delta` -> `message_stop` for each message sequence
4. Test backpressure detection with `slow_consumer` error emission during rapid frame transmission
5. Validate frame size limits trigger proper error messages on oversized inputs
6. Ensure tool results contain `output` fields with `tool_use_id` correlation
7. Verify error messages include `session_id`, `error_code`, and human-readable `message`

### Qwen chat validation

Step-by-step validation for Maestro `qwen chat` integration:

1. Start `maestro qwen chat` with live tool protocol enabled.
2. Issue a tool request and capture the JSON transcript.
3. Verify `tool_call_start` appears with payload and `tool_use_id`.
4. Check `tool_call_update` or intermediate tool status updates with `tool_use_id` correlation.
5. Confirm `tool_call_result` with final payload and timing information.

Example JSON snippet for tool start event:
```json
{"session_id": "sess_abc123", "message_id": "msg_def456", "tool_use_id": "tool_789", "type": "tool_call_start", "name": "execute_command", "arguments": {"cmd": "ls -la"}}
```

Expected tool result response:
```json
{"session_id": "sess_abc123", "message_id": "msg_def456", "tool_use_id": "tool_789", "type": "tool_call_result", "output": {"stdout": "...", "stderr": "", "exit_code": 0}}
```

### Input injection validation

Steps to validate input injection capabilities:

1. Initiate a streaming session with ongoing tool execution.
2. Inject `user_input` mid-stream and verify immediate processing.
3. Submit `tool_approval` and confirm the tool continues execution.
4. Trigger `interrupt` and verify graceful tool termination.
5. Switch model mid-session and confirm the session resumes with new model metadata.

Expected injection acknowledgment:
```json
{"session_id": "sess_abc123", "message_id": "inj_111", "type": "status", "status": "ack", "request_type": "user_input"}
```

Expected error response for invalid injection:
```json
{"session_id": "sess_abc123", "message_id": "err_222", "type": "error", "error_code": "INVALID_STATE", "message": "Injection not allowed in current state"}
```

### End-to-end smoke test

Minimal command sequence for validation:
```bash
maestro qwen chat --live-tools --session-id test_session
# Send: {"prompt": "Show me files in current directory"}
# Expect: message_start -> tool_call_start -> tool_call_result -> message_stop
```

Expected JSON message flow:
```json
{"session_id": "test_session", "message_id": "start_1", "type": "message_start", "role": "assistant"}
{"session_id": "test_session", "message_id": "delta_2", "type": "content_delta", "content": "...thinking..."}
{"session_id": "test_session", "message_id": "tool_3", "tool_use_id": "exec_4", "type": "tool_call_start", "name": "execute_command", "arguments": {"cmd": "ls"}}
{"session_id": "test_session", "message_id": "result_5", "tool_use_id": "exec_4", "type": "tool_call_result", "output": {"stdout": "file1.txt\nfile2.txt"}}
{"session_id": "test_session", "message_id": "stop_6", "type": "message_stop", "stop_reason": "tool_use"}
```

# Phase aicli7: Integration Implementation 📋 **[Planned]**

- *phase_id*: *aicli7*
- *track*: *AI CLI Live Tool Protocol*
- *track_id*: *ai-cli-protocol*
- *status*: *planned*
- *completion*: 0

## Tasks

### Task aicli7.1: Shared Messaging Helpers

- *task_id*: *aicli7-1*
- *priority*: *P0*
- *estimated_hours*: 4

Implement shared NodeJS helpers for protocol messaging and tool events.

- [ ] Create JSON message builder with required fields
- [ ] Add framing encoder/decoder for chosen transport
- [ ] Add tool event emit helper (start/update/end)

### Task aicli7.2: Qwen-Code Alignment Changes

- *task_id*: *aicli7-2*
- *priority*: *P0*
- *estimated_hours*: 4

Apply protocol alignment changes to qwen-code if required.

- [ ] Update Node CLI emission to match uniform schema
- [ ] Update C++ client framing or message fields if needed
- [ ] Validate backward compatibility strategy

### Task aicli7.3: Codex Integration

- *task_id*: *aicli7-3*
- *priority*: *P0*
- *estimated_hours*: 4

Integrate Codex CLI with the TCP protocol and tool events.

- [ ] Wire tool event hooks to protocol emitter
- [ ] Add input injection handler
- [ ] Add session registration handshake

### Task aicli7.4: Claude-Code Integration

- *task_id*: *aicli7-4*
- *priority*: *P0*
- *estimated_hours*: 4

Integrate Claude-Code CLI with the TCP protocol and tool events.

- [ ] Wire tool event hooks to protocol emitter
- [ ] Add input injection handler
- [ ] Add session registration handshake

### Task aicli7.5: Copilot-CLI Integration

- *task_id*: *aicli7-5*
- *priority*: *P1*
- *estimated_hours*: 4

Integrate Copilot-CLI with the TCP protocol and tool events.

- [ ] Wire tool event hooks to protocol emitter
- [ ] Add input injection handler
- [ ] Add session registration handshake

### Task aicli7.6: Gemini-CLI Integration

- *task_id*: *aicli7-6*
- *priority*: *P1*
- *estimated_hours*: 4

Integrate Gemini-CLI with the TCP protocol and tool events.

- [ ] Wire tool event hooks to protocol emitter
- [ ] Add input injection handler
- [ ] Add session registration handshake

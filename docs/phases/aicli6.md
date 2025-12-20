# Phase aicli6: TCP Server Design 📋 **[Planned]**

- *phase_id*: *aicli6*
- *track*: *AI CLI Live Tool Protocol*
- *track_id*: *ai-cli-protocol*
- *status*: *planned*
- *completion*: 0

## Tasks

### Task aicli6.1: Server API Surface

- *task_id*: *aicli6-1*
- *priority*: *P0*
- *estimated_hours*: 3

Define the TCP server public API and lifecycle.

- [ ] Define connection roles (agent vs client)
- [ ] Define handshake and session registration payloads
- [ ] Define auth or shared-secret requirements (if any)

### Task aicli6.2: Session Routing Model

- *task_id*: *aicli6-2*
- *priority*: *P0*
- *estimated_hours*: 3

Specify how sessions are tracked and events are routed.

- [ ] Session identity rules and storage
- [ ] Multi-subscriber fan-out semantics
- [ ] Input injection routing constraints

### Task aicli6.3: Transport & Framing Details

- *task_id*: *aicli6-3*
- *priority*: *P0*
- *estimated_hours*: 3

Define framing and backpressure strategy for TCP transport.

- [ ] Message framing choice and rationale
- [ ] Maximum message size and truncation rules
- [ ] Backpressure strategy and buffer limits

### Task aicli6.4: Error and Disconnect Handling

- *task_id*: *aicli6-4*
- *priority*: *P1*
- *estimated_hours*: 2

Define error handling and reconnection behavior.

- [ ] Error response schema and error codes
- [ ] Disconnect recovery rules
- [ ] Logging and diagnostics expectations

# Phase aicli3: Protocol & TCP Server Spec ✅ **[Done]**

- *phase_id*: *aicli3*
- *track*: *AI CLI Live Tool Protocol*
- *track_id*: *ai-cli-protocol*
- *status*: *done*
- *completion*: 100

## Tasks

### Task aicli3.1: Protocol Goals and Constraints

- *task_id*: *aicli3-1*
- *priority*: *P0*
- *estimated_hours*: 2

Define the uniform JSON protocol goals before any agent implementation.

- [ ] Document required message types (tool, output, input, status, error)
- [ ] Define required fields and correlations (ids, timestamps, session ids)
- [ ] Capture non-goals or deferred features

### Task aicli3.2: Message Framing and Reliability

- *task_id*: *aicli3-2*
- *priority*: *P0*
- *estimated_hours*: 3

Define message framing, backpressure, and error handling for the protocol.

- [ ] Frame format (newline JSON vs length-prefix)
- [ ] Error response schema
- [ ] Connection drop/retry behavior

### Task aicli3.3: Agent-Side Capability Contract

- *task_id*: *aicli3-3*
- *priority*: *P0*
- *estimated_hours*: 3

Document required agent-side hooks and emission points.

- [ ] Tool event capture points
- [ ] Output streaming boundaries
- [ ] Input injection entry points

### Task aicli3.4: Qwen-Code Alignment Plan

- *task_id*: *aicli3-4*
- *priority*: *P0*
- *estimated_hours*: 3

Plan qwen-code adjustments needed to align with the uniform protocol.

- [ ] List protocol mismatches
- [ ] Propose minimal changes to C++ client and Node runtime
- [ ] Decide on compatibility fallbacks

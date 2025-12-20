# Phase aicli8: End-to-End Testing 📋 **[Planned]**

- *phase_id*: *aicli8*
- *track*: *AI CLI Live Tool Protocol*
- *track_id*: *ai-cli-protocol*
- *status*: *planned*
- *completion*: 0

## Tasks

### Task aicli8.1: Cross-Agent Smoke Tests

- *task_id*: *aicli8-1*
- *priority*: *P1*
- *estimated_hours*: 3

Run smoke tests across all integrated agents.

- [ ] Verify tool event capture for each agent
- [ ] Validate input injection during active tool runs
- [ ] Confirm JSON framing and ordering

### Task aicli8.2: Protocol Conformance Checklist

- *task_id*: *aicli8-2*
- *priority*: *P1*
- *estimated_hours*: 3

Check all agents against the uniform protocol spec.

- [ ] Required fields present for all message types
- [ ] Correlation ids match tool lifecycles
- [ ] Error payloads conform to schema

### Task aicli8.3: Maestro Integration Validation

- *task_id*: *aicli8-3*
- *priority*: *P1*
- *estimated_hours*: 3

Validate Maestro workflows (e.g., `maestro qwen chat`) with live tool events.

- [ ] Confirm live tool event display
- [ ] Confirm input injection prompts
- [ ] Record known limitations

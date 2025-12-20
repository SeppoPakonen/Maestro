# Phase ce4: CLI Help Navigation 📋 **[Planned]**

- *phase_id*: *ce4*
- *track*: *CLI Editing*
- *track_id*: *cli-editing*
- *status*: *planned*
- *completion*: 0

## Tasks

### Task ce4.1: Help-only navigation runbook

- *task_id*: *ce4.1*
- *priority*: *P2*
- *status*: *planned*

- Document help-driven flows
- Use python maestro.py only


### Task ce4.2: Validate help messages

- *task_id*: *ce4.2*
- *priority*: *P2*
- *status*: *planned*

- Ensure task/phase/track help is discoverable
- Verify alias routing

### Task ce4.3: CLI-only walkthrough

- *task_id*: *ce4.3*
- *priority*: *P2*
- *status*: *planned*

- Add example flows using python maestro.py
- Confirm commands without m wrapper

## Help-Driven Walkthrough

- Start with `python maestro.py help`
- Follow to `python maestro.py track help`
- Navigate into `python maestro.py track cli-editing list`
- Drill into phases with `python maestro.py phase list cli-editing`
- Review tasks with `python maestro.py task list ce4`
- Edit a block with `python maestro.py phase edit ce4`

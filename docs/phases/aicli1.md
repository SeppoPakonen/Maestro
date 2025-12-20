# Phase aicli1: Submodules & Repo Wiring 📋 **[Planned]**

- *phase_id*: *aicli1*
- *track*: *AI CLI Live Tool Protocol*
- *track_id*: *ai-cli-protocol*
- *status*: *planned*
- *completion*: 0

## Tasks

### Task aicli1.1: Submodule Layout

- *task_id*: *aicli1-1*
- *priority*: *P1*
- *estimated_hours*: 2

Ensure AI agent forks are added as git submodules under `external/ai-agents/`.

- [ ] Verify submodule paths and URLs in `.gitmodules`
- [ ] Confirm each submodule folder exists and is clean
- [ ] Record expected directory tree for future checks

### Task aicli1.2: README Submodule Instructions

- *task_id*: *aicli1-2*
- *priority*: *P1*
- *estimated_hours*: 1

Document submodule cloning and initialization steps in `README.md`.

- [ ] Add clone instructions with `--recurse-submodules`
- [ ] Add post-clone `git submodule update --init --recursive`
- [ ] List submodule paths for discoverability

### Task aicli1.3: Repo Reference Hygiene

- *task_id*: *aicli1-3*
- *priority*: *P2*
- *estimated_hours*: 1

Ensure repo docs reference the correct submodule locations and naming.

- [ ] Scan for any stale paths (old locations or names)
- [ ] Update any internal docs referencing agent repo locations

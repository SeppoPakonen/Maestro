# Maestro AI Agents

This document contains instructions for all AI agents working with the Maestro project.

## Agent Policy Requirements

### Mandatory Task Lifecycle Rule

At the **end of a Phase**, the agent must:

1. Mark completed tasks as done in the JSON store
2. Preserve Phase structure and numbering
3. Never leave completed tasks marked as todo

This rule ensures the task tracking system remains accurate and up-to-date.

### Phase ID Policy

- Phase IDs must be non-numeric and should include a track prefix (e.g., `umk1`).

### Engine Enablement and Stacking Mode

When producing plans, agents must respect the engine enablement matrix and stacking mode:

- Engine enablement: Only use engines that are enabled for the required role (planner/worker)
- Stacking mode: In managed mode, return structured JSON plans; in handsoff mode, may include more direct instructions

## Repo Layout Notes

- AI agent forks are maintained as git submodules under `external/ai-agents/`.
- When working on agent CLI changes, keep updates inside their submodule directories.

## Track/Phase/Task Format

- Tracks live in `docs/maestro/tracks/*.json`.
- Phases live in `docs/maestro/phases/*.json` and include `phase_id`, `track`, and task references.
- Tasks live in `docs/maestro/tasks/*.json` and include `task_id`, priority, and estimates.
- Prefer using `python maestro.py track/phase/task` (or `~/bin/m`) to add/edit tracks, phases, and tasks.

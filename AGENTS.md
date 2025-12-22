# Maestro AI Agents

This document contains instructions for all AI agents working with the Maestro project.

## Agent Policy Requirements

### Mandatory Task Lifecycle Rule

At the **end of a Phase**, the agent must:

1. Move completed tasks from `docs/todo.md`
2. Into `docs/done.md`
3. Preserve Phase structure and numbering
4. Never leave completed tasks in `todo.md`

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

- Tracks live in `docs/todo.md` (and completed items in `docs/done.md`) with markdown metadata blocks.
- Phases live in `docs/phases/<phase_id>.md` and include `phase_id`, `track`, and task sections.
- Tasks are listed inside phase files and should include `task_id`, priority, and estimates.
- Prefer using `python maestro.py track/phase/task` (or `~/bin/m`) to add/edit tracks, phases, and tasks.

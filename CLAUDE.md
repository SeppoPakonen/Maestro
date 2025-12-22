# Maestro CLAUDE Agent Instructions

Instructions for Anthropic Claude when working on the Maestro project.

## Policy Requirements

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

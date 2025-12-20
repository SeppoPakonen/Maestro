# Maestro QWEN Agent Instructions

Instructions for Qwen (you) when working on the Maestro project.

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

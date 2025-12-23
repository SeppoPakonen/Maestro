# Maestro Plan Storage Format

This document describes the canonical Markdown format used by Maestro for storing plans.

## Format Structure

The canonical plan storage file is `docs/plans.md` with the following structure:

```markdown
# Plans

## Plan Title 1

- Plan item 1
- Plan item 2
- Plan item 3

## Plan Title 2

- Another plan item
- Yet another item
```

## Rules

1. The file must start with a top-level heading `# Plans`
2. Each plan is defined with a second-level heading `## Plan Title`
3. Plan items are listed as bullet points under their respective plan
4. Bullet points can use either `- ` or `* ` prefix
5. Plan titles must be unique (case-insensitive comparison)
6. Plan titles cannot be empty
7. Each plan must have a bullet list (even if empty)

## Validation

The PlanStore module enforces the following validation rules:

- No duplicate plan titles (case-insensitive)
- Plan title cannot be empty
- Each plan must contain a bullet list (can be empty)
- If the file is malformed, the system will hard stop with a clear error

## CLI Commands

The following commands are available for managing plans:

### `maestro plan add <title>`
Creates a new plan section with an empty bullet list.

### `maestro plan list`
Prints a numbered list of plan titles.

### `maestro plan remove <title|number>`
Removes the entire plan section.

### `maestro plan <title|number>` (show mode)
Shows the plan and its items as a numbered list.

### `maestro plan show <title|number>`
Same as show mode (explicit listing).

### `maestro plan add-item <title|number> <string>`
Appends a bullet item to the specified plan.

### `maestro plan remove-item <title|number> <item_number>`
Removes the numbered bullet item from the specified plan.

## Selection Rules

- If user passes a number, it's treated as the index from `plan list`
- If user passes a title, it matches exact title (case-insensitive); if not found, shows an error
- Ambiguity is handled deterministically with preference for strictness
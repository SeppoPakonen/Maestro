# Track/Phase/Task Markdown Data Contract

This document defines the contract for storing Track/Phase/Task data in human-readable, machine-parseable Markdown files under `docs/`.

## File Roles

### `docs/todo.md`
- **Purpose**: Top-level index of active tracks and their phases
- **Structure**: Contains track headings with phase references
- **Single source of truth** for active development work

### `docs/phases/*.md`
- **Purpose**: Detailed phase documentation with task lists
- **Structure**: Individual files per phase with tasks and metadata
- **Single source of truth** for phase details and tasks

### `docs/done.md`
- **Purpose**: Archive of completed tracks/phases
- **Structure**: Contains completed items moved from todo.md
- **Single source of truth** for completed work

## Required Headings and Fields

### Track Format
```
## Track: {Track Name}
- *track_id*: *{TR-###}*
- *priority*: {0-10}
- *status*: *{planned|in_progress|done|proposed}*
- *completion*: {0-100}%

Optional description text...
```

### Phase Format
```
### Phase {PH-###}: {Phase Name}
- *phase_id*: *{PH-###}*
- *track_id*: *{TR-###}*
- *status*: *{planned|in_progress|done|proposed}*
- *completion*: {0-100}%
- *order*: {integer}

Optional description text...
```

### Task Format
```
### Task {TS-####}: {Task Name}
- *task_id*: *{TS-####}*
- *phase_id*: *{PH-###}*
- *status*: *{todo|in_progress|done|blocked}*
- *priority*: *{P1|P2|P3|P4}*
- *estimated_hours*: {number}

Optional description text...
```

## Allowed List Syntaxes

### Checkbox Tasks (in phase files)
- **Open task**: `- [ ] **{TS-####}: {Task Name}**`
- **Completed task**: `- [x] **{TS-####}: {Task Name}**`
- **Nested subtasks**: `  - [ ] {Subtask description}`

## Stable ID Rules

### Track ID Format: `TR-###`
- Must start with "TR-"
- Followed by 3-4 digits
- Examples: TR-001, TR-1234

### Phase ID Format: `PH-###`
- Must start with "PH-"
- Followed by 3-4 digits
- Examples: PH-001, PH-1234

### Task ID Format: `TS-####`
- Must start with "TS-"
- Followed by 4-5 digits
- Examples: TS-0001, TS-12345

## Field Format

### Key-Value Pairs
- Format: `- *key*: *value*`
- Keys and values must be wrapped in asterisks
- Examples:
  - `- *status*: *planned*`
  - `- *priority*: *P2*`
  - `- *estimated_hours*: *8*`

## Forbidden Constructs

### Parsing will fail if:
- IDs are missing or malformed
- Duplicate IDs exist within the same scope
- Checkbox syntax is invalid (`- []` instead of `- [ ]` or `- [x]`)
- Required metadata fields are missing
- Header structure is broken (missing required fields)
- Non-standard formatting breaks parsing

## Style Policy

### User formatting is allowed but ignored by parser:
- Bold/italic text: `**bold**`, `*italic*`
- Emphasis: `***emphasis***`
- Code blocks: `` `code` ``
- Links: `[text](url)`
- Lists: `- item`, `1. item`

### Parser behavior:
- Strips formatting before parsing
- Preserves formatting in output
- Only processes semantic content

## Validation Rules

### Parsing errors stop execution with actionable messages:
- File path and line number
- Specific error description
- Suggested fix

### Validation checks:
- ID format compliance
- Required field presence
- Reference integrity (phase in todo.md has corresponding file)
- Status value validity
- Numeric field bounds

## Order and Sorting

### Default sorting:
- Always sort by ID unless `Order:` field exists
- Track order in todo.md
- Phase order within tracks
- Task order within phases

### Explicit ordering:
- Use `order` field for custom sorting
- Lower numbers appear first
- Default order is insertion order
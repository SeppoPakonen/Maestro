# Maestro Markdown Data Format Specification

**Version**: 1.0.0
**Last Updated**: 2025-12-18

## Overview

All Maestro data is stored in markdown files within the `docs/` directory. These files are:
- **Human-readable**: Natural markdown formatting with headings, lists, and tables
- **Machine-parsable**: Consistent patterns using quoted key/value pairs and structured elements
- **Version-controlled**: All project state lives in git-tracked markdown files

## Parsing Rules

### 1. Quoted Key-Value Pairs
Metadata is stored as quoted key-value pairs on their own lines:
```markdown
"key": "value"
"numeric_key": 123
"boolean_key": true
```

**Parsing:**
- Pattern: `"([^"]+)":\s*(.+)$`
- Values are typed: strings (quoted), numbers (bare), booleans (bare true/false)
- Whitespace around colons is ignored
- These lines are trimmed of styling before parsing

### 2. Status Badges
Status indicators use emoji and bold markdown:
```markdown
✅ **Done**
🚧 **In Progress**
📋 **Planned**
💡 **Proposed**
```

**Parsing:**
- Pattern: `(✅|🚧|📋|💡)\s*\*\*\[?([^\]]+)\]?\*\*`
- Map emoji to status enum: ✅→done, 🚧→in_progress, 📋→planned, 💡→proposed

### 3. Completion Percentages
Progress indicators:
```markdown
**10%**
**Completion**: 65%
```

**Parsing:**
- Pattern: `\*\*(\d+)%\*\*` or `\*\*Completion\*\*:\s*(\d+)%`

### 4. Task Checkboxes
GitHub-flavored markdown checkboxes:
```markdown
- [ ] Uncompleted task
- [x] Completed task
- [ ] **Task 1.1: Task Name**
```

**Parsing:**
- Pattern: `^(\s*)- \[([ x])\]\s+(.+)$`
- Indentation level determines nesting

### 5. Heading Hierarchy
Standard markdown headings define structure:
```markdown
## Track: Track Name
### Phase 1: Phase Name
#### Task 1.1: Task Name
```

**Parsing:**
- Track: `^##\s+Track:\s+(.+)$`
- Phase: `^###\s+Phase\s+(\w+):\s+(.+)$`
- Task: `^####\s+Task\s+([\d.]+):\s+(.+)$`

### 6. Tables
Status tables use markdown table format:
```markdown
| Track | Phase | Status | Completion |
|-------|-------|--------|------------|
| **Repository Scanning** | | | |
| | U++ packages | ✅ Done | 100% |
```

**Parsing:**
- Standard markdown table parser
- Empty cells indicate hierarchy (indented rows)

## File Structure

### docs/config.md
Project-level configuration and metadata.

```markdown
# Maestro Configuration

## Project Metadata
"project_id": "uuid-here"
"created_at": "2025-12-18T01:16:53"
"maestro_version": "1.2.1"
"base_dir": "/path/to/project"

## User Settings
"default_editor": "$EDITOR"
"discussion_mode": "editor"
"ai_context_window": 4096
```

### docs/todo.md
Active tracks, phases, and tasks.

```markdown
# Maestro Development TODO

**Last Updated**: 2025-12-18

---

## Track: Track Name
"track_id": "track-1"
"priority": 1
"status": "in_progress"

### Phase 1: Phase Name
"phase_id": "track-1-phase-1"
"status": "in_progress"
"completion": 45

- [ ] **Task 1.1: Task Name**
  "task_id": "track-1-phase-1-task-1"
  "priority": "P0"
  Description of task
  - [ ] Subtask 1
  - [ ] Subtask 2
```

### docs/done.md
Completed tracks, phases, and tasks (same format as todo.md).

### docs/phases/\*.md
Detailed phase specifications.

```markdown
# Phase 1: Phase Name

"phase_id": "track-1-phase-1"
"track": "Track Name"
"status": "in_progress"
"completion": 45
"duration": "2-3 weeks"
"dependencies": ["phase-0"]

**Objective**: Brief description

## Tasks

- [ ] **Task 1.1: Task Name**
  "task_id": "track-1-phase-1-task-1"
  "priority": "P0"
  "estimated_hours": 8

  Detailed description...

  - [ ] Subtask 1
  - [ ] Subtask 2

## Deliverables
- Deliverable 1
- Deliverable 2

## Test Criteria
- Test 1
- Test 2
```

### docs/repo/state.md
Repository scanning state.

```markdown
# Repository State

"last_resolved_at": "2025-12-18T00:25:56"
"repo_root": "/home/sblo/Dev/Maestro"
"packages_count": 12
"assemblies_count": 4
"scanner_version": "0.9.0"

## Scan History

| Timestamp | Packages | Assemblies | Duration |
|-----------|----------|------------|----------|
| 2025-12-18T00:25:56 | 12 | 4 | 1.2s |
```

### docs/repo/index.md
Repository package index (machine-readable markdown representation of current JSON).

```markdown
# Repository Package Index

"last_updated": "2025-12-18T00:25:56"

## Assemblies

### Assembly: complex_test
"root_path": "/home/sblo/Dev/Maestro/complex_test"
"package_count": 3

**Packages:**
- Core
- Draw
- Gui

## Packages

### Package: Core
"name": "Core"
"dir": "/home/sblo/Dev/Maestro/complex_test/Core"
"upp_path": "/home/sblo/Dev/Maestro/complex_test/Core/Core.upp"
"build_system": "upp"

**Dependencies:**
- None

**Files:**
- Core.upp
```

### docs/discussions/\*.md
AI discussion history (when using editor mode).

```markdown
# Discussion: track-1-phase-1

"discussion_id": "uuid"
"context": "track-1-phase-1"
"created_at": "2025-12-18T10:30:00"
"status": "active"

---

**User:**
I need help planning Phase 1 tasks...

**AI:**
# Based on your requirements, here's what I suggest:
#
# 1. Start with core infrastructure
# 2. Add parser implementations
# 3. ...

**User:**
/done

**AI:**
# Generated actions:
{
  "actions": [
    {"type": "task.add", "track": "track-1", "phase": "phase-1", "task": {...}}
  ]
}
```

## Parsing Error Handling

When a parsing error occurs:
1. Stop the operation immediately
2. Display the error with file location and line number
3. Offer two options:
   - Manual fix: Open file in $EDITOR
   - AI fix: Call AI to correct the format
4. Validate again after fix

Example error:
```
Parse Error in docs/todo.md:45
Expected quoted key-value pair, found: track_id: "track-1"
                                              ^ missing opening quote

Fix options:
  1. Edit manually: maestro edit docs/todo.md:45
  2. AI auto-fix: maestro fix docs/todo.md:45
```

## Migration Strategy

To migrate from `.maestro/` JSON files to `docs/` markdown:

1. **Config migration:**
   - `.maestro/config.json` → `docs/config.md`

2. **Repo data migration:**
   - `.maestro/repo/state.json` → `docs/repo/state.md`
   - `.maestro/repo/index.json` → `docs/repo/index.md`

3. **Future data:**
   - `.maestro/conversations/` → `docs/discussions/`
   - `.maestro/sessions/` → `docs/sessions/`
   - Build artifacts stay in `.maestro/build/` (binary data, not for docs/)

## Advantages

1. **Git-friendly**: All project state is version-controlled
2. **Human-readable**: Developers can read and edit directly
3. **Diff-friendly**: Changes are visible in git diffs
4. **Self-documenting**: Documentation and data are unified
5. **No hidden state**: Everything visible in docs/
6. **AI-friendly**: LLMs can read and edit naturally
7. **Collaboration**: Team members can review/edit in PRs

## Implementation Priority

1. ✅ Document format specification (this file)
2. Create parser module: `maestro/data/markdown_parser.py`
3. Create writer module: `maestro/data/markdown_writer.py`
4. Migrate existing docs/todo.md and docs/phases/*.md to new format
5. Create migration tool: `maestro migrate` command
6. Update all code to use markdown backend instead of JSON

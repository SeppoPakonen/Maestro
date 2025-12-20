# Phase CLI1: Markdown Data Backend 📋 **[Planned - Critical]**

"phase_id": "cli-tpt-1"
"track": "Track/Phase/Task CLI and AI Discussion System"
"track_id": "cli-tpt"
"status": "planned"
"completion": 0
"duration": "1-2 weeks"
"dependencies": []
"priority": "P0"

**Objective**: Create the markdown data backend to replace JSON storage in `.maestro/`, implementing both parser and writer modules with comprehensive error handling.

## Background

Currently, Maestro stores data in `.maestro/*.json` files, which are:
- Not human-readable without tools
- Hidden from git in a way that makes collaboration harder
- Not self-documenting

The new markdown backend will:
- Store all data in `docs/*.md` files
- Be both human-readable and machine-parsable
- Live alongside documentation
- Be diff-friendly for version control
- Allow direct editing by developers

## Tasks

### Task cli1.1: Parser Module

"task_id": "cli-tpt-1-1"
"priority": "P0"
"estimated_hours": 16

Create `maestro/data/markdown_parser.py` with functions to parse markdown data format.

- [ ] **cli1.1.1: Basic Parsing Infrastructure**
  - [ ] Create module structure: `maestro/data/markdown_parser.py`
  - [ ] Implement `parse_quoted_value(line: str) -> Tuple[str, Any]`
    - Pattern: `"([^"]+)":\s*(.+)$`
    - Type detection: quoted→str, bare number→int/float, bare true/false→bool
  - [ ] Implement `parse_status_badge(line: str) -> Optional[str]`
    - Pattern: `(✅|🚧|📋|💡)\s*\*\*\[?([^\]]+)\]?\*\*`
    - Map emoji to status: ✅→done, 🚧→in_progress, 📋→planned, 💡→proposed
  - [ ] Implement `parse_completion(line: str) -> Optional[int]`
    - Patterns: `\*\*(\d+)%\*\*` or `\*\*Completion\*\*:\s*(\d+)%`

- [ ] **cli1.1.2: Structured Element Parsing**
  - [ ] Implement `parse_checkbox(line: str) -> Optional[Tuple[int, bool, str]]`
    - Pattern: `^(\s*)- \[([ x])\]\s+(.+)$`
    - Return: (indent_level, is_checked, content)
  - [ ] Implement `parse_heading(line: str) -> Optional[Tuple[int, str]]`
    - Return: (level, text)
  - [ ] Implement `parse_track_heading(line: str) -> Optional[str]`
    - Pattern: `^##\s+(?:🔥\s+)?(?:TOP PRIORITY\s+)?Track:\s+(.+)$`
  - [ ] Implement `parse_phase_heading(line: str) -> Optional[Tuple[str, str]]`
    - Pattern: `^###\s+Phase\s+([\w\d]+):\s+(.+?)(?:\s+[📋🚧✅💡])?`
    - Return: (phase_id, phase_name)
  - [ ] Implement `parse_task_heading(line: str) -> Optional[Tuple[str, str]]`
    - Pattern: `^\*\*Task\s+([\d.]+):\s+(.+)\*\*`
    - Return: (task_number, task_name)

- [ ] **cli1.1.3: High-Level Parsers**
  - [ ] Implement `parse_metadata_block(lines: List[str]) -> Dict[str, Any]`
    - Parse consecutive quoted key-value pairs
    - Stop at first non-matching line
  - [ ] Implement `parse_track(lines: List[str], start_idx: int) -> Tuple[Dict, int]`
    - Extract track metadata, phases, description
    - Return: (track_dict, next_line_index)
  - [ ] Implement `parse_phase(lines: List[str], start_idx: int) -> Tuple[Dict, int]`
    - Extract phase metadata, tasks, description
    - Return: (phase_dict, next_line_index)
  - [ ] Implement `parse_task(lines: List[str], start_idx: int) -> Tuple[Dict, int]`
    - Extract task metadata, subtasks, description
    - Return: (task_dict, next_line_index)

- [ ] **cli1.1.4: Document Parsers**
  - [ ] Implement `parse_todo_md(path: str) -> Dict`
    - Parse docs/todo.md into structured data
    - Return: {tracks: [...], metadata: {...}}
  - [ ] Implement `parse_done_md(path: str) -> Dict`
    - Parse docs/done.md into structured data
  - [ ] Implement `parse_phase_md(path: str) -> Dict`
    - Parse docs/phases/*.md into structured data
  - [ ] Implement `parse_config_md(path: str) -> Dict`
    - Parse docs/config.md into structured data

### Task cli1.2: Writer Module

"task_id": "cli-tpt-1-2"
"priority": "P0"
"estimated_hours": 12

Create `maestro/data/markdown_writer.py` with functions to write markdown data format.

- [ ] **cli1.2.1: Basic Writing Infrastructure**
  - [ ] Create module structure: `maestro/data/markdown_writer.py`
  - [ ] Implement `format_quoted_value(key: str, value: Any) -> str`
    - Format: `"key": value` (quote strings, bare numbers/booleans)
  - [ ] Implement `format_status_badge(status: str) -> str`
    - Map status to emoji: done→✅, in_progress→🚧, planned→📋, proposed→💡
  - [ ] Implement `format_completion(completion: int) -> str`
    - Format: `**{completion}%**`
  - [ ] Implement `format_checkbox(checked: bool, content: str, indent: int = 0) -> str`
    - Format: `- [x]` or `- [ ]` with proper indentation

- [ ] **cli1.2.2: High-Level Writers**
  - [ ] Implement `write_metadata_block(metadata: Dict) -> List[str]`
    - Write quoted key-value pairs
  - [ ] Implement `write_track(track: Dict) -> List[str]`
    - Format track heading, metadata, phases
  - [ ] Implement `write_phase(phase: Dict) -> List[str]`
    - Format phase heading, metadata, tasks
  - [ ] Implement `write_task(task: Dict) -> List[str]`
    - Format task with metadata, subtasks

- [ ] **cli1.2.3: Document Writers**
  - [ ] Implement `write_todo_md(data: Dict, path: str)`
    - Write structured data to docs/todo.md
    - Preserve table of contents, status table
  - [ ] Implement `write_done_md(data: Dict, path: str)`
    - Write structured data to docs/done.md
  - [ ] Implement `write_phase_md(phase: Dict, path: str)`
    - Write phase data to docs/phases/*.md
  - [ ] Implement `write_config_md(config: Dict, path: str)`
    - Write config data to docs/config.md

### Task cli1.3: Error Handling and Validation

"task_id": "cli-tpt-1-3"
"priority": "P0"
"estimated_hours": 8

Implement comprehensive error handling and validation.

- [ ] **cli1.3.1: Parse Error Types**
  - [ ] Define `ParseError` exception class
    - Fields: file_path, line_number, column, message, context
  - [ ] Define specific error types:
    - `InvalidQuotedValueError`
    - `InvalidHeadingError`
    - `MissingMetadataError`
    - `InconsistentIndentationError`

- [ ] **cli1.3.2: Error Detection and Reporting**
  - [ ] Implement `validate_markdown_syntax(path: str) -> List[ParseError]`
    - Run all validators on a markdown file
  - [ ] Implement error reporting with context:
    ```
    Parse Error in docs/todo.md:45
    Expected quoted key-value pair, found: track_id: "track-1"
                                                  ^ missing opening quote
    ```
  - [ ] Add line and column tracking to all parse functions

- [ ] **cli1.3.3: Error Recovery Options**
  - [ ] Implement `prompt_fix_error(error: ParseError) -> bool`
    - Display error with context
    - Offer: "1. Edit manually  2. AI auto-fix  3. Abort"
  - [ ] Implement `open_editor_at_line(path: str, line: int)`
    - Open $EDITOR at error location
  - [ ] Design AI auto-fix interface (implementation in Phase CLI3)

### Task cli1.4: Migration Tools

"task_id": "cli-tpt-1-4"
"priority": "P1"
"estimated_hours": 12

Create migration tools to convert existing JSON data to markdown format.

- [ ] **cli1.4.1: Config Migration**
  - [ ] Implement `migrate_config() -> bool`
    - Read `.maestro/config.json`
    - Convert to markdown format
    - Write to `docs/config.md`
    - Validate result

- [ ] **cli1.4.2: Repo State Migration**
  - [ ] Implement `migrate_repo_state() -> bool`
    - Read `.maestro/repo/state.json`
    - Convert to markdown format
    - Write to `docs/repo/state.md`
    - Validate result

- [ ] **cli1.4.3: Repo Index Migration**
  - [ ] Implement `migrate_repo_index() -> bool`
    - Read `.maestro/repo/index.json`
    - Convert to markdown format (assemblies and packages)
    - Write to `docs/repo/index.md`
    - Validate result

- [ ] **cli1.4.4: CLI Command**
  - [ ] Implement `maestro migrate` command
    - Migrate all data from `.maestro/` to `docs/`
    - Create backup of original JSON files
    - Validate all migrated data
    - Report migration status
  - [ ] Add `--dry-run` flag to preview migration
  - [ ] Add `--backup-dir` to specify backup location

### Task cli1.5: Round-Trip Testing

"task_id": "cli-tpt-1-5"
"priority": "P0"
"estimated_hours": 8

Ensure parser and writer are consistent and lossless.

- [ ] **cli1.5.1: Unit Tests**
  - [ ] Test parse_quoted_value with various types
  - [ ] Test parse_status_badge with all emoji types
  - [ ] Test parse_heading with various levels
  - [ ] Test checkbox parsing with nested indentation
  - [ ] Test metadata block parsing

- [ ] **cli1.5.2: Integration Tests**
  - [ ] Test parse_todo_md → write_todo_md round-trip
  - [ ] Test parse_phase_md → write_phase_md round-trip
  - [ ] Test parse_config_md → write_config_md round-trip
  - [ ] Test preservation of manual styling (bold, italic, etc.)

- [ ] **cli1.5.3: Error Handling Tests**
  - [ ] Test malformed quoted values
  - [ ] Test missing metadata
  - [ ] Test inconsistent indentation
  - [ ] Test error reporting with correct line numbers

## Deliverables

- `maestro/data/markdown_parser.py` - Full parser implementation
- `maestro/data/markdown_writer.py` - Full writer implementation
- `maestro/data/errors.py` - Error types and handling
- `maestro/commands/migrate.py` - Migration command
- `tests/data/test_markdown_parser.py` - Parser tests
- `tests/data/test_markdown_writer.py` - Writer tests
- `tests/data/test_migration.py` - Migration tests
- `docs/config.md` - Migrated configuration
- `docs/repo/state.md` - Migrated repo state
- `docs/repo/index.md` - Migrated repo index

## Test Criteria

- All unit tests pass
- Round-trip parsing is lossless (parse → write → parse produces identical data)
- Error detection catches all malformed markdown
- Migration produces valid markdown files
- Existing docs/todo.md and docs/phases/*.md can be parsed correctly

## Dependencies

- None (foundational phase)

## Notes

- Parser must be tolerant of manual edits (whitespace, styling)
- Writer should produce consistent, readable markdown
- Error messages must be actionable and clear
- Migration should be idempotent (safe to run multiple times)

## Estimated Complexity: High (1-2 weeks total)

- Week 1: Parser (1.1), Writer (1.2), Error Handling (1.3)
- Week 2: Migration (1.4), Testing (1.5)

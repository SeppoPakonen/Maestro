# Subsystem Deep Dive: Docs Truth

The "Docs Truth" subsystem in Maestro is responsible for reading, parsing, and writing structured information directly from Markdown files within the `docs/` directory. This acts as a human-readable and version-controllable data store for tasks, plans, configurations, and other project metadata.

## 1. Markdown Parsing Pipeline

The core of the parsing logic resides in `maestro/data/markdown_parser.py`. It uses regular expressions and string manipulation to extract structured data from Markdown content, adhering to specific formatting conventions.

*   **Primary Parsing Functions (`maestro/data/markdown_parser.py`):**
    *   `_parse_asterisk_token(text: str)`: Helper for parsing tokens wrapped in asterisks.
    *   `_parse_asterisk_wrapped_value(value_str: str)`: Parses values wrapped in asterisks.
    *   `parse_quoted_value(line: str)`: Parses key-value pairs where values are quoted (e.g., `"key": "value"`).
    *   `parse_status_badge(line: str)`: Extracts status text from badge-like Markdown (e.g., `✅ **Done**`).
    *   `parse_completion(line: str)`: Extracts completion percentages (e.g., `**45%**`).
    *   `parse_checkbox(line: str)`: Parses GitHub-flavored Markdown checkboxes (e.g., `- [ ] Task`, `- [x] Task`).
    *   `parse_heading(line: str)`: Extracts heading level and text (e.g., `## Heading Text`).
    *   `parse_track_heading(line: str)`: Specifically parses track headings (e.g., `## Track: Name`).
    *   `parse_phase_heading(line: str)`: Specifically parses phase headings (e.g., `### Phase CLI1: Name`).
    *   `parse_task_heading(line: str)`: Specifically parses task headings (e.g., `**Task 1.1: Name**`).
    *   `parse_metadata_block(lines: List[str], start_idx: int)`: Parses blocks of key-value metadata.
    *   `parse_track(lines: List[str], start_idx: int)`: Parses an entire track section, including its metadata, phases, and tasks.
    *   `parse_phase(lines: List[str], start_idx: int)`: Parses an entire phase section, including its metadata and tasks.
    *   `parse_task(lines: List[str], start_idx: int)`: Parses an entire task section.

*   **File-Level Parsers (`maestro/data/markdown_parser.py`):**
    *   `parse_todo_md(path: str) -> Dict`: Reads `todo.md` and extracts tracks, phases, and tasks.
    *   `parse_done_md(path: str) -> Dict`: Reads `done.md` (re-uses `parse_todo_md` logic).
    *   `parse_phase_md(path: str) -> Dict`: Reads a specific phase Markdown file.
    *   `parse_config_md(path: str) -> Dict`: Reads `config.md` and extracts configuration settings.

*   **Safe Parsing Wrappers (`maestro/data/common_utils.py`):**
    *   `parse_todo_safe(todo_path: Path = None, verbose: bool = False) -> Optional[dict]`: Wraps `parse_todo_md` with error handling, returning `None` or an empty dict on failure.
    *   `parse_done_safe(done_path: Path = None, verbose: bool = False) -> Optional[dict]`: Wraps `parse_done_md` with error handling.

## 2. Writers/Format Constraints

The writing logic is found in `maestro/data/markdown_writer.py`. Instead of being a standalone writer, it often works by parsing the existing Markdown, identifying sections, and then inserting, updating, or deleting content while preserving the overall structure. This implies strict format constraints.

*   **Key Functions (`maestro/data/markdown_writer.py`):**
    *   Functions like `add_track_to_todo_md`, `update_task_in_phase_md`, `remove_phase_from_track_md` (names are illustrative, need to check actual functions) would encapsulate the read-parse-modify-write cycle.
    *   These writer functions heavily rely on the parsing functions (e.g., `parse_track_heading`, `parse_phase_heading`, `parse_checkbox`) to locate the correct positions within the Markdown file for modifications.
    *   The format dictates that tracks are `##` headings, phases are `###` headings, tasks are typically list items with checkboxes, and metadata is often within key-value pairs or specific badge formats. Any deviation from this expected structure could lead to parsing errors or incorrect modifications.

## 3. Where TODO/DONE Boundaries are Enforced

The "Docs Truth" utilizes two primary Markdown files for task and project state management:

*   **`docs/todo.md`**: This file contains all active, planned, and in-progress tracks, phases, and tasks. It represents the current workload and future plans.
    *   Read by `parse_todo_md` and `parse_todo_safe`.
    *   Modified by various command handlers (e.g., `handle_track_command`, `handle_phase_command`, `handle_task_command`) via `markdown_writer` functions to add, update, or remove items.
*   **`docs/done.md`**: This file archives all completed tracks, phases, and tasks. It serves as a historical record of finished work.
    *   Read by `parse_done_md` and `parse_done_safe`.
    *   Tasks and phases are moved from `todo.md` to `done.md` upon completion (e.g., by status change commands), orchestrated by command handlers interacting with both `markdown_parser` and `markdown_writer`.

The enforcement of these boundaries is not through hard schema validation but through the programmatic logic within the command handlers and the `markdown_writer` functions. These functions implicitly assume and maintain the segregation of active and completed work based on the file paths (`docs/todo.md` vs `docs/done.md`) and the internal structure within these files.

## 4. Existing Tests & Coverage Gaps

*   **Tests:**
    *   Look for `maestro/tests/test_markdown_parser.py` and `maestro/tests/test_markdown_writer.py` (or similar naming conventions) to verify the parsing and writing logic.
    *   Integration tests for commands interacting with `todo.md` and `done.md` (e.g., `maestro track add`, `maestro phase status done`) should cover the state transitions.
*   **Coverage Gaps:**
    *   Testing edge cases for Markdown formatting (malformed headings, incorrect checkbox syntax, missing metadata).
    *   Ensuring robustness against unexpected content that might break parsing or writing operations.
    *   Explicitly testing the backward compatibility aspects of parsing if the format evolves.

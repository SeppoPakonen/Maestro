# Phase CLI4: Settings and Configuration 📋 **[Planned]**

- *phase_id*: *cli-tpt-4*
- *track*: *Track/Phase/Task CLI and AI Discussion System*
- *track_id*: *cli-tpt*
- *status*: *planned*
- *completion*: 0
- *duration*: *3-5 days*
- *dependencies*: [*cli-tpt-1*]
- *priority*: *P1*

**Objective**: Implement the settings management system, migrate configuration from `~/.maestro/` to `docs/config.md`, and provide a user-friendly interface for managing preferences.

## Background

Currently, configuration is stored in `~/.maestro/config.json`, which is:
- Not version-controlled with the project
- Not visible in documentation
- Not easily shareable across team members

The new system stores configuration in `docs/config.md`:
- **Project metadata**: project_id, created_at, version
- **User preferences**: editor mode, AI settings, display preferences
- **Build settings**: default build methods, compiler flags
- **Current context**: active track/phase/task

## Tasks

### Task cli4.1: Configuration Schema

- *task_id*: *cli-tpt-4-1*
- *priority*: *P1*
- *estimated_hours*: 6

Define the complete configuration schema and structure.

- [ ] **cli4.1.1: Configuration Sections**
  - [ ] Define `docs/config.md` structure:
    ```markdown
    # Maestro Configuration

    ## Project Metadata
    "project_id": "<uuid>"
    "created_at": "YYYY-MM-DDTHH:MM:SS"
    "maestro_version": "x.y.z"
    "base_dir": "/path/to/project"

    ## User Preferences
    "default_editor": "$EDITOR"
    "discussion_mode": "editor"
    "list_format": "table"

    ## AI Settings
    "ai_provider": "anthropic"
    "ai_model": "claude-3-5-sonnet-20250205"
    "ai_api_key_file": "~/.anthropic_key"
    "ai_context_window": 8192

    ## Build Settings
    "default_build_method": "auto"
    "parallel_jobs": 4
    "verbose_builds": false

    ## Display Settings
    "color_output": true
    "unicode_symbols": true
    "compact_lists": false

    ## Current Context
    "current_track": null
    "current_phase": null
    "current_task": null
    ```

- [ ] **cli4.1.2: Schema Validation**
  - [ ] Define `ConfigSchema` dataclass with all fields
  - [ ] Implement type validation for each field
  - [ ] Define default values for all settings
  - [ ] Implement schema version for future migrations

### Task cli4.2: Settings Module

- *task_id*: *cli-tpt-4-2*
- *priority*: *P1*
- *estimated_hours*: 8

Implement the settings management module.

- [ ] **cli4.2.1: Settings Class**
  - [ ] Create `maestro/config/settings.py`
  - [ ] Implement `Settings` class:
    - `load() -> Settings` - Load from docs/config.md
    - `save()` - Save to docs/config.md
    - `get(key: str, default: Any = None) -> Any`
    - `set(key: str, value: Any)`
    - `get_section(section: str) -> Dict`
    - `set_section(section: str, data: Dict)`
  - [ ] Implement dot notation for nested access:
    - `settings.get("ai.provider")` → "anthropic"
    - `settings.set("ai.model", "claude-3-opus")`

- [ ] **cli4.2.2: Settings Validation**
  - [ ] Validate on load and save
  - [ ] Type checking (string, int, bool, etc.)
  - [ ] Enum validation (e.g., discussion_mode must be "editor" or "terminal")
  - [ ] Path expansion ($EDITOR, ~/ paths)
  - [ ] Raise `InvalidSettingError` with helpful message

- [ ] **cli4.2.3: Defaults and Migration**
  - [ ] Implement `create_default_config() -> Settings`
    - Generate new project_id (UUID)
    - Set created_at to current timestamp
    - Use default values for all settings
  - [ ] Implement config migration from `.maestro/config.json`
    - Preserve project_id and created_at
    - Map old settings to new schema
    - Add new settings with defaults

### Task cli4.3: Settings Command

- *task_id*: *cli-tpt-4-3*
- *priority*: *P1*
- *estimated_hours*: 10

Implement the `maestro settings` command for managing configuration.

- [ ] **cli4.3.1: Settings List**
  - [ ] Implement `maestro settings list`
    - Display all settings organized by section
    - Format:
      ```
      Project Metadata:
        project_id: e152dd7f-83c7-4550-84ec-d053a6004470
        created_at: 2025-12-18T01:16:53
        maestro_version: 1.2.1

      User Preferences:
        default_editor: $EDITOR (resolved: /usr/bin/vim)
        discussion_mode: editor

      AI Settings:
        ai_provider: anthropic
        ai_model: claude-3-5-sonnet-20250205
      ```
  - [ ] Add `--section <name>` to show only one section
  - [ ] Add `--json` for machine-readable output

- [ ] **cli4.3.2: Settings Get**
  - [ ] Implement `maestro settings get <key>`
    - Show single setting value
    - Support dot notation: `maestro settings get ai.provider`
    - Show resolved value for paths and env vars
  - [ ] Add `--raw` to show unresolved value

- [ ] **cli4.3.3: Settings Set**
  - [ ] Implement `maestro settings set <key> <value>`
    - Update single setting
    - Validate before saving
    - Confirm change:
      ```
      Updated ai.model:
        old: claude-3-5-sonnet-20250205
        new: claude-3-opus-20240620
      ```
  - [ ] Add `--no-confirm` to skip confirmation

- [ ] **cli4.3.4: Settings Edit**
  - [ ] Implement `maestro settings edit`
    - Open docs/config.md in $EDITOR
    - Validate after editing
    - Rollback if validation fails
  - [ ] Implement `maestro settings edit <section>`
    - Open editor at specific section
    - Jump to section heading

- [ ] **cli4.3.5: Settings Reset**
  - [ ] Implement `maestro settings reset <key>`
    - Reset single setting to default
    - Preserve project metadata (project_id, created_at)
  - [ ] Implement `maestro settings reset --all`
    - Reset all settings to defaults
    - Require `--force` confirmation

- [ ] **cli4.3.6: Settings Wizard**
  - [ ] Implement `maestro settings wizard`
    - Interactive setup for new projects
    - Prompt for common settings:
      - AI provider and API key
      - Default editor
      - Discussion mode preference
      - Build settings (parallel jobs, etc.)
    - Save to docs/config.md

### Task cli4.4: Context Management

- *task_id*: *cli-tpt-4-4*
- *priority*: *P1*
- *estimated_hours*: 6

Implement current context tracking for track/phase/task.

- [ ] **cli4.4.1: Context Commands**
  - [ ] Implement `maestro context show`
    - Display current track/phase/task
    - Format:
      ```
      Current context:
        Track: cli-tpt (Track/Phase/Task CLI and AI Discussion System)
        Phase: cli-tpt-1 (CLI1: Markdown Data Backend)
        Task: cli-tpt-1-1 (Task 1.1: Parser Module)
      ```
  - [ ] Implement `maestro context clear`
    - Clear all context (reset to null)

- [ ] **cli4.4.2: Context Setting**
  - [ ] Update `maestro track <id> set`
    - Set current_track in config
    - Clear current_phase and current_task
  - [ ] Update `maestro phase <id> set`
    - Set current_phase in config
    - Set current_track to phase's parent track
    - Clear current_task
  - [ ] Update `maestro task <id> set`
    - Set current_task in config
    - Set current_phase and current_track appropriately

- [ ] **cli4.4.3: Contextual Commands**
  - [ ] Update commands to use context when no ID provided:
    - `maestro phase list` → list phases in current track
    - `maestro task list` → list tasks in current phase
    - `maestro discuss` → discuss current phase/track
  - [ ] Display context in prompt when set:
    ```
    [Track: cli-tpt, Phase: cli-tpt-1] maestro task list
    ```

### Task cli4.5: Feature Matrix Update

- *task_id*: *cli-tpt-4-5*
- *priority*: *P2*
- *estimated_hours*: 4

Update CLI/TUI feature matrix with roadmap/plan/task → track/phase/task conversion.

- [ ] **cli4.5.1: Locate Feature Matrix**
  - [ ] Find existing feature matrix documentation
  - [ ] Identify all references to "roadmap", "plan", "task" terminology

- [ ] **cli4.5.2: Update Terminology**
  - [ ] Replace "roadmap" with "track"
  - [ ] Replace "plan" with "phase"
  - [ ] Keep "task" as is (no change)
  - [ ] Update all command examples
  - [ ] Update all documentation references

- [ ] **cli4.5.3: Add New Features**
  - [ ] Document track/phase/task commands
  - [ ] Document discuss commands
  - [ ] Document settings commands
  - [ ] Update CLI command tree diagram
  - [ ] Update TUI navigation diagram (if applicable)

## Deliverables

- `maestro/config/settings.py` - Settings management module
- `maestro/commands/settings.py` - Settings command implementation
- `maestro/commands/context.py` - Context management
- `docs/config.md` - Project configuration (migrated from JSON)
- `tests/config/test_settings.py` - Settings tests
- Updated feature matrix documentation

## Test Criteria

- Settings can be loaded, modified, and saved correctly
- Validation catches invalid settings
- Settings command works for all operations (list, get, set, edit, reset)
- Context management works correctly
- Migration from `.maestro/config.json` works
- Feature matrix is updated with new terminology

## Dependencies

- Phase CLI1 (Markdown Data Backend) must be complete

## Notes

- Settings should be easy to discover and modify
- Validation errors should be clear and actionable
- Context makes common operations more convenient
- Settings wizard helps new users get started quickly

## Estimated Complexity: Medium (3-5 days total)

- Day 1-2: Schema and Settings module (4.1, 4.2)
- Day 2-3: Settings command (4.3)
- Day 4: Context management (4.4)
- Day 5: Feature matrix update (4.5)

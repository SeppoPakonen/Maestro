# Command: `settings`

## 1. Command Surface

*   **Command:** `settings`
*   **Aliases:** `config`, `cfg`
*   **Handler Binding:** `maestro.main.main` dispatches to `maestro.commands.settings.handle_settings_command`.

## 2. Entrypoint(s)

*   **Primary Dispatcher:** `maestro.commands.settings.handle_settings_command(args: argparse.Namespace)`
*   **File Path:** `/home/sblo/Dev/Maestro/maestro/commands/settings.py`
*   **Specific Subcommand Handlers:** `list_settings`, `get_setting`, `set_setting`, `edit_settings`, `reset_settings`, `settings_wizard`, and various `profile_*` functions.

## 3. Call Chain (ordered)

The `handle_settings_command` function acts as the central router, dispatching to various specialized functions based on the `settings_subcommand` (and `profile_subcommand` for nested profile commands).

### Common Flow for most subcommands

1.  `maestro.main.main()` → `maestro.commands.settings.handle_settings_command(args)`
    *   **Purpose:** Entry point for the `settings` command.
2.  `maestro.config.settings.get_settings()` (called by most handlers).
    *   **Purpose:** Loads the current global settings from `docs/config.md`.

### `maestro settings list`

1.  ... → `maestro.commands.settings.list_settings(args)`
2.  `settings.get_section(section_key)`
    *   **Purpose:** Retrieves settings organized by logical sections.
3.  `settings.to_dict()` (if `--json` and no `--section`).
4.  `maestro.commands.settings.format_value_for_display(key, value)`.
5.  `json.dumps(...)` (if `--json`).
6.  `print()` for formatted human-readable output.

### `maestro settings get <key>`

1.  ... → `maestro.commands.settings.get_setting(args)`
2.  `settings.get(args.key, None)`.
3.  `maestro.commands.settings.format_value_for_display(args.key, value)`.
4.  `print()`.

### `maestro settings set <key> <value>`

1.  ... → `maestro.commands.settings.set_setting(args)`
2.  `settings.get(args.key, None)` (to get old value and infer type).
3.  `maestro.commands.settings.convert_value_to_type(args.value, target_type)`.
4.  `settings.set(args.key, converted_value)`.
5.  `settings.validate()`.
6.  `settings.save()`.
7.  `maestro.config.settings_profiles.SettingsProfileManager().get_settings_hash()` (to detect changes against active profile).
8.  `maestro.modules.utils.print_success(...)`.

### `maestro settings edit`

1.  ... → `maestro.commands.settings.edit_settings(args)`
2.  `pathlib.Path('docs/config.md').exists()` → `maestro.config.settings.create_default_config().save(config_path)` (if file doesn't exist).
3.  `maestro.config.settings_profiles.SettingsProfileManager().get_settings_hash()`.
4.  `subprocess.run([editor, str(config_path)])`
    *   **Purpose:** Invokes the user's `$EDITOR` to modify `docs/config.md`.
5.  `maestro.config.settings.Settings.load(config_path)`.
6.  `new_settings.validate()`.
7.  `maestro.modules.utils.print_success(...)`.

### `maestro settings reset`

1.  ... → `maestro.commands.settings.reset_settings(args)`
2.  `maestro.config.settings_profiles.SettingsProfileManager().get_settings_hash()`.
3.  `(If --all)` `maestro.config.settings.create_default_config()`.
4.  `(If --all)` `old_settings.project_id`, `old_settings.created_at`, etc. (to preserve project metadata).
5.  `settings.set(args.key, default_value)` (for single key reset).
6.  `settings.save()`.

### `maestro settings wizard`

1.  ... → `maestro.commands.settings.settings_wizard(args)`
2.  `maestro.config.settings.create_default_config()`.
3.  `input()` for interactive prompts.
4.  `settings.ai_provider = ai_provider`, `settings.ai_engines_claude = claude_role`, etc. (sets values).
5.  `settings.save()`.

### `maestro settings profile <subcommand>` (e.g., `list`, `save`, `load`, `get`, `set-default`)

1.  ... → (e.g., `profile_list(args)`, `profile_save(args)`).
2.  `maestro.config.settings_profiles.SettingsProfileManager()`
3.  `profile_manager.list_profiles()`, `get_active_profile()`, `get_default_profile()`, `update_profile()`, `create_profile()`, `set_active_profile()`, `set_default_profile()`, `load_profile()`, `has_unsaved_changes()`, `get_settings_hash()`, `create_audit_log()`.
4.  `settings.save()` (after loading a profile).
5.  `json.dumps(...)` (for JSON output).

## 4. Core Data Model Touchpoints

*   **Reads:**
    *   `docs/config.md`: The main settings file, where all current settings are stored.
    *   `~/.maestro/profiles.json`: A JSON file managed by `SettingsProfileManager` that stores metadata about saved profiles (names, IDs, active/default status).
    *   `~/.maestro/profiles/<profile_id>.json`: Individual JSON files for each saved profile, containing the actual settings values for that profile.
    *   Environment variables (`$EDITOR`, `$VISUAL`).
*   **Writes:**
    *   `docs/config.md`: Updated by `set_setting`, `edit_settings`, `reset_settings`, `settings_wizard`, and `profile_load`.
    *   `~/.maestro/profiles.json`: Updated when profiles are created, updated, or marked as active/default.
    *   `~/.maestro/profiles/<profile_id>.json`: Created or updated when a profile is saved.
    *   `~/.maestro/profiles/audit.jsonl`: Audit log for profile changes (created by `create_audit_log`).
*   **Schema:** Settings are stored in `docs/config.md` in a custom Markdown format (parsed by `maestro.data.markdown_parser.parse_config_md`). Settings profiles are stored as JSON files according to an implicit schema defined by `maestro.config.settings_profiles`.

## 5. Configuration & Globals

*   `os.environ.get('EDITOR', 'vim')`: Retrieves the user's preferred editor.
*   `maestro.config.settings`: Encapsulates all application settings, including loading, saving, and validation logic.
*   `maestro.config.settings_profiles`: Manages the lifecycle of settings profiles.
*   `docs/config.md`: The canonical file for runtime configuration.

## 6. Validation & Assertion Gates

*   **Setting Existence:** `get_setting` and `set_setting` verify if a key exists before proceeding.
*   **Type Conversion:** `convert_value_to_type` validates if a string can be cast to the target type (bool, int, float).
*   **Settings Validation:** `settings.validate()` is called after edits to ensure the overall configuration remains valid.
*   **Profile Uniqueness:** `profile_save` checks for duplicate profile names.
*   **`--force` for `reset --all`:** Prevents accidental data loss.
*   **User Confirmation:** Prompts for confirmation when overwriting profiles or applying changes after editing.

## 7. Side Effects

*   Modifies configuration files (`docs/config.md`, profile JSON files).
*   Creates profile-related directories (`~/.maestro/profiles/`).
*   Invokes external editor process (`subprocess`).
*   Prints detailed, formatted output to the console.
*   Interactively prompts the user (`input()`) during `settings_wizard` and profile management.

## 8. Error Semantics

*   `print_error` and `sys.exit(1)` for critical errors (e.g., setting not found, invalid input, editor not found, validation failure).
*   `ValueError` for invalid type conversions.
*   Error messages are designed to guide the user on how to resolve issues (e.g., "Use --force to confirm").

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/commands/test_settings.py` for CLI command behavior.
    *   `maestro/tests/config/test_settings.py` and `test_settings_profiles.py` for underlying logic.
    *   Tests covering each subcommand: `list` (JSON/human-readable, sections), `get` (raw/resolved), `set` (all types, existence checks), `edit` (editor integration), `reset` (single/all, force), `wizard` (interactive flow).
    *   Tests for profile management: `list`, `save`, `load`, `get`, `set-default` under various scenarios.
    *   Tests for `convert_value_to_type`.
*   **Coverage Gaps:**
    *   Comprehensive testing of all possible setting keys for `set` and `reset`.
    *   Robustness testing for malformed `docs/config.md` or profile JSON files.
    *   Integration tests for `edit_settings` ensuring correct validation loop.
    *   Testing of `settings_wizard` with various user inputs (including invalid ones).
    *   Thorough testing of `SettingsProfileManager` audit trail generation.

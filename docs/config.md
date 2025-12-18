# Maestro Configuration

**Last Updated**: 2025-12-19

---

## Project Metadata

"project_id": "e152dd7f-83c7-4550-84ec-d053a6004470"
"created_at": "2025-12-18T01:16:53.355885"
"maestro_version": "1.2.1"
"base_dir": "/home/sblo/Dev/Maestro"

---

## User Preferences

"default_editor": "$EDITOR"
"discussion_mode": "editor"
"list_format": "table"

---

## Ai Settings

"ai_provider": "anthropic"
"ai_model": "claude-3-5-sonnet-20250205"
"ai_api_key_file": "~/.anthropic_key"
"ai_context_window": 8192
"ai_temperature": 0.7

---

## Build Settings

"default_build_method": "auto"
"parallel_jobs": 4
"verbose_builds": false
"clean_before_build": false

---

## Display Settings

"color_output": true
"unicode_symbols": true
"compact_lists": false
"show_completion_bars": true

---

## Current Context

"current_track": null
"current_phase": null
"current_task": null

---

## Notes

This configuration file is both human-readable and machine-parsable. You can:

1. **Edit manually**: Modify values directly, preserving the quoted key-value format
2. **Use settings command**: `maestro settings set <key> <value>`
3. **Use settings wizard**: `maestro settings wizard` for guided setup

### Key Descriptions

**Project Metadata:**
- `project_id`: Unique identifier for this project (UUID)
- `created_at`: Project initialization timestamp
- `maestro_version`: Maestro version used to create project
- `base_dir`: Root directory of the project

**User Preferences:**
- `default_editor`: Editor to use for discussions ($EDITOR uses environment variable)
- `discussion_mode`: Default mode for AI discussions ("editor" or "terminal")
- `list_format`: How to display lists ("table", "compact", "detailed")

**AI Settings:**
- `ai_provider`: AI service provider ("anthropic", "openai", "local")
- `ai_model`: Model name to use
- `ai_api_key_file`: Path to file containing API key
- `ai_context_window`: Maximum context size in tokens
- `ai_temperature`: AI temperature (0.0-1.0, higher = more creative)

**Build Settings:**
- `default_build_method`: Default build method ("auto" detects from package type)
- `parallel_jobs`: Number of parallel build jobs
- `verbose_builds`: Show detailed build output
- `clean_before_build`: Clean before each build

**Display Settings:**
- `color_output`: Use ANSI colors in terminal output
- `unicode_symbols`: Use Unicode symbols (✅ 🚧 📋 💡)
- `show_completion_bars`: Show progress bars for completion percentages
- `compact_lists`: Show compact list format by default

**Current Context:**
- `current_track`: Currently active track ID (null = none)
- `current_phase`: Currently active phase ID (null = none)
- `current_task`: Currently active task ID (null = none)

### Commands

- `maestro settings list` - Show all settings
- `maestro settings get <key>` - Get a single setting
- `maestro settings set <key> <value>` - Update a setting
- `maestro settings edit` - Edit this file in $EDITOR
- `maestro settings reset <key>` - Reset setting to default
- `maestro settings wizard` - Interactive setup wizard

#!/bin/bash
# Task: Implement Settings Command for CLI4
# This script runs qwen to create the maestro settings command

TASK_PROMPT="# Task: Implement Settings Command for Maestro CLI4

## Context
You are implementing Phase CLI4 Task 4.3 for the Maestro build orchestration system.
The goal is to create the \`maestro settings\` command that provides a user-friendly interface for managing configuration.

## Completed Work
- ✅ maestro/config/settings.py - Settings module with load/save/get/set/validate
- ✅ maestro/config/__init__.py - Package initialization

## Current State Analysis

The existing commands follow this pattern (see maestro/commands/track.py):
1. Command handler function (e.g., \`handle_track_command\`)
2. Subcommand functions (e.g., \`list_tracks\`, \`show_track\`, \`edit_track\`)
3. Argument parser setup (e.g., \`add_track_parser\`)
4. Help text functions

## Task Requirements

### Create \`maestro/commands/settings.py\`

Implement the settings command with these subcommands:

#### 1. \`maestro settings list\` or \`maestro settings\` (default)
Display all settings organized by section:
\`\`\`
Project Metadata:
  project_id: e152dd7f-83c7-4550-84ec-d053a6004470
  created_at: 2025-12-18T01:16:53
  maestro_version: 1.2.1
  base_dir: /home/user/project

User Preferences:
  default_editor: \$EDITOR (resolved: /usr/bin/vim)
  discussion_mode: editor
  list_format: table

AI Settings:
  ai_provider: anthropic
  ai_model: claude-3-5-sonnet-20250205
  ai_api_key_file: ~/.anthropic_key
  ai_context_window: 8192

Build Settings:
  default_build_method: auto
  parallel_jobs: 4
  verbose_builds: false

Display Settings:
  color_output: true
  unicode_symbols: true
  compact_lists: false

Current Context:
  current_track: cli-tpt
  current_phase: cli-tpt-4
  current_task: null
\`\`\`

Options:
- \`--section <name>\`: Show only one section (e.g., \`--section ai_settings\`)
- \`--json\`: Output in JSON format for machine parsing

#### 2. \`maestro settings get <key>\`
Show a single setting value with dot notation support:
\`\`\`
\$ maestro settings get ai_provider
anthropic

\$ maestro settings get default_editor
\$EDITOR (resolved: /usr/bin/vim)
\`\`\`

Options:
- \`--raw\`: Show unresolved value (e.g., \"\$EDITOR\" instead of \"/usr/bin/vim\")

#### 3. \`maestro settings set <key> <value>\`
Update a single setting with validation and confirmation:
\`\`\`
\$ maestro settings set ai_model claude-3-opus-20240620
Updated ai_model:
  old: claude-3-5-sonnet-20250205
  new: claude-3-opus-20240620

Configuration saved to docs/config.md
\`\`\`

Options:
- \`--no-confirm\`: Skip confirmation message

#### 4. \`maestro settings edit\` or \`maestro settings edit <section>\`
Open docs/config.md in \$EDITOR:
- If section specified, try to jump to that section (if editor supports line numbers)
- After editing, validate the config
- If validation fails, show error and offer to rollback

#### 5. \`maestro settings reset <key>\`
Reset a single setting to default:
\`\`\`
\$ maestro settings reset ai_model
Reset ai_model to default value: claude-3-5-sonnet-20250205
\`\`\`

#### 6. \`maestro settings reset --all\`
Reset all settings to defaults (requires \`--force\`):
\`\`\`
\$ maestro settings reset --all
Error: This will reset ALL settings to defaults. Use --force to confirm.

\$ maestro settings reset --all --force
All settings reset to defaults. Project metadata preserved.
Configuration saved to docs/config.md
\`\`\`

#### 7. \`maestro settings wizard\`
Interactive setup wizard for new projects:
\`\`\`
\$ maestro settings wizard

Maestro Configuration Wizard
============================

AI Provider (anthropic/openai/local) [anthropic]:
AI Model [claude-3-5-sonnet-20250205]:
AI API Key File [~/.anthropic_key]:

Default Editor [\$EDITOR]: vim
Discussion Mode (editor/terminal) [editor]:

Build Settings:
  Default Build Method (auto/make/cmake/...) [auto]:
  Parallel Jobs [4]: 8

Display Settings:
  Color Output (true/false) [true]:
  Unicode Symbols (true/false) [true]:

Configuration saved to docs/config.md
Run 'maestro settings list' to view your settings.
\`\`\`

## Implementation Structure

\`\`\`python
# maestro/commands/settings.py
from maestro.config.settings import Settings, get_settings, create_default_config
from pathlib import Path
import os
import subprocess

def list_settings(args):
    \"\"\"List all settings or a specific section.\"\"\"
    settings = get_settings()

    if args.json:
        # Output JSON format
        pass
    elif args.section:
        # Show only one section
        pass
    else:
        # Show all sections
        pass
    return 0

def get_setting(args):
    \"\"\"Get a single setting value.\"\"\"
    settings = get_settings()
    value = settings.get(args.key, None)

    if value is None:
        print(f\"Error: Setting '{args.key}' not found.\")
        return 1

    if args.raw:
        # Show unresolved value
        pass
    else:
        # Resolve paths and env vars
        pass
    return 0

def set_setting(args):
    \"\"\"Set a single setting value.\"\"\"
    settings = get_settings()
    old_value = settings.get(args.key, None)

    try:
        settings.set(args.key, args.value)
        settings.validate()
        settings.save()

        if not args.no_confirm:
            print(f\"Updated {args.key}:\")
            print(f\"  old: {old_value}\")
            print(f\"  new: {args.value}\")
        return 0
    except Exception as e:
        print(f\"Error: {e}\")
        return 1

def edit_settings(args):
    \"\"\"Edit settings in \$EDITOR.\"\"\"
    editor = os.environ.get('EDITOR', 'vim')
    config_path = Path('docs/config.md')

    # Open editor
    try:
        subprocess.run([editor, str(config_path)])

        # Validate after editing
        settings = Settings.load(config_path)
        settings.validate()
        return 0
    except Exception as e:
        print(f\"Error: {e}\")
        print(\"Configuration validation failed. Please check docs/config.md\")
        return 1

def reset_settings(args):
    \"\"\"Reset settings to defaults.\"\"\"
    if args.all:
        if not args.force:
            print(\"Error: This will reset ALL settings to defaults. Use --force to confirm.\")
            return 1

        # Reset all settings
        settings = create_default_config()
        # Preserve project metadata from existing config
        old_settings = get_settings()
        settings.project_id = old_settings.project_id
        settings.created_at = old_settings.created_at
        settings.save()
        print(\"All settings reset to defaults. Project metadata preserved.\")
        return 0
    else:
        # Reset single setting
        settings = get_settings()
        default_settings = create_default_config()
        default_value = default_settings.get(args.key, None)

        if default_value is None:
            print(f\"Error: Setting '{args.key}' not found.\")
            return 1

        settings.set(args.key, default_value)
        settings.save()
        print(f\"Reset {args.key} to default value: {default_value}\")
        return 0

def settings_wizard(args):
    \"\"\"Interactive configuration wizard.\"\"\"
    print()
    print(\"Maestro Configuration Wizard\")
    print(\"============================\")
    print()

    # Prompt for settings
    # Create settings from responses
    # Save to docs/config.md
    pass

def handle_settings_command(args):
    \"\"\"Main handler for settings commands.\"\"\"
    if hasattr(args, 'settings_subcommand'):
        if args.settings_subcommand == 'list' or args.settings_subcommand == 'ls':
            return list_settings(args)
        elif args.settings_subcommand == 'get':
            return get_setting(args)
        elif args.settings_subcommand == 'set':
            return set_setting(args)
        elif args.settings_subcommand == 'edit':
            return edit_settings(args)
        elif args.settings_subcommand == 'reset':
            return reset_settings(args)
        elif args.settings_subcommand == 'wizard':
            return settings_wizard(args)
        elif args.settings_subcommand == 'help' or args.settings_subcommand == 'h':
            print_settings_help()
            return 0

    # Default: list settings
    return list_settings(args)

def print_settings_help():
    \"\"\"Print help for settings commands.\"\"\"
    help_text = \"\"\"
maestro settings - Manage project configuration

USAGE:
    maestro settings                          List all settings
    maestro settings list                     List all settings
    maestro settings get <key>                Get a setting value
    maestro settings set <key> <value>        Set a setting value
    maestro settings edit                     Edit settings in \$EDITOR
    maestro settings reset <key>              Reset a setting to default
    maestro settings reset --all --force      Reset all settings
    maestro settings wizard                   Interactive setup wizard

OPTIONS:
    --section <name>    Show only one section (for list)
    --json              Output in JSON format (for list)
    --raw               Show unresolved value (for get)
    --no-confirm        Skip confirmation (for set)
    --force             Force operation (for reset --all)

EXAMPLES:
    maestro settings
    maestro settings list --section ai_settings
    maestro settings get ai_provider
    maestro settings set parallel_jobs 8
    maestro settings edit
    maestro settings reset ai_model
    maestro settings wizard
\"\"\"
    print(help_text)

def add_settings_parser(subparsers):
    \"\"\"Add settings command parser to main argument parser.\"\"\"
    settings_parser = subparsers.add_parser(
        'settings',
        aliases=['config', 'cfg'],
        help='Manage project configuration'
    )

    # Settings subcommands
    settings_subparsers = settings_parser.add_subparsers(
        dest='settings_subcommand',
        help='Settings subcommands'
    )

    # maestro settings list
    list_parser = settings_subparsers.add_parser('list', aliases=['ls', 'l'])
    list_parser.add_argument('--section', help='Show only one section')
    list_parser.add_argument('--json', action='store_true', help='Output JSON')

    # maestro settings get <key>
    get_parser = settings_subparsers.add_parser('get', aliases=['g'])
    get_parser.add_argument('key', help='Setting key (supports dot notation)')
    get_parser.add_argument('--raw', action='store_true', help='Show unresolved value')

    # maestro settings set <key> <value>
    set_parser = settings_subparsers.add_parser('set', aliases=['s'])
    set_parser.add_argument('key', help='Setting key (supports dot notation)')
    set_parser.add_argument('value', help='Setting value')
    set_parser.add_argument('--no-confirm', action='store_true', help='Skip confirmation')

    # maestro settings edit
    edit_parser = settings_subparsers.add_parser('edit', aliases=['e'])
    edit_parser.add_argument('section', nargs='?', help='Section to jump to')

    # maestro settings reset
    reset_parser = settings_subparsers.add_parser('reset', aliases=['r'])
    reset_parser.add_argument('key', nargs='?', help='Setting key to reset')
    reset_parser.add_argument('--all', action='store_true', help='Reset all settings')
    reset_parser.add_argument('--force', action='store_true', help='Force reset')

    # maestro settings wizard
    wizard_parser = settings_subparsers.add_parser('wizard', aliases=['w'])

    # maestro settings help
    settings_subparsers.add_parser('help', aliases=['h'])

    return settings_parser
\`\`\`

## Integration with main.py

The command needs to be registered in maestro/main.py. Add this import and parser:
\`\`\`python
from maestro.commands.settings import handle_settings_command, add_settings_parser

# In the argument parser setup:
add_settings_parser(subparsers)

# In the command routing:
elif args.command == 'settings' or args.command == 'config' or args.command == 'cfg':
    return handle_settings_command(args)
\`\`\`

## Deliverables
1. \`maestro/commands/settings.py\` - Complete settings command implementation
2. Integration code for maestro/main.py
3. Summary of implementation in \`cli4_task2_summary.txt\`

## Output Format
Create a unified diff file that can be applied with \`patch\` command.
Save it to: \`cli4_task2_settings_command.patch\`

## Testing
The command should:
- List all settings in organized format
- Support --section and --json flags
- Get/set individual settings with validation
- Open editor for manual editing with validation
- Reset settings to defaults
- Provide interactive wizard

Please implement this command following the existing command patterns in the
Maestro project (see maestro/commands/track.py as reference)."

# Run qwen with the task
echo "Starting qwen for CLI4 Task 2: Settings Command..."
echo "This may take 20+ minutes. Output will be saved to cli4_task2_output.txt"

~/node_modules/.bin/qwen -y "$TASK_PROMPT" 2>&1 | tee cli4_task2_output.txt

# Check if patch was created
if [ -f cli4_task2_settings_command.patch ]; then
    echo "Patch file created successfully!"
    echo "Review the patch before applying:"
    echo "  cat cli4_task2_settings_command.patch"
    echo "To apply the patch:"
    echo "  patch -p1 < cli4_task2_settings_command.patch"
else
    echo "Note: Patch file not found. Check cli4_task2_output.txt for implementation."
fi

echo "Task completed. Check cli4_task2_output.txt for full output."

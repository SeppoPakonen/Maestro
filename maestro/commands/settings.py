"""
Settings command implementation for Maestro CLI4.

Commands:
- maestro settings list - List all settings organized by section
- maestro settings get <key> - Get a single setting value
- maestro settings set <key> <value> - Set a single setting value
- maestro settings edit - Edit settings in $EDITOR
- maestro settings reset <key> - Reset a single setting to default
- maestro settings reset --all --force - Reset all settings
- maestro settings wizard - Interactive setup wizard
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any
from maestro.config.settings import get_settings, create_default_config, Settings
import sys


def list_settings(args):
    """List all settings or a specific section."""
    settings = get_settings()

    if args.json:
        # Output JSON format
        if args.section:
            section_data = settings.get_section(args.section.replace('-', '_'))
            print(json.dumps(section_data, indent=2))
        else:
            full_dict = settings.to_dict()
            print(json.dumps(full_dict, indent=2))
        return 0

    # Organized display
    sections_mapping = {
        'project_metadata': 'Project Metadata',
        'user_preferences': 'User Preferences',
        'ai_settings': 'AI Settings',
        'build_settings': 'Build Settings',
        'display_settings': 'Display Settings',
        'current_context': 'Current Context'
    }

    if args.section:
        # Show only the specified section
        section_key = args.section.replace('-', '_')
        if section_key in sections_mapping:
            section_name = sections_mapping[section_key]
            section_data = settings.get_section(section_key)
            
            print(f"\n{section_name}:")
            print("-" * len(section_name))
            
            for key, value in section_data.items():
                formatted_value = format_value_for_display(key, value)
                print(f"  {key}: {formatted_value}")
            print()
        else:
            print(f"Error: Unknown section '{args.section}'")
            return 1
    else:
        # Show all sections
        print()
        print("=" * 80)
        print("SETTINGS")
        print("=" * 80)
        print()

        for section_key, section_name in sections_mapping.items():
            section_data = settings.get_section(section_key)
            if section_data:  # Only show sections that have data
                print(f"{section_name}:")
                print("-" * len(section_name))
                
                for key, value in section_data.items():
                    formatted_value = format_value_for_display(key, value)
                    print(f"  {key}: {formatted_value}")
                print()

    return 0


def format_value_for_display(key: str, value: Any) -> str:
    """Format a value for display, resolving paths and environment variables where appropriate."""
    if key == 'default_editor' and value == '$EDITOR':
        resolved_editor = os.environ.get('EDITOR', 'vim')
        return f'$EDITOR (resolved: {resolved_editor})'
    
    if isinstance(value, bool):
        return str(value).lower()
    elif value is None:
        return 'null'
    elif isinstance(value, str) and value.startswith('~'):
        # Expand home directory for display
        return os.path.expanduser(value)
    else:
        return str(value)


def get_setting(args):
    """Get a single setting value."""
    settings = get_settings()
    
    # Try to get the setting value
    value = settings.get(args.key, None)
    
    if value is None:
        print(f"Error: Setting '{args.key}' not found.")
        return 1

    if args.raw:
        # Show unresolved value (for strings that might contain env vars)
        if isinstance(value, str):
            print(value)
        else:
            print(value)
    else:
        # Resolve paths and env vars for display
        formatted_value = format_value_for_display(args.key, value)
        print(formatted_value)
    
    return 0


def set_setting(args):
    """Set a single setting value."""
    settings = get_settings()

    # Check if the key exists by trying to get it first
    old_value = settings.get(args.key, None)
    if old_value is None and not hasattr(settings, args.key):
        print(f"Error: Setting '{args.key}' does not exist.")
        return 1

    try:
        # Convert the value to the appropriate type if needed
        # First, get the current type to determine conversion
        current_value = settings.get(args.key)
        converted_value = convert_value_to_type(args.value, type(current_value))

        settings.set(args.key, converted_value)
        settings.validate()
        settings.save()

        if not args.no_confirm:
            print(f"Updated {args.key}:")
            print(f"  old: {old_value}")
            print(f"  new: {converted_value}")

        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def convert_value_to_type(value_str, target_type):
    """Convert a string value to the appropriate type based on the target type."""
    if target_type == bool:
        if value_str.lower() in ('true', '1', 'yes', 'on'):
            return True
        elif value_str.lower() in ('false', '0', 'no', 'off'):
            return False
        else:
            raise ValueError(f"Cannot convert '{value_str}' to bool")
    elif target_type == int:
        try:
            return int(value_str)
        except ValueError:
            raise ValueError(f"Cannot convert '{value_str}' to int")
    elif target_type == float:
        try:
            return float(value_str)
        except ValueError:
            raise ValueError(f"Cannot convert '{value_str}' to float")
    elif target_type == str:
        return value_str
    elif target_type is type(None):
        if value_str.lower() in ('null', 'none', ''):
            return None
        else:
            return value_str
    else:
        # For other types, return as string
        return value_str


def edit_settings(args):
    """Edit settings in $EDITOR."""
    editor = os.environ.get('EDITOR', 'vim')
    config_path = Path('docs/config.md')

    # Ensure the config file exists before trying to edit
    if not config_path.exists():
        settings = create_default_config()
        settings.save(config_path)
        print(f"Created default config at {config_path}")

    try:
        # Open editor
        subprocess.run([editor, str(config_path)])

        # Validate after editing
        try:
            new_settings = Settings.load(config_path)
            new_settings.validate()
            print(f"Configuration validated successfully")
            return 0
        except Exception as e:
            print(f"Error: Configuration validation failed after editing - {e}")
            print("Please check docs/config.md")
            return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


def reset_settings(args):
    """Reset settings to defaults."""
    if args.all:
        if not args.force:
            print("Error: This will reset ALL settings to defaults. Use --force to confirm.")
            return 1

        # Reset all settings to defaults but preserve project metadata
        old_settings = get_settings()

        # Create new settings with defaults
        new_settings = create_default_config()

        # Preserve project metadata from existing config
        new_settings.project_id = old_settings.project_id
        new_settings.created_at = old_settings.created_at
        new_settings.base_dir = old_settings.base_dir
        new_settings.maestro_version = old_settings.maestro_version

        # Save the new settings
        new_settings.save()
        print("All settings reset to defaults. Project metadata preserved.")
        return 0
    else:
        if not args.key:
            print("Error: Key required for reset. Usage: maestro settings reset <key>")
            return 1

        # Reset single setting
        settings = get_settings()

        # Create default settings to get the default value
        default_settings = create_default_config()

        # Check if the key exists in the current settings
        current_value = settings.get(args.key, None)
        if current_value is None and not hasattr(settings, args.key):
            print(f"Error: Setting '{args.key}' not found.")
            return 1

        # Get the default value
        default_value = default_settings.get(args.key)
        if default_value is None:
            print(f"Error: Setting '{args.key}' not found in default config.")
            return 1

        # Set the setting to the default value
        settings.set(args.key, default_value)
        settings.save()
        print(f"Reset {args.key} to default value: {default_value}")
        return 0


def settings_wizard(args):
    """Interactive configuration wizard."""
    print()
    print("Maestro Configuration Wizard")
    print("============================")
    print()

    # Start with default config and update values based on user input
    settings = create_default_config()

    # AI Provider
    ai_provider = input(f"AI Provider (anthropic/openai/local) [{settings.ai_provider}]: ").strip()
    if ai_provider:
        settings.ai_provider = ai_provider

    # AI Model
    ai_model = input(f"AI Model [{settings.ai_model}]: ").strip()
    if ai_model:
        settings.ai_model = ai_model

    # AI API Key File
    ai_api_key_file = input(f"AI API Key File [{settings.ai_api_key_file}]: ").strip()
    if ai_api_key_file:
        settings.ai_api_key_file = ai_api_key_file

    # Default Editor
    default_editor = input(f"Default Editor [$EDITOR]: ").strip()
    if default_editor:
        settings.default_editor = default_editor
    elif default_editor == "":  # User pressed Enter to keep default
        pass  # Keep the default '$EDITOR'

    # Discussion Mode
    discussion_mode = input(f"Discussion Mode (editor/terminal) [{settings.discussion_mode}]: ").strip()
    if discussion_mode:
        settings.discussion_mode = discussion_mode

    print("\nBuild Settings:")
    default_build_method = input(f"  Default Build Method (auto/make/cmake/...) [{settings.default_build_method}]: ").strip()
    if default_build_method:
        settings.default_build_method = default_build_method

    parallel_jobs = input(f"  Parallel Jobs [{settings.parallel_jobs}]: ").strip()
    if parallel_jobs:
        try:
            settings.parallel_jobs = int(parallel_jobs)
        except ValueError:
            print(f"Warning: Invalid value for parallel_jobs, keeping default: {settings.parallel_jobs}")

    print("\nDisplay Settings:")
    color_output = input(f"  Color Output (true/false) [{settings.color_output}]: ").strip()
    if color_output:
        settings.color_output = color_output.lower() in ['true', '1', 'yes', 'on']

    unicode_symbols = input(f"  Unicode Symbols (true/false) [{settings.unicode_symbols}]: ").strip()
    if unicode_symbols:
        settings.unicode_symbols = unicode_symbols.lower() in ['true', '1', 'yes', 'on']

    # Save the new settings
    saved_successfully = settings.save()
    if saved_successfully:
        print("\nConfiguration saved to docs/config.md")
        print("Run 'maestro settings list' to view your settings.")
        return 0
    else:
        print("\nError: Failed to save configuration")
        return 1


def handle_settings_command(args):
    """Main handler for settings commands."""
    if hasattr(args, 'settings_subcommand'):
        if args.settings_subcommand in ['list', 'ls', 'l']:
            return list_settings(args)
        elif args.settings_subcommand in ['get', 'g']:
            return get_setting(args)
        elif args.settings_subcommand in ['set', 's']:
            return set_setting(args)
        elif args.settings_subcommand in ['edit', 'e']:
            return edit_settings(args)
        elif args.settings_subcommand in ['reset', 'r']:
            return reset_settings(args)
        elif args.settings_subcommand in ['wizard', 'w']:
            return settings_wizard(args)
        elif args.settings_subcommand in ['help', 'h']:
            print_settings_help()
            return 0

    # Default: list settings
    # Create a mock args object with the necessary attributes for listing
    import argparse
    if not hasattr(args, 'json'):
        args.json = False
    if not hasattr(args, 'section'):
        args.section = None
    
    return list_settings(args)


def print_settings_help():
    """Print help for settings commands."""
    help_text = """
maestro settings - Manage project configuration

USAGE:
    maestro settings                          List all settings
    maestro settings list                     List all settings
    maestro settings get <key>                Get a setting value
    maestro settings set <key> <value>        Set a setting value
    maestro settings edit                     Edit settings in $EDITOR
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
"""
    print(help_text)


def add_settings_parser(subparsers):
    """Add settings command parser to main argument parser."""
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
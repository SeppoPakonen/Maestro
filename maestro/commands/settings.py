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
- maestro settings profile list - List all settings profiles
- maestro settings profile save <name> - Save current settings to a profile
- maestro settings profile load <name|number> - Load settings from a profile
- maestro settings profile get - Get active profile
- maestro settings profile set-default <name|number> - Set default profile
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from maestro.config.settings import get_settings, create_default_config, Settings
from maestro.config.settings_profiles import SettingsProfileManager


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

                # Special handling for AI settings to show engine matrix and per-engine blocks
                if section_key == 'ai_settings':
                    # Group engine enablement settings
                    engine_keys = ['ai_engines_claude', 'ai_engines_codex', 'ai_engines_gemini', 'ai_engines_qwen']
                    engine_settings = {}

                    # Extract engine settings
                    for key in engine_keys:
                        if key in section_data:
                            engine_settings[key] = section_data[key]

                    # Group per-engine settings
                    claude_settings = {}
                    codex_settings = {}
                    gemini_settings = {}
                    qwen_settings = {}

                    for key, value in section_data.items():
                        if key.startswith('ai_claude_') and key not in engine_keys:
                            claude_settings[key] = value
                        elif key.startswith('ai_codex_') and key not in engine_keys:
                            codex_settings[key] = value
                        elif key.startswith('ai_gemini_') and key not in engine_keys:
                            gemini_settings[key] = value
                        elif key.startswith('ai_qwen_') and key not in engine_keys:
                            qwen_settings[key] = value

                    # Create a copy of section_data without engine and per-engine settings
                    other_ai_settings = {
                        k: v for k, v in section_data.items()
                        if k not in engine_keys
                        and not k.startswith('ai_claude_')
                        and not k.startswith('ai_codex_')
                        and not k.startswith('ai_gemini_')
                        and not k.startswith('ai_qwen_')
                    }

                    # Display AI engine matrix if any engine settings exist
                    if engine_settings:
                        print("  AI Engines:")
                        for engine_key, engine_value in engine_settings.items():
                            print(f"    {engine_key}: {format_value_for_display(engine_key, engine_value)}")

                    # Display other AI settings (stacking mode, permissions, etc.)
                    for key, value in other_ai_settings.items():
                        formatted_value = format_value_for_display(key, value)
                        print(f"  {key}: {formatted_value}")

                    # Display per-engine settings if they exist
                    if claude_settings:
                        print("\n  Claude:")
                        for key, value in claude_settings.items():
                            formatted_value = format_value_for_display(key, value)
                            print(f"    {key}: {formatted_value}")

                    if codex_settings:
                        print("\n  Codex:")
                        for key, value in codex_settings.items():
                            formatted_value = format_value_for_display(key, value)
                            print(f"    {key}: {formatted_value}")

                    if gemini_settings:
                        print("\n  Gemini:")
                        for key, value in gemini_settings.items():
                            formatted_value = format_value_for_display(key, value)
                            print(f"    {key}: {formatted_value}")

                    if qwen_settings:
                        print("\n  Qwen:")
                        for key, value in qwen_settings.items():
                            formatted_value = format_value_for_display(key, value)
                            print(f"    {key}: {formatted_value}")
                else:
                    # Display other sections normally
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

    # Check if this is a valid AI engine setting path before checking if value is None
    parts = args.key.split('.')
    is_valid_ai_path = False
    if parts[0] == 'ai' and len(parts) >= 2:
        if parts[1] == 'engines' and len(parts) == 3 and parts[2] in ['claude', 'codex', 'gemini', 'qwen']:
            is_valid_ai_path = True
        elif parts[1] == 'qwen' and len(parts) >= 3 and parts[2] in ['use_stdio_or_tcp', 'transport', 'tcp_host', 'tcp_port']:
            is_valid_ai_path = True
        elif parts[1] == 'stacking_mode' and len(parts) == 2:
            is_valid_ai_path = True

    # If it's a valid path but value is None, it means the setting doesn't exist
    if value is None and not is_valid_ai_path:
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
    if old_value is None and not hasattr(settings, args.key.split('.')[-1]):
        # Check for dot notation keys specifically for AI engine settings
        parts = args.key.split('.')
        if parts[0] == 'ai' and len(parts) >= 2:
            if parts[1] == 'engines' and len(parts) == 3:
                # Valid engine setting path
                pass
            elif parts[1] == 'qwen' and len(parts) >= 3:
                # Valid qwen setting path
                pass
            elif parts[1] == 'stacking_mode' and len(parts) == 2:
                # Valid stacking mode setting path
                pass
            else:
                print(f"Error: Setting '{args.key}' does not exist.")
                return 1
        else:
            print(f"Error: Setting '{args.key}' does not exist.")
            return 1

    try:
        # Convert the value to the appropriate type if needed
        # First, get the current type to determine conversion
        current_value = settings.get(args.key)
        target_type = type(current_value) if current_value is not None else str
        converted_value = convert_value_to_type(args.value, target_type)

        # Get the original hash to detect changes
        profile_manager = SettingsProfileManager()
        original_hash = profile_manager.get_settings_hash()

        settings.set(args.key, converted_value)
        settings.validate()
        settings.save()

        # Check if settings have changed compared to the active profile
        new_hash = profile_manager.get_settings_hash()
        if original_hash != new_hash:
            active_profile = profile_manager.get_active_profile()
            if active_profile:
                print(f"Active profile: {active_profile['name']} (unsaved changes)")

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

    # Get the original hash to detect changes
    profile_manager = SettingsProfileManager()
    original_hash = profile_manager.get_settings_hash()

    try:
        # Open editor
        subprocess.run([editor, str(config_path)])

        # Validate after editing
        try:
            new_settings = Settings.load(config_path)
            new_settings.validate()
            print(f"Configuration validated successfully")

            # Check if settings have changed compared to the active profile
            new_hash = profile_manager.get_settings_hash()
            if original_hash != new_hash:
                active_profile = profile_manager.get_active_profile()
                if active_profile:
                    print(f"Active profile: {active_profile['name']} (unsaved changes)")

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
    # Get the original hash to detect changes
    profile_manager = SettingsProfileManager()
    original_hash = profile_manager.get_settings_hash()

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

    # Check if settings have changed compared to the active profile
    new_hash = profile_manager.get_settings_hash()
    if original_hash != new_hash:
        active_profile = profile_manager.get_active_profile()
        if active_profile:
            print(f"Active profile: {active_profile['name']} (unsaved changes)")

    return 0


def settings_wizard(args):
    """Interactive configuration wizard."""
    print()
    print("Maestro Configuration Wizard")
    print("============================")
    print()

    # Start with default config and update values based on user input
    settings = create_default_config()

    # Get the original hash to detect changes
    profile_manager = SettingsProfileManager()
    original_hash = profile_manager.get_settings_hash()

    # AI Provider (legacy)
    print("AI Settings:")
    ai_provider = input(f"  AI Provider (anthropic/openai/local) [{settings.ai_provider}]: ").strip()
    if ai_provider:
        settings.ai_provider = ai_provider

    # AI Model (legacy)
    ai_model = input(f"  AI Model [{settings.ai_model}]: ").strip()
    if ai_model:
        settings.ai_model = ai_model

    # AI API Key File (legacy)
    ai_api_key_file = input(f"  AI API Key File [{settings.ai_api_key_file}]: ").strip()
    if ai_api_key_file:
        settings.ai_api_key_file = ai_api_key_file

    # AI Engine Matrix
    print("\nAI Engine Configuration:")
    print("  Engine roles: disabled, planner, worker, both")
    claude_role = input(f"  Claude role (disabled/planner/worker/both) [{settings.ai_engines_claude}]: ").strip()
    if claude_role:
        settings.ai_engines_claude = claude_role

    codex_role = input(f"  Codex role (disabled/planner/worker/both) [{settings.ai_engines_codex}]: ").strip()
    if codex_role:
        settings.ai_engines_codex = codex_role

    gemini_role = input(f"  Gemini role (disabled/planner/worker/both) [{settings.ai_engines_gemini}]: ").strip()
    if gemini_role:
        settings.ai_engines_gemini = gemini_role

    qwen_role = input(f"  Qwen role (disabled/planner/worker/both) [{settings.ai_engines_qwen}]: ").strip()
    if qwen_role:
        settings.ai_engines_qwen = qwen_role

    # AI Stacking Mode
    stacking_mode = input(f"  AI Stacking Mode (managed/handsoff) [{settings.ai_stacking_mode}]: ").strip()
    if stacking_mode:
        settings.ai_stacking_mode = stacking_mode

    # Global AI Permissions
    print("\nGlobal AI Permissions:")
    dangerously_skip_permissions = input(f"  Dangerously skip permissions (true/false) [{settings.ai_dangerously_skip_permissions}]: ").strip()
    if dangerously_skip_permissions:
        settings.ai_dangerously_skip_permissions = dangerously_skip_permissions.lower() in ['true', '1', 'yes', 'on']

    # Qwen Transport Settings
    print("\nQwen Transport Settings:")
    qwen_transport = input(f"  Qwen transport (cmdline/stdio/tcp) [{settings.ai_qwen_transport}]: ").strip()
    if qwen_transport:
        settings.ai_qwen_transport = qwen_transport
    qwen_tcp_host = input(f"  Qwen TCP host [{settings.ai_qwen_tcp_host}]: ").strip()
    if qwen_tcp_host:
        settings.ai_qwen_tcp_host = qwen_tcp_host
    qwen_tcp_port = input(f"  Qwen TCP port [{settings.ai_qwen_tcp_port}]: ").strip()
    if qwen_tcp_port:
        try:
            settings.ai_qwen_tcp_port = int(qwen_tcp_port)
        except ValueError:
            print(f"Warning: Invalid value for qwen_tcp_port, keeping default: {settings.ai_qwen_tcp_port}")

    # Default Editor
    print("\nUser Preferences:")
    default_editor = input(f"  Default Editor [$EDITOR]: ").strip()
    if default_editor:
        settings.default_editor = default_editor
    elif default_editor == "":  # User pressed Enter to keep default
        pass  # Keep the default '$EDITOR'

    # Discussion Mode
    discussion_mode = input(f"  Discussion Mode (editor/terminal) [{settings.discussion_mode}]: ").strip()
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
        # Check if settings have changed compared to the active profile
        new_hash = profile_manager.get_settings_hash()
        if original_hash != new_hash:
            active_profile = profile_manager.get_active_profile()
            if active_profile:
                print(f"Active profile: {active_profile['name']} (unsaved changes)")

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
        elif args.settings_subcommand in ['profile', 'prof', 'pr']:
            # Handle profile subcommands
            if hasattr(args, 'profile_subcommand'):
                if args.profile_subcommand in ['list', 'ls']:
                    return profile_list(args)
                elif args.profile_subcommand in ['save', 's']:
                    return profile_save(args)
                elif args.profile_subcommand in ['load', 'l']:
                    return profile_load(args)
                elif args.profile_subcommand in ['get', 'g']:
                    return profile_get(args)
                elif args.profile_subcommand in ['set-default', 'sd']:
                    return profile_set_default(args)
                elif args.profile_subcommand in ['help', 'h']:
                    print_profile_help()
                    return 0
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


def print_profile_help():
    """Print help for settings profile commands."""
    help_text = """
maestro settings profile - Manage settings profiles

USAGE:
    maestro settings profile list                List all profiles
    maestro settings profile save [name]         Save current settings to a profile
    maestro settings profile load <name|number>  Load settings from a profile
    maestro settings profile get                 Get active profile
    maestro settings profile set-default <name|number> Set default profile

FLAGS:
    -y, --yes              Auto-confirm operations (skip prompts)
    --make-active          Set saved profile as active immediately
    --set-default          Set saved profile as default

OPTIONS:
    --json                 Output in JSON format (for list)

EXAMPLES:
    maestro settings profile list
    maestro settings profile save dev-fast
    maestro settings profile save dev-fast --make-active --set-default -y
    maestro settings profile load dev-fast
    maestro settings profile load 1
    maestro settings profile get
    maestro settings profile set-default dev-fast
"""
    print(help_text)


def profile_list(args):
    """List all settings profiles."""
    profile_manager = SettingsProfileManager()
    profiles = profile_manager.list_profiles()
    active_profile = profile_manager.get_active_profile()
    default_profile = profile_manager.get_default_profile()

    if args.json:
        # Output JSON format
        result = {
            "profiles": profiles,
            "active_profile": active_profile,
            "default_profile": default_profile
        }
        print(json.dumps(result, indent=2))
        return 0

    # Human-readable format
    if not profiles:
        print("No profiles found.")
        return 0

    for i, profile in enumerate(profiles, 1):
        is_active = active_profile and profile["id"] == active_profile["id"]
        is_default = default_profile and profile["id"] == default_profile["id"]

        marker = ""
        if is_active and is_default:
            marker = "*D"
        elif is_active:
            marker = "* "
        elif is_default:
            marker = " D"
        else:
            marker = "  "

        # Format the updated time
        updated_at = profile.get("updated_at", "")
        if updated_at:
            # Parse and format the datetime
            try:
                dt = updated_at.split("T")[0] + " " + updated_at.split("T")[1].split(".")[0][:5]
            except:
                dt = updated_at
        else:
            dt = "unknown"

        # Truncate ID to 8 characters for display
        profile_id = profile["id"][:8]

        print(f"[{i}] {marker} {profile['name']} ({profile_id})  updated {dt}")

    return 0


def profile_save(args):
    """Save current settings to a profile."""
    profile_manager = SettingsProfileManager()

    # Determine the profile name to use
    profile_id = None
    profile_name = None

    if args.name_or_number is None:
        # If no name provided, check for active or default profile
        active_profile = profile_manager.get_active_profile()
        default_profile = profile_manager.get_default_profile()

        if active_profile:
            profile_id = active_profile["id"]
            profile_name = active_profile["name"]
        elif default_profile:
            profile_id = default_profile["id"]
            profile_name = default_profile["name"]
        else:
            print("Error: No active or default profile. Please provide a name or set default.")
            return 1
    else:
        # Check if the argument is a number
        try:
            profile_num = int(args.name_or_number)
            profile_info = profile_manager.get_profile_by_number(profile_num)
            if profile_info:
                profile_id = profile_info["id"]
                profile_name = profile_info["name"]
            else:
                print(f"Error: Profile number {profile_num} not found.")
                return 1
        except ValueError:
            # Not a number, treat as name
            profile_info = profile_manager.get_profile_by_name(args.name_or_number)
            if profile_info:
                # Profile exists, we'll update it
                profile_id = profile_info["id"]
                profile_name = profile_info["name"]
            else:
                # Profile doesn't exist, we'll create a new one
                profile_name = args.name_or_number
                profile_id = None

    current_settings = get_settings()

    if profile_id is not None:
        # Profile exists, ask for confirmation if not using --yes
        if not args.yes:
            response = input(f"Profile '{profile_name}' exists. Overwrite? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Operation cancelled.")
                return 0

        # Update existing profile
        success = profile_manager.update_profile(profile_id, current_settings)
        if success:
            print(f"Profile '{profile_name}' updated successfully.")
        else:
            print(f"Error updating profile '{profile_name}'.")
            return 1
    else:
        # Create new profile
        profile_id = profile_manager.create_profile(profile_name, current_settings)
        if profile_id:
            print(f"Profile '{profile_name}' created successfully.")

            # Set as active if --make-active flag is provided
            if args.make_active:
                profile_manager.set_active_profile(profile_id)
                print(f"Profile '{profile_name}' set as active.")

            # Set as default if --set-default flag is provided
            if args.set_default:
                profile_manager.set_default_profile(profile_id)
                print(f"Profile '{profile_name}' set as default.")
        else:
            print(f"Error creating profile '{profile_name}'.")
            return 1

    return 0


def profile_load(args):
    """Load settings from a profile."""
    if not args.name_or_number:
        print("Error: Profile name or number required for load command.")
        return 1

    profile_manager = SettingsProfileManager()

    # Try to find the profile by number first
    try:
        profile_num = int(args.name_or_number)
        profile_info = profile_manager.get_profile_by_number(profile_num)
    except ValueError:
        # Not a number, try by name
        profile_info = profile_manager.get_profile_by_name(args.name_or_number)

    if not profile_info:
        print(f"Error: Profile '{args.name_or_number}' not found.")
        return 1

    # Get current settings hash for audit trail
    current_hash = profile_manager.get_settings_hash()

    # Load the profile settings
    profile_settings = profile_manager.load_profile(profile_info["id"])
    if not profile_settings:
        print(f"Error: Could not load settings from profile '{profile_info['name']}'.")
        return 1

    # Check for unsaved changes before applying
    if profile_manager.has_unsaved_changes():
        print("Warning: Current settings have unsaved changes compared to the active profile.")
        if not args.yes:
            response = input("Continue anyway? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Operation cancelled.")
                return 0

    # Apply the settings by saving to the active config file
    profile_settings.save()
    print(f"Settings loaded from profile '{profile_info['name']}' successfully.")

    # Calculate new hash for audit trail
    new_hash = profile_manager.get_settings_hash()

    # Create audit trail
    profile_manager.create_audit_log(
        previous_settings_hash=current_hash,
        new_settings_hash=new_hash,
        profile_id=profile_info["id"],
        profile_name=profile_info["name"],
        diff_summary="Settings loaded from profile"
    )

    return 0


def profile_get(args):
    """Get the active profile."""
    profile_manager = SettingsProfileManager()
    active_profile = profile_manager.get_active_profile()

    if active_profile:
        print(f"{active_profile['name']} ({active_profile['id'][:8]})")
    else:
        print("none")

    return 0


def profile_set_default(args):
    """Set the default profile."""
    if not args.name_or_number:
        print("Error: Profile name or number required for set-default command.")
        return 1

    profile_manager = SettingsProfileManager()

    # Try to find the profile by number first
    try:
        profile_num = int(args.name_or_number)
        profile_info = profile_manager.get_profile_by_number(profile_num)
    except ValueError:
        # Not a number, try by name
        profile_info = profile_manager.get_profile_by_name(args.name_or_number)

    if not profile_info:
        print(f"Error: Profile '{args.name_or_number}' not found.")
        return 1

    success = profile_manager.set_default_profile(profile_info["id"])
    if success:
        print(f"Profile '{profile_info['name']}' set as default.")
    else:
        print(f"Error setting profile '{profile_info['name']}' as default.")
        return 1

    return 0


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

PROFILE COMMANDS:
    maestro settings profile list              List all profiles
    maestro settings profile save [name]       Save current settings
    maestro settings profile load <name>       Load settings from profile
    maestro settings profile get               Get active profile
    maestro settings profile set-default <name> Set default profile

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

    maestro settings profile list
    maestro settings profile save dev-fast --make-active --set-default
    maestro settings profile load dev-fast
    maestro settings profile get
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

    # maestro settings profile
    profile_parser = settings_subparsers.add_parser('profile', aliases=['prof', 'pr'], help='Manage settings profiles')
    profile_subparsers = profile_parser.add_subparsers(dest='profile_subcommand', help='Profile subcommands')

    # maestro settings profile list
    profile_list_parser = profile_subparsers.add_parser('list', aliases=['ls'], help='List all profiles')
    profile_list_parser.add_argument('--json', action='store_true', help='Output JSON')

    # maestro settings profile save
    profile_save_parser = profile_subparsers.add_parser('save', aliases=['s'], help='Save current settings to a profile')
    profile_save_parser.add_argument('name_or_number', nargs='?', help='Profile name or number')
    profile_save_parser.add_argument('-y', '--yes', action='store_true', help='Auto-confirm operations')
    profile_save_parser.add_argument('--make-active', action='store_true', help='Set saved profile as active')
    profile_save_parser.add_argument('--set-default', action='store_true', help='Set saved profile as default')

    # maestro settings profile load
    profile_load_parser = profile_subparsers.add_parser('load', aliases=['l'], help='Load settings from a profile')
    profile_load_parser.add_argument('name_or_number', help='Profile name or number')
    profile_load_parser.add_argument('-y', '--yes', action='store_true', help='Auto-confirm operations')

    # maestro settings profile get
    profile_get_parser = profile_subparsers.add_parser('get', aliases=['g'], help='Get active profile')

    # maestro settings profile set-default
    profile_set_default_parser = profile_subparsers.add_parser('set-default', aliases=['sd'], help='Set default profile')
    profile_set_default_parser.add_argument('name_or_number', help='Profile name or number')

    # maestro settings help
    settings_subparsers.add_parser('help', aliases=['h'])
    profile_subparsers.add_parser('help', aliases=['h'])

    return settings_parser
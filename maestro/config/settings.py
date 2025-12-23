"""
Maestro Settings Module

This module implements the settings management system for Maestro CLI4,
storing configuration in docs/config.md instead of the legacy ~/.maestro/config.toml.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union
import uuid
from datetime import datetime
import os
from maestro.data.markdown_parser import parse_config_md


class InvalidSettingError(Exception):
    """Exception raised when a setting fails validation."""
    pass


@dataclass
class Settings:
    # Project Metadata
    project_id: str
    created_at: str
    maestro_version: str
    base_dir: str
    settings_schema_version: str = "1.2.1"  # Version of the settings schema

    # User Preferences
    default_editor: str = "$EDITOR"
    discussion_mode: str = "editor"
    list_format: str = "table"

    # AI Settings
    ai_provider: str = "anthropic"
    ai_model: str = "claude-3-5-sonnet-20250205"
    ai_api_key_file: str = "~/.anthropic_key"
    ai_context_window: int = 8192
    ai_temperature: float = 0.7
    # AI Engine Matrix
    ai_engines_claude: str = "both"  # disabled, planner, worker, both
    ai_engines_codex: str = "both"   # disabled, planner, worker, both
    ai_engines_gemini: str = "both"  # disabled, planner, worker, both
    ai_engines_qwen: str = "both"    # disabled, planner, worker, both
    # AI Stacking Mode
    ai_stacking_mode: str = "managed"  # managed, handsoff
    # Global AI Permissions
    ai_dangerously_skip_permissions: bool = True  # Allow wrappers to use bypass flags automatically
    # Qwen Transport Settings
    ai_qwen_transport: str = "cmdline"  # cmdline, stdio, tcp
    ai_qwen_tcp_host: str = "localhost"  # TCP host for qwen transport
    ai_qwen_tcp_port: int = 7777  # TCP port for qwen transport

    # Build Settings
    default_build_method: str = "auto"
    parallel_jobs: int = 4
    verbose_builds: bool = False
    clean_before_build: bool = False

    # Display Settings
    color_output: bool = True
    unicode_symbols: bool = True
    compact_lists: bool = False
    show_completion_bars: bool = True

    # Current Context
    current_track: Optional[str] = None
    current_phase: Optional[str] = None
    current_task: Optional[str] = None

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'Settings':
        """
        Load settings from docs/config.md file.
        
        Args:
            config_path: Path to config file (defaults to docs/config.md)
            
        Returns:
            Loaded Settings instance
        """
        if config_path is None:
            config_path = Path("docs/config.md")
        
        if not config_path.exists():
            # If config doesn't exist, return default config
            return create_default_config()
        
        config_data = parse_config_md(str(config_path))
        
        # Map config sections to individual fields
        # The parser flattens the config, so all keys are at the top level
        settings_kwargs = {}
        
        # Project Metadata
        settings_kwargs['project_id'] = config_data.get('project_id', str(uuid.uuid4()))
        settings_kwargs['created_at'] = config_data.get('created_at', datetime.now().isoformat())
        settings_kwargs['maestro_version'] = config_data.get('maestro_version', '1.0.0')
        settings_kwargs['base_dir'] = config_data.get('base_dir', str(Path.cwd()))
        settings_kwargs['settings_schema_version'] = config_data.get('settings_schema_version', '1.2.1')

        # User Preferences
        settings_kwargs['default_editor'] = config_data.get('default_editor', '$EDITOR')
        settings_kwargs['discussion_mode'] = config_data.get('discussion_mode', 'editor')
        settings_kwargs['list_format'] = config_data.get('list_format', 'table')

        # AI Settings
        settings_kwargs['ai_provider'] = config_data.get('ai_provider', 'anthropic')
        settings_kwargs['ai_model'] = config_data.get('ai_model', 'claude-3-5-sonnet-20250205')
        settings_kwargs['ai_api_key_file'] = config_data.get('ai_api_key_file', '~/.anthropic_key')
        settings_kwargs['ai_context_window'] = config_data.get('ai_context_window', 8192)
        settings_kwargs['ai_temperature'] = config_data.get('ai_temperature', 0.7)
        # AI Engine Matrix
        settings_kwargs['ai_engines_claude'] = config_data.get('ai_engines_claude', 'both')
        settings_kwargs['ai_engines_codex'] = config_data.get('ai_engines_codex', 'both')
        settings_kwargs['ai_engines_gemini'] = config_data.get('ai_engines_gemini', 'both')
        settings_kwargs['ai_engines_qwen'] = config_data.get('ai_engines_qwen', 'both')
        # AI Stacking Mode
        settings_kwargs['ai_stacking_mode'] = config_data.get('ai_stacking_mode', 'managed')
        # Global AI Permissions
        settings_kwargs['ai_dangerously_skip_permissions'] = config_data.get('ai_dangerously_skip_permissions', True)
        # Qwen Transport Settings
        settings_kwargs['ai_qwen_transport'] = config_data.get('ai_qwen_transport', 'cmdline')
        settings_kwargs['ai_qwen_tcp_host'] = config_data.get('ai_qwen_tcp_host', 'localhost')
        settings_kwargs['ai_qwen_tcp_port'] = config_data.get('ai_qwen_tcp_port', 7777)

        # Build Settings
        settings_kwargs['default_build_method'] = config_data.get('default_build_method', 'auto')
        settings_kwargs['parallel_jobs'] = config_data.get('parallel_jobs', 4)
        settings_kwargs['verbose_builds'] = config_data.get('verbose_builds', False)
        settings_kwargs['clean_before_build'] = config_data.get('clean_before_build', False)

        # Display Settings
        settings_kwargs['color_output'] = config_data.get('color_output', True)
        settings_kwargs['unicode_symbols'] = config_data.get('unicode_symbols', True)
        settings_kwargs['compact_lists'] = config_data.get('compact_lists', False)
        settings_kwargs['show_completion_bars'] = config_data.get('show_completion_bars', True)

        # Current Context
        settings_kwargs['current_track'] = config_data.get('current_track', None)
        settings_kwargs['current_phase'] = config_data.get('current_phase', None)
        settings_kwargs['current_task'] = config_data.get('current_task', None)

        settings = cls(**settings_kwargs)
        settings.validate()
        return settings

    def save(self, config_path: Optional[Path] = None) -> bool:
        """
        Save settings to docs/config.md file.

        Args:
            config_path: Path to config file (defaults to docs/config.md)

        Returns:
            True if save was successful, False otherwise
        """
        if config_path is None:
            config_path = Path("docs/config.md")
        else:
            # Ensure config_path is a Path object
            config_path = Path(config_path) if isinstance(config_path, str) else config_path

        try:
            # Ensure the docs directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert settings to dictionary organized by sections
            config_dict = self.to_dict()
            
            # Format the markdown content
            md_content = "# Maestro Configuration\n\n"
            md_content += f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d')}\n\n"
            md_content += "---\n\n"
            
            # Add each section
            for section_name, section_data in config_dict.items():
                md_content += f"## {section_name.replace('_', ' ').title()}\n\n"

                # Convert values to appropriate format for markdown
                for key, value in section_data.items():
                    formatted_value = self._format_value_for_markdown(value)
                    md_content += f'"{key}": {formatted_value}\n'

                md_content += "\n---\n\n"
            
            # Add notes section
            md_content += "## Notes\n\n"
            md_content += self._get_notes_content()
            
            # Write to file
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            return True
        except Exception as e:
            print(f"Error saving settings to {config_path}: {e}")
            return False

    def _format_value_for_markdown(self, value: Any) -> str:
        """Format a value for markdown representation."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            # Escape quotes in strings
            escaped_value = value.replace('"', '\\"')
            return f'"{escaped_value}"'
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            # For any other types, convert to string
            return f'"{str(value)}"'
    
    def _get_notes_content(self) -> str:
        """Return the notes content for the config file."""
        return """This configuration file is both human-readable and machine-parsable. You can:

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
"""
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value using dot notation (e.g., 'ai.provider').

        Args:
            key: Setting key in dot notation
            default: Default value if key is not found

        Returns:
            Setting value or default
        """
        # Split the key by dots to handle nested access
        parts = key.split('.')

        # For compatibility with flat access, first try direct attribute access
        if len(parts) == 1:
            try:
                return getattr(self, key)
            except AttributeError:
                # Not a direct attribute, try to find in sections
                pass

        # Handle dot notation for AI engine settings
        if parts[0] == 'ai' and len(parts) >= 2:
            if parts[1] == 'engines' and len(parts) == 3:
                engine_map = {
                    'claude': 'ai_engines_claude',
                    'codex': 'ai_engines_codex',
                    'gemini': 'ai_engines_gemini',
                    'qwen': 'ai_engines_qwen'
                }
                if parts[2] in engine_map:
                    return getattr(self, engine_map[parts[2]])
            elif parts[1] == 'qwen' and len(parts) >= 3:
                qwen_setting_map = {
                    'transport': 'ai_qwen_transport',
                    'tcp_host': 'ai_qwen_tcp_host',
                    'tcp_port': 'ai_qwen_tcp_port'
                }
                if parts[2] in qwen_setting_map:
                    return getattr(self, qwen_setting_map[parts[2]])
            elif parts[1] == 'stacking_mode' and len(parts) == 2:
                return getattr(self, 'ai_stacking_mode')
            elif parts[1] == 'dangerously_skip_permissions' and len(parts) == 2:
                return getattr(self, 'ai_dangerously_skip_permissions')

        # Navigate through sections using the parts
        current_obj = self
        for part in parts:
            try:
                current_obj = getattr(current_obj, part)
            except AttributeError:
                # If the part isn't an attribute, try looking in the flat representation
                # This handles cases like 'ai.provider' where ai is not an object
                try:
                    flat_dict = self.to_dict_flat()
                    return flat_dict.get(key, default)
                except:
                    return default

        return current_obj
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a setting value using dot notation (e.g., 'ai.provider').

        Args:
            key: Setting key in dot notation
            value: Value to set
        """
        parts = key.split('.')

        if len(parts) == 1:
            # Direct attribute assignment
            setattr(self, key, value)
        else:
            # Handle dot notation for AI engine settings
            if parts[0] == 'ai' and len(parts) >= 2:
                if parts[1] == 'engines' and len(parts) == 3:
                    engine_map = {
                        'claude': 'ai_engines_claude',
                        'codex': 'ai_engines_codex',
                        'gemini': 'ai_engines_gemini',
                        'qwen': 'ai_engines_qwen'
                    }
                    if parts[2] in engine_map:
                        setattr(self, engine_map[parts[2]], value)
                        return
                elif parts[1] == 'qwen' and len(parts) >= 3:
                    qwen_setting_map = {
                        'transport': 'ai_qwen_transport',
                        'tcp_host': 'ai_qwen_tcp_host',
                        'tcp_port': 'ai_qwen_tcp_port'
                    }
                    if parts[2] in qwen_setting_map:
                        setattr(self, qwen_setting_map[parts[2]], value)
                        return
                elif parts[1] == 'dangerously_skip_permissions' and len(parts) == 2:
                    setattr(self, 'ai_dangerously_skip_permissions', value)
                    return
                elif parts[1] == 'stacking_mode' and len(parts) == 2:
                    setattr(self, 'ai_stacking_mode', value)
                    return

            # For other nested access like 'ai.provider', we use the last part as attribute name
            setattr(self, parts[-1], value)
    
    def get_section(self, section: str) -> Dict:
        """
        Get an entire configuration section.

        Args:
            section: Section name (e.g., 'ai_settings', 'user_preferences')

        Returns:
            Dictionary with section settings
        """
        sections_mapping = {
            'project_metadata': [
                'project_id', 'created_at', 'maestro_version', 'base_dir'
            ],
            'user_preferences': [
                'default_editor', 'discussion_mode', 'list_format'
            ],
            'ai_settings': [
                'ai_provider', 'ai_model', 'ai_api_key_file',
                'ai_context_window', 'ai_temperature',
                # New AI engine settings
                'ai_engines_claude', 'ai_engines_codex', 'ai_engines_gemini', 'ai_engines_qwen',
                'ai_stacking_mode',
                'ai_dangerously_skip_permissions',
                'ai_qwen_transport', 'ai_qwen_tcp_host', 'ai_qwen_tcp_port'
            ],
            'build_settings': [
                'default_build_method', 'parallel_jobs', 'verbose_builds',
                'clean_before_build'
            ],
            'display_settings': [
                'color_output', 'unicode_symbols', 'compact_lists',
                'show_completion_bars'
            ],
            'current_context': [
                'current_track', 'current_phase', 'current_task'
            ]
        }

        section_attrs = sections_mapping.get(section.lower(), [])
        result = {}
        for attr in section_attrs:
            if hasattr(self, attr):
                result[attr] = getattr(self, attr)

        return result
    
    def set_section(self, section: str, data: Dict) -> None:
        """
        Set an entire configuration section.
        
        Args:
            section: Section name
            data: Dictionary with section settings
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def validate(self) -> bool:
        """
        Validate all settings.

        Returns:
            True if all validations pass, False otherwise
        """
        errors = []

        # Validate discussion_mode enum
        if self.discussion_mode not in ['editor', 'terminal']:
            errors.append(f"discussion_mode must be 'editor' or 'terminal', got '{self.discussion_mode}'")

        # Validate list_format enum
        if self.list_format not in ['table', 'compact', 'detailed']:
            errors.append(f"list_format must be 'table', 'compact', or 'detailed', got '{self.list_format}'")

        # Validate ai_provider enum
        if self.ai_provider not in ['anthropic', 'openai', 'local']:
            errors.append(f"ai_provider must be 'anthropic', 'openai', or 'local', got '{self.ai_provider}'")

        # Validate ai_temperature range
        if not 0.0 <= self.ai_temperature <= 1.0:
            errors.append(f"ai_temperature must be between 0.0 and 1.0, got {self.ai_temperature}")

        # Validate parallel_jobs is positive
        if self.parallel_jobs < 1:
            errors.append(f"parallel_jobs must be >= 1, got {self.parallel_jobs}")

        # Validate ai_context_window is positive
        if self.ai_context_window <= 0:
            errors.append(f"ai_context_window must be > 0, got {self.ai_context_window}")

        # Validate editor path expansion if not using $EDITOR
        if self.default_editor != "$EDITOR":
            expanded_path = os.path.expanduser(os.path.expandvars(self.default_editor))
            if not os.path.exists(expanded_path):
                errors.append(f"Editor path '{expanded_path}' does not exist")

        # Validate AI engine settings
        valid_engine_roles = ['disabled', 'planner', 'worker', 'both']
        if self.ai_engines_claude not in valid_engine_roles:
            errors.append(f"ai_engines_claude must be one of {valid_engine_roles}, got '{self.ai_engines_claude}'")
        if self.ai_engines_codex not in valid_engine_roles:
            errors.append(f"ai_engines_codex must be one of {valid_engine_roles}, got '{self.ai_engines_codex}'")
        if self.ai_engines_gemini not in valid_engine_roles:
            errors.append(f"ai_engines_gemini must be one of {valid_engine_roles}, got '{self.ai_engines_gemini}'")
        if self.ai_engines_qwen not in valid_engine_roles:
            errors.append(f"ai_engines_qwen must be one of {valid_engine_roles}, got '{self.ai_engines_qwen}'")

        # Validate AI stacking mode
        if self.ai_stacking_mode not in ['managed', 'handsoff']:
            errors.append(f"ai_stacking_mode must be 'managed' or 'handsoff', got '{self.ai_stacking_mode}'")

        # Validate Qwen transport settings
        if self.ai_qwen_transport not in ['cmdline', 'stdio', 'tcp']:
            errors.append(f"ai_qwen_transport must be 'cmdline', 'stdio', or 'tcp', got '{self.ai_qwen_transport}'")
        if self.ai_qwen_tcp_port <= 0 or self.ai_qwen_tcp_port > 65535:
            errors.append(f"ai_qwen_tcp_port must be between 1 and 65535, got {self.ai_qwen_tcp_port}")

        if errors:
            raise InvalidSettingError("\n".join(errors))

        return True
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Convert settings to a dictionary organized by sections.

        Returns:
            Dictionary with settings organized by sections
        """
        return {
            'project_metadata': {
                'project_id': self.project_id,
                'created_at': self.created_at,
                'maestro_version': self.maestro_version,
                'base_dir': self.base_dir,
                'settings_schema_version': self.settings_schema_version
            },
            'user_preferences': {
                'default_editor': self.default_editor,
                'discussion_mode': self.discussion_mode,
                'list_format': self.list_format
            },
            'ai_settings': {
                'ai_provider': self.ai_provider,
                'ai_model': self.ai_model,
                'ai_api_key_file': self.ai_api_key_file,
                'ai_context_window': self.ai_context_window,
                'ai_temperature': self.ai_temperature,
                # New AI engine settings
                'ai_engines_claude': self.ai_engines_claude,
                'ai_engines_codex': self.ai_engines_codex,
                'ai_engines_gemini': self.ai_engines_gemini,
                'ai_engines_qwen': self.ai_engines_qwen,
                'ai_stacking_mode': self.ai_stacking_mode,
                'ai_dangerously_skip_permissions': self.ai_dangerously_skip_permissions,
                'ai_qwen_transport': self.ai_qwen_transport,
                'ai_qwen_tcp_host': self.ai_qwen_tcp_host,
                'ai_qwen_tcp_port': self.ai_qwen_tcp_port
            },
            'build_settings': {
                'default_build_method': self.default_build_method,
                'parallel_jobs': self.parallel_jobs,
                'verbose_builds': self.verbose_builds,
                'clean_before_build': self.clean_before_build
            },
            'display_settings': {
                'color_output': self.color_output,
                'unicode_symbols': self.unicode_symbols,
                'compact_lists': self.compact_lists,
                'show_completion_bars': self.show_completion_bars
            },
            'current_context': {
                'current_track': self.current_track,
                'current_phase': self.current_phase,
                'current_task': self.current_task
            }
        }
    
    def to_dict_flat(self) -> Dict[str, Any]:
        """
        Convert settings to a flat dictionary.
        
        Returns:
            Flat dictionary with all settings
        """
        result = {}
        for section_name, section_data in self.to_dict().items():
            result.update(section_data)
        return result


def create_default_config() -> Settings:
    """
    Create a default configuration with new UUID and timestamp.

    Returns:
        Default Settings instance
    """
    return Settings(
        project_id=str(uuid.uuid4()),
        created_at=datetime.now().isoformat(),
        maestro_version="1.2.1",  # Use the current version from the existing config
        base_dir=str(Path.cwd()),
        settings_schema_version="1.2.1",
        default_editor="$EDITOR",
        discussion_mode="editor",
        list_format="table",
        ai_provider="anthropic",
        ai_model="claude-3-5-sonnet-20250205",
        ai_api_key_file="~/.anthropic_key",
        ai_context_window=8192,
        ai_temperature=0.7,
        # AI Engine Matrix
        ai_engines_claude="both",
        ai_engines_codex="both",
        ai_engines_gemini="both",
        ai_engines_qwen="both",
        # AI Stacking Mode
        ai_stacking_mode="managed",
        # Global AI Permissions
        ai_dangerously_skip_permissions=True,
        # Qwen Transport Settings
        ai_qwen_transport="cmdline",
        ai_qwen_tcp_host="localhost",
        ai_qwen_tcp_port=7777,
        default_build_method="auto",
        parallel_jobs=4,
        verbose_builds=False,
        clean_before_build=False,
        color_output=True,
        unicode_symbols=True,
        compact_lists=False,
        show_completion_bars=True,
        current_track=None,
        current_phase=None,
        current_task=None
    )


# Global settings instance
_global_settings = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _global_settings
    if _global_settings is None:
        _global_settings = Settings.load()
    return _global_settings


def set_settings(settings: Settings) -> None:
    """Set the global settings instance."""
    global _global_settings
    _global_settings = settings
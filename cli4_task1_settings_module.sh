#!/bin/bash
# Task: Implement Settings Module for CLI4
# This script runs qwen to create the settings management system

TASK_PROMPT="# Task: Implement Settings Module for Maestro CLI4

## Context
You are implementing Phase CLI4 Task 4.1 and 4.2 for the Maestro build orchestration system.
The goal is to create a settings management system that stores configuration in docs/config.md
instead of the existing ~/.maestro/config.toml system.

## Current State Analysis

The codebase already has:
1. \`maestro/config.py\` - TOML-based configuration (will remain for build/hub settings)
2. \`maestro/data/markdown_parser.py\` - Markdown parser with \`parse_config_md()\` function
3. \`maestro/commands/\` - Command implementations for track, phase, task, discuss

## Task Requirements

### Create \`maestro/config/settings.py\`

Implement a comprehensive settings management module with:

1. **Settings Class** with methods:
   - \`load(config_path=None) -> Settings\` - Load from docs/config.md
   - \`save(config_path=None) -> bool\` - Save to docs/config.md
   - \`get(key: str, default: Any = None) -> Any\` - Get setting value
   - \`set(key: str, value: Any) -> None\` - Set setting value
   - \`get_section(section: str) -> Dict\` - Get entire section
   - \`set_section(section: str, data: Dict) -> None\` - Set entire section
   - \`validate() -> bool\` - Validate all settings
   - \`to_dict() -> Dict\` - Convert to dictionary

2. **Settings Schema** (dataclass or dict) with sections:
   - **Project Metadata**: project_id, created_at, maestro_version, base_dir
   - **User Preferences**: default_editor, discussion_mode, list_format
   - **AI Settings**: ai_provider, ai_model, ai_api_key_file, ai_context_window
   - **Build Settings**: default_build_method, parallel_jobs, verbose_builds
   - **Display Settings**: color_output, unicode_symbols, compact_lists
   - **Current Context**: current_track, current_phase, current_task

3. **Validation Functions**:
   - Type checking (str, int, bool, etc.)
   - Enum validation (e.g., discussion_mode must be 'editor' or 'terminal')
   - Path expansion (\$EDITOR, ~/ paths)
   - Custom \`InvalidSettingError\` exception class

4. **Default Configuration**:
   - \`create_default_config() -> Settings\` function
   - Generate new UUID for project_id
   - Set created_at to current timestamp (ISO format)
   - Use sensible defaults for all settings

5. **Dot Notation Support**:
   - \`get('ai.provider')\` should access nested settings
   - \`set('ai.model', 'value')\` should update nested settings

6. **Markdown Format** for docs/config.md:
\`\`\`markdown
# Maestro Configuration

## Project Metadata
\"project_id\": \"<uuid>\"
\"created_at\": \"YYYY-MM-DDTHH:MM:SS\"
\"maestro_version\": \"x.y.z\"
\"base_dir\": \"/path/to/project\"

## User Preferences
\"default_editor\": \"\$EDITOR\"
\"discussion_mode\": \"editor\"
\"list_format\": \"table\"

## AI Settings
\"ai_provider\": \"anthropic\"
\"ai_model\": \"claude-3-5-sonnet-20250205\"
\"ai_api_key_file\": \"~/.anthropic_key\"
\"ai_context_window\": 8192

## Build Settings
\"default_build_method\": \"auto\"
\"parallel_jobs\": 4
\"verbose_builds\": false

## Display Settings
\"color_output\": true
\"unicode_symbols\": true
\"compact_lists\": false

## Current Context
\"current_track\": null
\"current_phase\": null
\"current_task\": null
\`\`\`

## Implementation Details

### Module Structure
\`\`\`python
# maestro/config/settings.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import uuid
from datetime import datetime

class InvalidSettingError(Exception):
    pass

@dataclass
class Settings:
    # Project Metadata
    project_id: str
    created_at: str
    maestro_version: str
    base_dir: str

    # User Preferences
    default_editor: str = \"\$EDITOR\"
    discussion_mode: str = \"editor\"
    list_format: str = \"table\"

    # AI Settings
    ai_provider: str = \"anthropic\"
    ai_model: str = \"claude-3-5-sonnet-20250205\"
    ai_api_key_file: str = \"~/.anthropic_key\"
    ai_context_window: int = 8192

    # Build Settings
    default_build_method: str = \"auto\"
    parallel_jobs: int = 4
    verbose_builds: bool = False

    # Display Settings
    color_output: bool = True
    unicode_symbols: bool = True
    compact_lists: bool = False

    # Current Context
    current_track: Optional[str] = None
    current_phase: Optional[str] = None
    current_task: Optional[str] = None

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'Settings':
        # Use parse_config_md from maestro.data
        pass

    def save(self, config_path: Optional[Path] = None) -> bool:
        # Write to docs/config.md in markdown format
        pass

    def get(self, key: str, default: Any = None) -> Any:
        # Support dot notation like 'ai.provider'
        pass

    def set(self, key: str, value: Any) -> None:
        # Support dot notation like 'ai.provider'
        pass

    def validate(self) -> bool:
        # Validate all settings
        pass

    def to_dict(self) -> Dict:
        # Convert to dictionary organized by sections
        pass

def create_default_config() -> Settings:
    # Create default configuration with UUID and timestamp
    pass

def get_settings() -> Settings:
    # Singleton getter
    pass

def set_settings(settings: Settings) -> None:
    # Singleton setter
    pass
\`\`\`

### Key Requirements:
1. Use \`maestro.data.parse_config_md()\` to read docs/config.md
2. Write markdown format compatible with parse_config_md()
3. Support both flat and nested access patterns
4. Validate on load and save
5. Provide helpful error messages for validation failures
6. Path expansion for \$EDITOR and ~/ paths
7. Handle missing config.md gracefully (create default)

## Deliverables
1. \`maestro/config/__init__.py\` - Package init file
2. \`maestro/config/settings.py\` - Complete settings module
3. Summary of implementation in \`cli4_task1_summary.txt\`

## Output Format
Create a unified diff file that can be applied with \`patch\` command.
Save it to: \`cli4_task1_settings.patch\`

## Testing
The module should:
- Load and save config without errors
- Validate settings correctly
- Support dot notation access
- Create default config when missing
- Preserve existing settings when loading

Please implement this module following Python best practices and the existing
code style in the Maestro project."

# Run qwen with the task
echo "Starting qwen for CLI4 Task 1: Settings Module..."
echo "This may take 20+ minutes. Output will be saved to cli4_task1_output.txt"

~/node_modules/.bin/qwen -y "$TASK_PROMPT" 2>&1 | tee cli4_task1_output.txt

# Check if patch was created
if [ -f cli4_task1_settings.patch ]; then
    echo "Patch file created successfully!"
    echo "Review the patch before applying:"
    echo "  cat cli4_task1_settings.patch"
    echo "To apply the patch:"
    echo "  patch -p1 < cli4_task1_settings.patch"
else
    echo "Note: Patch file not found. Check cli4_task1_output.txt for implementation."
fi

echo "Task completed. Check cli4_task1_output.txt for full output."

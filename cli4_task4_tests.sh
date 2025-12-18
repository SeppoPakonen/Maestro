#!/bin/bash
# Task: Create Tests for Settings and Configuration
# This script runs qwen to create comprehensive tests

TASK_PROMPT="# Task: Create Tests for Maestro CLI4 Settings and Configuration

## Context
You are implementing testing for Phase CLI4 (Settings and Configuration) of the Maestro build orchestration system.
The goal is to create comprehensive tests for the settings module and commands.

## Completed Work
- ✅ maestro/config/settings.py - Settings module
- ✅ maestro/commands/settings.py - Settings command
- ✅ maestro/commands/context.py - Context management

## Task Requirements

Create comprehensive tests for the settings and configuration system.

### Test File 1: \`tests/config/test_settings.py\`

Test the Settings module:

\`\`\`python
import pytest
import tempfile
import shutil
from pathlib import Path
from maestro.config.settings import Settings, create_default_config, InvalidSettingError

class TestSettings:
    def setup_method(self):
        \"\"\"Set up test fixtures.\"\"\"
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / 'config.md'

    def teardown_method(self):
        \"\"\"Clean up test fixtures.\"\"\"
        shutil.rmtree(self.temp_dir)

    def test_create_default_config(self):
        \"\"\"Test creating default configuration.\"\"\"
        settings = create_default_config()
        assert settings.project_id is not None
        assert settings.created_at is not None
        assert settings.ai_provider == 'anthropic'
        assert settings.parallel_jobs == 4

    def test_save_and_load(self):
        \"\"\"Test saving and loading configuration.\"\"\"
        settings = create_default_config()
        settings.save(self.config_path)

        loaded = Settings.load(self.config_path)
        assert loaded.project_id == settings.project_id
        assert loaded.ai_provider == settings.ai_provider

    def test_get_setting(self):
        \"\"\"Test getting setting values.\"\"\"
        settings = create_default_config()
        assert settings.get('ai_provider') == 'anthropic'
        assert settings.get('parallel_jobs') == 4
        assert settings.get('nonexistent', 'default') == 'default'

    def test_set_setting(self):
        \"\"\"Test setting values.\"\"\"
        settings = create_default_config()
        settings.set('ai_provider', 'openai')
        assert settings.ai_provider == 'openai'

        settings.set('parallel_jobs', 8)
        assert settings.parallel_jobs == 8

    def test_get_section(self):
        \"\"\"Test getting entire sections.\"\"\"
        settings = create_default_config()
        ai_settings = settings.get_section('ai_settings')
        assert 'ai_provider' in ai_settings
        assert 'ai_model' in ai_settings

    def test_set_section(self):
        \"\"\"Test setting entire sections.\"\"\"
        settings = create_default_config()
        new_ai_settings = {
            'ai_provider': 'openai',
            'ai_model': 'gpt-4',
            'ai_api_key_file': '~/.openai_key'
        }
        settings.set_section('ai_settings', new_ai_settings)
        assert settings.ai_provider == 'openai'
        assert settings.ai_model == 'gpt-4'

    def test_validation(self):
        \"\"\"Test settings validation.\"\"\"
        settings = create_default_config()
        # Should not raise for valid settings
        assert settings.validate() == True

        # Test invalid values
        settings.parallel_jobs = -1
        with pytest.raises(InvalidSettingError):
            settings.validate()

    def test_to_dict(self):
        \"\"\"Test converting settings to dictionary.\"\"\"
        settings = create_default_config()
        data = settings.to_dict()
        assert 'project_metadata' in data
        assert 'ai_settings' in data
        assert 'build_settings' in data

    def test_dot_notation(self):
        \"\"\"Test dot notation access.\"\"\"
        settings = create_default_config()
        # Get with dot notation
        assert settings.get('ai.provider') == settings.ai_provider
        # Set with dot notation
        settings.set('ai.provider', 'openai')
        assert settings.ai_provider == 'openai'

    def test_context_management(self):
        \"\"\"Test context tracking.\"\"\"
        settings = create_default_config()
        assert settings.current_track is None

        settings.current_track = 'cli-tpt'
        assert settings.get('current_track') == 'cli-tpt'

        settings.current_track = None
        assert settings.current_track is None
\`\`\`

### Test File 2: \`tests/commands/test_settings_command.py\`

Test the settings command:

\`\`\`python
import pytest
import tempfile
import shutil
from pathlib import Path
from maestro.commands.settings import (
    list_settings, get_setting, set_setting, reset_settings,
    handle_settings_command
)
from maestro.config.settings import create_default_config

class Args:
    \"\"\"Mock args object for testing.\"\"\"
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class TestSettingsCommand:
    def setup_method(self):
        \"\"\"Set up test fixtures.\"\"\"
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / 'config.md'

        # Create default config
        settings = create_default_config()
        settings.save(self.config_path)

    def teardown_method(self):
        \"\"\"Clean up test fixtures.\"\"\"
        shutil.rmtree(self.temp_dir)

    def test_list_settings(self):
        \"\"\"Test listing all settings.\"\"\"
        args = Args(json=False, section=None)
        result = list_settings(args)
        assert result == 0

    def test_list_settings_json(self):
        \"\"\"Test JSON output.\"\"\"
        args = Args(json=True, section=None)
        result = list_settings(args)
        assert result == 0

    def test_list_settings_section(self):
        \"\"\"Test listing specific section.\"\"\"
        args = Args(json=False, section='ai_settings')
        result = list_settings(args)
        assert result == 0

    def test_get_setting(self):
        \"\"\"Test getting a setting.\"\"\"
        args = Args(key='ai_provider', raw=False)
        result = get_setting(args)
        assert result == 0

    def test_get_setting_raw(self):
        \"\"\"Test getting raw setting value.\"\"\"
        args = Args(key='default_editor', raw=True)
        result = get_setting(args)
        assert result == 0

    def test_set_setting(self):
        \"\"\"Test setting a value.\"\"\"
        args = Args(key='parallel_jobs', value='8', no_confirm=True)
        result = set_setting(args)
        assert result == 0

    def test_reset_setting(self):
        \"\"\"Test resetting a single setting.\"\"\"
        args = Args(key='parallel_jobs', all=False, force=False)
        result = reset_settings(args)
        assert result == 0

    def test_reset_all_without_force(self):
        \"\"\"Test reset all without force flag.\"\"\"
        args = Args(key=None, all=True, force=False)
        result = reset_settings(args)
        assert result == 1  # Should fail without force

    def test_reset_all_with_force(self):
        \"\"\"Test reset all with force flag.\"\"\"
        args = Args(key=None, all=True, force=True)
        result = reset_settings(args)
        assert result == 0
\`\`\`

### Test File 3: \`tests/commands/test_context_command.py\`

Test the context management:

\`\`\`python
import pytest
import tempfile
import shutil
from pathlib import Path
from maestro.commands.context import show_context, clear_context, handle_context_command
from maestro.config.settings import create_default_config, set_settings

class Args:
    \"\"\"Mock args object for testing.\"\"\"
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class TestContextCommand:
    def setup_method(self):
        \"\"\"Set up test fixtures.\"\"\"
        settings = create_default_config()
        set_settings(settings)

    def test_show_context_empty(self):
        \"\"\"Test showing empty context.\"\"\"
        args = Args()
        result = show_context(args)
        assert result == 0

    def test_show_context_with_track(self):
        \"\"\"Test showing context with track set.\"\"\"
        from maestro.config.settings import get_settings
        settings = get_settings()
        settings.current_track = 'test-track'

        args = Args()
        result = show_context(args)
        assert result == 0

    def test_clear_context(self):
        \"\"\"Test clearing context.\"\"\"
        from maestro.config.settings import get_settings
        settings = get_settings()
        settings.current_track = 'test-track'
        settings.current_phase = 'test-phase'

        args = Args()
        result = clear_context(args)
        assert result == 0

        settings = get_settings()
        assert settings.current_track is None
        assert settings.current_phase is None
\`\`\`

## Directory Structure

Create the test directory structure:
\`\`\`
tests/
  config/
    __init__.py
    test_settings.py
  commands/
    __init__.py
    test_settings_command.py
    test_context_command.py
\`\`\`

## Additional Requirements

1. All tests should use pytest
2. Tests should be isolated (use temp directories, clean up after)
3. Tests should cover both success and failure cases
4. Mock external dependencies where needed
5. Follow existing test patterns in tests/ directory

## Deliverables
1. \`tests/config/__init__.py\` - Package init
2. \`tests/config/test_settings.py\` - Settings module tests
3. \`tests/commands/__init__.py\` - Package init (if not exists)
4. \`tests/commands/test_settings_command.py\` - Settings command tests
5. \`tests/commands/test_context_command.py\` - Context command tests
6. Summary in \`cli4_task4_summary.txt\`

## Output Format
Create files directly (not patches since these are new test files).
Provide summary of test coverage in summary file.

Please implement comprehensive tests following pytest best practices."

# Run qwen with the task
echo "Starting qwen for CLI4 Task 4: Create Tests..."
echo "This may take 20+ minutes. Output will be saved to cli4_task4_output.txt"

~/node_modules/.bin/qwen -y "$TASK_PROMPT" 2>&1 | tee cli4_task4_output.txt

echo "Task completed. Check cli4_task4_output.txt for full output."

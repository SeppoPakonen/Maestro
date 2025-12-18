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
    """Mock args object for testing."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class TestSettingsCommand:
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / 'config.md'

        # Create default config
        settings = create_default_config()
        settings.save(self.config_path)

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_list_settings(self):
        """Test listing all settings."""
        args = Args(json=False, section=None)
        result = list_settings(args)
        assert result == 0

    def test_list_settings_json(self):
        """Test JSON output."""
        args = Args(json=True, section=None)
        result = list_settings(args)
        assert result == 0

    def test_list_settings_section(self):
        """Test listing specific section."""
        args = Args(json=False, section='ai_settings')
        result = list_settings(args)
        assert result == 0

    def test_get_setting(self):
        """Test getting a setting."""
        args = Args(key='ai_provider', raw=False)
        result = get_setting(args)
        assert result == 0

    def test_get_setting_raw(self):
        """Test getting raw setting value."""
        args = Args(key='default_editor', raw=True)
        result = get_setting(args)
        assert result == 0

    def test_set_setting(self):
        """Test setting a value."""
        args = Args(key='parallel_jobs', value='8', no_confirm=True)
        result = set_setting(args)
        assert result == 0

    def test_reset_setting(self):
        """Test resetting a single setting."""
        args = Args(key='parallel_jobs', all=False, force=False)
        result = reset_settings(args)
        assert result == 0

    def test_reset_all_without_force(self):
        """Test reset all without force flag."""
        args = Args(key=None, all=True, force=False)
        result = reset_settings(args)
        assert result == 1  # Should fail without force

    def test_reset_all_with_force(self):
        """Test reset all with force flag."""
        args = Args(key=None, all=True, force=True)
        result = reset_settings(args)
        assert result == 0
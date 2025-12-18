import pytest
import tempfile
import shutil
from pathlib import Path
from maestro.config.settings import Settings, create_default_config, InvalidSettingError

class TestSettings:
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / 'config.md'

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_create_default_config(self):
        """Test creating default configuration."""
        settings = create_default_config()
        assert settings.project_id is not None
        assert settings.created_at is not None
        assert settings.ai_provider == 'anthropic'
        assert settings.parallel_jobs == 4

    def test_save_and_load(self):
        """Test saving and loading configuration."""
        settings = create_default_config()
        settings.save(self.config_path)

        loaded = Settings.load(self.config_path)
        assert loaded.project_id == settings.project_id
        assert loaded.ai_provider == settings.ai_provider

    def test_get_setting(self):
        """Test getting setting values."""
        settings = create_default_config()
        assert settings.get('ai_provider') == 'anthropic'
        assert settings.get('parallel_jobs') == 4
        assert settings.get('nonexistent', 'default') == 'default'

    def test_set_setting(self):
        """Test setting values."""
        settings = create_default_config()
        settings.set('ai_provider', 'openai')
        assert settings.ai_provider == 'openai'

        settings.set('parallel_jobs', 8)
        assert settings.parallel_jobs == 8

    def test_get_section(self):
        """Test getting entire sections."""
        settings = create_default_config()
        ai_settings = settings.get_section('ai_settings')
        assert 'ai_provider' in ai_settings
        assert 'ai_model' in ai_settings

    def test_set_section(self):
        """Test setting entire sections."""
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
        """Test settings validation."""
        settings = create_default_config()
        # Should not raise for valid settings
        assert settings.validate() == True

        # Test invalid values
        settings.parallel_jobs = -1
        with pytest.raises(InvalidSettingError):
            settings.validate()

    def test_to_dict(self):
        """Test converting settings to dictionary."""
        settings = create_default_config()
        data = settings.to_dict()
        assert 'project_metadata' in data
        assert 'ai_settings' in data
        assert 'build_settings' in data

    def test_dot_notation(self):
        """Test attribute access with underscores."""
        settings = create_default_config()
        # Get with attribute name
        assert settings.get('ai_provider') == settings.ai_provider
        # Set with attribute name
        settings.set('ai_provider', 'openai')
        assert settings.ai_provider == 'openai'

    def test_context_management(self):
        """Test context tracking."""
        settings = create_default_config()
        assert settings.current_track is None

        settings.current_track = 'cli-tpt'
        assert settings.get('current_track') == 'cli-tpt'

        settings.current_track = None
        assert settings.current_track is None
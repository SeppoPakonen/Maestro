import pytest
import tempfile
import shutil
from pathlib import Path
from maestro.commands.context import show_context, clear_context, handle_context_command
from maestro.config.settings import create_default_config, set_settings

class Args:
    """Mock args object for testing."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class TestContextCommand:
    def setup_method(self):
        """Set up test fixtures."""
        settings = create_default_config()
        set_settings(settings)

    def test_show_context_empty(self):
        """Test showing empty context."""
        args = Args()
        result = show_context(args)
        assert result == 0

    def test_show_context_with_track(self):
        """Test showing context with track set."""
        from maestro.config.settings import get_settings
        settings = get_settings()
        settings.current_track = 'test-track'

        args = Args()
        result = show_context(args)
        assert result == 0

    def test_clear_context(self):
        """Test clearing context."""
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
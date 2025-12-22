"""
Tests for settings profile functionality in Maestro CLI.
"""
import json
import os
import tempfile
from pathlib import Path
import pytest

from maestro.config.settings import Settings, create_default_config
from maestro.config.settings_profiles import SettingsProfileManager


def test_profile_creation():
    """Test creating a new settings profile."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Initialize profile manager
        profile_manager = SettingsProfileManager(temp_path)
        
        # Create a settings object
        settings = create_default_config()
        
        # Create a profile
        profile_id = profile_manager.create_profile("test-profile", settings, "Test profile for unit testing")
        
        # Verify profile was created
        assert profile_id is not None
        assert len(profile_manager.list_profiles()) == 1
        
        # Verify profile metadata
        profile = profile_manager.get_profile_by_id(profile_id)
        assert profile is not None
        assert profile["name"] == "test-profile"
        assert profile["notes"] == "Test profile for unit testing"


def test_profile_save_and_load():
    """Test saving and loading a profile."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Initialize profile manager
        profile_manager = SettingsProfileManager(temp_path)
        
        # Create and modify settings
        settings = create_default_config()
        settings.ai_provider = "openai"
        settings.ai_model = "gpt-4"
        
        # Save to profile
        profile_id = profile_manager.create_profile("dev-settings", settings)
        
        # Load from profile
        loaded_settings = profile_manager._load_profile(profile_id)
        
        # Verify settings were loaded correctly
        assert loaded_settings is not None
        assert loaded_settings.ai_provider == "openai"
        assert loaded_settings.ai_model == "gpt-4"


def test_profile_list():
    """Test listing profiles."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Initialize profile manager
        profile_manager = SettingsProfileManager(temp_path)
        
        # Create a few profiles
        settings = create_default_config()
        profile_manager.create_profile("profile-1", settings)
        profile_manager.create_profile("profile-2", settings)
        
        # List profiles
        profiles = profile_manager.list_profiles()
        
        # Verify we have 2 profiles
        assert len(profiles) == 2
        profile_names = [p["name"] for p in profiles]
        assert "profile-1" in profile_names
        assert "profile-2" in profile_names


def test_profile_update():
    """Test updating an existing profile."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Initialize profile manager
        profile_manager = SettingsProfileManager(temp_path)
        
        # Create initial settings
        settings = create_default_config()
        settings.ai_provider = "anthropic"
        
        # Create a profile
        profile_id = profile_manager.create_profile("update-test", settings)
        
        # Update settings
        settings.ai_provider = "openai"
        
        # Update the profile
        success = profile_manager.update_profile(profile_id, settings, "Updated profile")
        
        # Verify update was successful
        assert success is True
        
        # Load and verify updated settings
        updated_settings = profile_manager._load_profile(profile_id)
        assert updated_settings is not None
        assert updated_settings.ai_provider == "openai"
        
        # Check that notes were updated
        profile = profile_manager.get_profile_by_id(profile_id)
        assert profile["notes"] == "Updated profile"


def test_profile_delete():
    """Test deleting a profile."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Initialize profile manager
        profile_manager = SettingsProfileManager(temp_path)
        
        # Create a profile
        settings = create_default_config()
        profile_id = profile_manager.create_profile("to-delete", settings)
        
        # Verify profile exists
        assert profile_manager.get_profile_by_id(profile_id) is not None
        assert len(profile_manager.list_profiles()) == 1
        
        # Delete the profile
        success = profile_manager.delete_profile(profile_id)
        
        # Verify deletion
        assert success is True
        assert profile_manager.get_profile_by_id(profile_id) is None
        assert len(profile_manager.list_profiles()) == 0


def test_active_and_default_profiles():
    """Test setting and getting active and default profiles."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Initialize profile manager
        profile_manager = SettingsProfileManager(temp_path)
        
        # Create a profile
        settings = create_default_config()
        profile_id = profile_manager.create_profile("active-test", settings)
        
        # Set as active
        success = profile_manager.set_active_profile(profile_id)
        assert success is True
        
        # Get active profile
        active_profile = profile_manager.get_active_profile()
        assert active_profile is not None
        assert active_profile["id"] == profile_id
        
        # Set as default
        success = profile_manager.set_default_profile(profile_id)
        assert success is True
        
        # Get default profile
        default_profile = profile_manager.get_default_profile()
        assert default_profile is not None
        assert default_profile["id"] == profile_id


def test_profile_by_name_and_number():
    """Test getting profiles by name and number."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Initialize profile manager
        profile_manager = SettingsProfileManager(temp_path)
        
        # Create a few profiles
        settings = create_default_config()
        profile_manager.create_profile("first-profile", settings)
        profile_manager.create_profile("second-profile", settings)
        profile_manager.create_profile("third-profile", settings)
        
        # Test getting by name
        profile_by_name = profile_manager.get_profile_by_name("second-profile")
        assert profile_by_name is not None
        assert profile_by_name["name"] == "second-profile"
        
        # Test getting by number (1-indexed)
        profile_by_number = profile_manager.get_profile_by_number(2)
        assert profile_by_number is not None
        assert profile_by_number["name"] == "second-profile"


def test_settings_hash():
    """Test settings hashing functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Initialize profile manager
        profile_manager = SettingsProfileManager(temp_path)

        # Create a settings object and duplicate it
        settings1 = create_default_config()

        # Create a second settings object with same values
        settings2 = Settings(
            project_id=settings1.project_id,
            created_at=settings1.created_at,
            maestro_version=settings1.maestro_version,
            base_dir=settings1.base_dir,
            default_editor=settings1.default_editor,
            discussion_mode=settings1.discussion_mode,
            list_format=settings1.list_format,
            ai_provider=settings1.ai_provider,
            ai_model=settings1.ai_model,
            ai_api_key_file=settings1.ai_api_key_file,
            ai_context_window=settings1.ai_context_window,
            ai_temperature=settings1.ai_temperature,
            ai_engines_claude=settings1.ai_engines_claude,
            ai_engines_codex=settings1.ai_engines_codex,
            ai_engines_gemini=settings1.ai_engines_gemini,
            ai_engines_qwen=settings1.ai_engines_qwen,
            ai_stacking_mode=settings1.ai_stacking_mode,
            ai_qwen_use_stdio_or_tcp=settings1.ai_qwen_use_stdio_or_tcp,
            ai_qwen_transport=settings1.ai_qwen_transport,
            ai_qwen_tcp_host=settings1.ai_qwen_tcp_host,
            ai_qwen_tcp_port=settings1.ai_qwen_tcp_port,
            default_build_method=settings1.default_build_method,
            parallel_jobs=settings1.parallel_jobs,
            verbose_builds=settings1.verbose_builds,
            clean_before_build=settings1.clean_before_build,
            color_output=settings1.color_output,
            unicode_symbols=settings1.unicode_symbols,
            compact_lists=settings1.compact_lists,
            show_completion_bars=settings1.show_completion_bars,
            current_track=settings1.current_track,
            current_phase=settings1.current_phase,
            current_task=settings1.current_task
        )

        # Hash should be the same for identical settings
        hash1 = profile_manager._hash_settings(settings1)
        hash2 = profile_manager._hash_settings(settings2)
        assert hash1 == hash2

        # Modify one settings object
        settings1.ai_provider = "openai"
        hash1_modified = profile_manager._hash_settings(settings1)

        # Hash should be different now
        assert hash1_modified != hash1


def test_has_unsaved_changes():
    """Test detection of unsaved changes."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        os.chdir(temp_path)  # Change to temp directory so get_settings() works properly

        # Initialize profile manager
        profile_manager = SettingsProfileManager(temp_path)

        # Create settings and save as profile
        settings = create_default_config()
        # Save the settings to the active config file first
        settings.save()

        profile_id = profile_manager.create_profile("test-profile", settings)

        # Set as active profile
        profile_manager.set_active_profile(profile_id)

        # Initially, no unsaved changes (since active settings match the profile)
        assert profile_manager.has_unsaved_changes() is False

        # Now modify the active settings directly
        from maestro.config.settings import get_settings, set_settings
        current_settings = get_settings()
        current_settings.ai_provider = "openai"
        current_settings.save()  # Save the modified settings to the active config file

        # Now there should be unsaved changes since we modified the active settings file
        # but the profile still contains the original settings
        assert profile_manager.has_unsaved_changes() is True


if __name__ == "__main__":
    # Run tests
    test_profile_creation()
    test_profile_save_and_load()
    test_profile_list()
    test_profile_update()
    test_profile_delete()
    test_active_and_default_profiles()
    test_profile_by_name_and_number()
    test_settings_hash()
    test_has_unsaved_changes()
    
    print("All tests passed!")
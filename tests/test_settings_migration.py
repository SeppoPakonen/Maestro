"""
Tests for AI Settings Migration functionality.
This tests the migration from old settings to new settings structure.
"""

import os
import pytest
import tempfile
from pathlib import Path

from maestro.config.settings import Settings, create_default_config


def test_settings_migration_from_old_schema():
    """Test migration from old settings schema to new schema."""
    # Create a temporary config file with old schema
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            temp_dir_path = Path(temp_dir)
            config_path = temp_dir_path / "config.md"

            # Create old schema config content
            old_config_content = '''# Maestro Configuration

**Last Updated**: 2024-01-01

---

## Project Metadata

"project_id": "test-project-id"
"created_at": "2024-01-01T00:00:00"
"maestro_version": "1.0.0"
"base_dir": "/test/dir"

---

## AI Settings

"ai_provider": "anthropic"
"ai_model": "claude-3-5-sonnet-20250205"
"ai_api_key_file": "~/.anthropic_key"
"ai_context_window": 8192
"ai_temperature": 0.7
"ai_engines_claude": "both"
"ai_engines_codex": "both"
"ai_engines_gemini": "both"
"ai_engines_qwen": "both"
"ai_stacking_mode": "managed"
"ai_qwen_use_stdio_or_tcp": true
"ai_qwen_transport": "stdio"
"ai_qwen_tcp_host": "localhost"
"ai_qwen_tcp_port": 7777

---

## Build Settings

"default_build_method": "auto"
"parallel_jobs": 4
"verbose_builds": false
"clean_before_build": false

---

## Notes

This configuration file is both human-readable and machine-parsable.
'''

            # Write the old config to file
            with open(config_path, 'w') as f:
                f.write(old_config_content)

            # Load settings from the old config file
            settings = Settings.load(config_path)

            # Verify the new settings structure is properly loaded
            assert settings.ai_dangerously_skip_permissions is True  # Default value
            assert settings.ai_qwen_transport == "stdio"  # Should preserve existing value from config
            # Verify old field is not accessible
            try:
                getattr(settings, 'ai_qwen_use_stdio_or_tcp')
                assert False, "ai_qwen_use_stdio_or_tcp should not exist anymore"
            except AttributeError:
                pass  # Expected
        finally:
            os.chdir(original_cwd)


def test_settings_migration_with_new_schema():
    """Test loading settings with new schema."""
    # Create a temporary config file with new schema
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            temp_dir_path = Path(temp_dir)
            config_path = temp_dir_path / "config.md"

            # Create new schema config content
            new_config_content = '''# Maestro Configuration

**Last Updated**: 2024-01-01

---

## Project Metadata

"project_id": "test-project-id"
"created_at": "2024-01-01T00:00:00"
"maestro_version": "1.2.1"
"base_dir": "/test/dir"

---

## AI Settings

"ai_provider": "anthropic"
"ai_model": "claude-3-5-sonnet-20250205"
"ai_api_key_file": "~/.anthropic_key"
"ai_context_window": 8192
"ai_temperature": 0.7
"ai_engines_claude": "both"
"ai_engines_codex": "both"
"ai_engines_gemini": "both"
"ai_engines_qwen": "both"
"ai_stacking_mode": "managed"
"ai_dangerously_skip_permissions": true
"ai_qwen_transport": "cmdline"
"ai_qwen_tcp_host": "localhost"
"ai_qwen_tcp_port": 7777

---

## Build Settings

"default_build_method": "auto"
"parallel_jobs": 4
"verbose_builds": false
"clean_before_build": false

---

## Notes

This configuration file is both human-readable and machine-parsable.
'''

            # Write the new config to file
            with open(config_path, 'w') as f:
                f.write(new_config_content)

            # Load settings from the new config file
            settings = Settings.load(config_path)

            # Verify the new settings structure is properly loaded
            assert settings.ai_dangerously_skip_permissions is True
            assert settings.ai_qwen_transport == "cmdline"
            # Verify old field is not accessible
            try:
                getattr(settings, 'ai_qwen_use_stdio_or_tcp')
                assert False, "ai_qwen_use_stdio_or_tcp should not exist anymore"
            except AttributeError:
                pass  # Expected
        finally:
            os.chdir(original_cwd)


def test_settings_default_values():
    """Test that new settings have correct default values."""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            settings = create_default_config()

            # Verify new defaults
            assert settings.ai_dangerously_skip_permissions is True
            assert settings.ai_qwen_transport == "cmdline"

            # Verify old field is not accessible
            try:
                getattr(settings, 'ai_qwen_use_stdio_or_tcp')
                assert False, "ai_qwen_use_stdio_or_tcp should not exist anymore"
            except AttributeError:
                pass  # Expected
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    test_settings_migration_from_old_schema()
    test_settings_migration_with_new_schema()
    test_settings_default_values()
    print("All settings migration tests passed!")
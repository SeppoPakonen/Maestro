"""
Tests for AI Settings functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from maestro.config.settings import Settings, create_default_config, InvalidSettingError
from maestro.ai.engine_selector import get_eligible_engines, select_engine_for_role
from maestro.ai.stacking_enforcer import validate_planner_output, is_managed_mode, is_handsoff_mode


def test_ai_engine_settings_default_values():
    """Test that new AI engine settings have correct default values."""
    settings = create_default_config()

    assert settings.ai_engines_claude == "both"
    assert settings.ai_engines_codex == "both"
    assert settings.ai_engines_gemini == "both"
    assert settings.ai_engines_qwen == "both"
    assert settings.ai_stacking_mode == "managed"
    assert settings.ai_dangerously_skip_permissions is True
    assert settings.ai_qwen_transport == "cmdline"
    assert settings.ai_qwen_tcp_host == "localhost"
    assert settings.ai_qwen_tcp_port == 7777
    # Test new per-engine settings
    assert settings.ai_claude_provider == "anthropic"
    assert settings.ai_claude_model == "claude-3-5-sonnet-20250205"
    assert settings.ai_codex_model == "codex"
    assert settings.ai_gemini_model == "gemini-pro"
    assert settings.ai_qwen_model == "qwen"


def test_ai_engine_settings_validation():
    """Test validation of AI engine settings."""
    settings = create_default_config()
    
    # Test valid engine roles
    valid_roles = ['disabled', 'planner', 'worker', 'both']
    for role in valid_roles:
        settings.ai_engines_claude = role
        assert settings.validate() is True  # Should not raise exception
    
    # Test invalid engine role
    settings.ai_engines_claude = "invalid_role"
    with pytest.raises(InvalidSettingError):
        settings.validate()


def test_ai_stacking_mode_validation():
    """Test validation of AI stacking mode."""
    settings = create_default_config()
    
    # Test valid modes
    settings.ai_stacking_mode = "managed"
    assert settings.validate() is True
    
    settings.ai_stacking_mode = "handsoff"
    assert settings.validate() is True
    
    # Test invalid mode
    settings.ai_stacking_mode = "invalid_mode"
    with pytest.raises(InvalidSettingError):
        settings.validate()


def test_qwen_transport_settings_validation():
    """Test validation of Qwen transport settings."""
    settings = create_default_config()

    # Test valid transport
    settings.ai_qwen_transport = "cmdline"
    assert settings.validate() is True

    settings.ai_qwen_transport = "stdio"
    assert settings.validate() is True

    settings.ai_qwen_transport = "tcp"
    assert settings.validate() is True

    # Test invalid transport
    settings.ai_qwen_transport = "invalid_transport"
    with pytest.raises(InvalidSettingError):
        settings.validate()

    # Test valid port
    settings.ai_qwen_transport = "stdio"  # Reset to valid
    settings.ai_qwen_tcp_port = 8080
    assert settings.validate() is True

    # Test invalid port
    settings.ai_qwen_tcp_port = 0
    with pytest.raises(InvalidSettingError):
        settings.validate()

    settings.ai_qwen_tcp_port = 65536  # Too high
    with pytest.raises(InvalidSettingError):
        settings.validate()


def test_settings_get_set_dot_notation():
    """Test getting and setting settings using dot notation."""
    settings = create_default_config()

    # Test getting engine settings
    assert settings.get("ai.engines.claude") == "both"
    assert settings.get("ai.engines.codex") == "both"
    assert settings.get("ai.engines.gemini") == "both"
    assert settings.get("ai.engines.qwen") == "both"

    # Test getting global permissions setting
    assert settings.get("ai.dangerously_skip_permissions") is True

    # Test getting qwen transport settings
    assert settings.get("ai.qwen.transport") == "cmdline"
    assert settings.get("ai.qwen.tcp_host") == "localhost"
    assert settings.get("ai.qwen.tcp_port") == 7777

    # Test getting stacking mode
    assert settings.get("ai.stacking_mode") == "managed"

    # Test setting engine settings
    settings.set("ai.engines.claude", "planner")
    assert settings.get("ai.engines.claude") == "planner"

    settings.set("ai.engines.qwen", "worker")
    assert settings.get("ai.engines.qwen") == "worker"

    # Test setting global permissions
    settings.set("ai.dangerously_skip_permissions", False)
    assert settings.get("ai.dangerously_skip_permissions") is False

    # Test setting qwen transport settings
    settings.set("ai.qwen.tcp_port", 8080)
    assert settings.get("ai.qwen.tcp_port") == 8080

    # Test setting stacking mode
    settings.set("ai.stacking_mode", "handsoff")
    assert settings.get("ai.stacking_mode") == "handsoff"


def test_eligible_engines_selection():
    """Test engine selection based on role and matrix."""
    # Test with default settings (all engines set to 'both'), all should be eligible for both roles
    with patch('maestro.ai.engine_selector.get_settings') as mock_get_settings:
        # Mock default settings
        mock_settings = MagicMock()
        mock_settings.ai_engines_claude = "both"
        mock_settings.ai_engines_codex = "both"
        mock_settings.ai_engines_gemini = "both"
        mock_settings.ai_engines_qwen = "both"
        mock_get_settings.return_value = mock_settings

        planner_engines = get_eligible_engines('planner')
        assert 'claude' in planner_engines
        assert 'codex' in planner_engines
        assert 'gemini' in planner_engines
        assert 'qwen' in planner_engines
        assert len(planner_engines) == 4

        worker_engines = get_eligible_engines('worker')
        assert 'claude' in worker_engines
        assert 'codex' in worker_engines
        assert 'gemini' in worker_engines
        assert 'qwen' in worker_engines
        assert len(worker_engines) == 4

    # Test with modified settings
    with patch('maestro.ai.engine_selector.get_settings') as mock_get_settings:
        # Mock modified settings
        mock_settings = MagicMock()
        mock_settings.ai_engines_claude = 'planner'  # Only planner
        mock_settings.ai_engines_codex = 'worker'    # Only worker
        mock_settings.ai_engines_gemini = 'disabled' # Disabled
        mock_settings.ai_engines_qwen = 'both'       # Both
        mock_get_settings.return_value = mock_settings

        planner_engines = get_eligible_engines('planner')
        assert 'claude' in planner_engines
        assert 'codex' not in planner_engines  # codex is worker only
        assert 'gemini' not in planner_engines  # gemini is disabled
        assert 'qwen' in planner_engines
        assert len(planner_engines) == 2

        worker_engines = get_eligible_engines('worker')
        assert 'claude' not in worker_engines  # claude is planner only
        assert 'codex' in worker_engines
        assert 'gemini' not in worker_engines  # gemini is disabled
        assert 'qwen' in worker_engines
        assert len(worker_engines) == 2


def test_stacking_mode_enforcement():
    """Test stacking mode enforcement logic."""
    # Test managed mode validation
    with patch('maestro.ai.stacking_enforcer.get_settings') as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.ai_stacking_mode = 'managed'
        mock_get_settings.return_value = mock_settings
        
        # Valid JSON plan should pass
        valid_plan = '{"tasks": [{"id": 1, "action": "do something"}]}'
        result = validate_planner_output(valid_plan)
        assert result == {"tasks": [{"id": 1, "action": "do something"}]}
        
        # Invalid JSON should raise error in managed mode
        invalid_json = "not json"
        with pytest.raises(ValueError, match="Managed mode requires a full JSON plan"):
            validate_planner_output(invalid_json)
        
        # Valid JSON but not a plan structure should raise error
        valid_but_not_plan = '{"message": "hello"}'
        with pytest.raises(ValueError, match="Managed mode requires a full JSON plan"):
            validate_planner_output(valid_but_not_plan)
    
    # Test handsoff mode (should accept anything)
    with patch('maestro.ai.stacking_enforcer.get_settings') as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.ai_stacking_mode = 'handsoff'
        mock_get_settings.return_value = mock_settings
        
        # Any input should be accepted in handsoff mode
        result = validate_planner_output("any text")
        assert result == {"raw_output": "any text"}
        
        result = validate_planner_output('{"any": "json"}')
        assert result == {"raw_output": '{"any": "json"}'}


def test_mode_check_functions():
    """Test the mode checking functions."""
    with patch('maestro.ai.stacking_enforcer.get_settings') as mock_get_settings:
        # Test managed mode
        mock_settings = MagicMock()
        mock_settings.ai_stacking_mode = 'managed'
        mock_get_settings.return_value = mock_settings
        
        assert is_managed_mode() is True
        assert is_handsoff_mode() is False
        
        # Test handsoff mode
        mock_settings.ai_stacking_mode = 'handsoff'
        assert is_managed_mode() is False
        assert is_handsoff_mode() is True


def test_settings_persistence():
    """Test that settings are properly saved and loaded."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.md"

        # Create settings with custom values
        settings = create_default_config()
        settings.ai_engines_claude = "planner"
        settings.ai_engines_codex = "worker"
        settings.ai_engines_gemini = "disabled"
        settings.ai_engines_qwen = "both"
        settings.ai_stacking_mode = "handsoff"
        settings.ai_dangerously_skip_permissions = False
        settings.ai_qwen_transport = "stdio"
        settings.ai_qwen_tcp_port = 9999
        # Test new per-engine settings
        settings.ai_claude_provider = "openai"
        settings.ai_codex_model = "codex-new"
        settings.ai_gemini_model = "gemini-advanced"
        settings.ai_qwen_model = "qwen-new"

        # Save settings
        success = settings.save(config_path)
        assert success is True

        # Load settings
        loaded_settings = Settings.load(config_path)

        # Verify values
        assert loaded_settings.ai_engines_claude == "planner"
        assert loaded_settings.ai_engines_codex == "worker"
        assert loaded_settings.ai_engines_gemini == "disabled"
        assert loaded_settings.ai_engines_qwen == "both"
        assert loaded_settings.ai_stacking_mode == "handsoff"
        assert loaded_settings.ai_dangerously_skip_permissions is False
        assert loaded_settings.ai_qwen_transport == "stdio"
        assert loaded_settings.ai_qwen_tcp_port == 9999
        # Verify new per-engine settings
        assert loaded_settings.ai_claude_provider == "openai"
        assert loaded_settings.ai_codex_model == "codex-new"
        assert loaded_settings.ai_gemini_model == "gemini-advanced"
        assert loaded_settings.ai_qwen_model == "qwen-new"
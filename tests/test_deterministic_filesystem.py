"""Tests for deterministic filesystem operations and cleanup."""

import tempfile
import shutil
from pathlib import Path
import os
from unittest.mock import patch
import pytest
from maestro.ai.types import PromptRef, RunOpts
from maestro.ai.manager import AiEngineManager
from maestro.ai.session_manager import AISessionManager


class TestClaudeTempFileCleanup:
    """Test Claude temp file creation and cleanup."""

    def test_temp_file_created_and_removed_for_claude_stdin(self):
        """Test that temp file is created for Claude stdin and properly removed."""
        from maestro.ai.runner import run_engine_command
        
        # Create a fake runner that simulates Claude execution
        class MockRunner:
            def run(self, argv, *, input_bytes=None):
                # Check that the command includes a temporary file reference
                assert any('@' in arg and 'claude_stdin_' in arg for arg in argv)
                return type('Result', (), {
                    'stdout_chunks': [b'Successful response\n'],
                    'stderr_chunks': [],
                    'returncode': 0
                })()
        
        # Create a temporary directory for our test
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Change to temp directory to isolate our test
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                # Run a command that would trigger Claude temp file creation
                runner = MockRunner()
                result = run_engine_command(
                    engine="claude",
                    argv=["claude"],
                    stdin_text="Test stdin content",
                    runner=runner
                )
                
                # Verify the command completed successfully
                assert result.exit_code == 0
                
                # Verify that no temporary files remain in the temp directory
                temp_files = list(Path(tmp_dir).glob("claude_stdin_*"))
                assert len(temp_files) == 0, f"Temp files were not cleaned up: {temp_files}"
                
            finally:
                os.chdir(original_cwd)

    def test_temp_file_removed_even_if_command_fails(self):
        """Test that temp file is removed even if the command fails."""
        from maestro.ai.runner import run_engine_command
        
        class FailingRunner:
            def run(self, argv, *, input_bytes=None):
                # Check that the command includes a temporary file reference
                assert any('@' in arg and 'claude_stdin_' in arg for arg in argv)
                return type('Result', (), {
                    'stdout_chunks': [b''],
                    'stderr_chunks': [b'Command failed\n'],
                    'returncode': 1
                })()
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                runner = FailingRunner()
                result = run_engine_command(
                    engine="claude",
                    argv=["claude"],
                    stdin_text="Test stdin content",
                    runner=runner
                )
                
                # Command should have failed
                assert result.exit_code != 0
                
                # But temp file should still be cleaned up
                temp_files = list(Path(tmp_dir).glob("claude_stdin_*"))
                assert len(temp_files) == 0, f"Temp files were not cleaned up after failure: {temp_files}"
                
            finally:
                os.chdir(original_cwd)

    def test_temp_file_removed_on_exception(self):
        """Test that temp file is removed even if an exception occurs."""
        from maestro.ai.runner import _run_with_custom_runner
        from maestro.ai.types import AiSubprocessRunner
        
        class ExceptionRunner:
            def run(self, argv, *, input_bytes=None):
                # Check that the command includes a temporary file reference
                assert any('@' in arg and 'claude_stdin_' in arg for arg in argv)
                raise RuntimeError("Simulated error during execution")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                runner = ExceptionRunner()
                
                # This should raise an exception, but temp file should still be cleaned up
                with pytest.raises(RuntimeError, match="Simulated error during execution"):
                    _run_with_custom_runner(
                        runner=runner,
                        engine="claude",
                        argv=["claude"],
                        stdin_text="Test stdin content"
                    )
                
                # Temp file should still be cleaned up despite the exception
                temp_files = list(Path(tmp_dir).glob("claude_stdin_*"))
                assert len(temp_files) == 0, f"Temp files were not cleaned up after exception: {temp_files}"
                
            finally:
                os.chdir(original_cwd)


class TestMaestroArtifactsInTempDir:
    """Test that .maestro artifacts are created under temp directory."""

    def test_maestro_state_created_in_temp_location(self):
        """Test that .maestro state is created under temp directory, not real $HOME."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a temporary state file path
            temp_state_file = Path(tmp_dir) / "test_ai_sessions.json"
            
            # Create session manager with temp state file
            session_manager = AISessionManager(state_file=temp_state_file)
            
            # Add a session
            session_manager.update_session(
                engine="qwen",
                session_id="temp-session-123",
                model="test-model",
                danger_mode=True
            )
            
            # Verify the state file was created in the temp directory
            assert temp_state_file.exists()
            
            # Verify the content
            import json
            with open(temp_state_file, 'r') as f:
                data = json.load(f)
            
            assert "qwen" in data
            assert data["qwen"]["last_session_id"] == "temp-session-123"
            
            # Verify it's not in the real .maestro directory
            real_maestro_file = Path.home() / ".maestro" / "state" / "ai_sessions.json"
            # We didn't write to the real location
            assert not real_maestro_file.exists()

    def test_log_files_created_in_temp_location(self):
        """Test that log files are created under temp directory."""
        from maestro.ai.runner import run_engine_command
        
        class MockRunner:
            def run(self, argv, *, input_bytes=None):
                return type('Result', (), {
                    'stdout_chunks': [b'{"type": "message", "content": "Test", "session_id": "log-test-456"}\n'],
                    'stderr_chunks': [b''],
                    'returncode': 0
                })()
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                # Run command to generate logs
                runner = MockRunner()
                result = run_engine_command(
                    engine="qwen",
                    argv=["qwen", "test"],
                    runner=runner
                )
                
                # Verify logs were created under MAESTRO_DOCS_ROOT
                docs_root = Path(os.environ["MAESTRO_DOCS_ROOT"])
                log_dir = docs_root / "docs" / "logs" / "ai" / "qwen"
                assert log_dir.exists()
                
                # Check that log files exist
                stdout_files = list(log_dir.glob("*_stdout.txt"))
                stderr_files = list(log_dir.glob("*_stderr.txt"))
                events_files = list(log_dir.glob("*_events.jsonl"))
                
                assert len(stdout_files) >= 1
                assert len(stderr_files) >= 1
                assert len(events_files) >= 1
                
                # Verify all files are within the temp directory
                for file_list in [stdout_files, stderr_files, events_files]:
                    for file_path in file_list:
                        # The file should be under the docs root directory
                        assert str(file_path.resolve()).startswith(str(docs_root))
                        
            finally:
                os.chdir(original_cwd)


class TestNoRealUserSettingsDependency:
    """Test that tests don't depend on real user settings."""

    def test_manager_uses_injected_settings(self):
        """Test that manager can work with injected settings, not real user settings."""
        from maestro.config.settings import Settings

        # Create a mock settings object with known values
        mock_settings = Settings(
            project_id="test-project",
            created_at="2023-01-01T00:00:00Z",
            maestro_version="1.0.0",
            base_dir="/tmp/test",
            ai_engines_claude="both",
            ai_engines_codex="both",
            ai_engines_gemini="both",
            ai_engines_qwen="both",
            ai_dangerously_skip_permissions=False,
            ai_qwen_transport="cmdline",  # Default to cmdline for testing
            ai_qwen_tcp_host="localhost",
            ai_qwen_tcp_port=7777
        )
        
        # Create a fake runner for testing
        class MockRunner:
            def run(self, argv, *, input_bytes=None):
                return type('Result', (), {
                    'stdout_chunks': [b'{"type": "message", "content": "Test", "session_id": "settings-test-789"}\n'],
                    'stderr_chunks': [b''],
                    'returncode': 0
                })()
        
        with patch('maestro.ai.manager.get_settings', return_value=mock_settings):
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Change working directory to temp directory
                original_cwd = os.getcwd()
                os.chdir(tmp_dir)
                try:
                    # Create manager with fake runner
                    runner = MockRunner()
                    manager = AiEngineManager(runner=runner)
                    
                    # Verify the manager is using our mock settings
                    assert manager.settings.ai_engines_qwen == "both"
                    assert manager.settings.ai_dangerously_skip_permissions is False
                    
                    # Run a command to make sure everything works
                    prompt = PromptRef(source="Test with mock settings")
                    opts = RunOpts()
                    result = manager.run_once("qwen", prompt, opts)
                    
                    assert result.session_id == "settings-test-789"
                    
                finally:
                    os.chdir(original_cwd)

    def test_session_manager_uses_temp_state_file(self):
        """Test that session manager uses a temporary state file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_state_file = Path(tmp_dir) / "custom_ai_sessions.json"
            
            # Create session manager with custom state file
            session_manager = AISessionManager(state_file=temp_state_file)
            
            # Verify the state file path is what we specified
            assert session_manager.state_file == temp_state_file
            
            # The parent directory should exist
            assert temp_state_file.parent.exists()
            
            # Perform an operation
            session_manager.update_session("test_engine", "test_session_abc")
            
            # Verify the file was created at the specified location
            assert temp_state_file.exists()
            
            # And verify it contains the expected data
            import json
            with open(temp_state_file, 'r') as f:
                data = json.load(f)
            
            assert "test_engine" in data
            assert data["test_engine"]["last_session_id"] == "test_session_abc"
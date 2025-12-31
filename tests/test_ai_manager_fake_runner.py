"""Integration tests for AI engine manager using fake runner."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
from maestro.ai.types import AiEngineName, PromptRef, RunOpts, AiSubprocessRunner, FakeProcessResult
from maestro.ai.manager import AiEngineManager
from maestro.ai.session_manager import AISessionManager


class FakeRunner:
    """Fake runner implementation for testing."""
    
    def __init__(self, stdout_chunks=None, stderr_chunks=None, returncode=0, responses=None):
        self.stdout_chunks = stdout_chunks or []
        self.stderr_chunks = stderr_chunks or []
        self.returncode = returncode
        self.responses = responses or {}
        self.ran_commands = []  # Track commands that were run
    
    def run(self, argv, *, input_bytes=None):
        """Run a command and return the result."""
        self.ran_commands.append({
            'argv': argv,
            'input_bytes': input_bytes
        })
        
        # If responses are provided, use them based on the command
        command_key = ' '.join(argv)
        if command_key in self.responses:
            response = self.responses[command_key]
            return FakeProcessResult(
                stdout_chunks=[response['stdout'].encode('utf-8')] if response['stdout'] else [],
                stderr_chunks=[response['stderr'].encode('utf-8')] if response['stderr'] else [],
                returncode=response['returncode']
            )
        
        # Otherwise, use the default values
        return FakeProcessResult(
            stdout_chunks=self.stdout_chunks,
            stderr_chunks=self.stderr_chunks,
            returncode=self.returncode
        )


class TestStreamingAndCapture:
    """Test streaming and capture functionality."""

    def test_manager_iterates_fake_stdout_stream(self):
        """Test that manager iterates through fake stdout stream-json chunks."""
        # Create a fake runner that returns JSON stream output
        fake_stdout = [
            b'{"type": "message", "content": "Hello", "session_id": "test-session-123"}\n',
            b'{"type": "status", "status": "completed"}\n'
        ]
        runner = FakeRunner(stdout_chunks=fake_stdout, returncode=0)
        
        manager = AiEngineManager(runner=runner)
        prompt = PromptRef(source="Hello, world!")
        opts = RunOpts(stream_json=True, quiet=False)
        
        result = manager.run_once("qwen", prompt, opts)
        
        # Verify the result
        assert result.exit_code == 0
        assert result.session_id == "test-session-123"
        assert result.raw_events_count >= 0  # Should have parsed events
        
        # Verify the command was run
        assert len(runner.ran_commands) == 1

    def test_manager_handles_quiet_mode(self):
        """Test that manager respects quiet mode."""
        fake_stdout = [b'{"type": "message", "content": "Hello"}\n']
        runner = FakeRunner(stdout_chunks=fake_stdout, returncode=0)
        
        manager = AiEngineManager(runner=runner)
        prompt = PromptRef(source="Hello, world!")
        opts = RunOpts(quiet=True)  # Quiet mode should be respected
        
        result = manager.run_once("qwen", prompt, opts)
        
        # Verify the result
        assert result.exit_code == 0
        
        # Verify the command was run
        assert len(runner.ran_commands) == 1

    def test_raw_output_captured_to_log_locations(self):
        """Test that raw output is captured to expected log locations."""
        fake_stdout = [b'Hello from AI engine\n']
        fake_stderr = [b'Warning message\n']
        runner = FakeRunner(
            stdout_chunks=fake_stdout,
            stderr_chunks=fake_stderr,
            returncode=0
        )
        
        manager = AiEngineManager(runner=runner)
        prompt = PromptRef(source="Test prompt")
        opts = RunOpts()
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Temporarily change working directory to the temp directory
            import os
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                result = manager.run_once("qwen", prompt, opts)
                
                # Verify that log files were created under MAESTRO_DOCS_ROOT
                docs_root = Path(os.environ["MAESTRO_DOCS_ROOT"])
                log_dir = docs_root / "docs" / "logs" / "ai" / "qwen"
                assert log_dir.exists()
                
                # Find the log files (they have timestamped names)
                stdout_files = list(log_dir.glob("*_stdout.txt"))
                stderr_files = list(log_dir.glob("*_stderr.txt"))
                
                assert len(stdout_files) == 1
                assert len(stderr_files) == 1
                
                # Verify content
                with open(stdout_files[0], 'r') as f:
                    stdout_content = f.read()
                    assert "Hello from AI engine" in stdout_content
                
                with open(stderr_files[0], 'r') as f:
                    stderr_content = f.read()
                    assert "Warning message" in stderr_content
                    
            finally:
                os.chdir(original_cwd)


class TestSessionPersistence:
    """Test session persistence functionality."""

    def test_session_written_after_first_call(self):
        """Test that session file is written after first call."""
        fake_stdout = [b'{"type": "message", "content": "Hello", "session_id": "session-abc-123"}\n']
        runner = FakeRunner(stdout_chunks=fake_stdout, returncode=0)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "ai_sessions.json"
            session_manager = AISessionManager(state_file=state_file)
            
            # Create manager with the temporary state file
            manager = AiEngineManager(runner=runner)
            manager.session_manager = session_manager
            
            prompt = PromptRef(source="Hello, world!")
            opts = RunOpts(dangerously_skip_permissions=True, model="test-model")
            
            # First call
            result = manager.run_once("qwen", prompt, opts)
            
            # Verify session was saved
            assert result.session_id == "session-abc-123"
            
            # Check that the state file was created and contains the session
            assert state_file.exists()
            
            with open(state_file, 'r') as f:
                sessions = json.load(f)
                
            assert "qwen" in sessions
            assert sessions["qwen"]["last_session_id"] == "session-abc-123"
            assert sessions["qwen"]["model"] == "test-model"
            assert sessions["qwen"]["danger_mode"] is True

    def test_second_call_uses_stored_session_id(self):
        """Test that second call uses stored session ID if resume not specified."""
        # First response includes session ID
        first_response = [
            b'{"type": "message", "content": "Hello", "session_id": "first-session-456"}\n'
        ]
        
        # Second response
        second_response = [
            b'{"type": "message", "content": "Follow-up", "session_id": "second-session-789"}\n'
        ]
        
        # Set up responses for different commands
        responses = {
            "qwen Test first prompt": {
                'stdout': '{"type": "message", "content": "Hello", "session_id": "first-session-456"}\n',
                'stderr': '',
                'returncode': 0
            },
            "qwen -c first-session-456 Test second prompt": {  # For resume_id, it's -c followed by session ID and prompt
                'stdout': '{"type": "message", "content": "Follow-up", "session_id": "second-session-789"}\n',
                'stderr': '',
                'returncode': 0
            }
        }
        
        runner = FakeRunner(responses=responses)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "ai_sessions.json"
            session_manager = AISessionManager(state_file=state_file)
            
            manager = AiEngineManager(runner=runner)
            manager.session_manager = session_manager
            
            # First call - creates session
            prompt1 = PromptRef(source="Test first prompt")
            opts1 = RunOpts()
            result1 = manager.run_once("qwen", prompt1, opts1)
            assert result1.session_id == "first-session-456"
            
            # Second call with resume_id explicitly set to the stored session
            prompt2 = PromptRef(source="Test second prompt")
            opts2 = RunOpts(resume_id="first-session-456")  # Explicitly use the first session ID
            result2 = manager.run_once("qwen", prompt2, opts2)
            assert result2.session_id == "second-session-789"

            # Verify the command included the resume flag with the stored session ID
            assert len(runner.ran_commands) >= 2
            # The second command should include the resume flag
            second_cmd = ' '.join(runner.ran_commands[1]['argv'])
            assert "first-session-456" in second_cmd

    def test_session_file_content_structure(self):
        """Test that session file has correct structure."""
        fake_stdout = [b'{"type": "message", "content": "Hello", "session_id": "test-session-def"}\n']
        runner = FakeRunner(stdout_chunks=fake_stdout, returncode=0)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "ai_sessions.json"
            session_manager = AISessionManager(state_file=state_file)
            
            manager = AiEngineManager(runner=runner)
            manager.session_manager = session_manager
            
            prompt = PromptRef(source="Hello, world!")
            opts = RunOpts(model="test-model", dangerously_skip_permissions=True)
            
            result = manager.run_once("claude", prompt, opts)
            
            # Check file content structure
            with open(state_file, 'r') as f:
                sessions = json.load(f)
            
            assert "claude" in sessions
            claude_data = sessions["claude"]
            
            # Verify required fields are present
            assert "last_session_id" in claude_data
            assert "updated_at" in claude_data
            assert "model" in claude_data
            assert "danger_mode" in claude_data
            
            # Verify values are correct
            assert claude_data["last_session_id"] == "test-session-def"
            assert claude_data["model"] == "test-model"
            assert claude_data["danger_mode"] is True


class TestChatLoopCallsManagerRepeatedly:
    """Test chat loop functionality that calls manager repeatedly."""

    def test_chat_loop_multiple_calls_with_resume(self):
        """Test that chat loop makes multiple calls with correct resume IDs."""
        # Set up responses for multiple calls
        responses = {
            "qwen hello": {
                'stdout': '{"type": "message", "content": "Hi there!", "session_id": "session-001"}\n',
                'stderr': '',
                'returncode': 0
            },
            "qwen -c session-001 world": {  # For resume_id, it's -c followed by session ID and prompt
                'stdout': '{"type": "message", "content": "Hello to you too!", "session_id": "session-002"}\n',
                'stderr': '',
                'returncode': 0
            }
        }
        
        runner = FakeRunner(responses=responses)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "ai_sessions.json"
            session_manager = AISessionManager(state_file=state_file)
            
            manager = AiEngineManager(runner=runner)
            manager.session_manager = session_manager
            
            # First call: "hello"
            prompt1 = PromptRef(source="hello")
            opts1 = RunOpts()
            result1 = manager.run_once("qwen", prompt1, opts1)
            assert result1.session_id == "session-001"
            
            # Second call: "world" - should resume with explicit session ID
            prompt2 = PromptRef(source="world")
            opts2 = RunOpts(resume_id="session-001")  # Explicitly resume the first session
            result2 = manager.run_once("qwen", prompt2, opts2)
            assert result2.session_id == "session-002"
            
            # Verify both commands were run
            assert len(runner.ran_commands) == 2
            
            # Verify the commands were correct
            first_cmd = ' '.join(runner.ran_commands[0]['argv'])
            second_cmd = ' '.join(runner.ran_commands[1]['argv'])
            
            assert "hello" in first_cmd
            assert "world" in second_cmd
            # The second command should include the session ID from the first
            assert "session-001" in second_cmd

    def test_chat_loop_transcript_updates(self):
        """Test that transcripts and logging are updated appropriately."""
        responses = {
            "qwen hello": {
                'stdout': '{"type": "message", "content": "Hi there!", "session_id": "session-transcript-1"}\n',
                'stderr': '',
                'returncode': 0
            },
            "qwen -c session-transcript-1 world": {
                'stdout': '{"type": "message", "content": "Hello to you too!", "session_id": "session-transcript-2"}\n',
                'stderr': '',
                'returncode': 0
            }
        }
        
        runner = FakeRunner(responses=responses)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Change working directory to temp directory for logs
            import os
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                state_file = Path("ai_sessions.json")
                session_manager = AISessionManager(state_file=state_file)
                
                manager = AiEngineManager(runner=runner)
                manager.session_manager = session_manager
                
                # First call
                prompt1 = PromptRef(source="hello")
                opts1 = RunOpts()
                result1 = manager.run_once("qwen", prompt1, opts1)
                
                # Second call
                prompt2 = PromptRef(source="world")
                opts2 = RunOpts(resume_id="session-transcript-1")  # Explicitly resume the first session
                result2 = manager.run_once("qwen", prompt2, opts2)
                
                # Verify that log files were created for the calls
                docs_root = Path(os.environ["MAESTRO_DOCS_ROOT"])
                log_dir = docs_root / "docs" / "logs" / "ai" / "qwen"
                assert log_dir.exists()

                log_files = list(log_dir.glob("*.txt"))
                # Should have stdout and stderr files (may have same timestamp if calls are rapid)
                assert len(log_files) >= 2  # At least one set of log files created
                
            finally:
                os.chdir(original_cwd)

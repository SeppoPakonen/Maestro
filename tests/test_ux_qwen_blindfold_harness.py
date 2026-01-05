"""
Tests for qwen-driven blindfold UX audit harness.

These tests are deterministic and do NOT require qwen to be installed.
They test parsing logic, budget enforcement, write-safety, and reporting.
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess

import pytest

# Import from tools (note: adjust path if needed)
import sys
tools_path = Path(__file__).parent.parent / "tools" / "ux_blindfold"
sys.path.insert(0, str(tools_path))

from qwen_driver import QwenBlindfolDriver


class FakeSubprocessResult:
    """Mock subprocess result."""
    def __init__(self, returncode=0, stdout='', stderr=''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repo directory."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    return repo


@pytest.fixture
def driver(temp_repo):
    """Create a test driver instance."""
    return QwenBlindfolDriver(
        goal="Test goal",
        maestro_bin="maestro",
        repo=str(temp_repo),
        max_steps=6,
        execute=False,
        qwen_bin="qwen"
    )


def test_driver_initialization(temp_repo):
    """Test that driver initializes with correct defaults."""
    driver = QwenBlindfolDriver(
        goal="Test goal",
        repo=str(temp_repo)
    )

    assert driver.goal == "Test goal"
    assert driver.maestro_bin == "maestro"
    assert driver.qwen_bin == "qwen"
    assert driver.max_steps == 12
    assert driver.execute is False
    assert driver.help_call_count == 0
    assert driver.run_call_count == 0
    assert driver.blocked_write_count == 0
    assert len(driver.transcript) == 0


def test_is_writey_command_detects_write_verbs(driver):
    """Test that writey command detection works."""
    # Writey commands
    assert driver._is_writey_command(["maestro", "runbook", "add"]) is True
    assert driver._is_writey_command(["maestro", "plan", "enact"]) is True
    assert driver._is_writey_command(["maestro", "runbook", "resolve"]) is True
    assert driver._is_writey_command(["maestro", "track", "commit"]) is True

    # Non-writey commands
    assert driver._is_writey_command(["maestro", "runbook", "list"]) is False
    assert driver._is_writey_command(["maestro", "runbook", "show", "123"]) is False
    assert driver._is_writey_command(["maestro", "--help"]) is False


def test_is_writey_command_detects_write_flags(driver):
    """Test that writey flag detection works."""
    assert driver._is_writey_command(["maestro", "ux", "eval", "--execute"]) is True
    assert driver._is_writey_command(["maestro", "something", "--write"]) is True
    assert driver._is_writey_command(["maestro", "foo", "--apply"]) is True


def test_handle_help_action_enforces_budget(driver):
    """Test that help action enforces budget."""
    # Exhaust budget
    for i in range(driver.MAX_HELP_CALLS):
        with patch.object(driver, '_execute_command', return_value={
            'returncode': 0, 'stdout': 'help text', 'stderr': '', 'duration': 0.1
        }):
            result = driver.handle_help_action(["maestro", "--help"])
            assert result['event'] == 'help_result'

    # Next call should be rejected
    result = driver.handle_help_action(["maestro", "track", "--help"])
    assert result['event'] == 'help_budget_exceeded'
    assert 'budget exceeded' in result['message'].lower()


def test_handle_help_action_validates_help_flag(driver):
    """Test that help action validates --help or -h flag."""
    result = driver.handle_help_action(["maestro", "runbook"])
    assert result['event'] == 'help_invalid'
    assert '--help or -h' in result['message']

    # Valid help requests
    with patch.object(driver, '_execute_command', return_value={
        'returncode': 0, 'stdout': 'help', 'stderr': '', 'duration': 0.1
    }):
        result = driver.handle_help_action(["maestro", "--help"])
        assert result['event'] == 'help_result'

        result = driver.handle_help_action(["maestro", "runbook", "-h"])
        assert result['event'] == 'help_result'


def test_handle_run_action_blocks_writes_in_safe_mode(driver):
    """Test that run action blocks write commands in safe mode."""
    # Safe mode (execute=False)
    result = driver.handle_run_action(["maestro", "runbook", "add", "test"])
    assert result['event'] == 'blocked_write_attempt'
    assert 'blocked' in result['message'].lower()
    assert driver.blocked_write_count == 1
    assert driver.telemetry['blocked_writes'] == 1


def test_handle_run_action_allows_reads_in_safe_mode(driver):
    """Test that run action allows read commands in safe mode."""
    with patch.object(driver, '_execute_command', return_value={
        'returncode': 0, 'stdout': 'output', 'stderr': '', 'duration': 0.5, 'timeout': False
    }):
        result = driver.handle_run_action(["maestro", "runbook", "list"])
        assert result['event'] == 'run_result'
        assert result['returncode'] == 0
        assert driver.telemetry['successes'] == 1
        assert driver.telemetry['run_attempts'] == 1


def test_handle_run_action_allows_writes_in_execute_mode(temp_repo):
    """Test that run action allows writes in execute mode."""
    driver = QwenBlindfolDriver(
        goal="Test",
        repo=str(temp_repo),
        execute=True  # Execute mode
    )

    with patch.object(driver, '_execute_command', return_value={
        'returncode': 0, 'stdout': 'created', 'stderr': '', 'duration': 1.0, 'timeout': False
    }):
        result = driver.handle_run_action(["maestro", "runbook", "add", "test"])
        assert result['event'] == 'run_result'
        assert result['returncode'] == 0
        assert driver.blocked_write_count == 0


def test_execute_command_truncates_output(driver):
    """Test that command output is truncated deterministically."""
    long_output = "x" * (driver.MAX_OUTPUT_CHARS + 1000)

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = FakeSubprocessResult(
            returncode=0,
            stdout=long_output,
            stderr=""
        )

        result = driver._execute_command(["echo", "test"], timeout=5)

        assert len(result['stdout']) <= driver.MAX_OUTPUT_CHARS + 20  # Account for [TRUNCATED]
        assert '[TRUNCATED]' in result['stdout']


def test_execute_actions_stops_at_max_steps(driver):
    """Test that action execution stops at max_steps."""
    actions = [
        {"action": "note", "text": f"step {i}"} for i in range(20)
    ]

    driver.execute_actions(actions)

    # Should stop at max_steps
    assert len([e for e in driver.transcript if e.get('event') == 'qwen_note']) <= driver.max_steps


def test_execute_actions_stops_on_done(driver):
    """Test that action execution stops on done action."""
    actions = [
        {"action": "note", "text": "step 1"},
        {"action": "note", "text": "step 2"},
        {"action": "done", "result": {"success": True}},
        {"action": "note", "text": "step 4 - should not execute"},
    ]

    driver.execute_actions(actions)

    # Should have 3 events (2 notes + 1 done)
    note_events = [e for e in driver.transcript if e.get('event') == 'qwen_note']
    done_events = [e for e in driver.transcript if e.get('event') == 'qwen_done']

    assert len(note_events) == 2
    assert len(done_events) == 1


def test_execute_actions_enforces_transcript_budget(driver):
    """Test that action execution stops when transcript exceeds budget."""
    # Create actions that will generate large transcript
    huge_text = "x" * 50000
    actions = [
        {"action": "note", "text": huge_text} for _ in range(10)
    ]

    driver.execute_actions(actions)

    # Should have budget exceeded event
    budget_events = [e for e in driver.transcript if e.get('event') == 'transcript_budget_exceeded']
    assert len(budget_events) > 0


def test_generate_report_deterministic(driver, temp_repo):
    """Test that report generation is deterministic."""
    # Add some transcript events
    driver.transcript = [
        {'event': 'help_result', 'argv': ['maestro', '--help'], 'returncode': 0, 'stdout': 'help', 'stderr': '', 'duration': 0.1},
        {'event': 'run_result', 'argv': ['maestro', 'runbook', 'list'], 'returncode': 0, 'stdout': 'output', 'stderr': '', 'duration': 0.5, 'timeout': False},
        {'event': 'qwen_done', 'result': {
            'success': True,
            'friction_points': [
                {'issue': 'test issue', 'evidence': 'line 1', 'severity': 'high'}
            ],
            'improvement_suggestions': [
                {'priority': 'P0', 'area': 'help', 'proposed_change': 'fix it', 'expected_impact': 'better', 'evidence': 'line 2'}
            ]
        }}
    ]

    driver.telemetry['help_calls'] = 1
    driver.telemetry['run_attempts'] = 1
    driver.telemetry['successes'] = 1

    # Generate report twice
    report1 = driver.generate_report()
    report2 = driver.generate_report()

    # Should be identical
    assert report1 == report2

    # Should contain expected sections
    assert "# Maestro UX Blindfold Audit Report" in report1
    assert "## Summary" in report1
    assert "## Friction Points" in report1
    assert "## Improvement Suggestions" in report1
    assert "test issue" in report1
    assert "fix it" in report1


def test_save_artifacts_creates_all_files(driver):
    """Test that save_artifacts creates all required files."""
    driver.transcript = [
        {'event': 'test', 'data': 'value'}
    ]
    driver.telemetry['test_key'] = 'test_value'
    driver.surface_seed = "help text"
    driver.qwen_prompt = "prompt text"

    # Save prompt and seed first (normally done in run_qwen)
    (driver.output_dir / "qwen_prompt.txt").write_text(driver.qwen_prompt)
    (driver.output_dir / "surface_seed.txt").write_text(driver.surface_seed)

    driver.save_artifacts()

    # Check all files exist
    assert (driver.output_dir / "transcript.jsonl").exists()
    assert (driver.output_dir / "telemetry.json").exists()
    assert (driver.output_dir / "report.md").exists()
    assert (driver.output_dir / "qwen_prompt.txt").exists()
    assert (driver.output_dir / "surface_seed.txt").exists()


def test_artifact_path_structure_stable(temp_repo):
    """Test that artifact path structure is stable and timestamp format correct."""
    # Use monkeypatch to freeze time
    import datetime
    from unittest.mock import patch

    fake_now = datetime.datetime(2026, 1, 3, 12, 30, 45, tzinfo=datetime.timezone.utc)

    with patch('qwen_driver.datetime') as mock_datetime:
        mock_datetime.now.return_value = fake_now
        mock_datetime.timezone = datetime.timezone

        driver = QwenBlindfolDriver(
            goal="Test goal for stable path",
            repo=str(temp_repo)
        )

        # Check path format
        path_str = str(driver.output_dir)
        assert "ux_blindfold" in path_str
        assert "20260103T123045Z" in path_str  # Timestamp format
        # Should also have short hash
        parts = driver.output_dir.name.split('_')
        assert len(parts) == 2  # timestamp_hash
        assert len(parts[1]) == 8  # 8-char hash


def test_stream_json_parser_handles_multiple_objects(driver, temp_repo):
    """Test that stream-json parsing handles multiple JSON objects."""
    fixture_path = Path(__file__).parent / "fixtures" / "ux_qwen" / "plan_stream.jsonl"

    if not fixture_path.exists():
        pytest.skip("Fixture not found")

    # Read fixture
    with open(fixture_path, 'r') as f:
        stream_output = f.read()

    # Mock qwen execution
    with patch('subprocess.Popen') as mock_popen:
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (stream_output, "")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        # Mock get_surface_seed
        with patch.object(driver, 'get_surface_seed', return_value="help text"):
            actions = driver.run_qwen()

    # Should have parsed multiple actions
    assert len(actions) > 0

    # Check action types
    action_types = [a['action'] for a in actions]
    assert 'note' in action_types
    assert 'help' in action_types
    assert 'run' in action_types
    assert 'done' in action_types


def test_stream_json_parser_handles_garbage_lines(driver):
    """Test that stream-json parsing skips garbage lines."""
    # Mix of valid JSON and garbage
    stream_output = """{"action":"note","text":"valid"}
    This is garbage
    {"action":"help","argv":["maestro","--help"]}
    More garbage here
    invalid json {
    {"action":"done","result":{"success":true}}
    """

    with patch('subprocess.Popen') as mock_popen:
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (stream_output, "")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        with patch.object(driver, 'get_surface_seed', return_value="help"):
            actions = driver.run_qwen()

    # Should have 3 valid actions
    assert len(actions) == 3
    assert actions[0]['action'] == 'note'
    assert actions[1]['action'] == 'help'
    assert actions[2]['action'] == 'done'

    # Should have garbage events in transcript
    garbage_events = [e for e in driver.transcript if e.get('event') == 'qwen_garbage']
    assert len(garbage_events) > 0


def test_safety_execute_mode_sets_maestro_docs_root(temp_repo):
    """Test that execute mode sets MAESTRO_DOCS_ROOT."""
    driver = QwenBlindfolDriver(
        goal="Test",
        repo=str(temp_repo),
        execute=True
    )

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = FakeSubprocessResult(returncode=0, stdout="ok", stderr="")

        driver._execute_command(["maestro", "runbook", "list"], timeout=5)

        # Check that MAESTRO_DOCS_ROOT was set in env
        call_kwargs = mock_run.call_args[1]
        env = call_kwargs.get('env', {})
        assert 'MAESTRO_DOCS_ROOT' in env
        assert 'docs/maestro' in env['MAESTRO_DOCS_ROOT']

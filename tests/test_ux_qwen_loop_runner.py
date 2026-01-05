"""
Tests for qwen blindfold UX loop runner.

These tests are deterministic and do NOT require qwen to be installed.
They use stub qwen and maestro scripts for predictable behavior.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import from tools
import sys
tools_path = Path(__file__).parent.parent / "tools"
sys.path.insert(0, str(tools_path))

from ux_qwen_loop.run import QwenLoopRunner
from ux_qwen_loop.stuck import StuckDetector
from ux_qwen_loop.export import export_artifacts, generate_report, extract_ux_recommendations


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repo directory."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    return repo


@pytest.fixture
def stub_qwen():
    """Path to stub qwen script."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    return str(fixtures_dir / "stub_qwen.py")


@pytest.fixture
def stub_maestro():
    """Path to stub maestro script."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    return str(fixtures_dir / "stub_maestro.py")


def test_runner_initialization(temp_repo):
    """Test that runner initializes with correct defaults."""
    runner = QwenLoopRunner(
        maestro_bin="maestro",
        repo_root=str(temp_repo),
        goal="Test goal"
    )

    assert runner.goal == "Test goal"
    assert runner.maestro_bin == "maestro"
    assert runner.qwen_bin == "qwen"
    assert runner.max_steps == 30
    assert runner.execute is False
    assert runner.postmortem is False
    assert runner.step_count == 0
    assert len(runner.attempts) == 0
    assert runner.eval_id.startswith("ux_qwen_")


def test_eval_id_format_deterministic(temp_repo):
    """Test that EVAL_ID format is stable and deterministic."""
    runner1 = QwenLoopRunner(
        maestro_bin="maestro",
        repo_root=str(temp_repo),
        goal="Test goal"
    )

    runner2 = QwenLoopRunner(
        maestro_bin="maestro",
        repo_root=str(temp_repo),
        goal="Test goal"
    )

    # Should have same short_sha component (last 8 chars) since same goal+repo
    eval1_parts = runner1.eval_id.split('_')
    eval2_parts = runner2.eval_id.split('_')

    # Format: ux_qwen_YYYYMMDD_HHMMSS_hash (5 parts when split on _)
    assert len(eval1_parts) == 5
    assert eval1_parts[0] == "ux"
    assert eval1_parts[1] == "qwen"
    assert eval1_parts[4] == eval2_parts[4]  # Same hash (last part)


def test_normalize_command(temp_repo):
    """Test command normalization."""
    runner = QwenLoopRunner(
        maestro_bin="maestro",
        repo_root=str(temp_repo),
        goal="Test"
    )

    # Test env var removal
    assert runner.stuck_detector.normalize_command("FOO=bar maestro --help") == "maestro --help"

    # Test -h -> --help normalization
    assert runner.stuck_detector.normalize_command("maestro -h") == "maestro --help"
    assert runner.stuck_detector.normalize_command("maestro runbook -h") == "maestro runbook --help"

    # Test multiple space normalization
    assert runner.stuck_detector.normalize_command("maestro   runbook    list") == "maestro runbook list"


def test_safe_command_allowlist(temp_repo):
    """Test that safe mode only allows maestro + safe shell commands."""
    runner = QwenLoopRunner(
        maestro_bin="python stub_maestro.py",
        repo_root=str(temp_repo),
        goal="Test",
        allow_any_command=False
    )

    # Should allow maestro
    assert runner._is_safe_command("python stub_maestro.py --help") is True
    assert runner._is_safe_command("maestro runbook list") is True

    # Should allow safe shell commands
    assert runner._is_safe_command("ls") is True
    assert runner._is_safe_command("pwd") is True
    assert runner._is_safe_command("cat file.txt") is True

    # Should reject other commands
    assert runner._is_safe_command("rm -rf /") is False
    assert runner._is_safe_command("curl http://example.com") is False
    assert runner._is_safe_command("python malicious.py") is False


def test_execute_command_rejects_unsafe_in_safe_mode(temp_repo):
    """Test that unsafe commands are rejected in safe mode."""
    runner = QwenLoopRunner(
        maestro_bin="maestro",
        repo_root=str(temp_repo),
        goal="Test",
        allow_any_command=False
    )

    result = runner.execute_command("curl http://example.com")

    assert result['rejected'] is True
    assert result['rejection_reason'] is not None
    assert 'not in allowlist' in result['rejection_reason']


def test_execute_command_allows_unsafe_with_flag(temp_repo):
    """Test that unsafe commands are allowed with --allow-any-command."""
    runner = QwenLoopRunner(
        maestro_bin="maestro",
        repo_root=str(temp_repo),
        goal="Test",
        allow_any_command=True
    )

    # This would normally be rejected, but allow_any_command=True
    # Note: we're not actually executing curl, just testing the safety check
    # Let it fail naturally rather than be rejected
    result = runner.execute_command("echo test")

    assert result['rejected'] is False


def test_stuck_detector_repeated_command(temp_repo):
    """Test that stuck detector catches repeated commands."""
    detector = StuckDetector(max_repeated=2)

    # First occurrence - no stuck
    step1 = {
        'step': 1,
        'command': 'maestro --help',
        'stdout': 'help text',
        'stderr': '',
        'exit_code': 0,
        'timeout': False,
        'rejected': False
    }
    assert detector.update(step1) is None

    # Second occurrence - stuck if no progress
    step2 = {
        'step': 2,
        'command': 'maestro --help',
        'stdout': 'help text',
        'stderr': '',
        'exit_code': 0,
        'timeout': False,
        'rejected': False
    }
    stuck = detector.update(step2)
    assert stuck is not None
    assert 'repeated_command' in stuck


def test_stuck_detector_help_loop(temp_repo):
    """Test that stuck detector catches help loops."""
    detector = StuckDetector(
        help_loop_threshold=0.7,
        help_loop_window=10
    )

    # Create 8 help calls and 2 run calls (80% help ratio)
    for i in range(8):
        step = {
            'step': i + 1,
            'command': f'maestro something{i} --help',
            'stdout': 'help',
            'stderr': '',
            'exit_code': 0,
            'timeout': False,
            'rejected': False
        }
        detector.update(step)

    for i in range(2):
        step = {
            'step': i + 9,
            'command': f'maestro command{i}',
            'stdout': 'output',
            'stderr': '',
            'exit_code': 0,
            'timeout': False,
            'rejected': False
        }
        stuck = detector.update(step)

    # Should be stuck due to help loop
    assert stuck is not None
    assert 'help_loop' in stuck


def test_stuck_detector_no_progress(temp_repo):
    """Test that stuck detector catches lack of progress."""
    detector = StuckDetector(no_progress_steps=3)

    # Run 3 commands with no IDs in output
    for i in range(3):
        step = {
            'step': i + 1,
            'command': f'maestro cmd{i}',
            'stdout': 'generic output',
            'stderr': '',
            'exit_code': 0,
            'timeout': False,
            'rejected': False
        }
        stuck = detector.update(step)

    # Should be stuck after 3 steps with no progress
    assert stuck is not None
    assert 'no_progress' in stuck


def test_stuck_detector_extracts_ids(temp_repo):
    """Test that stuck detector extracts progress marker IDs."""
    detector = StuckDetector()

    # Should extract various ID patterns
    text = """
    Created WorkGraph: wg-20260103-a1b2c3d4
    Created runbook: RUN-123
    Created track: TRK-456
    Scan complete: SCAN-789
    """

    ids = detector.extract_ids(text)

    assert 'wg-20260103-a1b2c3d4' in ids
    assert 'RUN-123' in ids
    assert 'TRK-456' in ids
    assert 'SCAN-789' in ids


def test_export_artifacts_creates_all_files(temp_repo):
    """Test that export creates all required artifact files."""
    eval_id = "ux_qwen_20260103_120000_abcd1234"

    attempts = [
        {'step': 1, 'command': 'maestro --help', 'stdout': 'help', 'stderr': '', 'exit_code': 0}
    ]

    telemetry = {
        'eval_id': eval_id,
        'goal': 'Test goal',
        'total_steps': 1,
        'help_calls': 1,
        'run_calls': 0,
        'successes': 1,
        'failures': 0,
        'timeouts': 0,
        'stuck_reason': 'done_by_qwen'
    }

    stuck_summary = {
        'unique_commands': 1,
        'most_repeated_command': ('maestro --help', 1)
    }

    # Use temp_repo for output
    with patch('ux_qwen_loop.export.Path.cwd', return_value=temp_repo):
        output_dir = export_artifacts(
            eval_id=eval_id,
            attempts=attempts,
            telemetry=telemetry,
            surface_seed="surface help text",
            stuck_summary=stuck_summary,
            goal="Test goal",
            repo_root=str(temp_repo),
            maestro_bin="maestro"
        )

    # Check all files exist
    assert (output_dir / "attempts.jsonl").exists()
    assert (output_dir / "telemetry.json").exists()
    assert (output_dir / "surface.txt").exists()
    assert (output_dir / "report.md").exists()


def test_generate_report_deterministic(temp_repo):
    """Test that report generation is deterministic."""
    attempts = [
        {'step': 1, 'command': 'maestro --help', 'stdout': 'help', 'stderr': '', 'exit_code': 0, 'duration': 0.1, 'timeout': False, 'rejected': False}
    ]

    telemetry = {
        'eval_id': 'test-eval',
        'goal': 'Test goal',
        'start_time': '2026-01-03T12:00:00',
        'total_steps': 1,
        'max_steps': 30,
        'help_calls': 1,
        'run_calls': 0,
        'successes': 1,
        'failures': 0,
        'timeouts': 0,
        'stuck_reason': 'done_by_qwen'
    }

    stuck_summary = {
        'unique_commands': 1,
        'most_repeated_command': ('maestro --help', 1),
        'total_timeouts': 0,
        'total_errors': 0,
        'unique_ids_seen': 0,
        'steps_since_last_progress': 0,
        'recent_help_ratio': 1.0
    }

    # Generate twice
    report1 = generate_report(
        eval_id='test-eval',
        goal='Test goal',
        telemetry=telemetry,
        stuck_summary=stuck_summary,
        attempts=attempts,
        maestro_bin='maestro',
        repo_root=str(temp_repo)
    )

    report2 = generate_report(
        eval_id='test-eval',
        goal='Test goal',
        telemetry=telemetry,
        stuck_summary=stuck_summary,
        attempts=attempts,
        maestro_bin='maestro',
        repo_root=str(temp_repo)
    )

    # Should be identical
    assert report1 == report2
    assert '# Qwen Blindfold UX Evaluation Report' in report1
    assert 'Test goal' in report1


def test_ux_recommendations_from_patterns(temp_repo):
    """Test that UX recommendations are extracted from failure patterns."""
    attempts = []

    stuck_summary = {
        'most_repeated_command': ('maestro runbook resolve', 3),
        'recent_help_ratio': 0.8,
        'total_timeouts': 2,
        'steps_since_last_progress': 6,
        'total_errors': 4
    }

    recommendations = extract_ux_recommendations(attempts, 'stuck', stuck_summary)

    # Should have recommendations for all detected issues
    rec_titles = [r['title'].lower() for r in recommendations]

    assert any('repeated command' in t for t in rec_titles)
    assert any('discoverability' in t for t in rec_titles)
    assert any('timeout' in t or 'progress' in t for t in rec_titles)
    assert any('success' in t or 'progress' in t for t in rec_titles)
    assert any('error' in t for t in rec_titles)


def test_bound_output_truncates_deterministically(temp_repo):
    """Test that output truncation is deterministic."""
    runner = QwenLoopRunner(
        maestro_bin="maestro",
        repo_root=str(temp_repo),
        goal="Test"
    )

    long_text = "x" * 3000

    bounded = runner._bound_output(long_text)

    assert len(bounded) <= runner.MAX_OUTPUT_CHARS + 20
    assert '[TRUNCATED]' in bounded


def test_parse_qwen_output_handles_stream_json(temp_repo):
    """Test that qwen output parser handles stream-json (NDJSON)."""
    runner = QwenLoopRunner(
        maestro_bin="maestro",
        repo_root=str(temp_repo),
        goal="Test"
    )

    # Multiple JSON objects (NDJSON)
    output = """{"next_command": "maestro --help", "note": "first"}
{"next_command": "maestro runbook list", "note": "second"}
{"next_command": "maestro track list", "note": "third", "done": false}"""

    parsed = runner._parse_qwen_output(output)

    # Should take the last valid one
    assert parsed['next_command'] == "maestro track list"
    assert parsed['note'] == "third"
    assert parsed['done'] is False


def test_parse_qwen_output_handles_cmd_fallback(temp_repo):
    """Test that qwen output parser handles CMD: fallback."""
    runner = QwenLoopRunner(
        maestro_bin="maestro",
        repo_root=str(temp_repo),
        goal="Test"
    )

    # Fallback format
    output = """Some preamble text
CMD: maestro runbook list
Some trailing text"""

    parsed = runner._parse_qwen_output(output)

    assert parsed['next_command'] == "maestro runbook list"
    assert parsed['error'] is None

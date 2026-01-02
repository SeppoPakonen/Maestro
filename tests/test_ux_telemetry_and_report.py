"""
Tests for UX telemetry recorder and report generator.

All tests are deterministic with bounded outputs.
"""

import pytest
import json
import tempfile
from pathlib import Path
from maestro.ux.telemetry import TelemetryRecorder, AttemptRecord
from maestro.ux.report import UXReportGenerator
from maestro.ux.help_surface import HelpNode


def test_telemetry_record_attempt_dry_run():
    """Test that dry-run attempts are recorded without executing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        telemetry = TelemetryRecorder(
            eval_id="test-eval-001",
            goal="Test goal",
            output_dir=output_dir,
            verbose=False
        )

        # Record attempt in dry-run mode
        record = telemetry.record_attempt(
            command_argv=['maestro', 'plan', 'list'],
            timeout=30.0,
            dry_run=True
        )

        # Should create record without executing
        assert record.command_argv == ['maestro', 'plan', 'list']
        assert record.exit_code == 0
        assert record.stdout_excerpt == "[DRY RUN]"
        assert record.duration_ms == 0
        assert record.timed_out is False

        # Should be added to attempts list
        assert len(telemetry.attempts) == 1
        assert telemetry.attempts[0] == record


def test_telemetry_multiple_attempts():
    """Test recording multiple attempts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        telemetry = TelemetryRecorder(
            eval_id="test-eval-002",
            goal="Test goal",
            output_dir=output_dir,
            verbose=False
        )

        # Record 3 attempts
        telemetry.record_attempt(['maestro', 'plan', 'list'], dry_run=True)
        telemetry.record_attempt(['maestro', 'repo', 'resolve'], dry_run=True)
        telemetry.record_attempt(['maestro', 'runbook', 'show'], dry_run=True)

        assert len(telemetry.attempts) == 3

        # Attempt indices should be sequential
        assert telemetry.attempts[0].attempt_index == 0
        assert telemetry.attempts[1].attempt_index == 1
        assert telemetry.attempts[2].attempt_index == 2


def test_telemetry_save_files():
    """Test that telemetry saves JSON files correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        telemetry = TelemetryRecorder(
            eval_id="test-eval-003",
            goal="Test goal",
            output_dir=output_dir,
            verbose=False
        )

        telemetry.record_attempt(['maestro', 'plan', 'list'], dry_run=True)
        telemetry.increment_help_calls(5)

        # Save telemetry
        telemetry.save_telemetry()

        # Check telemetry.json exists
        telemetry_json = output_dir / 'telemetry.json'
        assert telemetry_json.exists()

        # Verify content
        with open(telemetry_json, 'r') as f:
            data = json.load(f)

        assert data['eval_id'] == 'test-eval-003'
        assert data['goal'] == 'Test goal'
        assert data['total_attempts'] == 1
        assert data['help_call_count'] == 5

        # Check attempts.jsonl exists
        attempts_jsonl = output_dir / 'attempts.jsonl'
        assert attempts_jsonl.exists()

        # Verify JSONL format (one JSON object per line)
        with open(attempts_jsonl, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 1
        attempt_data = json.loads(lines[0])
        assert attempt_data['attempt_index'] == 0
        assert attempt_data['command_argv'] == ['maestro', 'plan', 'list']


def test_telemetry_summary():
    """Test get_summary returns correct statistics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        telemetry = TelemetryRecorder(
            eval_id="test-eval-004",
            goal="Test goal",
            output_dir=output_dir,
            verbose=False
        )

        # Record successful and failed attempts
        telemetry.record_attempt(['maestro', 'plan', 'list'], dry_run=True)  # success (exit 0)

        # Manually add a failed attempt
        failed_record = AttemptRecord(
            attempt_index=1,
            command_argv=['maestro', 'plan', 'unknown'],
            exit_code=1,
            duration_ms=100,
            stdout_excerpt="",
            stderr_excerpt="Error: unknown command",
            timestamp="2025-01-01T00:00:00",
            timed_out=False
        )
        telemetry.attempts.append(failed_record)

        telemetry.increment_help_calls(3)
        telemetry.timeout_count = 1
        telemetry.unknown_command_count = 1

        summary = telemetry.get_summary()

        assert summary['total_attempts'] == 2
        assert summary['successful_attempts'] == 1
        assert summary['failed_attempts'] == 1
        assert summary['help_call_count'] == 3
        assert summary['timeout_count'] == 1
        assert summary['unknown_command_count'] == 1


def test_report_generation_basic():
    """Test basic report generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Create fake surface
        help_surface = {
            ('maestro',): HelpNode(
                command_path=['maestro'],
                help_text='Maestro CLI',
                help_hash='hash1',
                discovered_subcommands=['plan', 'repo']
            ),
        }

        # Create fake attempts
        attempts = [
            AttemptRecord(
                attempt_index=0,
                command_argv=['maestro', 'plan', 'list'],
                exit_code=0,
                duration_ms=150,
                stdout_excerpt="List of plans...",
                stderr_excerpt="",
                timestamp="2025-01-01T00:00:00",
                timed_out=False
            ),
        ]

        telemetry_summary = {
            'eval_id': 'test-eval-005',
            'goal': 'Test goal',
            'total_attempts': 1,
            'help_call_count': 2,
            'successful_attempts': 1,
            'failed_attempts': 0,
            'timeout_count': 0,
            'unknown_command_count': 0,
        }

        # Generate report
        generator = UXReportGenerator(
            eval_id='test-eval-005',
            goal='Test goal',
            help_surface=help_surface,
            attempts=attempts,
            telemetry_summary=telemetry_summary,
            verbose=False
        )

        report_path = output_dir / 'report.md'
        generator.generate_report(report_path)

        # Check report exists
        assert report_path.exists()

        # Read report content
        with open(report_path, 'r') as f:
            content = f.read()

        # Verify report sections
        assert '# UX Evaluation Report' in content
        assert '## Goal' in content
        assert 'Test goal' in content
        assert '## Discovered Surface Summary' in content
        assert '## Attempts Timeline' in content
        assert '## Failure Categorization' in content
        assert '## Suggested Improvements' in content
        assert '## Next Best Command' in content


def test_report_bounded_output():
    """Test that report output is bounded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        help_surface = {}

        # Create many failed attempts
        attempts = []
        for i in range(50):
            attempts.append(AttemptRecord(
                attempt_index=i,
                command_argv=['maestro', f'cmd{i}'],
                exit_code=1,
                duration_ms=100,
                stdout_excerpt="",
                stderr_excerpt=f"Error {i}",
                timestamp="2025-01-01T00:00:00",
                timed_out=False
            ))

        telemetry_summary = {
            'eval_id': 'test-eval-006',
            'goal': 'Test goal',
            'total_attempts': 50,
            'help_call_count': 10,
            'successful_attempts': 0,
            'failed_attempts': 50,
            'timeout_count': 0,
            'unknown_command_count': 0,
        }

        generator = UXReportGenerator(
            eval_id='test-eval-006',
            goal='Test goal',
            help_surface=help_surface,
            attempts=attempts,
            telemetry_summary=telemetry_summary,
            verbose=False
        )

        report_path = output_dir / 'report.md'
        generator.generate_report(report_path)

        # Read report
        with open(report_path, 'r') as f:
            content = f.read()

        # Should show "First 5 Attempts" not all 50
        assert 'First 5 Attempts' in content

        # Report should be bounded (not huge)
        assert len(content) < 50000  # Less than 50KB


def test_report_failure_categorization():
    """Test that failures are categorized correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        help_surface = {}

        # Create attempts with different failure types
        attempts = [
            # Timeout
            AttemptRecord(
                attempt_index=0,
                command_argv=['maestro', 'slow'],
                exit_code=124,
                duration_ms=30000,
                stdout_excerpt="",
                stderr_excerpt="[TIMEOUT]",
                timestamp="2025-01-01T00:00:00",
                timed_out=True
            ),
            # Unknown command
            AttemptRecord(
                attempt_index=1,
                command_argv=['maestro', 'unknown'],
                exit_code=127,
                duration_ms=10,
                stdout_excerpt="",
                stderr_excerpt="Command not found",
                timestamp="2025-01-01T00:00:01",
                timed_out=False
            ),
            # Help ambiguity
            AttemptRecord(
                attempt_index=2,
                command_argv=['maestro', 'plan', 'bad'],
                exit_code=1,
                duration_ms=50,
                stdout_excerpt="",
                stderr_excerpt="unrecognized argument: bad",
                timestamp="2025-01-01T00:00:02",
                timed_out=False
            ),
        ]

        telemetry_summary = {
            'eval_id': 'test-eval-007',
            'goal': 'Test goal',
            'total_attempts': 3,
            'help_call_count': 5,
            'successful_attempts': 0,
            'failed_attempts': 3,
            'timeout_count': 1,
            'unknown_command_count': 1,
        }

        generator = UXReportGenerator(
            eval_id='test-eval-007',
            goal='Test goal',
            help_surface=help_surface,
            attempts=attempts,
            telemetry_summary=telemetry_summary,
            verbose=False
        )

        report_path = output_dir / 'report.md'
        generator.generate_report(report_path)

        # Read report
        with open(report_path, 'r') as f:
            content = f.read()

        # Should categorize failures
        assert '### Timeouts' in content
        assert '### Unknown Commands' in content
        assert '### Help Ambiguity' in content or '### Unclear Errors' in content


def test_report_suggested_improvements():
    """Test that improvements are suggested based on heuristics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        help_surface = {}
        attempts = []

        # High unknown command count should trigger improvement
        telemetry_summary = {
            'eval_id': 'test-eval-008',
            'goal': 'Test goal',
            'total_attempts': 5,
            'help_call_count': 15,
            'successful_attempts': 0,
            'failed_attempts': 5,
            'timeout_count': 0,
            'unknown_command_count': 4,  # High
        }

        generator = UXReportGenerator(
            eval_id='test-eval-008',
            goal='Test goal',
            help_surface=help_surface,
            attempts=attempts,
            telemetry_summary=telemetry_summary,
            verbose=False
        )

        report_path = output_dir / 'report.md'
        generator.generate_report(report_path)

        with open(report_path, 'r') as f:
            content = f.read()

        # Should suggest help structure improvement
        assert 'Help Structure' in content or 'subcommand discovery' in content.lower()

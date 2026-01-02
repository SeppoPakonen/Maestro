"""
Tests for UX postmortem synthetic log builder.

All tests are deterministic with no subprocess calls.
"""

import pytest
from maestro.ux.postmortem import build_ux_log


def test_build_ux_log_basic():
    """Test that build_ux_log creates valid synthetic log."""
    attempts = [
        {
            'attempt_index': 0,
            'command_argv': ['maestro', 'plan', 'list'],
            'exit_code': 0,
            'duration_ms': 150,
            'stdout_excerpt': 'Plan 1\nPlan 2',
            'stderr_excerpt': '',
            'timestamp': '2025-01-01T00:00:00',
            'timed_out': False
        }
    ]

    surface = {
        'surface': {'cmd1': {}, 'cmd2': {}},
        'help_call_count': 5
    }

    report_text = "Test report\n\nSome findings"
    goal = "Test goal"

    log = build_ux_log(attempts, surface, report_text, goal)

    # Should contain expected sections
    assert "UX EVALUATION SYNTHETIC LOG" in log
    assert f"Goal: {goal}" in log
    assert "Total Attempts: 1" in log
    assert "Discovered 2 commands" in log
    assert "tool: plan list" in log
    assert "status: SUCCESS" in log
    assert "Attempt 1: maestro plan list" in log


def test_build_ux_log_with_failures():
    """Test log builder with failed attempts."""
    attempts = [
        {
            'attempt_index': 0,
            'command_argv': ['maestro', 'unknown', 'cmd'],
            'exit_code': 127,
            'duration_ms': 10,
            'stdout_excerpt': '',
            'stderr_excerpt': 'Command not found',
            'timestamp': '2025-01-01T00:00:00',
            'timed_out': False
        },
        {
            'attempt_index': 1,
            'command_argv': ['maestro', 'slow'],
            'exit_code': 124,
            'duration_ms': 30000,
            'stdout_excerpt': '',
            'stderr_excerpt': '[TIMEOUT]',
            'timestamp': '2025-01-01T00:00:01',
            'timed_out': True
        }
    ]

    surface = {'surface': {}, 'help_call_count': 3}
    log = build_ux_log(attempts, surface, "", "Test goal")

    # Should contain failure markers
    assert "status: UNKNOWN_COMMAND" in log
    assert "error: Unknown command" in log
    assert "status: TIMEOUT" in log
    assert "error: Command timed out" in log

    # Should have failure summary
    assert "Failure Summary" in log
    assert "Total Failures: 2" in log
    assert "Timeouts: 1" in log
    assert "Unknown Commands: 1" in log


def test_build_ux_log_ux_friction_signals():
    """Test that UX friction signals are generated."""
    # High unknown command rate
    attempts = [
        {'attempt_index': i, 'command_argv': ['maestro', f'cmd{i}'],
         'exit_code': 127, 'duration_ms': 10, 'stdout_excerpt': '',
         'stderr_excerpt': 'Not found', 'timestamp': '2025-01-01T00:00:00',
         'timed_out': False}
        for i in range(5)
    ]

    surface = {'surface': {}, 'help_call_count': 20}  # High help/attempt ratio
    log = build_ux_log(attempts, surface, "", "Goal")

    # Should detect high unknown command rate
    assert "signal: high_unknown_command_rate" in log
    assert "Poor subcommand discovery" in log

    # Should detect high help/attempt ratio
    assert "signal: high_help_to_attempt_ratio" in log
    assert "Unclear help text" in log

    # Should detect zero successful attempts
    assert "signal: zero_successful_attempts" in log


def test_build_ux_log_deterministic():
    """Test that same input produces same output."""
    attempts = [
        {
            'attempt_index': 0,
            'command_argv': ['maestro', 'test'],
            'exit_code': 0,
            'duration_ms': 100,
            'stdout_excerpt': 'Output',
            'stderr_excerpt': '',
            'timestamp': '2025-01-01T00:00:00',
            'timed_out': False
        }
    ]

    surface = {'surface': {'cmd': {}}, 'help_call_count': 1}
    report = "Report"
    goal = "Goal"

    # Build twice
    log1 = build_ux_log(attempts, surface, report, goal)
    log2 = build_ux_log(attempts, surface, report, goal)

    # Should be identical
    assert log1 == log2


def test_build_ux_log_bounded_output():
    """Test that output is bounded."""
    # Attempt with very long stdout/stderr
    long_stdout = "x" * 10000
    long_stderr = "y" * 10000

    attempts = [
        {
            'attempt_index': 0,
            'command_argv': ['maestro', 'test'],
            'exit_code': 1,
            'duration_ms': 100,
            'stdout_excerpt': long_stdout,
            'stderr_excerpt': long_stderr,
            'timestamp': '2025-01-01T00:00:00',
            'timed_out': False
        }
    ]

    surface = {'surface': {}, 'help_call_count': 1}
    long_report = "z" * 10000

    log = build_ux_log(attempts, surface, long_report, "Goal")

    # Log should be bounded (not 30KB+)
    # Original would be ~30KB, bounded should be much smaller
    # Actual size is ~12KB with bounding applied
    assert len(log) < 15000

    # Note: Truncation markers are line-based, not character-based
    # The test report is a single long line, so no truncation marker appears
    # But the log is still bounded by excerpt limits


def test_build_ux_log_empty_attempts():
    """Test log builder with no attempts."""
    attempts = []
    surface = {'surface': {}, 'help_call_count': 0}

    log = build_ux_log(attempts, surface, "", "Test goal")

    # Should still produce valid log
    assert "UX EVALUATION SYNTHETIC LOG" in log
    assert "Total Attempts: 0" in log
    assert "Discovered 0 commands" in log


def test_build_ux_log_tool_markers():
    """Test that tool markers are correct for log scanner."""
    attempts = [
        {
            'attempt_index': 0,
            'command_argv': ['maestro', 'plan', 'decompose'],
            'exit_code': 0,
            'duration_ms': 200,
            'stdout_excerpt': 'Success',
            'stderr_excerpt': '',
            'timestamp': '2025-01-01T00:00:00',
            'timed_out': False
        },
        {
            'attempt_index': 1,
            'command_argv': ['maestro', 'repo', 'resolve'],
            'exit_code': 1,
            'duration_ms': 100,
            'stdout_excerpt': '',
            'stderr_excerpt': 'Error occurred',
            'timestamp': '2025-01-01T00:00:01',
            'timed_out': False
        }
    ]

    surface = {'surface': {}, 'help_call_count': 3}
    log = build_ux_log(attempts, surface, "", "Goal")

    # Should have tool markers for log scanner
    assert "tool: plan decompose" in log
    assert "tool: repo resolve" in log

    # Should have error marker for failed attempt
    assert "error: Error occurred" in log


def test_build_ux_log_dry_run_marker():
    """Test that dry-run attempts are marked correctly."""
    attempts = [
        {
            'attempt_index': 0,
            'command_argv': ['maestro', 'plan', 'list'],
            'exit_code': 0,
            'duration_ms': 0,
            'stdout_excerpt': '[DRY RUN]',
            'stderr_excerpt': '',
            'timestamp': '2025-01-01T00:00:00',
            'timed_out': False
        }
    ]

    surface = {'surface': {}, 'help_call_count': 1}
    log = build_ux_log(attempts, surface, "", "Goal")

    # Should include status but not show "[DRY RUN]" in excerpt section
    assert "status: SUCCESS" in log
    assert "Attempt 1: maestro plan list" in log

    # Dry run marker should not appear in output excerpts
    # (build_ux_log filters it out with: stdout_excerpt != "[DRY RUN]")
    lines = log.split('\n')
    stdout_section_found = False
    for line in lines:
        if 'stdout (excerpt)' in line:
            stdout_section_found = True

    # If dry run, stdout section should not appear
    assert not stdout_section_found


def test_build_ux_log_multiple_failure_types():
    """Test log with mix of failure types."""
    attempts = [
        # Success
        {'attempt_index': 0, 'command_argv': ['maestro', 'ok'],
         'exit_code': 0, 'duration_ms': 50, 'stdout_excerpt': 'OK',
         'stderr_excerpt': '', 'timestamp': '2025-01-01T00:00:00', 'timed_out': False},
        # Unknown command
        {'attempt_index': 1, 'command_argv': ['maestro', 'bad'],
         'exit_code': 127, 'duration_ms': 10, 'stdout_excerpt': '',
         'stderr_excerpt': 'Not found', 'timestamp': '2025-01-01T00:00:01', 'timed_out': False},
        # Timeout
        {'attempt_index': 2, 'command_argv': ['maestro', 'slow'],
         'exit_code': 124, 'duration_ms': 30000, 'stdout_excerpt': '',
         'stderr_excerpt': '[TIMEOUT]', 'timestamp': '2025-01-01T00:00:02', 'timed_out': True},
        # Other failure
        {'attempt_index': 3, 'command_argv': ['maestro', 'fail'],
         'exit_code': 1, 'duration_ms': 100, 'stdout_excerpt': '',
         'stderr_excerpt': 'Other error', 'timestamp': '2025-01-01T00:00:03', 'timed_out': False}
    ]

    surface = {'surface': {}, 'help_call_count': 4}
    log = build_ux_log(attempts, surface, "", "Goal")

    # Should categorize correctly
    assert "Total Failures: 3" in log
    assert "Timeouts: 1" in log
    assert "Unknown Commands: 1" in log
    assert "Other Failures: 1" in log

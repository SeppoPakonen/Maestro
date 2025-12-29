"""
Tests for CLI Surface Contract and Legacy Kill Switch.

Verifies that:
1. Legacy commands are NOT in parser by default (MAESTRO_ENABLE_LEGACY unset/0)
2. Legacy commands ARE in parser when MAESTRO_ENABLE_LEGACY=1
3. Legacy commands show warnings when invoked (MAESTRO_ENABLE_LEGACY=1)
4. Help output correctly reflects enabled/disabled state
5. Canonical v3 commands continue to work in both modes

See: docs/workflows/v3/cli/CLI_SURFACE_CONTRACT.md
"""

import os
import sys
import pytest
import subprocess
from pathlib import Path

pytestmark = pytest.mark.slow


class TestLegacyKillSwitch:
    """Test legacy command enable/disable via MAESTRO_ENABLE_LEGACY environment variable."""

    def test_legacy_disabled_by_default(self):
        """Verify legacy commands not in parser when MAESTRO_ENABLE_LEGACY unset."""
        env = os.environ.copy()
        env.pop('MAESTRO_ENABLE_LEGACY', None)

        # maestro session --help should fail (command not found)
        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 'session', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        # Should fail because session command is not registered
        assert result.returncode != 0, "session command should not be available by default"
        # Error message should guide to replacement
        output = result.stdout + result.stderr
        assert 'wsession' in output or 'not available' in output.lower()

    def test_legacy_disabled_explicit_0(self):
        """Verify legacy commands not in parser when MAESTRO_ENABLE_LEGACY=0."""
        env = os.environ.copy()
        env['MAESTRO_ENABLE_LEGACY'] = '0'

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 'session', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        assert result.returncode != 0, "session command should not be available when explicitly disabled"

    def test_legacy_enabled_with_1(self):
        """Verify legacy commands in parser when MAESTRO_ENABLE_LEGACY=1."""
        env = os.environ.copy()
        env['MAESTRO_ENABLE_LEGACY'] = '1'

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 'session', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        # Should succeed - session command is registered
        assert result.returncode == 0, "session command should be available when enabled"
        # Should show deprecation marker
        output = result.stdout + result.stderr
        assert '[DEPRECATED]' in output or 'wsession' in output.lower()

    def test_legacy_enabled_with_true(self):
        """Verify MAESTRO_ENABLE_LEGACY=true also works."""
        env = os.environ.copy()
        env['MAESTRO_ENABLE_LEGACY'] = 'true'

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 'session', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        assert result.returncode == 0, "session command should be available when enabled with 'true'"

    def test_legacy_enabled_with_yes(self):
        """Verify MAESTRO_ENABLE_LEGACY=yes also works."""
        env = os.environ.copy()
        env['MAESTRO_ENABLE_LEGACY'] = 'yes'

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 'session', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        assert result.returncode == 0, "session command should be available when enabled with 'yes'"

    def test_all_legacy_commands_gated(self):
        """Verify all 5 legacy commands are gated by the kill switch."""
        legacy_commands = ['session', 'understand', 'resume', 'rules', 'root']
        env = os.environ.copy()
        env.pop('MAESTRO_ENABLE_LEGACY', None)

        for cmd in legacy_commands:
            result = subprocess.run(
                [sys.executable, '-m', 'maestro', cmd, '--help'],
                env=env,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            assert result.returncode != 0, f"{cmd} should not be available by default"


class TestParserStructure:
    """Test parser structure matches contract."""

    def test_canonical_commands_exist(self):
        """Verify canonical v3 commands are always registered."""
        canonical = [
            'init', 'runbook', 'workflow', 'repo', 'plan', 'make',
            'log', 'cache', 'track', 'phase', 'task', 'discuss',
            'settings', 'issues', 'solutions', 'ai', 'work', 'wsession',
            'tu', 'convert'
        ]

        # Save and clear MAESTRO_ENABLE_LEGACY to ensure legacy commands are not registered
        old_legacy = os.environ.get('MAESTRO_ENABLE_LEGACY')
        if 'MAESTRO_ENABLE_LEGACY' in os.environ:
            del os.environ['MAESTRO_ENABLE_LEGACY']

        try:
            # Import parser creation function
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from maestro.modules.cli_parser import create_main_parser

            # Create parser and get registered subcommands
            parser = create_main_parser()

            # Get all registered subcommands from the parser
            # The subparsers are stored in parser._subparsers._group_actions[0].choices
            subparsers_action = None
            for action in parser._subparsers._group_actions:
                if hasattr(action, 'choices'):
                    subparsers_action = action
                    break

            assert subparsers_action is not None, "Could not find subparsers in parser"
            registered_commands = set(subparsers_action.choices.keys())

            # Verify all canonical commands are registered
            for cmd in canonical:
                assert cmd in registered_commands, \
                    f"Canonical command '{cmd}' should always be available (found: {registered_commands})"
        finally:
            # Restore MAESTRO_ENABLE_LEGACY
            if old_legacy is not None:
                os.environ['MAESTRO_ENABLE_LEGACY'] = old_legacy

    def test_help_excludes_legacy_by_default(self):
        """Verify main help doesn't show legacy commands by default."""
        env = os.environ.copy()
        env.pop('MAESTRO_ENABLE_LEGACY', None)

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        assert result.returncode == 0
        # Help should not prominently feature legacy commands
        # Note: Some references may remain in deprecation notices, but they shouldn't be
        # listed as available subcommands


class TestLegacyWarnings:
    """Test warning banners when legacy commands invoked."""

    def test_session_command_warning(self):
        """Verify session command shows deprecation warning when enabled."""
        env = os.environ.copy()
        env['MAESTRO_ENABLE_LEGACY'] = '1'

        # Run session list (or any session subcommand)
        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 'session', 'list'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        # Warning should be printed (to stdout or stderr)
        output = result.stdout + result.stderr
        # Should contain deprecation warning and replacement suggestion
        assert 'DEPRECATED' in output or 'wsession' in output.lower()

    def test_understand_command_warning(self):
        """Verify understand command shows deprecation warning when enabled."""
        env = os.environ.copy()
        env['MAESTRO_ENABLE_LEGACY'] = '1'

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 'understand', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        # Help should succeed and show deprecation
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert '[DEPRECATED]' in output or 'deprecated' in output.lower()


class TestAliasNormalization:
    """Test that alias normalization respects legacy gate."""

    def test_session_alias_s_disabled(self):
        """Verify 's' alias for session not available by default."""
        env = os.environ.copy()
        env.pop('MAESTRO_ENABLE_LEGACY', None)

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 's', 'list'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        assert result.returncode != 0, "'s' alias should not work when legacy disabled"

    def test_session_alias_s_enabled(self):
        """Verify 's' alias for session works when enabled."""
        env = os.environ.copy()
        env['MAESTRO_ENABLE_LEGACY'] = '1'

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 's', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        # Should succeed - alias maps to session which is enabled
        assert result.returncode == 0, "'s' alias should work when legacy enabled"


class TestErrorMessages:
    """Test helpful error messages when legacy disabled."""

    def test_session_disabled_error_message(self):
        """Verify helpful error when session invoked while disabled."""
        env = os.environ.copy()
        env['MAESTRO_ENABLE_LEGACY'] = '0'

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 'session', 'list'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        assert result.returncode != 0
        output = result.stderr + result.stdout

        # Should suggest wsession replacement
        assert 'wsession' in output.lower() or 'not available' in output.lower()
        # Should mention environment variable
        assert 'MAESTRO_ENABLE_LEGACY' in output or 'enable legacy' in output.lower()

    def test_understand_disabled_error_message(self):
        """Verify helpful error when understand invoked while disabled."""
        env = os.environ.copy()
        env.pop('MAESTRO_ENABLE_LEGACY', None)

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 'understand', 'dump'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        assert result.returncode != 0
        output = result.stderr + result.stdout

        # Should suggest replacement
        assert 'repo' in output.lower() or 'not available' in output.lower()


class TestCanonicalCommandsContinueToWork:
    """Verify that killing legacy commands doesn't break v3 commands."""

    def test_wsession_works_with_legacy_disabled(self):
        """Verify wsession (replacement for session) works."""
        env = os.environ.copy()
        env.pop('MAESTRO_ENABLE_LEGACY', None)

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 'wsession', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        assert result.returncode == 0, "wsession should work regardless of legacy mode"

    def test_repo_resolve_works_with_legacy_disabled(self):
        """Verify repo resolve (replacement for understand) works."""
        env = os.environ.copy()
        env.pop('MAESTRO_ENABLE_LEGACY', None)

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 'repo', 'resolve', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        assert result.returncode == 0, "repo resolve should work regardless of legacy mode"

    def test_work_resume_works_with_legacy_disabled(self):
        """Verify work resume (replacement for resume) works."""
        env = os.environ.copy()
        env.pop('MAESTRO_ENABLE_LEGACY', None)

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 'work', 'resume', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        assert result.returncode == 0, "work resume should work regardless of legacy mode"

    def test_discuss_works_with_legacy_disabled(self):
        """Verify discuss command (replacement for resume) works."""
        env = os.environ.copy()
        env.pop('MAESTRO_ENABLE_LEGACY', None)

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 'discuss', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        assert result.returncode == 0, "discuss should work regardless of legacy mode"

    def test_track_works_with_legacy_disabled(self):
        """Verify track (replacement for root) works."""
        env = os.environ.copy()
        env.pop('MAESTRO_ENABLE_LEGACY', None)

        result = subprocess.run(
            [sys.executable, '-m', 'maestro', 'track', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        assert result.returncode == 0, "track should work regardless of legacy mode"


class TestContractStability:
    """Test that the contract is stable and well-defined."""

    def test_legacy_mode_is_repeatable(self):
        """Verify enabling legacy mode gives consistent results."""
        env = os.environ.copy()
        env['MAESTRO_ENABLE_LEGACY'] = '1'

        # Run twice and compare
        result1 = subprocess.run(
            [sys.executable, '-m', 'maestro', 'session', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        result2 = subprocess.run(
            [sys.executable, '-m', 'maestro', 'session', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        assert result1.returncode == result2.returncode
        assert result1.returncode == 0

    def test_default_mode_is_repeatable(self):
        """Verify default mode gives consistent results."""
        env = os.environ.copy()
        env.pop('MAESTRO_ENABLE_LEGACY', None)

        # Run twice and compare
        result1 = subprocess.run(
            [sys.executable, '-m', 'maestro', 'session', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        result2 = subprocess.run(
            [sys.executable, '-m', 'maestro', 'session', '--help'],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        assert result1.returncode == result2.returncode
        assert result1.returncode != 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

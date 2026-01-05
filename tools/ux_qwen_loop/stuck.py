"""
Stuck detection for qwen blindfold UX evaluation loop.

Detects when qwen is stuck in patterns that indicate UX issues:
- Repeated commands without progress
- Help loops (too many help calls)
- Repeated timeouts
- Repeated errors
- No progress (no new IDs or files created)
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class StuckDetector:
    """Deterministic stuck detection for qwen evaluation loops."""

    # Patterns for extracting IDs (progress markers)
    ID_PATTERNS = [
        r'wg-\d{8}-[a-f0-9]{8}',  # WorkGraph IDs
        r'run-\d{8}-[a-f0-9]{8}',  # Run IDs
        r'SCAN-\d{3}',  # Scan IDs
        r'ISSUE-\d{3}',  # Issue IDs
        r'ux_eval_\d{8}_\d{6}_[a-f0-9]{8}',  # UX eval IDs
        r'RUN-\d{3}',  # Runbook IDs
        r'TRK-\d{3}',  # Track IDs
        r'PH-\d{3}',  # Phase IDs
        r'TASK-\d{3}',  # Task IDs
    ]

    def __init__(
        self,
        max_repeated: int = 2,
        help_loop_threshold: float = 0.7,
        help_loop_window: int = 10,
        no_progress_steps: int = 8,
        max_same_timeout: int = 2,
        max_same_error: int = 3
    ):
        """
        Args:
            max_repeated: Max times same command can repeat without progress
            help_loop_threshold: Ratio of help calls in window to trigger stuck
            help_loop_window: Window size for help loop detection
            no_progress_steps: Steps without new IDs before triggering stuck
            max_same_timeout: Max times same command can timeout
            max_same_error: Max times same error pattern can occur
        """
        self.max_repeated = max_repeated
        self.help_loop_threshold = help_loop_threshold
        self.help_loop_window = help_loop_window
        self.no_progress_steps = no_progress_steps
        self.max_same_timeout = max_same_timeout
        self.max_same_error = max_same_error

        # State tracking
        self.command_counts: Dict[str, int] = {}
        self.timeout_counts: Dict[str, int] = {}
        self.error_counts: Dict[str, int] = {}
        self.recent_steps: List[Dict[str, Any]] = []
        self.seen_ids: Set[str] = set()
        self.steps_since_progress = 0

    def normalize_command(self, command: str) -> str:
        """Normalize a command for comparison.

        - Strip multiple spaces
        - Remove env var prefixes (FOO=bar cmd -> cmd)
        - Normalize --help/-h variants
        """
        # Remove env var assignments
        tokens = []
        for token in command.strip().split():
            if '=' not in token:
                tokens.append(token)

        normalized = ' '.join(tokens)

        # Normalize --help/-h
        normalized = normalized.replace(' -h ', ' --help ')
        normalized = normalized.replace(' -h\n', ' --help\n')
        if normalized.endswith(' -h'):
            normalized = normalized[:-3] + ' --help'

        # Normalize multiple spaces
        normalized = ' '.join(normalized.split())

        return normalized

    def extract_ids(self, text: str) -> Set[str]:
        """Extract progress marker IDs from text."""
        ids = set()
        for pattern in self.ID_PATTERNS:
            matches = re.findall(pattern, text)
            ids.update(matches)
        return ids

    def normalize_error(self, stderr: str, exit_code: int) -> str:
        """Normalize error for pattern matching."""
        # Key patterns
        if 'unknown command' in stderr.lower():
            return 'unknown_command'
        if 'invalid' in stderr.lower() and 'argument' in stderr.lower():
            return 'invalid_argument'
        if 'not found' in stderr.lower():
            return 'not_found'
        if 'permission denied' in stderr.lower():
            return 'permission_denied'
        if exit_code == 127:
            return 'command_not_found'
        if exit_code == 2:
            return 'usage_error'
        if exit_code == 1:
            return 'generic_error'

        return f'exit_{exit_code}'

    def update(self, step_event: Dict[str, Any]) -> Optional[str]:
        """Update stuck detector with new step event.

        Returns:
            Stuck reason if stuck, else None
        """
        command = step_event.get('command', '')
        normalized_cmd = self.normalize_command(command)
        stdout = step_event.get('stdout', '')
        stderr = step_event.get('stderr', '')
        exit_code = step_event.get('exit_code', 0)
        timeout = step_event.get('timeout', False)
        rejected = step_event.get('rejected', False)

        # Track recent steps
        self.recent_steps.append(step_event)
        if len(self.recent_steps) > self.help_loop_window:
            self.recent_steps.pop(0)

        # Check 1: Repeated command
        if normalized_cmd:
            self.command_counts[normalized_cmd] = self.command_counts.get(normalized_cmd, 0) + 1
            if self.command_counts[normalized_cmd] >= self.max_repeated:
                # Check if there was progress (new IDs)
                new_ids = self.extract_ids(stdout + stderr)
                if not new_ids:
                    return f'repeated_command_{self.command_counts[normalized_cmd]}_times: {normalized_cmd}'

        # Check 2: Help loop
        if len(self.recent_steps) >= self.help_loop_window:
            help_count = sum(
                1 for s in self.recent_steps
                if '--help' in s.get('command', '') or '-h ' in s.get('command', '')
            )
            help_ratio = help_count / len(self.recent_steps)
            if help_ratio >= self.help_loop_threshold:
                return f'help_loop: {help_count}/{len(self.recent_steps)} steps are help calls'

        # Check 3: Repeated timeout
        if timeout:
            self.timeout_counts[normalized_cmd] = self.timeout_counts.get(normalized_cmd, 0) + 1
            if self.timeout_counts[normalized_cmd] >= self.max_same_timeout:
                return f'repeated_timeout_{self.timeout_counts[normalized_cmd]}_times: {normalized_cmd}'

        # Check 4: Repeated error
        if exit_code != 0 or rejected:
            error_sig = self.normalize_error(stderr, exit_code)
            self.error_counts[error_sig] = self.error_counts.get(error_sig, 0) + 1
            if self.error_counts[error_sig] >= self.max_same_error:
                return f'repeated_error_{self.error_counts[error_sig]}_times: {error_sig}'

        # Check 5: No progress (no new IDs)
        new_ids = self.extract_ids(stdout + stderr)
        if new_ids:
            # Progress detected
            self.seen_ids.update(new_ids)
            self.steps_since_progress = 0
        else:
            self.steps_since_progress += 1
            if self.steps_since_progress >= self.no_progress_steps:
                return f'no_progress_for_{self.steps_since_progress}_steps'

        return None

    def summary(self) -> Dict[str, Any]:
        """Return summary of stuck detector state for reporting."""
        return {
            'total_commands_seen': sum(self.command_counts.values()),
            'unique_commands': len(self.command_counts),
            'most_repeated_command': max(
                self.command_counts.items(),
                key=lambda x: x[1],
                default=('none', 0)
            ),
            'total_timeouts': sum(self.timeout_counts.values()),
            'total_errors': sum(self.error_counts.values()),
            'unique_ids_seen': len(self.seen_ids),
            'steps_since_last_progress': self.steps_since_progress,
            'recent_help_ratio': (
                sum(1 for s in self.recent_steps if '--help' in s.get('command', ''))
                / len(self.recent_steps)
                if self.recent_steps else 0.0
            )
        }

"""Tests for discuss router and context detection."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from maestro.commands.discuss import _detect_discuss_context, DiscussContext
from maestro.ai import ContractType


class TestDiscussRouter:
    """Tests for the discuss router context detection."""

    def test_detect_context_explicit_task_flag(self):
        """Test router detects context from --task flag."""
        args = Mock()
        args.task_id = "task-123"
        args.phase_id = None
        args.track_id = None
        args.context = None

        context = _detect_discuss_context(args)

        assert context.kind == "task"
        assert context.ref == "task-123"
        assert "Explicit --task flag" in context.reason
        assert context.contract_type == ContractType.TASK

    def test_detect_context_explicit_phase_flag(self):
        """Test router detects context from --phase flag."""
        args = Mock()
        args.task_id = None
        args.phase_id = "phase-456"
        args.track_id = None
        args.context = None

        context = _detect_discuss_context(args)

        assert context.kind == "phase"
        assert context.ref == "phase-456"
        assert "Explicit --phase flag" in context.reason
        assert context.contract_type == ContractType.PHASE

    def test_detect_context_explicit_track_flag(self):
        """Test router detects context from --track flag."""
        args = Mock()
        args.task_id = None
        args.phase_id = None
        args.track_id = "track-789"
        args.context = None

        context = _detect_discuss_context(args)

        assert context.kind == "track"
        assert context.ref == "track-789"
        assert "Explicit --track flag" in context.reason
        assert context.contract_type == ContractType.TRACK

    def test_detect_context_explicit_context_flag(self):
        """Test router detects context from --context flag."""
        args = Mock()
        args.task_id = None
        args.phase_id = None
        args.track_id = None
        args.context = "repo"

        context = _detect_discuss_context(args)

        assert context.kind == "repo"
        assert context.ref is None
        assert "Explicit --context flag" in context.reason
        assert context.contract_type == ContractType.GLOBAL

    def test_detect_context_fallback_to_global(self):
        """Test router falls back to global context when no hints."""
        args = Mock()
        args.task_id = None
        args.phase_id = None
        args.track_id = None
        args.context = None
        args._wsession = None

        context = _detect_discuss_context(args)

        assert context.kind == "global"
        assert context.ref is None
        assert "No explicit context or active work session" in context.reason
        assert context.contract_type == ContractType.GLOBAL

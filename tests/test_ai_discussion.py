"""Tests for AI discussion context builders and mode selection."""

from pathlib import Path

import pytest

from maestro.ai.actions import extract_json_actions
from maestro.ai.discussion import (
    DiscussionMode,
    build_phase_context,
    build_task_context,
    build_track_context,
)
from maestro.commands.discuss import choose_mode


def _write_docs(root: Path) -> None:
    docs_dir = root / "docs"
    phases_dir = docs_dir / "phases"
    docs_dir.mkdir()
    phases_dir.mkdir()

    todo_content = "\n".join(
        [
            "## Track: Sample Track",
            '"track_id": "sample"',
            '"priority": 1',
            '"status": "planned"',
            "",
            "### Phase CLI1: Sample Phase",
            '"phase_id": "sample-1"',
            '"status": "planned"',
            '"completion": 0',
            "",
            "- [ ] [Phase CLI1: Sample Phase](phases/sample-1.md) 📋 **[Planned]**",
            "",
        ]
    )
    (docs_dir / "todo.md").write_text(f"{todo_content}\n", encoding="utf-8")

    phase_content = "\n".join(
        [
            "# Phase CLI1: Sample Phase 📋 **[Planned]**",
            "",
            '"phase_id": "sample-1"',
            '"track_id": "sample"',
            '"status": "planned"',
            '"completion": 0',
            "",
            "## Tasks",
            "",
            "### Task 1.1: First Task",
            '"task_id": "sample-1-1"',
            '"priority": "P0"',
            "",
        ]
    )
    (phases_dir / "sample-1.md").write_text(f"{phase_content}\n", encoding="utf-8")


def test_extract_json_actions_filters_blocks() -> None:
    text = """
Some text
```json
{"actions": [{"type": "track.add", "data": {"name": "Track"}}]}
```
```json
{"not_actions": []}
```
```json
{"actions": [{"type": "phase.add", "data": {"track_id": "t", "name": "Phase"}}]}
```
```json
{invalid json
```
"""
    actions = extract_json_actions(text)
    assert len(actions) == 2
    assert actions[0]["type"] == "track.add"
    assert actions[1]["type"] == "phase.add"


def test_build_track_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_docs(tmp_path)
    monkeypatch.chdir(tmp_path)

    context = build_track_context("sample")
    assert context.context_type == "track"
    assert context.context_id == "sample"
    assert "track.add" in context.allowed_actions

    general = build_track_context(None)
    assert general.context_type == "general"
    assert general.context_id is None
    assert "track.add" in general.allowed_actions


def test_build_phase_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_docs(tmp_path)
    monkeypatch.chdir(tmp_path)

    context = build_phase_context("sample-1")
    assert context.context_type == "phase"
    assert context.context_id == "sample-1"
    assert "task.add" in context.allowed_actions
    assert "track.add" not in context.allowed_actions


def test_build_task_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_docs(tmp_path)
    monkeypatch.chdir(tmp_path)

    context = build_task_context("sample-1-1")
    assert context.context_type == "task"
    assert context.context_id == "sample-1-1"
    assert "task.complete" in context.allowed_actions
    assert "task.add" not in context.allowed_actions


def test_choose_mode_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    config_content = "\n".join(
        [
            "## User Preferences",
            '"discussion_mode": "terminal"',
            "",
        ]
    )
    (docs_dir / "config.md").write_text(f"{config_content}\n", encoding="utf-8")

    assert choose_mode("editor") == DiscussionMode.EDITOR
    assert choose_mode(None) == DiscussionMode.TERMINAL

    (docs_dir / "config.md").unlink()
    monkeypatch.setenv("EDITOR", "/usr/bin/vi")
    assert choose_mode(None) == DiscussionMode.EDITOR

    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.delenv("VISUAL", raising=False)
    assert choose_mode(None) == DiscussionMode.TERMINAL

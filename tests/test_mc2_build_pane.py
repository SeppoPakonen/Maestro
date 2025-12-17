"""
MC2 build pane behavior tests.
"""
import curses

from maestro.tui_mc2.app import AppContext
import maestro.tui_mc2.panes.build as build_module
from maestro.ui_facade.build import BuildTargetInfo


class DummyWindow:
    def __init__(self):
        self.added_text = []

    def erase(self):
        return None

    def getmaxyx(self):
        return (16, 100)

    def bkgd(self, *_args, **_kwargs):
        return None

    def addstr(self, _y, _x, text, *_args, **_kwargs):
        self.added_text.append(text)

    def noutrefresh(self):
        return None


class DummyConfirmModal:
    def __init__(self, *_args, **_kwargs):
        pass

    def show(self):
        return False


class DummyInputModal:
    def __init__(self, *_args, **_kwargs):
        pass

    def show(self):
        return None


def _make_target(target_id: str, name: str) -> BuildTargetInfo:
    return BuildTargetInfo(
        id=target_id,
        name=name,
        path=f"/tmp/{target_id}.json",
        status="ok",
        last_build_time=None,
        dependencies=[],
        description="Sample build target",
        categories=["ci"],
        pipeline={"steps": ["configure", "build"]},
        patterns={},
        environment={},
        why="",
        created_at="2023-11-01T00:00:00Z",
    )


def test_build_pane_empty_render(monkeypatch):
    context = AppContext()
    context.active_view = "build"
    context.active_session_id = "session-1"

    monkeypatch.setattr(build_module, "list_build_targets", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(build_module, "get_active_build_target", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(build_module.curses, "has_colors", lambda: False)

    pane = build_module.BuildPane(position="left", context=context)
    window = DummyWindow()
    pane.set_window(window)
    pane.render()

    assert any("No build targets" in text for text in window.added_text)


def test_build_list_selection_updates_details(monkeypatch):
    context = AppContext()
    context.active_view = "build"
    context.active_session_id = "session-1"

    targets = [
        _make_target("target-1", "Alpha"),
        _make_target("target-2", "Beta"),
    ]

    monkeypatch.setattr(build_module, "list_build_targets", lambda *_args, **_kwargs: targets)
    monkeypatch.setattr(build_module, "get_active_build_target", lambda *_args, **_kwargs: targets[0])
    monkeypatch.setattr(build_module, "get_diagnostics", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(build_module, "list_diagnostics_sources", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(build_module.curses, "has_colors", lambda: False)

    left = build_module.BuildPane(position="left", context=context)
    left.set_window(DummyWindow())
    left.move_down()

    assert context.selected_build_target_id == "target-2"

    right = build_module.BuildPane(position="right", context=context)
    right.set_window(DummyWindow())
    right.render()

    assert any("target-2" in text for text in right.window.added_text)


def test_build_set_active_cancel(monkeypatch):
    context = AppContext()
    context.active_view = "build"
    context.active_session_id = "session-1"
    context.modal_parent = DummyWindow()

    targets = [_make_target("target-1", "Alpha")]
    calls = {"set_active": 0}

    def fake_set_active(*_args, **_kwargs):
        calls["set_active"] += 1
        return True

    monkeypatch.setattr(build_module, "ConfirmModal", DummyConfirmModal)
    monkeypatch.setattr(build_module, "list_build_targets", lambda *_args, **_kwargs: targets)
    monkeypatch.setattr(build_module, "get_active_build_target", lambda *_args, **_kwargs: targets[0])
    monkeypatch.setattr(build_module, "set_active_build_target", fake_set_active)

    pane = build_module.BuildPane(position="left", context=context)
    pane.handle_set_active()

    assert calls["set_active"] == 0
    assert "cancel" in context.status_message.lower()


def test_build_fix_loop_cancel(monkeypatch):
    context = AppContext()
    context.active_view = "build"
    context.active_session_id = "session-1"
    context.modal_parent = DummyWindow()

    targets = [_make_target("target-1", "Alpha")]

    monkeypatch.setattr(build_module, "InputModal", DummyInputModal)
    monkeypatch.setattr(build_module, "list_build_targets", lambda *_args, **_kwargs: targets)
    monkeypatch.setattr(build_module, "get_active_build_target", lambda *_args, **_kwargs: targets[0])

    pane = build_module.BuildPane(position="left", context=context)
    pane.handle_fix_loop()

    assert "cancel" in context.status_message.lower()


def test_build_stop_sets_status():
    context = AppContext()
    context.active_view = "build"
    context.active_session_id = "session-1"

    pane = build_module.BuildPane(position="left", context=context)
    pane._running_mode = "build"

    pane.handle_stop()

    assert "stop requested" in context.status_message.lower()

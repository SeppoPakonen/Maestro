"""
MC2 plans pane behavior tests.
"""
import curses

from maestro.tui_mc2.app import AppContext, MC2App
import maestro.tui_mc2.panes.plans as plans_module
from maestro.ui_facade.phases import PhaseTreeNode


class DummyWindow:
    def __init__(self):
        self.added_text = []

    def erase(self):
        return None

    def getmaxyx(self):
        return (12, 80)

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


class DummyMenubar:
    def __init__(self):
        self.active = False

    def is_active(self):
        return self.active

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False


class DummyPane:
    def set_focused(self, _focused: bool):
        return None


def test_plans_pane_empty_render(monkeypatch):
    context = AppContext()
    context.active_view = "plans"
    context.active_session_id = "session-1"

    def no_plans(_session_id):
        raise ValueError("No plans found in session")

    monkeypatch.setattr(plans_module, "get_plan_tree", no_plans)
    monkeypatch.setattr(plans_module, "list_tasks", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(plans_module, "get_active_plan", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(plans_module.curses, "has_colors", lambda: False)

    pane = plans_module.PlansPane(position="left", context=context)
    window = DummyWindow()
    pane.set_window(window)
    pane.render()

    assert any("No plans" in text for text in window.added_text)


def test_plans_set_active_cancel(monkeypatch):
    context = AppContext()
    context.active_view = "plans"
    context.active_session_id = "session-1"
    context.modal_parent = DummyWindow()

    root = PhaseTreeNode(
        phase_id="plan-1234567890",
        label="Root Plan",
        status="inactive",
        created_at="t1",
        parent_phase_id=None,
        children=[],
        subtasks=[],
    )

    calls = {"set_active": 0}

    def fake_set_active(_session_id, _plan_id):
        calls["set_active"] += 1

    monkeypatch.setattr(plans_module, "ConfirmModal", DummyConfirmModal)
    monkeypatch.setattr(plans_module, "get_plan_tree", lambda _sid: root)
    monkeypatch.setattr(plans_module, "list_tasks", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(plans_module, "get_active_plan", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(plans_module, "set_active_plan", fake_set_active)

    pane = plans_module.PlansPane(position="left", context=context)
    pane.handle_set_active()

    assert calls["set_active"] == 0
    assert "cancel" in context.status_message.lower()


def test_plans_kill_cancel(monkeypatch):
    context = AppContext()
    context.active_view = "plans"
    context.active_session_id = "session-1"
    context.modal_parent = DummyWindow()

    root = PhaseTreeNode(
        phase_id="plan-1234567890",
        label="Root Plan",
        status="inactive",
        created_at="t1",
        parent_phase_id=None,
        children=[],
        subtasks=[],
    )

    calls = {"kill": 0}

    def fake_kill(_session_id, _plan_id):
        calls["kill"] += 1

    monkeypatch.setattr(plans_module, "ConfirmModal", DummyConfirmModal)
    monkeypatch.setattr(plans_module, "get_plan_tree", lambda _sid: root)
    monkeypatch.setattr(plans_module, "list_tasks", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(plans_module, "get_active_plan", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(plans_module, "kill_plan", fake_kill)

    pane = plans_module.PlansPane(position="left", context=context)
    pane.handle_kill()

    assert calls["kill"] == 0
    assert "cancel" in context.status_message.lower()


def test_plans_menu_toggle_focus():
    app = MC2App(smoke_mode=True)
    app.left_pane = DummyPane()
    app.right_pane = DummyPane()
    app.menubar = DummyMenubar()

    assert app.context.focus_pane == "left"
    assert app._handle_key(curses.KEY_F9) is True
    assert app.context.focus_pane == "left"
    assert app.menubar.is_active() is True
    assert app._handle_key(curses.KEY_F9) is True
    assert app.context.focus_pane == "left"
    assert app.menubar.is_active() is False

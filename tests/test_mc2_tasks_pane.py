"""
MC2 tasks pane behavior tests.
"""
import curses

from maestro.tui_mc2.app import AppContext, MC2App
import maestro.tui_mc2.panes.tasks as tasks_module
from maestro.ui_facade.tasks import TaskInfo


class DummyWindow:
    def __init__(self):
        self.added_text = []

    def erase(self):
        return None

    def getmaxyx(self):
        return (14, 80)

    def bkgd(self, *_args, **_kwargs):
        return None

    def addstr(self, _y, _x, text, *_args, **_kwargs):
        self.added_text.append(text)

    def noutrefresh(self):
        return None


class DummyPlan:
    def __init__(self, plan_id: str):
        self.plan_id = plan_id


class DummyInputModal:
    def __init__(self, *_args, **_kwargs):
        pass

    def show(self):
        return None


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


def test_tasks_pane_empty_render(monkeypatch):
    context = AppContext()
    context.active_view = "tasks"
    context.active_session_id = "session-1"

    monkeypatch.setattr(tasks_module, "get_active_plan", lambda _sid: DummyPlan("plan-1"))
    monkeypatch.setattr(tasks_module, "list_tasks", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(tasks_module.curses, "has_colors", lambda: False)

    pane = tasks_module.TasksPane(position="left", context=context)
    window = DummyWindow()
    pane.set_window(window)
    pane.render()

    assert any("No tasks" in text for text in window.added_text)


def test_tasks_detail_render(monkeypatch):
    context = AppContext()
    context.active_view = "tasks"
    context.active_session_id = "session-1"
    context.selected_task_id = "task-1"

    tasks = [
        TaskInfo(
            id="task-1",
            title="First task",
            description="Desc",
            status="pending",
            planner_model="planner",
            worker_model="worker",
            summary_file="/tmp/task-1.summary.txt",
            categories=[],
            plan_id="plan-1",
        )
    ]

    class DummySession:
        status = "new"

    monkeypatch.setattr(tasks_module, "get_active_plan", lambda _sid: DummyPlan("plan-1"))
    monkeypatch.setattr(tasks_module, "list_tasks", lambda *_args, **_kwargs: tasks)
    monkeypatch.setattr(tasks_module, "get_session_details", lambda _sid: DummySession())
    monkeypatch.setattr(tasks_module.curses, "has_colors", lambda: False)

    pane = tasks_module.TasksPane(position="right", context=context)
    window = DummyWindow()
    pane.set_window(window)
    pane.render()

    assert any("Task ID" in text for text in window.added_text)
    assert any("task-1" in text for text in window.added_text)


def test_tasks_run_limit_cancel(monkeypatch):
    context = AppContext()
    context.active_view = "tasks"
    context.active_session_id = "session-1"
    context.modal_parent = DummyWindow()

    calls = {"run": 0}

    def fake_run(*_args, **_kwargs):
        calls["run"] += 1
        return True

    monkeypatch.setattr(tasks_module, "InputModal", DummyInputModal)
    monkeypatch.setattr(tasks_module, "get_active_plan", lambda _sid: DummyPlan("plan-1"))
    monkeypatch.setattr(tasks_module, "list_tasks", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(tasks_module, "run_tasks", fake_run)
    monkeypatch.setattr(tasks_module, "resume_tasks", fake_run)

    pane = tasks_module.TasksPane(position="left", context=context)
    pane.handle_run_with_limit()

    assert calls["run"] == 0
    assert "cancel" in context.status_message.lower()


def test_tasks_stop_sets_status(monkeypatch):
    context = AppContext()
    context.active_view = "tasks"
    context.active_session_id = "session-1"

    monkeypatch.setattr(tasks_module, "stop_tasks", lambda: True)
    monkeypatch.setattr(tasks_module, "get_current_execution_state", lambda: {"current_task_id": "task-1"})

    pane = tasks_module.TasksPane(position="left", context=context)
    pane.handle_stop()

    assert "stop requested" in context.status_message.lower()


def test_tasks_menu_toggle_focus():
    app = MC2App(smoke_mode=True)
    app.context.active_view = "tasks"
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

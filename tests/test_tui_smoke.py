"""
MC2 smoke and input behavior tests.
"""
import curses
import os

import pytest

from maestro.tui_mc2.app import MC2App


class DummyMenubar:
    def __init__(self):
        self.active = False

    def is_active(self):
        return self.active

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False

    def handle_key(self, key):
        return False

    def render(self):
        return None


class DummyPane:
    def __init__(self):
        self.focused = False
        self.enter_count = 0

    def set_focused(self, focused: bool):
        self.focused = focused

    def handle_enter(self):
        self.enter_count += 1

    def handle_set_active(self):
        self.enter_count += 1

    def handle_filter_backspace(self):
        return False

    def handle_filter_char(self, _ch):
        return False

    def clear_filter(self):
        return False

    def move_up(self):
        return None

    def move_down(self):
        return None

    def page_up(self):
        return None

    def page_down(self):
        return None

    def move_home(self):
        return None

    def move_end(self):
        return None

    def refresh_data(self):
        return None

    def render(self):
        return None


class DummyStatusLine:
    def set_debug_info(self, enabled: bool, info: str):
        return None

    def render(self):
        return None

    def time_until_expire(self, now):
        return None

    def maybe_expire(self, now):
        return False


class FakeScreen:
    def __init__(self):
        self.keypad_calls = []
        self.timeout_calls = []

    def keypad(self, flag: bool):
        self.keypad_calls.append(flag)

    def nodelay(self, flag: bool):
        return None

    def timeout(self, ms: int):
        self.timeout_calls.append(ms)

    def getch(self):
        return -1


class FakeCurses:
    KEY_RESIZE = -999

    def __init__(self, screen_holder, calls):
        self._screen_holder = screen_holder
        self._calls = calls

    def initscr(self):
        screen = FakeScreen()
        self._screen_holder["screen"] = screen
        return screen

    def noecho(self):
        self._calls["noecho"] += 1

    def cbreak(self):
        self._calls["cbreak"] += 1

    def nocbreak(self):
        self._calls["nocbreak"] += 1

    def echo(self):
        self._calls["echo"] += 1

    def endwin(self):
        self._calls["endwin"] += 1

    def curs_set(self, _):
        return None

    def has_colors(self):
        return False

    def start_color(self):
        return None

    def init_pair(self, *_args, **_kwargs):
        return None

    def resizeterm(self, *_args, **_kwargs):
        return None


class FaultyPane(DummyPane):
    def render(self):
        if os.getenv("MAESTRO_MC2_FAULT_INJECT"):
            raise RuntimeError("Injected pane render failure")
        return None


def test_mc2_input_sequence():
    app = MC2App(smoke_mode=True)
    app.left_pane = DummyPane()
    app.right_pane = DummyPane()
    app.menubar = DummyMenubar()

    assert app.context.focus_pane == "left"
    assert app._handle_key(ord("\t")) is True
    assert app.context.focus_pane == "right"
    assert app.left_pane.focused is False
    assert app.right_pane.focused is True

    assert app.menubar.is_active() is False
    assert app._handle_key(curses.KEY_F9) is True
    assert app.context.focus_pane == "right"
    assert app.menubar.is_active() is True
    assert app._handle_key(curses.KEY_F9) is True
    assert app.context.focus_pane == "right"
    assert app.menubar.is_active() is False
    assert app._handle_key(curses.KEY_F9) is True
    assert app.context.focus_pane == "right"
    assert app.menubar.is_active() is True
    assert app._handle_key(27) is True
    assert app.context.focus_pane == "right"
    assert app.menubar.is_active() is False

    app.context.focus_pane = "left"
    assert app._handle_key(ord("\n")) is True
    assert app.left_pane.enter_count == 1
    app.context.focus_pane = "right"
    assert app._handle_key(ord("\n")) is True
    assert app.right_pane.enter_count == 1


def test_mc2_teardown_on_render_exception(monkeypatch):
    import maestro.tui_mc2.app as app_module

    calls = {"noecho": 0, "cbreak": 0, "nocbreak": 0, "echo": 0, "endwin": 0}
    screen_holder = {}

    fake_curses = FakeCurses(screen_holder, calls)
    monkeypatch.setattr(app_module, "curses", fake_curses)

    def fake_setup(self, stdscr):
        self.stdscr = stdscr
        self.menubar = DummyMenubar()
        self.status_line = DummyStatusLine()
        self.left_pane = FaultyPane()
        self.right_pane = DummyPane()
        self._mark_all_dirty()

    monkeypatch.setattr(app_module.MC2App, "_setup_ui", fake_setup)
    monkeypatch.setenv("MAESTRO_MC2_FAULT_INJECT", "pane_render")
    monkeypatch.setenv("MAESTRO_MC2_SMOKE_USE_CURSES", "1")

    app = app_module.MC2App(smoke_mode=True, smoke_seconds=0.01)
    with pytest.raises(RuntimeError):
        app.run()

    screen = screen_holder.get("screen")
    assert screen is not None
    assert screen.keypad_calls[0] is True
    assert screen.keypad_calls[-1] is False
    assert calls["nocbreak"] == 1
    assert calls["echo"] == 1
    assert calls["endwin"] == 1
    assert app._teardown_called is True


def test_sessions_filter_and_clear(monkeypatch):
    from maestro.tui_mc2.app import AppContext
    import maestro.tui_mc2.panes.sessions as sessions_module
    from maestro.ui_facade.sessions import SessionInfo

    sessions = [
        SessionInfo(id="alpha-1", created_at="t1", updated_at="t1", root_task="Alpha", status="new"),
        SessionInfo(id="beta-1", created_at="t2", updated_at="t2", root_task="Beta", status="new"),
        SessionInfo(id="gamma-1", created_at="t3", updated_at="t3", root_task="Gamma", status="new"),
    ]

    monkeypatch.setattr(sessions_module, "list_sessions", lambda: sessions)
    monkeypatch.setattr(sessions_module, "get_active_session", lambda: None)

    context = AppContext()
    pane = sessions_module.SessionsPane(position="left", context=context)

    assert context.sessions_filter_total == 3
    assert pane.handle_filter_char("b") is True
    assert context.sessions_filter_text == "b"
    assert context.sessions_filter_visible == 1

    assert pane.clear_filter() is True
    assert context.sessions_filter_text == ""
    assert context.sessions_filter_visible == 3


def test_sessions_input_modal_cancel(monkeypatch):
    import maestro.tui_mc2.panes.sessions as sessions_module
    from maestro.tui_mc2.app import AppContext

    class DummyInputModal:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self):
            return None

    created = {"count": 0}

    def fake_create_session(_name):
        created["count"] += 1

    monkeypatch.setattr(sessions_module, "InputModal", DummyInputModal)
    monkeypatch.setattr(sessions_module, "create_session", fake_create_session)
    monkeypatch.setattr(sessions_module, "list_sessions", lambda: [])
    monkeypatch.setattr(sessions_module, "get_active_session", lambda: None)

    context = AppContext()
    context.modal_parent = FakeScreen()
    pane = sessions_module.SessionsPane(position="left", context=context)

    pane.handle_new()
    assert created["count"] == 0
    assert "cancelled" in context.status_message.lower()


def test_sessions_delete_modal_cancel(monkeypatch):
    import maestro.tui_mc2.panes.sessions as sessions_module
    from maestro.tui_mc2.app import AppContext
    from maestro.ui_facade.sessions import SessionInfo

    class DummyConfirmModal:
        def __init__(self, *_args, **_kwargs):
            pass

        def show(self):
            return False

    sessions = [
        SessionInfo(id="alpha-1", created_at="t1", updated_at="t1", root_task="Alpha", status="new"),
    ]

    removed = {"count": 0}

    def fake_remove_session(_session_id):
        removed["count"] += 1

    monkeypatch.setattr(sessions_module, "ConfirmModal", DummyConfirmModal)
    monkeypatch.setattr(sessions_module, "remove_session", fake_remove_session)
    monkeypatch.setattr(sessions_module, "list_sessions", lambda: sessions)
    monkeypatch.setattr(sessions_module, "get_active_session", lambda: None)

    context = AppContext()
    context.modal_parent = FakeScreen()
    pane = sessions_module.SessionsPane(position="left", context=context)

    pane.handle_delete()
    assert removed["count"] == 0
    assert "cancelled" in context.status_message.lower()

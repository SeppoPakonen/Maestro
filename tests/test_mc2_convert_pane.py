"""
MC2 convert pane behavior tests.
"""
import curses

from maestro.tui_mc2.app import AppContext, MC2App
import maestro.tui_mc2.panes.convert as convert_module
from maestro.ui_facade.convert import PipelineStatus, StageInfo
from maestro.ui_facade.semantic import SemanticSummary


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


def _pipeline_status(active_stage: str = "stage-one") -> PipelineStatus:
    return PipelineStatus(
        id="pipe-1",
        name="Pipe One",
        status="running",
        active_stage=active_stage,
        active_run_id=None,
        stages=[],
    )


def _stage(name: str, status: str) -> StageInfo:
    return StageInfo(
        name=name,
        status=status,
        icon="*",
        color="dim",
        start_time=None,
        end_time=None,
        artifacts=[],
        description=f"{name} stage",
        reason=None,
    )


def _semantic_summary() -> SemanticSummary:
    return SemanticSummary(
        total_findings=0,
        high_risk=0,
        medium_risk=0,
        low_risk=0,
        accepted=0,
        rejected=0,
        blocking=0,
        overall_health_score=1.0,
    )


def test_convert_pane_empty_render(monkeypatch):
    context = AppContext()
    context.active_view = "convert"

    monkeypatch.setattr(convert_module, "get_pipeline_status", lambda *_args, **_kwargs: PipelineStatus(id="", name="", status="idle"))
    monkeypatch.setattr(convert_module.curses, "has_colors", lambda: False)

    pane = convert_module.ConvertPane(position="left", context=context)
    window = DummyWindow()
    pane.set_window(window)
    pane.render()

    assert any("No conversion pipeline" in text for text in window.added_text)


def test_convert_selection_updates_details(monkeypatch):
    context = AppContext()
    context.active_view = "convert"

    stages = [_stage("stage-one", "running"), _stage("stage-two", "pending")]

    monkeypatch.setattr(convert_module, "get_pipeline_status", lambda *_args, **_kwargs: _pipeline_status())
    monkeypatch.setattr(convert_module, "list_stages", lambda *_args, **_kwargs: stages)
    monkeypatch.setattr(convert_module, "get_checkpoints", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(convert_module, "list_run_history", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(convert_module, "get_semantic_summary", lambda *_args, **_kwargs: _semantic_summary())
    monkeypatch.setattr(convert_module.curses, "has_colors", lambda: False)

    left = convert_module.ConvertPane(position="left", context=context)
    left.set_window(DummyWindow())
    left.move_down()

    assert context.selected_convert_stage == "stage-two"

    right = convert_module.ConvertPane(position="right", context=context)
    right.set_window(DummyWindow())
    right.render()

    assert any("stage-two" in text for text in right.window.added_text)


def test_convert_filter_edit_clear(monkeypatch):
    context = AppContext()
    context.active_view = "convert"

    stages = [_stage("alpha", "running"), _stage("beta", "pending")]

    monkeypatch.setattr(convert_module, "get_pipeline_status", lambda *_args, **_kwargs: _pipeline_status())
    monkeypatch.setattr(convert_module, "list_stages", lambda *_args, **_kwargs: stages)
    monkeypatch.setattr(convert_module, "get_checkpoints", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(convert_module, "list_run_history", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(convert_module, "get_semantic_summary", lambda *_args, **_kwargs: _semantic_summary())

    pane = convert_module.ConvertPane(position="left", context=context)
    pane.handle_filter_char("b")

    assert len(pane.filtered_stages) == 1
    assert pane.filtered_stages[0].name == "beta"

    pane.clear_filter()

    assert len(pane.filtered_stages) == 2


def test_convert_nav_keys_do_not_crash(monkeypatch):
    app = MC2App()
    app.context.active_view = "convert"
    app._set_view = lambda view: setattr(app.context, "active_view", view)

    assert app._handle_key(curses.KEY_F3)
    assert app._handle_key(curses.KEY_F4)

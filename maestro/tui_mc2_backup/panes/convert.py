"""
Convert pane for MC2 Curses TUI.
Read-only conversion pipeline dashboard (stages, checkpoints, evidence).
"""
from __future__ import annotations

import curses
import os
from dataclasses import dataclass
from typing import List, Optional

from maestro.tui_mc2.ui.modals import InputModal
from maestro.ui_facade.convert import (
    CheckpointInfo,
    PipelineStatus,
    RunHistory,
    StageInfo,
    get_checkpoints,
    get_pipeline_status,
    list_run_history,
    list_stages,
)
from maestro.ui_facade.semantic import get_semantic_summary, SemanticSummary


@dataclass
class ConvertStageRow:
    name: str
    status: str
    description: str
    reason: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    artifacts: List[str]


class ConvertPane:
    def __init__(self, position: str, context):
        self.position = position  # "left" or "right"
        self.context = context
        self.window = None
        self.is_focused = False
        self.pipeline_status: Optional[PipelineStatus] = None
        self.pipeline_id: Optional[str] = None
        self.active_stage: Optional[str] = None
        self.stages: List[ConvertStageRow] = []
        self.filtered_stages: List[ConvertStageRow] = []
        self.checkpoints: List[CheckpointInfo] = []
        self.run_history: List[RunHistory] = []
        self.semantic_summary: Optional[SemanticSummary] = None
        self.selected_index = 0
        self.scroll_offset = 0
        self.detail_scroll_offset = 0
        self.detail_scroll_max = 0
        self.filter_text = ""
        self.last_loaded_stage_name: Optional[str] = None

        self.refresh_data()

    def set_window(self, window):
        """Set the curses window for this pane."""
        self.window = window

    def set_focused(self, focused: bool):
        """Set focus state for this pane."""
        self.is_focused = focused

    def refresh_data(self):
        """Refresh conversion pipeline data."""
        self.pipeline_status = None
        self.pipeline_id = None
        self.active_stage = None
        self.stages = []
        self.filtered_stages = []
        self.checkpoints = []
        self.run_history = []
        self.semantic_summary = None

        try:
            self.pipeline_status = get_pipeline_status()
            if not self.pipeline_status.id:
                if self.position == "left":
                    self.context.selected_convert_stage = None
                    self._update_convert_status_text()
                return

            self.pipeline_id = self.pipeline_status.id
            self.active_stage = self.pipeline_status.active_stage
            stage_infos = list_stages(self.pipeline_id)
            self.stages = [self._to_row(stage) for stage in stage_infos]
            self.checkpoints = get_checkpoints(self.pipeline_id)
            self.run_history = list_run_history(self.pipeline_id)
            try:
                self.semantic_summary = get_semantic_summary(self.pipeline_id)
            except Exception:
                self.semantic_summary = None

            preserve_name = self.context.selected_convert_stage
            if preserve_name is None and self.stages and self.position == "left":
                preserve_name = self.stages[0].name
                self.context.selected_convert_stage = preserve_name

            self._apply_filter(preserve_name)

            if self.position == "right":
                self._sync_selected_index_from_context()
                self.last_loaded_stage_name = None
        except Exception as exc:
            self.context.status_message = f"Error loading convert pipeline: {str(exc)}"
            if self.position == "left":
                self.context.selected_convert_stage = None
                self._update_convert_status_text()

    def _to_row(self, stage: StageInfo) -> ConvertStageRow:
        return ConvertStageRow(
            name=stage.name,
            status=stage.status or "pending",
            description=stage.description or "",
            reason=stage.reason,
            start_time=stage.start_time,
            end_time=stage.end_time,
            artifacts=list(stage.artifacts or []),
        )

    def _apply_filter(self, preserve_selected_name: Optional[str] = None):
        filter_value = self.filter_text.lower()
        if filter_value:
            self.filtered_stages = [
                stage
                for stage in self.stages
                if filter_value in stage.name.lower()
                or filter_value in stage.status.lower()
                or filter_value in stage.description.lower()
                or filter_value in (stage.reason or "").lower()
            ]
        else:
            self.filtered_stages = list(self.stages)

        if preserve_selected_name:
            self._set_selected_by_name(preserve_selected_name)
        else:
            self.selected_index = 0
            self.scroll_offset = 0
            self._sync_selected_name()

        self._update_convert_status_text()

    def _get_selected_stage(self) -> Optional[ConvertStageRow]:
        if self.position == "right":
            stage_name = self.context.selected_convert_stage
            if not stage_name:
                return None
            for stage in self.stages:
                if stage.name == stage_name:
                    return stage
            return None
        if not self.filtered_stages:
            return None
        if self.selected_index < 0 or self.selected_index >= len(self.filtered_stages):
            return None
        return self.filtered_stages[self.selected_index]

    def _sync_selected_name(self):
        if self.position != "left":
            return
        selected = self._get_selected_stage()
        self.context.selected_convert_stage = selected.name if selected else None
        self._update_convert_status_text()

    def _sync_selected_index_from_context(self):
        if not self.filtered_stages:
            self.selected_index = 0
            return
        stage_name = self.context.selected_convert_stage
        if not stage_name:
            self.selected_index = 0
            return
        for idx, stage in enumerate(self.filtered_stages):
            if stage.name == stage_name:
                self.selected_index = idx
                break

    def _set_selected_by_name(self, stage_name: str):
        if not self.filtered_stages:
            self.selected_index = 0
            self.scroll_offset = 0
            self._sync_selected_name()
            return
        for idx, stage in enumerate(self.filtered_stages):
            if stage.name == stage_name:
                self.selected_index = idx
                self._ensure_visible()
                self._sync_selected_name()
                return
        self.selected_index = 0
        self.scroll_offset = 0
        self._sync_selected_name()

    def _ensure_visible(self):
        if not self.window:
            return
        height = max(1, self.window.getmaxyx()[0] - 2)
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + height:
            self.scroll_offset = self.selected_index - height + 1

    def _move_selection(self, delta: int):
        if self.position != "left" or not self.filtered_stages:
            return
        new_index = max(0, min(len(self.filtered_stages) - 1, self.selected_index + delta))
        if new_index != self.selected_index:
            self.selected_index = new_index
            self._ensure_visible()
            self._sync_selected_name()

    def move_up(self):
        if self.position == "right":
            self._scroll_details(-1)
            return
        self._move_selection(-1)

    def move_down(self):
        if self.position == "right":
            self._scroll_details(1)
            return
        self._move_selection(1)

    def page_up(self):
        if self.position == "right":
            self._scroll_page(-1)
            return
        if not self.window:
            return
        step = max(1, (self.window.getmaxyx()[0] - 2) // 2)
        self._move_selection(-step)

    def page_down(self):
        if self.position == "right":
            self._scroll_page(1)
            return
        if not self.window:
            return
        step = max(1, (self.window.getmaxyx()[0] - 2) // 2)
        self._move_selection(step)

    def move_home(self):
        if self.position == "left":
            self._move_selection(-len(self.filtered_stages))
        else:
            self._scroll_details(-self.detail_scroll_max)

    def move_end(self):
        if self.position == "left":
            self._move_selection(len(self.filtered_stages))
        else:
            self._scroll_details(self.detail_scroll_max)

    def handle_enter(self):
        self.context.status_message = "Convert view is read-only"

    def handle_filter_char(self, ch: str) -> bool:
        if not ch or not ch.isalnum():
            return False
        self.filter_text += ch
        self._apply_filter()
        return True

    def handle_filter_backspace(self) -> bool:
        if not self.filter_text:
            return False
        self.filter_text = self.filter_text[:-1]
        self._apply_filter()
        return True

    def clear_filter(self) -> bool:
        if not self.filter_text:
            return False
        self.filter_text = ""
        self._apply_filter()
        return True

    def handle_filter_input(self):
        parent = self.context.modal_parent or self.window
        if parent is None:
            self.context.status_message = "Unable to open modal"
            return
        input_modal = InputModal(parent, "Convert Filter", "Filter:", self.filter_text)
        new_value = input_modal.show()
        if new_value is None:
            self.context.status_message = "Filter unchanged"
            return
        self.filter_text = new_value.strip()
        self._apply_filter()
        self.context.status_message = "Filter updated"

    def _update_convert_status_text(self):
        if self.position != "left":
            return
        if not self.pipeline_status or not self.pipeline_status.id:
            self.context.convert_status_text = ""
            return
        pending_checkpoints = len([c for c in self.checkpoints if c.status == "pending"])
        blocked_stage = next((stage for stage in self.stages if stage.status == "blocked"), None)
        if blocked_stage:
            reason = (blocked_stage.reason or "reason not available").strip()
            if len(reason) > 60:
                reason = reason[:57] + "..."
            self.context.convert_status_text = (
                f"BLOCKED: {blocked_stage.name} - {reason} | checkpoints: {pending_checkpoints}"
            )
            return
        blocked = "yes" if self.pipeline_status.status == "blocked" else "no"
        active_stage = self.pipeline_status.active_stage or "None"
        self.context.convert_status_text = (
            f"Stage: {active_stage} | blocked: {blocked} | checkpoints: {pending_checkpoints}"
        )

    def _scroll_details(self, delta: int):
        if self.position != "right":
            return
        self.detail_scroll_offset = max(0, min(self.detail_scroll_offset + delta, self.detail_scroll_max))

    def _scroll_page(self, direction: int):
        if self.position != "right" or not self.window:
            return
        step = max(1, (self.window.getmaxyx()[0] - 2) // 2)
        self._scroll_details(direction * step)

    def render(self):
        if not self.window:
            return

        self.window.erase()
        height, width = self.window.getmaxyx()

        if self.is_focused and curses.has_colors():
            self.window.bkgd(' ', curses.color_pair(3))
        elif curses.has_colors():
            self.window.bkgd(' ', curses.color_pair(0))

        if self.position == "left":
            title = "Convert Stages"
        else:
            selected = self._get_selected_stage()
            title = f"Stage Details: {selected.name if selected else 'None'}"

        try:
            self.window.addstr(0, 1, title[: width - 3], curses.A_BOLD)
        except Exception:
            pass

        if self.position == "left":
            self._render_stage_list(height, width)
        else:
            self._render_stage_details(height, width)

        self.window.noutrefresh()

    def _render_stage_list(self, height: int, width: int):
        if not self.pipeline_status or not self.pipeline_status.id:
            try:
                self.window.addstr(2, 1, "No conversion pipeline found", curses.A_DIM)
            except Exception:
                pass
            return

        if not self.filtered_stages:
            message = "No stages found"
            if self.filter_text:
                message = "No stages match filter"
            try:
                self.window.addstr(2, 1, message, curses.A_DIM)
            except Exception:
                pass
            return

        display_count = height - 2
        start_idx = self.scroll_offset
        end_idx = min(start_idx + display_count - 1, len(self.filtered_stages))

        status_icons = {
            "pending": ".",
            "running": ">",
            "completed": "+",
            "ok": "+",
            "done": "+",
            "failed": "x",
            "blocked": "!",
            "skipped": "-",
        }

        for idx in range(start_idx, end_idx):
            stage = self.filtered_stages[idx]
            row = 1 + (idx - start_idx)

            is_selected = idx == self.selected_index
            status_icon = status_icons.get(stage.status, "?")
            current_marker = "*" if stage.name == self.active_stage else " "
            short_id = self._short_id(stage.name)
            display_text = f"{status_icon}{current_marker} {stage.name} {short_id}"
            if len(display_text) >= width - 2:
                display_text = display_text[: width - 5] + "..."

            try:
                attr = curses.A_REVERSE if is_selected and self.is_focused else 0
                if is_selected and self.is_focused and curses.has_colors():
                    attr = curses.color_pair(1) | curses.A_BOLD
                self.window.addstr(row, 1, display_text.ljust(width - 2), attr)
            except Exception:
                break

    def _render_stage_details(self, height: int, width: int):
        if not self.pipeline_status or not self.pipeline_status.id:
            try:
                self.window.addstr(2, 1, "No conversion pipeline found", curses.A_DIM)
            except Exception:
                pass
            return

        stage = self._get_selected_stage()
        if not stage:
            try:
                self.window.addstr(2, 1, "Select a stage in the left pane", curses.A_DIM)
            except Exception:
                pass
            return

        def _value(value: Optional[str]) -> str:
            if value is None or value == "":
                return "(not available)"
            return str(value)

        details: List[str] = []
        details.append(f"Stage Name: {_value(stage.name)}")
        details.append(f"Stage ID: {_value(stage.name)}")
        details.append(f"Status: {_value(stage.status)}")
        if stage.reason or stage.status == "blocked":
            details.append(f"Reason: {_value(stage.reason)}")
        if stage.description:
            details.append(f"Description: {_value(stage.description)}")
        details.append(f"Start: {_value(stage.start_time)}")
        details.append(f"End: {_value(stage.end_time)}")

        details.append("")
        details.append("Checkpoints:")
        stage_checkpoints = [c for c in self.checkpoints if c.stage == stage.name]
        pending = [c for c in stage_checkpoints if c.status == "pending"]
        details.append(f"  pending: {len(pending)} | total: {len(stage_checkpoints)}")
        if stage_checkpoints:
            for checkpoint in stage_checkpoints:
                action = "action: approve/reject/override" if checkpoint.status == "pending" else f"status: {checkpoint.status}"
                details.append(f"  {checkpoint.name} ({action})")
                if checkpoint.reason:
                    details.append(f"    reason: {checkpoint.reason}")
        else:
            details.append("  (none)")

        details.append("")
        details.append("Semantic Warnings:")
        if self.semantic_summary is None:
            details.append("  (not available)")
        else:
            details.append(
                f"  total: {self.semantic_summary.total_findings} | blocking: {self.semantic_summary.blocking}"
            )

        details.append("")
        details.append("Run Summary:")
        last_run = self.run_history[0] if self.run_history else None
        if last_run:
            details.append(f"  last run id: {_value(last_run.run_id)}")
            details.append(f"  started: {_value(last_run.started_at)}")
            details.append(f"  completed: {_value(last_run.completed_at)}")
            details.append(f"  status: {_value(last_run.status)}")
            details.append(f"  arbitration usage: {last_run.arbitration_usage}")
        else:
            details.append("  (not available)")

        details.append("")
        details.append("Evidence Paths:")
        pipeline_path = self._pipeline_file_path()
        details.append(f"  pipeline: {pipeline_path if pipeline_path and os.path.exists(pipeline_path) else '(not available)'}")
        semantic_path = self._semantic_file_path()
        details.append(f"  semantic: {semantic_path if semantic_path and os.path.exists(semantic_path) else '(not available)'}")
        if stage.artifacts:
            for artifact in stage.artifacts:
                details.append(f"  artifact: {artifact}")
        else:
            details.append("  artifacts: (not available)")

        content_height = height - 2
        self.detail_scroll_max = max(0, len(details) - content_height)
        if self.detail_scroll_offset > self.detail_scroll_max:
            self.detail_scroll_offset = self.detail_scroll_max

        start = self.detail_scroll_offset
        end = min(len(details), start + content_height)
        row = 1
        for idx in range(start, end):
            line = details[idx]
            try:
                self.window.addstr(row, 1, line[: width - 2], curses.A_NORMAL)
            except Exception:
                pass
            row += 1

    def _pipeline_file_path(self) -> Optional[str]:
        if not self.pipeline_id:
            return None
        return os.path.join("./.maestro/convert/pipelines", f"{self.pipeline_id}.json")

    def _semantic_file_path(self) -> Optional[str]:
        if not self.pipeline_id:
            return None
        return os.path.join("./.maestro/convert/semantic", f"{self.pipeline_id}_semantic_findings.json")

    def _short_id(self, value: str) -> str:
        return value[:8] + "..." if len(value) > 8 else value

"""
Build pane for MC2 Curses TUI.
Shows build target list in left pane and target details/diagnostics in right pane.
"""
from __future__ import annotations

import curses
import os
import queue
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from maestro.tui_mc2.ui.modals import ConfirmModal, InputModal
from maestro.ui_facade.build import (
    BuildStatus,
    BuildTargetInfo,
    DiagnosticInfo,
    get_active_build_target,
    get_build_status,
    get_diagnostics,
    list_build_targets,
    list_diagnostics_sources,
    run_build,
    run_fix_loop,
    set_active_build_target,
)


@dataclass
class BuildTargetRow:
    id: str
    name: str
    status: str
    path: str
    last_modified: Optional[str]
    last_build_time: Optional[str]
    description: str
    categories: List[str]
    pipeline: Dict[str, Any]
    patterns: Dict[str, Any]
    environment: Dict[str, Any]
    why: str
    dependencies: List[str]
    created_at: Optional[str]


class BuildPane:
    def __init__(self, position: str, context):
        self.position = position  # "left" or "right"
        self.context = context
        self.window = None
        self.is_focused = False
        self.targets: List[BuildTargetRow] = []
        self.filtered_targets: List[BuildTargetRow] = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.detail_scroll_offset = 0
        self.detail_scroll_max = 0
        self.filter_text = ""
        self.active_target_id: Optional[str] = None
        self.last_loaded_target_id: Optional[str] = None
        self.last_run_results: Dict[str, Dict[str, Any]] = {}
        self.last_artifact_hints: Dict[str, str] = {}
        self.last_status: Optional[BuildStatus] = None
        self.show_diagnostics_preview = False
        self.diagnostics_preview_limit = 5
        self.fix_loop_max_iterations: Optional[int] = None
        self.fix_loop_limit: Optional[int] = None
        self.fix_loop_iteration: int = 0
        self.fix_loop_signature: Optional[str] = None
        self._event_queue: "queue.Queue[dict]" = queue.Queue()
        self._runner_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running_mode: Optional[str] = None
        self._running_target_id: Optional[str] = None

        self.refresh_data()

    def set_window(self, window):
        """Set the curses window for this pane."""
        self.window = window

    def set_focused(self, focused: bool):
        """Set focus state for this pane."""
        self.is_focused = focused
        if focused and self.position == "right":
            self._load_target_details()

    def _get_session_id(self) -> Optional[str]:
        return self.context.active_session_id or self.context.selected_session_id

    def _format_mtime(self, path: Optional[str]) -> Optional[str]:
        if not path or not os.path.exists(path):
            return None
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return None
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

    def refresh_data(self):
        """Refresh build target data."""
        session_id = self._get_session_id()
        self.targets = []
        self.filtered_targets = []
        self.active_target_id = None

        if not session_id:
            if self.position == "left":
                self.context.selected_build_target_id = None
                self._update_build_status_text(None)
            return

        try:
            active = get_active_build_target(session_id)
            self.active_target_id = active.id if active else None
            self.context.active_build_target_id = self.active_target_id

            targets = list_build_targets(session_id)
            self.targets = [self._to_row(target) for target in targets]

            preserve_id = self.context.selected_build_target_id
            if preserve_id is None and self.targets and self.position == "left":
                preserve_id = self.targets[0].id
                self.context.selected_build_target_id = preserve_id

            self._apply_filter(preserve_id)

            if self.position == "right":
                self._sync_selected_index_from_context()
                self.last_loaded_target_id = None
                self._load_target_details()
        except Exception as exc:
            self.context.status_message = f"Error loading build targets: {str(exc)}"
            if self.position == "left":
                self.context.selected_build_target_id = None
                self._update_build_status_text(None)

    def _to_row(self, target: BuildTargetInfo) -> BuildTargetRow:
        return BuildTargetRow(
            id=target.id,
            name=target.name or "(not available)",
            status=getattr(target, "status", "unknown"),
            path=getattr(target, "path", ""),
            last_modified=self._format_mtime(getattr(target, "path", None)),
            last_build_time=getattr(target, "last_build_time", None),
            description=getattr(target, "description", "") or "",
            categories=list(getattr(target, "categories", []) or []),
            pipeline=dict(getattr(target, "pipeline", {}) or {}),
            patterns=dict(getattr(target, "patterns", {}) or {}),
            environment=dict(getattr(target, "environment", {}) or {}),
            why=getattr(target, "why", "") or "",
            dependencies=list(getattr(target, "dependencies", []) or []),
            created_at=getattr(target, "created_at", None),
        )

    def _apply_filter(self, preserve_selected_id: Optional[str] = None):
        filter_value = self.filter_text.lower()
        if filter_value:
            self.filtered_targets = [
                target
                for target in self.targets
                if filter_value in target.name.lower() or filter_value in target.id.lower()
            ]
        else:
            self.filtered_targets = list(self.targets)

        if preserve_selected_id:
            self._set_selected_by_id(preserve_selected_id)
        else:
            self.selected_index = 0
            self.scroll_offset = 0
            self._sync_selected_id()

    def _get_selected_target(self) -> Optional[BuildTargetRow]:
        if self.position == "right":
            target_id = self.context.selected_build_target_id
            if not target_id:
                return None
            for target in self.targets:
                if target.id == target_id:
                    return target
            return None
        if not self.filtered_targets:
            return None
        if self.selected_index < 0 or self.selected_index >= len(self.filtered_targets):
            return None
        return self.filtered_targets[self.selected_index]

    def _sync_selected_id(self):
        if self.position != "left":
            return
        selected = self._get_selected_target()
        self.context.selected_build_target_id = selected.id if selected else None
        self._update_build_status_text(selected)

    def _sync_selected_index_from_context(self):
        if not self.filtered_targets:
            self.selected_index = 0
            return
        target_id = self.context.selected_build_target_id
        if not target_id:
            self.selected_index = 0
            return
        for idx, target in enumerate(self.filtered_targets):
            if target.id == target_id:
                self.selected_index = idx
                break

    def _set_selected_by_id(self, target_id: str):
        if not self.filtered_targets:
            self.selected_index = 0
            self.scroll_offset = 0
            self._sync_selected_id()
            return
        for idx, target in enumerate(self.filtered_targets):
            if target.id == target_id:
                self.selected_index = idx
                self._ensure_visible()
                self._sync_selected_id()
                return
        self.selected_index = 0
        self.scroll_offset = 0
        self._sync_selected_id()

    def _ensure_visible(self):
        if not self.window:
            return
        height = max(1, self.window.getmaxyx()[0] - 2)
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + height:
            self.scroll_offset = self.selected_index - height + 1

    def _move_selection(self, delta: int):
        if self.position != "left" or not self.filtered_targets:
            return
        new_index = max(0, min(len(self.filtered_targets) - 1, self.selected_index + delta))
        if new_index != self.selected_index:
            self.selected_index = new_index
            self._ensure_visible()
            self._sync_selected_id()

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
            self._move_selection(-len(self.filtered_targets))
        else:
            self._scroll_details(-self.detail_scroll_max)

    def move_end(self):
        if self.position == "left":
            self._move_selection(len(self.filtered_targets))
        else:
            self._scroll_details(self.detail_scroll_max)

    def handle_enter(self):
        if self.position == "left":
            self.handle_set_active()
            return None
        self.show_diagnostics_preview = not self.show_diagnostics_preview
        if self.show_diagnostics_preview:
            self.context.status_message = "Diagnostics preview expanded"
        else:
            self.context.status_message = "Diagnostics preview collapsed"
        return None

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
        input_modal = InputModal(parent, "Build Filter", "Filter:", self.filter_text)
        new_value = input_modal.show()
        if new_value is None:
            self.context.status_message = "Filter unchanged"
            return
        self.filter_text = new_value.strip()
        self._apply_filter()
        self.context.status_message = "Filter updated"

    def handle_set_active(self):
        session_id = self._get_session_id()
        if not session_id:
            self.context.status_message = "No session selected"
            return
        target = self._get_selected_target()
        if not target:
            self.context.status_message = "No build target selected"
            return
        parent = self.context.modal_parent or self.window
        if parent is None:
            self.context.status_message = "Unable to open modal"
            return
        confirmation = ConfirmModal(
            parent,
            "Confirm Active Target",
            [
                "Set active build target?",
                "",
                f"{target.name} ({target.id[:8]}...)",
                "",
                "Press Enter to confirm, Esc to cancel",
            ],
        )
        if not confirmation.show():
            self.context.status_message = "Set active cancelled"
            return
        if set_active_build_target(session_id, target.id):
            self.active_target_id = target.id
            self.context.active_build_target_id = target.id
            self.context.status_message = "Active build target set"
            self.refresh_data()
            return
        self.context.status_message = "Failed to set active target"

    def handle_run(self):
        session_id = self._get_session_id()
        if not session_id:
            self.context.status_message = "No session selected"
            return
        if self._running_mode:
            self.context.status_message = "Build already running"
            return
        target = self._get_selected_target()
        if not target:
            self.context.status_message = "No build target selected"
            return
        self._start_run(mode="build", target_id=target.id)

    def handle_status(self):
        session_id = self._get_session_id()
        if not session_id:
            self.context.status_message = "No session selected"
            return
        target = self._get_selected_target()
        target_id = target.id if target else None
        try:
            status = get_build_status(session_id, target_id=target_id)
        except Exception as exc:
            self.context.status_message = f"Status error: {str(exc)}"
            return
        self.last_status = status
        error_text = f", errors: {status.error_count}" if status else ""
        state = status.state if status else "unknown"
        self.context.status_message = f"Build status: {state}{error_text}"
        self._update_build_status_text(target)

    def handle_fix_loop(self):
        session_id = self._get_session_id()
        if not session_id:
            self.context.status_message = "No session selected"
            return
        if self._running_mode:
            self.context.status_message = "Build already running"
            return
        target = self._get_selected_target()
        if not target:
            self.context.status_message = "No build target selected"
            return
        parent = self.context.modal_parent or self.window
        if parent is None:
            self.context.status_message = "Unable to open modal"
            return
        max_iterations = self._prompt_iterations(parent)
        if max_iterations is None:
            self.context.status_message = "Fix loop cancelled"
            return
        fix_limit = self._prompt_fix_limit(parent)
        if fix_limit is None:
            self.context.status_message = "Fix loop cancelled"
            return
        self.fix_loop_max_iterations = max_iterations
        self.fix_loop_limit = fix_limit
        self.fix_loop_iteration = 0
        self.fix_loop_signature = None
        self._start_run(mode="fix_loop", target_id=target.id)

    def _prompt_iterations(self, parent) -> Optional[int]:
        input_modal = InputModal(parent, "Fix Loop (Dangerous)", "Max iterations:", "5")
        value = input_modal.show()
        if value is None:
            return None
        value = value.strip()
        if not value.isdigit():
            self.context.status_message = "Invalid iteration count"
            return None
        count = int(value)
        if count <= 0:
            self.context.status_message = "Invalid iteration count"
            return None
        return count

    def _prompt_fix_limit(self, parent) -> Optional[int]:
        input_modal = InputModal(parent, "Fix Loop (Dangerous)", "Limit fixes per iteration:", "1")
        value = input_modal.show()
        if value is None:
            return None
        value = value.strip()
        if value == "":
            return 1
        if not value.isdigit():
            self.context.status_message = "Invalid fix limit"
            return None
        count = int(value)
        if count <= 0:
            self.context.status_message = "Invalid fix limit"
            return None
        return count

    def _start_run(self, mode: str, target_id: str):
        self._stop_event.clear()
        self._running_mode = mode
        self._running_target_id = target_id
        self.context.build_is_running = True
        if mode == "fix_loop":
            self.context.status_message = "DANGEROUS: Fix loop starting..."
        else:
            self.context.status_message = "Build running..."
        self._update_build_status_text(self._get_selected_target())
        thread = threading.Thread(
            target=self._run_worker,
            args=(mode, target_id),
            daemon=True,
        )
        self._runner_thread = thread
        thread.start()

    def handle_stop(self) -> bool:
        if not self._running_mode:
            self.context.status_message = "No build running"
            return False
        self._stop_event.set()
        self.context.status_message = "Stop requested... finishing current step safely"
        return True

    def _run_worker(self, mode: str, target_id: str):
        session_id = self._get_session_id()
        if not session_id:
            self._event_queue.put({"type": "error", "message": "No session selected"})
            return
        if mode == "build":
            self._run_build_worker(session_id, target_id)
        else:
            self._run_fix_loop_worker(session_id, target_id)

    def _run_build_worker(self, session_id: str, target_id: str):
        try:
            result = run_build(session_id, target_id=target_id)
            self._event_queue.put({"type": "result", "mode": "build", "target_id": target_id, "result": result})
        except Exception as exc:
            self._event_queue.put({"type": "error", "message": str(exc)})

    def _run_fix_loop_worker(self, session_id: str, target_id: str):
        max_iterations = self.fix_loop_max_iterations or 1
        fix_limit = self.fix_loop_limit or 1
        try:
            for iteration in range(1, max_iterations + 1):
                if self._stop_event.is_set():
                    self._event_queue.put({"type": "stopped", "mode": "fix_loop"})
                    return
                self._event_queue.put(
                    {
                        "type": "status",
                        "message": f"DANGEROUS: Fix loop iteration {iteration}/{max_iterations} - build",
                        "iteration": iteration,
                    }
                )
                run_build(session_id, target_id=target_id)
                diagnostics = get_diagnostics(session_id, target_id=target_id, include_samples=False)
                signature = self._pick_signature(diagnostics)
                self._event_queue.put(
                    {
                        "type": "fix_iteration",
                        "iteration": iteration,
                        "max_iterations": max_iterations,
                        "signature": signature,
                    }
                )
                if not diagnostics:
                    self._event_queue.put({"type": "done", "mode": "fix_loop", "status": "clean"})
                    return
                if self._stop_event.is_set():
                    self._event_queue.put({"type": "stopped", "mode": "fix_loop"})
                    return
                run_fix_loop(session_id, target_id=target_id, limit=fix_limit)
            self._event_queue.put({"type": "done", "mode": "fix_loop", "status": "complete"})
        except Exception as exc:
            self._event_queue.put({"type": "error", "message": str(exc)})

    def _pick_signature(self, diagnostics: List[DiagnosticInfo]) -> str:
        if not diagnostics:
            return "(no diagnostics)"
        diag = diagnostics[0]
        message = diag.message or "(no message)"
        if diag.file_path:
            location = f"{diag.file_path}:{diag.line_number or ''}"
            return f"{location} {message}".strip()
        return message

    def poll_updates(self) -> bool:
        if self.position != "left":
            return False
        updated = False
        refresh_needed = False
        while True:
            try:
                event = self._event_queue.get_nowait()
            except queue.Empty:
                break
            updated = True
            event_type = event.get("type")
            if event_type == "status":
                message = event.get("message", "")
                if message:
                    self.context.status_message = message
                self.fix_loop_iteration = event.get("iteration", self.fix_loop_iteration)
                refresh_needed = True
            elif event_type == "fix_iteration":
                self.fix_loop_iteration = event.get("iteration", self.fix_loop_iteration)
                self.fix_loop_signature = event.get("signature")
                refresh_needed = True
            elif event_type == "result":
                result = event.get("result", {}) or {}
                target_id = event.get("target_id")
                if target_id:
                    self.last_run_results[target_id] = result
                    artifact_hint = self._extract_artifact_hint(result)
                    self.last_artifact_hints[target_id] = artifact_hint
                status = result.get("status")
                if status == "success":
                    self.context.status_message = "Build complete"
                else:
                    self.context.status_message = f"Build finished: {status or 'unknown'}"
                self._running_mode = None
                self._running_target_id = None
                self.context.build_is_running = False
                refresh_needed = True
            elif event_type == "done":
                if event.get("mode") == "fix_loop":
                    status = event.get("status", "complete")
                    if status == "clean":
                        self.context.status_message = "Fix loop complete (no diagnostics)"
                    else:
                        self.context.status_message = "Fix loop complete"
                self._running_mode = None
                self._running_target_id = None
                self.context.build_is_running = False
                refresh_needed = True
            elif event_type == "stopped":
                self.context.status_message = "Fix loop stopped"
                self._running_mode = None
                self._running_target_id = None
                self.context.build_is_running = False
                refresh_needed = True
            elif event_type == "error":
                message = event.get("message", "Build error")
                self.context.status_message = f"Error: {message}"
                self._running_mode = None
                self._running_target_id = None
                self.context.build_is_running = False
                refresh_needed = True

        if refresh_needed:
            self.refresh_data()
        self._update_build_status_text(self._get_selected_target())
        return updated or refresh_needed

    def _extract_artifact_hint(self, result: Dict[str, Any]) -> str:
        if not isinstance(result, dict):
            return "(not available)"
        for key in ("artifacts", "artifact_paths", "artifact_path", "output_paths", "output_path"):
            value = result.get(key)
            if not value:
                continue
            if isinstance(value, list):
                return ", ".join(str(item) for item in value[:3])
            return str(value)
        return "(not available)"

    def _update_build_status_text(self, target: Optional[BuildTargetRow]):
        if self.position != "left":
            return
        if self._running_mode == "build" and self._running_target_id:
            short_id = self._short_id(self._running_target_id)
            self.context.build_status_text = f"RUNNING build: {short_id} | stop: F8"
            return
        if self._running_mode == "fix_loop":
            iteration = self.fix_loop_iteration or 0
            max_iter = self.fix_loop_max_iterations or 0
            signature = self.fix_loop_signature or "(awaiting diagnostics)"
            self.context.build_status_text = (
                f"DANGEROUS fix loop {iteration}/{max_iter} | top: {signature} | stop: F8"
            )
            return
        if not target:
            self.context.build_status_text = ""
            return
        short_id = self._short_id(target.id)
        active = "active" if target.id == self.active_target_id else "inactive"
        status = target.status or "unknown"
        self.context.build_status_text = f"Target: {short_id} ({active}) | status: {status}"

    def _short_id(self, value: str) -> str:
        return value[:8] + "..." if len(value) > 8 else value

    def _load_target_details(self):
        target_id = self.context.selected_build_target_id
        if not target_id:
            self.last_loaded_target_id = None
            return
        self.last_loaded_target_id = target_id

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

        if self.position == "right":
            self._load_target_details()

        self.window.erase()
        height, width = self.window.getmaxyx()

        if self.is_focused and curses.has_colors():
            self.window.bkgd(' ', curses.color_pair(3))
        elif curses.has_colors():
            self.window.bkgd(' ', curses.color_pair(0))

        if self.position == "left":
            title = "Build Targets"
        else:
            selected = self._get_selected_target()
            details_name = None
            if selected:
                details_name = selected.name or self._short_id(selected.id)
            title = f"Build Details: {details_name or 'None'}"

        try:
            self.window.addstr(0, 1, title[: width - 3], curses.A_BOLD)
        except Exception:
            pass

        if self.position == "left":
            self._render_target_list(height, width)
        else:
            self._render_target_details(height, width)

        self.window.noutrefresh()

    def _render_target_list(self, height: int, width: int):
        session_id = self._get_session_id()
        if not session_id:
            try:
                self.window.addstr(2, 1, "No session selected", curses.A_DIM)
            except Exception:
                pass
            return

        if not self.filtered_targets:
            message = "No build targets found"
            if self.filter_text:
                message = "No build targets match filter"
            try:
                self.window.addstr(2, 1, message, curses.A_DIM)
            except Exception:
                pass
            return

        display_count = height - 2
        start_idx = self.scroll_offset
        end_idx = min(start_idx + display_count - 1, len(self.filtered_targets))

        for idx in range(start_idx, end_idx):
            target = self.filtered_targets[idx]
            row = 1 + (idx - start_idx)

            is_selected = idx == self.selected_index
            marker = "*" if target.id == self.active_target_id else " "
            short_id = self._short_id(target.id)
            last_modified = target.last_modified or "(not available)"
            display_text = f"{marker} {target.name} {short_id} {last_modified}"
            if len(display_text) >= width - 2:
                display_text = display_text[: width - 5] + "..."

            try:
                attr = curses.A_REVERSE if is_selected and self.is_focused else 0
                if is_selected and self.is_focused and curses.has_colors():
                    attr = curses.color_pair(1) | curses.A_BOLD
                self.window.addstr(row, 1, display_text.ljust(width - 2), attr)
            except Exception:
                break

    def _render_target_details(self, height: int, width: int):
        target = self._get_selected_target()
        if not target:
            try:
                self.window.addstr(2, 1, "Select a build target in the left pane", curses.A_DIM)
            except Exception:
                pass
            return

        def _value(value: Optional[str]) -> str:
            if value is None or value == "":
                return "(not available)"
            return str(value)

        details: List[str] = []
        details.append(f"Name: {_value(target.name)}")
        details.append(f"Target ID: {_value(target.id)}")
        details.append(f"Status: {_value(target.status)}")
        details.append(f"Active: {'Yes' if target.id == self.active_target_id else 'No'}")
        details.append(f"Categories: {_value(', '.join(target.categories) if target.categories else None)}")
        if target.description:
            details.append(f"Description: {_value(target.description)}")
        if target.why:
            details.append(f"Why: {_value(target.why)}")
        details.append(f"Created: {_value(target.created_at)}")
        details.append(f"Last Modified: {_value(target.last_modified)}")
        details.append(f"Last Build: {_value(target.last_build_time)}")
        details.append(f"Target File: {_value(target.path)}")

        details.append("")
        details.append("Pipeline Steps:")
        steps = self._pipeline_steps(target.pipeline)
        if steps:
            details.extend([f"  {step}" for step in steps])
        else:
            details.append("  (not available)")

        details.append("")
        details.append("Environment:")
        env_lines = self._environment_lines(target.environment)
        if env_lines:
            details.extend([f"  {line}" for line in env_lines])
        else:
            details.append("  (not available)")

        details.append("")
        details.append("Patterns:")
        pattern_lines = self._pattern_lines(target.patterns)
        if pattern_lines:
            details.extend([f"  {line}" for line in pattern_lines])
        else:
            details.append("  (not available)")

        details.append("")
        details.append("Last Run Summary:")
        summary_lines = self._last_run_summary(target.id)
        if summary_lines:
            details.extend([f"  {line}" for line in summary_lines])
        else:
            details.append("  (not available)")

        details.append("")
        details.append("Diagnostics Summary:")
        diagnostics = get_diagnostics(
            self._get_session_id() or "",
            target_id=target.id,
            include_samples=False,
        )
        error_count = len([d for d in diagnostics if d.level == "error"])
        warn_count = len([d for d in diagnostics if d.level == "warning"])
        note_count = len([d for d in diagnostics if d.level == "note"])
        details.append(f"  error: {error_count} | warning: {warn_count} | note: {note_count}")

        sources = list_diagnostics_sources()
        details.append("Diagnostics Sources:")
        if sources:
            details.extend([f"  {path}" for path in sources])
        else:
            details.append("  (not available)")

        details.append("")
        if self.show_diagnostics_preview:
            details.append(f"Top Diagnostics (max {self.diagnostics_preview_limit}):")
            preview = self._diagnostics_preview(diagnostics)
            if preview:
                details.extend([f"  {line}" for line in preview])
            else:
                details.append("  (not available)")
        else:
            details.append("Top Diagnostics: (press Enter to preview)")

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

    def _pipeline_steps(self, pipeline: Dict[str, Any]) -> List[str]:
        if not pipeline:
            return []
        steps = pipeline.get("steps") if isinstance(pipeline, dict) else None
        if steps and isinstance(steps, list):
            return [str(step) for step in steps]
        if isinstance(pipeline, list):
            return [str(step) for step in pipeline]
        return []

    def _environment_lines(self, environment: Dict[str, Any]) -> List[str]:
        if not environment:
            return []
        lines = []
        cwd = environment.get("cwd") if isinstance(environment, dict) else None
        if cwd:
            lines.append(f"cwd: {cwd}")
        vars_map = environment.get("vars") if isinstance(environment, dict) else None
        if isinstance(vars_map, dict) and vars_map:
            for key, value in list(vars_map.items())[:6]:
                lines.append(f"{key}={value}")
            if len(vars_map) > 6:
                lines.append(f"... {len(vars_map) - 6} more")
        return lines

    def _pattern_lines(self, patterns: Dict[str, Any]) -> List[str]:
        if not patterns:
            return []
        lines = []
        if isinstance(patterns, dict):
            for key in ("error_extract", "ignore"):
                value = patterns.get(key)
                if value:
                    if isinstance(value, list):
                        snippet = ", ".join(str(item) for item in value[:3])
                        if len(value) > 3:
                            snippet = f"{snippet}, ... ({len(value)} total)"
                        lines.append(f"{key}: {snippet}")
                    else:
                        lines.append(f"{key}: {value}")
        return lines

    def _last_run_summary(self, target_id: str) -> List[str]:
        result = self.last_run_results.get(target_id)
        if not result:
            return []
        lines = []
        status = result.get("status")
        if status:
            lines.append(f"status: {status}")
        if result.get("start_time"):
            lines.append(f"start: {result.get('start_time')}")
        if result.get("end_time"):
            lines.append(f"end: {result.get('end_time')}")
        if result.get("duration") is not None:
            lines.append(f"duration: {result.get('duration')}s")
        artifact_hint = self.last_artifact_hints.get(target_id, "(not available)")
        lines.append(f"artifacts: {artifact_hint}")
        return lines

    def _diagnostics_preview(self, diagnostics: List[DiagnosticInfo]) -> List[str]:
        preview = []
        for diag in diagnostics[: self.diagnostics_preview_limit]:
            message = diag.message or "(no message)"
            level = diag.level or "note"
            location = ""
            if diag.file_path:
                location = f"{diag.file_path}:{diag.line_number or ''}".rstrip(":")
            prefix = f"[{level}]"
            if location:
                preview.append(f"{prefix} {location} - {message}")
            else:
                preview.append(f"{prefix} {message}")
        return preview

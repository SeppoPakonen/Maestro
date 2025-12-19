"""
Tasks pane for MC2 Curses TUI.
Shows task list in left pane and task details/log tail in right pane.
"""
import curses
import os
import queue
import threading
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional

from maestro.ui_facade.phases import get_active_phase
from maestro.ui_facade.sessions import get_session_details
from maestro.ui_facade.tasks import (
    get_current_execution_state,
    list_tasks,
    resume_tasks,
    run_tasks,
    stop_tasks,
)
from maestro.tui_mc2.ui.modals import InputModal


@dataclass
class TaskRow:
    id: str
    title: str
    description: str
    status: str
    planner_model: str
    worker_model: str
    summary_file: str
    plan_id: Optional[str]


class TasksPane:
    def __init__(self, position: str, context):
        self.position = position  # "left" or "right"
        self.context = context
        self.window = None
        self.is_focused = False
        self.sessions_dir = "./.maestro/sessions"
        self.tasks: List[TaskRow] = []
        self.filtered_tasks: List[TaskRow] = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.detail_scroll_offset = 0
        self.detail_scroll_max = 0
        self.filter_text = ""
        self.active_plan_id: Optional[str] = None
        self.last_loaded_task_id: Optional[str] = None
        self.last_interrupt_task_id: Optional[str] = None
        self.last_run_limit: Optional[int] = None
        self._event_queue: "queue.Queue[dict]" = queue.Queue()
        self._runner_thread: Optional[threading.Thread] = None
        self._log_buffers: Dict[str, Deque[str]] = context.task_log_buffers

        self.refresh_data()

    def set_window(self, window):
        """Set the curses window for this pane."""
        self.window = window

    def set_focused(self, focused: bool):
        """Set focus state for this pane."""
        self.is_focused = focused
        if focused and self.position == "right":
            self._load_task_details()

    def _get_session_id(self) -> Optional[str]:
        return self.context.active_session_id or self.context.selected_session_id

    def _get_active_plan(self, session_id: str) -> Optional[str]:
        try:
            phase = get_active_phase(session_id)
        except Exception:
            return None
        return phase.phase_id if phase else None

    def refresh_data(self):
        """Refresh task list data."""
        session_id = self._get_session_id()
        self.tasks = []
        self.filtered_tasks = []
        self.active_plan_id = None

        if not session_id:
            if self.position == "left":
                self.context.selected_task_id = None
                self._update_task_status_text(None)
            return

        try:
            self.active_plan_id = self._get_active_plan(session_id)
            self.context.active_plan_id = self.active_plan_id
            if not self.active_plan_id:
                if self.position == "left":
                    self.context.selected_task_id = None
                    self._update_task_status_text(None)
                return
            tasks = list_tasks(session_id, plan_id=self.active_plan_id)
            self.tasks = [
                TaskRow(
                    id=task.id,
                    title=task.title,
                    description=task.description,
                    status=task.status,
                    planner_model=task.planner_model,
                    worker_model=task.worker_model,
                    summary_file=task.summary_file,
                    plan_id=task.plan_id,
                )
                for task in tasks
            ]

            preserve_id = self.context.selected_task_id
            if preserve_id is None and self.tasks and self.position == "left":
                preserve_id = self.tasks[0].id
                self.context.selected_task_id = preserve_id

            self._apply_filter(preserve_id)

            if self.position == "right":
                self._sync_selected_index_from_context()
                self.last_loaded_task_id = None
                self._load_task_details()
        except Exception as exc:
            self.context.status_message = f"Error loading tasks: {str(exc)}"
            if self.position == "left":
                self.context.selected_task_id = None
                self._update_task_status_text(None)

    def _apply_filter(self, preserve_selected_id: Optional[str] = None):
        filter_value = self.filter_text.lower()
        if filter_value:
            self.filtered_tasks = [
                task
                for task in self.tasks
                if filter_value in task.title.lower() or filter_value in task.id.lower()
            ]
        else:
            self.filtered_tasks = list(self.tasks)

        if preserve_selected_id:
            self._set_selected_by_id(preserve_selected_id)
        else:
            self.selected_index = 0
            self.scroll_offset = 0
            self._sync_selected_id()

    def _get_selected_task(self) -> Optional[TaskRow]:
        if self.position == "right":
            target_id = self.context.selected_task_id
            if not target_id:
                return None
            for task in self.tasks:
                if task.id == target_id:
                    return task
            return None
        if not self.filtered_tasks:
            return None
        if self.selected_index < 0 or self.selected_index >= len(self.filtered_tasks):
            return None
        return self.filtered_tasks[self.selected_index]

    def _sync_selected_id(self):
        if self.position != "left":
            return
        selected = self._get_selected_task()
        self.context.selected_task_id = selected.id if selected else None
        self._update_task_status_text(selected)

    def _sync_selected_index_from_context(self):
        if not self.filtered_tasks:
            self.selected_index = 0
            return
        target_id = self.context.selected_task_id
        if not target_id:
            self.selected_index = 0
            return
        for idx, task in enumerate(self.filtered_tasks):
            if task.id == target_id:
                self.selected_index = idx
                break

    def _set_selected_by_id(self, task_id: str):
        if not self.filtered_tasks:
            self.selected_index = 0
            self.scroll_offset = 0
            self._sync_selected_id()
            return
        for idx, task in enumerate(self.filtered_tasks):
            if task.id == task_id:
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
        if self.position != "left" or not self.filtered_tasks:
            return
        new_index = max(0, min(len(self.filtered_tasks) - 1, self.selected_index + delta))
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
            self._move_selection(-len(self.filtered_tasks))
        else:
            self._scroll_details(-self.detail_scroll_max)

    def move_end(self):
        if self.position == "left":
            self._move_selection(len(self.filtered_tasks))
        else:
            self._scroll_details(self.detail_scroll_max)

    def handle_enter(self):
        """Handle enter key press."""
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
        input_modal = InputModal(parent, "Task Filter", "Filter:", self.filter_text)
        new_value = input_modal.show()
        if new_value is None:
            self.context.status_message = "Filter unchanged"
            return
        self.filter_text = new_value.strip()
        self._apply_filter()
        self.context.status_message = "Filter updated"

    def _is_running(self) -> bool:
        state = get_current_execution_state()
        return bool(state.get("is_running"))

    def _run_tasks_worker(self, session_id: str, limit: Optional[int], resume: bool):
        def on_status_change(message: str):
            self._event_queue.put({"type": "status", "message": message})

        def on_output(text: str):
            state = get_current_execution_state()
            task_id = state.get("current_task_id")
            self._event_queue.put({"type": "output", "task_id": task_id, "text": text})

        try:
            if resume:
                result = resume_tasks(
                    session_id,
                    limit=limit,
                    on_status_change=on_status_change,
                    on_output=on_output,
                    sessions_dir=self.sessions_dir,
                )
            else:
                result = run_tasks(
                    session_id,
                    limit=limit,
                    on_status_change=on_status_change,
                    on_output=on_output,
                    sessions_dir=self.sessions_dir,
                )
            self._event_queue.put({"type": "done", "success": bool(result)})
        except Exception as exc:
            self._event_queue.put({"type": "error", "message": str(exc)})

    def handle_run(self, limit: Optional[int] = None):
        session_id = self._get_session_id()
        if not session_id:
            self.context.status_message = "No session selected"
            return
        if not self.active_plan_id:
            self.context.status_message = "No active plan"
            return
        if self._is_running():
            self.context.status_message = "Already running"
            return
        interrupted = any(task.status == "interrupted" for task in self.tasks)
        self.last_run_limit = limit
        self.last_interrupt_task_id = None
        self.context.status_message = "Starting execution"
        thread = threading.Thread(
            target=self._run_tasks_worker,
            args=(session_id, limit, interrupted),
            daemon=True,
        )
        self._runner_thread = thread
        thread.start()

    def handle_run_with_limit(self):
        parent = self.context.modal_parent or self.window
        if parent is None:
            self.context.status_message = "Unable to open modal"
            return
        input_modal = InputModal(parent, "Run With Limit", "Task limit:", "")
        value = input_modal.show()
        if value is None:
            self.context.status_message = "Run limit cancelled"
            return
        value = value.strip()
        if not value.isdigit():
            self.context.status_message = "Invalid limit"
            return
        limit = int(value)
        if limit <= 0:
            self.context.status_message = "Invalid limit"
            return
        self.handle_run(limit=limit)

    def handle_stop(self):
        if stop_tasks():
            state = get_current_execution_state()
            self.last_interrupt_task_id = state.get("current_task_id")
            self.context.status_message = "Stop requested... finishing current step safely"
            return
        self.context.status_message = "No running tasks"

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
                refresh_needed = True
            elif event_type == "output":
                task_id = event.get("task_id")
                text = event.get("text", "")
                if task_id:
                    buffer = self._log_buffers.setdefault(task_id, deque(maxlen=200))
                    for line in text.splitlines():
                        buffer.append(line)
                refresh_needed = True
            elif event_type == "done":
                success = event.get("success", False)
                if not success:
                    if not self.last_interrupt_task_id:
                        state = get_current_execution_state()
                        self.last_interrupt_task_id = state.get("current_task_id")
                    self.context.status_message = "Execution interrupted"
                else:
                    self.last_interrupt_task_id = None
                    self.context.status_message = "Execution complete"
                refresh_needed = True
            elif event_type == "error":
                message = event.get("message", "Execution error")
                self.context.status_message = f"Error: {message}"
                refresh_needed = True

        if refresh_needed:
            self.refresh_data()
        self._update_task_status_text(self._get_selected_task())
        return updated or refresh_needed

    def _update_task_status_text(self, task: Optional[TaskRow]):
        if self.position != "left":
            return
        state = get_current_execution_state()
        current_task = state.get("current_task_id")
        is_running = state.get("is_running")
        if is_running and current_task:
            index = 0
            total = len(self.tasks)
            for idx, row in enumerate(self.tasks, start=1):
                if row.id == current_task:
                    index = idx
                    break
            short_id = current_task[:8] + "..." if len(current_task) > 8 else current_task
            limit_text = f" | limit: {self.last_run_limit}" if self.last_run_limit else ""
            self.context.task_status_text = (
                f"RUNNING: {short_id} ({index}/{total}) | stop: F8{limit_text}"
            )
            return
        if self.last_interrupt_task_id:
            short_id = (
                self.last_interrupt_task_id[:8] + "..."
                if len(self.last_interrupt_task_id) > 8
                else self.last_interrupt_task_id
            )
            self.context.task_status_text = f"INTERRUPTED at {short_id} | resume with F5"
            return
        if not task:
            self.context.task_status_text = ""
            return
        short_id = task.id[:8] + "..." if len(task.id) > 8 else task.id
        plan_short = (
            self.active_plan_id[:8] + "..." if self.active_plan_id and len(self.active_plan_id) > 8 else self.active_plan_id
        )
        engine = task.worker_model or "(not available)"
        self.context.task_status_text = (
            f"Task: {short_id} ({task.status}) | plan: {plan_short or '(none)'} | engine: {engine}"
        )

    def _load_task_details(self):
        task_id = self.context.selected_task_id
        if not task_id:
            self.last_loaded_task_id = None
            return
        self.last_loaded_task_id = task_id

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
        if os.getenv("MAESTRO_MC2_FAULT_INJECT") == "pane_render":
            raise RuntimeError("Injected pane render failure")
        if not self.window:
            return

        if self.position == "right":
            self._load_task_details()

        self.window.erase()
        height, width = self.window.getmaxyx()

        if self.is_focused and curses.has_colors():
            self.window.bkgd(' ', curses.color_pair(3))
        elif curses.has_colors():
            self.window.bkgd(' ', curses.color_pair(0))

        if self.position == "left":
            title = "Tasks"
        else:
            selected = self._get_selected_task()
            details_name = None
            if selected:
                details_name = selected.title or selected.id[:8] + "..."
            title = f"Task Details: {details_name or 'None'}"

        try:
            self.window.addstr(0, 1, title[: width - 3], curses.A_BOLD)
        except Exception:
            pass

        if self.position == "left":
            self._render_task_list(height, width)
        else:
            self._render_task_details(height, width)

        self.window.noutrefresh()

    def _render_task_list(self, height: int, width: int):
        session_id = self._get_session_id()
        if not session_id:
            try:
                self.window.addstr(2, 1, "No session selected", curses.A_DIM)
            except Exception:
                pass
            return

        if not self.active_plan_id:
            try:
                self.window.addstr(2, 1, "No active plan", curses.A_DIM)
            except Exception:
                pass
            return

        if not self.filtered_tasks:
            message = "No tasks found"
            if self.filter_text:
                message = "No tasks match filter"
            try:
                self.window.addstr(2, 1, message, curses.A_DIM)
            except Exception:
                pass
            return

        display_count = height - 2
        start_idx = self.scroll_offset
        end_idx = min(start_idx + display_count - 1, len(self.filtered_tasks))

        status_icons = {
            "pending": ".",
            "in_progress": ">",
            "done": "+",
            "error": "x",
            "interrupted": "!",
            "skipped": "-",
        }

        for idx in range(start_idx, end_idx):
            task = self.filtered_tasks[idx]
            row = 1 + (idx - start_idx)

            is_selected = (idx == self.selected_index)
            status_icon = status_icons.get(task.status, "?")
            title = task.title or "(not available)"
            engine = f" [{task.worker_model}]" if task.worker_model else ""
            display_text = f"{status_icon} {task.id[:8]} {title}{engine}"
            if len(display_text) >= width - 2:
                display_text = display_text[: width - 5] + "..."

            try:
                attr = curses.A_REVERSE if is_selected and self.is_focused else 0
                if is_selected and self.is_focused and curses.has_colors():
                    attr = curses.color_pair(1) | curses.A_BOLD
                self.window.addstr(row, 1, display_text.ljust(width - 2), attr)
            except Exception:
                break

    def _render_task_details(self, height: int, width: int):
        task = self._get_selected_task()
        if not task:
            try:
                self.window.addstr(2, 1, "Select a task in the left pane", curses.A_DIM)
            except Exception:
                pass
            return

        session_id = self._get_session_id()
        session_status = None
        if session_id:
            try:
                session_status = get_session_details(session_id).status
            except Exception:
                session_status = None

        details = []

        def _value(value: Optional[str]) -> str:
            if value is None or value == "":
                return "(not available)"
            return str(value)

        short_id = task.id[:8] + "..." if len(task.id) > 8 else task.id
        details.append(f"Task ID: {short_id}")
        details.append(f"Full ID: {_value(task.id)}")
        details.append(f"Status: {_value(task.status)}")
        details.append(f"Phase: (not available)")
        details.append(f"Engine: {_value(task.worker_model)}")
        details.append(f"Planner: {_value(task.planner_model)}")
        details.append(f"Plan ID: {_value(task.plan_id)}")
        details.append(f"Session Status: {_value(session_status)}")
        details.append(f"Summary File: {_value(task.summary_file)}")

        output_path = None
        if session_id:
            output_dir = os.path.join(self.sessions_dir, session_id[:8], "outputs")
            output_path = os.path.join(output_dir, f"{task.id}.txt")

        details.append(f"Stdout: {_value(output_path)}")
        details.append("Stderr: (not available)")
        details.append("Input Prompt: (not available)")
        details.append("Diff Ref: (not available)")
        details.append("")
        details.append("Log Tail:")

        log_lines = self._get_log_tail(task, max_lines=8, output_path=output_path)
        if log_lines:
            details.extend([f"  {line}" for line in log_lines])
        else:
            details.append("  (not available)")

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

    def _get_log_tail(self, task: TaskRow, max_lines: int, output_path: Optional[str]) -> List[str]:
        if output_path and os.path.exists(output_path):
            return self._tail_file(output_path, max_lines)
        buffer = self._log_buffers.get(task.id)
        if buffer:
            return list(buffer)[-max_lines:]
        if task.summary_file and os.path.exists(task.summary_file):
            return self._tail_file(task.summary_file, max_lines)
        return []

    @staticmethod
    def _tail_file(path: str, max_lines: int) -> List[str]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                lines = handle.read().splitlines()
        except Exception:
            return []
        if len(lines) <= max_lines:
            return lines
        return lines[-max_lines:]

"""
Plans pane for MC2 Curses TUI
Shows plan tree in left pane and plan details in right pane.
"""
import curses
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from maestro.ui_facade.plans import (
    PlanTreeNode,
    get_active_plan,
    get_plan_tree,
    kill_plan,
    set_active_plan,
)
from maestro.ui_facade.tasks import list_tasks
from maestro.tui_mc2.ui.modals import ConfirmModal


@dataclass
class PlanRow:
    plan_id: str
    label: str
    status: str
    created_at: str
    parent_plan_id: Optional[str]
    depth: int
    has_children: bool
    is_collapsed: bool
    subtask_count: int


class PlansPane:
    def __init__(self, position: str, context):
        self.position = position  # "left" or "right"
        self.context = context
        self.window = None
        self.is_focused = False
        self.plan_tree_root: Optional[PlanTreeNode] = None
        self.plan_map: Dict[str, PlanTreeNode] = {}
        self.plan_rows: List[PlanRow] = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.collapsed_plan_ids: Set[str] = set()
        self.task_status_counts: Dict[str, Dict[str, int]] = {}
        self.active_plan_id: Optional[str] = None
        self.no_plans_reason: Optional[str] = None
        self.last_loaded_plan_id: Optional[str] = None

        self.refresh_data()

    def set_window(self, window):
        """Set the curses window for this pane."""
        self.window = window

    def set_focused(self, focused: bool):
        """Set focus state for this pane."""
        self.is_focused = focused
        if focused and self.position == "right":
            self._load_plan_details()

    def _get_session_id(self) -> Optional[str]:
        return self.context.active_session_id or self.context.selected_session_id

    def refresh_data(self):
        """Refresh the plan data."""
        session_id = self._get_session_id()
        self.no_plans_reason = None
        self.plan_tree_root = None
        self.plan_map = {}
        self.plan_rows = []
        self.task_status_counts = {}
        self.active_plan_id = None

        if not session_id:
            if self.position == "left":
                self.context.selected_plan_id = None
                self._update_plan_status_text(None)
            return

        try:
            self.plan_tree_root = get_plan_tree(session_id)
            self.plan_map = {}
            self._index_tree(self.plan_tree_root)

            self.task_status_counts = self._compute_task_counts(session_id)

            active_plan = get_active_plan(session_id)
            self.active_plan_id = active_plan.plan_id if active_plan else None
            self.context.active_plan_id = self.active_plan_id

            self.collapsed_plan_ids &= set(self.plan_map.keys())
            preserve_id = self.context.selected_plan_id
            if preserve_id is None and self.position == "left" and self.plan_tree_root:
                preserve_id = self.plan_tree_root.plan_id
                self.context.selected_plan_id = preserve_id

            self._rebuild_rows(preserve_id)
            if self.position == "right":
                self.last_loaded_plan_id = None
                self._load_plan_details()
        except ValueError as exc:
            self.no_plans_reason = str(exc)
            if self.position == "left":
                self.context.selected_plan_id = None
                self._update_plan_status_text(None)
        except Exception as exc:
            self.context.status_message = f"Error loading plans: {str(exc)}"
            if self.position == "left":
                self.context.selected_plan_id = None
                self._update_plan_status_text(None)

    def _index_tree(self, node: PlanTreeNode):
        self.plan_map[node.plan_id] = node
        for child in node.children:
            self._index_tree(child)

    def _compute_task_counts(self, session_id: str) -> Dict[str, Dict[str, int]]:
        counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {
                "pending": 0,
                "running": 0,
                "done": 0,
                "failed": 0,
                "interrupted": 0,
            }
        )
        status_map = {
            "pending": "pending",
            "in_progress": "running",
            "done": "done",
            "error": "failed",
            "interrupted": "interrupted",
        }
        try:
            tasks = list_tasks(session_id)
        except Exception:
            return counts

        for task in tasks:
            plan_id = getattr(task, "plan_id", None)
            if not plan_id:
                continue
            status_key = status_map.get(getattr(task, "status", ""))
            if not status_key:
                continue
            counts[plan_id][status_key] += 1
        return counts

    def _rebuild_rows(self, preserve_selected_id: Optional[str] = None):
        self.plan_rows = []
        if not self.plan_tree_root:
            return

        def walk(node: PlanTreeNode, depth: int):
            has_children = bool(node.children)
            is_collapsed = node.plan_id in self.collapsed_plan_ids
            row = PlanRow(
                plan_id=node.plan_id,
                label=node.label,
                status=node.status,
                created_at=node.created_at,
                parent_plan_id=node.parent_plan_id,
                depth=depth,
                has_children=has_children,
                is_collapsed=is_collapsed,
                subtask_count=len(node.subtasks),
            )
            self.plan_rows.append(row)
            if has_children and is_collapsed:
                return
            for child in node.children:
                walk(child, depth + 1)

        walk(self.plan_tree_root, 0)

        if preserve_selected_id:
            self._set_selected_by_id(preserve_selected_id)
        else:
            self.selected_index = 0
            self.scroll_offset = 0
            self._sync_selected_id()

    def _get_selected_row(self) -> Optional[PlanRow]:
        if self.position == "right":
            target_id = self.context.selected_plan_id
            if not target_id:
                return None
            for row in self.plan_rows:
                if row.plan_id == target_id:
                    return row
            return None
        if not self.plan_rows:
            return None
        if self.selected_index < 0 or self.selected_index >= len(self.plan_rows):
            return None
        return self.plan_rows[self.selected_index]

    def _sync_selected_id(self):
        if self.position != "left":
            return
        selected = self._get_selected_row()
        self.context.selected_plan_id = selected.plan_id if selected else None
        self._update_plan_status_text(selected)

    def _set_selected_by_id(self, plan_id: str):
        if not self.plan_rows:
            self.selected_index = 0
            self.scroll_offset = 0
            self._sync_selected_id()
            return
        for idx, row in enumerate(self.plan_rows):
            if row.plan_id == plan_id:
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
        if self.position != "left" or not self.plan_rows:
            return
        new_index = max(0, min(len(self.plan_rows) - 1, self.selected_index + delta))
        if new_index != self.selected_index:
            self.selected_index = new_index
            self._ensure_visible()
            self._sync_selected_id()

    def move_up(self):
        self._move_selection(-1)

    def move_down(self):
        self._move_selection(1)

    def page_up(self):
        if not self.window:
            return
        step = max(1, (self.window.getmaxyx()[0] - 2) // 2)
        self._move_selection(-step)

    def page_down(self):
        if not self.window:
            return
        step = max(1, (self.window.getmaxyx()[0] - 2) // 2)
        self._move_selection(step)

    def move_home(self):
        if self.position == "left":
            self._move_selection(-len(self.plan_rows))

    def move_end(self):
        if self.position == "left":
            self._move_selection(len(self.plan_rows))

    def handle_enter(self):
        self.handle_set_active()

    def handle_left(self) -> bool:
        row = self._get_selected_row()
        if not row or not row.has_children or row.is_collapsed:
            return False
        self.collapsed_plan_ids.add(row.plan_id)
        self._rebuild_rows(row.plan_id)
        return True

    def handle_right(self) -> bool:
        row = self._get_selected_row()
        if not row or not row.has_children or not row.is_collapsed:
            return False
        self.collapsed_plan_ids.discard(row.plan_id)
        self._rebuild_rows(row.plan_id)
        return True

    def toggle_collapse(self) -> bool:
        row = self._get_selected_row()
        if not row or not row.has_children:
            return False
        if row.is_collapsed:
            self.collapsed_plan_ids.discard(row.plan_id)
        else:
            self.collapsed_plan_ids.add(row.plan_id)
        self._rebuild_rows(row.plan_id)
        return True

    def handle_set_active(self):
        selected = self._get_selected_row()
        if not selected:
            self.context.status_message = "No plan selected"
            return
        if self.active_plan_id == selected.plan_id:
            self.context.status_message = "Already active"
            return

        session_id = self._get_session_id()
        if not session_id:
            self.context.status_message = "No session selected"
            return

        parent = self.context.modal_parent or self.window
        if parent is None:
            self.context.status_message = "Unable to open modal"
            return

        lines = [
            f"Set active plan '{selected.label}'?",
            f"ID: {selected.plan_id[:8]}...",
        ]
        confirm_modal = ConfirmModal(parent, "Set Active Plan", lines)
        if not confirm_modal.show():
            self.context.status_message = "Set active cancelled"
            return

        try:
            updated = set_active_plan(session_id, selected.plan_id)
            self.active_plan_id = updated.plan_id
            self.context.active_plan_id = updated.plan_id
            self.refresh_data()
            self.context.status_message = f"Set active: {updated.plan_id[:8]}..."
        except Exception as exc:
            self.context.status_message = f"Error setting active: {str(exc)}"

    def handle_kill(self):
        selected = self._get_selected_row()
        if not selected:
            self.context.status_message = "No plan selected"
            return

        session_id = self._get_session_id()
        if not session_id:
            self.context.status_message = "No session selected"
            return

        parent = self.context.modal_parent or self.window
        if parent is None:
            self.context.status_message = "Unable to open modal"
            return

        lines = [
            f"Kill plan '{selected.label}'?",
            f"ID: {selected.plan_id[:8]}...",
        ]
        if self.active_plan_id == selected.plan_id:
            lines.append("WARNING: This is the active plan.")
        lines.append("")
        lines.append("Confirm kill?")

        confirm_modal = ConfirmModal(parent, "Kill Plan Branch", lines)
        if not confirm_modal.show():
            self.context.status_message = "Kill cancelled"
            return

        try:
            kill_plan(session_id, selected.plan_id)
            self.refresh_data()
            self.context.status_message = f"Killed plan: {selected.plan_id[:8]}..."
        except Exception as exc:
            self.context.status_message = f"Error killing plan: {str(exc)}"

    def handle_filter_char(self, _ch: str) -> bool:
        return False

    def handle_filter_backspace(self) -> bool:
        return False

    def clear_filter(self) -> bool:
        return False

    def _status_counts_for(self, plan_id: str) -> Dict[str, int]:
        counts = self.task_status_counts.get(plan_id)
        if not counts:
            return {
                "pending": 0,
                "running": 0,
                "done": 0,
                "failed": 0,
                "interrupted": 0,
            }
        return {
            "pending": counts.get("pending", 0),
            "running": counts.get("running", 0),
            "done": counts.get("done", 0),
            "failed": counts.get("failed", 0),
            "interrupted": counts.get("interrupted", 0),
        }

    def _update_plan_status_text(self, row: Optional[PlanRow]):
        if self.position != "left":
            return
        if not row:
            self.context.plan_status_text = ""
            return
        counts = self._status_counts_for(row.plan_id)
        short_id = row.plan_id[:8] + "..." if row.plan_id and len(row.plan_id) > 8 else row.plan_id
        state = "active" if self.active_plan_id == row.plan_id else row.status
        self.context.plan_status_text = (
            f"Plan: {short_id} ({state}) | tasks: "
            f"{counts['pending']} pending / {counts['running']} running / "
            f"{counts['done']} done / {counts['failed']} failed / {counts['interrupted']} interrupted"
        )

    def _load_plan_details(self):
        plan_id = self.context.selected_plan_id
        if not plan_id:
            self.last_loaded_plan_id = None
            return
        self.last_loaded_plan_id = plan_id

    def render(self):
        if os.getenv("MAESTRO_MC2_FAULT_INJECT") == "pane_render":
            raise RuntimeError("Injected pane render failure")
        if not self.window:
            return

        if self.position == "right":
            self._load_plan_details()

        self.window.erase()
        height, width = self.window.getmaxyx()

        if self.is_focused and curses.has_colors():
            self.window.bkgd(' ', curses.color_pair(3))
        elif curses.has_colors():
            self.window.bkgd(' ', curses.color_pair(0))

        if self.position == "left":
            title = "Plans"
        else:
            selected = self._get_selected_row()
            details_name = None
            if selected:
                details_name = selected.label or selected.plan_id[:8] + "..."
            title = f"Plan Details: {details_name or 'None'}"

        try:
            self.window.addstr(0, 1, title[: width - 3], curses.A_BOLD)
        except Exception:
            pass

        if self.position == "left":
            self._render_plan_list(height, width)
        else:
            self._render_plan_details(height, width)

        self.window.noutrefresh()

    def _render_plan_list(self, height, width):
        session_id = self._get_session_id()
        if not session_id:
            try:
                self.window.addstr(2, 1, "No session selected", curses.A_DIM)
            except Exception:
                pass
            return

        if not self.plan_rows:
            message = "No plans found"
            if self.no_plans_reason and "not found" in self.no_plans_reason.lower():
                message = "Session not found"
            try:
                self.window.addstr(2, 1, message, curses.A_DIM)
            except Exception:
                pass
            return

        display_count = height - 2
        start_idx = self.scroll_offset
        end_idx = min(start_idx + display_count - 1, len(self.plan_rows))

        for idx in range(start_idx, end_idx):
            row_data = self.plan_rows[idx]
            row = 1 + (idx - start_idx)

            is_selected = (idx == self.selected_index)
            active_marker = "○"
            if row_data.status == "dead":
                active_marker = "×"
            if self.active_plan_id == row_data.plan_id:
                active_marker = "●"

            branch_marker = " "
            if row_data.has_children:
                branch_marker = "+" if row_data.is_collapsed else "-"

            indent = "  " * row_data.depth
            label = row_data.label or "(not available)"
            created = row_data.created_at or ""
            display_text = (
                f"{indent}{branch_marker} {active_marker} {row_data.plan_id[:8]} "
                f"({row_data.subtask_count}) {label}"
            )
            if created:
                display_text += f" [{created}]"
            if len(display_text) >= width - 2:
                display_text = display_text[: width - 5] + "..."

            try:
                attr = curses.A_REVERSE if is_selected and self.is_focused else 0
                if is_selected and self.is_focused and curses.has_colors():
                    attr = curses.color_pair(1) | curses.A_BOLD
                self.window.addstr(row, 1, display_text.ljust(width - 2), attr)
            except Exception:
                break

    def _render_plan_details(self, height, width):
        selected = self._get_selected_row()
        if not selected:
            try:
                self.window.addstr(2, 1, "Select a plan in the left pane", curses.A_DIM)
            except Exception:
                pass
            return

        row = 2
        counts = self._status_counts_for(selected.plan_id)

        def _value(value: Optional[str]) -> str:
            if value is None or value == "":
                return "(not available)"
            return str(value)

        def _add_line(label: str, value: Optional[str]):
            nonlocal row
            if row >= height - 1:
                return
            text = f"{label}: {_value(value)}"
            try:
                self.window.addstr(row, 1, text[: width - 2], curses.A_NORMAL)
            except Exception:
                pass
            row += 1

        short_id = selected.plan_id[:8] + "..." if len(selected.plan_id) > 8 else selected.plan_id
        status = "active" if self.active_plan_id == selected.plan_id else selected.status

        _add_line("Label", selected.label)
        _add_line("Status", status)
        _add_line("Plan ID", short_id)
        _add_line("Full Plan ID", selected.plan_id)
        _add_line("Parent ID", selected.parent_plan_id)
        _add_line("Created", selected.created_at)
        _add_line("Modified", None)
        _add_line("Tasks (pending)", counts["pending"])
        _add_line("Tasks (running)", counts["running"])
        _add_line("Tasks (done)", counts["done"])
        _add_line("Tasks (failed)", counts["failed"])
        _add_line("Tasks (interrupted)", counts["interrupted"])
        _add_line("Dead Reason", None)
        _add_line("Killed At", None)

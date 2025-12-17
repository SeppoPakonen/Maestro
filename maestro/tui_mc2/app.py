"""
MC2 Curses-based TUI Application

Midnight Commander-style TUI implemented with Python curses.
Features:
- Top menubar row (1 line)
- Two panes (left/right) filling the screen
- Bottom status line (1 line)
- Tab to switch panes, arrow keys to navigate, F-keys for actions
"""

import curses
import os
import sys
import time
from typing import Optional, Dict
from dataclasses import dataclass, field

from maestro.tui_mc2.ui.menubar import Menubar
from maestro.tui_mc2.ui.status import StatusLine
from maestro.tui_mc2.ui.modals import ModalDialog
from maestro.tui_mc2.panes.sessions import SessionsPane
from maestro.tui_mc2.panes.plans import PlansPane
from maestro.tui_mc2.panes.tasks import TasksPane
from maestro.ui_facade.tasks import get_current_execution_state, stop_tasks
from maestro.tui_mc2.util.smoke import (
    SmokeMode,
    write_smoke_success,
    write_smoke_timeout,
    SMOKE_WATCHDOG_GRACE_SECONDS,
)


@dataclass
class AppContext:
    """Global application context/state"""
    smoke_mode: bool = False
    smoke_seconds: float = 0.5
    smoke_out: Optional[str] = None
    should_exit: bool = False
    status_message: str = "Ready"
    active_view: str = "sessions"
    focus_pane: str = "left"  # "left" or "right"
    active_session_id: Optional[str] = None
    selected_session_id: Optional[str] = None
    active_plan_id: Optional[str] = None
    selected_plan_id: Optional[str] = None
    selected_task_id: Optional[str] = None
    sessions_filter_text: str = ""
    sessions_filter_visible: int = 0
    sessions_filter_total: int = 0
    plan_status_text: str = ""
    task_status_text: str = ""
    task_log_buffers: Dict[str, object] = field(default_factory=dict)
    modal_parent: Optional[object] = None


class MC2App:
    """Main MC2 Curses Application"""
    
    def __init__(
        self,
        smoke_mode: bool = False,
        smoke_seconds: float = 0.5,
        smoke_out: Optional[str] = None,
        render_debug: bool = False,
    ):
        self.context = AppContext(
            smoke_mode=smoke_mode,
            smoke_seconds=smoke_seconds,
            smoke_out=smoke_out
        )
        self.stdscr = None
        self.menubar = None
        self.status_line = None
        self.left_pane = None
        self.right_pane = None
        self.render_debug = render_debug or os.getenv("MAESTRO_TUI_RENDER_DEBUG") == "1"
        self.force_curses_smoke = os.getenv("MAESTRO_MC2_SMOKE_USE_CURSES") == "1"
        self.fault_inject = os.getenv("MAESTRO_MC2_FAULT_INJECT")
        self.dirty_regions: Dict[str, bool] = {
            "menubar": True,
            "left": True,
            "right": True,
            "status": True,
            "modal": False,
        }
        self.last_status_message = self.context.status_message
        self.last_focus_pane = self.context.focus_pane
        self.last_active_session_id = self.context.active_session_id
        self.last_active_view = self.context.active_view
        self.last_plan_status_text = self.context.plan_status_text
        self.last_active_plan_id = self.context.active_plan_id
        self.last_task_status_text = self.context.task_status_text
        self.last_filter_status = (
            self.context.sessions_filter_text,
            self.context.sessions_filter_visible,
            self.context.sessions_filter_total,
        )
        self.frames = 0
        self.doupdate_calls = 0
        self.last_dirty_snapshot = []
        self.last_input_time = None
        self.last_timeout_ms = None
        self.loop_wakeups = 0
        self.loop_wakeups_per_sec = 0.0
        self.loop_sample_time = time.time()
        self.smoke_exit_status: Optional[int] = None
        self._teardown_called = False
        
        # Initialize panes
        self.left_pane = self._create_pane(self.context.active_view, position="left")
        self.right_pane = self._create_pane(self.context.active_view, position="right")
        
        # Create smoke mode manager
        self.smoke_manager = SmokeMode(
            enabled=smoke_mode,
            seconds=smoke_seconds,
            success_file=smoke_out,
            watchdog_grace=SMOKE_WATCHDOG_GRACE_SECONDS,
        )

    def run(self):
        """Main application entry point"""
        if self.context.smoke_mode and not self.force_curses_smoke:
            return self._run_smoke()
        return self._run_curses()

    def _run_smoke(self) -> int:
        """Run smoke mode without curses."""
        self.smoke_manager.start(None)
        try:
            self.left_pane.refresh_data()
            self.right_pane.refresh_data()

            while True:
                now = time.time()
                if self.smoke_manager.timed_out(now):
                    write_smoke_timeout(self.context.smoke_out)
                    return 1
                if self.smoke_manager.should_exit(now):
                    write_smoke_success(self.context.smoke_out)
                    return 0
                time.sleep(0.02)
        except Exception as e:
            print(f"Smoke test error: {e}", file=sys.stderr)
            return 1

    def _run_curses(self) -> int:
        """Run the interactive curses loop with guaranteed teardown."""
        stdscr = None
        try:
            stdscr = curses.initscr()
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            self._main_loop(stdscr)
            return self.smoke_exit_status or 0
        finally:
            if stdscr is not None:
                try:
                    stdscr.keypad(False)
                except Exception:
                    pass
            try:
                curses.nocbreak()
            except Exception:
                pass
            try:
                curses.echo()
            except Exception:
                pass
            try:
                curses.endwin()
            except Exception:
                pass
            self._teardown_called = True

    def _setup_ui(self, stdscr):
        """Setup the UI components"""
        self.stdscr = stdscr
        curses.curs_set(0)  # Hide cursor
        stdscr.keypad(True)
        stdscr.nodelay(False)  # Block on getch
        stdscr.timeout(-1)  # Block by default
        self.context.modal_parent = stdscr
        
        # Initialize colors if available
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)    # Menubar
            curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Status
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)   # Highlight
            curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_RED)     # Messages

        self._rebuild_layout()
        self._mark_all_dirty()

    def _rebuild_layout(self):
        """Rebuild windows based on the current terminal size."""
        height, width = self.stdscr.getmaxyx()
        content_height = max(1, height - 2)
        left_width = max(1, width // 2)
        right_width = max(1, width - left_width)

        menubar_win = self.stdscr.subwin(1, width, 0, 0)
        if self.menubar:
            self.menubar.set_window(menubar_win)
        else:
            self.menubar = Menubar(menubar_win, self.context)

        left_win = self.stdscr.subwin(content_height, left_width, 1, 0)
        right_win = self.stdscr.subwin(content_height, right_width, 1, left_width)
        self.left_pane.set_window(left_win)
        self.right_pane.set_window(right_win)

        status_win = self.stdscr.subwin(1, width, height - 1, 0)
        if self.status_line:
            self.status_line.set_window(status_win)
        else:
            self.status_line = StatusLine(status_win, self.context)
        self.status_line.set_debug_info(self.render_debug, "")

        self.left_pane.set_focused(self.context.focus_pane == "left")
        self.right_pane.set_focused(self.context.focus_pane == "right")

    def _create_pane(self, view: str, position: str):
        if view == "plans":
            return PlansPane(position=position, context=self.context)
        if view == "tasks":
            return TasksPane(position=position, context=self.context)
        return SessionsPane(position=position, context=self.context)

    def _set_view(self, view: str):
        if view == self.context.active_view:
            return
        self.context.active_view = view
        self.left_pane = self._create_pane(view, position="left")
        self.right_pane = self._create_pane(view, position="right")
        if self.stdscr is not None:
            self._rebuild_layout()
        self._mark_all_dirty()

    def _mark_dirty(self, *regions: str):
        for region in regions:
            if region in self.dirty_regions:
                self.dirty_regions[region] = True

    def _mark_all_dirty(self):
        for region in self.dirty_regions:
            self.dirty_regions[region] = True

    def _handle_resize(self):
        height, width = self.stdscr.getmaxyx()
        curses.resizeterm(height, width)
        self.stdscr.erase()
        self._rebuild_layout()
        self._mark_all_dirty()

    def _compute_timeout_ms(self, now: float) -> int:
        timeout_ms: Optional[int] = None
        if self.status_line:
            remaining = self.status_line.time_until_expire(now)
            if remaining is not None:
                timeout_ms = max(0, int(remaining * 1000))
        if self.context.smoke_mode:
            smoke_remaining = self.smoke_manager.time_until_exit(now)
            if smoke_remaining is not None:
                smoke_ms = max(0, int(smoke_remaining * 1000))
                timeout_ms = smoke_ms if timeout_ms is None else min(timeout_ms, smoke_ms)
        state = get_current_execution_state()
        if state.get("is_running"):
            task_ms = 200
            timeout_ms = task_ms if timeout_ms is None else min(timeout_ms, task_ms)
        return -1 if timeout_ms is None else timeout_ms

    def _sync_status_message(self):
        if not self.status_line:
            return
        if self.context.status_message != self.last_status_message:
            self.last_status_message = self.context.status_message
            ttl = self.status_line.default_ttl if self.context.status_message else None
            self.status_line.set_message(self.context.status_message, ttl=ttl)
            self._mark_dirty("status")

    def _sync_status_context(self):
        changed = False
        if self.context.active_view != self.last_active_view:
            self.last_active_view = self.context.active_view
            changed = True
        if self.context.focus_pane != self.last_focus_pane:
            self.last_focus_pane = self.context.focus_pane
            changed = True
        if self.context.active_session_id != self.last_active_session_id:
            self.last_active_session_id = self.context.active_session_id
            changed = True
        if self.context.active_plan_id != self.last_active_plan_id:
            self.last_active_plan_id = self.context.active_plan_id
            changed = True
        if self.context.plan_status_text != self.last_plan_status_text:
            self.last_plan_status_text = self.context.plan_status_text
            changed = True
        if self.context.task_status_text != self.last_task_status_text:
            self.last_task_status_text = self.context.task_status_text
            changed = True
        current_filter = (
            self.context.sessions_filter_text,
            self.context.sessions_filter_visible,
            self.context.sessions_filter_total,
        )
        if current_filter != self.last_filter_status:
            self.last_filter_status = current_filter
            changed = True
        if changed:
            self._mark_dirty("status")

    def _handle_menu_action(self, action_id: str):
        if action_id in ("refresh", "sessions.refresh"):
            if self.context.active_view != "sessions" and action_id != "refresh":
                self.context.status_message = "Switch to Sessions view"
                self._mark_dirty("status")
                return
            self.left_pane.refresh_data()
            self.right_pane.refresh_data()
            self.context.status_message = "Refreshed"
            self._mark_dirty("left", "right", "status")
        elif action_id in ("new", "sessions.new"):
            if self.context.active_view != "sessions":
                self.context.status_message = "Switch to Sessions view"
                self._mark_dirty("status")
                return
            self.dirty_regions["modal"] = True
            self.left_pane.handle_new()
            self.dirty_regions["modal"] = False
            self._mark_dirty("left", "right", "status")
        elif action_id in ("delete", "sessions.delete"):
            if self.context.active_view != "sessions":
                self.context.status_message = "Switch to Sessions view"
                self._mark_dirty("status")
                return
            self.dirty_regions["modal"] = True
            self.left_pane.handle_delete()
            self.dirty_regions["modal"] = False
            self._mark_dirty("left", "right", "status")
        elif action_id in ("set_active", "sessions.set_active"):
            if self.context.active_view != "sessions":
                self.context.status_message = "Switch to Sessions view"
                self._mark_dirty("status")
                return
            self.dirty_regions["modal"] = True
            self.left_pane.handle_set_active()
            self.dirty_regions["modal"] = False
            self._mark_dirty("left", "right", "status")
        elif action_id in ("plans.refresh",):
            if self.context.active_view != "plans":
                self.context.status_message = "Switch to Plans view"
                self._mark_dirty("status")
                return
            self.left_pane.refresh_data()
            self.right_pane.refresh_data()
            self.context.status_message = "Plans refreshed"
            self._mark_dirty("left", "right", "status")
        elif action_id in ("plans.set_active",):
            if self.context.active_view != "plans":
                self.context.status_message = "Switch to Plans view"
                self._mark_dirty("status")
                return
            self.dirty_regions["modal"] = True
            self.left_pane.handle_set_active()
            self.dirty_regions["modal"] = False
            self._mark_dirty("left", "right", "status")
        elif action_id in ("plans.kill",):
            if self.context.active_view != "plans":
                self.context.status_message = "Switch to Plans view"
                self._mark_dirty("status")
                return
            self.dirty_regions["modal"] = True
            self.left_pane.handle_kill()
            self.dirty_regions["modal"] = False
            self._mark_dirty("left", "right", "status")
        elif action_id in ("plans.toggle_collapse",):
            if self.context.active_view != "plans":
                self.context.status_message = "Switch to Plans view"
                self._mark_dirty("status")
                return
            if self.left_pane.toggle_collapse():
                self._mark_dirty("left", "right", "status")
            else:
                self._mark_dirty("status")
        elif action_id in ("tasks.refresh",):
            if self.context.active_view != "tasks":
                self.context.status_message = "Switch to Tasks view"
                self._mark_dirty("status")
                return
            self.left_pane.refresh_data()
            self.right_pane.refresh_data()
            self.context.status_message = "Tasks refreshed"
            self._mark_dirty("left", "right", "status")
        elif action_id in ("tasks.run",):
            if self.context.active_view != "tasks":
                self.context.status_message = "Switch to Tasks view"
                self._mark_dirty("status")
                return
            self.left_pane.handle_run()
            self._mark_dirty("left", "right", "status")
        elif action_id in ("tasks.run_limit",):
            if self.context.active_view != "tasks":
                self.context.status_message = "Switch to Tasks view"
                self._mark_dirty("status")
                return
            self.dirty_regions["modal"] = True
            self.left_pane.handle_run_with_limit()
            self.dirty_regions["modal"] = False
            self._mark_dirty("left", "right", "status")
        elif action_id in ("tasks.stop",):
            if self.context.active_view != "tasks":
                self.context.status_message = "Switch to Tasks view"
                self._mark_dirty("status")
                return
            self.left_pane.handle_stop()
            self._mark_dirty("left", "right", "status")
        elif action_id in ("view.sessions", "view.plans"):
            view = "sessions" if action_id.endswith("sessions") else "plans"
            self._set_view(view)
            self.context.status_message = f"View: {view.title()}"
            self._mark_dirty("menubar", "status")
        elif action_id == "view.tasks":
            self._set_view("tasks")
            self.context.status_message = "View: Tasks"
            self._mark_dirty("menubar", "status")
        elif action_id == "help":
            self.dirty_regions["modal"] = True
            modal = ModalDialog(self.stdscr, "Help", [
                "Maestro MC2 Help",
                "",
                "Navigation:",
                "  Arrows: Move cursor",
                "  Tab: Switch panes",
                "  Enter: Select/Open",
                "  ESC: Cancel/Back",
                "  F1: Help (this screen)",
                "  F5: Refresh",
                "  F7: New",
                "  F8: Delete",
                "  F9: Toggle menubar",
                "  F10: Quit",
                "",
                "Press any key to close..."
            ])
            modal.show()
            self.dirty_regions["modal"] = False
            self._mark_all_dirty()
        elif action_id == "quit":
            self.context.should_exit = True
        elif action_id == "toggle_menu":
            pass
        else:
            self.context.status_message = f"Unhandled menu action: {action_id}"
            self._mark_dirty("status")
        self._mark_dirty("menubar", "status")

    def _handle_key(self, key: int) -> bool:
        """Handle keyboard input, return True to continue, False to exit"""
        if key == 3:  # Ctrl+C
            if self._handle_ctrl_c():
                return True
            return False
        if key == 27:  # ESC
            # Check if we're in a menu first
            if self.menubar and self.menubar.is_active():
                self.menubar.deactivate()
                self._mark_dirty("menubar", "status")
                return True
            if self.context.focus_pane == "left" and self.left_pane.clear_filter():
                self._mark_dirty("left", "right", "status")
                return True
            return True
            
        elif key == ord('\t'):  # TAB
            # Switch focus between panes
            if self.context.focus_pane == "left":
                self.context.focus_pane = "right"
                self.left_pane.set_focused(False)
                self.right_pane.set_focused(True)
            else:
                self.context.focus_pane = "left"
                self.left_pane.set_focused(True)
                self.right_pane.set_focused(False)
            self._mark_dirty("left", "right", "status")
            return True

        elif key in (curses.KEY_PPAGE, 21):  # PageUp or Ctrl+U
            if key == 21 and self.context.active_view == "tasks" and self.context.focus_pane == "left":
                if self.left_pane.clear_filter():
                    self._mark_dirty("left", "right", "status")
                    return True
            if self.context.focus_pane == "left":
                self.left_pane.page_up()
                self._mark_dirty("left", "right", "status")
            elif hasattr(self.right_pane, "page_up"):
                self.right_pane.page_up()
                self._mark_dirty("right", "status")
            return True

        elif key in (curses.KEY_NPAGE, 4):  # PageDown or Ctrl+D
            if self.context.focus_pane == "left":
                self.left_pane.page_down()
                self._mark_dirty("left", "right", "status")
            elif hasattr(self.right_pane, "page_down"):
                self.right_pane.page_down()
                self._mark_dirty("right", "status")
            return True

        elif key == curses.KEY_HOME:
            if self.context.focus_pane == "left":
                self.left_pane.move_home()
                self._mark_dirty("left", "right", "status")
            return True

        elif key == curses.KEY_END:
            if self.context.focus_pane == "left":
                self.left_pane.move_end()
                self._mark_dirty("left", "right", "status")
            return True
            
        elif key == curses.KEY_UP:
            if self.context.focus_pane == "left":
                self.left_pane.move_up()
                self._mark_dirty("left", "right")
            else:
                self.right_pane.move_up()
                self._mark_dirty("right")
            return True
            
        elif key == curses.KEY_DOWN:
            if self.context.focus_pane == "left":
                self.left_pane.move_down()
                self._mark_dirty("left", "right")
            else:
                self.right_pane.move_down()
                self._mark_dirty("right")
            return True
                
        elif key == ord('\n') or key == 10 or key == 13:  # Enter
            if self.context.focus_pane == "left":
                self.left_pane.handle_enter()
                self._mark_dirty("left", "right", "status")
            else:
                self.right_pane.handle_enter()
                self._mark_dirty("right", "status")
            return True
            
        elif key == ord('q') or key == ord('Q'):
            return False  # Quit
            
        elif key == curses.KEY_F1:
            self._handle_menu_action("help")
            return True
            
        elif key == curses.KEY_F5:
            if self.context.active_view == "tasks":
                self._handle_menu_action("tasks.run")
            else:
                # Refresh both panes
                self.left_pane.refresh_data()
                self.right_pane.refresh_data()
                self.context.status_message = "Refreshed"
                self._mark_dirty("left", "right", "status")
            return True
            
        elif key == curses.KEY_F7:
            if self.context.active_view == "tasks":
                self._handle_menu_action("tasks.run_limit")
            elif self.context.active_view == "sessions":
                self._handle_menu_action("sessions.new")
            else:
                self.context.status_message = "No action for F7"
                self._mark_dirty("status")
            return True
            
        elif key == curses.KEY_F8:
            if self.context.active_view == "tasks":
                self._handle_menu_action("tasks.stop")
            elif self.context.active_view == "plans":
                self._handle_menu_action("plans.kill")
            else:
                self._handle_menu_action("sessions.delete")
            return True
            
        elif key == curses.KEY_F9:
            # Toggle menubar
            if self.menubar.is_active():
                self.menubar.deactivate()
            else:
                self.menubar.activate()
            self._mark_dirty("menubar", "status")
            return True
            
        elif key == curses.KEY_F10:
            from maestro.tui_mc2.ui.modals import ConfirmModal

            self.dirty_regions["modal"] = True
            confirmation = ConfirmModal(self.stdscr, "Confirm Quit", [
                "Quit Maestro TUI?",
                "",
                "Press Enter to confirm, Esc to cancel",
            ])
            confirmed = confirmation.show()
            self.dirty_regions["modal"] = False
            if confirmed:
                return False
            self._mark_all_dirty()
            return True

        elif key == curses.KEY_LEFT:
            if self.context.focus_pane == "left" and hasattr(self.left_pane, "handle_left"):
                if self.left_pane.handle_left():
                    self._mark_dirty("left", "right", "status")
            return True

        elif key == curses.KEY_RIGHT:
            if self.context.focus_pane == "left" and hasattr(self.left_pane, "handle_right"):
                if self.left_pane.handle_right():
                    self._mark_dirty("left", "right", "status")
            return True

        elif key == ord('/'):
            if self.context.active_view == "tasks" and self.context.focus_pane == "left":
                self.dirty_regions["modal"] = True
                self.left_pane.handle_filter_input()
                self.dirty_regions["modal"] = False
                self._mark_dirty("left", "right", "status")
                return True

        if self.context.focus_pane == "left":
            if key in (curses.KEY_BACKSPACE, 127, 8):
                if self.left_pane.handle_filter_backspace():
                    self._mark_dirty("left", "right", "status")
                    return True
            if 0 <= key <= 255:
                ch = chr(key)
                if ch.isalnum() and self.left_pane.handle_filter_char(ch):
                    self._mark_dirty("left", "right", "status")
                    return True
            
        return True

    def _main_loop(self, stdscr):
        """Main curses event loop"""
        self._setup_ui(stdscr)
        self.loop_sample_time = time.time()
        self.loop_wakeups = 0
        
        # Start smoke mode if enabled
        if self.context.smoke_mode:
            self.smoke_manager.start(stdscr)
        
        # Initial render
        self._render()
        
        # Main event loop
        while not self.context.should_exit:
            try:
                now = time.time()
                self.loop_wakeups += 1
                if now - self.loop_sample_time >= 1.0:
                    elapsed = now - self.loop_sample_time
                    self.loop_wakeups_per_sec = self.loop_wakeups / elapsed
                    self.loop_wakeups = 0
                    self.loop_sample_time = now

                # Check for smoke mode exit
                if self.context.smoke_mode and self.smoke_manager.timed_out(now):
                    self.smoke_exit_status = 1
                    write_smoke_timeout(self.context.smoke_out)
                    break
                if self.context.smoke_mode and self.smoke_manager.should_exit(now):
                    self.smoke_exit_status = 0
                    write_smoke_success(self.context.smoke_out)
                    break

                timeout_ms = self._compute_timeout_ms(now)
                if timeout_ms != self.last_timeout_ms:
                    stdscr.timeout(timeout_ms)
                    self.last_timeout_ms = timeout_ms

                # Get input (with timeout)
                key = stdscr.getch()

                if key != -1:  # -1 means no input within timeout
                    self.last_input_time = now
                    if key == curses.KEY_RESIZE:
                        self._handle_resize()
                    elif self.menubar and self.menubar.is_active() and self.menubar.handle_key(key):
                        action_id = self.menubar.consume_last_action()
                        if action_id:
                            self._handle_menu_action(action_id)
                        else:
                            self._mark_dirty("menubar", "status")
                    else:
                        if not self._handle_key(key):
                            break

                if self.status_line and self.status_line.maybe_expire(time.time()):
                    self._mark_dirty("status")

                if hasattr(self.left_pane, "poll_updates") and self.left_pane.poll_updates():
                    self._mark_dirty("left", "right", "status")
                if hasattr(self.right_pane, "poll_updates") and self.right_pane.poll_updates():
                    self._mark_dirty("right", "status")

                self._sync_status_message()
                self._sync_status_context()

                # Update display only if dirty
                self._render()
                
            except KeyboardInterrupt:
                if not self._handle_ctrl_c():
                    break
            except Exception as e:
                if self.fault_inject:
                    raise
                # Log error and continue
                self.context.status_message = f"Error: {str(e)}"
                self._sync_status_message()
                self._mark_dirty("status")
                self._render()

    def _handle_ctrl_c(self) -> bool:
        if stop_tasks():
            self.context.status_message = "Stop requested... finishing current step safely"
            self._mark_dirty("status")
            return True
        return False

    def _render(self):
        """Render all UI components"""
        if not self.stdscr:
            return

        renderable = ("menubar", "left", "right", "status")
        dirty_regions = [name for name, dirty in self.dirty_regions.items() if dirty]
        render_dirty = [name for name in renderable if self.dirty_regions.get(name)]
        if not render_dirty:
            return

        if self.render_debug and "status" not in dirty_regions:
            self.dirty_regions["status"] = True
            dirty_regions.append("status")

        self.last_dirty_snapshot = sorted(set(dirty_regions))
        debug_info = ""
        if self.render_debug:
            last_input = "idle"
            if self.last_input_time is not None:
                last_input = f"{max(0.0, time.time() - self.last_input_time):.1f}s"
            timeout_label = "block" if self.last_timeout_ms is None or self.last_timeout_ms < 0 else f"{self.last_timeout_ms}ms"
            dirty_label = ",".join(self.last_dirty_snapshot)
            wakeups = f"{self.loop_wakeups_per_sec:.1f}/s"
            debug_info = (
                f"DBG f={self.frames} d={self.doupdate_calls} dirty={dirty_label} "
                f"input={last_input} timeout={timeout_label} wake={wakeups}"
            )

        if self.status_line:
            self.status_line.set_debug_info(self.render_debug, debug_info)

        need_update = False
        if self.menubar and self.dirty_regions["menubar"]:
            self.menubar.render()
            self.dirty_regions["menubar"] = False
            need_update = True
        if self.left_pane and self.dirty_regions["left"]:
            self.left_pane.render()
            self.dirty_regions["left"] = False
            need_update = True
        if self.right_pane and self.dirty_regions["right"]:
            self.right_pane.render()
            self.dirty_regions["right"] = False
            need_update = True
        if self.status_line and self.dirty_regions["status"]:
            self.status_line.render()
            self.dirty_regions["status"] = False
            need_update = True

        if need_update:
            curses.doupdate()
            self.doupdate_calls += 1
            self.frames += 1


def main(smoke_mode=False, smoke_seconds=0.5, smoke_out=None, mc2_mode=True, render_debug: bool = False):
    """Main entry point for MC2 curses TUI"""
    if mc2_mode:
        app = MC2App(
            smoke_mode=smoke_mode,
            smoke_seconds=smoke_seconds,
            smoke_out=smoke_out,
            render_debug=render_debug,
        )
        return app.run()
    else:
        # Fallback to existing TUI
        from maestro.tui.app import main as textual_main
        return textual_main(smoke_mode=smoke_mode, smoke_seconds=smoke_seconds, smoke_out=smoke_out, mc_shell=False)


if __name__ == "__main__":
    raise SystemExit(main() or 0)

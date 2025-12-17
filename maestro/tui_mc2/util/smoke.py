"""
Smoke mode utilities for MC2 TUI
"""
import threading
import time
from typing import Optional


def write_smoke_success(smoke_out: Optional[str] = None):
    """Write smoke success marker to file or stdout"""
    marker = "MAESTRO_TUI_SMOKE_OK"
    print(marker)  # Always print to stdout
    
    if smoke_out:
        try:
            with open(smoke_out, 'w') as f:
                f.write(marker)
        except Exception:
            # If file write fails, just continue
            pass


class SmokeMode:
    def __init__(self, enabled: bool = False, seconds: float = 0.5, success_file: Optional[str] = None):
        self.enabled = enabled
        self.seconds = seconds
        self.success_file = success_file
        self.start_time: Optional[float] = None
        self.should_exit_flag = False
        
        if enabled:
            # Start timer in background thread to ensure we don't hang
            self.timer_thread = threading.Thread(target=self._timer_worker, daemon=True)
            self.timer_thread.start()
    
    def _timer_worker(self):
        """Background timer worker"""
        time.sleep(self.seconds)
        self.should_exit_flag = True
        write_smoke_success(self.success_file)
    
    def start(self, stdscr):
        """Start smoke mode (for curses apps)"""
        if self.enabled:
            self.start_time = time.time()
    
    def should_exit(self) -> bool:
        """Check if smoke mode says we should exit"""
        if not self.enabled:
            return False
        return self.should_exit_flag or (self.start_time and time.time() - self.start_time >= self.seconds)
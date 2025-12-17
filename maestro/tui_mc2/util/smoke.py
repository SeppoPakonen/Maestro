"""
Smoke mode utilities for MC2 TUI
"""
import time
from typing import Optional


SMOKE_OK_MARKER = "MAESTRO_TUI_SMOKE_OK"
SMOKE_TIMEOUT_MARKER = "MAESTRO_TUI_SMOKE_TIMEOUT"
SMOKE_WATCHDOG_GRACE_SECONDS = 0.2


def _write_smoke_marker(marker: str, smoke_out: Optional[str] = None):
    """Write smoke marker to file or stdout."""
    print(marker)  # Always print to stdout
    if smoke_out:
        try:
            with open(smoke_out, "w") as f:
                f.write(marker)
        except Exception:
            # If file write fails, just continue
            pass


def write_smoke_success(smoke_out: Optional[str] = None):
    """Write smoke success marker to file or stdout"""
    _write_smoke_marker(SMOKE_OK_MARKER, smoke_out)


def write_smoke_timeout(smoke_out: Optional[str] = None):
    """Write smoke timeout marker to file or stdout"""
    _write_smoke_marker(SMOKE_TIMEOUT_MARKER, smoke_out)


class SmokeMode:
    def __init__(
        self,
        enabled: bool = False,
        seconds: float = 0.5,
        success_file: Optional[str] = None,
        watchdog_grace: float = SMOKE_WATCHDOG_GRACE_SECONDS,
    ):
        self.enabled = enabled
        self.seconds = seconds
        self.success_file = success_file
        self.watchdog_grace = watchdog_grace
        self.start_time: Optional[float] = None
        self.should_exit_flag = False
    
    def start(self, stdscr):
        """Start smoke mode (for curses apps)"""
        if self.enabled:
            self.start_time = time.time()

    def should_exit(self, now: Optional[float] = None) -> bool:
        """Check if smoke mode says we should exit"""
        if not self.enabled:
            return False
        now = time.time() if now is None else now
        return self.should_exit_flag or (self.start_time and now - self.start_time >= self.seconds)

    def timed_out(self, now: Optional[float] = None) -> bool:
        """Return True if watchdog grace period has elapsed."""
        if not self.enabled or not self.start_time:
            return False
        now = time.time() if now is None else now
        return now - self.start_time >= self.seconds + self.watchdog_grace

    def time_until_exit(self, now: Optional[float] = None) -> Optional[float]:
        """Return seconds remaining until smoke exit, else None."""
        if not self.enabled or not self.start_time:
            return None
        now = time.time() if now is None else now
        return max(0.0, self.seconds - (now - self.start_time))

"""Repository locking mechanism for discuss sessions.

Provides simple file-based locking to prevent concurrent mutatative discuss sessions.
This is NOT a full cross-process semaphore, just an "idiot-proof" basic lock.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class LockInfo:
    """Information about a repository lock."""
    session_id: str
    pid: int
    timestamp: str
    hostname: Optional[str] = None


class RepoLock:
    """Simple file-based repository lock for discuss sessions."""

    def __init__(self, lock_dir: Optional[Path] = None):
        """Initialize repo lock manager.

        Args:
            lock_dir: Directory to store lock files (default: docs/maestro/locks)
        """
        self.lock_dir = lock_dir or Path("docs/maestro/locks")
        self.lock_file = self.lock_dir / "repo.lock"

    def acquire(self, session_id: str) -> None:
        """Acquire the repository lock.

        Args:
            session_id: Session ID requesting the lock

        Raises:
            RuntimeError: If lock is already held by another session
        """
        # Create lock directory if it doesn't exist
        self.lock_dir.mkdir(parents=True, exist_ok=True)

        # Check if lock exists
        if self.lock_file.exists():
            # Read existing lock
            existing_lock = self._read_lock()
            if existing_lock:
                # Check if the lock is stale (process no longer exists)
                if not self._is_process_running(existing_lock.pid):
                    # Remove stale lock
                    self.lock_file.unlink()
                else:
                    # Lock is held by another active session
                    raise RuntimeError(
                        f"Repository is locked by session {existing_lock.session_id} "
                        f"(PID {existing_lock.pid}, started {existing_lock.timestamp}). "
                        f"Close that session before starting a new one."
                    )

        # Create new lock
        lock_info = LockInfo(
            session_id=session_id,
            pid=os.getpid(),
            timestamp=datetime.now().isoformat(),
            hostname=self._get_hostname()
        )
        self._write_lock(lock_info)

    def release(self, session_id: Optional[str] = None) -> None:
        """Release the repository lock.

        Args:
            session_id: Session ID releasing the lock (optional, for validation)
        """
        if not self.lock_file.exists():
            return

        # If session_id provided, verify it matches
        if session_id:
            existing_lock = self._read_lock()
            if existing_lock and existing_lock.session_id != session_id:
                # Don't release someone else's lock
                return

        # Remove lock file
        self.lock_file.unlink()

    def is_locked(self) -> bool:
        """Check if repository is currently locked.

        Returns:
            True if locked by an active session, False otherwise
        """
        if not self.lock_file.exists():
            return False

        existing_lock = self._read_lock()
        if not existing_lock:
            return False

        # Check if process is still running
        if not self._is_process_running(existing_lock.pid):
            # Stale lock
            return False

        return True

    def get_lock_info(self) -> Optional[LockInfo]:
        """Get information about the current lock.

        Returns:
            LockInfo if locked, None otherwise
        """
        if not self.lock_file.exists():
            return None
        return self._read_lock()

    def _read_lock(self) -> Optional[LockInfo]:
        """Read lock info from lock file."""
        try:
            with open(self.lock_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return LockInfo(**data)
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            return None

    def _write_lock(self, lock_info: LockInfo) -> None:
        """Write lock info to lock file."""
        lock_data = {
            "session_id": lock_info.session_id,
            "pid": lock_info.pid,
            "timestamp": lock_info.timestamp
        }
        if lock_info.hostname:
            lock_data["hostname"] = lock_info.hostname

        with open(self.lock_file, 'w', encoding='utf-8') as f:
            json.dump(lock_data, f, indent=2)

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running."""
        try:
            # Send signal 0 to check if process exists
            # This doesn't actually send a signal, just checks existence
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _get_hostname(self) -> Optional[str]:
        """Get the current hostname."""
        try:
            import socket
            return socket.gethostname()
        except Exception:
            return None

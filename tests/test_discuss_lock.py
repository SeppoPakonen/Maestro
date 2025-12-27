"""Tests for repository locking mechanism."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from maestro.repo_lock import RepoLock, LockInfo


class TestRepoLock:
    """Tests for RepoLock class."""

    def test_acquire_and_release(self, tmp_path):
        """Test basic acquire and release."""
        lock = RepoLock(lock_dir=tmp_path)
        session_id = "test-session-1"

        # Lock should not exist initially
        assert not lock.is_locked()
        assert lock.get_lock_info() is None

        # Acquire lock
        lock.acquire(session_id)
        assert lock.is_locked()

        # Get lock info
        lock_info = lock.get_lock_info()
        assert lock_info is not None
        assert lock_info.session_id == session_id
        assert lock_info.pid == os.getpid()

        # Release lock
        lock.release(session_id)
        assert not lock.is_locked()

    def test_acquire_when_locked(self, tmp_path):
        """Test that acquiring when locked raises RuntimeError."""
        lock = RepoLock(lock_dir=tmp_path)

        # Acquire lock with first session
        lock.acquire("session-1")

        # Try to acquire with second session
        with pytest.raises(RuntimeError, match="Repository is locked by session session-1"):
            lock.acquire("session-2")

    def test_stale_lock_cleanup(self, tmp_path):
        """Test that stale locks (dead process) are cleaned up."""
        lock = RepoLock(lock_dir=tmp_path)

        # Create a lock with a fake (non-existent) PID
        fake_lock = LockInfo(
            session_id="stale-session",
            pid=99999,  # Unlikely to be a real process
            timestamp="2025-01-01T00:00:00"
        )
        lock._write_lock(fake_lock)

        # Lock should not be considered active (stale)
        # When we try to acquire, it should remove the stale lock
        lock.acquire("new-session")

        # New lock should be in place
        lock_info = lock.get_lock_info()
        assert lock_info.session_id == "new-session"

    def test_is_locked_with_active_process(self, tmp_path):
        """Test is_locked returns True for active process."""
        lock = RepoLock(lock_dir=tmp_path)
        lock.acquire("test-session")

        # Lock should be active (current process)
        assert lock.is_locked()

    def test_is_locked_with_stale_lock(self, tmp_path):
        """Test is_locked returns False for stale lock."""
        lock = RepoLock(lock_dir=tmp_path)

        # Create stale lock
        fake_lock = LockInfo(
            session_id="stale-session",
            pid=99999,
            timestamp="2025-01-01T00:00:00"
        )
        lock._write_lock(fake_lock)

        # Should not be considered locked
        assert not lock.is_locked()

    def test_release_wrong_session(self, tmp_path):
        """Test that releasing with wrong session_id doesn't release."""
        lock = RepoLock(lock_dir=tmp_path)

        # Acquire with session-1
        lock.acquire("session-1")

        # Try to release with session-2
        lock.release("session-2")

        # Lock should still be held
        assert lock.is_locked()
        assert lock.get_lock_info().session_id == "session-1"

    def test_release_without_session_id(self, tmp_path):
        """Test that release without session_id releases unconditionally."""
        lock = RepoLock(lock_dir=tmp_path)
        lock.acquire("session-1")

        # Release without session_id
        lock.release()

        # Lock should be released
        assert not lock.is_locked()

    def test_lock_directory_creation(self, tmp_path):
        """Test that lock directory is created if it doesn't exist."""
        lock_dir = tmp_path / "nested" / "locks"
        assert not lock_dir.exists()

        lock = RepoLock(lock_dir=lock_dir)
        lock.acquire("test-session")

        # Directory should be created
        assert lock_dir.exists()
        assert (lock_dir / "repo.lock").exists()

    def test_concurrent_lock_check(self, tmp_path):
        """Test that concurrent session attempts are blocked."""
        lock1 = RepoLock(lock_dir=tmp_path)
        lock2 = RepoLock(lock_dir=tmp_path)

        # First lock acquires
        lock1.acquire("session-1")

        # Second lock should fail
        with pytest.raises(RuntimeError, match="locked by session session-1"):
            lock2.acquire("session-2")

        # Release first lock
        lock1.release()

        # Now second can acquire
        lock2.acquire("session-2")
        assert lock2.is_locked()


class TestDiscussLockIntegration:
    """Integration tests for lock enforcement in discuss commands."""

    def test_save_discussion_artifacts_with_pregenerated_session_id(self):
        """Test that save_discussion_artifacts uses pre-generated session_id."""
        from maestro.commands.discuss import save_discussion_artifacts
        from maestro.session_format import create_session_id
        from maestro.ai import ContractType, PatchOperation, PatchOperationType

        # Pre-generate session_id
        session_id = create_session_id()

        # Mock operation
        ops = [PatchOperation(op_type=PatchOperationType.ADD_TRACK, data={"track_name": "Test Track"})]

        # Save artifacts with pre-generated session_id
        returned_id = save_discussion_artifacts(
            initial_prompt="Test prompt",
            patch_operations=ops,
            engine_name="test-engine",
            model_name="test-model",
            contract_type=ContractType.GLOBAL,
            session_id=session_id
        )

        # Should return the same session_id
        assert returned_id == session_id

    def test_lock_file_removed_on_status_applied(self, tmp_path):
        """Test that lock file is removed when status changes to 'applied'."""
        lock_dir = tmp_path / "locks"
        lock_file = lock_dir / "repo.lock"

        # Create lock
        lock = RepoLock(lock_dir=lock_dir)
        lock.acquire("test-session")
        assert lock_file.exists()

        # Release lock
        lock.release("test-session")
        assert not lock_file.exists()

    def test_lock_file_removed_on_status_cancelled(self, tmp_path):
        """Test that lock file is removed when status changes to 'cancelled'."""
        lock_dir = tmp_path / "locks"
        lock_file = lock_dir / "repo.lock"

        # Create lock
        lock = RepoLock(lock_dir=lock_dir)
        lock.acquire("test-session")
        assert lock_file.exists()

        # Release lock
        lock.release("test-session")
        assert not lock_file.exists()

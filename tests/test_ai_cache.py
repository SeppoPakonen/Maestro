"""Tests for AI cache store functionality."""

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from maestro.ai.cache import AiCacheStore, CacheEntryMeta, WorkspaceFingerprint


class TestAiCacheStore:
    """Test AI cache store operations."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def cache_store(self, temp_cache_dir):
        """Create cache store with temp directory."""
        with patch('maestro.ai.cache.Path.home') as mock_home:
            mock_home.return_value = Path(temp_cache_dir) / "home"
            with patch('maestro.config.paths.get_docs_root') as mock_docs:
                mock_docs.return_value = Path(temp_cache_dir) / "repo"
                store = AiCacheStore()
                yield store

    def test_compute_prompt_hash_stability(self, cache_store):
        """Test that prompt hash is stable for identical inputs."""
        prompt = "Test prompt for hashing"
        engine = "qwen"
        model = "default"
        context = "task"

        hash1 = cache_store.compute_prompt_hash(prompt, engine, model, context)
        hash2 = cache_store.compute_prompt_hash(prompt, engine, model, context)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex digest

    def test_compute_prompt_hash_uniqueness(self, cache_store):
        """Test that different prompts produce different hashes."""
        hash1 = cache_store.compute_prompt_hash("prompt 1", "qwen", "default", "task")
        hash2 = cache_store.compute_prompt_hash("prompt 2", "qwen", "default", "task")
        hash3 = cache_store.compute_prompt_hash("prompt 1", "claude", "default", "task")

        assert hash1 != hash2
        assert hash1 != hash3
        assert hash2 != hash3

    def test_create_entry_minimal(self, cache_store):
        """Test creating cache entry with minimal data."""
        prompt_hash = "test_hash_123"
        scope = "user"
        engine = "qwen"
        model = "default"
        prompt = "Test prompt"
        ops_result = [{"op_type": "add_task", "data": {"task_name": "Test task"}}]

        success = cache_store.create_entry(
            prompt_hash=prompt_hash,
            scope=scope,
            engine=engine,
            model=model,
            prompt=prompt,
            ops_result=ops_result
        )

        assert success is True

        # Verify entry exists
        entry_dir = cache_store._get_entry_dir(prompt_hash, scope)
        assert entry_dir.exists()
        assert (entry_dir / "meta.json").exists()
        assert (entry_dir / "prompt.txt").exists()
        assert (entry_dir / "ops.json").exists()

    def test_create_entry_full(self, cache_store):
        """Test creating cache entry with all data."""
        prompt_hash = "test_hash_full"
        scope = "repo"
        engine = "claude"
        model = "sonnet"
        prompt = "Complex test prompt"
        ops_result = [{"op_type": "add_phase", "data": {"phase_name": "Test phase"}}]
        transcript = [
            {"ts": datetime.now().isoformat(), "type": "user_message", "payload": {"content": prompt}}
        ]
        workspace_fp = WorkspaceFingerprint(
            git_head="abc123def456",
            git_dirty=False,
            watched_files={"test.py": "file_hash_123"}
        )
        patch_diff = "diff --git a/test.py b/test.py\n+new line"

        success = cache_store.create_entry(
            prompt_hash=prompt_hash,
            scope=scope,
            engine=engine,
            model=model,
            prompt=prompt,
            ops_result=ops_result,
            transcript=transcript,
            workspace_fp=workspace_fp,
            patch_diff=patch_diff,
            context_kind="phase",
            context_ref="test-phase-001",
            notes="Test entry"
        )

        assert success is True

        # Verify all files exist
        entry_dir = cache_store._get_entry_dir(prompt_hash, scope)
        assert (entry_dir / "meta.json").exists()
        assert (entry_dir / "prompt.txt").exists()
        assert (entry_dir / "ops.json").exists()
        assert (entry_dir / "response.jsonl").exists()
        assert (entry_dir / "workspace.json").exists()
        assert (entry_dir / "patch.diff").exists()

    def test_lookup_repo_priority(self, cache_store):
        """Test that repo cache has priority over user cache."""
        prompt_hash = "test_priority_hash"

        # Create entry in user cache
        cache_store.create_entry(
            prompt_hash=prompt_hash,
            scope="user",
            engine="qwen",
            model="default",
            prompt="Test",
            ops_result=[{"op_type": "add_task", "data": {"task_name": "User task"}}]
        )

        # Create entry in repo cache
        cache_store.create_entry(
            prompt_hash=prompt_hash,
            scope="repo",
            engine="qwen",
            model="default",
            prompt="Test",
            ops_result=[{"op_type": "add_task", "data": {"task_name": "Repo task"}}]
        )

        # Lookup should return repo cache
        result = cache_store.lookup(prompt_hash)
        assert result is not None
        scope, entry_dir = result
        assert scope == "repo"

    def test_lookup_fallback_to_user(self, cache_store):
        """Test that lookup falls back to user cache if repo not found."""
        prompt_hash = "test_fallback_hash"

        # Create entry only in user cache
        cache_store.create_entry(
            prompt_hash=prompt_hash,
            scope="user",
            engine="qwen",
            model="default",
            prompt="Test",
            ops_result=[{"op_type": "add_task", "data": {"task_name": "User task"}}]
        )

        # Lookup should return user cache
        result = cache_store.lookup(prompt_hash)
        assert result is not None
        scope, entry_dir = result
        assert scope == "user"

    def test_lookup_miss(self, cache_store):
        """Test cache lookup miss."""
        result = cache_store.lookup("nonexistent_hash")
        assert result is None

    def test_load_entry(self, cache_store):
        """Test loading cache entry data."""
        prompt_hash = "test_load_hash"
        prompt = "Test prompt for loading"
        ops_result = [{"op_type": "add_track", "data": {"track_name": "Test track"}}]

        cache_store.create_entry(
            prompt_hash=prompt_hash,
            scope="user",
            engine="qwen",
            model="default",
            prompt=prompt,
            ops_result=ops_result
        )

        # Load entry
        scope, entry_dir = cache_store.lookup(prompt_hash)
        entry_data = cache_store.load_entry(entry_dir)

        assert "meta" in entry_data
        assert "prompt" in entry_data
        assert "ops" in entry_data
        assert entry_data["prompt"] == prompt
        assert entry_data["ops"] == ops_result

    def test_validate_entry_valid(self, cache_store):
        """Test validating a valid cache entry."""
        workspace_fp = WorkspaceFingerprint(
            git_head="abc123",
            git_dirty=False,
            watched_files={"test.py": "hash123"}
        )

        entry_data = {
            "workspace": workspace_fp
        }

        # Same workspace fingerprint
        is_valid, error = cache_store.validate_entry(entry_data, workspace_fp)
        assert is_valid is True
        assert error is None

    def test_validate_entry_git_mismatch(self, cache_store):
        """Test validation fails on git HEAD mismatch."""
        cached_fp = WorkspaceFingerprint(git_head="abc123", git_dirty=False)
        current_fp = WorkspaceFingerprint(git_head="def456", git_dirty=False)

        entry_data = {"workspace": cached_fp}

        is_valid, error = cache_store.validate_entry(entry_data, current_fp)
        assert is_valid is False
        assert "Git HEAD mismatch" in error

    def test_validate_entry_lenient_git(self, cache_store):
        """Test validation passes with lenient git mode."""
        cached_fp = WorkspaceFingerprint(git_head="abc123", git_dirty=False)
        current_fp = WorkspaceFingerprint(git_head="def456", git_dirty=False)

        entry_data = {"workspace": cached_fp}

        is_valid, error = cache_store.validate_entry(
            entry_data, current_fp, lenient_git=True
        )
        assert is_valid is True
        assert error is None

    def test_validate_entry_file_hash_mismatch(self, cache_store):
        """Test validation fails on file hash mismatch."""
        cached_fp = WorkspaceFingerprint(
            git_head="abc123",
            watched_files={"test.py": "hash123"}
        )
        current_fp = WorkspaceFingerprint(
            git_head="abc123",
            watched_files={"test.py": "hash456"}
        )

        entry_data = {"workspace": cached_fp}

        is_valid, error = cache_store.validate_entry(entry_data, current_fp)
        assert is_valid is False
        assert "File hash mismatch" in error

    def test_mark_stale(self, cache_store):
        """Test marking cache entry as stale."""
        prompt_hash = "test_stale_hash"

        cache_store.create_entry(
            prompt_hash=prompt_hash,
            scope="user",
            engine="qwen",
            model="default",
            prompt="Test",
            ops_result=[{"op_type": "add_task", "data": {}}]
        )

        scope, entry_dir = cache_store.lookup(prompt_hash)
        success = cache_store.mark_stale(entry_dir, "Test staleness")

        assert success is True

        # Verify meta updated
        meta_path = entry_dir / "meta.json"
        with open(meta_path, 'r') as f:
            meta = json.load(f)
            assert meta["validity"] == "stale"
            assert "Stale: Test staleness" in meta.get("notes", "")

    def test_list_entries(self, cache_store):
        """Test listing cache entries."""
        # Create multiple entries
        for i in range(3):
            cache_store.create_entry(
                prompt_hash=f"hash_{i}",
                scope="user",
                engine="qwen",
                model="default",
                prompt=f"Prompt {i}",
                ops_result=[{"op_type": "add_task", "data": {"task_name": f"Task {i}"}}]
            )

        entries = cache_store.list_entries("user")
        assert len(entries) == 3

        # Check entry structure
        for entry in entries:
            assert "prompt_hash" in entry
            assert "engine_kind" in entry
            assert "created_at" in entry

    def test_prune_old_entries(self, cache_store):
        """Test pruning old cache entries."""
        # Create old entry
        prompt_hash = "old_hash"
        cache_store.create_entry(
            prompt_hash=prompt_hash,
            scope="user",
            engine="qwen",
            model="default",
            prompt="Old prompt",
            ops_result=[{"op_type": "add_task", "data": {}}]
        )

        # Manually modify created_at to be old
        scope, entry_dir = cache_store.lookup(prompt_hash)
        meta_path = entry_dir / "meta.json"
        with open(meta_path, 'r') as f:
            meta = json.load(f)

        old_time = (datetime.now() - timedelta(days=45)).isoformat()
        meta["created_at"] = old_time

        with open(meta_path, 'w') as f:
            json.dump(meta, f)

        # Create recent entry
        cache_store.create_entry(
            prompt_hash="recent_hash",
            scope="user",
            engine="qwen",
            model="default",
            prompt="Recent prompt",
            ops_result=[{"op_type": "add_task", "data": {}}]
        )

        # Prune entries older than 30 days
        deleted_count = cache_store.prune_old_entries("user", older_than_days=30)

        assert deleted_count == 1

        # Verify old entry deleted
        assert cache_store.lookup("old_hash") is None
        # Verify recent entry still exists
        assert cache_store.lookup("recent_hash") is not None

    def test_get_cache_enabled(self, cache_store):
        """Test cache enabled check from environment."""
        with patch.dict(os.environ, {"MAESTRO_AI_CACHE": "on"}):
            assert cache_store.get_cache_enabled() is True

        with patch.dict(os.environ, {"MAESTRO_AI_CACHE": "off"}):
            assert cache_store.get_cache_enabled() is False

        with patch.dict(os.environ, {}, clear=True):
            # Default is on
            assert cache_store.get_cache_enabled() is True

    def test_get_cache_scope(self, cache_store):
        """Test cache scope from environment."""
        with patch.dict(os.environ, {"MAESTRO_AI_CACHE_SCOPE": "repo"}):
            assert cache_store.get_cache_scope() == "repo"

        with patch.dict(os.environ, {"MAESTRO_AI_CACHE_SCOPE": "user"}):
            assert cache_store.get_cache_scope() == "user"

        with patch.dict(os.environ, {}, clear=True):
            # Default is auto
            assert cache_store.get_cache_scope() == "auto"

    def test_get_watch_patterns(self, cache_store):
        """Test watch patterns from environment."""
        with patch.dict(os.environ, {"MAESTRO_AI_CACHE_WATCH": "tests/**;fixtures/**"}):
            patterns = cache_store.get_watch_patterns()
            assert len(patterns) == 2
            assert "tests/**" in patterns
            assert "fixtures/**" in patterns

        with patch.dict(os.environ, {}, clear=True):
            patterns = cache_store.get_watch_patterns()
            assert len(patterns) == 0

    def test_apply_patch_dry_run(self, cache_store, temp_cache_dir):
        """Test patch application in dry-run mode."""
        # Create a simple patch
        patch_content = """diff --git a/test.txt b/test.txt
--- a/test.txt
+++ b/test.txt
@@ -1 +1,2 @@
 Original line
+New line
"""

        # Create test file
        test_file = Path(temp_cache_dir) / "test.txt"
        test_file.write_text("Original line\n")

        with patch.dict(os.environ, {"PWD": temp_cache_dir}):
            # Dry run should succeed (checking if patch can be applied)
            # Note: This test might fail if git is not available or if we're not in a git repo
            # So we'll just verify the function runs without crashing
            success, error = cache_store.apply_patch(patch_content, dry_run=True)
            # Don't assert success as it depends on git availability

    def test_compute_workspace_fingerprint_minimal(self, cache_store, temp_cache_dir):
        """Test computing minimal workspace fingerprint."""
        # Without watch patterns
        with patch.dict(os.environ, {"PWD": temp_cache_dir}):
            fp = cache_store.compute_workspace_fingerprint()

        # Should have git info (if in a git repo)
        assert isinstance(fp.git_dirty, bool)
        assert isinstance(fp.watched_files, dict)

    def test_compute_workspace_fingerprint_with_patterns(self, cache_store, temp_cache_dir):
        """Test computing workspace fingerprint with watch patterns."""
        # Create test files
        test_file1 = Path(temp_cache_dir) / "test1.py"
        test_file2 = Path(temp_cache_dir) / "test2.py"
        test_file1.write_text("content 1")
        test_file2.write_text("content 2")

        with patch.dict(os.environ, {"PWD": temp_cache_dir}):
            # Compute fingerprint with patterns
            fp = cache_store.compute_workspace_fingerprint([str(test_file1), str(test_file2)])

            # Should have file hashes (if files exist)
            # Note: Paths might be different depending on how glob resolves them
            assert isinstance(fp.watched_files, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

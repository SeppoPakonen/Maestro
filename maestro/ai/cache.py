"""AI Cache Store for Maestro.

This module implements a pragmatic caching layer that can:
- Reuse prior AI results for identical inputs
- Optionally apply deterministic patches without re-calling the AI
- Support deterministic test runs via repo-local cache
- Remain safe via workspace fingerprint + file hashes + RepoLock

Storage layout:
- User cache: $HOME/.maestro/cache/ai/entries/<prompt_hash>/
- Repo cache: docs/maestro/cache/ai/entries/<prompt_hash>/

Each cache entry contains:
- meta.json: Metadata (engine, created_at, validity, etc.)
- prompt.txt: Original prompt text
- response.jsonl: Raw stream-json transcript (if available)
- ops.json: Parsed ops / final JSON contract result
- workspace.json: Fingerprint + file hashes snapshot
- patch.diff: Optional git diff (only if computed)
"""

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from maestro.config.paths import get_docs_root


@dataclass
class CacheEntryMeta:
    """Metadata for a cache entry."""
    engine_kind: str  # qwen/claude/codex/gemini
    model: str  # Model identifier
    created_at: str
    prompt_hash: str
    cache_scope: str  # user | repo
    apply_mode: str  # ops_only | patch | both
    validity: str  # ok | stale | rejected
    notes: Optional[str] = None
    context_kind: Optional[str] = None  # task/phase/track/repo/global
    context_ref: Optional[str] = None  # ID of the entity
    contract_type: Optional[str] = None  # Contract type used


@dataclass
class WorkspaceFingerprint:
    """Workspace state fingerprint for cache validation."""
    git_head: Optional[str] = None
    git_dirty: bool = False
    watched_files: Dict[str, str] = field(default_factory=dict)  # path -> sha256


class AiCacheStore:
    """Manages AI cache entries with dual-scope storage (user + repo)."""

    def __init__(self):
        """Initialize cache store with user and repo cache paths."""
        # User cache: $HOME/.maestro/cache/ai/
        home = Path.home()
        self.user_cache_root = home / ".maestro" / "cache" / "ai" / "entries"
        self.user_cache_root.mkdir(parents=True, exist_ok=True)

        # Repo cache: docs/maestro/cache/ai/
        docs_root = get_docs_root()
        self.repo_cache_root = docs_root / "docs" / "maestro" / "cache" / "ai" / "entries"
        # Don't auto-create repo cache (only when explicitly storing)

    def _get_cache_root(self, scope: str) -> Path:
        """Get the cache root for a specific scope."""
        if scope == "repo":
            return self.repo_cache_root
        elif scope == "user":
            return self.user_cache_root
        else:
            raise ValueError(f"Invalid cache scope: {scope}")

    def _get_entry_dir(self, prompt_hash: str, scope: str) -> Path:
        """Get the directory path for a cache entry."""
        cache_root = self._get_cache_root(scope)
        return cache_root / prompt_hash

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        if not file_path.exists():
            return ""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def compute_workspace_fingerprint(
        self,
        watched_paths: Optional[List[str]] = None
    ) -> WorkspaceFingerprint:
        """Compute workspace fingerprint with git state + file hashes.

        Args:
            watched_paths: Optional list of glob patterns to watch.
                          If None, uses minimal fingerprint (git HEAD + dirty flag).

        Returns:
            WorkspaceFingerprint with git state and file hashes
        """
        fingerprint = WorkspaceFingerprint()

        # Get git HEAD
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if result.returncode == 0:
                fingerprint.git_head = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Check if working directory is dirty
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if result.returncode == 0:
                fingerprint.git_dirty = bool(result.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Compute file hashes for watched paths
        if watched_paths:
            from glob import glob
            for pattern in watched_paths:
                for file_path_str in glob(pattern, recursive=True):
                    file_path = Path(file_path_str)
                    if file_path.is_file():
                        file_hash = self._compute_file_hash(file_path)
                        if file_hash:
                            # Use relative path from current dir
                            rel_path = str(file_path.relative_to(Path.cwd()))
                            fingerprint.watched_files[rel_path] = file_hash

        return fingerprint

    def compute_prompt_hash(
        self,
        prompt: str,
        engine: str,
        model: str,
        context_kind: str = "global",
        inputs_signature: Optional[Dict[str, str]] = None
    ) -> str:
        """Compute stable SHA256 hash of prompt and metadata.

        Args:
            prompt: Normalized prompt text
            engine: Engine identifier (qwen/claude/codex/gemini)
            model: Model selector string
            context_kind: Context kind (task/phase/track/repo/global)
            inputs_signature: Optional dict of input_file_path -> content_hash

        Returns:
            SHA256 hex digest
        """
        canonical = {
            "prompt": prompt.strip(),
            "engine": engine,
            "model": model,
            "context_kind": context_kind
        }

        if inputs_signature:
            canonical["inputs"] = inputs_signature

        # Deterministic JSON serialization
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    def create_entry(
        self,
        prompt_hash: str,
        scope: str,
        engine: str,
        model: str,
        prompt: str,
        ops_result: Any,
        transcript: Optional[List[Dict[str, Any]]] = None,
        workspace_fp: Optional[WorkspaceFingerprint] = None,
        patch_diff: Optional[str] = None,
        context_kind: Optional[str] = None,
        context_ref: Optional[str] = None,
        contract_type: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Create a new cache entry.

        Args:
            prompt_hash: SHA256 hash of the prompt
            scope: Cache scope (user or repo)
            engine: Engine kind
            model: Model identifier
            prompt: Original prompt text
            ops_result: Parsed ops / final JSON contract result
            transcript: Optional raw stream-json transcript
            workspace_fp: Optional workspace fingerprint
            patch_diff: Optional git diff
            context_kind: Optional context kind
            context_ref: Optional context ref
            contract_type: Optional contract type
            notes: Optional notes

        Returns:
            True if entry created successfully
        """
        entry_dir = self._get_entry_dir(prompt_hash, scope)
        entry_dir.mkdir(parents=True, exist_ok=True)

        # Determine apply_mode based on what's available
        apply_mode = "ops_only"
        if patch_diff:
            apply_mode = "both" if ops_result else "patch"

        # Create metadata
        meta = CacheEntryMeta(
            engine_kind=engine,
            model=model,
            created_at=datetime.now().isoformat(),
            prompt_hash=prompt_hash,
            cache_scope=scope,
            apply_mode=apply_mode,
            validity="ok",
            notes=notes,
            context_kind=context_kind,
            context_ref=context_ref,
            contract_type=contract_type
        )

        # Write meta.json
        meta_path = entry_dir / "meta.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            meta_dict = {
                "engine_kind": meta.engine_kind,
                "model": meta.model,
                "created_at": meta.created_at,
                "prompt_hash": meta.prompt_hash,
                "cache_scope": meta.cache_scope,
                "apply_mode": meta.apply_mode,
                "validity": meta.validity,
                "notes": meta.notes,
                "context_kind": meta.context_kind,
                "context_ref": meta.context_ref,
                "contract_type": meta.contract_type
            }
            json.dump(meta_dict, f, indent=2)

        # Write prompt.txt
        prompt_path = entry_dir / "prompt.txt"
        prompt_path.write_text(prompt, encoding='utf-8')

        # Write ops.json
        if ops_result:
            ops_path = entry_dir / "ops.json"
            with open(ops_path, 'w', encoding='utf-8') as f:
                json.dump(ops_result, f, indent=2)

        # Write response.jsonl (transcript)
        if transcript:
            transcript_path = entry_dir / "response.jsonl"
            with open(transcript_path, 'w', encoding='utf-8') as f:
                for event in transcript:
                    f.write(json.dumps(event) + '\n')

        # Write workspace.json
        if workspace_fp:
            workspace_path = entry_dir / "workspace.json"
            workspace_dict = {
                "git_head": workspace_fp.git_head,
                "git_dirty": workspace_fp.git_dirty,
                "watched_files": workspace_fp.watched_files
            }
            with open(workspace_path, 'w', encoding='utf-8') as f:
                json.dump(workspace_dict, f, indent=2)

        # Write patch.diff
        if patch_diff:
            patch_path = entry_dir / "patch.diff"
            patch_path.write_text(patch_diff, encoding='utf-8')

        return True

    def lookup(self, prompt_hash: str) -> Optional[Tuple[str, Path]]:
        """Look up a cache entry by prompt hash.

        Lookup order:
        1. Repo cache (if exists)
        2. User cache

        Args:
            prompt_hash: SHA256 hash of the prompt

        Returns:
            Tuple of (scope, entry_dir) if found, None otherwise
        """
        # Check repo cache first
        repo_entry_dir = self._get_entry_dir(prompt_hash, "repo")
        if repo_entry_dir.exists() and (repo_entry_dir / "meta.json").exists():
            return ("repo", repo_entry_dir)

        # Check user cache
        user_entry_dir = self._get_entry_dir(prompt_hash, "user")
        if user_entry_dir.exists() and (user_entry_dir / "meta.json").exists():
            return ("user", user_entry_dir)

        return None

    def load_entry(self, entry_dir: Path) -> Dict[str, Any]:
        """Load a cache entry from disk.

        Args:
            entry_dir: Path to cache entry directory

        Returns:
            Dict with cache entry data (meta, ops, workspace, etc.)
        """
        result = {}

        # Load meta.json
        meta_path = entry_dir / "meta.json"
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as f:
                result["meta"] = json.load(f)

        # Load prompt.txt
        prompt_path = entry_dir / "prompt.txt"
        if prompt_path.exists():
            result["prompt"] = prompt_path.read_text(encoding='utf-8')

        # Load ops.json
        ops_path = entry_dir / "ops.json"
        if ops_path.exists():
            with open(ops_path, 'r', encoding='utf-8') as f:
                result["ops"] = json.load(f)

        # Load workspace.json
        workspace_path = entry_dir / "workspace.json"
        if workspace_path.exists():
            with open(workspace_path, 'r', encoding='utf-8') as f:
                workspace_dict = json.load(f)
                result["workspace"] = WorkspaceFingerprint(
                    git_head=workspace_dict.get("git_head"),
                    git_dirty=workspace_dict.get("git_dirty", False),
                    watched_files=workspace_dict.get("watched_files", {})
                )

        # Load patch.diff
        patch_path = entry_dir / "patch.diff"
        if patch_path.exists():
            result["patch"] = patch_path.read_text(encoding='utf-8')

        # Load response.jsonl
        transcript_path = entry_dir / "response.jsonl"
        if transcript_path.exists():
            transcript = []
            with open(transcript_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        transcript.append(json.loads(line))
            result["transcript"] = transcript

        return result

    def validate_entry(
        self,
        entry_data: Dict[str, Any],
        current_workspace_fp: Optional[WorkspaceFingerprint] = None,
        lenient_git: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Validate a cache entry against current workspace state.

        Args:
            entry_data: Cache entry data from load_entry()
            current_workspace_fp: Current workspace fingerprint
            lenient_git: If True, allow git mismatch

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if entry has workspace fingerprint
        cached_workspace = entry_data.get("workspace")
        if not cached_workspace:
            # No workspace fingerprint recorded, assume valid
            return (True, None)

        if not current_workspace_fp:
            # No current fingerprint provided, can't validate
            return (True, None)

        # Validate git HEAD (unless lenient)
        if not lenient_git:
            if cached_workspace.git_head != current_workspace_fp.git_head:
                return (False, f"Git HEAD mismatch: cached={cached_workspace.git_head[:8]}, current={current_workspace_fp.git_head[:8] if current_workspace_fp.git_head else 'None'}")

        # Validate watched files
        for file_path, cached_hash in cached_workspace.watched_files.items():
            current_hash = current_workspace_fp.watched_files.get(file_path)
            if current_hash != cached_hash:
                return (False, f"File hash mismatch: {file_path}")

        return (True, None)

    def mark_stale(self, entry_dir: Path, reason: str) -> bool:
        """Mark a cache entry as stale.

        Args:
            entry_dir: Path to cache entry directory
            reason: Reason for staleness

        Returns:
            True if marked successfully
        """
        meta_path = entry_dir / "meta.json"
        if not meta_path.exists():
            return False

        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)

        meta["validity"] = "stale"
        if "notes" in meta and meta["notes"]:
            meta["notes"] += f" | Stale: {reason}"
        else:
            meta["notes"] = f"Stale: {reason}"

        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)

        return True

    def get_cache_enabled(self) -> bool:
        """Check if cache is enabled via environment variable.

        Returns:
            True if cache is enabled
        """
        cache_enabled = os.environ.get('MAESTRO_AI_CACHE', 'on').lower()
        return cache_enabled in ('on', 'true', '1', 'yes')

    def get_cache_scope(self) -> str:
        """Get the cache scope from environment variable.

        Returns:
            Cache scope (auto, user, or repo)
        """
        return os.environ.get('MAESTRO_AI_CACHE_SCOPE', 'auto').lower()

    def get_watch_patterns(self) -> List[str]:
        """Get watch patterns from environment variable.

        Returns:
            List of glob patterns to watch
        """
        watch_env = os.environ.get('MAESTRO_AI_CACHE_WATCH', '')
        if not watch_env:
            return []
        return [p.strip() for p in watch_env.split(';') if p.strip()]

    def list_entries(self, scope: str) -> List[Dict[str, Any]]:
        """List all cache entries in a scope.

        Args:
            scope: Cache scope (user or repo)

        Returns:
            List of cache entry metadata dicts
        """
        cache_root = self._get_cache_root(scope)
        if not cache_root.exists():
            return []

        entries = []
        for entry_dir in cache_root.iterdir():
            if not entry_dir.is_dir():
                continue

            meta_path = entry_dir / "meta.json"
            if not meta_path.exists():
                continue

            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    meta["entry_dir"] = str(entry_dir)
                    entries.append(meta)
            except (json.JSONDecodeError, KeyError):
                continue

        return entries

    def prune_old_entries(
        self,
        scope: str,
        older_than_days: int = 30
    ) -> int:
        """Prune cache entries older than specified days.

        Args:
            scope: Cache scope (user or repo)
            older_than_days: Delete entries older than this many days

        Returns:
            Number of entries deleted
        """
        from datetime import timedelta

        cache_root = self._get_cache_root(scope)
        if not cache_root.exists():
            return 0

        cutoff_time = datetime.now() - timedelta(days=older_than_days)
        deleted_count = 0

        for entry_dir in cache_root.iterdir():
            if not entry_dir.is_dir():
                continue

            meta_path = entry_dir / "meta.json"
            if not meta_path.exists():
                continue

            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    created_at_str = meta.get("created_at")
                    if not created_at_str:
                        continue

                    created_at = datetime.fromisoformat(created_at_str)
                    if created_at < cutoff_time:
                        # Delete entry directory
                        import shutil
                        shutil.rmtree(entry_dir)
                        deleted_count += 1
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        return deleted_count

    def capture_git_diff(self) -> Optional[str]:
        """Capture current git diff for patch mode.

        Returns:
            Git diff output as string, or None if git not available
        """
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def apply_patch(self, patch_diff: str, dry_run: bool = False) -> Tuple[bool, Optional[str]]:
        """Apply a patch using git apply.

        Args:
            patch_diff: Patch content to apply
            dry_run: If True, check if patch can be applied without applying

        Returns:
            Tuple of (success, error_message)
        """
        # Write patch to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
            f.write(patch_diff)
            patch_file = f.name

        try:
            # Prepare git apply command
            cmd = ["git", "apply"]
            if dry_run:
                cmd.append("--check")
            cmd.append(patch_file)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )

            if result.returncode == 0:
                return (True, None)
            else:
                return (False, result.stderr)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return (False, str(e))
        finally:
            # Clean up temp file
            try:
                os.unlink(patch_file)
            except OSError:
                pass

    def compute_patch_diff(self, before_diff: str, after_diff: str) -> str:
        """Compute the patch diff between before and after states.

        For now, this just returns the after_diff since that represents
        the changes made during the AI session.

        Args:
            before_diff: Git diff before AI execution
            after_diff: Git diff after AI execution

        Returns:
            Patch diff string
        """
        # Simple implementation: just return the after_diff
        # In a more sophisticated version, we could compute the delta
        return after_diff

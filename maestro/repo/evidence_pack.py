"""Evidence Pack - Deterministic, budgeted collection of repository evidence.

An Evidence Pack is a bounded, portable snapshot of repository context that can be:
- Generated deterministically (same repo + same rules → same pack)
- Consumed by AI for runbook resolve, plan decompose, and other workflows
- Stored and reused across multiple AI calls

Evidence includes:
- Build signatures (CMakeLists.txt, Makefile, package.json, etc.)
- Documentation samples (README, docs/**, command docs)
- CLI help output (from inferred or profile-specified binaries)

All collection respects hard budgets to keep packs bounded and AI-friendly.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class EvidenceItem:
    """A single piece of evidence in the pack."""
    kind: str  # "file", "command", "docs"
    source: str  # file path or command name
    content: str  # actual content (may be truncated)
    truncated: bool = False
    size_bytes: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> EvidenceItem:
        """Load from dictionary."""
        return cls(**data)


@dataclass
class EvidencePackMeta:
    """Metadata about an evidence pack."""
    pack_id: str
    repo_root: str
    created_at: str  # ISO 8601
    profile_hash: Optional[str] = None  # Hash of profile used (if any)
    evidence_count: int = 0
    total_bytes: int = 0
    budget_applied: Dict[str, int] = field(default_factory=dict)
    truncated_items: List[str] = field(default_factory=list)  # Sources that were truncated
    skipped_items: List[str] = field(default_factory=list)  # Items skipped due to budget

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> EvidencePackMeta:
        """Load from dictionary."""
        return cls(**data)


@dataclass
class EvidencePack:
    """Complete evidence pack with metadata and items."""
    meta: EvidencePackMeta
    items: List[EvidenceItem] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "meta": self.meta.to_dict(),
            "items": [item.to_dict() for item in self.items]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> EvidencePack:
        """Load from dictionary."""
        meta = EvidencePackMeta.from_dict(data["meta"])
        items = [EvidenceItem.from_dict(item) for item in data.get("items", [])]
        return cls(meta=meta, items=items)


class EvidenceCollector:
    """Collects evidence from a repository with deterministic, budgeted sampling."""

    def __init__(
        self,
        repo_root: Path,
        max_files: int = 60,
        max_bytes: int = 250000,
        max_help_calls: int = 6,
        timeout_seconds: int = 5,
        prefer_dirs: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ):
        """
        Initialize evidence collector.

        Args:
            repo_root: Root directory of the repository
            max_files: Maximum number of evidence items to collect
            max_bytes: Maximum total bytes across all evidence
            max_help_calls: Maximum number of CLI help commands to run
            timeout_seconds: Timeout for CLI help commands
            prefer_dirs: Preferred directories to sample from (e.g., ["docs/commands"])
            exclude_patterns: Patterns to exclude (e.g., ["*.pyc", "node_modules"])
        """
        self.repo_root = repo_root
        self.max_files = max_files
        self.max_bytes = max_bytes
        self.max_help_calls = max_help_calls
        self.timeout_seconds = timeout_seconds
        self.prefer_dirs = prefer_dirs or []
        self.exclude_patterns = exclude_patterns or []

        self.items: List[EvidenceItem] = []
        self.total_bytes = 0
        self.files_processed = 0
        self.help_calls_made = 0
        self.truncated_items: List[str] = []
        self.skipped_items: List[str] = []

    def _should_exclude(self, path: Path) -> bool:
        """Check if path matches any exclude pattern."""
        for pattern in self.exclude_patterns:
            # Simple wildcard matching (could be enhanced with fnmatch)
            if pattern.startswith("*."):
                ext = pattern[1:]
                if str(path).endswith(ext):
                    return True
            elif pattern in str(path):
                return True
        return False

    def _add_item(self, item: EvidenceItem) -> bool:
        """
        Add an evidence item if budgets allow.

        Returns:
            True if added, False if skipped due to budget
        """
        if self.files_processed >= self.max_files:
            self.skipped_items.append(item.source)
            return False

        if self.total_bytes + item.size_bytes > self.max_bytes:
            self.skipped_items.append(item.source)
            return False

        self.items.append(item)
        self.total_bytes += item.size_bytes
        self.files_processed += 1
        return True

    def _read_file_safe(self, file_path: Path, max_size: int = 10000) -> tuple[str, bool]:
        """
        Read file safely with size limit.

        Args:
            file_path: Path to file
            max_size: Maximum bytes to read

        Returns:
            Tuple of (content, was_truncated)
        """
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            if len(content) > max_size:
                self.truncated_items.append(str(file_path.relative_to(self.repo_root)))
                return content[:max_size], True
            return content, False
        except Exception:
            return "", False

    def collect_build_signatures(self):
        """Collect build system signature files (deterministic order)."""
        build_files = [
            "CMakeLists.txt", "configure.ac", "Makefile", "GNUmakefile",
            "build.sh", "build.py", "build.gradle", "build.xml",
            "package.json", "pyproject.toml", "setup.py", "setup.cfg",
            "Cargo.toml", "go.mod", "pom.xml", "composer.json",
            ".github/workflows/build.yml", ".github/workflows/ci.yml",
            ".gitlab-ci.yml", ".circleci/config.yml"
        ]

        for build_file in build_files:
            if self.files_processed >= self.max_files:
                break

            path = self.repo_root / build_file
            if path.exists() and path.is_file() and not self._should_exclude(path):
                content, truncated = self._read_file_safe(path, max_size=5000)
                if content:
                    item = EvidenceItem(
                        kind="file",
                        source=str(path.relative_to(self.repo_root)),
                        content=content,
                        truncated=truncated,
                        size_bytes=len(content)
                    )
                    self._add_item(item)

    def collect_docs(self):
        """Collect documentation files (prioritized, deterministic)."""
        # Priority 1: Root README
        readme_files = ["README.md", "README.rst", "README.txt", "README"]
        for readme in readme_files:
            if self.files_processed >= self.max_files:
                break

            path = self.repo_root / readme
            if path.exists() and path.is_file():
                content, truncated = self._read_file_safe(path, max_size=3000)
                if content:
                    item = EvidenceItem(
                        kind="docs",
                        source=str(path.relative_to(self.repo_root)),
                        content=content,
                        truncated=truncated,
                        size_bytes=len(content)
                    )
                    self._add_item(item)
                break  # Only one README

        # Priority 2: Preferred directories (from profile)
        for prefer_dir in self.prefer_dirs:
            if self.files_processed >= self.max_files:
                break

            dir_path = self.repo_root / prefer_dir
            if dir_path.exists() and dir_path.is_dir():
                self._collect_docs_from_dir(dir_path, max_depth=2)

        # Priority 3: Standard docs directories
        standard_doc_dirs = ["docs", "doc", "documentation"]
        for doc_dir in standard_doc_dirs:
            if self.files_processed >= self.max_files:
                break

            if doc_dir in self.prefer_dirs:
                continue  # Already collected

            dir_path = self.repo_root / doc_dir
            if dir_path.exists() and dir_path.is_dir():
                self._collect_docs_from_dir(dir_path, max_depth=2)

    def _collect_docs_from_dir(self, dir_path: Path, max_depth: int = 2, current_depth: int = 0):
        """Recursively collect docs from a directory with depth limit."""
        if current_depth >= max_depth:
            return

        if self.files_processed >= self.max_files:
            return

        try:
            # Get all markdown and text files, sorted for determinism
            files = sorted([
                f for f in dir_path.rglob("*.md")
                if f.is_file() and not self._should_exclude(f)
            ])

            for file_path in files:
                if self.files_processed >= self.max_files:
                    break

                content, truncated = self._read_file_safe(file_path, max_size=2000)
                if content:
                    item = EvidenceItem(
                        kind="docs",
                        source=str(file_path.relative_to(self.repo_root)),
                        content=content,
                        truncated=truncated,
                        size_bytes=len(content)
                    )
                    self._add_item(item)
        except Exception:
            pass  # Skip directories we can't access

    def collect_cli_help(self, cli_candidates: Optional[List[str]] = None):
        """
        Collect CLI help output from candidate binaries.

        Args:
            cli_candidates: List of binary paths relative to repo root
        """
        if not cli_candidates:
            # Auto-detect common binary locations
            cli_candidates = self._find_executables()

        for candidate in cli_candidates:
            if self.help_calls_made >= self.max_help_calls:
                break

            if self.files_processed >= self.max_files:
                break

            binary_path = self.repo_root / candidate
            if not binary_path.exists() or not binary_path.is_file():
                continue

            if not os.access(binary_path, os.X_OK):
                continue  # Not executable

            # Try to run --help
            try:
                result = subprocess.run(
                    [str(binary_path), "--help"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    cwd=str(self.repo_root)
                )

                help_text = result.stdout or result.stderr
                if help_text.strip():
                    # Truncate if too long
                    truncated = False
                    if len(help_text) > 3000:
                        help_text = help_text[:3000]
                        truncated = True
                        self.truncated_items.append(f"{candidate} --help")

                    item = EvidenceItem(
                        kind="command",
                        source=f"{candidate} --help",
                        content=help_text,
                        truncated=truncated,
                        size_bytes=len(help_text)
                    )
                    if self._add_item(item):
                        self.help_calls_made += 1

            except subprocess.TimeoutExpired:
                # Skip commands that timeout
                pass
            except Exception:
                # Skip binaries that fail to run
                pass

    def _find_executables(self) -> List[str]:
        """Find executable binaries in common locations (deterministic order)."""
        bin_dirs = ["bin", "build", "dist", "target/release", ".venv/bin"]
        executables = []

        for bin_dir in bin_dirs:
            bin_path = self.repo_root / bin_dir
            if not bin_path.exists() or not bin_path.is_dir():
                continue

            try:
                files = sorted([
                    f for f in bin_path.iterdir()
                    if f.is_file() and os.access(f, os.X_OK)
                ])

                for f in files[:10]:  # Max 10 per directory
                    executables.append(str(f.relative_to(self.repo_root)))
            except Exception:
                pass

        return executables

    def generate_pack_id(self, profile_hash: Optional[str] = None) -> str:
        """
        Generate deterministic pack ID based on collected evidence.

        Args:
            profile_hash: Optional hash of profile used for collection

        Returns:
            Pack ID string (e.g., "pack-abc123def456")
        """
        # Hash based on:
        # 1. Sorted list of sources
        # 2. Profile hash (if any)
        # 3. Budget parameters

        sources = sorted([item.source for item in self.items])
        budget_str = f"{self.max_files}:{self.max_bytes}:{self.max_help_calls}"

        hash_input = "\n".join(sources) + "\n" + budget_str
        if profile_hash:
            hash_input += "\n" + profile_hash

        hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        return f"pack-{hash_digest}"

    def collect_all(self, cli_candidates: Optional[List[str]] = None) -> EvidencePack:
        """
        Collect all evidence and return a complete pack.

        Args:
            cli_candidates: Optional list of CLI binaries to check

        Returns:
            Complete EvidencePack
        """
        # Collect in priority order
        self.collect_build_signatures()
        self.collect_docs()
        self.collect_cli_help(cli_candidates)

        # Generate pack ID
        pack_id = self.generate_pack_id()

        # Create metadata
        meta = EvidencePackMeta(
            pack_id=pack_id,
            repo_root=str(self.repo_root),
            created_at=datetime.now(timezone.utc).isoformat(),
            evidence_count=len(self.items),
            total_bytes=self.total_bytes,
            budget_applied={
                "max_files": self.max_files,
                "max_bytes": self.max_bytes,
                "max_help_calls": self.max_help_calls,
                "files_processed": self.files_processed,
                "help_calls_made": self.help_calls_made
            },
            truncated_items=self.truncated_items,
            skipped_items=self.skipped_items
        )

        return EvidencePack(meta=meta, items=self.items)


def save_evidence_pack(pack: EvidencePack, storage_dir: Path) -> Path:
    """
    Save evidence pack to disk.

    Args:
        pack: EvidencePack to save
        storage_dir: Base directory for evidence packs (e.g., docs/maestro/evidence_packs)

    Returns:
        Path to saved pack directory
    """
    pack_dir = storage_dir / pack.meta.pack_id
    pack_dir.mkdir(parents=True, exist_ok=True)

    # Save metadata
    meta_path = pack_dir / "meta.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(pack.meta.to_dict(), f, indent=2)

    # Save pack
    pack_path = pack_dir / "pack.json"
    with open(pack_path, 'w', encoding='utf-8') as f:
        json.dump(pack.to_dict(), f, indent=2)

    return pack_dir


def load_evidence_pack(pack_id: str, storage_dir: Path) -> Optional[EvidencePack]:
    """
    Load evidence pack from disk.

    Args:
        pack_id: Pack ID to load
        storage_dir: Base directory for evidence packs

    Returns:
        EvidencePack if found, None otherwise
    """
    pack_path = storage_dir / pack_id / "pack.json"
    if not pack_path.exists():
        return None

    try:
        with open(pack_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return EvidencePack.from_dict(data)
    except Exception:
        return None


def find_evidence_packs(storage_dir: Path) -> List[str]:
    """
    Find all evidence pack IDs in storage directory.

    Args:
        storage_dir: Base directory for evidence packs

    Returns:
        List of pack IDs
    """
    if not storage_dir.exists():
        return []

    pack_ids = []
    for item in storage_dir.iterdir():
        if item.is_dir() and (item / "pack.json").exists():
            pack_ids.append(item.name)

    return sorted(pack_ids)  # Deterministic order

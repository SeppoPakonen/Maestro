"""Repo Profile - Repository metadata and evidence collection hints.

A Repo Profile is a repo-local, optional configuration file that helps Maestro
understand "what" the repository is and "where" truth can be found, without
forcing a specific repository layout.

Profile location:
- Primary: docs/maestro/repo_profile.json
- Fallback: .maestro/profile.json

The profile is entirely optional. When absent, Maestro falls back to heuristic-based
discovery.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class EvidenceRules:
    """Budget and preference rules for evidence collection."""
    max_files: int = 60
    max_bytes: int = 250000
    max_help_calls: int = 6
    timeout_seconds: int = 5
    prefer_dirs: List[str] = field(default_factory=list)  # e.g., ["docs/commands", "docs/api"]
    exclude_patterns: List[str] = field(default_factory=list)  # e.g., ["*.pyc", "node_modules"]


@dataclass
class RepoProfile:
    """Repository profile describing the project and evidence collection hints.

    This is a lightweight, repo-local configuration that helps Maestro:
    1. Understand what the repository is (product_name, language)
    2. Find truth efficiently (build_entrypoints, docs_hints, cli_help_candidates)
    3. Budget evidence collection (evidence_rules)

    All fields are optional with sensible defaults.
    """
    product_name: str = ""
    primary_language: str = ""
    build_entrypoints: List[str] = field(default_factory=list)  # e.g., ["cmake", "make", "./build.sh"]
    docs_hints: List[str] = field(default_factory=list)  # e.g., ["docs/", "README.md", "docs/commands/"]
    cli_help_candidates: List[str] = field(default_factory=list)  # e.g., ["bin/maestro", "build/maestro"]
    evidence_rules: EvidenceRules = field(default_factory=EvidenceRules)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> RepoProfile:
        """Load from dictionary."""
        # Handle nested EvidenceRules
        evidence_rules_data = data.get('evidence_rules', {})
        if evidence_rules_data and not isinstance(evidence_rules_data, EvidenceRules):
            evidence_rules = EvidenceRules(**evidence_rules_data)
        else:
            evidence_rules = evidence_rules_data or EvidenceRules()

        return cls(
            product_name=data.get('product_name', ""),
            primary_language=data.get('primary_language', ""),
            build_entrypoints=data.get('build_entrypoints', []),
            docs_hints=data.get('docs_hints', []),
            cli_help_candidates=data.get('cli_help_candidates', []),
            evidence_rules=evidence_rules
        )


def find_profile_path(repo_root: Path) -> Optional[Path]:
    """Find the repo profile file if it exists.

    Checks in order:
    1. docs/maestro/repo_profile.json
    2. .maestro/profile.json

    Args:
        repo_root: Root directory of the repository

    Returns:
        Path to profile file if found, None otherwise
    """
    candidates = [
        repo_root / "docs" / "maestro" / "repo_profile.json",
        repo_root / ".maestro" / "profile.json"
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    return None


def load_profile(repo_root: Path) -> Optional[RepoProfile]:
    """Load repo profile if it exists.

    Args:
        repo_root: Root directory of the repository

    Returns:
        RepoProfile if found and valid, None otherwise
    """
    profile_path = find_profile_path(repo_root)
    if not profile_path:
        return None

    try:
        with open(profile_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return RepoProfile.from_dict(data)
    except Exception:
        # If profile is malformed, return None and fall back to heuristics
        return None


def save_profile(profile: RepoProfile, repo_root: Path, prefer_maestro_dir: bool = True) -> Path:
    """Save repo profile to disk.

    Args:
        profile: RepoProfile to save
        repo_root: Root directory of the repository
        prefer_maestro_dir: If True, save to docs/maestro/; if False, save to .maestro/

    Returns:
        Path where profile was saved
    """
    if prefer_maestro_dir:
        profile_dir = repo_root / "docs" / "maestro"
        profile_path = profile_dir / "repo_profile.json"
    else:
        profile_dir = repo_root / ".maestro"
        profile_path = profile_dir / "profile.json"

    # Ensure directory exists
    profile_dir.mkdir(parents=True, exist_ok=True)

    # Write profile
    with open(profile_path, 'w', encoding='utf-8') as f:
        json.dump(profile.to_dict(), f, indent=2)

    return profile_path


def infer_profile_from_repo(repo_root: Path) -> RepoProfile:
    """Infer a reasonable repo profile from repository heuristics.

    This function analyzes the repository structure to generate a sensible
    default profile. It looks for:
    - Language indicators (file extensions, build files)
    - Build system markers (Makefile, CMakeLists.txt, package.json, etc.)
    - Documentation directories
    - Executable binaries

    Args:
        repo_root: Root directory of the repository

    Returns:
        RepoProfile with inferred values
    """
    product_name = repo_root.name
    primary_language = ""
    build_entrypoints = []
    docs_hints = []
    cli_help_candidates = []

    # Infer primary language from build files
    if (repo_root / "CMakeLists.txt").exists() or (repo_root / "configure.ac").exists():
        primary_language = "C++"
    elif (repo_root / "Cargo.toml").exists():
        primary_language = "Rust"
    elif (repo_root / "go.mod").exists():
        primary_language = "Go"
    elif (repo_root / "package.json").exists():
        primary_language = "JavaScript"
    elif (repo_root / "pyproject.toml").exists() or (repo_root / "setup.py").exists():
        primary_language = "Python"
    elif (repo_root / "build.gradle").exists() or (repo_root / "pom.xml").exists():
        primary_language = "Java"

    # Infer build entrypoints
    if (repo_root / "Makefile").exists():
        build_entrypoints.append("make")
    if (repo_root / "CMakeLists.txt").exists():
        build_entrypoints.append("cmake . && make")
    if (repo_root / "build.sh").exists():
        build_entrypoints.append("./build.sh")
    if (repo_root / "configure.ac").exists():
        build_entrypoints.append("./configure && make")
    if (repo_root / "package.json").exists():
        build_entrypoints.append("npm install && npm run build")
    if (repo_root / "Cargo.toml").exists():
        build_entrypoints.append("cargo build")
    if (repo_root / "go.mod").exists():
        build_entrypoints.append("go build")

    # Infer docs hints
    if (repo_root / "README.md").exists():
        docs_hints.append("README.md")
    if (repo_root / "docs").exists() and (repo_root / "docs").is_dir():
        docs_hints.append("docs/")
    if (repo_root / "doc").exists() and (repo_root / "doc").is_dir():
        docs_hints.append("doc/")

    # Infer CLI help candidates from common binary locations
    bin_dirs = ["bin", "build", "target/release", "dist"]
    for bin_dir in bin_dirs:
        bin_path = repo_root / bin_dir
        if bin_path.exists() and bin_path.is_dir():
            # Look for executables (rough heuristic: no extension or .exe)
            try:
                for item in bin_path.iterdir():
                    if item.is_file() and (not item.suffix or item.suffix == '.exe'):
                        # Add relative path
                        cli_help_candidates.append(str(item.relative_to(repo_root)))
            except Exception:
                pass

    return RepoProfile(
        product_name=product_name,
        primary_language=primary_language,
        build_entrypoints=build_entrypoints,
        docs_hints=docs_hints,
        cli_help_candidates=cli_help_candidates,
        evidence_rules=EvidenceRules()
    )

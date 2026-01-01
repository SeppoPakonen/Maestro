"""Repo-agnostic discovery for collecting evidence about a codebase.

This module provides budget-enforced discovery that works without hardcoded assumptions
about repository structure. It gathers evidence from READMEs, build systems, and binaries
while respecting hard limits on files and bytes processed.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class DiscoveryBudget:
    """Hard limits for discovery to keep prompts bounded."""
    max_files: int = 40
    max_bytes: int = 200000
    max_depth: int = 2
    timeout_seconds: int = 5


@dataclass
class DiscoveryEvidence:
    """Evidence collected from repo discovery."""
    evidence: List[Dict[str, str]] = field(default_factory=list)  # [{kind, path, summary}]
    warnings: List[str] = field(default_factory=list)
    budget: Dict[str, int] = field(default_factory=dict)


def discover_repo(repo_root: Path, budget: DiscoveryBudget) -> DiscoveryEvidence:
    """Discover repo structure and evidence with hard budgets.

    This function is repo-agnostic and makes NO assumptions about:
    - Presence of specific directories like docs/commands/
    - Project language or build system
    - Repository structure conventions

    Instead, it uses heuristics and budgets to gather evidence:
    - README files (deterministic order)
    - Top-level structure listing
    - Build system detection
    - Binary --help text (with timeouts)

    Args:
        repo_root: Root directory of the repository
        budget: Budget limits for discovery

    Returns:
        DiscoveryEvidence with collected evidence, warnings, and budget stats
    """
    evidence = []
    warnings = []
    total_bytes = 0
    files_processed = 0

    # 1. Try to read README files (deterministic order)
    readme_patterns = ["README.md", "docs/README.md", "docs/index.md"]
    for pattern in readme_patterns:
        if files_processed >= budget.max_files:
            warnings.append(f"Reached max_files budget ({budget.max_files}), skipping remaining READMEs")
            break

        path = repo_root / pattern
        if path.exists() and path.is_file():
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")[:1000]  # First 1KB
                evidence.append({
                    "kind": "file",
                    "path": str(path.relative_to(repo_root)),
                    "summary": f"README file ({len(content)} chars)"
                })
                total_bytes += len(content)
                files_processed += 1

                if total_bytes >= budget.max_bytes:
                    warnings.append(f"Reached max_bytes budget ({budget.max_bytes}), stopping README collection")
                    break
            except Exception as e:
                warnings.append(f"Could not read {path}: {e}")

    # 2. List top-level structure (hard cap 200 entries)
    try:
        entries = list(repo_root.iterdir())[:200]
        structure_summary = f"Top-level: {len(entries)} entries"
        evidence.append({
            "kind": "structure",
            "path": str(repo_root),
            "summary": structure_summary
        })
    except Exception as e:
        warnings.append(f"Could not list repo structure: {e}")

    # 3. Detect build systems (deterministic order)
    build_files = [
        "CMakeLists.txt", "Makefile", "configure.ac",
        "package.json", "pyproject.toml", "setup.py",
        "build.gradle", "pom.xml", "Cargo.toml",
        "go.mod", "Gemfile", "composer.json"
    ]

    for build_file in build_files:
        if files_processed >= budget.max_files:
            warnings.append(f"Reached max_files budget ({budget.max_files}), skipping remaining build files")
            break

        path = repo_root / build_file
        if path.exists() and path.is_file():
            evidence.append({
                "kind": "file",
                "path": str(path.relative_to(repo_root)),
                "summary": f"Build system: {build_file}"
            })
            files_processed += 1

    # 4. Try --help on binaries (with timeout)
    bin_dirs = ["build", "bin", "target/release", ".venv/bin", "node_modules/.bin"]

    for bin_dir in bin_dirs:
        if files_processed >= budget.max_files:
            warnings.append(f"Reached max_files budget ({budget.max_files}), skipping remaining binaries")
            break

        bin_path = repo_root / bin_dir
        if bin_path.exists() and bin_path.is_dir():
            try:
                binaries = [
                    f for f in bin_path.iterdir()
                    if f.is_file() and os.access(f, os.X_OK)
                ]

                for binary in binaries[:5]:  # Max 5 binaries per directory
                    if files_processed >= budget.max_files:
                        break

                    try:
                        result = subprocess.run(
                            [str(binary), "--help"],
                            capture_output=True,
                            text=True,
                            timeout=budget.timeout_seconds
                        )
                        help_text = result.stdout[:500]  # First 500 chars
                        if help_text.strip():  # Only record if we got output
                            evidence.append({
                                "kind": "command",
                                "cmd": f"{binary.name} --help",
                                "summary": f"Help text ({len(help_text)} chars)"
                            })
                            total_bytes += len(help_text)
                            files_processed += 1
                    except subprocess.TimeoutExpired:
                        warnings.append(f"Timeout running {binary.name} --help")
                    except Exception as e:
                        # Silently skip binaries that can't run (many false positives)
                        pass
            except Exception as e:
                warnings.append(f"Could not scan {bin_dir}: {e}")

    return DiscoveryEvidence(
        evidence=evidence,
        warnings=warnings,
        budget={
            "max_files": budget.max_files,
            "max_bytes": budget.max_bytes,
            "files_processed": files_processed,
            "bytes_collected": total_bytes
        }
    )

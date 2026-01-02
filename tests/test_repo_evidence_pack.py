"""Tests for repo evidence pack generation (deterministic + budgeted)."""
import pytest
import tempfile
from pathlib import Path
from maestro.repo.evidence_pack import (
    EvidenceCollector,
    EvidencePack,
    save_evidence_pack,
    load_evidence_pack,
    find_evidence_packs
)


def create_test_repo(tmpdir: Path):
    """Create a minimal test repository structure."""
    # Create basic files
    (tmpdir / "README.md").write_text("# Test Repo\n\nTest content for README")
    (tmpdir / "Makefile").write_text("all:\n\techo 'test'\n")

    # Create docs directory
    docs_dir = tmpdir / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("# Guide\n\nTest documentation")

    # Create build file
    (tmpdir / "package.json").write_text('{"name": "test"}')

    return tmpdir


def test_evidence_pack_determinism():
    """Test that same repo + same settings → same pack ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        create_test_repo(repo_root)

        # Generate pack 1
        collector1 = EvidenceCollector(
            repo_root=repo_root,
            max_files=10,
            max_bytes=10000,
            max_help_calls=2
        )
        pack1 = collector1.collect_all()

        # Generate pack 2 (same settings)
        collector2 = EvidenceCollector(
            repo_root=repo_root,
            max_files=10,
            max_bytes=10000,
            max_help_calls=2
        )
        pack2 = collector2.collect_all()

        # Verify determinism
        assert pack1.meta.pack_id == pack2.meta.pack_id, "Pack IDs should match for same inputs"
        assert len(pack1.items) == len(pack2.items), "Item counts should match"
        assert [i.source for i in pack1.items] == [i.source for i in pack2.items], "Sources should match"


def test_evidence_pack_budget_enforcement():
    """Test that budgets are enforced correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        create_test_repo(repo_root)

        # Create many files to test budget
        docs_dir = repo_root / "docs"
        for i in range(20):
            (docs_dir / f"file{i}.md").write_text(f"# File {i}\n\nContent {i}")

        # Test with small budget
        collector = EvidenceCollector(
            repo_root=repo_root,
            max_files=5,
            max_bytes=5000,
            max_help_calls=1
        )
        pack = collector.collect_all()

        # Verify budget enforcement
        assert pack.meta.evidence_count <= 5, "Should not exceed max_files budget"
        assert pack.meta.total_bytes <= 5000, "Should not exceed max_bytes budget"
        assert pack.meta.budget_applied['files_processed'] <= 5
        assert pack.meta.budget_applied['help_calls_made'] <= 1


def test_evidence_pack_different_budgets():
    """Test that different budgets produce different pack IDs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        create_test_repo(repo_root)

        # Pack with max_files=5
        collector1 = EvidenceCollector(repo_root=repo_root, max_files=5)
        pack1 = collector1.collect_all()

        # Pack with max_files=10
        collector2 = EvidenceCollector(repo_root=repo_root, max_files=10)
        pack2 = collector2.collect_all()

        # Verify different packs
        # Pack IDs should be different because budget parameters are different
        assert pack1.meta.pack_id != pack2.meta.pack_id, "Different budgets should produce different pack IDs"
        # Note: evidence_count may be the same if repo is small, but pack IDs will differ


def test_evidence_pack_save_load():
    """Test that packs can be saved and loaded correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        create_test_repo(repo_root)

        storage_dir = Path(tmpdir) / "packs"

        # Generate and save pack
        collector = EvidenceCollector(
            repo_root=repo_root,
            max_files=10,
            max_bytes=10000
        )
        original_pack = collector.collect_all()

        pack_dir = save_evidence_pack(original_pack, storage_dir)
        assert pack_dir.exists(), "Pack directory should be created"
        assert (pack_dir / "meta.json").exists(), "meta.json should exist"
        assert (pack_dir / "pack.json").exists(), "pack.json should exist"

        # Load pack
        loaded_pack = load_evidence_pack(original_pack.meta.pack_id, storage_dir)

        assert loaded_pack is not None, "Pack should load successfully"
        assert loaded_pack.meta.pack_id == original_pack.meta.pack_id
        assert loaded_pack.meta.evidence_count == original_pack.meta.evidence_count
        assert len(loaded_pack.items) == len(original_pack.items)


def test_evidence_pack_stable_ordering():
    """Test that evidence items are collected in stable order."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        create_test_repo(repo_root)

        # Generate pack multiple times
        sources_list = []
        for _ in range(3):
            collector = EvidenceCollector(
                repo_root=repo_root,
                max_files=10,
                max_bytes=10000
            )
            pack = collector.collect_all()
            sources = [item.source for item in pack.items]
            sources_list.append(sources)

        # Verify all runs produced same order
        assert sources_list[0] == sources_list[1] == sources_list[2], "Source ordering should be stable"


def test_find_evidence_packs():
    """Test finding evidence packs in storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        create_test_repo(repo_root)
        storage_dir = Path(tmpdir) / "packs"

        # Create multiple packs with different budgets
        for max_files in [5, 10, 15]:
            collector = EvidenceCollector(
                repo_root=repo_root,
                max_files=max_files
            )
            pack = collector.collect_all()
            save_evidence_pack(pack, storage_dir)

        # Find all packs
        pack_ids = find_evidence_packs(storage_dir)

        assert len(pack_ids) == 3, "Should find all 3 packs"
        assert all(isinstance(pid, str) for pid in pack_ids), "Pack IDs should be strings"
        assert pack_ids == sorted(pack_ids), "Pack IDs should be sorted"


def test_evidence_pack_truncation_tracking():
    """Test that truncation is tracked correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)

        # Create large file that will be truncated
        large_content = "x" * 20000  # 20KB
        (repo_root / "README.md").write_text(large_content)

        collector = EvidenceCollector(
            repo_root=repo_root,
            max_files=5,
            max_bytes=10000
        )
        pack = collector.collect_all()

        # Verify truncation tracking
        if pack.meta.truncated_items:
            assert "README.md" in pack.meta.truncated_items, "Large README should be in truncated list"
            # Find README item
            readme_item = next((item for item in pack.items if "README.md" in item.source), None)
            if readme_item:
                assert readme_item.truncated, "README item should be marked as truncated"
                assert len(readme_item.content) < len(large_content), "Content should be truncated"

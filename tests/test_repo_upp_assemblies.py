"""
Regression tests for U++ assembly detection rules.
"""

from pathlib import Path

import pytest

from maestro.repo.scanner import is_upp_package_root, scan_upp_repo_v2

pytestmark = pytest.mark.fast


def _write_upp(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('file "dummy.cpp";\n', encoding="utf-8")


def _assembly_relpaths(repo_root: Path, scan_result) -> set[Path]:
    roots = set()
    for asm in scan_result.assemblies_detected:
        asm_root = Path(asm.root_path).resolve()
        roots.add(asm_root.relative_to(repo_root.resolve()))
    return roots


def test_package_root_with_subpackages_is_not_assembly(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write_upp(repo_root / "uppsrc/Core/Core.upp")
    _write_upp(repo_root / "uppsrc/Core/SSH/SSH.upp")
    _write_upp(repo_root / "uppsrc/Core/SMTP/SMTP.upp")

    result = scan_upp_repo_v2(str(repo_root), verbose=False, include_user_config=False)

    package_names = {pkg.name for pkg in result.packages_detected}
    assert package_names >= {"Core", "SSH", "SMTP"}

    asm_roots = _assembly_relpaths(repo_root, result)
    assert Path("uppsrc/Core") not in asm_roots
    assert all(
        not is_upp_package_root(Path(asm.root_path))
        for asm in result.assemblies_detected
    )


def test_uppsrc_grouping_is_assembly(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _write_upp(repo_root / "uppsrc/Core/Core.upp")
    _write_upp(repo_root / "uppsrc/Core/SSH/SSH.upp")
    _write_upp(repo_root / "uppsrc/Core/SMTP/SMTP.upp")
    _write_upp(repo_root / "uppsrc/AllForI18n/AllForI18n.upp")
    _write_upp(repo_root / "uppsrc/CtrlCore/CtrlCore.upp")

    result = scan_upp_repo_v2(str(repo_root), verbose=False, include_user_config=False)

    asm_roots = _assembly_relpaths(repo_root, result)
    assert Path("uppsrc") in asm_roots

    pkg_roots = {Path(pkg.dir).resolve().relative_to(repo_root.resolve()) for pkg in result.packages_detected}
    assert asm_roots.isdisjoint(pkg_roots)
    assert all(
        not is_upp_package_root(Path(asm.root_path))
        for asm in result.assemblies_detected
    )

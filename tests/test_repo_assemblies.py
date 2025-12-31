"""
Tests for U++ assembly detection and repo asm CLI.
"""

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CLI_TIMEOUT = int(os.environ.get("MAESTRO_CLI_TIMEOUT", "60"))

pytestmark = pytest.mark.fast


def _maestro_cmd() -> list[str]:
    maestro_bin = os.environ.get("MAESTRO_BIN")
    if maestro_bin:
        return shlex.split(maestro_bin)
    repo_root = Path(__file__).resolve().parents[1]
    return [sys.executable, str(repo_root / "maestro.py")]


def _fixture_root() -> Path:
    return Path(__file__).parent / "fixtures" / "repos" / "upp_min"


def _setup_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "upp_min_repo"
    shutil.copytree(_fixture_root(), repo_root)
    init_cmd = _maestro_cmd() + ["init", "--dir", str(repo_root)]
    result = subprocess.run(init_cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT)
    assert result.returncode == 0, f"maestro init failed: {result.stderr}"
    return repo_root


def _resolve_repo(repo_root: Path) -> dict:
    resolve_cmd = _maestro_cmd() + ["repo", "resolve", "--path", str(repo_root)]
    result = subprocess.run(resolve_cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT)
    assert result.returncode == 0, f"maestro repo resolve failed: {result.stderr}"
    model_path = repo_root / "docs" / "maestro" / "repo_model.json"
    with open(model_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_repo_model_assemblies_and_packages(tmp_path: Path):
    repo_root = _setup_repo(tmp_path)
    index_data = _resolve_repo(repo_root)

    assemblies = index_data.get("assemblies", [])
    packages = index_data.get("packages", [])

    assert assemblies, "Expected assemblies in repo model"
    assert packages, "Expected packages in repo model"

    root_relpaths = [asm["root_relpath"] for asm in assemblies]
    assert root_relpaths == sorted(root_relpaths), "Assemblies are not sorted by root_relpath"
    assert set(root_relpaths) >= {"uppsrc", "reference"}

    assembly_by_name = {asm["name"]: asm for asm in assemblies}
    uppsrc_id = assembly_by_name["uppsrc"]["assembly_id"]
    reference_id = assembly_by_name["reference"]["assembly_id"]

    package_by_name = {pkg["name"]: pkg for pkg in packages}
    assert package_by_name["Core"]["assembly_id"] == uppsrc_id
    assert package_by_name["umk"]["assembly_id"] == uppsrc_id
    assert package_by_name["RefPack"]["assembly_id"] == reference_id

    uppsrc_packages = {
        pkg_id for pkg_id in assembly_by_name["uppsrc"]["package_ids"]
    }
    assert package_by_name["Core"]["package_id"] in uppsrc_packages
    assert package_by_name["umk"]["package_id"] in uppsrc_packages


def test_repo_model_ids_stable(tmp_path: Path):
    repo_root = _setup_repo(tmp_path)
    index_data_1 = _resolve_repo(repo_root)
    index_data_2 = _resolve_repo(repo_root)

    assert index_data_1.get("assemblies") == index_data_2.get("assemblies")
    assert index_data_1.get("packages") == index_data_2.get("packages")


def test_repo_asm_cli_list_show(tmp_path: Path):
    repo_root = _setup_repo(tmp_path)
    _resolve_repo(repo_root)

    list_cmd = _maestro_cmd() + ["repo", "asm", "list", "--path", str(repo_root), "--json"]
    result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT)
    assert result.returncode == 0, f"maestro repo asm list failed: {result.stderr}"
    list_payload = json.loads(result.stdout)
    assembly_names = [asm["name"] for asm in list_payload.get("assemblies", [])]
    assert "uppsrc" in assembly_names
    assert "reference" in assembly_names

    show_cmd = _maestro_cmd() + ["repo", "asm", "show", "uppsrc", "--path", str(repo_root), "--json"]
    result = subprocess.run(show_cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT)
    assert result.returncode == 0, f"maestro repo asm show failed: {result.stderr}"
    show_payload = json.loads(result.stdout)
    show_packages = [pkg["name"] for pkg in show_payload.get("packages", [])]
    assert "Core" in show_packages
    assert "umk" in show_packages

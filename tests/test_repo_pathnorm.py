import json
from pathlib import Path

from maestro.repo.pathnorm import (
    is_subpath,
    normalize_path_to_posix,
    normalize_relpath,
)
from maestro.repo.storage import load_repo_model
from maestro.commands.repo.resolve_cmd import handle_repo_pkg_list


def test_normalize_relpath_windows_wsl_unc():
    repo_root = "C:\\Users\\sblo\\Dev\\ai-upp"
    target = "C:\\Users\\sblo\\Dev\\ai-upp\\uppsrc\\Core"
    assert is_subpath(repo_root, target)
    assert normalize_relpath(repo_root, target) == "uppsrc/Core"

    repo_root = "/mnt/c/Users/sblo/Dev/ai-upp"
    target = "C:\\Users\\sblo\\Dev\\ai-upp\\uppsrc\\Core"
    assert is_subpath(repo_root, target)
    assert normalize_relpath(repo_root, target) == "uppsrc/Core"

    repo_root = "\\\\server\\share\\ai-upp"
    target = "\\\\server\\share\\ai-upp\\docs\\maestro"
    assert is_subpath(repo_root, target)
    assert normalize_relpath(repo_root, target) == "docs/maestro"

    repo_root = "/mnt/e/active/ai-upp"
    target = "/mnt/e/active/ai-upp/docs/maestro"
    assert is_subpath(repo_root, target)
    assert normalize_relpath(repo_root, target) == "docs/maestro"

    repo_root = "C:/Users/sblo/Dev/ai-upp"
    target = "C:\\Users\\sblo\\Dev\\ai-upp\\docs/maestro"
    assert normalize_relpath(repo_root, target) == "docs/maestro"

    assert normalize_path_to_posix("docs\\maestro\\repo_model.json") == "docs/maestro/repo_model.json"


def test_load_repo_model_normalizes_absolute_paths(tmp_path, capsys):
    repo_root = tmp_path
    repo_truth = repo_root / "docs" / "maestro"
    repo_truth.mkdir(parents=True)

    model = {
        "repo_root": str(repo_root),
        "assemblies_detected": [
            {
                "name": "uppsrc",
                "root_path": str(repo_root / "uppsrc"),
                "package_folders": [str(repo_root / "uppsrc")],
                "package_dirs": [str(repo_root / "uppsrc" / "Core")],
            }
        ],
        "packages_detected": [
            {
                "name": "Core",
                "dir": str(repo_root / "uppsrc" / "Core"),
                "upp_path": str(repo_root / "uppsrc" / "Core" / "Core.upp"),
                "files": ["Core.cpp"],
                "groups": [],
                "ungrouped_files": ["Core.cpp"],
                "build_system": "upp",
            }
        ],
        "unknown_paths": [
            {"path": str(repo_root / "README.md"), "type": "file", "guessed_kind": "docs"}
        ],
        "internal_packages": [
            {
                "name": "docs",
                "root_path": str(repo_root / "docs"),
                "guessed_type": "docs",
                "members": ["docs/README.md"],
                "groups": [],
                "ungrouped_files": ["docs/README.md"],
            }
        ],
    }

    (repo_truth / "repo_model.json").write_text(json.dumps(model, indent=2), encoding="utf-8")

    loaded = load_repo_model(str(repo_root))
    captured = capsys.readouterr()
    assert "Normalized" in captured.out

    pkg = loaded["packages_detected"][0]
    assert pkg["dir"] == "uppsrc/Core"
    assert pkg["upp_path"] == "uppsrc/Core/Core.upp"

    handle_repo_pkg_list(loaded["packages_detected"], json_output=False, repo_root=str(repo_root))
    output = capsys.readouterr().out
    assert str(repo_root) in output

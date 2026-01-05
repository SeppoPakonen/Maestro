import shutil
from pathlib import Path

from maestro.commands.repo.import_roadmap import build_import_plan, render_import_plan, apply_import_plan
from maestro.tracks.json_store import JsonStore


def _copy_fixture(tmp_path: Path) -> Path:
    fixture_root = Path(__file__).parent / "fixtures" / "roadmap_import_demo"
    repo_root = tmp_path / "repo"
    shutil.copytree(fixture_root, repo_root)
    (repo_root / "docs" / "maestro").mkdir(parents=True, exist_ok=True)
    return repo_root


def _find_task(plan, source_root: str, relpath: str):
    for track in plan.values():
        for phase in track.phases.values():
            for task in phase.tasks.values():
                if task.source_item.source_root == source_root and task.source_item.relpath == relpath:
                    return task
    return None


def test_import_roadmap_dry_run_stable(tmp_path):
    repo_root = _copy_fixture(tmp_path)
    roadmap_dir = repo_root / "roadmap"
    task_dir = repo_root / "task"

    plan_first = build_import_plan(roadmap_dir, task_dir)
    plan_second = build_import_plan(roadmap_dir, task_dir)

    assert render_import_plan(plan_first) == render_import_plan(plan_second)


def test_import_roadmap_apply_idempotent(tmp_path):
    repo_root = _copy_fixture(tmp_path)
    roadmap_dir = repo_root / "roadmap"
    task_dir = repo_root / "task"

    plan = build_import_plan(roadmap_dir, task_dir)

    done_task = _find_task(plan, "roadmap", "core/phase1/done_task.md")
    todo_task = _find_task(plan, "roadmap", "core/phase2/todo_task.md")
    checklist_task = _find_task(plan, "task", "ops/checklist.md")

    assert done_task is not None and done_task.status == "done"
    assert todo_task is not None and todo_task.status == "todo"
    assert checklist_task is not None and checklist_task.status == "done"

    apply_import_plan(plan, repo_root)
    store = JsonStore(base_path=str(repo_root / "docs" / "maestro"))
    first_task_files = sorted(store.tasks_dir.glob("*.json"))

    apply_import_plan(plan, repo_root)
    second_task_files = sorted(store.tasks_dir.glob("*.json"))

    assert first_task_files == second_task_files

    loaded_task = store.load_task(done_task.task_id)
    assert loaded_task is not None
    assert loaded_task.status == "done"

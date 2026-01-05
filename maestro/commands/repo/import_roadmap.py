"""Import roadmap/task folders into Maestro tracks/phases/tasks."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from maestro.modules.utils import print_error, print_info, print_success
from maestro.repo.storage import find_repo_root
from maestro.tracks.json_store import JsonStore
from maestro.tracks.models import Phase, Task, Track


DONE_TOKENS = ("done", "finished", "completed", "complete", "✓", "x_", "_done")
STATUS_DONE_TOKENS = ("done", "finished", "completed", "complete", "closed")
STATUS_TODO_TOKENS = ("todo", "pending", "open", "in progress", "in_progress")
CONTENT_DONE_TOKENS = ("complete", "completed", "finished", "✓")
CONTENT_TODO_TOKENS = ("todo", "backlog", "in progress", "in_progress")


@dataclass
class SourceItem:
    source_root: str
    relpath: str
    title: str
    status: str
    summary: str
    excerpt: List[str]
    mtime: Optional[float]


@dataclass
class TaskSpec:
    task_id: str
    title: str
    status: str
    description: List[str]
    tags: List[str]
    source_item: SourceItem


@dataclass
class PhaseSpec:
    phase_id: str
    name: str
    tasks: Dict[str, TaskSpec] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class TrackSpec:
    track_id: str
    name: str
    phases: Dict[str, PhaseSpec] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


def slugify(text: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in text.strip())
    slug = "-".join(filter(None, slug.split("-")))
    return slug or "item"


def titleize(text: str) -> str:
    cleaned = text.replace("_", " ").replace("-", " ").strip()
    return " ".join(part.capitalize() for part in cleaned.split()) or text


def _read_text(path: Path, max_bytes: int = 200000) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read(max_bytes)
    except OSError:
        return ""


def _extract_excerpt(content: str, max_lines: int = 6) -> List[str]:
    lines = []
    for line in content.splitlines():
        if len(lines) >= max_lines:
            break
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
    return lines


def _extract_summary(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:160]
    return fallback


def _status_from_tokens(path_text: str) -> Optional[str]:
    lowered = path_text.lower()
    for token in DONE_TOKENS:
        if token in lowered:
            return "done"
    return None


def _status_from_checkboxes(content: str) -> Optional[str]:
    checkboxes = []
    for line in content.splitlines():
        stripped = line.strip().lower()
        if stripped.startswith("- [") or stripped.startswith("* ["):
            checkboxes.append(stripped)
    if not checkboxes:
        return None
    all_checked = all("[x]" in line for line in checkboxes)
    return "done" if all_checked else None


def _status_from_status_line(content: str) -> Optional[str]:
    for line in content.splitlines():
        stripped = line.strip().lower()
        if "status:" in stripped:
            value = stripped.split("status:", 1)[1].strip()
            if any(token in value for token in STATUS_DONE_TOKENS):
                return "done"
            if any(token in value for token in STATUS_TODO_TOKENS):
                return "todo"
    return None


def _status_from_content_tokens(content: str) -> Optional[str]:
    lowered = content.lower()
    if any(token in lowered for token in CONTENT_DONE_TOKENS):
        if not any(token in lowered for token in CONTENT_TODO_TOKENS):
            return "done"
    return None


def infer_status(path_text: str, content: str) -> str:
    status = _status_from_tokens(path_text)
    if status:
        return status

    status = _status_from_checkboxes(content)
    if status:
        return status

    status = _status_from_status_line(content)
    if status:
        return status

    status = _status_from_content_tokens(content)
    if status:
        return status

    return "todo"


def _source_item_from_file(root_label: str, root_dir: Path, file_path: Path) -> SourceItem:
    relpath = file_path.relative_to(root_dir).as_posix()
    content = _read_text(file_path)
    title = titleize(file_path.stem)
    status = infer_status(relpath, content)
    summary = _extract_summary(content, title)
    excerpt = _extract_excerpt(content)
    try:
        mtime = file_path.stat().st_mtime
    except OSError:
        mtime = None
    return SourceItem(
        source_root=root_label,
        relpath=relpath,
        title=title,
        status=status,
        summary=summary,
        excerpt=excerpt,
        mtime=mtime,
    )


def _collect_source_items(root_label: str, root_dir: Path) -> List[SourceItem]:
    items: List[SourceItem] = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = sorted([d for d in dirnames if not d.startswith(".")])
        for filename in sorted(filenames):
            if filename.startswith("."):
                continue
            file_path = Path(dirpath) / filename
            if not file_path.is_file():
                continue
            items.append(_source_item_from_file(root_label, root_dir, file_path))
    return items


def _derive_track_phase(relpath: str, root_label: str) -> Tuple[str, str, str]:
    parts = Path(relpath).parts
    if len(parts) == 0:
        return f"{root_label} root", "root", ""
    if len(parts) == 1:
        return f"{root_label} root", "root", parts[0]
    if len(parts) == 2:
        return parts[0], "root", parts[1]
    return parts[0], parts[1], Path(*parts[2:]).as_posix()


def _task_id_for(phase_id: str, source_relpath: str) -> str:
    base = slugify(Path(source_relpath).stem)
    digest = hashlib.sha1(source_relpath.encode("utf-8")).hexdigest()[:6]
    return f"{phase_id}-{base}-{digest}"


def build_import_plan(roadmap_dir: Path, tasks_dir: Path) -> Dict[str, TrackSpec]:
    plan: Dict[str, TrackSpec] = {}
    for root_label, root_dir in (("roadmap", roadmap_dir), ("task", tasks_dir)):
        items = _collect_source_items(root_label, root_dir)
        for item in items:
            track_name, phase_name, task_rel = _derive_track_phase(item.relpath, root_label)
            is_root_track = track_name == f"{root_label} root"
            track_id = f"{root_label}-root" if is_root_track else f"{root_label}-{slugify(track_name)}"
            track_display = f"{root_label.title()} (root)" if is_root_track else f"{root_label.title()}: {titleize(track_name)}"
            phase_id = f"{track_id}-{slugify(phase_name)}"

            task_title = titleize(Path(task_rel).stem) if task_rel else item.title
            task_id = _task_id_for(phase_id, f"{root_label}/{item.relpath}")

            track = plan.setdefault(
                track_id,
                TrackSpec(
                    track_id=track_id,
                    name=track_display,
                    tags=["imported", root_label],
                ),
            )
            phase = track.phases.setdefault(
                phase_id,
                PhaseSpec(
                    phase_id=phase_id,
                    name=titleize(phase_name),
                    tags=["imported", root_label],
                ),
            )

            description = [
                f"Source: {root_label}/{item.relpath}",
                f"Summary: {item.summary}",
            ]
            if item.excerpt:
                description.append("Excerpt:")
                description.extend([f"  {line}" for line in item.excerpt])

            phase.tasks[task_id] = TaskSpec(
                task_id=task_id,
                title=task_title,
                status=item.status,
                description=description,
                tags=["imported", root_label],
                source_item=item,
            )
    return plan


def _status_rollup(statuses: Iterable[str]) -> Tuple[str, int]:
    statuses = list(statuses)
    if not statuses:
        return "planned", 0
    done_count = sum(1 for status in statuses if status == "done")
    completion = int(round((done_count / len(statuses)) * 100))
    if done_count == len(statuses):
        return "done", 100
    if done_count == 0:
        return "planned", 0
    return "in_progress", completion


def _phase_timestamp(tasks: Iterable[TaskSpec]) -> Optional[datetime]:
    mtimes = [task.source_item.mtime for task in tasks if task.source_item.mtime]
    if not mtimes:
        return None
    return datetime.utcfromtimestamp(max(mtimes))


def apply_import_plan(plan: Dict[str, TrackSpec], repo_root: Path) -> None:
    store = JsonStore(base_path=str(repo_root / "docs" / "maestro"))
    index = store.load_index(load_tracks=False)
    track_ids = {track_id for track_id in index.tracks}

    for track_id in sorted(plan.keys()):
        track_spec = plan[track_id]
        existing_track = store.load_track(track_id, load_phases=False, load_tasks=False)

        phase_ids = []
        for phase_id in sorted(track_spec.phases.keys()):
            phase_spec = track_spec.phases[phase_id]
            task_ids = []
            task_statuses = []
            for task_id in sorted(phase_spec.tasks.keys()):
                task_spec = phase_spec.tasks[task_id]
                task_statuses.append(task_spec.status)
                task_ids.append(task_id)

                existing_task = store.load_task(task_id)
                completed = task_spec.status == "done"
                task_timestamp = (
                    datetime.utcfromtimestamp(task_spec.source_item.mtime)
                    if task_spec.source_item.mtime
                    else None
                )
                task = Task(
                    task_id=task_id,
                    name=task_spec.title,
                    status=task_spec.status,
                    completed=completed,
                    description=task_spec.description,
                    phase_id=phase_id,
                    tags=sorted(set(task_spec.tags + (existing_task.tags if existing_task else []))),
                    created_at=task_timestamp,
                    updated_at=task_timestamp,
                )
                store.save_task(task)

            phase_status, phase_completion = _status_rollup(task_statuses)
            phase_timestamp = _phase_timestamp(phase_spec.tasks.values())
            existing_phase = store.load_phase(phase_id, load_tasks=False)
            merged_task_ids = list(task_ids)
            if existing_phase:
                for existing in existing_phase.tasks:
                    if existing not in merged_task_ids:
                        merged_task_ids.append(existing)

            phase = Phase(
                phase_id=phase_id,
                name=phase_spec.name,
                status=phase_status,
                completion=phase_completion,
                description=[f"Imported from {track_spec.name} / {phase_spec.name}"],
                tasks=merged_task_ids,
                track_id=track_id,
                tags=sorted(set(phase_spec.tags + (existing_phase.tags if existing_phase else []))),
                created_at=phase_timestamp,
                updated_at=phase_timestamp,
            )
            store.save_phase(phase)
            phase_ids.append(phase_id)

        phase_statuses = []
        for phase_id in phase_ids:
            phase = store.load_phase(phase_id, load_tasks=False)
            if phase:
                phase_statuses.append(phase.status)
        track_status, track_completion = _status_rollup(phase_statuses)
        track_timestamp = _phase_timestamp(
            [task for phase in track_spec.phases.values() for task in phase.tasks.values()]
        )

        merged_phase_ids = list(phase_ids)
        if existing_track:
            for existing in existing_track.phases:
                if existing not in merged_phase_ids:
                    merged_phase_ids.append(existing)

        track = Track(
            track_id=track_id,
            name=track_spec.name,
            status=track_status,
            completion=track_completion,
            description=[f"Imported from {track_spec.name} sources."],
            phases=merged_phase_ids,
            tags=sorted(set(track_spec.tags + (existing_track.tags if existing_track else []))),
            created_at=track_timestamp,
            updated_at=track_timestamp,
        )
        store.save_track(track)

        if track_id not in track_ids:
            index.tracks.append(track_id)
            track_ids.add(track_id)

    store.save_index(index)


def render_import_plan(plan: Dict[str, TrackSpec]) -> List[str]:
    lines: List[str] = []
    for track_id in sorted(plan.keys()):
        track = plan[track_id]
        lines.append(f"Track {track_id}: {track.name} ({len(track.phases)} phases)")
        for phase_id in sorted(track.phases.keys()):
            phase = track.phases[phase_id]
            statuses = [task.status for task in phase.tasks.values()]
            done_count = sum(1 for status in statuses if status == "done")
            total = len(statuses)
            lines.append(f"  Phase {phase_id}: {phase.name} ({done_count}/{total} done)")
            for task_id in sorted(phase.tasks.keys()):
                task = phase.tasks[task_id]
                lines.append(f"    - [{task.status}] {task_id}: {task.title}")
    return lines


def handle_repo_import_roadmap(args) -> int:
    repo_root = Path(getattr(args, "path", None) or find_repo_root()).resolve()
    roadmap_dir = Path(args.roadmap).resolve()
    tasks_dir = Path(args.tasks).resolve()

    if not roadmap_dir.exists():
        print_error(f"Roadmap directory not found: {roadmap_dir}", 2)
        return 2
    if not tasks_dir.exists():
        print_error(f"Task directory not found: {tasks_dir}", 2)
        return 2

    apply = getattr(args, "apply", False)
    dry_run = getattr(args, "dry_run", False)
    if apply and dry_run:
        print_error("Use either --apply or --dry-run, not both.", 2)
        return 2
    if not apply:
        dry_run = True

    plan = build_import_plan(roadmap_dir, tasks_dir)
    plan_lines = render_import_plan(plan)

    if dry_run:
        print_info("Roadmap import plan (dry-run):", 0)
        for line in plan_lines:
            print_info(line, 1)
        return 0

    apply_import_plan(plan, repo_root)
    print_success("Roadmap import complete.", 2)
    return 0

"""Lightweight conversion pipeline helpers for tests and UI facades."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from maestro.modules.dataclasses import ConversionPipeline, ConversionStage
from maestro.convert.conversion_memory import ConversionMemory


def _pipeline_dir(conversion_dir: str = "./.maestro/convert/pipelines") -> Path:
    path = Path(conversion_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _stage_dir(stage_name: str) -> Path:
    path = Path(".maestro/convert/stages") / stage_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _now() -> str:
    return datetime.now().isoformat()


def _default_stages() -> List[ConversionStage]:
    stage_names = [
        "overview",
        "core_builds",
        "grow_from_main",
        "full_tree_check",
        "refactor",
    ]
    return [ConversionStage(name=name, status="pending") for name in stage_names]


def create_conversion_pipeline(name: str, source: str, target: str) -> ConversionPipeline:
    pipeline_id = uuid.uuid4().hex[:8]
    now = _now()
    pipeline = ConversionPipeline(
        id=pipeline_id,
        name=name,
        source=source,
        target=target,
        created_at=now,
        updated_at=now,
        status="new",
        stages=_default_stages(),
        active_stage=None,
    )
    save_conversion_pipeline(pipeline)
    return pipeline


def save_conversion_pipeline(pipeline: ConversionPipeline, conversion_dir: str = "./.maestro/convert/pipelines") -> None:
    pipeline.updated_at = _now()
    data = asdict(pipeline)
    # Normalize stage details to dicts
    for stage in data.get("stages", []):
        if stage.get("details") is None:
            stage["details"] = {}
    path = _pipeline_dir(conversion_dir) / f"{pipeline.id}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_conversion_pipeline(pipeline_id: str, conversion_dir: str = "./.maestro/convert/pipelines") -> ConversionPipeline:
    path = _pipeline_dir(conversion_dir) / f"{pipeline_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Pipeline not found: {pipeline_id}")

    data = json.loads(path.read_text(encoding="utf-8"))
    stages = []
    for stage_data in data.get("stages", []):
        stages.append(
            ConversionStage(
                name=stage_data.get("name", ""),
                status=stage_data.get("status", "pending"),
                started_at=stage_data.get("started_at"),
                completed_at=stage_data.get("completed_at"),
                error=stage_data.get("error"),
                details=stage_data.get("details") or {},
            )
        )

    return ConversionPipeline(
        id=data.get("id", pipeline_id),
        name=data.get("name", pipeline_id),
        source=data.get("source", ""),
        target=data.get("target", ""),
        created_at=data.get("created_at", _now()),
        updated_at=data.get("updated_at", _now()),
        status=data.get("status", "new"),
        stages=stages,
        active_stage=data.get("active_stage"),
        logs_dir=data.get("logs_dir"),
        inputs_dir=data.get("inputs_dir"),
        outputs_dir=data.get("outputs_dir"),
        source_repo=data.get("source_repo"),
        target_repo=data.get("target_repo"),
        conversion_intent=data.get("conversion_intent"),
    )


def _mark_stage(stage: ConversionStage, status: str, details: Optional[dict] = None) -> None:
    if status == "running":
        stage.started_at = _now()
    if status in {"completed", "failed", "blocked", "skipped"}:
        stage.completed_at = _now()
    stage.status = status
    if details is not None:
        stage.details = details


def run_overview_stage(pipeline: ConversionPipeline, stage: ConversionStage, verbose: bool = False) -> None:
    _mark_stage(stage, "running")
    _mark_stage(stage, "completed", {"summary": "overview complete"})
    save_conversion_pipeline(pipeline)


def run_core_builds_stage(pipeline: ConversionPipeline, stage: ConversionStage, verbose: bool = False) -> None:
    _mark_stage(stage, "running")
    _mark_stage(stage, "completed", {"summary": "core builds complete"})
    save_conversion_pipeline(pipeline)


def run_grow_from_main_stage(pipeline: ConversionPipeline, stage: ConversionStage, verbose: bool = False) -> None:
    _mark_stage(stage, "running")
    stage_path = _stage_dir("grow_from_main")
    # Minimal stage artifacts for tests/fixtures
    (stage_path / "stage.json").write_text(json.dumps({"status": "completed"}, indent=2), encoding="utf-8")
    for filename in ("inventory.json", "frontier.json", "included_set.json", "progress.json"):
        (stage_path / filename).write_text(json.dumps({}, indent=2), encoding="utf-8")
    _mark_stage(stage, "completed", {"artifacts_dir": str(stage_path)})
    save_conversion_pipeline(pipeline)


def run_full_tree_check_stage(pipeline: ConversionPipeline, stage: ConversionStage, verbose: bool = False) -> None:
    _mark_stage(stage, "running")
    _mark_stage(stage, "completed", {"summary": "full tree check complete"})
    save_conversion_pipeline(pipeline)


def run_refactor_stage(pipeline: ConversionPipeline, stage: ConversionStage, verbose: bool = False) -> None:
    _mark_stage(stage, "running")
    _mark_stage(stage, "completed", {"summary": "refactor stage complete"})
    save_conversion_pipeline(pipeline)


def get_decisions() -> list[dict]:
    return ConversionMemory().load_decisions()


def get_decision_by_id(decision_id: str):
    return ConversionMemory().get_decision_by_id(decision_id)

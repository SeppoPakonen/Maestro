"""Canonical session format for discuss subsystem.

This module provides readers and writers for the canonical discuss session format:
- docs/maestro/sessions/discuss/<session_id>/meta.json
- docs/maestro/sessions/discuss/<session_id>/transcript.jsonl

It also provides backward-compatible loaders for legacy formats.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from maestro.ai import ContractType


@dataclass
class SessionMeta:
    """Metadata for a discuss session."""
    session_id: str
    context: Dict[str, Any]  # kind, ref, router_reason
    contract_type: str
    created_at: str
    updated_at: str
    status: str  # "open" or "closed"
    final_json_present: bool
    engine: str
    model: str
    initial_prompt: str


@dataclass
class TranscriptEvent:
    """Single event in a discuss transcript."""
    ts: str
    type: str  # user_message, assistant_message, final_json, error, replay_run
    payload: Dict[str, Any]


@dataclass
class DiscussSession:
    """Complete discuss session with metadata and transcript."""
    meta: SessionMeta
    transcript: List[TranscriptEvent] = field(default_factory=list)
    session_dir: Optional[Path] = None


def create_session_id() -> str:
    """Create a new stable UUID-based session ID."""
    return str(uuid.uuid4())


def get_session_path(session_id: str) -> Path:
    """Get the canonical path for a session directory."""
    return Path("docs/maestro/sessions/discuss") / session_id


def create_session(
    context_kind: str,
    context_ref: Optional[str],
    router_reason: str,
    contract_type: ContractType,
    engine: str,
    model: str,
    initial_prompt: str
) -> DiscussSession:
    """Create a new discuss session with canonical format."""
    session_id = create_session_id()
    now = datetime.now().isoformat()

    meta = SessionMeta(
        session_id=session_id,
        context={
            "kind": context_kind,
            "ref": context_ref,
            "router_reason": router_reason
        },
        contract_type=contract_type.value,
        created_at=now,
        updated_at=now,
        status="open",
        final_json_present=False,
        engine=engine,
        model=model,
        initial_prompt=initial_prompt
    )

    session_dir = get_session_path(session_id)

    return DiscussSession(meta=meta, transcript=[], session_dir=session_dir)


def write_session(session: DiscussSession) -> None:
    """Write session to canonical format (meta.json + transcript.jsonl)."""
    if not session.session_dir:
        raise ValueError("Session directory not set")

    session.session_dir.mkdir(parents=True, exist_ok=True)

    # Write meta.json
    meta_path = session.session_dir / "meta.json"
    meta_dict = {
        "session_id": session.meta.session_id,
        "context": session.meta.context,
        "contract_type": session.meta.contract_type,
        "created_at": session.meta.created_at,
        "updated_at": session.meta.updated_at,
        "status": session.meta.status,
        "final_json_present": session.meta.final_json_present,
        "engine": session.meta.engine,
        "model": session.meta.model,
        "initial_prompt": session.meta.initial_prompt
    }
    meta_path.write_text(json.dumps(meta_dict, indent=2), encoding='utf-8')

    # Write transcript.jsonl
    transcript_path = session.session_dir / "transcript.jsonl"
    with open(transcript_path, 'w', encoding='utf-8') as f:
        for event in session.transcript:
            event_dict = {
                "ts": event.ts,
                "type": event.type,
                "payload": event.payload
            }
            f.write(json.dumps(event_dict) + '\n')


def append_event(session_dir: Path, event: TranscriptEvent) -> None:
    """Append an event to the transcript.jsonl file."""
    transcript_path = session_dir / "transcript.jsonl"
    event_dict = {
        "ts": event.ts,
        "type": event.type,
        "payload": event.payload
    }
    with open(transcript_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(event_dict) + '\n')


def update_session_status(session_dir: Path, status: str, final_json_present: bool = None) -> None:
    """Update session status in meta.json."""
    meta_path = session_dir / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Session metadata not found: {meta_path}")

    with open(meta_path, 'r', encoding='utf-8') as f:
        meta_dict = json.load(f)

    meta_dict["status"] = status
    meta_dict["updated_at"] = datetime.now().isoformat()

    if final_json_present is not None:
        meta_dict["final_json_present"] = final_json_present

    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta_dict, f, indent=2)


def load_session(session_id_or_path: str) -> DiscussSession:
    """Load a session from canonical or legacy format.

    Args:
        session_id_or_path: Session ID or path to session directory/file

    Returns:
        DiscussSession with loaded data

    Raises:
        FileNotFoundError: If session not found
        ValueError: If session format is invalid
    """
    # Try canonical format first
    if "/" not in session_id_or_path:
        # Assume it's a session ID
        session_dir = get_session_path(session_id_or_path)
        if session_dir.exists():
            return _load_canonical_session(session_dir)

    # Try as a path
    path = Path(session_id_or_path)
    if path.is_dir():
        # Check if it's canonical format
        if (path / "meta.json").exists():
            return _load_canonical_session(path)
        # Check if it's legacy work session format
        if (path / "session.json").exists():
            return _load_legacy_work_session(path)
    elif path.is_file():
        # Check if it's legacy artifact format
        if path.name.endswith("_results.json"):
            return _load_legacy_artifact(path)

    raise FileNotFoundError(f"Session not found: {session_id_or_path}")


def _load_canonical_session(session_dir: Path) -> DiscussSession:
    """Load session from canonical format."""
    meta_path = session_dir / "meta.json"
    transcript_path = session_dir / "transcript.jsonl"

    if not meta_path.exists():
        raise ValueError(f"meta.json not found in {session_dir}")

    # Load metadata
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta_dict = json.load(f)

    meta = SessionMeta(**meta_dict)

    # Load transcript
    transcript = []
    if transcript_path.exists():
        with open(transcript_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    event_dict = json.loads(line)
                    event = TranscriptEvent(**event_dict)
                    transcript.append(event)

    return DiscussSession(meta=meta, transcript=transcript, session_dir=session_dir)


def _load_legacy_work_session(session_dir: Path) -> DiscussSession:
    """Load session from legacy work session format (docs/sessions/<uuid>/)."""
    session_file = session_dir / "session.json"

    with open(session_file, 'r', encoding='utf-8') as f:
        session_data = json.load(f)

    # Extract context from related_entity
    related = session_data.get("related_entity", {})
    context_kind = "global"
    context_ref = None
    if "task_id" in related:
        context_kind = "task"
        context_ref = related["task_id"]
    elif "phase_id" in related:
        context_kind = "phase"
        context_ref = related["phase_id"]
    elif "track_id" in related:
        context_kind = "track"
        context_ref = related["track_id"]

    # Create metadata (best effort)
    meta = SessionMeta(
        session_id=session_data.get("session_id", "unknown"),
        context={
            "kind": context_kind,
            "ref": context_ref,
            "router_reason": "Loaded from legacy work session"
        },
        contract_type="global",  # Unknown from legacy format
        created_at=session_data.get("created", datetime.now().isoformat()),
        updated_at=session_data.get("modified", datetime.now().isoformat()),
        status="open" if session_data.get("status") == "running" else "closed",
        final_json_present=False,
        engine="unknown",
        model="unknown",
        initial_prompt=""
    )

    # Load breadcrumbs as transcript events (best effort)
    transcript = []
    breadcrumbs_dir = session_dir / "breadcrumbs"
    if breadcrumbs_dir.exists():
        for bc_file in sorted(breadcrumbs_dir.glob("*.json")):
            try:
                with open(bc_file, 'r', encoding='utf-8') as f:
                    bc_data = json.load(f)
                # Convert breadcrumb to event
                event = TranscriptEvent(
                    ts=bc_data.get("timestamp", datetime.now().isoformat()),
                    type="user_message",  # Assume user message
                    payload={"content": str(bc_data)}
                )
                transcript.append(event)
            except (json.JSONDecodeError, KeyError):
                continue

    return DiscussSession(meta=meta, transcript=transcript, session_dir=session_dir)


def _load_legacy_artifact(artifact_path: Path) -> DiscussSession:
    """Load session from legacy artifact format (docs/maestro/ai/artifacts/<id>_results.json)."""
    with open(artifact_path, 'r', encoding='utf-8') as f:
        artifact_data = json.load(f)

    # Extract context
    context_data = artifact_data.get("context", {})

    # Create metadata
    meta = SessionMeta(
        session_id=artifact_data.get("session_id", "unknown"),
        context=context_data if context_data else {"kind": "global", "ref": None, "router_reason": "Loaded from legacy artifact"},
        contract_type=artifact_data.get("contract_type", "global"),
        created_at=artifact_data.get("timestamp", datetime.now().isoformat()),
        updated_at=artifact_data.get("applied_at", artifact_data.get("timestamp", datetime.now().isoformat())),
        status="closed" if artifact_data.get("status") in ["applied", "cancelled", "dry_run"] else "open",
        final_json_present="patch_operations" in artifact_data,
        engine=artifact_data.get("engine", "unknown"),
        model=artifact_data.get("model", "unknown"),
        initial_prompt=artifact_data.get("initial_prompt", "")
    )

    # Create transcript with final_json event
    transcript = []

    # Add initial prompt as user message
    if meta.initial_prompt:
        transcript.append(TranscriptEvent(
            ts=meta.created_at,
            type="user_message",
            payload={"content": meta.initial_prompt}
        ))

    # Add final_json if present
    if "patch_operations" in artifact_data:
        transcript.append(TranscriptEvent(
            ts=meta.updated_at,
            type="final_json",
            payload={"patch_operations": artifact_data["patch_operations"]}
        ))

    return DiscussSession(meta=meta, transcript=transcript, session_dir=None)


def extract_final_json(session: DiscussSession) -> Optional[List[Dict[str, Any]]]:
    """Extract final_json patch_operations from session transcript.

    Returns:
        List of patch operations if found, None otherwise
    """
    for event in reversed(session.transcript):
        if event.type == "final_json":
            return event.payload.get("patch_operations")
    return None

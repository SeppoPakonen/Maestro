from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import os
import re
from typing import Dict, List, Optional, Tuple

from maestro.issues.model import IssueRecord


@dataclass
class SolutionDetails:
    title: str
    problem: str
    steps: List[str]
    keywords: List[str] = field(default_factory=list)
    regex: List[str] = field(default_factory=list)
    contexts: List[str] = field(default_factory=list)
    confidence: int = 70
    success_rate: int = 0


@dataclass
class SolutionRecord:
    solution_id: str
    title: str
    problem: str
    steps: List[str]
    keywords: List[str] = field(default_factory=list)
    regex: List[str] = field(default_factory=list)
    contexts: List[str] = field(default_factory=list)
    confidence: int = 70
    success_rate: int = 0
    created_at: str = ""
    modified_at: str = ""


@dataclass
class SolutionMatch:
    solution: SolutionRecord
    score: int
    reasons: List[str]


def generate_solution_id(title: str, problem: str, keywords: List[str]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    seed = f"{title}:{problem}:{','.join(keywords)}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
    if slug:
        return f"sol-{slug[:24]}-{digest}"
    return f"sol-{digest}"


def write_solution(details: SolutionDetails, repo_root: str, solution_id: Optional[str] = None) -> str:
    solutions_dir = os.path.join(repo_root, "docs", "solutions")
    os.makedirs(solutions_dir, exist_ok=True)
    solution_id = solution_id or generate_solution_id(details.title, details.problem, details.keywords)
    solution_path = os.path.join(solutions_dir, f"{solution_id}.md")
    if os.path.exists(solution_path):
        return solution_id

    now = datetime.now(timezone.utc).isoformat()
    lines = [
        f"# Solution: {details.title}",
        "",
        f"\"solution_id\": \"{solution_id}\"",
        f"\"title\": \"{details.title}\"",
        f"\"problem\": \"{details.problem}\"",
        f"\"keywords\": \"{_join_list(details.keywords)}\"",
        f"\"regex\": \"{_join_list(details.regex)}\"",
        f"\"contexts\": \"{_join_list(details.contexts)}\"",
        f"\"confidence\": {details.confidence}",
        f"\"success_rate\": {details.success_rate}",
        f"\"created_at\": \"{now}\"",
        f"\"modified_at\": \"{now}\"",
        "",
        "## Steps",
    ]
    if details.steps:
        for step in details.steps:
            lines.append(f"- {step}")
    else:
        lines.append("- TODO")
    lines.extend(["", "## Notes", "", ""])

    with open(solution_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    return solution_id


def load_solution(solution_path: str) -> SolutionRecord:
    metadata: Dict[str, str] = {}
    steps: List[str] = []
    in_steps = False
    with open(solution_path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.rstrip("\n")
            match = re.match(r"^\"([^\"]+)\":\s*(.+)$", stripped)
            if match:
                key = match.group(1)
                raw_value = match.group(2).strip()
                metadata[key] = _parse_value(raw_value)
                continue
            if stripped == "## Steps":
                in_steps = True
                continue
            if stripped.startswith("## ") and in_steps:
                in_steps = False
            if in_steps and stripped.startswith("- "):
                steps.append(stripped[2:].strip())

    return SolutionRecord(
        solution_id=str(metadata.get("solution_id", "")),
        title=str(metadata.get("title", "")),
        problem=str(metadata.get("problem", "")),
        steps=steps,
        keywords=_split_list(metadata.get("keywords")),
        regex=_split_list(metadata.get("regex")),
        contexts=_split_list(metadata.get("contexts")),
        confidence=int(metadata.get("confidence", 70) or 70),
        success_rate=int(metadata.get("success_rate", 0) or 0),
        created_at=str(metadata.get("created_at", "")),
        modified_at=str(metadata.get("modified_at", "")),
    )


def list_solutions(repo_root: str) -> List[SolutionRecord]:
    solutions_dir = os.path.join(repo_root, "docs", "solutions")
    if not os.path.isdir(solutions_dir):
        return []
    records: List[SolutionRecord] = []
    for name in sorted(os.listdir(solutions_dir)):
        if not name.endswith(".md"):
            continue
        records.append(load_solution(os.path.join(solutions_dir, name)))
    return records


def delete_solution(repo_root: str, solution_id: str) -> bool:
    solutions_dir = os.path.join(repo_root, "docs", "solutions")
    candidate = os.path.join(solutions_dir, f"{solution_id}.md")
    if os.path.exists(candidate):
        os.remove(candidate)
        return True
    if not os.path.isdir(solutions_dir):
        return False
    for name in os.listdir(solutions_dir):
        if name.startswith(solution_id) and name.endswith(".md"):
            os.remove(os.path.join(solutions_dir, name))
            return True
    return False


def match_solutions(
    issue: IssueRecord,
    repo_root: str,
    include_external: bool = False,
) -> List[SolutionMatch]:
    solutions = list_solutions(repo_root)
    if include_external:
        solutions.extend(list_external_solutions())
    if not solutions:
        return []

    matches: List[SolutionMatch] = []
    haystack = _build_issue_haystack(issue)
    contexts = _build_issue_contexts(issue)
    for solution in solutions:
        score, reasons = _score_solution(solution, haystack, contexts)
        if score > 0:
            matches.append(SolutionMatch(solution=solution, score=score, reasons=reasons))
    matches.sort(key=lambda item: item.score, reverse=True)
    return matches


def list_external_solutions() -> List[SolutionRecord]:
    home_index = os.path.expanduser("~/.maestro/repos.json")
    if not os.path.exists(home_index):
        return []
    try:
        import json

        with open(home_index, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return []

    records: List[SolutionRecord] = []
    for entry in data.get("repositories", []):
        repo_path = entry.get("path")
        if not repo_path:
            continue
        solutions_dir = os.path.join(repo_path, "docs", "solutions")
        if not os.path.isdir(solutions_dir):
            continue
        for name in sorted(os.listdir(solutions_dir)):
            if not name.endswith(".md"):
                continue
            try:
                records.append(load_solution(os.path.join(solutions_dir, name)))
            except OSError:
                continue
    return records


def _parse_value(raw_value: str):
    if raw_value.startswith('"') and raw_value.endswith('"'):
        return raw_value.strip('"')
    if raw_value.lower() in ("true", "false"):
        return raw_value.lower() == "true"
    if re.match(r"^\d+$", raw_value):
        return int(raw_value)
    return raw_value


def _join_list(items: List[str]) -> str:
    return ", ".join([item.strip() for item in items if item.strip()])


def _split_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _build_issue_haystack(issue: IssueRecord) -> str:
    parts = [
        issue.title,
        issue.description,
        issue.file,
        issue.tool or "",
        issue.rule or "",
    ]
    return "\n".join([part for part in parts if part])


def _build_issue_contexts(issue: IssueRecord) -> List[str]:
    contexts = [issue.issue_type, issue.source]
    if issue.tool:
        contexts.append(issue.tool)
    if issue.file:
        _, ext = os.path.splitext(issue.file)
        if ext:
            contexts.append(ext.lstrip("."))
    return [ctx.lower() for ctx in contexts if ctx]


def _score_solution(solution: SolutionRecord, haystack: str, contexts: List[str]) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []
    haystack_lower = haystack.lower()

    for keyword in solution.keywords:
        if keyword.lower() in haystack_lower:
            score += 10
            reasons.append(f"keyword:{keyword}")

    for pattern in solution.regex:
        try:
            if re.search(pattern, haystack, re.IGNORECASE):
                score += 15
                reasons.append(f"regex:{pattern}")
        except re.error:
            continue

    for context in solution.contexts:
        if context.lower() in contexts:
            score += 8
            reasons.append(f"context:{context}")

    if solution.problem and solution.problem.lower() in haystack_lower:
        score += 5
        reasons.append("problem")

    weighted = min(100, score)
    if solution.confidence:
        weighted = min(100, int((solution.confidence * 0.6) + (score * 0.4)))

    return weighted, reasons

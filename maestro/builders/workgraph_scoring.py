"""Deterministic WorkGraph scoring engine for investor/purpose prioritization.

This module provides deterministic (no AI) scoring and ranking of WorkGraph tasks
based on effort, impact, risk, and purpose heuristics.

Supports three profiles:
- investor: maximize ROI (impact/effort) and reduce risk
- purpose: maximize mission-alignment/user-value
- default: balanced approach

All scoring is deterministic and repo-agnostic.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from ..data.workgraph_schema import WorkGraph, Task, Phase


@dataclass
class ScoreResult:
    """Result of scoring a single task."""
    task_id: str
    task_title: str
    score: float
    effort_bucket: int  # 1-5 (inferred or provided)
    impact: int  # 0-5 (inferred or provided)
    risk: int  # 0-5 (inferred or provided)
    purpose: int  # 0-5 (inferred or provided)
    rationale: str  # Human-readable "why" string
    inferred_fields: List[str] = field(default_factory=list)  # Which fields were inferred


@dataclass
class RankedWorkGraph:
    """WorkGraph with ranked tasks."""
    workgraph_id: str
    profile: str
    ranked_tasks: List[ScoreResult]
    summary: Dict[str, Any] = field(default_factory=dict)


# META: Effort bucket conversion (minutes → bucket 1-5)
EFFORT_BUCKETS = [
    (5, 1),    # 0-5 min → bucket 1 (trivial)
    (15, 2),   # 6-15 min → bucket 2 (quick)
    (60, 3),   # 16-60 min → bucket 3 (medium)
    (240, 4),  # 61-240 min (4h) → bucket 4 (long)
    (float('inf'), 5)  # >240 min → bucket 5 (very long)
]


def _effort_to_bucket(effort_min: int, effort_max: int) -> int:
    """Convert effort range (minutes) to bucket 1-5."""
    avg_effort = (effort_min + effort_max) / 2
    for threshold, bucket in EFFORT_BUCKETS:
        if avg_effort <= threshold:
            return bucket
    return 5


def _infer_effort_from_task(task: Task, context: Dict[str, Any]) -> int:
    """Infer effort bucket (1-5) from task characteristics.

    Heuristics:
    - More commands/DoDs → more effort
    - safe_to_execute=False → add effort penalty
    - tags: "build", "test" → higher effort baseline
    - tags: "docs", "cleanup" → lower effort baseline
    """
    # Start with base effort
    base_effort = 3  # Default: medium

    # Count commands in DoDs
    cmd_count = sum(1 for dod in task.definition_of_done if dod.kind == "command")
    verif_count = sum(1 for verif in task.verification if verif.kind == "command")
    total_commands = cmd_count + verif_count

    if total_commands == 0:
        effort = 2  # Low effort (only file checks)
    elif total_commands == 1:
        effort = 2  # Single command
    elif total_commands <= 3:
        effort = 3  # Medium
    elif total_commands <= 6:
        effort = 4  # Long
    else:
        effort = 5  # Very long (>6 commands)

    # Unsafe tasks require more care (add 1)
    if not task.safe_to_execute:
        effort = min(5, effort + 1)

    # Tag-based adjustments
    if any(tag in task.tags for tag in ["build", "test", "integration"]):
        effort = min(5, effort + 1)
    if any(tag in task.tags for tag in ["docs", "cleanup", "trivial"]):
        effort = max(1, effort - 1)

    return effort


def _infer_impact_from_task(task: Task, context: Dict[str, Any]) -> int:
    """Infer impact score (0-5) from task characteristics.

    Heuristics:
    - domain=issues → check if task addresses blockers
    - tags: "build", "fix", "blocker", "gate" → high impact
    - tags: "cleanup", "refactor", "docs" → medium-low impact
    - outputs → higher impact (produces artifacts)
    """
    base_impact = 2  # Default: medium-low

    # Check context for domain-specific hints
    domain = context.get("domain", "general")
    if domain == "issues":
        # If this task mentions "blocker" or "fix" in title/intent, boost impact
        text_to_check = (task.title + " " + task.intent).lower()
        if any(keyword in text_to_check for keyword in ["blocker", "blocking", "critical", "urgent"]):
            base_impact = 5
        elif any(keyword in text_to_check for keyword in ["fix", "bug", "error", "failure"]):
            base_impact = 4

    # Tag-based impact
    high_impact_tags = ["build", "fix", "blocker", "gate", "ci", "test", "critical"]
    medium_impact_tags = ["feature", "enhancement", "improvement"]
    low_impact_tags = ["cleanup", "refactor", "docs", "trivial", "formatting"]

    if any(tag in task.tags for tag in high_impact_tags):
        base_impact = max(base_impact, 4)
    elif any(tag in task.tags for tag in medium_impact_tags):
        base_impact = max(base_impact, 3)
    elif any(tag in task.tags for tag in low_impact_tags):
        base_impact = min(base_impact, 2)

    # Tasks with outputs (artifacts) tend to have higher impact
    if task.outputs:
        base_impact = min(5, base_impact + 1)

    return base_impact


def _infer_risk_from_task(task: Task, context: Dict[str, Any]) -> int:
    """Infer risk score (0-5) from task characteristics.

    Heuristics:
    - safe_to_execute=False → high risk
    - Many outputs → higher risk (modifies many files)
    - tags: "unsafe", "experimental" → high risk
    - tags: "readonly", "docs" → low risk
    """
    base_risk = 2  # Default: medium-low

    # Unsafe tasks are risky
    if not task.safe_to_execute:
        base_risk = 4

    # More outputs = more potential for breaking things
    if len(task.outputs) > 5:
        base_risk = min(5, base_risk + 2)
    elif len(task.outputs) > 2:
        base_risk = min(5, base_risk + 1)

    # Tag-based risk
    high_risk_tags = ["unsafe", "experimental", "migration", "destructive"]
    low_risk_tags = ["readonly", "docs", "analysis", "trivial"]

    if any(tag in task.tags for tag in high_risk_tags):
        base_risk = 5
    elif any(tag in task.tags for tag in low_risk_tags):
        base_risk = max(0, base_risk - 2)

    # Check risk dict (legacy field)
    if task.risk and task.risk.get("level") == "high":
        base_risk = max(base_risk, 4)
    elif task.risk and task.risk.get("level") == "low":
        base_risk = min(base_risk, 1)

    return base_risk


def _infer_purpose_from_task(task: Task, context: Dict[str, Any]) -> int:
    """Infer purpose score (0-5) from task characteristics.

    Purpose = mission-alignment / user-value / non-ROI strategic value

    Heuristics:
    - tags: "docs", "user-facing", "accessibility", "ux" → high purpose
    - tags: "build", "internal", "cleanup" → low purpose
    - domain=issues and user-facing → high purpose
    """
    base_purpose = 2  # Default: medium-low

    # Tag-based purpose
    high_purpose_tags = ["docs", "user-facing", "accessibility", "ux", "onboarding", "tutorial", "examples"]
    medium_purpose_tags = ["feature", "enhancement", "api", "cli"]
    low_purpose_tags = ["build", "internal", "cleanup", "refactor", "tooling"]

    if any(tag in task.tags for tag in high_purpose_tags):
        base_purpose = 5
    elif any(tag in task.tags for tag in medium_purpose_tags):
        base_purpose = 3
    elif any(tag in task.tags for tag in low_purpose_tags):
        base_purpose = 1

    # Check title/intent for user-facing keywords
    text_to_check = (task.title + " " + task.intent).lower()
    if any(keyword in text_to_check for keyword in ["user", "customer", "documentation", "guide", "tutorial"]):
        base_purpose = max(base_purpose, 4)

    return base_purpose


def score_task(task: Task, profile: str, context: Dict[str, Any]) -> ScoreResult:
    """Score a single task using deterministic heuristics.

    Args:
        task: The task to score
        profile: Scoring profile ("investor", "purpose", "default")
        context: Additional context (domain, hints, etc.)

    Returns:
        ScoreResult with score, rationale, and inferred fields
    """
    inferred_fields = []

    # Get or infer effort
    if task.effort is not None:
        effort_bucket = _effort_to_bucket(task.effort['min'], task.effort['max'])
    else:
        effort_bucket = _infer_effort_from_task(task, context)
        inferred_fields.append("effort")

    # Get or infer impact
    if task.impact is not None:
        impact = task.impact
    else:
        impact = _infer_impact_from_task(task, context)
        inferred_fields.append("impact")

    # Get or infer risk (use risk_score if available, fallback to risk dict or infer)
    if task.risk_score is not None:
        risk = task.risk_score
    else:
        risk = _infer_risk_from_task(task, context)
        inferred_fields.append("risk")

    # Get or infer purpose
    if task.purpose is not None:
        purpose = task.purpose
    else:
        purpose = _infer_purpose_from_task(task, context)
        inferred_fields.append("purpose")

    # Calculate score based on profile
    if profile == "investor":
        # Investor: maximize ROI (impact*3 + purpose) - (effort*2 + risk*2)
        score = (impact * 3 + purpose) - (effort_bucket * 2 + risk * 2)
    elif profile == "purpose":
        # Purpose: maximize mission-alignment (purpose*3 + impact) - (effort + risk)
        score = (purpose * 3 + impact) - (effort_bucket + risk)
    else:  # default
        # Default: balanced (impact*2 + purpose) - (effort + risk)
        score = (impact * 2 + purpose) - (effort_bucket + risk)

    # Build rationale
    effort_labels = ["", "trivial", "quick", "medium", "long", "very long"]
    impact_labels = ["none", "minimal", "low", "medium", "high", "critical"]
    risk_labels = ["none", "minimal", "low", "medium", "high", "critical"]
    purpose_labels = ["none", "minimal", "low", "medium", "high", "critical"]

    rationale_parts = []
    rationale_parts.append(f"impact: {impact_labels[impact]} ({impact})")
    rationale_parts.append(f"effort: {effort_labels[effort_bucket]} ({effort_bucket})")
    rationale_parts.append(f"risk: {risk_labels[risk]} ({risk})")
    rationale_parts.append(f"purpose: {purpose_labels[purpose]} ({purpose})")
    rationale_parts.append(f"{profile}_score: {score}")

    if inferred_fields:
        rationale_parts.append(f"(inferred: {', '.join(inferred_fields)})")

    rationale = "; ".join(rationale_parts)

    return ScoreResult(
        task_id=task.id,
        task_title=task.title,
        score=score,
        effort_bucket=effort_bucket,
        impact=impact,
        risk=risk,
        purpose=purpose,
        rationale=rationale,
        inferred_fields=inferred_fields
    )


def rank_workgraph(workgraph: WorkGraph, profile: str = "default", context: Optional[Dict[str, Any]] = None) -> RankedWorkGraph:
    """Rank all tasks in a WorkGraph using deterministic scoring.

    Args:
        workgraph: The WorkGraph to rank
        profile: Scoring profile ("investor", "purpose", "default")
        context: Optional context dict (domain, hints, etc.)

    Returns:
        RankedWorkGraph with tasks sorted by score (highest first)
    """
    if context is None:
        context = {}

    # Add workgraph domain to context
    context["domain"] = workgraph.domain

    # Score all tasks across all phases
    scored_tasks = []
    for phase in workgraph.phases:
        for task in phase.tasks:
            score_result = score_task(task, profile, context)
            scored_tasks.append(score_result)

    # Sort by score (descending)
    ranked_tasks = sorted(scored_tasks, key=lambda x: x.score, reverse=True)

    # Build summary buckets
    quick_wins = [t for t in ranked_tasks if t.score >= 5 and t.effort_bucket <= 2]
    risky_bets = [t for t in ranked_tasks if t.risk >= 4]
    purpose_wins = [t for t in ranked_tasks if t.purpose >= 4]

    summary = {
        "total_tasks": len(ranked_tasks),
        "profile": profile,
        "quick_wins": len(quick_wins),
        "risky_bets": len(risky_bets),
        "purpose_wins": len(purpose_wins),
        "top_score": ranked_tasks[0].score if ranked_tasks else 0,
        "avg_score": sum(t.score for t in ranked_tasks) / len(ranked_tasks) if ranked_tasks else 0
    }

    return RankedWorkGraph(
        workgraph_id=workgraph.id,
        profile=profile,
        ranked_tasks=ranked_tasks,
        summary=summary
    )


def get_top_recommendations(ranked_wg: RankedWorkGraph, top_n: int = 3) -> List[ScoreResult]:
    """Get top N recommended tasks from a ranked WorkGraph.

    Args:
        ranked_wg: RankedWorkGraph (already sorted)
        top_n: Number of top tasks to return

    Returns:
        List of top N ScoreResults
    """
    return ranked_wg.ranked_tasks[:top_n]

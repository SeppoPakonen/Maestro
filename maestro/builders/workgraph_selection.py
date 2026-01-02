"""WorkGraph task selection with dependency closure.

This module provides deterministic selection of top-N tasks from a WorkGraph
with automatic inclusion of transitive dependencies.
"""
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass

from maestro.data.workgraph_schema import WorkGraph, Task
from maestro.builders.workgraph_scoring import rank_workgraph, RankedWorkGraph, ScoreResult


@dataclass
class SelectionResult:
    """Result of selecting top-N tasks with dependency closure."""
    top_task_ids: List[str]  # Original top-N selected tasks (in ranking order)
    closure_task_ids: List[str]  # Dependencies added via closure (excl top tasks)
    ordered_task_ids: List[str]  # Final ordered list: deps first (topo), then top tasks
    all_tasks: Dict[str, Task]  # Map of task_id -> Task for all selected tasks
    ranked_tasks: List[ScoreResult]  # Full ranking (for reference)
    warnings: List[str]  # Any warnings during selection (e.g., cycles)


def select_top_n_with_closure(
    workgraph: WorkGraph,
    profile: str = "default",
    top_n: int = 5,
    context: Optional[Dict[str, Any]] = None
) -> SelectionResult:
    """Select top-N tasks by score with transitive dependency closure.

    Args:
        workgraph: WorkGraph to select from
        profile: Scoring profile ("investor", "purpose", "default")
        top_n: Number of top tasks to select
        context: Optional context for scoring

    Returns:
        SelectionResult with top tasks, closure, and deterministic ordering

    Algorithm:
        1. Score and rank all tasks using workgraph_scoring
        2. Select top N tasks (by score DESC, task_id ASC for ties)
        3. Compute transitive closure of dependencies
        4. Topologically sort dependencies (deterministic)
        5. Return: deps first (topo order), then top tasks (ranking order)
    """
    warnings = []

    # Step 1: Rank all tasks
    ranked_wg = rank_workgraph(workgraph, profile=profile, context=context)
    ranked_tasks = ranked_wg.ranked_tasks

    # Build task map (task_id -> Task)
    all_tasks_map: Dict[str, Task] = {}
    for phase in workgraph.phases:
        for task in phase.tasks:
            all_tasks_map[task.id] = task

    # Step 2: Select top N tasks (stable sorting: score DESC, task_id ASC)
    # ranked_tasks is already sorted by score DESC
    # For ties, sort by task_id ASC
    ranked_with_ties = sorted(ranked_tasks, key=lambda x: (-x.score, x.task_id))
    top_n_scored = ranked_with_ties[:top_n]
    top_task_ids = [t.task_id for t in top_n_scored]

    # Step 3: Compute transitive dependency closure
    closure_ids = _compute_dependency_closure(top_task_ids, all_tasks_map)

    # closure_ids should NOT include top_task_ids (per spec)
    closure_only = [tid for tid in closure_ids if tid not in top_task_ids]

    # Step 4: Topologically sort dependencies (deterministic)
    try:
        deps_ordered = _topological_sort_deterministic(closure_only, all_tasks_map)
    except ValueError as e:
        # Cycle detected - use stable fallback
        warnings.append(f"Dependency cycle detected: {e}. Using stable task_id sort as fallback.")
        deps_ordered = sorted(closure_only)

    # Step 5: Build final ordered list
    # Dependencies first (topologically sorted), then top tasks (ranking order)
    ordered_task_ids = deps_ordered + top_task_ids

    # Build final task map (only selected tasks)
    selected_tasks = {tid: all_tasks_map[tid] for tid in ordered_task_ids}

    return SelectionResult(
        top_task_ids=top_task_ids,
        closure_task_ids=closure_only,
        ordered_task_ids=ordered_task_ids,
        all_tasks=selected_tasks,
        ranked_tasks=ranked_tasks,
        warnings=warnings
    )


def _compute_dependency_closure(
    initial_task_ids: List[str],
    all_tasks: Dict[str, Task]
) -> List[str]:
    """Compute transitive closure of dependencies.

    Args:
        initial_task_ids: Starting set of task IDs
        all_tasks: Map of all tasks in WorkGraph

    Returns:
        List of all task IDs in transitive closure (including initial_task_ids)
    """
    closure: Set[str] = set()
    to_process: List[str] = list(initial_task_ids)

    while to_process:
        current_id = to_process.pop(0)

        if current_id in closure:
            continue

        closure.add(current_id)

        # Get task and its dependencies
        task = all_tasks.get(current_id)
        if task is None:
            # Task not found - skip (could be a dangling reference)
            continue

        # Add dependencies to process queue
        for dep_id in task.depends_on:
            if dep_id not in closure:
                to_process.append(dep_id)

    return list(closure)


def _topological_sort_deterministic(
    task_ids: List[str],
    all_tasks: Dict[str, Task]
) -> List[str]:
    """Topologically sort tasks by dependencies (deterministic).

    Args:
        task_ids: List of task IDs to sort
        all_tasks: Map of all tasks

    Returns:
        List of task IDs in topological order (dependencies first)

    Raises:
        ValueError: If a dependency cycle is detected

    Algorithm:
        Kahn's algorithm with deterministic tie-breaking (task_id ASC)
    """
    # Build dependency graph (only for tasks in task_ids)
    task_set = set(task_ids)
    in_degree: Dict[str, int] = {tid: 0 for tid in task_ids}
    adjacency: Dict[str, List[str]] = {tid: [] for tid in task_ids}

    for tid in task_ids:
        task = all_tasks.get(tid)
        if task is None:
            continue

        for dep_id in task.depends_on:
            # Only count dependencies within our subset
            if dep_id in task_set:
                adjacency[dep_id].append(tid)
                in_degree[tid] += 1

    # Kahn's algorithm with deterministic ordering
    result = []
    # Start with tasks that have no dependencies (in_degree == 0)
    # Sort by task_id for determinism
    queue = sorted([tid for tid in task_ids if in_degree[tid] == 0])

    while queue:
        # Pop first (smallest task_id due to sorting)
        current = queue.pop(0)
        result.append(current)

        # Reduce in-degree for dependent tasks
        for neighbor in sorted(adjacency.get(current, [])):  # Sort for determinism
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                # Add to queue in sorted position
                queue.append(neighbor)
                queue.sort()  # Keep queue sorted

    # Check for cycles
    if len(result) != len(task_ids):
        # Cycle detected
        remaining = set(task_ids) - set(result)
        raise ValueError(f"Dependency cycle detected involving tasks: {sorted(remaining)}")

    return result


def format_selection_summary(
    selection: SelectionResult,
    profile: str,
    max_ids_per_list: int = 10
) -> str:
    """Format a human-readable summary of the selection.

    Args:
        selection: SelectionResult from select_top_n_with_closure
        profile: Scoring profile used
        max_ids_per_list: Maximum IDs to show per list (rest shown as "+N more")

    Returns:
        Multi-line string summary
    """
    lines = []

    # Top tasks selected
    top_ids = selection.top_task_ids
    if len(top_ids) <= max_ids_per_list:
        top_str = ", ".join(top_ids)
    else:
        shown = top_ids[:max_ids_per_list]
        remaining = len(top_ids) - max_ids_per_list
        top_str = ", ".join(shown) + f" +{remaining} more"

    lines.append(f"Top tasks selected ({profile} profile): {top_str}")

    # Dependencies added
    closure_ids = selection.closure_task_ids
    if closure_ids:
        if len(closure_ids) <= max_ids_per_list:
            closure_str = ", ".join(closure_ids)
        else:
            shown = closure_ids[:max_ids_per_list]
            remaining = len(closure_ids) - max_ids_per_list
            closure_str = ", ".join(shown) + f" +{remaining} more"
        lines.append(f"Dependencies added: {closure_str}")
    else:
        lines.append("Dependencies added: (none)")

    # Total materialized
    total = len(selection.ordered_task_ids)
    lines.append(f"Materialized total: {total} tasks")

    # Warnings
    if selection.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in selection.warnings:
            lines.append(f"  - {warning}")

    return "\n".join(lines)

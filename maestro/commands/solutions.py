from __future__ import annotations

import argparse
import os
import subprocess
from typing import Optional

from maestro.solutions.solution_store import (
    SolutionDetails,
    delete_solution,
    list_external_solutions,
    list_solutions,
    load_solution,
    write_solution,
)


def add_solutions_parser(subparsers) -> argparse.ArgumentParser:
    solutions_parser = subparsers.add_parser("solutions", help="Solution management commands")
    solutions_subparsers = solutions_parser.add_subparsers(dest="solutions_subcommand", help="Solutions subcommands")

    add_parser = solutions_subparsers.add_parser("add", help="Add a new solution")
    add_parser.add_argument("--id", dest="solution_id", help="Solution ID override")
    add_parser.add_argument("--title", help="Solution title")
    add_parser.add_argument("--problem", help="Problem description")
    add_parser.add_argument("--keyword", action="append", default=[], help="Keyword match (repeatable)")
    add_parser.add_argument("--regex", action="append", default=[], help="Regex match (repeatable)")
    add_parser.add_argument("--context", action="append", default=[], help="Context match (repeatable)")
    add_parser.add_argument("--step", action="append", default=[], help="Solution step (repeatable)")
    add_parser.add_argument("--confidence", type=int, default=70, help="Applicability confidence")
    add_parser.add_argument("--success-rate", type=int, default=0, help="Success rate")
    add_parser.add_argument("--edit", action="store_true", help="Open in $EDITOR after creation")

    list_parser = solutions_subparsers.add_parser("list", aliases=["ls"], help="List solutions")
    list_parser.add_argument("--external", action="store_true", help="Include external solutions")

    remove_parser = solutions_subparsers.add_parser("remove", aliases=["rm"], help="Remove a solution")
    remove_parser.add_argument("solution_id", help="Solution ID to remove")

    show_parser = solutions_subparsers.add_parser("show", help="Show solution details")
    show_parser.add_argument("solution_id", help="Solution ID to show")

    edit_parser = solutions_subparsers.add_parser("edit", help="Edit a solution in $EDITOR")
    edit_parser.add_argument("solution_id", help="Solution ID to edit")

    return solutions_parser


def handle_solutions_command(args: argparse.Namespace) -> int:
    repo_root = _find_repo_root() or os.getcwd()
    subcommand = getattr(args, "solutions_subcommand", None)
    if subcommand in (None, "list"):
        return _handle_list(repo_root, include_external=getattr(args, "external", False))
    if subcommand == "show":
        return _handle_show(repo_root, args.solution_id)
    if subcommand == "add":
        return _handle_add(repo_root, args)
    if subcommand == "remove":
        return _handle_remove(repo_root, args.solution_id)
    if subcommand == "edit":
        return _handle_edit(repo_root, args.solution_id)
    print(f"Unknown solutions subcommand: {subcommand}")
    return 1


def _handle_list(repo_root: str, include_external: bool) -> int:
    solutions = list_solutions(repo_root)
    if include_external:
        solutions.extend(list_external_solutions())
    if not solutions:
        print("No solutions found.")
        return 0
    for solution in solutions:
        contexts = ", ".join(solution.contexts) if solution.contexts else "-"
        print(f"- {solution.solution_id} {solution.title} [{contexts}]")
    return 0


def _handle_show(repo_root: str, solution_id: str) -> int:
    solution_path = _find_solution_path(repo_root, solution_id)
    if not solution_path:
        print(f"Solution not found: {solution_id}")
        return 1
    record = load_solution(solution_path)
    print(f"ID: {record.solution_id}")
    print(f"Title: {record.title}")
    print(f"Problem: {record.problem}")
    print(f"Confidence: {record.confidence}")
    print(f"Success rate: {record.success_rate}")
    if record.keywords:
        print(f"Keywords: {', '.join(record.keywords)}")
    if record.regex:
        print(f"Regex: {', '.join(record.regex)}")
    if record.contexts:
        print(f"Contexts: {', '.join(record.contexts)}")
    if record.steps:
        print("Steps:")
        for step in record.steps:
            print(f"- {step}")
    return 0


def _handle_add(repo_root: str, args: argparse.Namespace) -> int:
    title = args.title or "New Solution"
    problem = args.problem or "Describe the problem this solution addresses."
    steps = args.step or ["Fill in steps."]
    details = SolutionDetails(
        title=title,
        problem=problem,
        steps=steps,
        keywords=args.keyword or [],
        regex=args.regex or [],
        contexts=args.context or [],
        confidence=args.confidence,
        success_rate=args.success_rate,
    )
    solution_id = write_solution(details, repo_root, solution_id=args.solution_id)
    solution_path = os.path.join(repo_root, "docs", "solutions", f"{solution_id}.md")
    if args.edit or not args.title or not args.problem:
        _open_editor(solution_path)
    print(f"Solution created: {solution_id}")
    return 0


def _handle_remove(repo_root: str, solution_id: str) -> int:
    removed = delete_solution(repo_root, solution_id)
    if not removed:
        print(f"Solution not found: {solution_id}")
        return 1
    print(f"Removed {solution_id}")
    return 0


def _handle_edit(repo_root: str, solution_id: str) -> int:
    solution_path = _find_solution_path(repo_root, solution_id)
    if not solution_path:
        print(f"Solution not found: {solution_id}")
        return 1
    _open_editor(solution_path)
    return 0


def _find_solution_path(repo_root: str, solution_id: str) -> Optional[str]:
    solutions_dir = os.path.join(repo_root, "docs", "solutions")
    candidate = os.path.join(solutions_dir, f"{solution_id}.md")
    if os.path.exists(candidate):
        return candidate
    if not os.path.isdir(solutions_dir):
        return None
    for name in os.listdir(solutions_dir):
        if name.startswith(solution_id) and name.endswith(".md"):
            return os.path.join(solutions_dir, name)
    return None


def _open_editor(path: str) -> None:
    editor = os.environ.get("EDITOR", "vim")
    try:
        subprocess.run([editor, path])
    except OSError as exc:
        print(f"Error opening editor: {exc}")


def _find_repo_root() -> Optional[str]:
    current_dir = os.getcwd()
    while current_dir != "/":
        if os.path.exists(os.path.join(current_dir, ".maestro")):
            return current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir
    return None

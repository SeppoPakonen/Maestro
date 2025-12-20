from __future__ import annotations

import argparse
from datetime import datetime
import os
import re
import textwrap
from typing import List, Optional

from maestro.ai.client import ExternalCommandClient
from maestro.issues.issue_store import (
    list_issues,
    load_issue,
    rollback_issue_state,
    update_issue_metadata,
    update_issue_priority,
    update_issue_section,
    update_issue_state,
)
from maestro.issues.model import ISSUE_TYPES, ISSUE_STATES
from maestro.solutions.solution_store import SolutionMatch, match_solutions

ISSUE_TYPE_ORDER = [
    "hier",
    "convention",
    "build",
    "runtime",
    "features",
    "product",
    "look",
    "ux",
]


def add_issues_parser(subparsers) -> argparse.ArgumentParser:
    issues_parser = subparsers.add_parser("issues", help="Issue tracking commands")
    issues_subparsers = issues_parser.add_subparsers(dest="issues_subcommand", help="Issues subcommands")

    list_parser = issues_subparsers.add_parser("list", aliases=["ls"], help="List issues")
    list_parser.add_argument("--type", help="Filter by issue type")

    show_parser = issues_subparsers.add_parser("show", help="Show issue details")
    show_parser.add_argument("issue_id", help="Issue ID to show")

    state_parser = issues_subparsers.add_parser("state", help="Update issue state")
    state_parser.add_argument("issue_id", help="Issue ID to update")
    state_parser.add_argument("state", help="New state")

    rollback_parser = issues_subparsers.add_parser("rollback", help="Rollback issue state")
    rollback_parser.add_argument("issue_id", help="Issue ID to rollback")

    react_parser = issues_subparsers.add_parser("react", help="React to an issue and match solutions")
    react_parser.add_argument("issue_id", help="Issue ID to react to")
    react_parser.add_argument("--external", action="store_true", help="Include external solutions")

    analyze_parser = issues_subparsers.add_parser("analyze", help="Analyze an issue")
    analyze_parser.add_argument("issue_id", help="Issue ID to analyze")
    analyze_parser.add_argument("--no-ai", action="store_true", help="Skip AI analysis and use manual summary")
    analyze_parser.add_argument("--summary", help="Analysis summary override")
    analyze_parser.add_argument("--confidence", type=int, help="Confidence score 0-100")
    analyze_parser.add_argument("--external", action="store_true", help="Include external solutions")

    decide_parser = issues_subparsers.add_parser("decide", help="Decide what to do with an issue")
    decide_parser.add_argument("issue_id", help="Issue ID to decide")
    decide_parser.add_argument(
        "--decision",
        choices=["approve", "reject", "defer", "cancel"],
        help="Decision override",
    )
    decide_parser.add_argument("--auto", action="store_true", help="Auto-approve when confidence >= 80")
    decide_parser.add_argument("--priority", type=int, help="Priority for defer decision")

    fix_parser = issues_subparsers.add_parser("fix", help="Start or complete fix phase")
    fix_parser.add_argument("issue_id", help="Issue ID to fix")
    fix_parser.add_argument("--complete", action="store_true", help="Mark issue as fixed after session creation")
    fix_parser.add_argument("--external", action="store_true", help="Include external solutions")

    issue_type_order = [issue_type for issue_type in ISSUE_TYPE_ORDER if issue_type in ISSUE_TYPES]
    extra_types = sorted(set(ISSUE_TYPES) - set(issue_type_order))
    for issue_type in issue_type_order + extra_types:
        type_parser = issues_subparsers.add_parser(issue_type, help=f"List {issue_type} issues")
        type_parser.set_defaults(issue_type=issue_type)

    return issues_parser


def handle_issues_command(args: argparse.Namespace) -> int:
    repo_root = _find_repo_root() or os.getcwd()
    subcommand = getattr(args, "issues_subcommand", None)
    if subcommand in (None, "list"):
        issue_type = getattr(args, "type", None)
        if subcommand is None and hasattr(args, "issue_type"):
            issue_type = args.issue_type
        return _handle_list(repo_root, issue_type)
    if subcommand == "show":
        return _handle_show(repo_root, args.issue_id)
    if subcommand == "state":
        return _handle_state(repo_root, args.issue_id, args.state)
    if subcommand == "rollback":
        return _handle_rollback(repo_root, args.issue_id)
    if subcommand == "react":
        return _handle_react(repo_root, args.issue_id, args.external)
    if subcommand == "analyze":
        return _handle_analyze(
            repo_root,
            args.issue_id,
            use_ai=not args.no_ai,
            summary=args.summary,
            confidence=args.confidence,
            include_external=args.external,
        )
    if subcommand == "decide":
        return _handle_decide(
            repo_root,
            args.issue_id,
            decision=args.decision,
            auto=args.auto,
            priority=args.priority,
        )
    if subcommand == "fix":
        return _handle_fix(repo_root, args.issue_id, complete=args.complete, include_external=args.external)
    if hasattr(args, "issue_type"):
        return _handle_list(repo_root, args.issue_type)
    print(f"Unknown issues subcommand: {subcommand}")
    return 1


def _handle_list(repo_root: str, issue_type: str | None) -> int:
    if issue_type and issue_type not in ISSUE_TYPES:
        print(f"Unknown issue type: {issue_type}")
        return 1
    issues = list_issues(repo_root, issue_type=issue_type)
    if not issues:
        print("No issues found.")
        return 0
    for issue in issues:
        location = f"{issue.file}:{issue.line}:{issue.column}".rstrip(":0")
        print(f"- {issue.issue_id} [{issue.issue_type}] {issue.state} {issue.title}")
        if location:
            print(f"  {location}")
    return 0


def _handle_show(repo_root: str, issue_id: str) -> int:
    issue_path = _find_issue_path(repo_root, issue_id)
    if not issue_path:
        print(f"Issue not found: {issue_id}")
        return 1
    record = load_issue(issue_path)
    print(f"ID: {record.issue_id}")
    print(f"Type: {record.issue_type}")
    print(f"State: {record.state}")
    print(f"Priority: {record.priority}")
    print(f"Title: {record.title}")
    print(f"Description: {record.description}")
    location = f"{record.file}:{record.line}:{record.column}".rstrip(":0")
    print(f"Location: {location or 'N/A'}")
    print(f"Created: {record.created_at}")
    print(f"Modified: {record.modified_at}")
    if record.tool:
        print(f"Tool: {record.tool}")
    if record.rule:
        print(f"Rule: {record.rule}")
    if record.solutions:
        print(f"Solutions: {', '.join(record.solutions)}")
    if record.analysis_summary:
        print(f"Analysis: {record.analysis_summary}")
    if record.analysis_confidence:
        print(f"Confidence: {record.analysis_confidence}")
    if record.decision:
        print(f"Decision: {record.decision}")
    if record.fix_session:
        print(f"Fix session: {record.fix_session}")
    return 0


def _handle_state(repo_root: str, issue_id: str, state: str) -> int:
    if state not in ISSUE_STATES:
        print(f"Invalid state '{state}'. Valid: {', '.join(ISSUE_STATES)}")
        return 1
    try:
        updated = update_issue_state(repo_root, issue_id, state)
    except ValueError as exc:
        print(str(exc))
        return 1
    if not updated:
        print(f"Issue not found: {issue_id}")
        return 1
    print(f"Issue {issue_id} -> {state}")
    return 0


def _handle_rollback(repo_root: str, issue_id: str) -> int:
    rolled_back = rollback_issue_state(repo_root, issue_id)
    if not rolled_back:
        print(f"No rollback available for {issue_id}")
        return 1
    print(f"Rolled back {issue_id}")
    return 0


def _handle_react(repo_root: str, issue_id: str, include_external: bool) -> int:
    issue_path = _find_issue_path(repo_root, issue_id)
    if not issue_path:
        print(f"Issue not found: {issue_id}")
        return 1
    record = load_issue(issue_path)
    matches = match_solutions(record, repo_root, include_external=include_external)
    solution_ids = [match.solution.solution_id for match in matches]
    update_issue_state(repo_root, record.issue_id, "reacted")
    if solution_ids:
        update_issue_metadata(repo_root, record.issue_id, "solutions", ", ".join(solution_ids))
        summary = [
            "Matched solutions:",
            *[f"- {match.solution.solution_id} ({match.score})" for match in matches[:5]],
        ]
    else:
        summary = ["No matching solutions found."]
    update_issue_section(repo_root, record.issue_id, "Reaction", summary)
    if solution_ids:
        print(f"Reacted to {record.issue_id}: {', '.join(solution_ids[:5])}")
    else:
        print(f"Reacted to {record.issue_id}: no matches")
    return 0


def _handle_analyze(
    repo_root: str,
    issue_id: str,
    use_ai: bool,
    summary: Optional[str],
    confidence: Optional[int],
    include_external: bool,
) -> int:
    issue_path = _find_issue_path(repo_root, issue_id)
    if not issue_path:
        print(f"Issue not found: {issue_id}")
        return 1
    record = load_issue(issue_path)
    matches = match_solutions(record, repo_root, include_external=include_external)
    solution_context = "\n".join(
        [f"- {match.solution.solution_id}: {match.solution.problem}" for match in matches[:5]]
    )
    analysis_text = ""
    if use_ai:
        try:
            client = ExternalCommandClient()
            context = (
                "You are Maestro's issue analysis assistant. Provide a concise analysis, "
                "a confidence score 0-100, and suggested next steps."
            )
            issue_payload = textwrap.dedent(
                f"""
                Issue ID: {record.issue_id}
                Title: {record.title}
                Type: {record.issue_type}
                Description: {record.description}
                File: {record.file}:{record.line}:{record.column}
                Tool: {record.tool}
                Rule: {record.rule}
                Known solutions:
                {solution_context or '- none'}
                """
            ).strip()
            analysis_text = client.send_message(
                [{"role": "user", "content": issue_payload}],
                context,
            )
        except Exception as exc:
            print(f"AI analysis failed ({exc}). Falling back to manual summary.")

    if not analysis_text:
        analysis_text = summary or "Manual analysis required. Review issue context and propose a fix."

    parsed_confidence = _extract_confidence(analysis_text)
    final_confidence = confidence if confidence is not None else parsed_confidence or 50
    analysis_summary = summary or _first_sentence(analysis_text)

    update_issue_state(repo_root, record.issue_id, "analyzing")
    update_issue_metadata(repo_root, record.issue_id, "analysis_summary", analysis_summary)
    update_issue_metadata(repo_root, record.issue_id, "analysis_confidence", final_confidence)
    update_issue_section(repo_root, record.issue_id, "Analysis", analysis_text.splitlines())
    update_issue_state(repo_root, record.issue_id, "analyzed")

    print(f"Analyzed {record.issue_id} (confidence {final_confidence})")
    return 0


def _handle_decide(
    repo_root: str,
    issue_id: str,
    decision: Optional[str],
    auto: bool,
    priority: Optional[int],
) -> int:
    issue_path = _find_issue_path(repo_root, issue_id)
    if not issue_path:
        print(f"Issue not found: {issue_id}")
        return 1
    record = load_issue(issue_path)

    final_decision = decision
    if not final_decision and auto and record.analysis_confidence >= 80:
        final_decision = "approve"
    if not final_decision:
        prompt = "Decision [approve/reject/defer/cancel]: "
        final_decision = input(prompt).strip().lower()

    if final_decision not in {"approve", "reject", "defer", "cancel"}:
        print(f"Invalid decision: {final_decision}")
        return 1

    update_issue_metadata(repo_root, record.issue_id, "decision", final_decision)
    update_issue_section(repo_root, record.issue_id, "Decision", [f"Decision: {final_decision}"])

    if final_decision == "approve":
        update_issue_state(repo_root, record.issue_id, "decided")
        print(f"Decision recorded: approve ({record.issue_id})")
        return 0
    if final_decision == "defer":
        update_issue_state(repo_root, record.issue_id, "decided")
        if priority is None:
            priority = 75
        update_issue_priority(repo_root, record.issue_id, priority)
        print(f"Decision recorded: defer ({record.issue_id}) priority={priority}")
        return 0

    update_issue_state(repo_root, record.issue_id, "cancelled")
    print(f"Decision recorded: {final_decision} ({record.issue_id})")
    return 0


def _handle_fix(repo_root: str, issue_id: str, complete: bool, include_external: bool) -> int:
    issue_path = _find_issue_path(repo_root, issue_id)
    if not issue_path:
        print(f"Issue not found: {issue_id}")
        return 1
    record = load_issue(issue_path)
    matches = match_solutions(record, repo_root, include_external=include_external)
    session_path = _create_fix_session(repo_root, record, matches)
    update_issue_metadata(repo_root, record.issue_id, "fix_session", session_path)
    update_issue_state(repo_root, record.issue_id, "fixing")
    update_issue_section(
        repo_root,
        record.issue_id,
        "Fix",
        [f"Session: {session_path}", "Status: fixing"],
    )
    if complete:
        update_issue_state(repo_root, record.issue_id, "fixed")
        update_issue_section(
            repo_root,
            record.issue_id,
            "Fix",
            [f"Session: {session_path}", "Status: fixed"],
        )
        print(f"Fix marked complete for {record.issue_id}")
        return 0

    print(f"Fix session created for {record.issue_id}: {session_path}")
    return 0


def _extract_confidence(text: str) -> int:
    match = re.search(r"confidence\\s*[:=]\\s*(\\d{1,3})", text, re.IGNORECASE)
    if match:
        return min(100, max(0, int(match.group(1))))
    percent_match = re.search(r"(\\d{1,3})\\s*%+", text)
    if percent_match:
        return min(100, max(0, int(percent_match.group(1))))
    return 0


def _first_sentence(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return text.strip()[:200]


def _create_fix_session(
    repo_root: str,
    record,
    matches: List[SolutionMatch],
) -> str:
    sessions_dir = os.path.join(repo_root, "docs", "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name = f"issue-{record.issue_id}-fix-{timestamp}.md"
    session_path = os.path.join(sessions_dir, session_name)

    lines = [
        f"# Issue Fix Session: {record.issue_id}",
        "",
        f"Title: {record.title}",
        f"Type: {record.issue_type}",
        f"State: {record.state}",
        f"Location: {record.file}:{record.line}:{record.column}".rstrip(":0"),
        "",
        "## Matched Solutions",
    ]
    if matches:
        for match in matches[:5]:
            lines.append(f"- {match.solution.solution_id} ({match.score}) {match.solution.problem}")
    else:
        lines.append("- None")

    lines.extend(["", "## Plan"])
    if matches and matches[0].solution.steps:
        for step in matches[0].solution.steps:
            lines.append(f"- [ ] {step}")
    else:
        lines.append("- [ ] Investigate root cause")
        lines.append("- [ ] Implement fix")
        lines.append("- [ ] Run relevant tests")

    lines.extend(["", "## Notes", ""])

    with open(session_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    return session_path


def _find_issue_path(repo_root: str, issue_id: str) -> str | None:
    issues_dir = os.path.join(repo_root, "docs", "issues")
    candidate = os.path.join(issues_dir, f"{issue_id}.md")
    if os.path.exists(candidate):
        return candidate
    if not os.path.isdir(issues_dir):
        return None
    for name in os.listdir(issues_dir):
        if name.startswith(issue_id) and name.endswith(".md"):
            return os.path.join(issues_dir, name)
    return None


def _find_repo_root() -> str | None:
    current_dir = os.getcwd()
    while current_dir != "/":
        if os.path.exists(os.path.join(current_dir, ".maestro")):
            return current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir
    return None

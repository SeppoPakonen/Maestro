from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, List, Optional

from .issue_store import IssueDetails


@dataclass
class ParsedIssue:
    issue_type: str
    title: str
    description: str
    file: str = ""
    line: int = 0
    column: int = 0
    tool: Optional[str] = None
    rule: Optional[str] = None

    def to_issue_details(self, source: str) -> IssueDetails:
        return IssueDetails(
            issue_type=self.issue_type,
            title=self.title,
            description=self.description,
            file=self.file,
            line=self.line,
            column=self.column,
            source=source,
            tool=self.tool,
            rule=self.rule,
        )


_MSVC_RE = re.compile(
    r"^(?P<file>.+)\((?P<line>\d+)(?:,(?P<column>\d+))?\):\s*"
    r"(?P<level>fatal error|error|warning)\s*(?P<code>[A-Za-z]+\d+):\s*(?P<message>.+)$"
)
_JAVAC_RE = re.compile(
    r"^(?P<file>.+\.java):(?P<line>\d+):\s*(?P<level>error|warning):\s*(?P<message>.+)$"
)
_GCC_RE = re.compile(
    r"^(?P<file>.+):(?P<line>\d+):(?P<column>\d+):\s*"
    r"(?P<level>fatal error|error|warning|note):\s*(?P<message>.+)$"
)
_GCC_NO_COL_RE = re.compile(
    r"^(?P<file>.+):(?P<line>\d+):\s*(?P<level>fatal error|error|warning|note):\s*(?P<message>.+)$"
)
_LD_ERROR_RE = re.compile(r"^(?P<tool>ld|collect2|link)(:|\s).*(error|fatal error)", re.IGNORECASE)


def _normalize_title(message: str) -> str:
    return message.split(" (", 1)[0].strip()[:120] or "Build issue"


def parse_build_logs(log_entries: Iterable[dict]) -> List[ParsedIssue]:
    issues: List[ParsedIssue] = []
    seen = set()
    for entry in log_entries:
        for stream in ("stdout", "stderr"):
            text = entry.get(stream, "") or ""
            for line in text.splitlines():
                parsed = _parse_build_line(line)
                if not parsed:
                    continue
                fingerprint = (parsed.file, parsed.line, parsed.column, parsed.description, parsed.tool)
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                issues.append(parsed)
    return issues


def _parse_build_line(line: str) -> Optional[ParsedIssue]:
    if not line:
        return None

    match = _GCC_RE.match(line)
    if match:
        level = match.group("level")
        if "error" in level:
            message = match.group("message").strip()
            return ParsedIssue(
                issue_type="build",
                title=_normalize_title(message),
                description=message,
                file=match.group("file"),
                line=int(match.group("line")),
                column=int(match.group("column")),
                tool="gcc/clang",
            )
        return None

    match = _GCC_NO_COL_RE.match(line)
    if match:
        level = match.group("level")
        if "error" in level:
            message = match.group("message").strip()
            return ParsedIssue(
                issue_type="build",
                title=_normalize_title(message),
                description=message,
                file=match.group("file"),
                line=int(match.group("line")),
                tool="gcc/clang",
            )
        return None

    match = _MSVC_RE.match(line)
    if match:
        level = match.group("level")
        if "error" in level:
            message = match.group("message").strip()
            return ParsedIssue(
                issue_type="build",
                title=_normalize_title(message),
                description=message,
                file=match.group("file"),
                line=int(match.group("line")),
                column=int(match.group("column") or 0),
                tool="msvc",
                rule=match.group("code"),
            )
        return None

    match = _JAVAC_RE.match(line)
    if match:
        level = match.group("level")
        if "error" in level:
            message = match.group("message").strip()
            return ParsedIssue(
                issue_type="build",
                title=_normalize_title(message),
                description=message,
                file=match.group("file"),
                line=int(match.group("line")),
                tool="javac",
            )
        return None

    if _LD_ERROR_RE.match(line) or "undefined reference" in line:
        message = line.strip()
        return ParsedIssue(
            issue_type="build",
            title=_normalize_title(message),
            description=message,
            tool="linker",
        )

    return None


def parse_analyzer_output(tool: str, output: str) -> List[ParsedIssue]:
    issues: List[ParsedIssue] = []
    seen = set()
    for line in output.splitlines():
        parsed = _parse_analyzer_line(tool, line)
        if not parsed:
            continue
        fingerprint = (parsed.file, parsed.line, parsed.column, parsed.description, parsed.tool, parsed.rule)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        issues.append(parsed)
    return issues


def _parse_analyzer_line(tool: str, line: str) -> Optional[ParsedIssue]:
    if not line:
        return None

    match = _GCC_RE.match(line) or _GCC_NO_COL_RE.match(line)
    if match:
        message = match.group("message").strip()
        rule = None
        rule_match = re.search(r"\[(?P<rule>[^\]]+)\]\s*$", message)
        if rule_match:
            rule = rule_match.group("rule")
            message = message[: rule_match.start()].strip()
        severity = match.group("level")
        issue_type = "build" if "error" in severity else "convention"
        return ParsedIssue(
            issue_type=issue_type,
            title=_normalize_title(message),
            description=message,
            file=match.group("file"),
            line=int(match.group("line")),
            column=int(match.groupdict().get("column") or 0),
            tool=tool,
            rule=rule,
        )

    if tool == "cppcheck":
        cppcheck_re = re.compile(
            r"^(?P<file>.+?):(?P<line>\d+):(?P<column>\d+):\s*"
            r"(?P<severity>[a-zA-Z]+):\s*(?P<message>.+)$"
        )
        match = cppcheck_re.match(line)
        if match:
            severity = match.group("severity").lower()
            message = match.group("message").strip()
            issue_type = "build" if severity == "error" else "convention"
            return ParsedIssue(
                issue_type=issue_type,
                title=_normalize_title(message),
                description=message,
                file=match.group("file"),
                line=int(match.group("line")),
                column=int(match.group("column")),
                tool=tool,
                rule=severity,
            )

    if tool == "pylint":
        pylint_re = re.compile(
            r"^(?P<file>.+?):(?P<line>\d+):(?P<column>\d+):\s*"
            r"(?P<code>[A-Z]\d+):\s*(?P<message>.+)$"
        )
        match = pylint_re.match(line)
        if match:
            message = match.group("message").strip()
            rule_match = re.search(r"\((?P<rule>[^)]+)\)\s*$", message)
            rule = match.group("code")
            if rule_match:
                rule = f"{rule}:{rule_match.group('rule')}"
                message = message[: rule_match.start()].strip()
            return ParsedIssue(
                issue_type="convention",
                title=_normalize_title(message),
                description=message,
                file=match.group("file"),
                line=int(match.group("line")),
                column=int(match.group("column")),
                tool=tool,
                rule=rule,
            )

    if tool == "checkstyle":
        checkstyle_re = re.compile(
            r"^(?P<file>.+?):(?P<line>\d+):(?P<column>\d+):\s*(?P<message>.+)$"
        )
        match = checkstyle_re.match(line)
        if match:
            message = match.group("message").strip()
            rule = None
            rule_match = re.search(r"\[(?P<rule>[^\]]+)\]\s*$", message)
            if rule_match:
                rule = rule_match.group("rule")
                message = message[: rule_match.start()].strip()
            return ParsedIssue(
                issue_type="convention",
                title=_normalize_title(message),
                description=message,
                file=match.group("file"),
                line=int(match.group("line")),
                column=int(match.group("column")),
                tool=tool,
                rule=rule,
            )

    return None

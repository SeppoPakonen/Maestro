"""
Known issue patterns library for matching common diagnostic problems.
"""
import re
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class KnownIssue:
    """
    Represents a known diagnostic issue with patterns and fix hints.
    """
    id: str
    description: str
    patterns: List[str]        # regex patterns against diagnostic.raw or message
    tags: List[str]
    fix_hint: str              # short actionable hint
    confidence: float          # 0..1


def match_known_issues(diagnostics: List[Any]) -> Dict[str, List[KnownIssue]]:
    """
    Match diagnostics against known issues and return a mapping of
    signature to list of matched KnownIssue objects.

    Args:
        diagnostics: List of Diagnostic objects to match (using Any to avoid circular import)

    Returns:
        Dict mapping diagnostic signature to list of matched KnownIssues
    """
    # Define known issue patterns
    known_issues = [
        # U++ Moveable/Vector issue - matches common patterns
        KnownIssue(
            id="upp-moveable-vector",
            description="U++ Vector<T> requires T : Moveable<T> for proper element relocation",
            patterns=[
                r"(?i)(vector|Moveable|moveable|relocate|deep copy|element relocation|container|Move|Copy)",
                r"(?i)(template|instantiation|requirement|constraint|failed)",
                r"(?i)(U\+\+|Ultimate\+\+|move semantics|copy semantics)"
            ],
            tags=["upp", "moveable", "vector", "container"],
            fix_hint="In U++, types stored in Vector<> should derive from Moveable<T> (or use a container appropriate for non-moveable types). Avoid taking pointers to elements because relocation can occur.",
            confidence=0.9
        ),
        # U++ more specific patterns for the Vector<T> requiring T : Moveable<T> issue
        KnownIssue(
            id="upp-moveable-vector-specific",
            description="U++ Vector<T> type T does not satisfy Moveable<T> requirement",
            patterns=[
                r"(?i)(no match for.*operator.*Moveable|T must be Moveable|does not satisfy.*Moveable|Moveable constraint failed)",
                r"(?i)(Vector.*require.*Moveable|Vector.*T.*Moveable|template.*require.*T.*Moveable)",
                r"(?i)(can't copy.*Vector.*not Moveable|relocation.*failed.*not Moveable)"
            ],
            tags=["upp", "moveable", "vector", "template"],
            fix_hint="In U++, types stored in Vector<> should derive from Moveable<T> (or use a container appropriate for non-moveable types). Avoid taking pointers to elements because relocation can occur.",
            confidence=0.95
        ),
        # General C++ template error pattern
        KnownIssue(
            id="cpp-template-constraint",
            description="C++ template constraint or concept violation",
            patterns=[
                r"(?i)(constraint|requirement|satisfy|not match|no match for)",
                r"(?i)(template.*argument|template instantiation|template parameter)",
                r"(?i)(concept|requires|static_assert|enable_if)"
            ],
            tags=["cpp", "template", "constraint"],
            fix_hint="Check that template arguments satisfy all required concepts and constraints. Verify template parameter types meet all requirements.",
            confidence=0.7
        ),
        # Memory/pointer issue
        KnownIssue(
            id="memory-pointer-relocation",
            description="Issues related to pointer invalidation due to memory relocation",
            patterns=[
                r"(?i)(invalid pointer|dangling pointer|pointer invalidated|access violation)",
                r"(?i)(relocation.*invalid|container resize.*invalid|pointer.*invalid)",
                r"(?i)(use after free|memory corruption|buffer overflow)"
            ],
            tags=["memory", "pointer", "relocation"],
            fix_hint="Avoid storing pointers to container elements that may be relocated. Use indices or references if available, or use pointer-stable containers.",
            confidence=0.8
        ),
        # General 'deep copy' issue typical of U++
        KnownIssue(
            id="cpp-deep-copy-required",
            description="Deep copy required but not implemented",
            patterns=[
                r"(?i)(deep copy|deep_copy|copy constructor|assignment operator)",
                r"(?i)(member function required|not implemented|not defined)",
                r"(?i)(explicitly deleted|defaulted|deleted function)"
            ],
            tags=["cpp", "copy", "moveable"],
            fix_hint="Implement proper copy constructor and assignment operator, or make the class Moveable if copying is expensive or not needed.",
            confidence=0.75
        )
    ]

    # Result dictionary mapping signature to matched issues
    result = {}

    for diagnostic in diagnostics:
        matched_issues = []

        # Check each known issue against the diagnostic
        for issue in known_issues:
            match_count = 0
            total_patterns = len(issue.patterns)

            # Check if any of the patterns match the diagnostic content
            diagnostic_text = f"{diagnostic.raw} {diagnostic.message}".lower()

            for pattern in issue.patterns:
                if re.search(pattern, diagnostic_text, re.IGNORECASE):
                    match_count += 1

            # If at least half of the patterns match, consider it a match
            if total_patterns == 0 or (match_count > 0 and match_count >= max(1, total_patterns // 2)):
                # Add confidence adjustment based on how many patterns matched
                adjusted_confidence = issue.confidence * (match_count / total_patterns)

                # Create a copy of the issue with adjusted confidence if needed
                if abs(adjusted_confidence - issue.confidence) > 0.01:  # Only if different
                    matched_issue = KnownIssue(
                        id=issue.id,
                        description=issue.description,
                        patterns=issue.patterns,
                        tags=issue.tags,
                        fix_hint=issue.fix_hint,
                        confidence=adjusted_confidence
                    )
                else:
                    matched_issue = issue

                matched_issues.append(matched_issue)

        # If any issues matched, add to results
        if matched_issues:
            result[diagnostic.signature] = matched_issues

    return result
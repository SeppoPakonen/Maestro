"""
Goal-to-attempt evaluator for UX evaluation.

Takes a goal string and discovered help surface, produces an attempt plan without
using internal parser knowledge (only help text).
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from .help_surface import HelpNode


@dataclass
class AttemptPlan:
    """
    A plan to achieve a goal using discovered commands.

    Contains a ranked list of command attempts that may satisfy the goal.
    """
    goal: str
    attempts: List[List[str]] = field(default_factory=list)  # List of command_path lists
    reasoning: str = ""  # Brief explanation of why these attempts were chosen


class GoalEvaluator:
    """
    Evaluates a goal and produces an attempt plan using only help surface knowledge.

    This evaluator does not use internal parser knowledge - it only uses strings
    learned from help text to propose command invocations.
    """

    def __init__(self, help_surface: Dict[tuple, HelpNode], verbose: bool = False):
        """
        Initialize evaluator.

        Args:
            help_surface: Discovered command surface (from HelpSurface.discover())
            verbose: Whether to print reasoning
        """
        self.help_surface = help_surface
        self.verbose = verbose

        # Build keyword index: keyword → list of command paths
        self.keyword_index: Dict[str, List[tuple]] = {}
        self._build_keyword_index()

    def _build_keyword_index(self) -> None:
        """Build an index of keywords to command paths."""
        for cmd_tuple, node in self.help_surface.items():
            # Extract keywords from command path
            for part in node.command_path:
                keyword = part.lower()
                if keyword not in self.keyword_index:
                    self.keyword_index[keyword] = []
                self.keyword_index[keyword].append(cmd_tuple)

            # Extract keywords from help text (simple word extraction)
            words = re.findall(r'\b[a-z]{3,}\b', node.help_text.lower())
            for word in set(words):  # dedupe
                if word not in self.keyword_index:
                    self.keyword_index[word] = []
                self.keyword_index[word].append(cmd_tuple)

    def generate_attempt_plan(self, goal: str) -> AttemptPlan:
        """
        Generate an attempt plan for the given goal.

        Args:
            goal: User's goal string (e.g., "Create an actionable runbook")

        Returns:
            AttemptPlan with ranked command attempts
        """
        # Extract keywords from goal
        goal_keywords = self._extract_goal_keywords(goal)

        if self.verbose:
            print(f"Goal keywords: {goal_keywords}")

        # Score commands based on keyword matches
        scores: Dict[tuple, int] = {}

        for cmd_tuple in self.help_surface.keys():
            score = self._score_command(cmd_tuple, goal_keywords)
            if score > 0:
                scores[cmd_tuple] = score

        # Rank by score (descending)
        ranked_commands = sorted(scores.items(), key=lambda x: (-x[1], x[0]))

        # Take top N attempts (bounded)
        max_attempts = 10
        top_commands = ranked_commands[:max_attempts]

        # Convert to command paths
        attempts = [list(cmd_tuple) for cmd_tuple, _score in top_commands]

        # Generate reasoning
        reasoning = self._generate_reasoning(goal, goal_keywords, top_commands)

        return AttemptPlan(
            goal=goal,
            attempts=attempts,
            reasoning=reasoning
        )

    def _extract_goal_keywords(self, goal: str) -> Set[str]:
        """
        Extract meaningful keywords from goal string.

        Args:
            goal: Goal string

        Returns:
            Set of lowercase keywords
        """
        # Extract words (3+ characters, alphanumeric)
        words = re.findall(r'\b[a-z]{3,}\b', goal.lower())

        # Filter out common stop words
        stop_words = {
            'the', 'and', 'for', 'this', 'that', 'with', 'from',
            'into', 'create', 'make', 'build', 'run', 'execute'
        }

        keywords = set(w for w in words if w not in stop_words)

        return keywords

    def _score_command(self, cmd_tuple: tuple, goal_keywords: Set[str]) -> int:
        """
        Score a command based on keyword matches.

        Args:
            cmd_tuple: Command path tuple
            goal_keywords: Keywords from goal

        Returns:
            Score (higher = better match)
        """
        node = self.help_surface[cmd_tuple]
        score = 0

        # Match in command path (high weight)
        for part in node.command_path:
            if part.lower() in goal_keywords:
                score += 10

        # Match in discovered subcommands (medium weight)
        for subcmd in node.discovered_subcommands:
            if subcmd.lower() in goal_keywords:
                score += 5

        # Match in help text (low weight, count unique matches)
        help_lower = node.help_text.lower()
        for keyword in goal_keywords:
            if keyword in help_lower:
                score += 1

        return score

    def _generate_reasoning(
        self,
        goal: str,
        keywords: Set[str],
        top_commands: List[Tuple[tuple, int]]
    ) -> str:
        """
        Generate human-readable reasoning for the attempt plan.

        Args:
            goal: Original goal
            keywords: Extracted keywords
            top_commands: Ranked commands with scores

        Returns:
            Reasoning string
        """
        lines = []
        lines.append(f"Goal: {goal}")
        lines.append(f"Extracted keywords: {', '.join(sorted(keywords))}")
        lines.append(f"Top matches:")

        for cmd_tuple, score in top_commands[:5]:  # Show top 5
            cmd_str = ' '.join(cmd_tuple)
            lines.append(f"  - {cmd_str} (score: {score})")

        return '\n'.join(lines)

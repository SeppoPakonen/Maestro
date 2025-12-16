"""
Conditional expression evaluator for U++ build configurations.

Based on U++ Package.cpp MatchWhen() logic:
- Supports operators: | (OR), & (AND), ! (NOT)
- Supports || and && as aliases
- Supports parentheses for grouping
- No operator between identifiers defaults to AND
"""

import re
from typing import List, Set


class ConditionalParser:
    """
    Parser for U++ conditional expressions.

    Expression syntax:
    - FLAG: flag is set
    - !FLAG: flag is not set
    - FLAG1 FLAG2: FLAG1 AND FLAG2 (implicit AND)
    - FLAG1 & FLAG2: FLAG1 AND FLAG2
    - FLAG1 && FLAG2: FLAG1 AND FLAG2
    - FLAG1 | FLAG2: FLAG1 OR FLAG2
    - FLAG1 || FLAG2: FLAG1 OR FLAG2
    - (EXPR): grouping

    Operator precedence: NOT > AND > OR
    """

    def __init__(self, expression: str):
        self.expr = expression.strip()
        self.pos = 0

    def _current_char(self) -> str:
        """Get current character or empty string if at end."""
        if self.pos < len(self.expr):
            return self.expr[self.pos]
        return ''

    def _peek_char(self, offset: int = 0) -> str:
        """Peek at character at offset from current position."""
        pos = self.pos + offset
        if pos < len(self.expr):
            return self.expr[pos]
        return ''

    def _skip_whitespace(self):
        """Skip whitespace characters."""
        while self.pos < len(self.expr) and self.expr[self.pos].isspace():
            self.pos += 1

    def _read_identifier(self) -> str:
        """Read an identifier (alphanumeric and underscores)."""
        start = self.pos
        while self.pos < len(self.expr) and (self.expr[self.pos].isalnum() or self.expr[self.pos] == '_'):
            self.pos += 1
        return self.expr[start:self.pos]

    def _parse_flag(self, flags: Set[str]) -> bool:
        """
        Parse a single flag or negated flag or grouped expression.

        flag = '!' flag | '(' or_expr ')' | IDENTIFIER
        """
        self._skip_whitespace()

        # Handle negation
        if self._current_char() == '!':
            self.pos += 1
            return not self._parse_flag(flags)

        # Handle grouping
        if self._current_char() == '(':
            self.pos += 1
            result = self._parse_or(flags)
            self._skip_whitespace()
            if self._current_char() == ')':
                self.pos += 1
            return result

        # Handle identifier
        if self.pos >= len(self.expr):
            return True  # Empty expression is true

        identifier = self._read_identifier()
        if not identifier:
            return True

        return identifier in flags

    def _parse_and(self, flags: Set[str]) -> bool:
        """
        Parse AND expression with implicit AND support.

        and_expr = flag { ('&' | '&&' | implicit) flag }
        """
        result = self._parse_flag(flags)

        while True:
            self._skip_whitespace()

            # Check for end of expression or OR operator
            if self.pos >= len(self.expr) or self._current_char() == ')' or self._current_char() == '|':
                break

            # Explicit AND operators
            if self._current_char() == '&':
                self.pos += 1
                if self._current_char() == '&':
                    self.pos += 1  # Skip second '&' in '&&'
                next_val = self._parse_flag(flags)
                result = result and next_val
            # Implicit AND (identifier or negation or grouping follows)
            elif self._current_char() in ('!', '(') or self._current_char().isalnum():
                next_val = self._parse_flag(flags)
                result = result and next_val
            else:
                break

        return result

    def _parse_or(self, flags: Set[str]) -> bool:
        """
        Parse OR expression.

        or_expr = and_expr { ('|' | '||') and_expr }
        """
        result = self._parse_and(flags)

        while True:
            self._skip_whitespace()

            if self.pos >= len(self.expr) or self._current_char() == ')':
                break

            if self._current_char() == '|':
                self.pos += 1
                if self._current_char() == '|':
                    self.pos += 1  # Skip second '|' in '||'
                next_val = self._parse_and(flags)
                result = result or next_val
            else:
                break

        return result

    def evaluate(self, flags: Set[str]) -> bool:
        """
        Evaluate the conditional expression with given flags.

        Args:
            flags: Set of flag names that are enabled

        Returns:
            True if condition is satisfied, False otherwise
        """
        if not self.expr:
            return True

        self.pos = 0
        result = self._parse_or(flags)
        return result


def match_when(expression: str, flags: List[str]) -> bool:
    """
    Evaluate a U++ conditional expression.

    Args:
        expression: Conditional expression string (e.g., "WIN32 | POSIX", "!NOMM", "AUDIO & !SYS_PORTAUDIO")
        flags: List of enabled flag names

    Returns:
        True if condition matches, False otherwise

    Examples:
        >>> match_when("WIN32", ["WIN32", "GUI"])
        True
        >>> match_when("WIN32 | POSIX", ["POSIX"])
        True
        >>> match_when("!NOMM", ["WIN32"])
        True
        >>> match_when("!NOMM", ["NOMM"])
        False
        >>> match_when("AUDIO & !SYS_PORTAUDIO", ["AUDIO"])
        True
    """
    try:
        parser = ConditionalParser(expression)
        return parser.evaluate(set(flags))
    except Exception:
        # If parsing fails, default to False (conservative)
        return False

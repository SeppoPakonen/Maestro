from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Sequence
from .ast_nodes import ASTDocument


class TranslationUnitParser(ABC):
    """Abstract base class for language-specific translation unit parsers."""

    @abstractmethod
    def parse_file(self, path: str, *, compile_flags: Optional[Sequence[str]] = None, verbose: bool = False, **kwargs) -> ASTDocument:
        """
        Parse a single file and return its AST.

        Args:
            path: Path to the source file
            compile_flags: Optional list of compiler flags
            verbose: Optional flag for verbose output
            **kwargs: Additional parser-specific options

        Returns:
            ASTDocument: The parsed AST document
        """
        raise NotImplementedError


def ensure_path(path: str) -> Path:
    """Ensure that a path is a Path object."""
    return Path(path) if isinstance(path, str) else path
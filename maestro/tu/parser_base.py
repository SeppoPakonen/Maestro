import abc
from pathlib import Path
from typing import Optional, Sequence

from .ast_nodes import ASTDocument


def ensure_path(path) -> Path:
    if isinstance(path, Path):
        return path
    return Path(path)


class TranslationUnitParser(abc.ABC):
    """Abstract base class for translation unit parsers."""

    @abc.abstractmethod
    def parse_file(self, path: str, *, compile_flags: Optional[Sequence[str]] = None) -> ASTDocument:
        """Parse a file and return an ASTDocument."""
        raise NotImplementedError

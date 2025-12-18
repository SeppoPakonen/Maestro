from .parser_base import TranslationUnitParser
from .errors import ParserUnavailableError


class KotlinParser(TranslationUnitParser):
    """Kotlin parser stub using tree-sitter or other backend (planned)."""

    def parse_file(self, path: str, *, compile_flags: list = None) -> 'ASTDocument':
        raise ParserUnavailableError(
            "Kotlin parser not yet implemented. Planned support via tree-sitter-kotlin."
        )

from typing import Optional, Sequence, List

from .parser_base import TranslationUnitParser, ensure_path
from .ast_nodes import ASTNode, SourceLocation, ASTDocument, Symbol, SourceExtent
from .errors import ParserUnavailableError, ParserExecutionError
from .clang_utils import (
    get_default_compile_flags,
    safe_get_usr,
    safe_get_type_spelling,
    is_reference_cursor,
)


def _lazy_import_clang():
    try:
        import clang.cindex  # type: ignore
        return clang.cindex
    except ImportError as exc:
        raise ParserUnavailableError(
            "clang.cindex is not available. Install with: pip install libclang"
        ) from exc


def _get_kind_str(cursor_kind):
    if hasattr(cursor_kind, 'name'):
        return cursor_kind.name
    return str(cursor_kind)


class ClangParser(TranslationUnitParser):
    """Clang-based parser implementation with semantic symbols and references."""

    def __init__(self):
        self.clang = _lazy_import_clang()

    def parse_file(self, path: str, *, compile_flags: Optional[Sequence[str]] = None, verbose: bool = False) -> ASTDocument:
        path_obj = ensure_path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {path_obj}")

        try:
            index = self.clang.Index.create()
            flags = list(compile_flags) if compile_flags else get_default_compile_flags()
            if verbose:
                print(f"clang_parser.py:parse_file: file={path}, flags={flags}")
            tu = index.parse(
                str(path_obj),
                args=flags,
                options=self.clang.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
            )

            for diag in tu.diagnostics:
                if diag.severity >= self.clang.Diagnostic.Error:
                    if verbose:
                        print(f"CLANG ERROR: {diag.location.file}:{diag.location.line} - {diag.spelling}")
                    raise ParserExecutionError(f"CIndex diagnostic error: {diag.spelling}")
                elif diag.severity >= self.clang.Diagnostic.Warning and verbose:
                    print(f"CLANG WARNING: {diag.location.file}:{diag.location.line} - {diag.spelling}")

            symbols: List[Symbol] = []
            root_node = self._cursor_to_ast_node(tu.cursor, symbols, is_root=True)
            return ASTDocument(root=root_node, symbols=symbols)
        except ParserExecutionError:
            raise
        except Exception as exc:
            raise ParserExecutionError(f"Failed to parse with clang: {exc}") from exc

    def _cursor_to_ast_node(self, cursor, symbols: List[Symbol], is_root: bool = False) -> ASTNode:
        loc = cursor.location
        file_path = loc.file.name if loc and loc.file else "<no_file>"
        sl = SourceLocation(file=file_path, line=getattr(loc, "line", 0), column=getattr(loc, "column", 0))
        extent = self._get_extent(cursor)

        kind_str = _get_kind_str(cursor.kind)
        name = cursor.spelling or cursor.displayname or ""
        node = ASTNode(
            kind=kind_str,
            name=name,
            loc=sl,
            type=safe_get_type_spelling(cursor),
            children=[],
            symbol_refs=[],
            usr=safe_get_usr(cursor),
            extent=extent,
        )

        # Add definitions/declarations as symbols
        self._maybe_add_symbol(cursor, sl, kind_str, symbols)

        # Add reference from this cursor if applicable
        ref = self._make_reference_symbol(cursor, sl)
        if ref:
            node.symbol_refs.append(ref)

        for child in cursor.get_children():
            child_node = self._cursor_to_ast_node(child, symbols)
            node.children.append(child_node)

        if not node.children:
            node.children = None
        if not node.symbol_refs:
            node.symbol_refs = None
        return node

    def _maybe_add_symbol(self, cursor, loc: SourceLocation, kind_str: str, symbols: List[Symbol]) -> None:
        try:
            ck = self.clang.CursorKind
            if cursor.kind in {
                ck.FUNCTION_DECL,
                ck.CXX_METHOD,
                ck.CONSTRUCTOR,
                ck.DESTRUCTOR,
                ck.FUNCTION_TEMPLATE,
                ck.VAR_DECL,
                ck.PARM_DECL,
                ck.FIELD_DECL,
                ck.STRUCT_DECL,
                ck.CLASS_DECL,
                ck.CLASS_TEMPLATE,
                ck.UNION_DECL,
                ck.ENUM_DECL,
                ck.ENUM_CONSTANT_DECL,
                ck.NAMESPACE,
                ck.TYPEDEF_DECL,
                ck.TYPE_ALIAS_DECL,
                ck.MACRO_DEFINITION,
                ck.USING_DECL,
                ck.USING_DIRECTIVE,
            }:
                sym = Symbol(
                    name=cursor.spelling or cursor.displayname or kind_str,
                    kind=kind_str,
                    loc=loc,
                    target=safe_get_usr(cursor),
                )
                symbols.append(sym)
        except Exception:
            return

    def _make_reference_symbol(self, cursor, loc: SourceLocation) -> Optional[Symbol]:
        if not is_reference_cursor(cursor):
            return None
        try:
            referenced = cursor.referenced
        except Exception:
            referenced = None
        if referenced is None:
            return None
        refers_to = safe_get_usr(referenced)
        if not refers_to:
            return None
        return Symbol(
            name=referenced.spelling or cursor.spelling or "",
            kind=_get_kind_str(referenced.kind),
            loc=loc,
            refers_to=refers_to,
        )

    def _get_extent(self, cursor) -> Optional[SourceExtent]:
        try:
            if not cursor.extent:
                return None
            start = cursor.extent.start
            end = cursor.extent.end
            if start.file is None or end.file is None:
                return None
            return SourceExtent(
                start=SourceLocation(file=start.file.name, line=start.line, column=start.column),
                end=SourceLocation(file=end.file.name, line=end.line, column=end.column),
            )
        except Exception:
            return None
from .parser_base import TranslationUnitParser
from .errors import ParserUnavailableError
from .ast_nodes import ASTNode, SourceLocation, Symbol, ASTDocument
from typing import Optional, Sequence, List


def _lazy_import_tree_sitter_java():
    try:
        import tree_sitter
        import tree_sitter_java
        return tree_sitter, tree_sitter_java
    except ImportError as exc:
        raise ParserUnavailableError(
            "tree-sitter or tree-sitter-java not available. Install with: pip install tree-sitter tree-sitter-java"
        ) from exc


def _get_node_text(node, source_bytes: bytes) -> str:
    """Extract text content of a node from source bytes."""
    return source_bytes[node.start_byte:node.end_byte].decode('utf8')


def _get_node_kind_str(node) -> str:
    """Get a string representation of the node kind."""
    return node.type


class JavaParser(TranslationUnitParser):
    """Java parser using tree-sitter."""

    def __init__(self):
        tree_sitter, tree_sitter_java = _lazy_import_tree_sitter_java()
        self.tree_sitter = tree_sitter
        self.language = tree_sitter.Language(tree_sitter_java.language())
        self.parser = tree_sitter.Parser(self.language)

    def parse_file(self, path: str, *, compile_flags: Optional[Sequence[str]] = None, verbose: bool = False, **kwargs) -> ASTDocument:
        from pathlib import Path

        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {path_obj}")

        try:
            source_bytes = path_obj.read_bytes()
            tree = self.parser.parse(source_bytes)

            symbols: List[Symbol] = []
            root_node = self._ts_node_to_ast_node(tree.root_node, source_bytes, symbols, path, is_root=True)
            return ASTDocument(root=root_node, symbols=symbols)
        except Exception as exc:
            from .errors import ParserExecutionError
            raise ParserExecutionError(f"Failed to parse Java file: {exc}") from exc

    def _ts_node_to_ast_node(self, ts_node, source_bytes: bytes, symbols: List[Symbol], file_path: str, is_root: bool = False) -> ASTNode:
        # Get location information
        start_pos = ts_node.start_point
        sl = SourceLocation(file=file_path, line=start_pos[0] + 1, column=start_pos[1])

        kind_str = _get_node_kind_str(ts_node)
        node_text = _get_node_text(ts_node, source_bytes)

        # Extract name based on node type
        name = self._extract_name_from_node(ts_node, source_bytes)

        node = ASTNode(
            kind=kind_str,
            name=name,
            loc=sl,
            type=None,  # Type info not readily available with tree-sitter
            children=[],
            symbol_refs=[],
        )

        # Add definitions/declarations as symbols
        self._maybe_add_symbol(ts_node, sl, kind_str, symbols, source_bytes)

        # Recursively process children
        for child in ts_node.children:
            child_node = self._ts_node_to_ast_node(child, source_bytes, symbols, file_path)
            node.children.append(child_node)

        if not node.children:
            node.children = None
        if not node.symbol_refs:
            node.symbol_refs = None

        return node

    def _extract_name_from_node(self, ts_node, source_bytes: bytes) -> str:
        """Extract the name of the node based on its type."""
        # For Java-specific node types that have names
        if ts_node.type in ['identifier', 'field_identifier', 'method_declaration', 'class_declaration',
                           'interface_declaration', 'enum_declaration', 'variable_declarator',
                           'function_declaration', 'type_identifier']:
            return _get_node_text(ts_node, source_bytes)

        # For method calls and similar that have an identifier child
        if ts_node.type in ['method_invocation', 'object_creation_expression', 'field_access']:
            for child in ts_node.children:
                if child.type == 'identifier' or child.type == 'field_identifier':
                    return _get_node_text(child, source_bytes)

        # For class declarations with an identifier child
        if ts_node.type in ['class_declaration', 'interface_declaration', 'enum_declaration']:
            for child in ts_node.children:
                if child.type == 'identifier':
                    return _get_node_text(child, source_bytes)

        # For method declarations
        if ts_node.type == 'method_declaration':
            for child in ts_node.children:
                if child.type == 'identifier' or child.type == 'field_identifier':
                    return _get_node_text(child, source_bytes)

        # For variable declarations
        if ts_node.type == 'variable_declarator':
            for child in ts_node.children:
                if child.type == 'identifier':
                    return _get_node_text(child, source_bytes)

        # Default to empty string if no name found
        return ""

    def _maybe_add_symbol(self, ts_node, loc: SourceLocation, kind_str: str, symbols: List[Symbol], source_bytes: bytes) -> None:
        """Add symbol to symbol table if the node represents a definition."""
        # Map tree-sitter Java node types to semantic types
        if ts_node.type in [
            'class_declaration', 'interface_declaration', 'enum_declaration',
            'method_declaration', 'constructor_declaration', 'field_declaration',
            'variable_declarator', 'local_variable_declaration'
        ]:
            name = self._extract_name_from_node(ts_node, source_bytes)

            # For method and variable declarations, get type information from the parent
            type_info = None
            if ts_node.type in ['method_declaration', 'field_declaration', 'local_variable_declaration']:
                # Look for type information in the children
                for child in ts_node.children:
                    if child.type in ['type_identifier', 'primitive_type', 'array_type']:
                        type_info = _get_node_text(child, source_bytes)
                        break

            # Create a unique identifier for the symbol (like a USR in clang)
            # In tree-sitter, we'll use the file + line + name as a proxy for uniqueness
            usr = f"{loc.file}:{loc.line}:{name}"

            sym = Symbol(
                name=name,
                kind=kind_str,
                loc=loc,
                target=usr,  # Point to the symbol's own USR
            )
            symbols.append(sym)

        # Handle method calls and variable references as symbol references
        elif ts_node.type in ['method_invocation', 'identifier', 'field_access']:
            name = self._extract_name_from_node(ts_node, source_bytes)
            if name:
                # This is a reference to another symbol
                # For now, we'll add it with a placeholder target that needs to be resolved later
                refers_to = f"UNRESOLVED:{name}"  # Placeholder, needs resolution

                sym = Symbol(
                    name=name,
                    kind=kind_str,
                    loc=loc,
                    refers_to=refers_to,
                )
                symbols.append(sym)

    def _get_extent(self, ts_node, file_path: str):
        """Create SourceExtent from tree-sitter node."""
        start_point = ts_node.start_point
        end_point = ts_node.end_point

        from .ast_nodes import SourceExtent

        start_loc = SourceLocation(
            file=file_path,
            line=start_point[0] + 1,  # 1-based line numbers
            column=start_point[1]
        )
        end_loc = SourceLocation(
            file=file_path,
            line=end_point[0] + 1,  # 1-based line numbers
            column=end_point[1]
        )

        return SourceExtent(start=start_loc, end=end_loc)

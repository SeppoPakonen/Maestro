"""
Python parser using Python's built-in AST module.
"""
import ast
from pathlib import Path
from typing import Optional, Sequence, List

from .parser_base import TranslationUnitParser
from .ast_nodes import ASTNode, SourceLocation, Symbol, ASTDocument


class PythonParser(TranslationUnitParser):
    """Python parser using the built-in ast module."""

    def parse_file(self, path: str, *, compile_flags: Optional[Sequence[str]] = None) -> ASTDocument:
        """Parse a Python file and return an ASTDocument."""
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {path_obj}")

        source_code = path_obj.read_text()

        # Parse the Python source code
        try:
            tree = ast.parse(source_code, filename=str(path_obj))
        except SyntaxError as e:
            raise ValueError(f"Syntax error in {path}: {e}")

        # Convert Python AST to our AST format
        symbols: List[Symbol] = []
        root_node = self._py_ast_to_ast_node(tree, symbols, str(path_obj))

        return ASTDocument(root=root_node, symbols=symbols)

    def _py_ast_to_ast_node(self, node: ast.AST, symbols: List[Symbol], file_path: str) -> ASTNode:
        """Convert Python AST node to our ASTNode format."""

        # Get node information
        node_kind = node.__class__.__name__
        node_name = getattr(node, 'name', '') or ''

        # Get location information
        lineno = getattr(node, 'lineno', 0)
        col_offset = getattr(node, 'col_offset', 0)
        loc = SourceLocation(file=file_path, line=lineno, column=col_offset)

        # Get type information if available
        node_type = None
        if isinstance(node, ast.FunctionDef):
            if node.returns:
                node_type = ast.unparse(node.returns)
        elif isinstance(node, (ast.arg, ast.AnnAssign)):
            if hasattr(node, 'annotation') and node.annotation:
                node_type = ast.unparse(node.annotation)

        # Get value for constants
        value = None
        if isinstance(node, ast.Constant):
            value = str(node.value)
        elif isinstance(node, ast.Name):
            node_name = node.id

        # Get modifiers (decorators, async, etc.)
        modifiers = []
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            if node.decorator_list:
                modifiers.extend([ast.unparse(dec) for dec in node.decorator_list])
        if isinstance(node, ast.AsyncFunctionDef):
            modifiers.append('async')
        if isinstance(node, ast.FunctionDef) and isinstance(node, ast.AsyncFunctionDef):
            modifiers.append('async')

        # Extract function arguments as names
        if isinstance(node, ast.FunctionDef):
            if not node_name:
                node_name = node.name
        elif isinstance(node, ast.ClassDef):
            if not node_name:
                node_name = node.name
        elif isinstance(node, ast.arg):
            node_name = node.arg
        elif isinstance(node, ast.Attribute):
            node_name = node.attr

        # Convert children
        children = []
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        children.append(self._py_ast_to_ast_node(item, symbols, file_path))
            elif isinstance(value, ast.AST):
                children.append(self._py_ast_to_ast_node(value, symbols, file_path))

        # Add symbols for definitions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(Symbol(
                name=node.name,
                kind='function',
                loc=loc
            ))
        elif isinstance(node, ast.ClassDef):
            symbols.append(Symbol(
                name=node.name,
                kind='class',
                loc=loc
            ))
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            symbols.append(Symbol(
                name=node.id,
                kind='variable',
                loc=loc
            ))

        return ASTNode(
            kind=node_kind,
            name=node_name,
            loc=loc,
            type=node_type,
            value=value,
            modifiers=modifiers if modifiers else None,
            children=children if children else None
        )

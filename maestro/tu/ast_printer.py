"""
AST Printer for visualizing Abstract Syntax Trees.
Provides pretty-printed tree output for AST structures.
"""
from typing import Optional, Set
from .ast_nodes import ASTNode, ASTDocument


class ASTPrinter:
    """Pretty printer for AST structures."""

    def __init__(self,
                 show_types: bool = True,
                 show_locations: bool = True,
                 show_values: bool = True,
                 show_modifiers: bool = True,
                 max_depth: Optional[int] = None,
                 filter_kinds: Optional[Set[str]] = None):
        """
        Initialize the AST printer.

        Args:
            show_types: Include type information in output
            show_locations: Include source locations
            show_values: Include constant values
            show_modifiers: Include modifiers (public, static, etc.)
            max_depth: Maximum depth to print (None for unlimited)
            filter_kinds: Set of node kinds to include (None for all)
        """
        self.show_types = show_types
        self.show_locations = show_locations
        self.show_values = show_values
        self.show_modifiers = show_modifiers
        self.max_depth = max_depth
        self.filter_kinds = filter_kinds

    def print_document(self, document: ASTDocument) -> str:
        """Print an entire AST document."""
        lines = []
        lines.append("=" * 80)
        lines.append("AST DOCUMENT")
        lines.append("=" * 80)
        lines.append("")

        # Print root node tree
        lines.append("AST TREE:")
        lines.append("-" * 80)
        lines.extend(self.print_node(document.root))
        lines.append("")

        # Print symbol table summary
        if document.symbols:
            lines.append("")
            lines.append("SYMBOL TABLE SUMMARY:")
            lines.append("-" * 80)
            lines.append(f"Total symbols: {len(document.symbols)}")

            # Group by kind
            by_kind = {}
            for sym in document.symbols:
                by_kind.setdefault(sym.kind, []).append(sym)

            for kind, symbols in sorted(by_kind.items()):
                lines.append(f"  {kind}: {len(symbols)}")
                for sym in symbols[:5]:  # Show first 5 of each kind
                    loc = f"{sym.loc.file}:{sym.loc.line}:{sym.loc.column}"
                    lines.append(f"    - {sym.name} @ {loc}")
                if len(symbols) > 5:
                    lines.append(f"    ... and {len(symbols) - 5} more")

        lines.append("")
        lines.append("=" * 80)
        return "\n".join(lines)

    def print_node(self, node: ASTNode, prefix: str = "", depth: int = 0) -> list:
        """
        Print an AST node and its children in tree format.

        Args:
            node: The AST node to print
            prefix: Prefix for tree drawing (for recursion)
            depth: Current depth in tree (for recursion)

        Returns:
            List of output lines
        """
        if self.max_depth is not None and depth > self.max_depth:
            return []

        if self.filter_kinds is not None and node.kind not in self.filter_kinds:
            return []

        lines = []

        # Format node header
        node_str = f"{node.kind}"
        if node.name:
            node_str += f": '{node.name}'"

        # Add type info
        if self.show_types and node.type:
            node_str += f" <{node.type}>"

        # Add value info
        if self.show_values and node.value:
            # Truncate long values
            value_str = str(node.value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."
            node_str += f" = {value_str}"

        # Add modifiers
        if self.show_modifiers and node.modifiers:
            node_str += f" [{', '.join(node.modifiers)}]"

        # Add location
        if self.show_locations and node.loc:
            loc_str = f"@ {node.loc.line}:{node.loc.column}"
            node_str += f"  {loc_str}"

        lines.append(prefix + node_str)

        # Print children
        if node.children:
            for i, child in enumerate(node.children):
                is_last = (i == len(node.children) - 1)

                # Create appropriate prefix for child
                if is_last:
                    child_prefix = prefix + "└── "
                    continuation = prefix + "    "
                else:
                    child_prefix = prefix + "├── "
                    continuation = prefix + "│   "

                # Recursively print child
                child_lines = self.print_node(child, child_prefix, depth + 1)
                if child_lines:
                    # Update continuation for nested children
                    if len(child_lines) > 1:
                        child_lines[0] = child_lines[0]  # First line keeps child_prefix
                        for j in range(1, len(child_lines)):
                            # Replace the prefix part with continuation
                            child_lines[j] = continuation + child_lines[j][len(prefix) + 4:]

                    lines.extend(child_lines)

        return lines


def print_ast(document: ASTDocument, **kwargs) -> str:
    """
    Convenience function to print an AST document.

    Args:
        document: The AST document to print
        **kwargs: Options to pass to ASTPrinter constructor

    Returns:
        Formatted AST string
    """
    printer = ASTPrinter(**kwargs)
    return printer.print_document(document)

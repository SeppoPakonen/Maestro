"""
Symbol resolver for resolving cross-file symbol references.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from .ast_nodes import ASTDocument, Symbol, ASTNode
from .symbol_table import SymbolTable


class SymbolResolver:
    """
    Resolves cross-file symbol references by matching symbol references 
    to their corresponding definitions using a symbol table.
    """

    def __init__(self, symbol_table: SymbolTable):
        self.symbol_table = symbol_table

    def resolve_references(self, documents: List[ASTDocument]) -> List[ASTDocument]:
        """
        Resolve symbol references in the given documents using the symbol table.
        Returns new documents with resolved references (Symbol.target filled in).
        """
        resolved_documents = []
        
        for doc in documents:
            resolved_doc = self._resolve_document_references(doc)
            resolved_documents.append(resolved_doc)
        
        return resolved_documents

    def _resolve_document_references(self, document: ASTDocument) -> ASTDocument:
        """
        Resolve symbol references in a single document.
        """
        # Walk the AST to find nodes with symbol references
        resolved_root = self._resolve_node_references(document.root)
        
        # Resolve references in top-level symbols too
        resolved_symbols = []
        for symbol in document.symbols:
            resolved_symbol = self._resolve_symbol_references(symbol)
            resolved_symbols.append(resolved_symbol)
        
        return type(document)(
            root=resolved_root,
            symbols=resolved_symbols
        )

    def _resolve_node_references(self, node: ASTNode) -> ASTNode:
        """
        Recursively resolve symbol references in an AST node and its children.
        """
        # Resolve references in the current node
        resolved_symbol_refs = []
        if node.symbol_refs:
            for sym_ref in node.symbol_refs:
                resolved_sym_ref = self._resolve_symbol_references(sym_ref)
                resolved_symbol_refs.append(resolved_sym_ref)
        
        # Process children recursively
        resolved_children = []
        if node.children:
            for child in node.children:
                resolved_child = self._resolve_node_references(child)
                resolved_children.append(resolved_child)
        
        # Return a new node with resolved references
        return type(node)(
            kind=node.kind,
            name=node.name,
            loc=node.loc,
            type=node.type,
            value=node.value,
            modifiers=node.modifiers,
            children=resolved_children if resolved_children else node.children,
            symbol_refs=resolved_symbol_refs if resolved_symbol_refs else node.symbol_refs
        )

    def _resolve_symbol_references(self, symbol: Symbol) -> Symbol:
        """
        Resolve a single symbol reference by finding its target in the symbol table.
        If the reference can be resolved, sets the target field.
        """
        # If symbol already has a target, it's already resolved or intentionally left unresolved
        if symbol.target is not None:
            return symbol
        
        # Look for matching definition by name and kind in the symbol table
        matching_symbols = self.symbol_table.get_symbols_by_name(symbol.name)
        
        # Find the most appropriate match based on kind and context
        for candidate in matching_symbols:
            # For now, match by name and kind (can be extended later)
            # Only match if this is a reference (refers_to is None or not pointing to itself)
            if candidate.kind == symbol.kind and candidate.loc != symbol.loc:
                # Found a match - set the target to point to the definition
                target_id = self.symbol_table.make_symbol_id(candidate)
                return type(symbol)(
                    name=symbol.name,
                    kind=symbol.kind,
                    loc=symbol.loc,
                    refers_to=symbol.refers_to,
                    target=target_id
                )
        
        # No matching definition found, return original symbol unchanged
        return symbol

    def resolve_single_reference(self, ref_symbol: Symbol) -> Optional[Symbol]:
        """
        Attempt to resolve a single symbol reference and return the matched symbol if found.
        """
        if ref_symbol.target is not None:
            # Already resolved
            return self.symbol_table.get_symbol_by_id(ref_symbol.target)
        
        # Look for matching definition
        matching_symbols = self.symbol_table.get_symbols_by_name(ref_symbol.name)
        
        for candidate in matching_symbols:
            if candidate.kind == ref_symbol.kind and candidate.loc != ref_symbol.loc:
                return candidate
        
        return None

"""
Completion provider for Maestro's TU module.
Provides auto-completion capabilities for LSP integration.
"""

from __future__ import annotations

import os
from typing import List, Optional, Dict, Any
from .ast_nodes import ASTDocument, SourceLocation, Symbol
from .symbol_table import SymbolTable


class CompletionItem:
    """Represents a completion item returned by the completion provider."""
    
    def __init__(self, label: str, kind: str, detail: Optional[str] = None, 
                 documentation: Optional[str] = None, insert_text: Optional[str] = None):
        self.label = label
        self.kind = kind
        self.detail = detail
        self.documentation = documentation
        self.insert_text = insert_text or label


class CompletionProvider:
    """
    Provides completion suggestions for a given position in a file.
    """

    def __init__(self, symbol_table: SymbolTable, documents: Dict[str, ASTDocument],
                 use_clang_completion: bool = False):
        """
        Initialize the completion provider.

        Args:
            symbol_table: The symbol table containing all known symbols
            documents: Dictionary mapping file paths to ASTDocument objects
            use_clang_completion: Whether to use clang-based completion (currently not implemented in provider, kept for backward compatibility)
        """
        self.symbol_table = symbol_table
        self.documents = documents
        self.use_clang_completion = use_clang_completion
    
    def get_completion_items(self, 
                           file_path: str, 
                           line: int, 
                           column: int, 
                           prefix: Optional[str] = None,
                           max_results: int = 50) -> List[CompletionItem]:
        """
        Get completion items for a given position in a file.
        
        Args:
            file_path: Path to the file
            line: Line number (1-based)
            column: Column number (1-based)
            prefix: Optional prefix to filter results (if not provided, derived from file content)
            max_results: Maximum number of results to return
        
        Returns:
            List of completion items
        """
        # If prefix is not provided, try to derive it from the file content
        if prefix is None:
            prefix = self._derive_prefix(file_path, line, column)
        
        # Get symbols visible at this location
        visible_symbols = self._get_visible_symbols(file_path, line, prefix)
        
        # Filter symbols based on the prefix
        filtered_symbols = self._filter_symbols_by_prefix(visible_symbols, prefix)
        
        # Convert symbols to completion items
        completion_items = self._symbols_to_completion_items(filtered_symbols)
        
        # Sort completion items by priority (same-file symbols first, then others)
        sorted_items = self._sort_completion_items(completion_items, file_path)
        
        # Return up to max_results items
        return sorted_items[:max_results]
    
    def _derive_prefix(self, file_path: str, line: int, column: int) -> str:
        """
        Derive the prefix from the file content at the given position.
        
        Args:
            file_path: Path to the file
            line: Line number (1-based)
            column: Column number (1-based)
        
        Returns:
            The prefix up to the cursor position
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            if line <= len(lines):
                current_line = lines[line - 1]  # 0-based indexing
                # Extract prefix from start of identifier-like sequence
                # Column is 1-based, so subtract 1 to get 0-based index
                prefix_end = column - 1
                
                # Adjust for potential newline characters at the end of line
                if prefix_end > len(current_line):
                    prefix_end = len(current_line)
                
                # Ensure prefix_end doesn't go negative
                if prefix_end < 0:
                    prefix_end = 0
                    
                # Find the start of the identifier (going backwards from cursor position)
                prefix_start = prefix_end
                while prefix_start > 0:
                    char = current_line[prefix_start - 1]
                    if char.isalnum() or char == '_':
                        prefix_start -= 1
                    else:
                        break
                
                return current_line[prefix_start:prefix_end]
            else:
                return ""
        except Exception:
            return ""
    
    def _get_visible_symbols(self, file_path: str, line: int, prefix: str) -> List[Symbol]:
        """
        Get symbols that are visible at the given line in the file.
        This is a simplified implementation using heuristics.
        
        Args:
            file_path: Path to the file
            line: Line number (1-based)
            prefix: Prefix to filter by (for optimization)
        
        Returns:
            List of visible symbols
        """
        # For now, return all symbols that match the prefix
        # In a more sophisticated implementation, we would analyze scoping rules
        all_symbols = self.symbol_table.get_all_symbols()
        
        if prefix:
            matching_symbols = [
                sym for sym in all_symbols 
                if sym.name.lower().startswith(prefix.lower())
            ]
        else:
            matching_symbols = all_symbols
            
        return matching_symbols
    
    def _filter_symbols_by_prefix(self, symbols: List[Symbol], prefix: str) -> List[Symbol]:
        """
        Filter symbols based on the given prefix.
        
        Args:
            symbols: List of symbols to filter
            prefix: Prefix to filter by
        
        Returns:
            Filtered list of symbols
        """
        if not prefix:
            return symbols
            
        return [
            sym for sym in symbols 
            if sym.name.lower().startswith(prefix.lower())
        ]
    
    def _symbols_to_completion_items(self, symbols: List[Symbol]) -> List[CompletionItem]:
        """
        Convert symbols to completion items.
        
        Args:
            symbols: List of symbols
        
        Returns:
            List of completion items
        """
        items = []
        for symbol in symbols:
            detail = f"{symbol.kind} in {os.path.basename(symbol.loc.file)}"
            item = CompletionItem(
                label=symbol.name,
                kind=symbol.kind,
                detail=detail
            )
            items.append(item)
        return items
    
    def _sort_completion_items(self, items: List[CompletionItem], current_file: str) -> List[CompletionItem]:
        """
        Sort completion items by priority - same-file symbols first.
        
        Args:
            items: List of completion items to sort
            current_file: Path to the current file (to prioritize same-file symbols)
        
        Returns:
            Sorted list of completion items
        """
        def sort_key(item):
            # Find the symbol associated with this item to check its file
            for symbol in self.symbol_table.get_all_symbols():
                if symbol.name == item.label:
                    # Same file gets priority (lower sort value)
                    if symbol.loc.file == current_file:
                        return (0, symbol.name.lower())  # Priority 0 for same file
                    else:
                        return (1, symbol.name.lower())  # Priority 1 for other files
            return (2, item.label.lower())  # Lowest priority if no matching symbol found
        
        return sorted(items, key=sort_key)
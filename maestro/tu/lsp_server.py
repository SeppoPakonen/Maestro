"""
Stub LSP server for Maestro that integrates with TU modules.
Provides basic LSP capabilities using in-process calls.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from pathlib import Path
from .ast_nodes import ASTDocument, SourceLocation, Symbol
from .symbol_table import SymbolTable
from .symbol_resolver import SymbolResolver
from .completion import CompletionProvider
from .tu_builder import TUBuilder


class MaestroLSPServer:
    """
    A stub LSP server that provides basic language server functionality
    using in-process calls to TU modules.
    """
    
    def __init__(self, tu_builder: TUBuilder):
        """
        Initialize the LSP server.
        
        Args:
            tu_builder: TUBuilder instance to use for building translation units
        """
        self.tu_builder = tu_builder
        self.symbol_table = SymbolTable()
        self.documents: Dict[str, ASTDocument] = {}
        self.completion_provider: Optional[CompletionProvider] = None
    
    def reload_documents(self, files: List[str], compile_flags: Optional[List[str]] = None) -> None:
        """
        Reload documents using the TUBuilder.
        
        Args:
            files: List of file paths to reload
            compile_flags: Optional compilation flags
        """
        # Build documents with symbol resolution
        self.documents = self.tu_builder.build_with_symbols(
            files, 
            compile_flags=compile_flags
        )
        
        # Rebuild symbol table
        self.symbol_table = SymbolTable()
        for doc in self.documents.values():
            self.symbol_table.add_document(doc)
        
        # Create/update completion provider
        self.completion_provider = CompletionProvider(self.symbol_table, self.documents)
    
    def get_definition(self, file: str, line: int, column: int) -> Optional[SourceLocation]:
        """
        Get the definition location for the symbol at the given position.
        
        Args:
            file: File path
            line: Line number (1-based)
            column: Column number (1-based)
            
        Returns:
            SourceLocation of the definition or None if not found
        """
        abs_file_path = str(Path(file).resolve())
        
        # Get the document for the given file
        doc = self.documents.get(abs_file_path)
        if not doc:
            return None
        
        # Find the symbol at the given position
        target_symbol = self._find_symbol_at_position(doc, line, column)
        if not target_symbol or not target_symbol.target:
            return None
        
        # Look up the target symbol in the symbol table
        target_symbol_obj = self.symbol_table.get_symbol_by_id(target_symbol.target)
        if not target_symbol_obj:
            return None
        
        return target_symbol_obj.loc
    
    def get_references(self, file: str, line: int, column: int) -> List[SourceLocation]:
        """
        Get all reference locations for the symbol at the given position.
        
        Args:
            file: File path
            line: Line number (1-based)
            column: Column number (1-based)
            
        Returns:
            List of SourceLocation objects representing reference positions
        """
        abs_file_path = str(Path(file).resolve())
        
        # Find the symbol at the given position
        doc = self.documents.get(abs_file_path)
        if not doc:
            return []
        
        target_symbol = self._find_symbol_at_position(doc, line, column)
        if not target_symbol:
            return []
        
        # Get the symbol ID that this symbol refers to
        symbol_id = None
        if target_symbol.target:
            symbol_id = target_symbol.target
        elif target_symbol.refers_to:
            symbol_id = target_symbol.refers_to
        else:
            # If it's a definition, use its own symbol ID
            symbol_id = self.symbol_table.make_symbol_id(target_symbol)
        
        # If we have a symbol ID, find all references to it
        if not symbol_id:
            return []
        
        # Find all symbols that refer to this symbol ID
        references = []
        for doc_path, doc in self.documents.items():
            for symbol in doc.symbols:
                if (symbol.refers_to == symbol_id) or (symbol.target == symbol_id) or self.symbol_table.make_symbol_id(symbol) == symbol_id:
                    references.append(symbol.loc)
        
        return references
    
    def get_completions(self, file: str, line: int, column: int, 
                       prefix: Optional[str] = None, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Get completion suggestions for the given position.
        
        Args:
            file: File path
            line: Line number (1-based)
            column: Column number (1-based)
            prefix: Optional prefix to filter results
            max_results: Maximum number of results to return
            
        Returns:
            List of completion items as dictionaries
        """
        if not self.completion_provider:
            return []
        
        completion_items = self.completion_provider.get_completion_items(
            file, line, column, prefix, max_results
        )
        
        # Convert to dictionaries for easy serialization
        result = []
        for item in completion_items:
            result.append({
                'label': item.label,
                'kind': item.kind,
                'detail': item.detail,
                'documentation': item.documentation,
                'insert_text': item.insert_text
            })
        
        return result
    
    def _find_symbol_at_position(self, doc: ASTDocument, line: int, column: int) -> Optional[Symbol]:
        """
        Find the symbol at the given position in the document.
        
        Args:
            doc: ASTDocument to search
            line: Line number (1-based)
            column: Column number (1-based)
            
        Returns:
            Symbol object or None if not found
        """
        # Search for symbols near the given position
        for symbol in doc.symbols:
            if (symbol.loc.line == line and 
                symbol.loc.column <= column <= symbol.loc.column + len(symbol.name)):
                return symbol
        
        # Also check if the position is near the beginning of a symbol name
        for symbol in doc.symbols:
            if symbol.loc.line == line:
                # Consider symbols that start a bit before the cursor position
                if abs(symbol.loc.column - column) <= len(symbol.name):
                    # Check if cursor is within or right after the symbol name
                    end_column = symbol.loc.column + len(symbol.name)
                    if symbol.loc.column <= column <= end_column:
                        return symbol
        
        return None
"""
Symbol table for managing and combining symbols across multiple AST documents.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set
from .ast_nodes import ASTDocument, Symbol, SourceLocation


class SymbolTable:
    """
    A symbol table that can combine multiple ASTDocuments and provide
    methods for looking up symbols and managing symbol relationships.
    """

    def __init__(self):
        # Dictionary mapping symbol_id to Symbol
        # Symbol ID format: f"{kind}:{name} @{file}:{line}:{column}"
        self.symbols: Dict[str, Symbol] = {}
        
        # Dictionary mapping symbol name to list of symbol IDs (for name-based lookup)
        self.name_to_symbol_ids: Dict[str, List[str]] = {}
        
        # Dictionary mapping file path to set of symbol IDs defined in that file
        self.file_to_symbol_ids: Dict[str, Set[str]] = {}

    def add_document(self, document: ASTDocument) -> None:
        """
        Add symbols from an ASTDocument to the symbol table.
        """
        for symbol in document.symbols:
            symbol_id = self.make_symbol_id(symbol)
            
            # Add the symbol to the main symbol dictionary
            self.symbols[symbol_id] = symbol
            
            # Add to name-based lookup
            if symbol.name not in self.name_to_symbol_ids:
                self.name_to_symbol_ids[symbol.name] = []
            if symbol_id not in self.name_to_symbol_ids[symbol.name]:
                self.name_to_symbol_ids[symbol.name].append(symbol_id)
            
            # Add to file-based lookup
            if symbol.loc.file not in self.file_to_symbol_ids:
                self.file_to_symbol_ids[symbol.loc.file] = set()
            self.file_to_symbol_ids[symbol.loc.file].add(symbol_id)

    def get_symbol_by_id(self, symbol_id: str) -> Optional[Symbol]:
        """
        Get a symbol by its unique ID.
        """
        return self.symbols.get(symbol_id)

    def get_symbols_by_name(self, name: str) -> List[Symbol]:
        """
        Get all symbols with the given name.
        """
        symbol_ids = self.name_to_symbol_ids.get(name, [])
        return [self.symbols[sym_id] for sym_id in symbol_ids if sym_id in self.symbols]

    def get_symbols_in_file(self, file_path: str) -> List[Symbol]:
        """
        Get all symbols defined in the specified file.
        """
        symbol_ids = self.file_to_symbol_ids.get(file_path, set())
        return [self.symbols[sym_id] for sym_id in symbol_ids if sym_id in self.symbols]

    def get_all_symbols(self) -> List[Symbol]:
        """
        Get all symbols in the symbol table.
        """
        return list(self.symbols.values())

    @staticmethod
    def make_symbol_id(symbol: Symbol) -> str:
        """
        Generate a deterministic symbol ID based on kind, name, and location.
        Format: f"{kind}:{name} @{file}:{line}:{column}"
        """
        loc = symbol.loc
        return f"{symbol.kind}:{symbol.name} @{loc.file}:{loc.line}:{loc.column}"

    def combine_with(self, other: SymbolTable) -> SymbolTable:
        """
        Combine this symbol table with another, returning a new combined table.
        """
        combined = SymbolTable()
        
        # Add symbols from this table
        for symbol_id, symbol in self.symbols.items():
            combined.symbols[symbol_id] = symbol
            
            # Add to name-based lookup
            if symbol.name not in combined.name_to_symbol_ids:
                combined.name_to_symbol_ids[symbol.name] = []
            if symbol_id not in combined.name_to_symbol_ids[symbol.name]:
                combined.name_to_symbol_ids[symbol.name].append(symbol_id)
                
            # Add to file-based lookup
            if symbol.loc.file not in combined.file_to_symbol_ids:
                combined.file_to_symbol_ids[symbol.loc.file] = set()
            combined.file_to_symbol_ids[symbol.loc.file].add(symbol_id)
        
        # Add symbols from the other table
        for symbol_id, symbol in other.symbols.items():
            if symbol_id not in combined.symbols:  # Avoid duplicates
                combined.symbols[symbol_id] = symbol
                
                # Add to name-based lookup
                if symbol.name not in combined.name_to_symbol_ids:
                    combined.name_to_symbol_ids[symbol.name] = []
                if symbol_id not in combined.name_to_symbol_ids[symbol.name]:
                    combined.name_to_symbol_ids[symbol.name].append(symbol_id)
                    
                # Add to file-based lookup
                if symbol.loc.file not in combined.file_to_symbol_ids:
                    combined.file_to_symbol_ids[symbol.loc.file] = set()
                combined.file_to_symbol_ids[symbol.loc.file].add(symbol_id)
        
        return combined

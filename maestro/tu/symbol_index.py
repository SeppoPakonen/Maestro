"""
Persistent symbol index backed by SQLite.
"""

from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from .ast_nodes import ASTDocument, Symbol
from .symbol_table import SymbolTable


class SymbolIndex:
    """
    Persistent symbol index backed by SQLite, supporting indexing of definitions
    and resolved references, with lookup by name and location-based queries.
    """

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self._setup_database()

    def _setup_database(self):
        """
        Setup the database tables if they don't exist.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS definitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    file TEXT NOT NULL,
                    line INTEGER NOT NULL,
                    column INTEGER NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS "references" (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    file TEXT NOT NULL,
                    line INTEGER NOT NULL,
                    column INTEGER NOT NULL,
                    target_symbol_id TEXT,
                    FOREIGN KEY (target_symbol_id) REFERENCES definitions (symbol_id)
                )
            """)

            # Create indexes for faster lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_definitions_name ON definitions (name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_definitions_file ON definitions (file)")
            conn.execute('CREATE INDEX IF NOT EXISTS idx_references_name ON "references" (name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_references_file ON "references" (file)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_references_target ON "references" (target_symbol_id)')

    def rebuild_from_symbol_table(self, symbol_table: SymbolTable, resolved_documents: Optional[Sequence[ASTDocument]] = None) -> None:
        """
        Rebuild the index from a symbol table and optionally resolved documents.
        """
        # Clear existing data
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM "references"')
            conn.execute("DELETE FROM definitions")

        # Index all symbols from the symbol table as definitions
        for symbol in symbol_table.get_all_symbols():
            self.add_definition(symbol)

        # If resolved documents are provided, also index the resolved references
        if resolved_documents:
            for doc in resolved_documents:
                self._index_document_references(doc)

    def add_definition(self, symbol: Symbol) -> None:
        """
        Add a symbol definition to the index.
        """
        symbol_id = SymbolTable.make_symbol_id(symbol)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO definitions 
                (symbol_id, name, kind, file, line, column)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol_id,
                    symbol.name,
                    symbol.kind,
                    symbol.loc.file,
                    symbol.loc.line,
                    symbol.loc.column,
                ),
            )

    def add_reference(self, ref_symbol: Symbol, target_symbol_id: Optional[str] = None) -> None:
        """
        Add a symbol reference to the index.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO "references"
                (name, kind, file, line, column, target_symbol_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ref_symbol.name,
                ref_symbol.kind,
                ref_symbol.loc.file,
                ref_symbol.loc.line,
                ref_symbol.loc.column,
                target_symbol_id
            ))

    def _index_document_references(self, document) -> None:
        """
        Index all symbol references in a document.
        """
        # Walk through the document to find all symbol references
        for node in document.root.walk() if hasattr(document, 'root') else []:
            if hasattr(node, 'symbol_refs') and node.symbol_refs:
                for ref_symbol in node.symbol_refs:
                    target_id = ref_symbol.target
                    self.add_reference(ref_symbol, target_id)

        # Also check top-level symbols for references
        if hasattr(document, 'symbols'):
            for symbol in document.symbols:
                if symbol.target:
                    self.add_reference(symbol, symbol.target)

    def get_definitions_by_name(self, name: str) -> List[Dict[str, Any]]:
        """
        Get all definitions with the given name.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT symbol_id, name, kind, file, line, column
                FROM definitions
                WHERE name = ?
            """, (name,))
            
            rows = cursor.fetchall()
            return [dict(zip(['symbol_id', 'name', 'kind', 'file', 'line', 'column'], row)) for row in rows]

    def get_references_by_name(self, name: str) -> List[Dict[str, Any]]:
        """
        Get all references with the given name.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT name, kind, file, line, column, target_symbol_id
                FROM "references"
                WHERE name = ?
            """, (name,))

            rows = cursor.fetchall()
            return [dict(zip(['name', 'kind', 'file', 'line', 'column', 'target_symbol_id'], row)) for row in rows]

    def find_definitions_at_location(self, file_path: str, line: int, column: int) -> List[Dict[str, Any]]:
        """
        Find all definitions at a specific location.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT symbol_id, name, kind, file, line, column
                FROM definitions
                WHERE file = ? AND line = ? AND column = ?
            """, (file_path, line, column))
            
            rows = cursor.fetchall()
            return [dict(zip(['symbol_id', 'name', 'kind', 'file', 'line', 'column'], row)) for row in rows]

    def find_references_to_definition(self, symbol_id: str) -> List[Dict[str, Any]]:
        """
        Find all references that point to a specific definition.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT name, kind, file, line, column, target_symbol_id
                FROM "references"
                WHERE target_symbol_id = ?
            """, (symbol_id,))

            rows = cursor.fetchall()
            return [dict(zip(['name', 'kind', 'file', 'line', 'column', 'target_symbol_id'], row)) for row in rows]

    def find_all_definitions(self) -> List[Dict[str, Any]]:
        """
        Get all definitions in the index.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT symbol_id, name, kind, file, line, column
                FROM definitions
            """)
            
            rows = cursor.fetchall()
            return [dict(zip(['symbol_id', 'name', 'kind', 'file', 'line', 'column'], row)) for row in rows]

    def find_all_references(self) -> List[Dict[str, Any]]:
        """
        Get all references in the index.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT name, kind, file, line, column, target_symbol_id
                FROM "references"
            """)

            rows = cursor.fetchall()
            return [dict(zip(['name', 'kind', 'file', 'line', 'column', 'target_symbol_id'], row)) for row in rows]

    def close(self):
        """
        Close the database connection properly (SQLite handles this automatically with context manager).
        """
        pass  # Context managers handle closing automatically

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Sequence, Union
from .cache import ASTCache, CacheMetadata
from .file_hasher import FileHasher
from .ast_nodes import ASTDocument
from .parser_base import TranslationUnitParser


class TUBuilder:
    """Builds translation units with caching support."""

    def __init__(self, parser: TranslationUnitParser, cache_dir: Union[Path, str] = ".maestro/tu/cache", compress: bool = False):
        self.parser = parser
        self.cache_dir = Path(cache_dir)
        self.compress = compress

        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize hasher and cache
        self.hasher = FileHasher(self.cache_dir / "file_hashes.json")
        self.cache = ASTCache(self.cache_dir)

    def build(self, files: Sequence[Union[str, Path]], *, compile_flags: Optional[Sequence[str]] = None, verbose: bool = False) -> Dict[str, ASTDocument]:
        """Build translation units for the given files."""
        results = {}
        flags_list = list(compile_flags) if compile_flags else None

        for path in files:
            abs_path = str(Path(path).resolve())

            # Compute current hash
            current_hash = self.hasher.hash_file(abs_path)

            # Check if cached
            cached_result = self.cache.load_if_present(current_hash)
            if cached_result is not None:
                document, _ = cached_result
                results[abs_path] = document
            else:
                # Parse the file
                document = self.parser.parse_file(abs_path, compile_flags=compile_flags, verbose=verbose)

                # Store in cache
                metadata = CacheMetadata(
                    source_path=abs_path,
                    file_hash=current_hash,
                    dependencies=None,
                    compile_flags=flags_list,
                )
                self.cache.store(document, metadata, compress=self.compress)

                results[abs_path] = document

            # Update hasher after resolving current file
            self.hasher.update(abs_path, current_hash)

        # Persist file hashes
        self.hasher.persist()

        # Store for later retrieval
        self._last_built_documents = results

        return results

    def get_documents(self) -> Dict[str, ASTDocument]:
        """Return the most recently built documents."""
        # This method is added to expose built documents for LSP integration
        # Note: This is a placeholder that returns an empty dict to satisfy the interface
        # Actual implementation would need to store the last built results
        return getattr(self, '_last_built_documents', {})

    def build_with_symbols(self, files: Sequence[Union[str, Path]], *,
                          compile_flags: Optional[Sequence[str]] = None,
                          build_index: bool = False,
                          index_db_path: Optional[Union[Path, str]] = None) -> Dict[str, ASTDocument]:
        """
        Build translation units with optional symbol resolution and indexing.

        Args:
            files: Files to build
            compile_flags: Compilation flags
            build_index: Whether to build a symbol index
            index_db_path: Path to SQLite database for symbol index (required if build_index=True)

        Returns:
            Dictionary mapping file paths to indexed/resolved ASTDocuments
        """
        from .symbol_table import SymbolTable
        from .symbol_resolver import SymbolResolver

        # Build the basic documents first (using regular build)
        results = self.build(files, compile_flags=compile_flags)

        # Create a symbol table and populate it with symbols from all documents
        symbol_table = SymbolTable()
        for file_path, document in results.items():
            symbol_table.add_document(document)

        # Resolve references
        resolver = SymbolResolver(symbol_table)
        resolved_documents = resolver.resolve_references(list(results.values()))

        # Create a mapping from file path to resolved document
        resolved_results = {}
        file_paths = list(results.keys())  # Maintain the same order
        for i, file_path in enumerate(file_paths):
            resolved_results[file_path] = resolved_documents[i]

        # Store the resolved documents for later retrieval
        self._last_built_documents = resolved_results

        # Optionally build index
        if build_index:
            if index_db_path is None:
                raise ValueError("index_db_path must be provided when build_index=True")

            from .symbol_index import SymbolIndex
            index = SymbolIndex(index_db_path)
            index.rebuild_from_symbol_table(symbol_table, resolved_documents)

        return resolved_results
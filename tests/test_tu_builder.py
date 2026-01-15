import tempfile
import json
from pathlib import Path
from unittest.mock import Mock
import pytest

from maestro.tu import (
    FileHasher,
    CacheMetadata,
    ASTCache,
    TUBuilder,
    ASTDocument,
    ASTNode,
    SourceLocation,
    Symbol,
)
from maestro.tu.parser_base import TranslationUnitParser


def test_file_hasher_persist_round_trip():
    """Test FileHasher persist and load functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "hashes.json"
        hasher = FileHasher(json_path)
        
        # Create a test file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("hello world")
        
        # Hash the file
        hash_val = hasher.hash_file(test_file)
        hasher.update(test_file, hash_val)
        
        # Persist to disk
        hasher.persist()
        
        # Load a new hasher and verify
        new_hasher = FileHasher(json_path)
        assert new_hasher.get(test_file) == hash_val


def test_ast_cache_round_trip_uncompressed():
    """Test ASTCache store/load functionality without compression."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ASTCache(tmpdir)
        
        # Create a sample AST document
        loc = SourceLocation(file="test.c", line=1, column=1)
        node = ASTNode(kind="Function", name="main", loc=loc)
        symbol = Symbol(name="main", kind="Function", loc=loc)
        doc = ASTDocument(root=node, symbols=[symbol])
        
        # Create metadata
        metadata = CacheMetadata(
            source_path="test.c",
            file_hash="abc123",
            dependencies=["stdlib.h"],
            compile_flags=["-Wall"]
        )
        
        # Store and load
        cache.store(doc, metadata, compress=False)
        loaded_doc, loaded_metadata = cache.load("abc123")
        
        # Verify content
        assert loaded_doc.root.kind == "Function"
        assert loaded_doc.root.name == "main"
        assert len(loaded_doc.symbols) == 1
        assert loaded_metadata.source_path == "test.c"
        assert loaded_metadata.dependencies == ["stdlib.h"]
        assert loaded_metadata.compile_flags == ["-Wall"]


def test_ast_cache_round_trip_compressed():
    """Test ASTCache store/load functionality with compression."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ASTCache(tmpdir)
        
        # Create a sample AST document
        loc = SourceLocation(file="test.c", line=1, column=1)
        node = ASTNode(kind="Function", name="main", loc=loc)
        symbol = Symbol(name="main", kind="Function", loc=loc)
        doc = ASTDocument(root=node, symbols=[symbol])
        
        # Create metadata
        metadata = CacheMetadata(
            source_path="test.c",
            file_hash="def456",
            dependencies=["stdio.h"],
            compile_flags=["-O2"]
        )
        
        # Store and load with compression
        cache.store(doc, metadata, compress=True)
        loaded_doc, loaded_metadata = cache.load("def456")
        
        # Verify content
        assert loaded_doc.root.kind == "Function"
        assert loaded_doc.root.name == "main"
        assert len(loaded_doc.symbols) == 1
        assert loaded_metadata.source_path == "test.c"
        assert loaded_metadata.dependencies == ["stdio.h"]
        assert loaded_metadata.compile_flags == ["-O2"]


def test_tu_builder_incremental_behavior():
    """Test TUBuilder incremental parsing behavior."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        file1 = Path(tmpdir) / "file1.c"
        file1.write_text("int main() { return 0; }")
        
        file2 = Path(tmpdir) / "file2.c"
        file2.write_text("void helper() {}")
        
        # Create a mock parser that counts calls
        class CountingParser(TranslationUnitParser):
            def __init__(self):
                self.parse_count = 0
            
            def parse_file(self, path: str, *, compile_flags=None, verbose=False) -> ASTDocument:
                self.parse_count += 1
                loc = SourceLocation(file=path, line=1, column=1)
                node = ASTNode(kind="File", name=Path(path).name, loc=loc)
                return ASTDocument(root=node, symbols=[])
        
        parser = CountingParser()
        builder = TUBuilder(parser, cache_dir=Path(tmpdir) / ".maestro" / "tu" / "cache")
        
        # First build - should parse both files
        results1 = builder.build([file1, file2])
        assert parser.parse_count == 2
        assert len(results1) == 2
        
        # Second build - should use cache, no new parses
        results2 = builder.build([file1, file2])
        assert parser.parse_count == 2  # Count unchanged
        assert len(results2) == 2
        
        # Modify one file and rebuild - should only parse the changed file
        file1.write_text("int main() { return 1; }")  # Change content to change hash
        results3 = builder.build([file1, file2])
        assert parser.parse_count == 3  # One more parse for the modified file
        assert len(results3) == 2
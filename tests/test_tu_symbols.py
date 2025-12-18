import tempfile
import os
from pathlib import Path
from unittest.mock import Mock
import pytest

from maestro.tu import (
    SourceLocation,
    Symbol,
    ASTNode,
    ASTDocument,
    SymbolTable,
    SymbolResolver,
    SymbolIndex,
    TUBuilder,
)
from maestro.tu.parser_base import TranslationUnitParser


def test_symbol_table_basic_functionality():
    """Test basic SymbolTable functionality."""
    table = SymbolTable()
    
    # Create test symbols
    loc1 = SourceLocation(file="test1.c", line=5, column=10)
    loc2 = SourceLocation(file="test2.c", line=10, column=5)
    
    sym1 = Symbol(name="function1", kind="Function", loc=loc1)
    sym2 = Symbol(name="function1", kind="Function", loc=loc2)  # Same name, different location
    
    # Create documents with these symbols
    doc1 = ASTDocument(root=ASTNode(kind="File", name="test1.c", loc=loc1), symbols=[sym1])
    doc2 = ASTDocument(root=ASTNode(kind="File", name="test2.c", loc=loc2), symbols=[sym2])
    
    # Add documents to symbol table
    table.add_document(doc1)
    table.add_document(doc2)
    
    # Test symbol retrieval by name
    symbols = table.get_symbols_by_name("function1")
    assert len(symbols) == 2
    assert sym1 in symbols
    assert sym2 in symbols
    
    # Test symbol retrieval by ID
    sym1_id = f"Function:function1 @{loc1.file}:{loc1.line}:{loc1.column}"
    retrieved_sym1 = table.get_symbol_by_id(sym1_id)
    assert retrieved_sym1 == sym1
    
    # Test symbol retrieval by file
    file1_symbols = table.get_symbols_in_file("test1.c")
    assert len(file1_symbols) == 1
    assert file1_symbols[0] == sym1


def test_symbol_resolver_basic_resolution():
    """Test basic SymbolResolver functionality."""
    # Create test symbols
    func_def_loc = SourceLocation(file="defs.c", line=5, column=5)
    func_call_loc = SourceLocation(file="calls.c", line=10, column=10)
    
    # Definition symbol
    func_def = Symbol(name="my_function", kind="Function", loc=func_def_loc)
    
    # Reference symbol (before resolution)
    func_ref = Symbol(name="my_function", kind="Function", loc=func_call_loc, refers_to=None, target=None)
    
    # Create documents
    def_doc = ASTDocument(root=ASTNode(kind="File", name="defs.c", loc=func_def_loc), symbols=[func_def])
    call_doc = ASTDocument(root=ASTNode(kind="File", name="calls.c", loc=func_call_loc), symbols=[func_ref])
    
    # Create symbol table and populate with definition
    symbol_table = SymbolTable()
    symbol_table.add_document(def_doc)
    
    # Create resolver and resolve references
    resolver = SymbolResolver(symbol_table)
    resolved_docs = resolver.resolve_references([call_doc])
    
    # Check that the reference was resolved
    resolved_ref = resolved_docs[0].symbols[0]
    expected_target = f"Function:my_function @{func_def_loc.file}:{func_def_loc.line}:{func_def_loc.column}"
    assert resolved_ref.target == expected_target


def test_symbol_resolver_cross_file_resolution():
    """Test that references can be resolved across different files."""
    # Create locations
    def_loc = SourceLocation(file="/path/to/defs.c", line=1, column=1)
    ref_loc = SourceLocation(file="/path/to/refs.c", line=5, column=5)
    
    # Create definition and reference symbols
    def_symbol = Symbol(name="shared_func", kind="Function", loc=def_loc)
    ref_symbol = Symbol(name="shared_func", kind="Function", loc=ref_loc)  # Reference to resolve
    
    # Create documents
    def_doc = ASTDocument(root=ASTNode(kind="File", name="defs.c", loc=def_loc), symbols=[def_symbol])
    ref_doc = ASTDocument(root=ASTNode(kind="File", name="refs.c", loc=ref_loc), symbols=[ref_symbol])
    
    # Create symbol table with both documents
    symbol_table = SymbolTable()
    symbol_table.add_document(def_doc)
    symbol_table.add_document(ref_doc)  # Adding both, though only def is needed for resolution
    
    # Create resolver and resolve
    resolver = SymbolResolver(symbol_table)
    resolved_documents = resolver.resolve_references([ref_doc])
    
    # Check the reference was resolved
    resolved_ref = resolved_documents[0].symbols[0]
    expected_target = f"Function:shared_func @{def_loc.file}:{def_loc.line}:{def_loc.column}"
    assert resolved_ref.target == expected_target


def test_symbol_index_basic_functionality():
    """Test basic SymbolIndex functionality."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_db:
        tmp_db_path = tmp_db.name
    
    try:
        # Create index
        index = SymbolIndex(tmp_db_path)
        
        # Create test symbols
        def_loc = SourceLocation(file="defs.c", line=5, column=10)
        ref_loc = SourceLocation(file="refs.c", line=15, column=20)
        
        def_symbol = Symbol(name="test_func", kind="Function", loc=def_loc)
        ref_symbol = Symbol(name="test_func", kind="Function", loc=ref_loc)
        
        # Add definition to index
        index.add_definition(def_symbol)
        
        # Add reference to index with target
        index.add_reference(ref_symbol, f"Function:test_func @{def_loc.file}:{def_loc.line}:{def_loc.column}")
        
        # Test definition lookup
        defs = index.get_definitions_by_name("test_func")
        assert len(defs) == 1
        assert defs[0]['name'] == "test_func"
        assert defs[0]['file'] == "defs.c"
        
        # Test reference lookup
        refs = index.get_references_by_name("test_func")
        assert len(refs) == 1
        assert refs[0]['name'] == "test_func"
        assert refs[0]['file'] == "refs.c"
        
        # Test location-based lookup
        defs_at_loc = index.find_definitions_at_location("defs.c", 5, 10)
        assert len(defs_at_loc) == 1
        assert defs_at_loc[0]['name'] == "test_func"
    finally:
        # Clean up
        os.unlink(tmp_db_path)


def test_symbol_index_rebuild():
    """Test rebuilding the index from symbol table and resolved documents."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_db:
        tmp_db_path = tmp_db.name
    
    try:
        # Create test data
        def_loc = SourceLocation(file="defs.c", line=1, column=1)
        ref_loc = SourceLocation(file="refs.c", line=5, column=5)
        
        def_symbol = Symbol(name="my_func", kind="Function", loc=def_loc)
        ref_symbol = Symbol(name="my_func", kind="Function", loc=ref_loc)
        
        # Set up a target for the reference (simulating a resolved reference)
        ref_symbol.target = f"Function:my_func @{def_loc.file}:{def_loc.line}:{def_loc.column}"
        
        def_doc = ASTDocument(root=ASTNode(kind="File", name="defs.c", loc=def_loc), symbols=[def_symbol])
        ref_doc = ASTDocument(root=ASTNode(kind="File", name="refs.c", loc=ref_loc), symbols=[ref_symbol])
        
        # Create symbol table
        symbol_table = SymbolTable()
        symbol_table.add_document(def_doc)
        
        # Create and rebuild index
        index = SymbolIndex(tmp_db_path)
        index.rebuild_from_symbol_table(symbol_table, [def_doc, ref_doc])
        
        # Verify that both definitions and references are indexed
        defs = index.get_definitions_by_name("my_func")
        refs = index.get_references_by_name("my_func")
        
        assert len(defs) == 1
        assert len(refs) == 1
        assert defs[0]['file'] == "defs.c"
        assert refs[0]['file'] == "refs.c"
        assert refs[0]['target_symbol_id'] is not None
    finally:
        # Clean up
        os.unlink(tmp_db_path)


def test_build_with_symbols_integration():
    """Test the TUBuilder.build_with_symbols integration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        file1 = Path(tmpdir) / "defs.c"
        file1.write_text("int test_function() { return 0; }")

        file2 = Path(tmpdir) / "refs.c"
        file2.write_text("int main() { return test_function(); }")  # References test_function

        # Create a mock parser that creates ASTs with symbols
        class MockParser(TranslationUnitParser):
            def __init__(self):
                self.call_count = 0

            def parse_file(self, path: str, *, compile_flags=None) -> ASTDocument:
                self.call_count += 1

                # Create different locations based on file
                if "defs.c" in path:
                    loc = SourceLocation(file=path, line=1, column=5)  # Location of function definition
                    # Create a function definition symbol
                    func_def = Symbol(name="test_function", kind="Function", loc=loc)
                    node = ASTNode(kind="FunctionDef", name="test_function", loc=loc)
                    return ASTDocument(root=node, symbols=[func_def])
                else:  # refs.c
                    loc = SourceLocation(file=path, line=1, column=25)  # Location of function call
                    # Create a function reference symbol
                    func_ref = Symbol(name="test_function", kind="Function", loc=loc)
                    node = ASTNode(kind="FunctionCall", name="test_function", loc=loc, symbol_refs=[func_ref])
                    return ASTDocument(root=node, symbols=[])

        parser = MockParser()
        builder = TUBuilder(parser, cache_dir=Path(tmpdir) / ".maestro" / "cache")

        # Call build_with_symbols
        results = builder.build_with_symbols([file1, file2])

        # Verify both files were parsed
        assert len(results) == 2
        assert parser.call_count == 2  # Both files should be parsed if not in cache

        # Verify the reference was resolved
        refs_path = str(file2.resolve())
        if refs_path in results:
            refs_doc = results[refs_path]  # Get the document for refs.c
            if hasattr(refs_doc.root, 'symbol_refs') and refs_doc.root.symbol_refs:
                ref_symbol = refs_doc.root.symbol_refs[0]
                assert ref_symbol.target is not None  # Should be resolved
                assert "test_function" in ref_symbol.target


def test_build_with_symbols_and_index():
    """Test building with symbols and creating an index."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        file1 = Path(tmpdir) / "defs.c"
        file1.write_text("int shared_func() { return 0; }")
        
        file2 = Path(tmpdir) / "usage.c"
        file2.write_text("int main() { return shared_func(); }")
        
        # Create mock parser
        class MockParser(TranslationUnitParser):
            def parse_file(self, path: str, *, compile_flags=None) -> ASTDocument:
                if "defs.c" in path:
                    loc = SourceLocation(file=path, line=1, column=5)
                    func_def = Symbol(name="shared_func", kind="Function", loc=loc)
                    node = ASTNode(kind="FunctionDef", name="shared_func", loc=loc)
                    return ASTDocument(root=node, symbols=[func_def])
                else:  # usage.c
                    loc = SourceLocation(file=path, line=1, column=25)
                    func_ref = Symbol(name="shared_func", kind="Function", loc=loc)
                    node = ASTNode(kind="FunctionCall", name="shared_func", loc=loc, symbol_refs=[func_ref])
                    return ASTDocument(root=node, symbols=[])
        
        parser = MockParser()
        builder = TUBuilder(parser, cache_dir=Path(tmpdir) / ".maestro" / "cache")
        
        # Create index DB path
        index_db_path = Path(tmpdir) / "symbols.db"
        
        # Build with symbols and index
        results = builder.build_with_symbols([file1, file2], build_index=True, index_db_path=index_db_path)
        
        # Verify results
        assert len(results) == 2
        
        # Verify index exists and has data
        index = SymbolIndex(index_db_path)
        defs = index.get_definitions_by_name("shared_func")
        refs = index.get_references_by_name("shared_func")
        
        assert len(defs) >= 1  # At least one definition
        assert len(refs) >= 1  # At least one reference
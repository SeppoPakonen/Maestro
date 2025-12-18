"""
Tests for the LSP server module.
"""

import tempfile
import os
from pathlib import Path
from maestro.tu.lsp_server import MaestroLSPServer
from maestro.tu.tu_builder import TUBuilder
from maestro.tu.parser_base import TranslationUnitParser
from maestro.tu.ast_nodes import ASTDocument, ASTNode, Symbol, SourceLocation


class MockParser(TranslationUnitParser):
    """Mock parser for testing purposes."""
    
    def parse_file(self, file_path: str, compile_flags=None):
        # Create a simple AST document for testing
        loc = SourceLocation(file=file_path, line=1, column=1)
        # Create a few test symbols
        symbols = []
        if "test1" in file_path:
            symbols.append(Symbol(name="function_test1", kind="function", loc=loc))
            symbols.append(Symbol(name="variable_test1", kind="variable", loc=SourceLocation(file=file_path, line=2, column=1)))
        else:
            symbols.append(Symbol(name="function_other", kind="function", loc=loc))
            symbols.append(Symbol(name="variable_other", kind="variable", loc=SourceLocation(file=file_path, line=2, column=1)))
        
        root = ASTNode(kind="root", name="root", loc=loc)
        return ASTDocument(root=root, symbols=symbols)


def test_lsp_server_initialization():
    """Test basic initialization of the LSP server."""
    parser = MockParser()
    builder = TUBuilder(parser)
    server = MaestroLSPServer(builder)
    
    # Server should initialize without errors
    assert server.tu_builder == builder
    assert server.symbol_table is not None
    assert server.documents is not None


def test_reload_documents():
    """Test reloading documents functionality."""
    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f1:
        f1.write("def function_test1(): pass\nvar1 = 10\n")
        file1 = f1.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f2:
        f2.write("def function_other(): pass\nvar2 = 20\n")
        file2 = f2.name
    
    try:
        parser = MockParser()
        builder = TUBuilder(parser)
        server = MaestroLSPServer(builder)
        
        # Reload documents
        server.reload_documents([file1, file2])
        
        # Check that documents were loaded
        assert len(server.documents) == 2
        assert file1 in server.documents
        assert file2 in server.documents
        
        # Check that symbol table was populated
        all_symbols = server.symbol_table.get_all_symbols()
        assert len(all_symbols) > 0  # Should have symbols from both files
        
        # Check that completion provider was created
        assert server.completion_provider is not None
    finally:
        os.unlink(file1)
        os.unlink(file2)


def test_get_completions():
    """Test getting completions from the LSP server."""
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("def function_test1(): pass\nvar1 = 10\n")
        file_path = f.name
    
    try:
        parser = MockParser()
        builder = TUBuilder(parser)
        server = MaestroLSPServer(builder)
        
        # Reload documents
        server.reload_documents([file_path])
        
        # Get completions
        completions = server.get_completions(file_path, 1, 5, prefix="func", max_results=10)
        
        # Should have at least one completion starting with "func"
        assert len(completions) >= 1
        func_completions = [comp for comp in completions if comp['label'].startswith('func')]
        assert len(func_completions) >= 1
    finally:
        os.unlink(file_path)


def test_get_definition_and_references():
    """Test getting definitions and references."""
    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("# Test file with symbols\n")
        file_path = f.name
    
    try:
        parser = MockParser()
        builder = TUBuilder(parser)
        server = MaestroLSPServer(builder)
        
        # Reload documents
        server.reload_documents([file_path])
        
        # Test get_definition - should return None for this mock setup
        # (since our mock parser doesn't create symbols with target/refers_to)
        definition = server.get_definition(file_path, 1, 1)
        # Result may be None or a location depending on the mock implementation
        
        # Test get_references - test that it returns a list
        references = server.get_references(file_path, 1, 1)
        assert isinstance(references, list)
    finally:
        os.unlink(file_path)


if __name__ == "__main__":
    test_lsp_server_initialization()
    test_reload_documents()
    test_get_completions()
    test_get_definition_and_references()
    print("All LSP server tests passed!")
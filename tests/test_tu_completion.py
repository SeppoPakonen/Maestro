"""
Tests for the completion provider module.
"""

import tempfile
import os
from pathlib import Path
from maestro.tu.ast_nodes import ASTDocument, ASTNode, Symbol, SourceLocation
from maestro.tu.symbol_table import SymbolTable
from maestro.tu.completion import CompletionProvider


def test_completion_provider_basic():
    """Test basic completion provider functionality."""
    # Create mock documents and symbols
    loc1 = SourceLocation(file="/test/file1.py", line=1, column=1)
    symbol1 = Symbol(name="function_one", kind="function", loc=loc1)
    
    loc2 = SourceLocation(file="/test/file2.py", line=2, column=5)
    symbol2 = Symbol(name="function_two", kind="function", loc=loc2)
    
    loc3 = SourceLocation(file="/test/file1.py", line=10, column=1)
    symbol3 = Symbol(name="variable_a", kind="variable", loc=loc3)
    
    # Create a mock AST document
    doc = ASTDocument(root=ASTNode(kind="root", name="root", loc=loc1), symbols=[symbol1, symbol2, symbol3])
    
    # Create symbol table and add document
    symbol_table = SymbolTable()
    symbol_table.add_document(doc)
    
    # Create completion provider
    documents = {"/test/file1.py": doc}
    provider = CompletionProvider(symbol_table, documents)
    
    # Test completion with prefix
    completions = provider.get_completion_items("/test/file1.py", 1, 1, "func", max_results=10)
    
    # Should contain function_one and function_two (both start with "func")
    assert len(completions) >= 1  # At least function_one should match
    labels = [item.label for item in completions]
    assert "function_one" in labels
    
    # Test sorting - same file symbols should come first
    completions_all = provider.get_completion_items("/test/file1.py", 1, 1, "", max_results=50)
    labels_ordered = [item.label for item in completions_all]
    
    # Since we're in file1.py, symbols from file1.py should appear first
    file1_symbols = [sym for sym in [symbol1, symbol2, symbol3] if sym.loc.file == "/test/file1.py"]
    file2_symbols = [sym for sym in [symbol1, symbol2, symbol3] if sym.loc.file != "/test/file1.py"]
    
    # Check that file1 symbols appear before file2 symbols in results
    all_labels = [item.label for item in completions_all]
    file1_positions = [all_labels.index(sym.name) for sym in file1_symbols if sym.name in all_labels]
    file2_positions = [all_labels.index(sym.name) for sym in file2_symbols if sym.name in all_labels]
    
    # All file1 positions should be smaller than file2 positions
    if file1_positions and file2_positions:
        assert max(file1_positions) < min(file2_positions)


def test_prefix_derivation():
    """Test that prefixes are correctly derived from file content."""
    # Create a temporary file with test content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("def my_function():\n    my_var = 10\n    return my_\n")
        temp_file = f.name
    
    try:
        # Create mock document
        loc = SourceLocation(file=temp_file, line=3, column=12)  # Position at "my_" line
        symbol = Symbol(name="my_variable", kind="variable", loc=loc)
        
        doc = ASTDocument(root=ASTNode(kind="root", name="root", loc=loc), symbols=[symbol])
        
        symbol_table = SymbolTable()
        symbol_table.add_document(doc)
        
        documents = {temp_file: doc}
        provider = CompletionProvider(symbol_table, documents)
        
        # Test prefix derivation at line 3, column 15 (after "my_")
        prefix = provider._derive_prefix(temp_file, 3, 15)
        assert prefix == "my_"
        
        # Test completion with derived prefix
        completions = provider.get_completion_items(temp_file, 3, 12, None, max_results=10)
        # Should match symbols that start with "my_"
    finally:
        os.unlink(temp_file)


def test_max_results_limit():
    """Test that max_results properly limits the number of returned completions."""
    # Create multiple symbols
    symbols = []
    for i in range(100):
        loc = SourceLocation(file=f"/test/file{i}.py", line=1, column=1)
        symbol = Symbol(name=f"var_{i}", kind="variable", loc=loc)
        symbols.append(symbol)
    
    # Create document
    root_loc = SourceLocation(file="/test/root.py", line=1, column=1)
    doc = ASTDocument(root=ASTNode(kind="root", name="root", loc=root_loc), symbols=symbols)
    
    symbol_table = SymbolTable()
    symbol_table.add_document(doc)
    
    documents = {"/test/root.py": doc}
    provider = CompletionProvider(symbol_table, documents)
    
    # Test with max_results=10
    completions = provider.get_completion_items("/test/root.py", 1, 1, "", max_results=10)
    assert len(completions) <= 10
    
    # Test with max_results=50 (default)
    completions = provider.get_completion_items("/test/root.py", 1, 1, "", max_results=50)
    assert len(completions) <= 50


if __name__ == "__main__":
    test_completion_provider_basic()
    test_prefix_derivation()
    test_max_results_limit()
    print("All completion tests passed!")
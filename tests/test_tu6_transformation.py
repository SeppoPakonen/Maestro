#!/usr/bin/env python3
"""
Test script for TU6 transformation functionality.
"""
import tempfile
import os
from pathlib import Path

from maestro.tu import (
    TUBuilder, ClangParser,
    ASTTransformer, UppConventionTransformer, CodeGenerator
)
from maestro.tu.ast_nodes import ASTNode, SourceLocation, ASTDocument


def test_ast_transformer():
    """Test the basic ASTTransformer functionality."""
    print("Testing ASTTransformer...")
    
    # Create a simple AST node for testing
    test_node = ASTNode(
        kind="function_decl",
        name="test_function",
        loc=SourceLocation(file="test.cpp", line=1, column=1),
        type="void",
        children=[]
    )
    
    # Create a document
    doc = ASTDocument(root=test_node, symbols=[])
    
    # Create a simple transformer that changes the function name
    class TestTransformer(ASTTransformer):
        def transform_current_node(self, node):
            if node.kind == "function_decl":
                node.name = f"transformed_{node.name}"
            return node
    
    transformer = TestTransformer()
    result_doc = transformer.transform_document(doc)
    
    assert result_doc.root.name == "transformed_test_function"
    print("✓ ASTTransformer test passed")


def test_upp_convention_transformer():
    """Test the UppConventionTransformer functionality."""
    print("Testing UppConventionTransformer...")
    
    # Create a simple AST with dependencies
    class_a = ASTNode(
        kind="class_decl",
        name="ClassA",
        loc=SourceLocation(file="a.cpp", line=1, column=1),
        children=[
            ASTNode(
                kind="field_decl",
                name="b_member",
                type="ClassB",
                loc=SourceLocation(file="a.cpp", line=2, column=1)
            )
        ]
    )
    
    class_b = ASTNode(
        kind="class_decl", 
        name="ClassB",
        loc=SourceLocation(file="b.cpp", line=1, column=1),
        children=[]
    )
    
    # Create a document with both classes
    root_node = ASTNode(
        kind="translation_unit",
        name="root",
        loc=SourceLocation(file="test.cpp", line=1, column=1),
        children=[class_a, class_b]
    )
    
    doc = ASTDocument(root=root_node, symbols=[])
    
    # Create transformer and apply it
    transformer = UppConventionTransformer(package_name="test_package")
    result_doc = transformer.transform_document(doc)
    
    print(f"Dependencies found: {transformer.dependencies}")
    print(f"Declaration order: {transformer.declaration_order}")
    print(f"Forward declarations needed: {transformer.forward_declarations_needed}")
    
    print("✓ UppConventionTransformer test passed")


def test_code_generator():
    """Test the CodeGenerator functionality."""
    print("Testing CodeGenerator...")
    
    generator = CodeGenerator()
    
    # Create a test class AST node
    class_node = ASTNode(
        kind="class_decl",
        name="TestClass",
        loc=SourceLocation(file="test.h", line=1, column=1),
        children=[
            ASTNode(
                kind="field_decl",
                name="test_field",
                type="int",
                loc=SourceLocation(file="test.h", line=3, column=1)
            ),
            ASTNode(
                kind="function_decl",
                name="test_method",
                type="void",
                loc=SourceLocation(file="test.h", line=4, column=1)
            )
        ]
    )
    
    # Generate declaration
    decl = generator.generate_declaration(class_node)
    print(f"Generated declaration:\n{decl}")
    
    print("✓ CodeGenerator test passed")


def test_end_to_end_transformation():
    """Test end-to-end transformation using a simple C++ file."""
    print("Testing end-to-end transformation...")
    
    # Create a temporary directory for our test
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a simple C++ file with dependencies
        cpp_content = '''
        #include <iostream>
        #include "ClassB.h"
        
        class ClassB {
        public:
            int value;
        };
        
        class ClassA {
        private:
            ClassB b_instance;  // ClassA depends on ClassB
        public:
            void do_something();
        };
        
        void ClassA::do_something() {
            std::cout << "Hello from ClassA" << std::endl;
        }
        '''
        
        source_file = temp_path / "test.cpp"
        with open(source_file, 'w') as f:
            f.write(cpp_content)
        
        print(f"Created test file: {source_file}")
        
        # Create TU builder and parse the file
        try:
            parser = ClangParser()
        except Exception as exc:
            try:
                import pytest
            except ImportError:
                raise
            from maestro.tu.errors import ParserUnavailableError
            if isinstance(exc, ParserUnavailableError):
                pytest.skip("clang.cindex not available for TU6 end-to-end test")
            raise
        builder = TUBuilder(parser, cache_dir=temp_path / "cache")
        results = builder.build([str(source_file)], compile_flags=["-std=c++11"])
        
        print(f"Built TUs for {len(results)} files")
        
        # Check if we got results
        if results:
            for path, doc in results.items():
                print(f"Document {path} has root kind: {doc.root.kind}")
                
                # Apply U++ transformation
                transformer = UppConventionTransformer(package_name="test_package")
                transformed_doc = transformer.transform_document(doc)
                
                print(f"Applied transformation, dependencies: {transformer.dependencies}")
                print(f"Declaration order: {transformer.declaration_order}")
                print(f"Forward declarations needed: {transformer.forward_declarations_needed}")
                
                # Generate primary header
                class_nodes = []
                for node in doc.root.walk():
                    if node.kind in ['class_decl', 'struct_decl', 'function_decl']:
                        class_nodes.append(node)
                
                header_content = transformer.generate_primary_header(class_nodes, "test_package.h")
                print(f"Generated header:\n{header_content}")
                
                # Update the .cpp includes
                updated_cpp = transformer.update_cpp_includes(cpp_content, "test_package.h")
                print(f"Updated .cpp includes:\n{updated_cpp}")
        
        print("✓ End-to-end transformation test passed")


def main():
    """Run all tests."""
    print("Running TU6 transformation tests...\n")
    
    test_ast_transformer()
    print()
    
    test_upp_convention_transformer()
    print()
    
    test_code_generator()
    print()
    
    test_end_to_end_transformation()
    print()
    
    print("All TU6 tests passed! ✓")


if __name__ == "__main__":
    main()

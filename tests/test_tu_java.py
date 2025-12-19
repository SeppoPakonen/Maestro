import os
import tempfile
from pathlib import Path

import pytest

from maestro.tu import JavaParser, ASTSerializer


def test_java_parser_simple_class():
    """Test parsing a simple Java class."""
    # Skip test if tree-sitter-java is not available
    try:
        parser = JavaParser()
    except Exception:
        pytest.skip("tree-sitter-java not available")

    java_code = """
public class HelloWorld {
    private String message;

    public HelloWorld(String message) {
        this.message = message;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }
}
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
        f.write(java_code)
        temp_path = f.name

    try:
        result = parser.parse_file(temp_path)

        # Check that we have a root node
        assert result.root is not None
        assert result.root.kind == 'program'

        # Check that we have symbols
        assert len(result.symbols) > 0

        # Find the class symbol
        class_symbols = [s for s in result.symbols if s.kind == 'class_declaration' and s.name == 'HelloWorld']
        assert len(class_symbols) == 1

        # Find the field symbol
        field_symbols = [s for s in result.symbols if s.kind == 'field_declaration']
        assert len(field_symbols) >= 1

        # Find method symbols
        method_symbols = [s for s in result.symbols if s.kind == 'method_declaration']
        assert len(method_symbols) >= 3  # constructor + getMessage + setMessage

    finally:
        os.unlink(temp_path)


def test_java_parser_serialization():
    """Test that Java parser results can be serialized."""
    # Skip test if tree-sitter-java is not available
    try:
        parser = JavaParser()
    except Exception:
        pytest.skip("tree-sitter-java not available")

    java_code = """
public class SimpleClass {
    int x;
}
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
        f.write(java_code)
        temp_path = f.name

    try:
        result = parser.parse_file(temp_path)

        # Test serialization
        serializer = ASTSerializer()
        data = serializer.serialize(result)

        # Test deserialization
        restored = serializer.deserialize(data)

        # Check that the restored document is equivalent
        assert restored.root.kind == result.root.kind
        assert len(restored.symbols) == len(result.symbols)

    finally:
        os.unlink(temp_path)
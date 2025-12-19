import os
import tempfile
from pathlib import Path

import pytest

from maestro.tu import KotlinParser, ASTSerializer


def test_kotlin_parser_simple_class():
    """Test parsing a simple Kotlin class."""
    # Skip test if tree-sitter-kotlin is not available
    try:
        parser = KotlinParser()
    except Exception:
        pytest.skip("tree-sitter-kotlin not available")

    kotlin_code = """
class Greeter(val name: String) {
    fun greet(): String {
        return "Hello, $name!"
    }

    var message: String = "Default"

    fun setMessage(newMessage: String) {
        message = newMessage
    }
}
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.kt', delete=False) as f:
        f.write(kotlin_code)
        temp_path = f.name

    try:
        result = parser.parse_file(temp_path)

        # Check that we have a root node
        assert result.root is not None
        assert result.root.kind == 'program'

        # Check that we have symbols
        assert len(result.symbols) > 0

        # Find the class symbol
        class_symbols = [s for s in result.symbols if s.kind == 'class_declaration' and s.name == 'Greeter']
        assert len(class_symbols) == 1

        # Find the property symbol
        property_symbols = [s for s in result.symbols if s.kind == 'property_declaration']
        assert len(property_symbols) >= 1

        # Find function symbols
        function_symbols = [s for s in result.symbols if s.kind == 'function_declaration']
        assert len(function_symbols) >= 2  # greet + setMessage

    finally:
        os.unlink(temp_path)


def test_kotlin_parser_serialization():
    """Test that Kotlin parser results can be serialized."""
    # Skip test if tree-sitter-kotlin is not available
    try:
        parser = KotlinParser()
    except Exception:
        pytest.skip("tree-sitter-kotlin not available")

    kotlin_code = """
class SimpleClass {
    var x: Int = 0
}
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.kt', delete=False) as f:
        f.write(kotlin_code)
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
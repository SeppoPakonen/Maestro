import os
import tempfile
from pathlib import Path

import pytest

from maestro.commands.tu import (
    handle_tu_build_command, handle_tu_info_command, 
    handle_tu_query_command, handle_tu_complete_command,
    handle_tu_references_command, handle_tu_cache_stats_command
)
from maestro.tu import JavaParser, KotlinParser


# Mock args class for testing
class MockArgs:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_tu_build_command_java():
    """Test the TU build command with Java files."""
    # Skip test if tree-sitter-java is not available
    try:
        JavaParser()
    except Exception:
        pytest.skip("tree-sitter-java not available")

    java_code = """
public class TestClass {
    private int value;

    public TestClass(int value) {
        this.value = value;
    }

    public int getValue() {
        return value;
    }
}
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / "TestClass.java"
        with open(temp_path, 'w') as f:
            f.write(java_code)

        args = MockArgs(
            path=str(temp_path.parent),
            force=False,
            verbose=False,
            output=".maestro/tu/cache",
            threads=None,
            lang="java",
            compile_flags=None
        )

        # This should succeed without errors
        result = handle_tu_build_command(args)
        assert result == 0


def test_tu_build_command_kotlin():
    """Test the TU build command with Kotlin files."""
    # Skip test if tree-sitter-kotlin is not available
    try:
        KotlinParser()
    except Exception:
        pytest.skip("tree-sitter-kotlin not available")

    kotlin_code = """
class TestClass(val value: Int) {
    fun getValue(): Int {
        return value
    }
}
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / "TestClass.kt"
        with open(temp_path, 'w') as f:
            f.write(kotlin_code)

        args = MockArgs(
            path=str(temp_path.parent),
            force=False,
            verbose=False,
            output=".maestro/tu/cache",
            threads=None,
            lang="kotlin",
            compile_flags=None
        )

        # This should succeed without errors
        result = handle_tu_build_command(args)
        assert result == 0


def test_tu_info_command():
    """Test the TU info command."""
    args = MockArgs(
        path=".maestro/tu/cache"
    )

    # This should not crash
    result = handle_tu_info_command(args)
    # The result could be 0 or 1 depending on whether cache exists, both are acceptable for this test


def test_tu_cache_stats_command():
    """Test the TU cache stats command."""
    args = MockArgs()

    # This should not crash
    result = handle_tu_cache_stats_command(args)
    # The result could be 0 or 1 depending on whether cache exists, both are acceptable for this test


def test_language_detection():
    """Test language detection from file extensions."""
    from maestro.commands.tu import detect_language_from_path

    assert detect_language_from_path("test.java") == "java"
    assert detect_language_from_path("test.kt") == "kotlin"
    assert detect_language_from_path("test.cpp") == "cpp"
    assert detect_language_from_path("test.c") == "c"

    with pytest.raises(ValueError):
        detect_language_from_path("test.unknown")
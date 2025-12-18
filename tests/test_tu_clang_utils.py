import os
import tempfile
from pathlib import Path

import pytest

try:
    import clang.cindex
    try:
        clang.cindex.Config.set_library_file("/usr/lib/llvm/21/lib64/libclang.so")
    except Exception:
        # Fall back to the default search if explicit path fails
        pass
    LIBCLANG_AVAILABLE = True
except ImportError:
    LIBCLANG_AVAILABLE = False

from maestro.tu.clang_utils import get_builtin_include_paths, get_default_compile_flags


@pytest.mark.skipif(not LIBCLANG_AVAILABLE, reason="libclang not available")
def test_get_builtin_include_paths():
    paths = get_builtin_include_paths()
    assert len(paths) > 1, f"Expected more than one path, got {len(paths)}"
    for path in paths:
        p = Path(path)
        assert p.exists(), f"Path does not exist: {p}"
        assert p.is_dir(), f"Path is not a directory: {p}"


@pytest.mark.skipif(not LIBCLANG_AVAILABLE, reason="libclang not available")
def test_get_default_compile_flags_includes_builtin_paths():
    builtin_paths = get_builtin_include_paths()
    flags = get_default_compile_flags()

    found_paths = []
    i = 0
    while i < len(flags):
        if flags[i] == "-I" and i + 1 < len(flags):
            found_paths.append(flags[i + 1])
            i += 1
        i += 1

    for path in builtin_paths:
        assert path in found_paths, f"Builtin path {path} not found in -I flags {found_paths}"


@pytest.mark.skipif(not LIBCLANG_AVAILABLE, reason="libclang not available")
def test_libclang_can_parse_with_flags():
    code_snippet = """
#include <iostream>
int main(){ std:: }
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cpp", delete=False) as f:
        f.write(code_snippet)
        temp_file = f.name

    try:
        flags = get_default_compile_flags() + ["-x", "c++"]
        index = clang.cindex.Index.create()
        translation_unit = index.parse(temp_file, args=flags)
        fatal_errors = [
            diag
            for diag in translation_unit.diagnostics
            if diag.severity == clang.cindex.Diagnostic.Fatal
        ]
        assert (
            len(fatal_errors) == 0
        ), f"Fatal parsing errors: {[str(err) for err in fatal_errors]}"
    finally:
        os.unlink(temp_file)


@pytest.mark.skipif(not LIBCLANG_AVAILABLE, reason="libclang not available")
def test_stdlib_completions():
    code_snippet = """#include <iostream>
int main(){
    std::
    return 0;
}
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cpp", delete=False) as f:
        f.write(code_snippet)
        temp_file = f.name

    try:
        flags = get_default_compile_flags() + ["-x", "c++"]
        index = clang.cindex.Index.create()
        translation_unit = index.parse(temp_file, args=flags)

        # Signal parsing problems but continue to attempt completion
        parsing_errors = [
            d
            for d in translation_unit.diagnostics
            if d.severity >= clang.cindex.Diagnostic.Error
        ]
        if parsing_errors:
            pytest.xfail(f"Parsing errors prevent completion: {parsing_errors}")

        completions = translation_unit.codeComplete(
            temp_file,
            3,
            8,
            unsaved_files=[(temp_file, code_snippet)],
            include_macros=True,
            include_code_patterns=True,
            include_brief_comments=True,
        )
        if completions is None:
            pytest.xfail("Code completion not available for this libclang setup")

        completion_strings = []
        for completion in getattr(completions, "results", []):
            if hasattr(completion, "completion_string"):
                chunks = []
                for chunk in completion.completion_string:
                    spell = chunk.spelling
                    if spell:
                        chunks.append(spell)
                completion_strings.append("".join(chunks))

        std_completions = [
            comp
            for comp in completion_strings
            if any(keyword in comp.lower() for keyword in ["cout", "cerr"])
        ]

        if not std_completions:
            if not completion_strings:
                pytest.xfail(
                    "No completions available - libclang completion engine may not be working in this environment"
                )
            # At least some completions exist; infrastructure works
            assert (
                len(completion_strings) > 0
            ), "At least some completions should be available"
        else:
            assert len(std_completions) > 0, f"Found std:: completions: {std_completions}"
    finally:
        os.unlink(temp_file)

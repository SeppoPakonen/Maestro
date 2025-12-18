# TU/AST Scaffolding Notes

## Purpose

The `maestro/tu` modules introduce the initial TU/AST scaffolding for Phase TU1:
- Common data model for `ASTNode`, `SourceLocation`, and symbols
- Optional C/C++ parsing via `clang.cindex`
- Placeholders for Java/Kotlin parsers (planned tree-sitter or similar backends)

## Setup

Install libclang (optional for C/C++ parsing):

```bash
pip install libclang
```

If libclang cannot be located, set `LIBCLANG_PATH` to the shared library:

```bash
export LIBCLANG_PATH=/path/to/libclang.so    # Linux
export LIBCLANG_PATH=/path/to/libclang.dylib # macOS
```

## Running Tests

Run the TU/AST smoke tests with pytest:

```bash
python -m pytest tests/test_tu_ast.py
```

Or execute the test file directly:

```bash
python tests/test_tu_ast.py
```

# maestro tu - Translation Unit Analysis Command

## Overview
The `maestro tu` command provides Translation Unit analysis and indexing capabilities for multiple programming languages. It enables AST-based analysis, refactoring, and code completion.

## Subcommands

### `maestro tu build`
Builds translation units for source files with caching support.

**Usage:**
```
maestro tu build [PATH] [OPTIONS]
```

**Options:**
- `--force` - Force rebuild (ignore cache)
- `--verbose, -v` - Show detailed progress
- `--output, -o` - Output directory for TU (default: .maestro/tu/cache)
- `--threads` - Parallel parsing threads (default: CPU count)
- `--lang` - Language: cpp, java, kotlin (auto-detect if not specified)
- `--compile-flags` - Compile flags for C/C++ parsing

**Implementation:**
- Located in: `maestro/commands/tu.py` (handle_tu_build_command)
- Uses TUBuilder from `maestro/tu/tu_builder.py`
- Supports caching via `maestro/tu/cache.py`
- Language-specific parsers: ClangParser (C++), JavaParser, KotlinParser, PythonParser

### `maestro tu query`
Queries symbols in translation unit index.

**Usage:**
```
maestro tu query [PATH] [OPTIONS]
```

**Options:**
- `--symbol` - Symbol name to search
- `--file` - Limit search to file
- `--kind` - Filter by kind (function, class, etc.)
- `--json` - JSON output

**Implementation:**
- Located in: `maestro/commands/tu.py` (handle_tu_query_command)
- Uses SymbolIndex from `maestro/tu/symbol_index.py`
- Stores index in `.maestro/tu/analysis/symbols.db`

### `maestro tu complete`
Provides auto-completion at a specific location in a file.

**Usage:**
```
maestro tu complete [PATH] [OPTIONS]
```

**Options:**
- `--file` - Source file (required)
- `--line` - Line number (1-based, required)
- `--column` - Column number (0-based, default: 0)
- `--json` - JSON output

**Implementation:**
- Located in: `maestro/commands/tu.py` (handle_tu_complete_command)
- Uses CompletionProvider from `maestro/tu/completion.py`
- Integrates with SymbolIndex for symbol resolution

### `maestro tu references`
Finds all references to a specific symbol.

**Usage:**
```
maestro tu references [PATH] [OPTIONS]
```

**Options:**
- `--symbol` - Symbol name (required)
- `--file` - Symbol definition file (required)
- `--line` - Symbol definition line (required)
- `--json` - JSON output

**Implementation:**
- Located in: `maestro/commands/tu.py` (handle_tu_references_command)
- Uses SymbolIndex to find references
- Stores index in `.maestro/tu/analysis/symbols.db`

### `maestro tu transform`
Transforms code to follow specific conventions (e.g., U++ style).

**Usage:**
```
maestro tu transform PACKAGE --to TARGET [OPTIONS]
```

**Options:**
- `--to` - Target convention (required, e.g., upp)
- `--output, -o` - Output directory (default: .maestro/tu/transform)
- `--lang` - Language: cpp, java, kotlin (auto-detect if not specified)
- `--compile-flags` - Compile flags for C/C++ parsing

**Implementation:**
- Located in: `maestro/commands/tu.py` (handle_tu_transform_command)
- Uses UppConventionTransformer from `maestro/tu/transformers.py`
- Implements dependency graph building and topological sorting

### `maestro tu lsp`
Starts Language Server Protocol server for IDE integration.

**Usage:**
```
maestro tu lsp [OPTIONS]
```

**Options:**
- `--port` - TCP port (default: stdio)
- `--log` - Log file path

**Implementation:**
- Located in: `maestro/commands/tu.py` (handle_tu_lsp_command)
- Uses MaestroLSPServer from `maestro/tu/lsp_server.py`
- Provides completion, definition, and reference lookups

### `maestro tu print-ast`
Prints the AST representation for a source file.

**Usage:**
```
maestro tu print-ast FILE [OPTIONS]
```

**Options:**
- `--output, -o` - Output file (default: stdout)
- `--no-types` - Hide type information
- `--no-locations` - Hide source locations
- `--no-values` - Hide constant values
- `--no-modifiers` - Hide modifiers (public, static, etc.)
- `--max-depth` - Maximum tree depth to print
- `--compile-flags` - Compile flags for C/C++ parsing
- `--verbose, -v` - Show detailed error messages

**Implementation:**
- Located in: `maestro/commands/tu.py` (handle_tu_print_ast_command)
- Uses ASTPrinter from `maestro/tu/ast_printer.py`

### `maestro tu cache`
Manages the TU cache for cleaning and statistics.

**Usage:**
```
maestro tu cache [SUBCOMMAND]
```

**Subcommands:**
- `clear [PATH]` - Clear TU cache for package
- `stats` - Show cache statistics

**Implementation:**
- Located in: `maestro/commands/tu.py` (handle_tu_cache commands)
- Uses cache from `maestro/tu/cache.py`

### `maestro tu draft`
Creates draft classes and functions for a translation unit.

**Usage:**
```
maestro tu draft [PATH] [OPTIONS]
```

**Options:**
- `--class` - Draft class name to create
- `--function` - Draft function name to create
- `--lang` - Language: cpp, java, kotlin, python (auto-detect if not specified)
- `--output, -o` - Output directory (default: .maestro/tu/draft)
- `--link-phase` - Phase ID to link the draft to
- `--link-task` - Task ID to link the draft to
- `--prompt, -p` - AI prompt to help generate the draft implementation
- `--verbose, -v` - Show detailed progress

**Implementation:**
- Located in: `maestro/commands/tu.py` (handle_tu_draft_command)
- Uses CodeGenerator from `maestro/tu/code_generator.py`

## Implementation Details

### Core Components
- **TUBuilder** (`maestro/tu/tu_builder.py`): Builds translation units with caching
- **SymbolIndex** (`maestro/tu/symbol_index.py`): Persistent symbol index using SQLite
- **SymbolResolver** (`maestro/tu/symbol_resolver.py`): Resolves cross-file symbol references
- **CompletionProvider** (`maestro/tu/completion.py`): Provides auto-completion capabilities
- **Language Parsers**: ClangParser (C++), JavaParser, KotlinParser, PythonParser
- **Transformers**: UppConventionTransformer and other AST transformers

### Configuration Selection
The TU commands use build configurations identified by `maestro repo conf` to determine appropriate compile flags and include paths for AST generation. This ensures accurate parsing that matches the actual build environment.

### Storage Locations
- AST cache: `.maestro/tu/cache/`
- Symbol index: `.maestro/tu/analysis/symbols.db`
- Transform results: `.maestro/tu/transform/`
- Draft files: `.maestro/tu/draft/`
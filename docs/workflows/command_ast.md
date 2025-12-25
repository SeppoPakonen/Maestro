# maestro ast - AST Operations Command (Conceptual)

## Overview
**Note:** Maestro does not currently have a dedicated `maestro ast` command. AST operations are accessed through the `maestro tu` (Translation Unit) command.

The AST functionality is implemented through the Translation Unit system, which provides AST generation, indexing, and manipulation capabilities for multiple programming languages.

## Relationship to TU Commands
All AST operations are currently available through the `maestro tu` command hierarchy. This design emphasizes the translation unit concept where ASTs are generated and processed per unit of compilation.

## Available AST Operations via `maestro tu`

### AST Generation and Analysis
- `maestro tu build` - Generate ASTs for source files with caching
- `maestro tu print-ast` - Print AST representation for a file
- `maestro tu query` - Query symbols in the AST index

### AST-Guided Operations
- `maestro tu complete` - AST-based auto-completion
- `maestro tu references` - Find all references to a symbol
- `maestro tu transform` - AST-driven code transformation

## Core AST Components

### AST Node Structure
Located in `maestro/tu/ast_nodes.py`, the AST node structure provides:
- Generic AST node representation
- Source location tracking
- Symbol information storage
- Child node relationships

### AST Parser Base
Located in `maestro/tu/parser_base.py`, providing:
- Base interface for language-specific parsers
- Common parsing functionality
- Error handling framework

### Language-Specific Parsers
- **ClangParser** (`maestro/tu/clang_parser.py`) - For C/C++ AST generation
- **JavaParser** (`maestro/tu/java_parser.py`) - For Java AST generation
- **KotlinParser** (`maestro/tu/kotlin_parser.py`) - For Kotlin AST generation
- **PythonParser** (`maestro/tu/python_parser.py`) - For Python AST generation

## AST Storage and Indexing

### Symbol Index
Located in `maestro/tu/symbol_index.py`, provides:
- Persistent symbol index using SQLite
- Definition and reference tracking
- Location-based queries
- Cross-reference capabilities

### Caching System
Located in `maestro/tu/cache.py`, providing:
- AST caching with file hash verification
- Metadata storage for rebuild decisions
- Compressed storage options

## AST Transformation

### Transformers
Located in `maestro/tu/transformers.py`, including:
- Base ASTTransformer class
- UppConventionTransformer for U++ style enforcement
- CompositeTransformer for multiple transformations
- Dependency graph building for proper declaration ordering

## AST-Driven Features

### Auto-Completion
The completion system in `maestro/tu/completion.py` provides:
- Context-aware symbol completion
- Scope-aware visibility rules
- Priority-based ranking (same-file symbols first)

### Language Server Protocol
The LSP server in `maestro/tu/lsp_server.py` integrates AST functionality for:
- Real-time completion suggestions
- Go-to-definition functionality
- Find-all-references capability
- Document symbol information

## Implementation Notes

The AST system is designed to work with the repository's build configuration system (`maestro repo conf`) to ensure that AST generation uses the same flags and includes as the actual build process, providing accurate analysis results.
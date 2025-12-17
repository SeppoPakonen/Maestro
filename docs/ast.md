# Translation Unit (TU) / AST Integration Roadmap

## Executive Summary

This document outlines the implementation of Translation Unit (TU) and Abstract Syntax Tree (AST) generation for Maestro, enabling advanced code analysis, auto-completion, code transformation, and convention enforcement across multiple build systems.

**Vision**: `maestro tu` becomes a universal AST generation and analysis system that can parse entire codebases, maintain incremental compilation tracking, and provide rich semantic analysis for IDE features, code transformation, and convention enforcement.

**Key Use Cases**:
1. **Auto-completion**: Context-aware code completion based on visible symbols at cursor location
2. **Code transformation**: Convert between coding conventions (e.g., standard C++ to U++ conventions)
3. **Order fixing**: Automatically reorder code to satisfy dependency requirements
4. **AI-assisted editing**: Provide AST context to AI for better code understanding
5. **Build system integration**: Share AST data between `maestro repo conf`, `maestro build`, and AI workflows

## Strategic Context

### Relationship to Existing Work

The TU/AST system builds on and integrates with:

1. **`maestro repo resolve`** (docs/todo.md): Package and dependency detection
   - TU/AST extends this by parsing the actual source code within packages
   - Uses the dependency graph to determine compilation order

2. **`maestro make` (umk integration)** (docs/umk.md): Universal build system
   - TU/AST shares the compilation pipeline (finding sources, resolving includes)
   - Uses build system metadata to configure parsers
   - The difference: `make` produces executables, `tu` produces AST

3. **`maestro repo <pkg> conf`**: Build configuration
   - TU generation requires similar configuration (compiler flags, include paths, defines)
   - Reuses the same configuration infrastructure

4. **`maestro build` (AI-assisted builds)**: Intelligent build fixing
   - TU/AST provides semantic context for understanding build failures
   - Enables AI to understand code structure when fixing compile errors

### Why TU/AST Matters

**For U++ Convention Enforcement**:
- U++ has strict conventions: one primary header per package, cpp files include only that header
- Standard C++ allows includes anywhere
- Converting projects to U++ convention requires knowing:
  - The correct order of declarations (from AST)
  - Which forward declarations are needed
  - What can be moved without breaking semantics

**For Auto-Completion**:
- Traditional tools (clangd, ccls) require full project compilation
- Maestro TU/AST integrates with build system knowledge
- Can provide completion even with partially compilable code

**For Code Transformation**:
- AST → transform → regenerate code
- Enables safe refactoring operations
- Supports dialect conversion (C++17 → C++20, standard C++ → U++)

**For AI Workflows**:
- Provides structured code context instead of raw text
- Enables semantic-aware code generation
- Improves AI understanding of code intent

## Architecture Overview

### Core Components

```
maestro tu/
├── ast/
│   ├── __init__.py
│   ├── parser.py           # Universal parser interface
│   ├── clang_parser.py     # libclang-based C/C++ parser
│   ├── java_parser.py      # Java AST parser (tree-sitter or JavaParser)
│   ├── kotlin_parser.py    # Kotlin AST parser (tree-sitter)
│   ├── nodes.py            # Universal AST node representation
│   ├── location.py         # Source location tracking
│   └── serializer.py       # AST serialization (JSON/binary)
├── tu/
│   ├── __init__.py
│   ├── builder.py          # Translation unit builder
│   ├── cache.py            # Incremental TU cache with file hashing
│   ├── context.py          # Compilation context (flags, includes, defines)
│   ├── resolver.py         # Symbol resolution and lookup
│   └── index.py            # TU index for fast queries
├── analysis/
│   ├── __init__.py
│   ├── completion.py       # Auto-completion engine
│   ├── navigation.py       # Go-to-definition, find-references
│   ├── diagnostics.py      # Semantic error detection
│   └── transform.py        # Code transformation utilities
├── lsp/
│   ├── __init__.py
│   └── server.py           # Language Server Protocol implementation
└── cli.py                  # maestro tu CLI implementation
```

### Data Flow

```
Source Files → Parser → AST Nodes → TU Builder → Translation Unit
                  ↓                        ↓
              File Hashes            Symbol Index
                  ↓                        ↓
            Incremental Cache    → Query Engine → Auto-completion
                                                 → Navigation
                                                 → Diagnostics
                                                 → Transformation
```

### Storage Structure

```
.maestro/tu/
├── cache/
│   ├── file_hashes.json         # SHA-256 hashes of source files
│   ├── ast/
│   │   ├── <hash>.ast           # Serialized AST per file
│   │   └── <hash>.meta          # AST metadata (symbols, dependencies)
│   └── tu/
│       ├── <package>.tu         # Complete translation unit
│       └── <package>.idx        # Symbol index
├── config/
│   ├── compile_flags.json       # Per-package compilation flags
│   └── include_paths.json       # Include path resolution
└── analysis/
    ├── symbols.db               # Symbol database (SQLite)
    └── references.db            # Cross-reference database
```

## Phase 1: Core AST Infrastructure

**Duration**: 3-4 weeks
**Dependencies**: None

### Objective

Build the foundation for parsing and representing ASTs across multiple languages.

### Tasks

#### 1.1: Universal AST Node Representation

Design a language-agnostic AST node structure:

```python
@dataclass
class ASTNode:
    """Universal AST node representation."""
    kind: str  # e.g., "function", "class", "variable", "expression"
    name: Optional[str]
    location: SourceLocation
    children: List['ASTNode']
    attributes: Dict[str, Any]  # Language-specific attributes

    def find_node_at(self, location: SourceLocation) -> Optional['ASTNode']:
        """Find AST node at given source location (for cursor queries)."""
        pass

    def get_visible_symbols(self, location: SourceLocation) -> List['Symbol']:
        """Get symbols visible at given location (for auto-completion)."""
        pass

@dataclass
class SourceLocation:
    """Source location with file and position."""
    file: str
    line: int
    column: int
    offset: int  # Byte offset in file

@dataclass
class Symbol:
    """Symbol (variable, function, class, etc.)."""
    name: str
    kind: str  # "function", "variable", "class", "namespace", etc.
    type: Optional[str]
    location: SourceLocation
    scope: Optional['Symbol']  # Parent scope
    visibility: str  # "public", "private", "protected"
```

Key design principles:
- **Language-agnostic core**: Common fields work for C++, Java, Kotlin, etc.
- **Extensible attributes**: Language-specific data in `attributes` dict
- **Location tracking**: Every node knows its source location
- **Hierarchical**: Nodes form a tree matching code structure

#### 1.2: libclang-based C/C++ Parser

Implement C/C++ parser using libclang:

```python
class ClangParser(Parser):
    def __init__(self, compile_flags: List[str], include_paths: List[str]):
        """Initialize clang parser with compilation context."""
        self.index = clang.cindex.Index.create()
        self.compile_flags = compile_flags
        self.include_paths = include_paths

    def parse_file(self, file_path: str) -> ASTNode:
        """Parse C/C++ file and return AST."""
        args = self.compile_flags + [f'-I{p}' for p in self.include_paths]
        tu = self.index.parse(file_path, args=args)

        # Convert clang AST to universal AST
        return self._convert_cursor(tu.cursor)

    def _convert_cursor(self, cursor) -> ASTNode:
        """Convert clang cursor to universal AST node."""
        # Map clang CursorKind to our node kinds
        # Recursively process children
        pass
```

Features:
- Use libclang Python bindings
- Support C++17/C++20 (configurable)
- Handle preprocessor directives
- Track include dependencies

#### 1.3: Java/Kotlin Parser Integration

Implement parsers for Gradle projects:

```python
class JavaParser(Parser):
    def __init__(self):
        """Initialize Java parser (using tree-sitter or JavaParser)."""
        # Option 1: tree-sitter (fast, incremental)
        # Option 2: JavaParser library (full semantic analysis)
        pass

    def parse_file(self, file_path: str) -> ASTNode:
        """Parse Java file and return AST."""
        pass

class KotlinParser(Parser):
    def __init__(self):
        """Initialize Kotlin parser (using tree-sitter or kotlin-compiler)."""
        pass

    def parse_file(self, file_path: str) -> ASTNode:
        """Parse Kotlin file and return AST."""
        pass
```

Options for Java parsing:
1. **tree-sitter**: Fast, incremental, good for syntax
2. **JavaParser**: Full semantic analysis, slower
3. **Eclipse JDT**: Heavy but comprehensive

Options for Kotlin parsing:
1. **tree-sitter**: Fast, good syntax
2. **kotlin-compiler-embeddable**: Full semantics, heavy

#### 1.4: AST Serialization

Implement efficient AST storage:

```python
class ASTSerializer:
    def serialize(self, ast: ASTNode, output_path: str):
        """Serialize AST to disk."""
        # Option 1: JSON (human-readable, slower)
        # Option 2: MessagePack (compact, faster)
        # Option 3: Protocol Buffers (efficient, typed)
        pass

    def deserialize(self, input_path: str) -> ASTNode:
        """Deserialize AST from disk."""
        pass
```

Format considerations:
- **JSON**: Easy debugging, human-readable
- **MessagePack**: 10x smaller than JSON, fast
- **Protocol Buffers**: Typed schema, version-safe

### Deliverables

- Universal AST node representation
- C/C++ parser using libclang
- Java/Kotlin parsers (initial)
- AST serialization/deserialization
- Unit tests for parsing sample files

### Test Criteria

- Parse simple C++ file with classes and functions
- Parse Java file from Gradle project
- Round-trip: parse → serialize → deserialize → verify equality
- Extract all symbols from parsed AST

## Phase 2: Incremental TU Builder with File Hashing

**Duration**: 3-4 weeks
**Dependencies**: Phase 1

### Objective

Build translation units efficiently with incremental compilation tracking.

### Tasks

#### 2.1: File Hash Tracking

Implement SHA-256-based file change detection:

```python
class FileHasher:
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self.hash_file = os.path.join(cache_dir, 'file_hashes.json')
        self.hashes = self._load_hashes()

    def get_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of file content."""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def has_changed(self, file_path: str) -> bool:
        """Check if file has changed since last parse."""
        current_hash = self.get_hash(file_path)
        cached_hash = self.hashes.get(file_path)
        return current_hash != cached_hash

    def update_hash(self, file_path: str):
        """Update cached hash for file."""
        self.hashes[file_path] = self.get_hash(file_path)
        self._save_hashes()
```

#### 2.2: AST Cache Management

Implement cache for parsed ASTs:

```python
class ASTCache:
    def __init__(self, cache_dir: str):
        self.cache_dir = os.path.join(cache_dir, 'ast')
        self.hasher = FileHasher(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cached_ast(self, file_path: str) -> Optional[ASTNode]:
        """Retrieve cached AST if file unchanged."""
        if not self.hasher.has_changed(file_path):
            hash_val = self.hasher.get_hash(file_path)
            cache_path = os.path.join(self.cache_dir, f'{hash_val}.ast')
            if os.path.exists(cache_path):
                return ASTSerializer().deserialize(cache_path)
        return None

    def cache_ast(self, file_path: str, ast: ASTNode):
        """Cache parsed AST."""
        hash_val = self.hasher.get_hash(file_path)
        cache_path = os.path.join(self.cache_dir, f'{hash_val}.ast')
        ASTSerializer().serialize(ast, cache_path)
        self.hasher.update_hash(file_path)
```

#### 2.3: Translation Unit Builder

Build complete TU from package files:

```python
class TUBuilder:
    def __init__(self, package: PackageInfo, config: BuildConfig):
        self.package = package
        self.config = config
        self.parser = self._create_parser()
        self.cache = ASTCache('.maestro/tu/cache')
        self.file_asts: Dict[str, ASTNode] = {}

    def build_tu(self) -> TranslationUnit:
        """Build complete translation unit for package."""
        # 1. Parse all source files (using cache)
        for file_path in self.package.files:
            if file_path.endswith(self._source_extensions()):
                ast = self._parse_with_cache(file_path)
                self.file_asts[file_path] = ast

        # 2. Build symbol table
        symbol_table = self._build_symbol_table()

        # 3. Resolve cross-file references
        self._resolve_references()

        # 4. Create translation unit
        tu = TranslationUnit(
            package=self.package.name,
            file_asts=self.file_asts,
            symbols=symbol_table,
            dependencies=self._extract_dependencies()
        )

        # 5. Cache TU
        self._cache_tu(tu)

        return tu

    def _parse_with_cache(self, file_path: str) -> ASTNode:
        """Parse file, using cache if unchanged."""
        cached = self.cache.get_cached_ast(file_path)
        if cached:
            return cached

        # Parse fresh
        ast = self.parser.parse_file(file_path)
        self.cache.cache_ast(file_path, ast)
        return ast
```

#### 2.4: Dependency Tracking

Track which AST nodes depend on which files:

```python
@dataclass
class ASTDependency:
    """Track file dependencies in AST."""
    file: str  # Source file
    depends_on: List[str]  # Files this file depends on (includes, imports)
    symbols_used: List[str]  # External symbols referenced
    symbols_defined: List[str]  # Symbols defined in this file

class DependencyTracker:
    def extract_dependencies(self, ast: ASTNode, file_path: str) -> ASTDependency:
        """Extract dependency information from AST."""
        depends_on = []

        # Find all includes/imports
        for node in ast.walk():
            if node.kind == 'include':
                include_file = self._resolve_include(node.attributes['path'])
                depends_on.append(include_file)
            elif node.kind == 'import':
                import_file = self._resolve_import(node.attributes['module'])
                depends_on.append(import_file)

        # Extract symbols
        symbols_defined = self._extract_definitions(ast)
        symbols_used = self._extract_usages(ast)

        return ASTDependency(
            file=file_path,
            depends_on=depends_on,
            symbols_used=symbols_used,
            symbols_defined=symbols_defined
        )
```

### Deliverables

- File hash tracking system
- AST cache management
- Translation unit builder
- Dependency tracking
- Incremental rebuild (only re-parse changed files)

### Test Criteria

- Build TU for simple package (3-5 files)
- Modify one file, rebuild TU (only that file re-parsed)
- Verify cached ASTs are reused correctly
- Extract correct dependency graph

## Phase 3: Symbol Resolution and Indexing

**Duration**: 3-4 weeks
**Dependencies**: Phase 2

### Objective

Build symbol table and index for fast queries.

### Tasks

#### 3.1: Symbol Table Construction

Build comprehensive symbol table:

```python
class SymbolTable:
    def __init__(self):
        self.symbols: Dict[str, List[Symbol]] = {}  # name -> symbols (overloads)
        self.scopes: Dict[SourceLocation, Scope] = {}  # location -> scope

    def add_symbol(self, symbol: Symbol):
        """Add symbol to table."""
        if symbol.name not in self.symbols:
            self.symbols[symbol.name] = []
        self.symbols[symbol.name].append(symbol)

    def lookup(self, name: str, location: SourceLocation) -> List[Symbol]:
        """Lookup symbol by name at given location (respects scope)."""
        scope = self._find_scope(location)
        candidates = []

        # Search current scope and parent scopes
        while scope:
            for sym in self.symbols.get(name, []):
                if self._is_visible(sym, scope):
                    candidates.append(sym)
            scope = scope.parent

        return candidates

    def get_visible_symbols(self, location: SourceLocation) -> List[Symbol]:
        """Get all symbols visible at location (for auto-completion)."""
        scope = self._find_scope(location)
        visible = []

        # Collect all symbols from current and parent scopes
        while scope:
            visible.extend(scope.symbols)
            scope = scope.parent

        return visible
```

#### 3.2: Cross-File Symbol Resolution

Resolve symbols across files in TU:

```python
class SymbolResolver:
    def __init__(self, tu: TranslationUnit):
        self.tu = tu
        self.symbol_table = SymbolTable()

    def resolve(self):
        """Resolve all symbols in translation unit."""
        # Phase 1: Collect all definitions
        for file_path, ast in self.tu.file_asts.items():
            self._collect_definitions(ast, file_path)

        # Phase 2: Resolve all references
        for file_path, ast in self.tu.file_asts.items():
            self._resolve_references(ast, file_path)

    def _collect_definitions(self, ast: ASTNode, file_path: str):
        """Collect all symbol definitions from AST."""
        for node in ast.walk():
            if node.kind in ['function', 'class', 'variable', 'typedef']:
                symbol = Symbol(
                    name=node.name,
                    kind=node.kind,
                    type=node.attributes.get('type'),
                    location=node.location,
                    scope=self._current_scope(node),
                    visibility=node.attributes.get('visibility', 'public')
                )
                self.symbol_table.add_symbol(symbol)

    def _resolve_references(self, ast: ASTNode, file_path: str):
        """Resolve all symbol references in AST."""
        for node in ast.walk():
            if node.kind in ['identifier', 'call', 'member_access']:
                # Lookup symbol at this location
                symbols = self.symbol_table.lookup(node.name, node.location)
                if symbols:
                    # Store resolved symbol in node
                    node.attributes['resolved_symbol'] = symbols[0]
                else:
                    # Unresolved symbol (error or external)
                    node.attributes['resolved_symbol'] = None
```

#### 3.3: Symbol Index (SQLite)

Store symbols in database for fast queries:

```python
class SymbolIndex:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self._create_schema()

    def _create_schema(self):
        """Create symbol database schema."""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                type TEXT,
                file TEXT NOT NULL,
                line INTEGER NOT NULL,
                column INTEGER NOT NULL,
                scope TEXT,
                visibility TEXT,
                UNIQUE(name, file, line, column)
            )
        ''')

        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS references (
                id INTEGER PRIMARY KEY,
                symbol_id INTEGER NOT NULL,
                file TEXT NOT NULL,
                line INTEGER NOT NULL,
                column INTEGER NOT NULL,
                FOREIGN KEY(symbol_id) REFERENCES symbols(id)
            )
        ''')

        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_name ON symbols(name)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_file ON symbols(file)')
        self.conn.commit()

    def add_symbol(self, symbol: Symbol):
        """Add symbol to index."""
        self.conn.execute('''
            INSERT OR REPLACE INTO symbols
            (name, kind, type, file, line, column, scope, visibility)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol.name, symbol.kind, symbol.type,
            symbol.location.file, symbol.location.line, symbol.location.column,
            symbol.scope.name if symbol.scope else None,
            symbol.visibility
        ))
        self.conn.commit()

    def find_symbols(self, name: str) -> List[Symbol]:
        """Find all symbols with given name."""
        cursor = self.conn.execute('''
            SELECT name, kind, type, file, line, column, scope, visibility
            FROM symbols WHERE name = ?
        ''', (name,))

        symbols = []
        for row in cursor:
            symbols.append(Symbol(
                name=row[0],
                kind=row[1],
                type=row[2],
                location=SourceLocation(file=row[3], line=row[4], column=row[5]),
                scope=None,  # TODO: resolve scope
                visibility=row[7]
            ))
        return symbols

    def find_references(self, symbol: Symbol) -> List[SourceLocation]:
        """Find all references to symbol."""
        # Query references table
        pass
```

### Deliverables

- Symbol table construction
- Cross-file symbol resolution
- SQLite-based symbol index
- Symbol lookup and reference finding

### Test Criteria

- Build symbol table for multi-file package
- Lookup symbol definition by name
- Find all references to symbol
- Get visible symbols at cursor position

## Phase 4: Auto-Completion Engine

**Duration**: 2-3 weeks
**Dependencies**: Phase 3

### Objective

Implement context-aware auto-completion.

### Tasks

#### 4.1: Completion Provider

Implement completion at cursor location:

```python
class CompletionProvider:
    def __init__(self, tu: TranslationUnit, symbol_table: SymbolTable):
        self.tu = tu
        self.symbol_table = symbol_table

    def complete_at(self, file: str, line: int, column: int) -> List[CompletionItem]:
        """Provide completion items at cursor location."""
        location = SourceLocation(file, line, column)

        # Find AST node at location
        ast = self.tu.file_asts.get(file)
        if not ast:
            return []

        node = ast.find_node_at(location)
        if not node:
            return []

        # Determine completion context
        context = self._determine_context(node, location)

        # Get appropriate completions
        if context == 'member_access':
            return self._complete_members(node)
        elif context == 'scope_resolution':
            return self._complete_scope(node)
        else:
            return self._complete_symbols(location)

    def _complete_symbols(self, location: SourceLocation) -> List[CompletionItem]:
        """Complete visible symbols at location."""
        symbols = self.symbol_table.get_visible_symbols(location)
        items = []

        for sym in symbols:
            items.append(CompletionItem(
                label=sym.name,
                kind=sym.kind,
                type=sym.type,
                detail=self._format_symbol(sym),
                documentation=self._get_documentation(sym)
            ))

        return items

@dataclass
class CompletionItem:
    """Auto-completion item."""
    label: str  # What to display
    kind: str  # "function", "variable", "class", etc.
    type: Optional[str]  # Type signature
    detail: str  # Additional info
    documentation: Optional[str]  # Full documentation
```

#### 4.2: LSP Integration

Implement Language Server Protocol:

```python
class MaestroLSPServer:
    def __init__(self, tu_manager: TUManager):
        self.tu_manager = tu_manager
        self.completion_provider = CompletionProvider(...)

    def handle_completion(self, params):
        """Handle textDocument/completion request."""
        file = params['textDocument']['uri']
        line = params['position']['line']
        column = params['position']['character']

        completions = self.completion_provider.complete_at(file, line, column)

        # Convert to LSP format
        return {
            'isIncomplete': False,
            'items': [self._to_lsp_item(c) for c in completions]
        }

    def handle_definition(self, params):
        """Handle textDocument/definition request."""
        # Go to definition
        pass

    def handle_references(self, params):
        """Handle textDocument/references request."""
        # Find all references
        pass
```

### Deliverables

- Completion provider with context awareness
- LSP server implementation
- Integration with editors (VS Code, Vim, Emacs)

### Test Criteria

- Provide completions at various locations
- Complete after `.` (member access)
- Complete after `::` (scope resolution)
- Complete local variables in function

## Phase 5: Integration with Build System and CLI

**Duration**: 3-4 weeks
**Dependencies**: Phases 2-4

### Objective

Integrate TU/AST with existing Maestro workflows.

### Tasks

#### 5.1: Build Configuration Integration

Reuse build configuration for TU generation:

```python
class TUConfigBuilder:
    def __init__(self, package: PackageInfo, repo_dir: str):
        self.package = package
        self.repo_dir = repo_dir

    def get_compile_context(self) -> CompileContext:
        """Extract compile context from package metadata."""
        if self.package.build_system == 'gradle':
            return self._extract_gradle_context()
        elif self.package.build_system == 'cmake':
            return self._extract_cmake_context()
        elif self.package.build_system == 'upp':
            return self._extract_upp_context()
        else:
            raise ValueError(f"Unknown build system: {self.package.build_system}")

    def _extract_gradle_context(self) -> CompileContext:
        """Extract compile flags from Gradle."""
        # Read build.gradle to get:
        # - Source compatibility (Java version)
        # - Kotlin version
        # - Dependencies (for classpath)
        # - Compiler options

        build_file = self.package.metadata.get('build_file')
        # Parse build.gradle.kts
        # Extract sourceCompatibility, kotlinOptions, etc.

        return CompileContext(
            language='java',  # or 'kotlin'
            standard='11',  # Java 11
            include_paths=[],  # Not applicable for Java
            defines=[],
            flags=['-encoding', 'UTF-8']
        )

    def _extract_upp_context(self) -> CompileContext:
        """Extract compile flags from U++ package."""
        # Read .upp file
        # Extract flags, mainconfig
        # Resolve includes from uses

        return CompileContext(
            language='c++',
            standard='c++17',
            include_paths=self._resolve_upp_includes(),
            defines=self._extract_upp_defines(),
            flags=['-Wall', '-Wextra']
        )

@dataclass
class CompileContext:
    """Compilation context for parsing."""
    language: str  # 'c++', 'java', 'kotlin'
    standard: str  # 'c++17', '11' (Java), etc.
    include_paths: List[str]
    defines: List[str]
    flags: List[str]
```

#### 5.2: `maestro tu` CLI Implementation

Implement CLI commands:

```
maestro tu build [PACKAGE]
    Build translation unit for package

    Options:
        --force             Force rebuild (ignore cache)
        --verbose           Show detailed progress
        --output PATH       Output directory for TU
        --threads N         Parallel parsing threads

maestro tu info [PACKAGE]
    Show translation unit information

    Output:
        - Number of files parsed
        - Number of symbols defined
        - Number of symbols referenced
        - Parse time, cache hit rate

maestro tu query [PACKAGE] --symbol NAME
    Query symbol in translation unit

    Options:
        --symbol NAME       Symbol name to search
        --file PATH         Limit search to file
        --kind KIND         Filter by kind (function, class, etc.)
        --json              JSON output

maestro tu complete [PACKAGE] --file PATH --line N --column N
    Get auto-completion at location

    Options:
        --file PATH         Source file
        --line N            Line number (1-based)
        --column N          Column number (0-based)
        --json              JSON output

maestro tu references [PACKAGE] --symbol NAME
    Find all references to symbol

    Options:
        --symbol NAME       Symbol name
        --file PATH         Symbol definition file
        --line N            Symbol definition line

maestro tu lsp
    Start Language Server Protocol server

    Options:
        --port N            TCP port (default: stdio)
        --log PATH          Log file path

maestro tu cache clear [PACKAGE]
    Clear TU cache for package

maestro tu cache stats
    Show cache statistics (size, hit rate)
```

#### 5.3: Integration with `maestro repo conf`

Share configuration between TU and build:

```python
class RepoConfigurator:
    def configure_package(self, package: PackageInfo):
        """Configure package for building and TU generation."""
        # 1. Detect build system
        # 2. Extract compile flags
        # 3. Store in .maestro/tu/config/

        config = TUConfigBuilder(package, self.repo_dir).get_compile_context()

        # Save for both build and TU
        config_path = f'.maestro/tu/config/{package.name}.json'
        with open(config_path, 'w') as f:
            json.dump(asdict(config), f, indent=2)
```

#### 5.4: Integration with `maestro build` (AI workflow)

Provide AST context to AI:

```python
class AIBuildFixer:
    def __init__(self, tu_manager: TUManager):
        self.tu_manager = tu_manager

    def fix_build_error(self, package: PackageInfo, error: CompileError):
        """Fix build error using AST context."""
        # 1. Get TU for package
        tu = self.tu_manager.get_tu(package.name)

        # 2. Find AST node at error location
        ast = tu.file_asts.get(error.file)
        node = ast.find_node_at(error.location)

        # 3. Get surrounding context
        context = self._extract_context(node, lines=10)

        # 4. Get visible symbols at error location
        symbols = tu.symbol_table.get_visible_symbols(error.location)

        # 5. Send to AI with rich context
        prompt = f"""
        Build error: {error.message}

        Location: {error.file}:{error.location.line}

        AST context:
        {self._format_ast(node)}

        Visible symbols:
        {self._format_symbols(symbols)}

        Source context:
        {context}

        How should this be fixed?
        """

        # AI processes with full semantic understanding
        return self._send_to_ai(prompt)
```

### Deliverables

- `maestro tu` CLI with all subcommands
- Integration with build configuration
- Integration with AI build fixing workflow
- Documentation and examples

### Test Criteria

- `maestro tu build` works for Gradle project
- `maestro tu complete` provides correct completions
- `maestro tu query` finds symbols
- `maestro tu lsp` works with VS Code

## Phase 6: Code Transformation and Convention Enforcement

**Duration**: 3-4 weeks
**Dependencies**: Phases 3-5

### Objective

Implement code transformation and U++ convention enforcement.

### Tasks

#### 6.1: AST Transformation Framework

Build framework for AST transformations:

```python
class ASTTransformer:
    def __init__(self, tu: TranslationUnit):
        self.tu = tu

    def transform(self, transformation: Transformation) -> TranslationUnit:
        """Apply transformation to TU."""
        new_tu = copy.deepcopy(self.tu)

        for file_path, ast in new_tu.file_asts.items():
            self._transform_ast(ast, transformation)

        return new_tu

    def _transform_ast(self, ast: ASTNode, transformation: Transformation):
        """Recursively transform AST."""
        for node in ast.walk():
            if transformation.matches(node):
                transformation.apply(node)

class Transformation(ABC):
    @abstractmethod
    def matches(self, node: ASTNode) -> bool:
        """Check if transformation applies to node."""
        pass

    @abstractmethod
    def apply(self, node: ASTNode):
        """Apply transformation to node."""
        pass
```

#### 6.2: U++ Convention Enforcer

Implement U++ convention transformation:

```python
class UppConventionTransformer(Transformation):
    """Transform code to U++ conventions."""

    def transform_package(self, package: PackageInfo, tu: TranslationUnit):
        """
        Transform package to U++ conventions:
        1. Create primary header (PackageName.h)
        2. Move all declarations to primary header in correct order
        3. Update .cpp files to only include primary header
        4. Add forward declarations where needed
        """
        # 1. Analyze dependencies from TU
        dep_graph = self._build_dependency_graph(tu)

        # 2. Compute correct order using topological sort
        ordered_declarations = self._topological_sort(dep_graph)

        # 3. Generate primary header
        primary_header = self._generate_primary_header(
            package.name,
            ordered_declarations,
            tu
        )

        # 4. Update .cpp files
        for cpp_file in self._find_cpp_files(package):
            self._update_cpp_file(cpp_file, package.name)

        return primary_header

    def _build_dependency_graph(self, tu: TranslationUnit) -> DependencyGraph:
        """Build dependency graph from AST."""
        graph = DependencyGraph()

        for file_path, ast in tu.file_asts.items():
            for node in ast.walk():
                if node.kind in ['class', 'function', 'typedef']:
                    # Add node to graph
                    graph.add_node(node.name)

                    # Find dependencies (types used in this declaration)
                    deps = self._find_dependencies(node, tu)
                    for dep in deps:
                        graph.add_edge(node.name, dep)

        return graph

    def _topological_sort(self, graph: DependencyGraph) -> List[str]:
        """Compute correct declaration order."""
        # Standard topological sort
        # Detects cycles (circular dependencies)
        pass

    def _generate_primary_header(
        self,
        package_name: str,
        ordered_declarations: List[str],
        tu: TranslationUnit
    ) -> str:
        """Generate primary header with correct order."""
        header = f"#ifndef _{package_name}_h_\n"
        header += f"#define _{package_name}_h_\n\n"

        # Add includes from uses
        header += self._generate_includes(tu)

        # Add forward declarations
        header += self._generate_forward_declarations(ordered_declarations, tu)

        # Add declarations in correct order
        for decl_name in ordered_declarations:
            decl_node = self._find_declaration(decl_name, tu)
            header += self._generate_declaration(decl_node)

        header += f"\n#endif\n"
        return header
```

#### 6.3: Code Generation from AST

Generate source code from transformed AST:

```python
class CodeGenerator:
    def __init__(self, language: str):
        self.language = language

    def generate(self, ast: ASTNode) -> str:
        """Generate source code from AST."""
        if self.language == 'c++':
            return self._generate_cpp(ast)
        elif self.language == 'java':
            return self._generate_java(ast)
        else:
            raise ValueError(f"Unknown language: {self.language}")

    def _generate_cpp(self, ast: ASTNode) -> str:
        """Generate C++ code."""
        code = []

        for node in ast.children:
            if node.kind == 'class':
                code.append(self._generate_class(node))
            elif node.kind == 'function':
                code.append(self._generate_function(node))
            # ... etc

        return '\n\n'.join(code)

    def _generate_class(self, node: ASTNode) -> str:
        """Generate class declaration."""
        code = f"class {node.name}"

        if node.attributes.get('bases'):
            bases = ', '.join(node.attributes['bases'])
            code += f" : {bases}"

        code += " {\n"

        # Generate members
        for child in node.children:
            code += f"    {self._generate_node(child)}\n"

        code += "};"
        return code
```

### Deliverables

- AST transformation framework
- U++ convention enforcer
- Code generator from AST
- CLI: `maestro tu transform --to-upp PACKAGE`

### Test Criteria

- Transform simple C++ project to U++ conventions
- Verify generated code compiles
- Verify declaration order is correct
- Verify forward declarations added where needed

## Technical Considerations

### 1. Parser Choice

**C/C++**:
- **libclang**: Mature, maintained by LLVM project, full semantic analysis
- **tree-sitter**: Fast, incremental, good for syntax highlighting, weaker semantics
- **Recommendation**: libclang for full analysis, tree-sitter for fast queries

**Java**:
- **tree-sitter**: Fast syntax parsing
- **JavaParser**: Full semantic analysis, can resolve types
- **Eclipse JDT**: Heavy but comprehensive
- **Recommendation**: JavaParser for full analysis

**Kotlin**:
- **tree-sitter**: Fast syntax parsing
- **kotlin-compiler-embeddable**: Official parser, full semantics
- **Recommendation**: kotlin-compiler-embeddable for full analysis

### 2. Incremental Parsing

Use file hashing to avoid re-parsing:
- SHA-256 hash of file content
- Cache AST per file hash
- Only re-parse files with changed hash
- Invalidate dependent files when includes change

### 3. Parallel Parsing

Parse files in parallel for speed:
- Use Python multiprocessing
- One process per file
- Limit to CPU count
- Progress indicator for large projects

### 4. Memory Management

Large projects have large ASTs:
- Stream ASTs to disk (don't keep all in memory)
- Load on-demand for queries
- Use memory-mapped files for large ASTs
- Consider AST compression

### 5. Language Server Protocol

Implement LSP for editor integration:
- Standard protocol (VS Code, Vim, Emacs, etc.)
- Real-time completion and diagnostics
- Incremental updates (didChange)
- Background TU building

## Integration with Existing Features

### With `maestro repo resolve`

TU uses package detection:
1. `maestro repo resolve` finds packages
2. `maestro tu build` parses sources in packages
3. Uses dependency graph from `repo pkg tree`

### With `maestro make` (umk)

TU shares compilation context:
1. Both need compiler flags, include paths, defines
2. Both need to resolve dependencies
3. Different outputs: executables vs AST

### With `maestro build` (AI)

TU provides context to AI:
1. AI gets AST structure, not just text
2. AI understands visible symbols at error location
3. AI can suggest fixes with semantic understanding

## Success Metrics

1. **Performance**: Parse 10K line project in <10 seconds
2. **Cache hit rate**: >90% for unchanged files
3. **Completion accuracy**: >95% correct suggestions
4. **Memory usage**: <500MB for 100K line project
5. **Editor integration**: Works smoothly with VS Code

## Risks and Mitigations

### Risk 1: libclang Complexity

**Mitigation**:
- Start with simple C++ parsing
- Gradually add features (templates, preprocessor)
- Option to fallback to tree-sitter for fast queries

### Risk 2: Large Project Performance

**Mitigation**:
- Aggressive caching with file hashing
- Parallel parsing
- Stream ASTs to disk
- Lazy loading of ASTs

### Risk 3: Symbol Resolution Across Languages

**Mitigation**:
- Universal AST node format
- Language-specific resolvers
- Common symbol table interface

### Risk 4: U++ Convention Edge Cases

**Mitigation**:
- Start with simple cases
- Test on real U++ projects
- Document limitations
- Manual review of transformations

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Core AST Infrastructure | 3-4 weeks | None |
| Phase 2: Incremental TU Builder | 3-4 weeks | Phase 1 |
| Phase 3: Symbol Resolution | 3-4 weeks | Phase 2 |
| Phase 4: Auto-Completion | 2-3 weeks | Phase 3 |
| Phase 5: Integration | 3-4 weeks | Phases 2-4 |
| Phase 6: Code Transformation | 3-4 weeks | Phases 3-5 |

**Total Estimate**: 17-23 weeks (4-6 months)

**MVP**: Phases 1-3 (9-12 weeks)
- Parse C++ and Java/Kotlin
- Build TU with caching
- Symbol table and queries

**Extended MVP**: Phases 1-5 (14-19 weeks)
- Add auto-completion
- CLI integration
- LSP server

## Future Extensions

1. **Refactoring Tools**: Rename, extract method, inline, etc.
2. **Cross-Language Analysis**: Call graph across C++/Java/Kotlin
3. **Advanced Diagnostics**: Dead code detection, unused symbols
4. **Code Metrics**: Complexity, coupling, cohesion
5. **Documentation Generation**: Extract docs from AST
6. **Test Generation**: Generate tests from AST structure
7. **Diff-Aware Parsing**: Only parse changed functions
8. **Distributed TU Building**: Build TU on multiple machines

## Conclusion

The TU/AST integration provides Maestro with powerful code analysis capabilities that extend far beyond simple build system detection. By generating and caching ASTs with incremental rebuilding, Maestro can provide IDE-quality features like auto-completion, navigation, and semantic understanding while also enabling advanced use cases like code transformation and convention enforcement.

The phased approach ensures incremental value delivery, with the MVP providing basic AST parsing and caching, and later phases adding increasingly sophisticated features. Integration with existing Maestro workflows (`maestro repo`, `maestro make`, `maestro build`) ensures that TU/AST capabilities enhance rather than duplicate existing functionality.

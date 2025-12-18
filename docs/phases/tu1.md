# Phase TU1: Core AST Infrastructure 📋 **[Planned]**

**Reference**: `docs/ast.md` Phase 1
**Duration**: 3-4 weeks
**Dependencies**: None

**Objective**: Build foundation for parsing and representing ASTs across multiple languages.

## Tasks

- [ ] **TU1.1: Universal AST Node Representation**
  - [ ] Design language-agnostic AST node structure
  - [ ] Implement `ASTNode` dataclass with location tracking
  - [ ] Implement `SourceLocation` for file/line/column tracking
  - [ ] Implement `Symbol` dataclass for definitions/references

- [ ] **TU1.2: libclang-based C/C++ Parser**
  - [ ] Integrate libclang Python bindings
  - [ ] Implement `ClangParser` class
  - [ ] Convert clang AST to universal AST format
  - [ ] Handle preprocessor directives
  - [ ] Track include dependencies

- [ ] **TU1.3: Java/Kotlin Parser Integration**
  - [ ] Implement `JavaParser` using tree-sitter or JavaParser library
  - [ ] Implement `KotlinParser` using tree-sitter or kotlin-compiler
  - [ ] Support for Gradle projects

- [ ] **TU1.4: AST Serialization**
  - [ ] Design serialization format (JSON/MessagePack/Protobuf)
  - [ ] Implement `ASTSerializer` class
  - [ ] Support round-trip: parse → serialize → deserialize
  - [ ] Optimize for size and speed

## Deliverables:
- Universal AST node representation
- C/C++ parser using libclang
- Java/Kotlin parsers (initial)
- AST serialization/deserialization

## Test Repository:
- `~/Dev/RainbowGame/trash` (Gradle multi-module with Java/Kotlin)

## Test Criteria:
- Parse simple C++ file with classes and functions
- Parse Java file from Gradle project
- Round-trip serialization works correctly
- Extract all symbols from parsed AST
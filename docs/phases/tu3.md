# Phase TU3: Symbol Resolution and Indexing 📋 **[Planned]**

**Reference**: `docs/ast.md` Phase 3
**Duration**: 3-4 weeks
**Dependencies**: Phase TU2

**Objective**: Build symbol table and index for fast queries.

## Tasks

- [ ] **TU3.1: Symbol Table Construction**
  - [ ] Implement `SymbolTable` class
  - [ ] Support scoped symbol lookup
  - [ ] Handle overloaded symbols
  - [ ] Track symbol visibility (public/private/protected)

- [ ] **TU3.2: Cross-File Symbol Resolution**
  - [ ] Implement `SymbolResolver` class
  - [ ] Resolve symbols across files in TU
  - [ ] Handle forward declarations
  - [ ] Detect unresolved symbols

- [ ] **TU3.3: Symbol Index (SQLite)**
  - [ ] Create `.maestro/tu/analysis/symbols.db`
  - [ ] Implement `SymbolIndex` class
  - [ ] Store symbols in database for fast queries
  - [ ] Index by name, file, location
  - [ ] Support find-references queries

## Deliverables:
- Symbol table construction
- Cross-file symbol resolution
- SQLite-based symbol index
- Symbol lookup and reference finding

## Test Criteria:
- Build symbol table for multi-file package
- Lookup symbol definition by name
- Find all references to symbol
- Get visible symbols at cursor position
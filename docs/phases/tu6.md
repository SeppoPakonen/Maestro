# Phase TU6: Code Transformation and Convention Enforcement 📋 **[Planned]**

**Reference**: `docs/ast.md` Phase 6
**Duration**: 3-4 weeks
**Dependencies**: Phases TU3-TU5

**Objective**: Implement code transformation and U++ convention enforcement.

## Tasks

- [ ] **TU6.1: AST Transformation Framework**
  - [ ] Implement `ASTTransformer` base class
  - [ ] Support pluggable transformations
  - [ ] Preserve source locations during transformation

- [ ] **TU6.2: U++ Convention Enforcer**
  - [ ] Implement `UppConventionTransformer`
  - [ ] Build dependency graph from AST
  - [ ] Compute correct declaration order (topological sort)
  - [ ] Generate primary header with declarations in order
  - [ ] Update .cpp files to include only primary header
  - [ ] Add forward declarations where needed

- [ ] **TU6.3: Code Generation from AST**
  - [ ] Implement `CodeGenerator` class
  - [ ] Generate C++ code from AST
  - [ ] Generate Java code from AST
  - [ ] Preserve formatting and comments (optional)

## Deliverables:
- AST transformation framework
- U++ convention enforcer
- Code generator from AST
- CLI: `maestro tu transform --to-upp PACKAGE`

## Test Criteria:
- Transform simple C++ project to U++ conventions
- Verify generated code compiles
- Verify declaration order is correct
- Verify forward declarations added where needed
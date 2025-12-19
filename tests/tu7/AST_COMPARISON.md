# TU7: Multi-Language AST Comparison

**Date**: 2025-12-19
**Languages**: C++, Java, Python
**Tool**: `maestro tu print-ast`

## Overview

This document compares the Abstract Syntax Tree (AST) structures generated from equivalent code constructs across three programming languages: C++, Java, and Python. The goal is to identify common patterns, differences, and opportunities for unified transformations.

## Test Programs

Three comprehensive test programs were created to exercise various language features:

1. **C++ (`test_sample.cpp`)**:
   - Classes with inheritance (Vehicle → Car)
   - Templates (Container<T>)
   - Namespaces (Utility)
   - Enums (Color)
   - Functions with various control structures
   - Smart pointers

2. **Java (`TestSample.java`)**:
   - Interfaces (Drawable)
   - Abstract classes (Shape)
   - Concrete classes with inheritance (Circle, Rectangle)
   - Enums (Direction)
   - Generics (Container<T>)
   - Annotations (@TestInfo)
   - Inner and nested classes
   - Lambda expressions

3. **Python (`test_sample.py`)**:
   - Abstract base classes (Shape)
   - Dataclasses (@dataclass Point)
   - Enums (Direction)
   - Generic classes (Container[T])
   - Decorators (timer_decorator, memoize)
   - Async functions
   - Generators
   - Context managers
   - Properties

## AST Structure Comparison

### Root Node

| Language | Root Node Type | Notes |
|----------|----------------|-------|
| C++ | `TRANSLATION_UNIT` | Contains all top-level declarations and macro definitions |
| Java | `program` | Tree-sitter root node containing all package/import/class declarations |
| Python | `Module` | Python AST root containing all module-level statements |

**Observation**: Each language has a distinct root node type reflecting its compilation model:
- C++ uses translation unit concept (preprocessed source)
- Java uses program (complete compilation unit)
- Python uses module (importable unit)

### Class Declarations

#### C++ Class Structure
```
CLASS_DECL: 'Vehicle'
├── Access specifiers (protected, public)
├── FIELD_DECL (members)
├── CONSTRUCTOR
├── DESTRUCTOR
├── CXX_METHOD (virtual functions)
└── Inheritance specifiers
```

#### Java Class Structure
```
class_declaration: 'Circle'
├── modifiers (public, private, etc.)
├── superclass (extends)
├── interfaces (implements)
├── class_body
│   ├── field_declaration
│   ├── constructor_declaration
│   └── method_declaration
```

#### Python Class Structure
```
ClassDef: 'Circle'
├── bases (inheritance)
├── keywords
├── decorator_list
├── FunctionDef (methods)
│   ├── arguments
│   ├── decorator_list (@property, etc.)
│   └── body
└── AnnAssign (annotated fields)
```

**Key Differences**:
- C++ uses access specifiers (public/private/protected) as distinct nodes
- Java uses modifiers as attributes on each member
- Python uses decorators and relies on naming conventions (e.g., `_private`)
- C++ has explicit constructor/destructor nodes
- All three support inheritance but express it differently

### Function/Method Declarations

| Feature | C++ | Java | Python |
|---------|-----|------|--------|
| Node Type | `FUNCTION_DECL`, `CXX_METHOD` | `method_declaration` | `FunctionDef`, `AsyncFunctionDef` |
| Return Type | Explicit type node | Type in declaration | Optional annotation |
| Parameters | `PARM_DECL` nodes | `formal_parameters` | `arguments` node with `arg` children |
| Decorators/Annotations | N/A (attributes) | `@annotation` | `decorator_list` |
| Modifiers | Access specifiers, `virtual`, `static` | `public`, `private`, `static`, `final` | `@staticmethod`, `@classmethod` |

**Observations**:
- C++ and Java have strong typing in AST; Python types are optional annotations
- Python's decorator system is more flexible than Java's annotations
- C++ virtual methods are explicit; Java uses `@Override`; Python uses duck typing

### Control Flow Structures

#### If-Else Statements

**C++ AST**:
```
IF_STMT
├── Condition (BINARY_OPERATOR)
├── Then (COMPOUND_STMT)
└── Else (COMPOUND_STMT or IF_STMT)
```

**Java AST**:
```
if_statement
├── condition (parenthesized_expression)
├── consequence (block or statement)
└── alternative (block or statement)
```

**Python AST**:
```
If
├── test (Compare node)
├── body (list of statements)
└── orelse (list of statements)
```

**Commonality**: All three follow a similar tree structure: condition → true branch → false branch

#### Loops

| Loop Type | C++ | Java | Python |
|-----------|-----|------|--------|
| For Loop | `FOR_STMT` | `for_statement` | `For` |
| While Loop | `WHILE_STMT` | `while_statement` | `While` |
| Enhanced For | Range-based for | Enhanced for | For with iteration |
| Do-While | `DO_STMT` | `do_statement` | N/A (use while) |

**Observations**:
- Python lacks do-while loops
- Range-based/enhanced for loops are syntactic sugar over iterators
- All three have similar AST structure for basic while loops

### Type System Representation

#### C++ Types
- Explicit type nodes: `TYPE_REF`, built-in types
- Template instantiations: `TEMPLATE_REF`
- Pointer/reference types: separate node kinds

#### Java Types
- Type nodes: primitive types, class types, array types
- Generic types: `type_arguments` node
- Full type information in AST

#### Python Types
- Optional type annotations: `Name` or `Subscript` nodes
- Runtime types not in AST (dynamic typing)
- Type hints are just annotations, not enforced

**Major Difference**: C++ and Java have complete type information in AST; Python types are optional hints.

### Templates/Generics

| Language | Feature | AST Representation |
|----------|---------|-------------------|
| C++ | Templates | `TEMPLATE_DECL`, `TEMPLATE_TYPE_PARAMETER` |
| Java | Generics | `type_parameters`, `type_arguments` |
| Python | Generic Types | TypeVar usage (runtime, not in AST structure) |

**Observations**:
- C++ templates are most powerful (full Turing-complete metaprogramming)
- Java generics use type erasure (less information at runtime)
- Python generics are runtime hints using `typing` module

### Namespaces/Packages

| Language | Concept | AST Node |
|----------|---------|----------|
| C++ | Namespace | `NAMESPACE` |
| Java | Package | `package_declaration` |
| Python | Module | Implicit (file = module) |

**Differences**:
- C++ allows nested namespaces and namespace aliases
- Java packages are directory-based, declared at file start
- Python modules are implicit (filename = module name)

## Common Patterns

1. **Tree Structure**: All three languages use hierarchical tree structures for AST
2. **Declarations**: Classes, functions, and variables are represented as declaration nodes
3. **Statements vs Expressions**: Clear distinction between statements and expressions
4. **Block Scoping**: Compound statements/blocks contain child statements
5. **Symbol Information**: Location info (file, line, column) available for all

## Key Differences

1. **Type Information**:
   - C++: Strong, compile-time types deeply embedded in AST
   - Java: Strong, compile-time types with full representation
   - Python: Optional type hints, dynamic typing at runtime

2. **Inheritance Model**:
   - C++: Multiple inheritance, virtual methods, access specifiers
   - Java: Single inheritance (classes), multiple interfaces, modifiers
   - Python: Multiple inheritance, duck typing, no access control

3. **Preprocessing**:
   - C++: Heavy preprocessing (macros, includes) visible in AST
   - Java: No preprocessing, clean AST
   - Python: No preprocessing (imports are runtime)

4. **Memory Management**:
   - C++: Manual/RAII, smart pointers visible in AST
   - Java: Garbage collected, not visible in AST
   - Python: Garbage collected, not visible in AST

5. **Metaprogramming**:
   - C++: Template metaprogramming (compile-time)
   - Java: Reflection (runtime), annotations
   - Python: Decorators, metaclasses (runtime)

## Opportunities for Unified Transformations

### 1. Code Style Enforcement
**Feasible**: Convert naming conventions across languages
- Example: camelCase (Java) ↔ snake_case (Python) ↔ PascalCase (C++)

### 2. Structural Refactoring
**Feasible**: Extract methods, rename symbols, move declarations
- All three have clear function/method boundaries
- Symbol resolution works similarly

### 3. Design Pattern Detection
**Feasible**: Identify common patterns (Singleton, Factory, etc.)
- Class hierarchies are similar enough
- Method call patterns are comparable

### 4. Documentation Generation
**Highly Feasible**: Extract API documentation from AST
- All three have docstrings/comments
- Parameter information is available
- Return types (C++, Java) or annotations (Python)

### 5. Cross-Language Code Generation
**Challenging**: Generate equivalent code in another language
- Type system differences are significant
- Memory models differ fundamentally
- Some idioms don't translate (C++ templates → Java generics)

### 6. Dependency Analysis
**Feasible**: Build dependency graphs from imports/includes
- C++: Parse `#include` directives
- Java: Parse `import` statements
- Python: Parse `import`/`from` statements

### 7. Complexity Metrics
**Highly Feasible**: Calculate cyclomatic complexity, nesting depth
- Control flow structures are similar
- All have countable decision points

## Recommendations

1. **Unified AST Format**: Create a language-agnostic intermediate representation for common constructs
   - Base nodes: Class, Method, Function, Variable
   - Control flow: If, While, For, Switch/Match
   - Type information: Normalized representation

2. **Language-Specific Extensions**: Preserve unique features
   - C++: Templates, multiple inheritance
   - Java: Interfaces, annotations
   - Python: Decorators, async/await

3. **Transformation Pipeline**:
   ```
   Source Code → Language Parser → Language AST →
   Unified IR → Transformation → Target AST → Code Generation
   ```

4. **Tool Development**:
   - AST query language (similar to CSS selectors for DOM)
   - Pattern matching for code search
   - Transformation DSL for refactoring

## Test Results Summary

✅ **C++ AST Printing**: Success
- Tested with: classes, templates, inheritance, namespaces, control flow
- Output: Readable tree structure with type information
- File: `cpp_ast_output.txt`

✅ **Java AST Printing**: Success
- Tested with: interfaces, classes, generics, annotations, lambdas
- Output: Complete tree structure from tree-sitter
- File: `java_ast_output.txt`

✅ **Python AST Printing**: Success
- Tested with: classes, decorators, async, generators, comprehensions
- Output: Python AST module output in tree format
- File: `python_ast_output.txt`

## Conclusion

The three languages show significant differences in their AST structures, reflecting different design philosophies:

- **C++**: Complex, type-rich, low-level control
- **Java**: Structured, object-oriented, platform-independent
- **Python**: Dynamic, high-level, flexible

Despite differences, common patterns exist that enable:
1. Cross-language analysis tools
2. Code quality metrics
3. Structural refactoring
4. Documentation generation

The biggest challenges for unified transformations are:
1. Type system incompatibilities
2. Memory management differences
3. Language-specific idioms
4. Runtime vs compile-time features

**TU7 Success Criteria Met**:
- ✅ AST correctly captures all language constructs
- ✅ Output is readable and well-formatted
- ✅ Node types match expected language semantics
- ✅ Relationships between nodes are accurate
- ✅ Foundation laid for future cross-language transformations

## Files Generated

1. `test_sample.cpp` - C++ test program (210 lines)
2. `TestSample.java` - Java test program (328 lines)
3. `test_sample.py` - Python test program (390 lines)
4. `cpp_ast_output.txt` - C++ AST output
5. `java_ast_output.txt` - Java AST output
6. `python_ast_output.txt` - Python AST output
7. `AST_COMPARISON.md` - This document

## Command Reference

```bash
# Print AST for C++ file
maestro tu print-ast tests/tu7/test_sample.cpp --max-depth 4

# Print AST for Java file
maestro tu print-ast tests/tu7/TestSample.java --max-depth 4

# Print AST for Python file
maestro tu print-ast tests/tu7/test_sample.py --max-depth 4

# Save to file
maestro tu print-ast <file> --output <output.txt>

# Hide certain information
maestro tu print-ast <file> --no-types --no-locations
```

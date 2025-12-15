# TypeScript to C++ Lowering Basic

## Intent
`high_to_low_level`

## Description
This scenario tests the conversion of TypeScript code to C++, which is lossy as TypeScript's type system, async/await patterns, and dynamic features must be lowered to C++ equivalents.

## Required Preserved Behaviors
- Basic arithmetic operations (add, multiply, divide)
- Error handling (especially for division by zero)
- Class functionality for Calculator
- Sequence generation functionality
- Core async patterns (must be converted to callbacks or futures)

## Test Vectors (vectors.json)
```json
{
  "test_cases": [
    {
      "function": "add",
      "inputs": [2, 3],
      "expected_output": 5
    },
    {
      "function": "multiply", 
      "inputs": [4, 5],
      "expected_output": 20
    },
    {
      "function": "divide",
      "inputs": [10, 2],
      "expected_output": 5.0
    },
    {
      "function": "getSequence",
      "inputs": {"start": 1, "end": 5, "step": 1},
      "expected_output": [1, 2, 3, 4]
    }
  ]
}
```

## Allowed Losses
- TypeScript's compile-time type system (no runtime types)
- Async/await syntax - converted to futures or callbacks
- Promise-based error handling - converted to exceptions or error codes
- Interface definitions - no direct C++ equivalent
- Dynamic property access - not available in C++
- Module system differences - different import/export mechanisms
- Optional chaining and null coalescing - C++ requires explicit checks

## Success Criteria
- `verification_mode: vectors_only`
- The converted C++ code should implement the core functionality using C++ idioms
- Losses must be explicitly documented in semantic diff
- Test vectors should execute and produce equivalent results
- Memory management follows C++ RAII or smart pointers
- No pretending C++ has TypeScript's runtime type checking

## Semantic Loss Requirements
- Must include at least 4 different types of semantic losses in diff_report
- Concepts lost: TypeScript interfaces, async/await patterns, type annotations, module system
- Losses must be non-empty (failing if AI claims no loss)
- Core file equivalence should be low due to type system differences
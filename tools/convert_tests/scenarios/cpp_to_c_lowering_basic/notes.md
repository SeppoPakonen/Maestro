# C++ to C Lowering Basic

## Intent
`high_to_low_level`

## Description
This scenario tests the conversion of C++ code to C, which is inherently lossy as C++ features like classes, RAII, smart pointers, and STL containers must be lowered to C equivalents.

## Required Preserved Behaviors
- Basic arithmetic operations (add, multiply, divide)
- Error handling for division by zero
- Functionality for creating sequences
- Input/output operations should maintain similar behavior

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
      "function": "divide",
      "inputs": [10, 0], 
      "expected_output": "error"
    }
  ]
}
```

## Allowed Losses
- RAII (Resource Acquisition Is Initialization) - C has no constructors/destructors
- Smart pointers - no automatic memory management
- STL containers - must be replaced with arrays or manual memory management
- Exception handling - must be replaced with error codes
- Function overloading - not supported in C
- Operator overloading - not supported in C
- Namespaces - not available in C

## Success Criteria
- `verification_mode: vectors_only`
- The converted C code should implement the core functionality using C idioms
- Losses must be explicitly documented in semantic diff
- Test vectors should execute and produce equivalent results
- Memory management must be explicit (malloc/free instead of RAII)
- No "fake" C++ runtime should be created in C

## Semantic Loss Requirements
- Must include at least 5 different types of semantic losses in diff_report
- Concepts lost: classes, smart pointers, STL containers, RAII, destructors
- Losses must be non-empty (failing if AI claims no loss)
# Language Conversion Tests

This directory contains test scenarios for Maestro's `convert` functionality focused on different types of language migrations with various semantics preservation requirements.

## Scenarios

### Same-Family Language Conversion Tests

#### JavaScript to TypeScript (`js_to_ts_basic`)
- Conversion from JavaScript to TypeScript with type annotations
- Preserves runtime behavior while adding compile-time type safety
- Maps `require` statements to `import` statements
- Adds type annotations to function parameters and return values

#### C to C++ (`c_to_cpp_basic`)
- Conversion from C to C++ with semantic preservation
- Maps C structs to C++ classes
- Converts malloc/free to new/delete or RAII patterns
- Adapts C standard library to C++ STL equivalents

#### Java to C# (`java_to_csharp_basic`)
- Conversion from Java to C# with object-oriented structure preservation
- Maps Java packages to C# namespaces
- Converts Java Collections to .NET Collections equivalent
- Adapts Java I/O classes to .NET equivalents

### High-to-Low Conversion Tests (Category Test 4)

#### C++ to C Lowering (`cpp_to_c_lowering_basic`)
- **Intent**: `high_to_low_level`
- **Conversion**: C++ with classes, RAII, smart pointers, STL → C with manual memory management
- **Semantic losses**: Classes to structs, RAII to manual cleanup, smart pointers to raw pointers, STL containers to arrays
- **Verification**: `vectors_only` - test vectors execution, semantic diff validation
- **Success criteria**: Truthful, traceable lowering with explicit loss documentation

#### TypeScript to C++ Lowering (`ts_to_cpp_lowering_basic`)
- **Intent**: `high_to_low_level`
- **Conversion**: TypeScript with type system, async/await, interfaces → C++ compilation
- **Semantic losses**: Type system, async/await patterns, interface definitions, module differences
- **Verification**: `vectors_only` - test vectors execution, semantic diff validation
- **Success criteria**: Truthful, traceable lowering with explicit loss documentation; designed to trigger checkpoint escalation

## Running Tests

### Run Individual Tests
```bash
# JavaScript to TypeScript
python tools/convert_tests/run_scenario.py --scenario js_to_ts_basic --force-clean --verbose

# C to C++
python tools/convert_tests/run_scenario.py --scenario c_to_cpp_basic --force-clean --verbose

# Java to C#
python tools/convert_tests/run_scenario.py --scenario java_to_csharp_basic --force-clean --verbose

# Category Test 4 - High-to-Low Conversion Tests
# C++ to C Lowering
python tools/convert_tests/run_scenario.py --scenario cpp_to_c_lowering_basic --force-clean --verbose

# TypeScript to C++ Lowering (with auto-approval for checkpoints)
python tools/convert_tests/run_scenario.py --scenario ts_to_cpp_lowering_basic --force-clean --auto-approve-checkpoints --verbose

# Or without auto-approval (will pause at checkpoints):
python tools/convert_tests/run_scenario.py --scenario ts_to_cpp_lowering_basic --force-clean --verbose
```

### Run All Tests
```bash
# List all available scenarios
python tools/convert_tests/run_scenario.py --list

# Run in dry mode (validation only, no conversion)
python tools/convert_tests/run_scenario.py --scenario js_to_ts_basic --no-ai --verbose
python tools/convert_tests/run_scenario.py --scenario c_to_cpp_basic --no-ai --verbose
python tools/convert_tests/run_scenario.py --scenario java_to_csharp_basic --no-ai --verbose
python tools/convert_tests/run_scenario.py --scenario cpp_to_c_lowering_basic --no-ai --verbose
python tools/convert_tests/run_scenario.py --scenario ts_to_cpp_lowering_basic --no-ai --verbose
```

## Test Structure

Each scenario contains:
- `source_repo/` - Input repository with language-specific code
- `notes.md` - Intent, preservation requirements, and success criteria
- `expected/` - Golden files for validation
  - `output_schema.json` - Expected artifacts and mapping elements
  - `summary.json` - Expected execution summary
  - `report_sections.txt` - Expected content in reports
  - `semantic_diff_requirements.json` - For high_to_low_level scenarios: expected semantic losses, checkpoint requirements

The test harness validates:
- No writes to source repository (protection enforced)
- Proper semantic mapping file generation
- Correct intent handling (`language_to_language` or `high_to_low_level`)
- Required stages execution (`semantic_mapping`, `overview`, etc.)
- Semantic diff execution and validation for `high_to_low_level` scenarios
- Checkpoint handling for scenarios designed to trigger escalation
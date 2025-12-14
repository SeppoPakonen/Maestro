# Same-Family Language Conversion Tests

This directory contains test scenarios for Maestro's `convert` functionality focused on **same-family language migrations** where semantics are largely preserved and success can be measured mechanically.

## Scenarios

### JavaScript to TypeScript (`js_to_ts_basic`)
- Conversion from JavaScript to TypeScript with type annotations
- Preserves runtime behavior while adding compile-time type safety
- Maps `require` statements to `import` statements
- Adds type annotations to function parameters and return values

### C to C++ (`c_to_cpp_basic`)
- Conversion from C to C++ with semantic preservation
- Maps C structs to C++ classes
- Converts malloc/free to new/delete or RAII patterns
- Adapts C standard library to C++ STL equivalents

### Java to C# (`java_to_csharp_basic`)
- Conversion from Java to C# with object-oriented structure preservation
- Maps Java packages to C# namespaces
- Converts Java Collections to .NET Collections equivalent
- Adapts Java I/O classes to .NET equivalents

## Running Tests

### Run Individual Tests
```bash
# JavaScript to TypeScript
python tools/convert_tests/run_scenario.py --scenario js_to_ts_basic --force-clean --verbose

# C to C++
python tools/convert_tests/run_scenario.py --scenario c_to_cpp_basic --force-clean --verbose

# Java to C#
python tools/convert_tests/run_scenario.py --scenario java_to_csharp_basic --force-clean --verbose
```

### Run All Tests
```bash
# List all available scenarios
python tools/convert_tests/run_scenario.py --list

# Run in dry mode (validation only, no conversion)
python tools/convert_tests/run_scenario.py --scenario js_to_ts_basic --no-ai --verbose
python tools/convert_tests/run_scenario.py --scenario c_to_cpp_basic --no-ai --verbose
python tools/convert_tests/run_scenario.py --scenario java_to_csharp_basic --no-ai --verbose
```

## Test Structure

Each scenario contains:
- `source_repo/` - Input repository with language-specific code
- `notes.md` - Intent, preservation requirements, and success criteria
- `expected/` - Golden files for validation
  - `output_schema.json` - Expected artifacts and mapping elements
  - `summary.json` - Expected execution summary
  - `report_sections.txt` - Expected content in reports

The test harness validates:
- No writes to source repository (protection enforced)
- Proper semantic mapping file generation
- Correct intent handling (`language_to_language`)
- Required stages execution (`semantic_mapping`, `overview`, etc.)
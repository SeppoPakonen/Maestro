# Python to Typed Python Conversion Test

## Intent
typedness_upgrade

## Description
This scenario tests conversion from untyped Python to typed Python with semantic preservation. The conversion should add type annotations while maintaining the runtime behavior. This is a "tempo discipline" conversion: same song, less improvisation allowed.

## Required Typing Improvements
- Addition of type hints to function parameters and return values
- Type annotations for class instance variables
- TypedDict for dictionary structures
- Type hints for variables
- Updated mypy configuration to enforce stricter typing
- Prefer dataclasses + type hints over basic classes
- Gradual typing approach: allow Any only where unavoidable

## What Must Not Change
- Core functionality and logic flow
- Runtime behavior of all functions
- All existing functionality must remain intact
- Import statements (unless required for typing imports)

## Success Criteria
- Generated Python code has comprehensive type annotations added appropriately
- mypy configuration updated to enforce stricter typing
- All original functionality remains intact
- Semantic mapping file contains typing policy decisions and risk notes
- No changes made to source repository
- Target repo contains properly typed Python equivalents
- Generated code passes py_compile validation (hard gate)
- mypy runs successfully on generated code (soft validation if mypy available)
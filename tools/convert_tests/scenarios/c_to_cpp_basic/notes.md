# C to C++ Conversion Test

## Intent
language_to_language

## Description
This scenario tests conversion from C to C++ with semantic preservation. The conversion should maintain the same functionality while introducing C++ idioms like classes, RAII, and STL.

## What Must Be Preserved
- Core functionality and program logic
- Runtime behavior of all functions
- Overall program structure and flow

## Allowed/Expected Changes
- Conversion of structs to classes
- Replacement of malloc/free with new/delete or RAII patterns
- Conversion of C-style arrays to std::vector/std::array
- Use of C++ standard library instead of C library functions
- Introduction of member functions instead of standalone functions
- Header file adjustments (e.g., cstdio instead of stdio.h)

## Success Criteria
- Generated C++ code compiles with g++
- All original functionality remains intact  
- Modern C++ idioms introduced appropriately
- Semantic mapping file contains C to C++ construct mappings
- No changes made to source repository
- Target repo contains properly converted C++ equivalents
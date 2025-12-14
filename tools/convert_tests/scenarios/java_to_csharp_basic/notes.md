# Java to C# Conversion Test

## Intent
language_to_language

## Description
This scenario tests conversion from Java to C# with semantic preservation. The conversion should maintain the same functionality while adapting to C# idioms and .NET Framework equivalents.

## What Must Be Preserved
- Core functionality and program logic
- Runtime behavior of all methods
- Object-oriented structure and relationships

## Allowed/Expected Changes
- Package declarations to namespace declarations
- Java Collections to .NET Collections (ArrayList to List<T>, etc.)
- Java I/O classes to .NET equivalents
- Access modifiers adjustments (public/private/protected to C# equivalents)
- Exception handling patterns (try-catch-finally to C# equivalents)
- Method signatures adapted to C# conventions

## Success Criteria
- Generated C# code compiles with dotnet build (or validates with syntax checker)
- All original functionality remains intact
- Proper .NET idioms introduced appropriately
- Semantic mapping file contains Java to C# construct mappings
- No changes made to source repository
- Target repo contains properly converted C# equivalents
# JavaScript to TypeScript Conversion Test

## Intent
language_to_language

## Description
This scenario tests conversion from JavaScript to TypeScript with semantic preservation. The conversion should add type annotations while maintaining the runtime behavior.

## What Must Be Preserved
- Core functionality and logic flow
- Runtime behavior of all functions
- Package dependencies and structure

## Allowed/Expected Changes
- Addition of type annotations to function parameters and return values
- Conversion of `var/let/const` patterns to TypeScript equivalents
- Module import/export transformations (`require` to `import` statements)
- Addition of interface/type definitions where appropriate
- Possible conversion of classes to more TypeScript-idiomatic patterns

## Success Criteria
- Generated TypeScript code compiles with `tsc --noEmit`
- All original functionality remains intact
- Type annotations added appropriately
- Semantic mapping file contains JS to TS construct mappings
- No changes made to source repository
- Target repo contains properly typed TypeScript equivalents
# U++ Package/Assembly Discovery Contract

## Overview
This document specifies Maestro's U++ package and assembly discovery model, aligned with U++ IDE core's reference behavior.

## Definitions

### Assembly
- An **assembly** is a directory containing U++ packages
- In Maestro's model:
  - Default assembly: repository root directory
  - Additional assemblies: configured via settings or discovered automatically
  - Each assembly contains zero or more package folders
  - Assemblies are searched in a deterministic order (config order, then filesystem order)

### Package Folder
- A **package folder** is a directory that may or may not contain a valid U++ package
- Identified by directory name (e.g., `Core`, `CtrlLib`, `ide`)

### Package
- A **package** exists **iff** `<PkgName>/<PkgName>.upp` file exists in the package folder
- The `.upp` file defines the package's metadata, dependencies, and build configuration
- A package folder without a corresponding `.upp` file is not considered a valid package

## Discovery Model

### Assembly Discovery
1. **Config-driven**: Assemblies specified in configuration files take precedence
2. **Auto-discovered**: Repository root is automatically treated as an assembly
3. **Search Order**: 
   - Configured assemblies in order of specification
   - Repository root (if not already included via config)
   - Additional discovered assemblies in alphabetical order (or stable filesystem order)

### Package Discovery
1. Within each assembly:
   - Recursively scan subdirectories to find package folders
   - A directory becomes a package if `<DirName>/<DirName>.upp` exists
   - File extensions for source files: `.cpp`, `.cppi`, `.icpp`, `.h`, `.hpp`, `.inl`, `.c`, `.cc`, `.cxx`
   - Package name is derived from directory name (case-sensitive)

### Dependency Resolution
1. Given a main package with dependencies listed in its `.upp` file (in `uses` section)
2. For each dependency package name:
   - Search assemblies in order
   - Within each assembly, search package folders in order
   - First matching package (`<Name>/<Name>.upp`) wins
   - Stop searching after first match (first-match-wins rule)

## Example Discovery Flow

```
Repository Root: /home/user/uppsrc
Assemblies:
1. /home/user/uppsrc/assemblerA
2. /home/user/uppsrc/assemblerB

[maestro] assemblies (2):
  1) /home/user/uppsrc/assemblerA
  2) /home/user/uppsrc/assemblerB

[maestro] scanning assembly: assemblerA
  package folders: Core, CtrlLib, MyPkg
    Core/Core.upp -> FOUND (package: Core)
    CtrlLib/CtrlLib.upp -> FOUND (package: CtrlLib) 
    MyPkg/MyPkg.upp -> NOT FOUND (not a package)

[maestro] scanning assembly: assemblerB
  package folders: Core, TestLib
    Core/Core.upp -> FOUND (package: Core) - DUPLICATE
    TestLib/TestLib.upp -> FOUND (package: TestLib)

[maestro] resolve dependency: Core
  check: assemblerA/Core/Core.upp -> FOUND (first match wins)
  check: assemblerB/Core/Core.upp -> SKIPPED (already found)

[maestro] resolve dependency: TestLib  
  check: assemblerA/TestLib/TestLib.upp -> NOT FOUND
  check: assemblerB/TestLib/TestLib.upp -> FOUND
```

## Search Order Determinism

### Assembly Order
- Configured assemblies: order of appearance in configuration
- Auto-discovered: alphabetical order by directory name
- Repository root: placed appropriately in order

### Package Folder Order  
- Within each assembly: alphabetical order by directory name
- This ensures consistent and predictable package discovery

### Dependency Resolution Order
- For each dependency: iterate assemblies in order
- Within each assembly: iterate package folders in order  
- First match wins

## Error Handling

### No Assemblies Found
- Actionable message: "No assemblies found. Please configure assemblies in your project settings."

### Main Package Not Found  
- Show what packages were found in available assemblies
- Suggestion: "Check that your main package has a <Name>/<Name>.upp file"

### Dependency Package Missing
- Show all searched locations
- Suggestion: "Add assembly containing the package, create the package, or fix dependency declaration in .upp file"

## Trace Mode (Verbose Output)

In verbose mode (`-v`), Maestro should output:
- Repository root identification
- Configured assembly roots  
- Discovered assemblies in search order
- Package folders scanned per assembly
- Resolved main package
- Dependency resolution search path for each dependency
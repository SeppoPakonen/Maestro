# Subsystem Deep Dive: Repo Resolve

The `Repo Resolve` subsystem is critical for understanding the structural layout of a codebase, identifying packages, assemblies, and their relationships, detecting various build systems, and inferring file conventions. It provides a structured, hierarchical view of the repository's components.

## 1. Scanner Modules

The subsystem leverages several specialized modules to perform its scanning and parsing tasks:

*   **`maestro/repo/scanner.py`:** The central orchestrator. It performs multi-pass file system walks, intelligently prunes irrelevant directories, and coordinates calls to other parsers. It aggregates all discovered information into a `RepoScanResult`.
*   **`maestro/repo/build_systems.py`:** Dedicated to detecting and parsing various non-U++ build systems like CMake, GNU Make, Autoconf, Maven, Gradle, and MSBuild/Visual Studio. It provides generic functions to scan for packages within these systems.
*   **`maestro/repo/upp_parser.py`:** A tolerant parser specifically designed for U++ `.upp` package definition files. It extracts metadata, dependencies, and file groupings from these files.
*   **`maestro/repo/uplusplus_var_reader.py`:** Reads U++ IDE `.var` configuration files, which define user-specific or global U++ assembly paths, integrating external assembly definitions into the scan.
*   **`maestro/repo/assembly.py`:** Aggregates individual package discoveries into higher-level "assembly" units, classifying them based on their content and build systems.
*   **`maestro/repo/grouping.py`:** Provides an `AutoGrouper` to infer logical `FileGroup`s within packages based on file types and patterns, contributing to convention inference.

## 2. Package/Assembly Discovery

The subsystem systematically identifies and categorizes code components:

*   **U++ Packages:**
    *   `maestro/repo/scanner.py` performs a file system walk to locate directories conforming to the U++ package convention (`<Name>/<Name>.upp`).
    *   `maestro/repo/upp_parser.py` is then used to parse these `.upp` files, extracting metadata, explicitly defined file groups, and dependencies.
    *   Results are encapsulated in `maestro/repo/package.py:PackageInfo` objects with `build_system='upp'`.
*   **Other Build System Packages:**
    *   `maestro/repo/build_systems.py`'s `scan_all_build_systems` function is dynamically called by `scanner.py`.
    *   It detects specific build system files (e.g., `CMakeLists.txt`, `pom.xml`, `build.gradle`, `.sln`).
    *   Specialized parsers within `build_systems.py` (`scan_cmake_packages`, `scan_maven_packages`, `scan_gradle_packages`, etc.) extract targets, source files, and dependencies, wrapping them in `maestro/repo/build_systems.BuildSystemPackage` objects (which are then converted to `PackageInfo` by `scanner.py`).
*   **Assemblies:**
    *   `maestro/repo/assembly.py:detect_assemblies` takes the list of all discovered `PackageInfo` objects.
    *   It groups packages by their parent directories.
    *   It then applies heuristics (e.g., a directory containing multiple packages, or specific build system types) to identify and classify higher-level `AssemblyInfo` units.
    *   User-defined assemblies are incorporated via `maestro/repo/uplusplus_var_reader.py:read_user_assemblies`, which finds and parses `.var` files typically located in `~/.config/u++/ide/`. These external assembly definitions contribute to the `user_assemblies` list in `RepoScanResult`.
*   **Unknown Paths & Internal Packages:**
    *   `maestro/repo/scanner.py` performs a second pass over the file system, pruning known package and assembly directories.
    *   Any remaining files or directories are identified as `UnknownPath` objects, with their likely `guessed_kind` inferred by `scanner.guess_path_kind`.
    *   These `UnknownPath`s are then aggregated into `maestro/repo/scanner.InternalPackage` objects by `scanner.infer_internal_packages`, often representing implicit groupings like 'docs', 'scripts', or 'assets'.

## 3. Build System Detection

*   **Initial Detection:** `maestro/repo/build_systems.py:detect_build_system` performs a high-level check to determine which build systems are present in the repository by searching for signature files.
*   **Detailed Parsing:** Based on the initial detection, `maestro/repo/build_systems.scan_all_build_systems` invokes specialized parsers (e.g., `scan_cmake_packages`, `scan_maven_packages`) to extract detailed package information.
*   **Classification:** The `build_system` field in `maestro/repo/package.py:PackageInfo` and the `build_systems` list in `maestro/repo/assembly.py:AssemblyInfo` explicitly record the type(s) of build systems associated with each discovered component.

## 4. Convention Inference/Violations

*   **File Grouping (`maestro/repo/grouping.py:AutoGrouper`):**
    *   The `AutoGrouper` uses a predefined set of `GROUP_RULES` (mappings from file extensions/patterns to logical categories like 'Scripts', 'Documentation', 'C/C++').
    *   It applies these rules to lists of files (e.g., `PackageInfo.files`, `InternalPackage.members`) to automatically organize them into `maestro/repo/package.py:FileGroup` objects. This is a primary mechanism for inferring common project conventions.
    *   `FileGroup.auto_generated` is set to `True` for these inferred groups.
*   **Explicit U++ File Groups:**
    *   `maestro/repo/upp_parser.py:_process_file_groups` creates `FileGroup`s based on explicit `separator` directives found within `.upp` files. These represent developer-defined logical groupings.
    *   `FileGroup.readonly` can also be set from `.upp` metadata.
*   **Representation:** Both explicitly defined and automatically inferred `FileGroup`s are stored in `PackageInfo.groups`. Files that don't fit into any defined or inferred group are listed in `PackageInfo.ungrouped_files`.
*   **Dependency Inference:** The `dependencies` field in `PackageInfo` represents explicit dependencies between packages, often inferred directly from build system configurations (e.g., Maven POMs, U++ `uses` directives).
*   **Violations (Conceptual):** While the subsystem excels at *inferring* conventions, explicitly reporting "violations" would typically involve a separate analysis layer that compares the discovered structure (`RepoScanResult`) against a set of predefined or user-configured "ideal" conventions. This module primarily provides the data needed for such an analysis.

## 5. Configuration & Globals

*   `os.walk`, `pathlib.Path`: Standard Python libraries for file system traversal.
*   `re`: Standard Python library for regular expression parsing of build system files.
*   `xml.etree.ElementTree`: Used for parsing XML-based build files (Maven `pom.xml`, MSBuild `.vcxproj`).
*   `skip_dirs` (in `maestro/repo/scanner.py`): A hardcoded list of directories to ignore during scanning.
*   `source_extensions` (in `maestro/repo/scanner.py`): Common source file extensions for U++ packages.

## 6. Validation & Assertion Gates

*   **File Existence:** Many parsing functions check for file existence before attempting to read.
*   **Parsing Errors:** Parsers (e.g., `UppParser`, build system scanners) are designed to be tolerant; they often catch exceptions during parsing and report warnings or return partial data rather than crashing.
*   **Pattern Matching:** Relies heavily on regex patterns for extracting information from text-based build files. Incorrect patterns could lead to missed or malformed data.

## 7. Side Effects

*   Reads numerous files from the repository's file system.
*   No direct write operations are performed by this subsystem; it focuses purely on analysis and discovery.

## 8. Error Semantics

*   Errors during parsing (e.g., malformed XML, unexpected file content) are often caught and reported as warnings (if `verbose`) or lead to incomplete metadata for a specific package/assembly.
*   `FileNotFoundError` is handled gracefully.
*   `ImportError` is handled if optional parsing modules (like `uplusplus_var_reader`) are not available.

## 9. Existing Tests & Coverage Gaps

*   **Tests:**
    *   `maestro/tests/repo/` directory should contain unit tests for `scanner.py`, `upp_parser.py`, `build_systems.py`, `assembly.py`, and `grouping.py`.
    *   Tests should cover:
        *   Correct identification of packages/assemblies for various build systems.
        *   Accurate parsing of metadata (dependencies, source files, file groups).
        *   Handling of edge cases like nested packages, complex build file syntax, and malformed inputs.
        *   Effectiveness of directory pruning.
        *   Accuracy of `AutoGrouper` rules.
*   **Coverage Gaps:**
    *   Testing the interaction of multiple build systems in a single repository, and how `assembly.py` resolves them.
    *   Performance testing on large repositories with deep nesting or many files.
    *   Robustness against unusual build file formats or highly customized setups.
    *   Comprehensive testing of all `GROUP_RULES` in `AutoGrouper`.

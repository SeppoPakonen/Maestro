"""
TU (Translation Unit) commands for Maestro.
Provides AST-based analysis, indexing, and completion for multiple languages.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

from ..tu import (
    TUBuilder, ClangParser, JavaParser, KotlinParser, PythonParser,
    ASTSerializer, SymbolIndex, CompletionProvider, ASTPrinter
)
from ..tu.lsp_server import MaestroLSPServer


def get_parser_by_language(lang: str):
    """Get the appropriate parser for the specified language."""
    lang = lang.lower()
    if lang in ['cpp', 'c++', 'cxx', 'cc', 'c']:
        return ClangParser()
    elif lang in ['java']:
        return JavaParser()
    elif lang in ['kotlin', 'kt']:
        return KotlinParser()
    elif lang in ['python', 'py']:
        return PythonParser()
    else:
        raise ValueError(f"Unsupported language: {lang}")


def detect_language_from_path(file_path: str) -> str:
    """Detect language based on file extension."""
    ext = Path(file_path).suffix.lower()
    if ext in ['.cpp', '.cxx', '.cc', '.c++']:
        return 'cpp'
    elif ext in ['.c']:
        return 'c'
    elif ext in ['.java']:
        return 'java'
    elif ext in ['.kt', '.kotlin']:
        return 'kotlin'
    elif ext in ['.py']:
        return 'python'
    else:
        raise ValueError(f"Could not detect language from extension: {ext}")


def get_files_by_language(path: str, lang: str) -> List[str]:
    """Get all files matching the specified language in the given path."""
    path_obj = Path(path)
    if not path_obj.is_dir():
        return [str(path_obj)] if detect_language_from_path(str(path_obj)) == lang else []

    extensions = []
    if lang in ['cpp', 'c++', 'cxx', 'cc']:
        extensions = ['.cpp', '.cxx', '.cc', '.c++', '.h', '.hpp', '.hxx']
    elif lang == 'c':
        extensions = ['.c', '.h']
    elif lang == 'java':
        extensions = ['.java']
    elif lang == 'kotlin':
        extensions = ['.kt', '.kotlin']

    files = []
    for ext in extensions:
        files.extend([str(p) for p in path_obj.rglob(f'*{ext}')])

    return files


def handle_tu_build_command(args):
    """Handle maestro tu build [PACKAGE]"""
    print(f"Building translation unit for path: {args.path}")

    # Determine language
    lang = args.lang
    if not lang:
        # Auto-detect from first file in path
        files = get_files_by_language(args.path, 'cpp') + \
                get_files_by_language(args.path, 'java') + \
                get_files_by_language(args.path, 'kotlin')
        if not files:
            print("Error: No source files found in specified path")
            return 1
        lang = detect_language_from_path(files[0])
        print(f"Auto-detected language: {lang}")

    # Create the appropriate parser
    try:
        parser = get_parser_by_language(lang)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    # Get files to process
    files = get_files_by_language(args.path, lang)
    if not files:
        print(f"Error: No {lang} files found in {args.path}")
        return 1

    print(f"Found {len(files)} {lang} files")

    # Setup TU builder
    builder = TUBuilder(parser, cache_dir=args.output)

    try:
        # If force is requested, clear the cache first
        if args.force:
            import shutil
            cache_dir = Path(args.output)
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)  # Recreate the cache directory

        # Build TUs for all files
        results = builder.build(
            files=files,
            compile_flags=args.compile_flags or []
        )

        print(f"Successfully built translation units for {len(results)} files")
        if args.verbose:
            for result in results:
                print(f"  - {result.file_path}: {'success' if result.success else 'failed'}")

        return 0

    except Exception as e:
        print(f"Error building translation units: {e}")
        return 1


def handle_tu_info_command(args):
    """Handle maestro tu info [PACKAGE]"""
    print(f"Showing translation unit info for path: {args.path}")
    
    # This is a placeholder implementation - would typically show cache stats, etc.
    cache_path = Path(args.path) if args.path else Path('.maestro/tu/cache')
    if cache_path.exists():
        print(f"Cache directory: {cache_path}")
        print(f"Cache size: {len(list(cache_path.rglob('*.ast')))} cached units")
    else:
        print(f"Cache directory not found: {cache_path}")


def handle_tu_query_command(args):
    """Handle maestro tu query [PACKAGE]"""
    print(f"Querying symbols (name: {args.symbol}, file: {args.file}, kind: {args.kind})")

    # Look for symbol index (if exists)
    index_path = '.maestro/tu/analysis/symbols.db'
    if not os.path.exists(index_path):
        print(f"Symbol index not found: {index_path}")
        return 1

    try:
        index = SymbolIndex(index_path)
        symbols = index.query(name=args.symbol, file_path=args.file, kind=args.kind)

        if args.json:
            print(json.dumps([{
                'name': s.name,
                'kind': s.kind,
                'file': s.loc.file,
                'line': s.loc.line,
                'column': s.loc.column
            } for s in symbols]))
        else:
            if not symbols:
                print("No symbols found")
            else:
                print(f"Found {len(symbols)} symbols:")
                for sym in symbols:
                    print(f"  {sym.kind}: {sym.name} at {sym.loc.file}:{sym.loc.line}:{sym.loc.column}")

    except Exception as e:
        print(f"Error querying symbols: {e}")
        return 1


def handle_tu_complete_command(args):
    """Handle maestro tu complete [PACKAGE]"""
    print(f"Getting completions for {args.file}:{args.line}:{args.column}")

    try:
        # Load the AST for the file
        # This would normally be done via a TUBuilder with symbol resolution
        # For now, we'll create a simple completion provider
        provider = CompletionProvider()

        # In a real implementation, we'd have a TU with symbols available
        # Here we'll just return a simple placeholder
        completions = provider.get_completions(
            file_path=args.file,
            line=args.line,
            column=args.column
        )

        if args.json:
            print(json.dumps([{
                'label': c.label,
                'kind': c.kind,
                'detail': c.detail,
                'documentation': c.documentation
            } for c in completions]))
        else:
            if not completions:
                print("No completions available")
            else:
                print(f"Found {len(completions)} completions:")
                for comp in completions:
                    print(f"  {comp.label} ({comp.kind}): {comp.detail}")

    except Exception as e:
        print(f"Error getting completions: {e}")
        return 1


def handle_tu_references_command(args):
    """Handle maestro tu references [PACKAGE]"""
    print(f"Finding references to symbol {args.symbol} (defined in {args.file}:{args.line})")

    # Look for symbol index (if exists)
    index_path = '.maestro/tu/analysis/symbols.db'
    if not os.path.exists(index_path):
        print(f"Symbol index not found: {index_path}")
        return 1

    try:
        index = SymbolIndex(index_path)
        references = index.find_references(symbol_name=args.symbol, file_path=args.file, line=args.line)

        if args.json:
            print(json.dumps([{
                'file': ref.loc.file,
                'line': ref.loc.line,
                'column': ref.loc.column
            } for ref in references]))
        else:
            if not references:
                print("No references found")
            else:
                print(f"Found {len(references)} references:")
                for ref in references:
                    print(f"  at {ref.loc.file}:{ref.loc.line}:{ref.loc.column}")

    except Exception as e:
        print(f"Error finding references: {e}")
        return 1


def handle_tu_transform_command(args):
    """Handle maestro tu transform --to-upp PACKAGE"""
    from ..tu.transformers import UppConventionTransformer
    from ..tu.tu_builder import TUBuilder
    from ..tu.clang_parser import ClangParser
    from pathlib import Path

    print(f"Transforming package to U++ conventions: {args.package}")

    if args.to != 'upp':
        print(f"Error: Only 'upp' target is currently supported, got: {args.to}")
        return 1

    # Determine language
    lang = args.lang
    if not lang:
        # Auto-detect from first file in path
        files = get_files_by_language(args.package, 'cpp') + \
                get_files_by_language(args.package, 'java') + \
                get_files_by_language(args.package, 'kotlin')
        if not files:
            print("Error: No source files found in specified path")
            return 1
        lang = detect_language_from_path(files[0])
        print(f"Auto-detected language: {lang}")

    # Create the appropriate parser
    try:
        parser = get_parser_by_language(lang)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    # Get files to process
    files = get_files_by_language(args.package, lang)
    if not files:
        print(f"Error: No {lang} files found in {args.package}")
        return 1

    print(f"Found {len(files)} {lang} files")

    # Setup TU builder with symbol resolution
    builder = TUBuilder(parser, cache_dir=args.output)

    # For U++ transformation, we need a two-phase approach:
    # 1. First parse the original files to extract information for primary header
    # 2. Then update files to include the generated primary header

    try:
        # Phase 1: Parse original files to extract information for header generation
        # Build basic TUs for analysis without symbol indexing to avoid include issues
        results = {}
        for file_path in files:
            abs_path = str(Path(file_path).resolve())

            # Parse the file directly without includes to the primary header that doesn't exist yet
            document = parser.parse_file(abs_path, compile_flags=args.compile_flags or [])
            results[abs_path] = document

        print(f"Successfully parsed {len(results)} files for header generation")

        # Create U++ convention transformer
        package_name = Path(args.package).name or "transformed_package"
        transformer = UppConventionTransformer(package_name=package_name)

        # Build dependency graph from all documents FIRST
        for file_path, document in results.items():
            transformer._build_dependency_graph(document)

        # Compute declaration order
        transformer.declaration_order = transformer._compute_declaration_order()
        transformer.forward_declarations_needed = transformer._find_forward_declarations()

        print(f"Dependency order: {transformer.declaration_order[:10]}")  # Show first 10

        # Collect all declarations from all documents for primary header generation
        # Only include declarations from the source files being transformed (not system headers)
        all_nodes = []
        seen_declarations = set()  # Track (name, kind) to avoid duplicates
        source_files = set(str(Path(f).resolve()) for f in files)

        for file_path, document in results.items():
            # Extract class/struct/function nodes from all documents
            for node in document.root.walk():
                # Check for both lowercase and uppercase kind strings
                if node.kind.upper() in ['CLASS_DECL', 'STRUCT_DECL', 'FUNCTION_DECL']:
                    # Only include nodes that are defined in our source files
                    if hasattr(node, 'loc') and node.loc and hasattr(node.loc, 'file'):
                        node_file = str(Path(node.loc.file).resolve())
                        # Check if this node is from one of our source files
                        if node_file in source_files:
                            # Avoid duplicates
                            decl_key = (node.name, node.kind)
                            if decl_key not in seen_declarations:
                                seen_declarations.add(decl_key)
                                all_nodes.append(node)

        # Generate the primary header once
        if lang in ['cpp', 'c++', 'cxx', 'cc', 'c']:  # Only for C++ files
            # Generate primary header name from package name
            primary_header_name = f"{package_name}.h"

            # Generate primary header content
            header_content = transformer.generate_primary_header(all_nodes, primary_header_name)

            # Write the generated header to a file in the package directory
            header_path = Path(args.package) / primary_header_name
            with open(header_path, 'w') as f:
                f.write(header_content)

            print(f"Generated primary header: {header_path}")

        # Transform each document
        transformed_results = {}
        for file_path, document in results.items():
            print(f"Transforming {file_path}...")
            transformed_doc = transformer.transform_document(document)
            transformed_results[file_path] = transformed_doc

        # After generating the primary header, update .cpp files to use it
        for file_path in files:
            # Update the corresponding .cpp file to use only the primary header
            if file_path.endswith(('.cpp', '.cxx', '.cc', '.c++', '.c')):
                # Read the original file content (before transformation)
                with open(file_path, 'r') as f:
                    original_cpp_content = f.read()

                # Update includes
                updated_cpp_content = transformer.update_cpp_includes(original_cpp_content, f"{package_name}.h")

                # Write the updated content back
                with open(file_path, 'w') as f:
                    f.write(updated_cpp_content)

                print(f"Updated includes in: {file_path}")

        # Optionally rebuild the final TUs with symbols (commented out for now as it might fail)
        # This can be done separately after verifying the generated header is correct
        # final_results = builder.build_with_symbols(
        #     files=files,
        #     compile_flags=args.compile_flags or [],
        #     build_index=True,
        #     index_db_path='.maestro/tu/analysis/symbols.db'
        # )
        # print(f"Successfully built final translation units with symbols for {len(final_results)} files")

        print("Transformation completed successfully")
        return 0

    except Exception as e:
        print(f"Error during transformation: {e}")
        import traceback
        traceback.print_exc()
        return 1


def handle_tu_lsp_command(args):
    """Handle maestro tu lsp"""
    print("Starting Language Server Protocol server...")

    try:
        server = MaestroLSPServer()
        if args.port:
            # Run in TCP mode
            server.start_tcp(args.port)
        else:
            # Run in stdio mode
            server.start_io()

    except Exception as e:
        print(f"Error starting LSP server: {e}")
        return 1


def handle_tu_cache_clear_command(args):
    """Handle maestro tu cache clear [PACKAGE]"""
    cache_dir = Path('.maestro/tu/cache')

    if cache_dir.exists():
        import shutil
        try:
            shutil.rmtree(cache_dir)
            print(f"Cleared TU cache: {cache_dir}")
        except Exception as e:
            print(f"Error clearing cache: {e}")
            return 1
    else:
        print(f"Cache directory does not exist: {cache_dir}")


def handle_tu_cache_stats_command(args):
    """Handle maestro tu cache stats"""
    cache_dir = Path('.maestro/tu/cache')

    if not cache_dir.exists():
        print(f"Cache directory does not exist: {cache_dir}")
        return 1

    # Calculate cache statistics
    ast_files = list(cache_dir.rglob('*.ast'))
    total_size = sum(f.stat().st_size for f in ast_files)

    # Calculate cache hit rate (if we stored this info)
    # For now, just show total size and count
    print(f"Cache statistics:")
    print(f"  Files: {len(ast_files)}")
    print(f"  Total size: {total_size} bytes ({total_size / 1024 / 1024:.2f} MB)")


def handle_tu_print_ast_command(args):
    """Handle maestro tu print-ast <file>"""
    file_path = args.file

    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return 1

    print(f"Parsing and printing AST for: {file_path}")

    # Detect language
    try:
        lang = detect_language_from_path(file_path)
        print(f"Detected language: {lang}")
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    # Get the appropriate parser
    try:
        parser = get_parser_by_language(lang)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    try:
        # Parse the file
        document = parser.parse_file(file_path, compile_flags=args.compile_flags or [])

        # Create printer with options
        printer = ASTPrinter(
            show_types=not args.no_types,
            show_locations=not args.no_locations,
            show_values=not args.no_values,
            show_modifiers=not args.no_modifiers,
            max_depth=args.max_depth
        )

        # Print the AST
        output = printer.print_document(document)

        # Output to file or stdout
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"\nAST written to: {args.output}")
        else:
            print(output)

        return 0

    except Exception as e:
        print(f"Error parsing file: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        return 1


def add_tu_parser(subparsers):
    """Add TU command subparsers."""
    tu_parser = subparsers.add_parser('tu', help='Translation unit analysis and indexing')
    tu_subparsers = tu_parser.add_subparsers(dest='tu_subcommand', help='TU subcommands')

    # tu build
    build_parser = tu_subparsers.add_parser('build', help='Build translation unit for package')
    build_parser.add_argument('path', help='Path to source files', nargs='?', default='.')
    build_parser.add_argument('--force', action='store_true', help='Force rebuild (ignore cache)')
    build_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed progress')
    build_parser.add_argument('--output', '-o', default='.maestro/tu/cache', help='Output directory for TU (default: .maestro/tu/cache)')
    build_parser.add_argument('--threads', type=int, default=None, help='Parallel parsing threads (default: CPU count)')
    build_parser.add_argument('--lang', help='Language: cpp, java, kotlin (auto-detect if not specified)')
    build_parser.add_argument('--compile-flags', action='append', help='Compile flags for C/C++ parsing')

    # tu info
    info_parser = tu_subparsers.add_parser('info', help='Show translation unit information')
    info_parser.add_argument('path', help='Path to TU cache directory', nargs='?', default='.maestro/tu/cache')

    # tu query
    query_parser = tu_subparsers.add_parser('query', help='Query symbols in translation unit')
    query_parser.add_argument('path', help='Path to search in', nargs='?', default='.')
    query_parser.add_argument('--symbol', help='Symbol name to search')
    query_parser.add_argument('--file', help='Limit search to file')
    query_parser.add_argument('--kind', help='Filter by kind (function, class, etc.)')
    query_parser.add_argument('--json', action='store_true', help='JSON output')

    # tu complete
    complete_parser = tu_subparsers.add_parser('complete', help='Get auto-completion at location')
    complete_parser.add_argument('path', help='Path to source', nargs='?', default='.')
    complete_parser.add_argument('--file', required=True, help='Source file')
    complete_parser.add_argument('--line', type=int, required=True, help='Line number (1-based)')
    complete_parser.add_argument('--column', type=int, default=0, help='Column number (0-based)')
    complete_parser.add_argument('--json', action='store_true', help='JSON output')

    # tu references
    references_parser = tu_subparsers.add_parser('references', help='Find all references to symbol')
    references_parser.add_argument('path', help='Path to search', nargs='?', default='.')
    references_parser.add_argument('--symbol', required=True, help='Symbol name')
    references_parser.add_argument('--file', required=True, help='Symbol definition file')
    references_parser.add_argument('--line', type=int, required=True, help='Symbol definition line')
    references_parser.add_argument('--json', action='store_true', help='JSON output')

    # tu lsp
    lsp_parser = tu_subparsers.add_parser('lsp', help='Start Language Server Protocol server')
    lsp_parser.add_argument('--port', type=int, help='TCP port (default: stdio)')
    lsp_parser.add_argument('--log', help='Log file path')

    # tu cache
    cache_parser = tu_subparsers.add_parser('cache', help='TU cache management')
    cache_subparsers = cache_parser.add_subparsers(dest='cache_subcommand', help='Cache subcommands')

    cache_clear_parser = cache_subparsers.add_parser('clear', help='Clear TU cache for package')
    cache_clear_parser.add_argument('path', help='Package path', nargs='?', default='.')

    cache_stats_parser = cache_subparsers.add_parser('stats', help='Show cache statistics')

    # tu transform
    transform_parser = tu_subparsers.add_parser('transform', help='Transform code to follow conventions (e.g., U++)')
    transform_parser.add_argument('package', help='Package path to transform')
    transform_parser.add_argument('--to', required=True, help='Target convention (e.g., upp)')
    transform_parser.add_argument('--output', '-o', default='.maestro/tu/transform', help='Output directory for transformation results')
    transform_parser.add_argument('--lang', help='Language: cpp, java, kotlin (auto-detect if not specified)')
    transform_parser.add_argument('--compile-flags', action='append', help='Compile flags for C/C++ parsing')

    # tu print-ast
    print_ast_parser = tu_subparsers.add_parser('print-ast', help='Print AST for a source file')
    print_ast_parser.add_argument('file', help='Source file to parse and print AST')
    print_ast_parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    print_ast_parser.add_argument('--no-types', action='store_true', help='Hide type information')
    print_ast_parser.add_argument('--no-locations', action='store_true', help='Hide source locations')
    print_ast_parser.add_argument('--no-values', action='store_true', help='Hide constant values')
    print_ast_parser.add_argument('--no-modifiers', action='store_true', help='Hide modifiers (public, static, etc.)')
    print_ast_parser.add_argument('--max-depth', type=int, help='Maximum tree depth to print')
    print_ast_parser.add_argument('--compile-flags', action='append', help='Compile flags for C/C++ parsing')
    print_ast_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed error messages')


def handle_tu_command(args):
    """Main handler for the TU command."""
    if args.tu_subcommand == 'build':
        return handle_tu_build_command(args)
    elif args.tu_subcommand == 'info':
        return handle_tu_info_command(args)
    elif args.tu_subcommand == 'query':
        return handle_tu_query_command(args)
    elif args.tu_subcommand == 'complete':
        return handle_tu_complete_command(args)
    elif args.tu_subcommand == 'references':
        return handle_tu_references_command(args)
    elif args.tu_subcommand == 'lsp':
        return handle_tu_lsp_command(args)
    elif args.tu_subcommand == 'transform':
        return handle_tu_transform_command(args)
    elif args.tu_subcommand == 'print-ast':
        return handle_tu_print_ast_command(args)
    elif args.tu_subcommand == 'cache':
        if args.cache_subcommand == 'clear':
            return handle_tu_cache_clear_command(args)
        elif args.cache_subcommand == 'stats':
            return handle_tu_cache_stats_command(args)
        else:
            print("Usage: maestro tu cache [clear|stats]")
            return 1
    else:
        print("Usage: maestro tu [build|info|query|complete|references|lsp|transform|print-ast|cache]")
        return 1
"""
AST transformers for code transformation and convention enforcement.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set
from .ast_nodes import ASTDocument, ASTNode, SourceLocation
from .symbol_table import SymbolTable
import re


class ASTTransformer(ABC):
    """
    Base class for AST transformations.
    
    This class provides the foundation for transforming ASTs for purposes like
    code style enforcement, refactoring, or conversion between different conventions.
    """
    
    def __init__(self, preserve_locations: bool = True):
        """
        Initialize the transformer.
        
        Args:
            preserve_locations: Whether to preserve original source locations during transformation
        """
        self.preserve_locations = preserve_locations
        
    def transform_document(self, document: ASTDocument) -> ASTDocument:
        """
        Transform an entire AST document.
        
        Args:
            document: The AST document to transform
            
        Returns:
            The transformed AST document
        """
        # Transform the root node
        new_root = self.transform_node(document.root)
        
        # Return a new document with the transformed root
        return ASTDocument(root=new_root, symbols=document.symbols)
    
    def transform_node(self, node: ASTNode) -> ASTNode:
        """
        Transform a single AST node and recursively process its children.
        
        Args:
            node: The AST node to transform
            
        Returns:
            The transformed AST node
        """
        # Apply custom transformation to the current node
        transformed_node = self.transform_current_node(node)
        
        # Recursively transform children if they exist
        if transformed_node.children:
            transformed_children = [self.transform_node(child) for child in transformed_node.children]
            transformed_node.children = transformed_children
            
        return transformed_node
    
    @abstractmethod
    def transform_current_node(self, node: ASTNode) -> ASTNode:
        """
        Apply transformation specifically to the current node.
        
        Args:
            node: The current node to transform
            
        Returns:
            The transformed node
        """
        raise NotImplementedError("Subclasses must implement transform_current_node")


class UppConventionTransformer(ASTTransformer):
    """
    Transformer that enforces U++ conventions.
    
    This transformer implements U++ specific code organization rules:
    1. Topologically sorted declarations in header files
    2. Proper forward declarations for dependencies
    3. Correct include structure (primary header in .cpp files)
    """
    
    def __init__(self, package_name: str, preserve_locations: bool = True):
        super().__init__(preserve_locations=preserve_locations)
        self.package_name = package_name
        self.dependencies: Dict[str, Set[str]] = {}  # Maps symbol names to their dependencies
        self.declaration_order: List[str] = []       # Order in which symbols should be declared
        self.forward_declarations_needed: Set[str] = set()  # Types that need forward declarations
    
    def transform_document(self, document: ASTDocument) -> ASTDocument:
        """Transform document to enforce U++ conventions."""
        # First, build dependency information
        self._build_dependency_graph(document)
        
        # Compute correct declaration order (topological sort)
        self.declaration_order = self._compute_declaration_order()
        
        # Find which declarations need forward declarations
        self.forward_declarations_needed = self._find_forward_declarations()
        
        # Transform the AST nodes
        transformed_document = super().transform_document(document)
        
        return transformed_document
    
    def transform_current_node(self, node: ASTNode) -> ASTNode:
        """
        Apply U++ specific transformations to a single node.
        
        Args:
            node: The node to transform
            
        Returns:
            Transformed node
        """
        # For now, just return the node unchanged - the actual transformation
        # will happen at the document level to handle cross-file changes
        return node
    
    def _build_dependency_graph(self, document: ASTDocument):
        """Build a dependency graph from the AST document."""
        for node in document.root.walk():
            if node.kind in ('class_decl', 'struct_decl'):
                # Process class/struct dependencies
                self._process_class_dependencies(node)
            elif node.kind in ['function_decl', 'FUNCTION_DECL']:
                # Process function dependencies
                self._process_function_dependencies(node)
    
    def _process_class_dependencies(self, node: ASTNode):
        """Process dependencies for class declarations."""
        class_name = node.name
        deps = set()
        
        # Find dependencies in inheritance
        if node.children:
            for child in node.children:
                if child.kind == 'base_specifier':
                    deps.add(child.type)  # Add parent class as dependency
        
        # Find member variable dependencies
        for child in node.walk():  # Walk all descendants
            if child.kind in ('field_decl', 'var_decl') and child.type:
                # Don't add the class itself as a dependency
                if child.type != class_name:
                    deps.add(child.type)
        
        # Store dependencies for this class
        self.dependencies[class_name] = deps

    def _process_function_dependencies(self, node: ASTNode):
        """Process dependencies for function declarations."""
        func_name = node.name
        deps = set()
        
        # Find return type dependencies
        if node.type:
            deps.add(node.type)
            
        # Find parameter dependencies
        if node.children:
            for child in node.children:
                if child.kind == 'parm_var_decl' and child.type:
                    deps.add(child.type)
                    
        # Store dependencies for this function
        self.dependencies[func_name] = deps
    
    def _compute_declaration_order(self) -> List[str]:
        """
        Compute the correct declaration order using topological sorting.

        Returns:
            List of symbol names in dependency order
        """
        from collections import defaultdict, deque

        # Build adjacency list and in-degree count
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        # Initialize in-degrees for all nodes
        all_nodes = set()
        for node, deps in self.dependencies.items():
            all_nodes.add(node)
            for dep in deps:
                all_nodes.add(dep)

        for node in all_nodes:
            in_degree[node] = 0  # Initialize to 0

        # Build graph and compute in-degrees
        for node, deps in self.dependencies.items():
            for dep in deps:
                # node depends on dep, so edge goes dep -> node
                graph[dep].append(node)
                in_degree[node] += 1

        # Kahn's algorithm for topological sort
        queue = deque([node for node in all_nodes if in_degree[node] == 0])
        result = []

        while queue:
            current = queue.popleft()
            result.append(current)

            # Reduce in-degree of all neighbors
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycles - if we didn't visit all nodes, there's a cycle
        if len(result) != len(all_nodes):
            # Handle cycles by appending remaining nodes
            unprocessed = all_nodes - set(result)
            result.extend(list(unprocessed))

        return result
    
    def _find_forward_declarations(self) -> Set[str]:
        """
        Determine which types need forward declarations.

        Returns:
            Set of types that need forward declarations
        """
        needed = set()

        # Any type that's referenced but not yet declared in the current context
        # would need a forward declaration
        for node_name, deps in self.dependencies.items():
            for dep in deps:
                # If node_name needs dep but dep comes after node_name in the order,
                # we'll need a forward declaration for dep
                try:
                    node_idx = self.declaration_order.index(node_name)
                    dep_idx = self.declaration_order.index(dep)

                    # If dep comes after node_name in the order, we need a forward declaration
                    if dep_idx > node_idx:
                        needed.add(dep)
                except ValueError:
                    # Either node_name or dep is not in the declaration order
                    # This could happen if they're system types or not properly parsed
                    # We won't add them to forward declarations
                    continue

        return needed
    
    def generate_primary_header(self, symbols: List[ASTNode], primary_header_name: str) -> str:
        """
        Generate a primary header file with declarations in the correct order.

        Args:
            symbols: List of symbols to include in the header
            primary_header_name: Name of the primary header file (without path)

        Returns:
            Generated header content as a string
        """
        from .code_generator import CodeGenerator

        generator = CodeGenerator()
        header_content = []

        # Generate header guard name from the filename
        header_guard = primary_header_name.replace('.', '_').replace('-', '_').upper()

        # Add license/preamble comment if needed
        header_content.append(f"// Generated primary header for {self.package_name}")
        header_content.append(f"// Generated by Maestro TU6 - U++ Convention Enforcer")
        header_content.append(f"#ifndef {header_guard}")
        header_content.append(f"#define {header_guard}")
        header_content.append("")

        # Add system includes first
        header_content.append("// System includes")
        header_content.append("#include <memory>")
        header_content.append("#include <vector>")
        header_content.append("#include <string>")
        header_content.append("#include <iostream>")
        header_content.append("#include <stdexcept>")
        header_content.append("")

        # Add forward declarations if needed
        if self.forward_declarations_needed:
            header_content.append("// Forward declarations")
            for fwd_decl in sorted(self.forward_declarations_needed):
                # Clean up the type name for forward declaration
                clean_type = fwd_decl.rstrip('*& ').strip()
                # Only forward declare if it looks like a class/struct name (doesn't contain primitive types)
                if not any(primitive in clean_type.lower() for primitive in
                          ['int', 'float', 'double', 'char', 'bool', 'void', 'long', 'short', 'signed', 'unsigned']):
                    # Check if this is indeed a class/struct in our symbols
                    if any(node.name == clean_type and node.kind in ['class_decl', 'struct_decl'] for node in symbols):
                        header_content.append(f"class {clean_type};")
            header_content.append("")

        # Collect all declarations - include all valid symbols, not just those in declaration_order
        # This handles the case where simple functions might not be in the order due to no dependencies
        standalone_symbols = []

        for symbol in symbols:
            # Check for both lowercase and uppercase kind strings
            if symbol.kind.upper() in ['CLASS_DECL', 'STRUCT_DECL', 'FUNCTION_DECL']:
                # Skip main function
                if symbol.name == 'main':
                    continue
                standalone_symbols.append(symbol)

        # Sort symbols: first by whether they're in declaration_order, then alphabetically
        def sort_key(x):
            if x.name in self.declaration_order:
                return (0, self.declaration_order.index(x.name))
            else:
                return (1, x.name)

        standalone_symbols.sort(key=sort_key)

        if standalone_symbols:
            header_content.append("// Declarations in dependency order")
            for symbol in standalone_symbols:
                decl_code = generator.generate_declaration(symbol)
                header_content.append(decl_code)
                header_content.append("")  # Blank line between declarations

        # Close header guard
        header_content.append(f"#endif // {header_guard}")

        return "\n".join(header_content)
    
    def update_cpp_includes(self, cpp_content: str, primary_header_name: str) -> str:
        """
        Update a C++ file to include only the primary header.

        Args:
            cpp_content: Original C++ file content
            primary_header_name: Name of the primary header to include

        Returns:
            Updated C++ file content
        """
        import re

        # Split content into lines
        lines = cpp_content.split('\n')
        new_lines = []
        has_primary_include = False

        for line in lines:
            stripped_line = line.strip()

            if stripped_line.startswith('#include'):
                # Check if it's including a local header (not system)
                local_include_match = re.search(r'#include\s+"([^"]+)"', stripped_line)
                if local_include_match:
                    included_file = local_include_match.group(1)
                    # If this include is for our primary header, keep it
                    if included_file == primary_header_name:
                        new_lines.append(line)
                        has_primary_include = True
                    else:
                        # This is a different local header, skip it (will be in primary header now)
                        continue
                else:
                    # This is a system header or other include, keep it
                    new_lines.append(line)
            else:
                # Non-include line, keep it
                new_lines.append(line)

        # If the primary header isn't already included, add it after system includes
        if not has_primary_include:
            # Find the position after the last system include
            insert_position = 0
            for i, line in enumerate(new_lines):
                if line.strip().startswith('#include'):
                    if not re.search(r'#include\s+"', line):  # This is a system include like #include <...>
                        insert_position = i + 1
                    elif re.search(r'#include\s+"<[^>]+>"', line):  # This is a system include
                        insert_position = i + 1
                else:
                    break  # Stop once we reach non-include content

            primary_include_line = f'#include "{primary_header_name}"'
            new_lines.insert(insert_position, primary_include_line)

        return "\n".join(new_lines)


class CompositeTransformer(ASTTransformer):
    """
    Transformer that applies multiple transformations in sequence.
    """
    
    def __init__(self, transformers: List[ASTTransformer], preserve_locations: bool = True):
        super().__init__(preserve_locations=preserve_locations)
        self.transformers = transformers
        
    def transform_document(self, document: ASTDocument) -> ASTDocument:
        """Apply all transformers in sequence."""
        result = document
        for transformer in self.transformers:
            result = transformer.transform_document(result)
        return result
        
    def transform_current_node(self, node: ASTNode) -> ASTNode:
        """Apply transformations to the current node."""
        result = node
        for transformer in self.transformers:
            result = transformer.transform_current_node(result)
        return result
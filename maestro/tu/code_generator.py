"""
Code generator for converting AST back to source code.
"""
from typing import List, Optional
from .ast_nodes import ASTNode


class CodeGenerator:
    """
    Generates source code from AST nodes.
    
    Supports generation for different languages with basic formatting.
    """
    
    def __init__(self, indent_size: int = 4):
        self.indent_size = indent_size
        
    def generate_declaration(self, node: ASTNode) -> str:
        """
        Generate a declaration from an AST node.
        
        Args:
            node: AST node representing a declaration
            
        Returns:
            String representation of the declaration
        """
        # Check for both lowercase and uppercase kind strings
        kind_upper = node.kind.upper()
        if kind_upper in ['CLASS_DECL', 'STRUCT_DECL']:
            return self._generate_class_declaration(node)
        elif kind_upper in ['FUNCTION_DECL']:
            return self._generate_function_declaration(node)
        elif kind_upper == 'VAR_DECL':
            return self._generate_variable_declaration(node)
        else:
            # For unsupported node types, return a basic representation
            return f"// Unsupported node type: {node.kind}\n// {node.name}"
    
    def generate_definition(self, node: ASTNode) -> str:
        """
        Generate a full definition from an AST node.
        
        Args:
            node: AST node representing a definition
            
        Returns:
            String representation of the definition
        """
        if node.kind in ['class_decl', 'struct_decl']:
            return self._generate_class_definition(node)
        elif node.kind == 'function_decl':
            return self._generate_function_definition(node)
        else:
            return self.generate_declaration(node)  # Fallback to declaration
    
    def _generate_class_declaration(self, node: ASTNode) -> str:
        """
        Generate a class/struct declaration.

        Args:
            node: AST node representing a class/struct

        Returns:
            String representation of the class/struct declaration
        """
        # Get class/struct keyword
        keyword = 'class' if node.kind.upper() == 'CLASS_DECL' else 'struct'

        # Check for inheritance
        base_classes = []
        if node.children:
            for child in node.children:
                if child.kind.upper() == 'CXX_BASE_SPECIFIER':
                    # Get base class name
                    base_name = child.name if child.name else child.type
                    if base_name:
                        # Check access specifier for inheritance (public, private, protected)
                        # Default is public for struct, private for class
                        access = "public" if keyword == "struct" else "private"
                        # In libclang, the access is often in the type string
                        # For now, we'll default to public
                        base_classes.append(f"public {base_name}")

        # Start with the class/struct declaration
        if base_classes:
            lines = [f"{keyword} {node.name} : {', '.join(base_classes)} {{"]
        else:
            lines = [f"{keyword} {node.name} {{"]

        # Group members by access specifier
        # Track current access level and members
        current_access = None
        access_groups = {
            'public': [],
            'private': [],
            'protected': []
        }

        # Default access for class is private, for struct is public
        default_access = 'public' if keyword == 'struct' else 'private'
        current_access = default_access

        if node.children:
            for child in node.children:
                if child.kind.upper() == 'CXX_ACCESS_SPEC_DECL':
                    # Access specifier changes the current access level
                    # The name is empty, but we can infer from position
                    # Usually followed by members of that access level
                    # We need to track this by looking at the next members
                    # For now, we'll detect from the context
                    continue
                elif child.kind.upper() == 'CXX_BASE_SPECIFIER':
                    # Skip base specifiers (already handled)
                    continue
                else:
                    # This is a member - assign to current access level
                    # The access level tracking is complex in libclang
                    # We'll use a heuristic: check the child's position
                    # For simplicity, we'll put all members in their natural groups
                    access_groups[current_access].append(child)

        # Simplified approach: use libclang's access specifier information if available
        # For now, just organize by typical C++ pattern: public first, then private
        # We'll scan through and categorize members
        access_groups = {'public': [], 'private': [], 'protected': []}

        # In the original source code pattern for classes:
        # Usually: private members first (or after first access spec), then public
        # The CXX_ACCESS_SPEC_DECL nodes mark transitions but don't tell us TO what
        # Heuristic: constructor/destructor/public methods are usually public,
        # fields are usually private

        if node.children:
            for child in node.children:
                if child.kind.upper() in ['CXX_BASE_SPECIFIER', 'CXX_ACCESS_SPEC_DECL']:
                    continue

                kind_upper = child.kind.upper()

                # Heuristic-based access determination
                if kind_upper in ['CONSTRUCTOR', 'DESTRUCTOR', 'CXX_METHOD']:
                    # Methods, constructors, destructors are typically public
                    access_groups['public'].append(child)
                elif kind_upper == 'FIELD_DECL':
                    # Fields are typically private
                    access_groups['private'].append(child)
                else:
                    # Default to the class default
                    access_groups[default_access].append(child)

        # Generate members for each access level
        for access in ['public', 'private', 'protected']:
            if access_groups[access]:
                lines.append(f"{access}:")
                for member in access_groups[access]:
                    member_decl = self._generate_member_declaration(member)
                    if member_decl:  # Skip None returns
                        lines.append(f"    {member_decl}")
                lines.append("")  # Empty line after section

        # Close the class
        lines.append("};")

        return "\n".join(lines)
    
    def _generate_member_declaration(self, node: ASTNode) -> str:
        """
        Generate a declaration for a class member.

        Args:
            node: AST node representing a member

        Returns:
            String representation of the member declaration
        """
        kind_upper = node.kind.upper()

        if kind_upper == 'FIELD_DECL':
            # Field declaration: type name;
            if node.type and node.name:
                return f"{node.type} {node.name};"
            elif node.name:
                return f"{node.name};"
            else:
                return f"/* unknown field */;"

        elif kind_upper == 'CXX_METHOD':
            # Method declaration: return_type name(params) const;
            return self._generate_method_signature(node) + ";"

        elif kind_upper == 'CONSTRUCTOR':
            # Constructor: ClassName(params);
            return self._generate_constructor_signature(node) + ";"

        elif kind_upper == 'DESTRUCTOR':
            # Destructor: ~ClassName();
            return self._generate_destructor_signature(node) + ";"

        elif kind_upper == 'CXX_ACCESS_SPEC_DECL':
            # Access specifier - skip, handled separately
            return None

        elif kind_upper == 'CXX_BASE_SPECIFIER':
            # Base class specifier - skip, handled in class header
            return None

        elif kind_upper == 'FUNCTION_DECL':
            # Regular function (shouldn't be in class, but handle anyway)
            return self._generate_function_signature(node) + ";"

        else:
            return f"// Unsupported member type: {node.kind}"
    
    def _generate_function_declaration(self, node: ASTNode) -> str:
        """
        Generate a function declaration.
        
        Args:
            node: AST node representing a function
            
        Returns:
            String representation of the function declaration
        """
        return self._generate_function_signature(node) + ";"
    
    def _generate_function_signature(self, node: ASTNode) -> str:
        """
        Generate a function signature (return type + name + parameters).

        Args:
            node: AST node representing a function

        Returns:
            String representation of the function signature
        """
        # Determine return type from the type attribute
        # For functions, node.type contains the full function type like "int (int, int)"
        # We need to extract just the return type
        return_type = "void"
        if node.type:
            # Parse the function type to extract return type
            # Format is typically: "return_type (param_types)"
            import re
            match = re.match(r'^([^(]+)\s*\(', node.type)
            if match:
                return_type = match.group(1).strip()
            else:
                # If no parentheses, it might just be the return type
                return_type = node.type.strip()

        # Parameters
        params = []
        if node.children:
            for child in node.children:
                if child.kind.upper() in ['PARM_VAR_DECL', 'PARM_DECL']:
                    # Parameter: type name
                    param_str = child.type + " " + child.name if child.type and child.name else child.name or child.type or "/*param*/"
                    params.append(param_str)

        params_str = ", ".join(params) if params else "void"

        # Full signature
        return f"{return_type} {node.name}({params_str})"

    def _generate_method_signature(self, node: ASTNode) -> str:
        """
        Generate a method signature (like function but with const/override/virtual modifiers).

        Args:
            node: AST node representing a method

        Returns:
            String representation of the method signature
        """
        import re

        # Extract return type from method type
        return_type = "void"
        is_const = False
        is_virtual = False
        is_pure_virtual = False

        if node.type:
            # Method type format: "return_type (params) const"
            # First extract return type
            match = re.match(r'^([^(]+)\s*\(', node.type)
            if match:
                return_type = match.group(1).strip()
            else:
                return_type = node.type.strip()

            # Check for const
            if 'const' in node.type:
                is_const = True

        # Check for virtual/override in children
        if node.children:
            for child in node.children:
                if child.kind == 'CXX_OVERRIDE_ATTR':
                    # Method has override
                    pass  # We'll add "override" later
                # Pure virtual is indicated by lack of body and virtual keyword

        # Parameters
        params = []
        if node.children:
            for child in node.children:
                if child.kind.upper() in ['PARM_VAR_DECL', 'PARM_DECL']:
                    param_str = child.type + " " + child.name if child.type and child.name else child.name or child.type or "/*param*/"
                    params.append(param_str)

        params_str = ", ".join(params) if params else ""

        # Build signature
        signature = f"{return_type} {node.name}({params_str})"

        # Add const if needed
        if is_const:
            signature += " const"

        # Check for pure virtual (= 0) - this is tricky from AST
        # For now, we'll generate all methods as declarations only

        return signature

    def _generate_constructor_signature(self, node: ASTNode) -> str:
        """
        Generate a constructor signature.

        Args:
            node: AST node representing a constructor

        Returns:
            String representation of the constructor signature
        """
        # Constructor name is usually the class name
        # Parameters
        params = []
        if node.children:
            for child in node.children:
                if child.kind.upper() in ['PARM_VAR_DECL', 'PARM_DECL']:
                    param_str = child.type + " " + child.name if child.type and child.name else child.name or child.type or "/*param*/"
                    params.append(param_str)

        params_str = ", ".join(params) if params else ""

        return f"{node.name}({params_str})"

    def _generate_destructor_signature(self, node: ASTNode) -> str:
        """
        Generate a destructor signature.

        Args:
            node: AST node representing a destructor

        Returns:
            String representation of the destructor signature
        """
        # Destructor name already has ~
        # Check for virtual
        is_virtual = False
        if node.type and 'virtual' in node.type:
            is_virtual = True

        signature = f"{node.name}()"

        # Add noexcept if present
        if node.type and 'noexcept' in node.type:
            signature += " noexcept"

        return signature
    
    def _generate_variable_declaration(self, node: ASTNode) -> str:
        """
        Generate a variable declaration.
        
        Args:
            node: AST node representing a variable
            
        Returns:
            String representation of the variable declaration
        """
        if node.type and node.name:
            return f"{node.type} {node.name};"
        elif node.name:
            return f"{node.name};"
        else:
            return "/* unknown variable */;"
    
    def _generate_class_definition(self, node: ASTNode) -> str:
        """
        Generate a full class definition.
        
        Args:
            node: AST node representing a class
            
        Returns:
            String representation of the class definition
        """
        # For now, just return the declaration
        # In a more complete implementation, this would include method bodies
        return self._generate_class_declaration(node)
    
    def _generate_function_definition(self, node: ASTNode) -> str:
        """
        Generate a function definition with body.
        
        Args:
            node: AST node representing a function
            
        Returns:
            String representation of the function definition
        """
        # Signature
        signature = self._generate_function_signature(node)
        
        # For now, just add an empty body
        # In a more complete implementation, we would extract the function body from the AST
        return f"{signature} {{\n    // TODO: implement function body\n}}"
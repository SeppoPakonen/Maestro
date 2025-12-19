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
        if node.kind in ['class_decl', 'struct_decl']:
            return self._generate_class_declaration(node)
        elif node.kind == 'function_decl':
            return self._generate_function_declaration(node)
        elif node.kind == 'var_decl':
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
        keyword = 'class' if node.kind == 'class_decl' else 'struct'
        
        # Start with the class/struct declaration
        lines = [f"{keyword} {node.name} {{"] 
        
        # Group members by visibility (public, private, protected)
        public_members = []
        private_members = []
        protected_members = []
        other_members = []
        
        if node.children:
            for child in node.children:
                if child.kind == 'access_spec':
                    # This is where the access specifier starts
                    continue
                elif child.modifiers and 'public' in child.modifiers:
                    public_members.append(child)
                elif child.modifiers and 'private' in child.modifiers:
                    private_members.append(child)
                elif child.modifiers and 'protected' in child.modifiers:
                    protected_members.append(child)
                else:
                    other_members.append(child)  # Default to public for now
        
        # Add public members
        if public_members:
            lines.append("public:")
            for member in public_members:
                member_decl = self._generate_member_declaration(member)
                if member_decl:
                    lines.append(f"    {member_decl}")
            lines.append("")  # Empty line after section
        
        # Add private members
        if private_members:
            lines.append("private:")
            for member in private_members:
                member_decl = self._generate_member_declaration(member)
                if member_decl:
                    lines.append(f"    {member_decl}")
            lines.append("")  # Empty line after section
        
        # Add protected members
        if protected_members:
            lines.append("protected:")
            for member in protected_members:
                member_decl = self._generate_member_declaration(member)
                if member_decl:
                    lines.append(f"    {member_decl}")
            lines.append("")  # Empty line after section
        
        # Add members without explicit visibility
        if other_members:
            for member in other_members:
                member_decl = self._generate_member_declaration(member)
                if member_decl:
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
        if node.kind == 'field_decl':
            # Field declaration: type name;
            if node.type and node.name:
                return f"{node.type} {node.name};"
            elif node.name:
                return f"{node.name};"
            else:
                return f"/* unknown field */;"
        elif node.kind == 'function_decl':
            # Method declaration: return_type name(params);
            return self._generate_function_signature(node) + ";"
        elif node.kind in ['constructor', 'destructor']:
            # Constructor/destructor
            params_part = ""
            if node.children:
                # Extract parameters for constructor/destructor
                params = []
                for child in node.children:
                    if child.kind == 'parm_var_decl':
                        param_str = child.type + " " + child.name if child.type and child.name else child.name or child.type or "/*param*/"
                        params.append(param_str)
                params_part = "(" + ", ".join(params) + ")"
            else:
                params_part = "()"
            return f"{node.name}{params_part};"
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
        # Determine return type (could be in the 'type' attribute)
        return_type = node.type if node.type else "void"
        
        # Parameters
        params = []
        if node.children:
            for child in node.children:
                if child.kind == 'parm_var_decl':
                    # Parameter: type name
                    param_str = child.type + " " + child.name if child.type and child.name else child.name or child.type or "/*param*/"
                    params.append(param_str)
        
        params_str = ", ".join(params) if params else "void"
        
        # Full signature
        return f"{return_type} {node.name}({params_str})"
    
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
#!/usr/bin/env python3
"""
TU/AST Completion GUI Tester

A simple graphical interface for testing Maestro's TU/AST completion capabilities.
Features:
- Text editor with syntax highlighting
- Language selection (C++, Java)
- File operations (load/save)
- Completion triggering (Ctrl+Space or button)
- Fallback symbol extraction using regex heuristics

Usage: python tools/tu_completion_gui.py [file_path]
"""

import os
import sys
import re
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from pathlib import Path

# Add the project root to sys.path to import maestro
sys.path.insert(0, str(Path(__file__).parent.parent))

from maestro.tu.completion import CompletionProvider, CompletionItem
from maestro.tu.ast_nodes import ASTNode, ASTDocument, Symbol, SourceLocation
from maestro.tu.symbol_table import SymbolTable
from maestro.tu.clang_utils import get_default_compile_flags


class ClangCompletionAdapter:
    """
    Adapter for libclang-based completion functionality.
    Provides lazy initialization of clang and handles clang completion requests.
    """

    def __init__(self):
        self.clang_loaded = False
        self.libclang_available = False
        self.load_clang()

    def load_clang(self):
        """Load clang.cindex and set library path if LIBCLANG_PATH is provided."""
        try:
            import clang.cindex
            import os

            # Set the library path if provided
            libclang_path = os.environ.get("LIBCLANG_PATH")
            if libclang_path and os.path.exists(libclang_path):
                clang.cindex.Config.set_library_path(libclang_path)

            # Test basic functionality to ensure clang is working
            clang.cindex.Index.create()
            self.libclang_available = True
            self.clang_loaded = True
        except ImportError:
            print("Warning: libclang not available. Falling back to regex completion only.")
        except Exception as e:
            print(f"Warning: Failed to initialize libclang: {e}. Falling back to regex completion only.")

    def get_clang_completions(self, content: str, file_path: str, line: int, col: int,
                             prefix: str, language: str = "cpp") -> list:
        """
        Get completion results from libclang.

        Args:
            content: The buffer content to parse
            file_path: Path to the file (used for completion context)
            line: Line number (1-based) for completion request
            col: Column number (1-based) for completion request
            prefix: Prefix to filter results
            language: Language to determine appropriate flags

        Returns:
            List of CompletionItem objects from clang
        """
        if not self.libclang_available:
            return []

        try:
            import clang.cindex

            # Determine compile flags based on language
            flags = get_default_compile_flags(language)

            # Create a temporary file path for the buffer content
            temp_file_path = file_path

            # Parse the translation unit with the content
            index = clang.cindex.Index.create()

            # Parse with detailed processing and precompiled preamble for header visibility
            tu = index.parse(temp_file_path,
                           args=flags,
                           unsaved_files=[(temp_file_path, content)],
                           options=clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD |
                                   clang.cindex.TranslationUnit.PARSE_PRECOMPILED_PREAMBLE)

            # Request completions at the specified location
            completion_results = tu.codeComplete(
                temp_file_path,
                line,
                col,
                unsaved_files=[(temp_file_path, content)],
                include_macros=True,
                include_code_patterns=True,
                include_brief_comments=True
            )

            if completion_results is None:
                return []

            completions = []
            for result in completion_results.results:
                # Get the typed text (the text that will be inserted)
                typed_text = ""
                for chunk in result.string:
                    if chunk.isKindTypedText():
                        typed_text = chunk.spelling
                        break

                # Only include items that start with the prefix (unless prefix is empty)
                if prefix and not typed_text.lower().startswith(prefix.lower()):
                    continue

                # If no typed text found, use the first chunk as label
                if not typed_text:
                    for chunk in result.string:
                        if chunk.spelling:
                            typed_text = chunk.spelling
                            break

                if not typed_text:
                    continue

                # Build detail string from result string
                detail_parts = []
                for chunk in result.string:
                    if chunk.spelling:
                        detail_parts.append(chunk.spelling)

                detail = " ".join(detail_parts)

                # Create completion item
                completion_item = CompletionItem(
                    label=typed_text,
                    kind='clang',
                    detail=detail
                )

                completions.append(completion_item)

            return completions

        except Exception as e:
            print(f"Error getting clang completions: {e}")
            return []


class FallbackSymbolExtractor:
    """
    A fallback symbol extractor that parses source code using regex heuristics
    to extract symbols (functions, classes, variables) for completion purposes.
    
    Heuristics:
    - C++: Look for class declarations, function declarations, variable definitions
    - Java: Similar approach for classes, methods, fields
    - Uses regex patterns to identify language-specific constructs
    """
    
    def __init__(self, language="cpp"):
        self.language = language
        self.patterns = self._get_patterns(language)
        
    def _get_patterns(self, language):
        """Get regex patterns for symbol extraction based on language."""
        if language == "cpp":
            return {
                # Class declaration: class ClassName { ... } or class ClassName;
                'class': r'\bclass\s+(\w+)\s*(?:\{|;)',
                # Function declaration: returnType funcName(...) { ... }
                'function': r'\b(?:\w+::)*(\w+)\s*\([^;]*\)\s*[^\{]*\{',
                # Function pointer/declaration: returnType (*funcName)(...)
                'function_ptr': r'\b\w+\s*\(\*\s*(\w+)\s*\)\s*\([^)]*\)',
                # Variable declaration: type varName = value; or type varName;
                'variable': r'\b(?:[\w:<>]+\s+)+(\w+)\s*(?:[=;])',
                # Method declaration in class: returnType methodName(...);
                'method': r'\b(?:virtual|static)?\s*\w+(?:\s+\w+)?\s*(\w+)\s*\([^;]*\)\s*[;=]',
                # Struct declaration
                'struct': r'\bstruct\s+(\w+)\s*(?:\{|;)',
            }
        elif language == "java":
            return {
                # Class declaration
                'class': r'\b(?:public|private|protected)?\s*class\s+(\w+)',
                # Interface declaration
                'interface': r'\b(?:public|private|protected)?\s*interface\s+(\w+)',
                # Method declaration
                'method': r'\b(?:public|private|protected|static|final|abstract)+\s+\w+(?:\s+|\[\])+\w+\s+(\w+)\s*\([^)]*\)\s*[^\{]*\{?',
                # Field/variable declaration with improved capturing
                'field': r'\b(?:public|private|protected|static|final|transient|volatile|\s)+\s*[\w<>\[\]]+\s+(\w+)\s*(?:[=;,])',
            }
        else:
            return {}
    
    def extract_symbols(self, content, file_path):
        """Extract symbols from content using regex patterns."""
        symbols = []
        lines = content.split('\n')

        for i, line in enumerate(lines, 1):
            for kind_str, pattern in self.patterns.items():
                matches = re.finditer(pattern, line)
                for match in matches:
                    symbol_name = match.group(1) if len(match.groups()) >= 1 else None

                    if symbol_name and not symbol_name.startswith('_'):  # Skip private/internal symbols
                        # Calculate column position (1-based)
                        col_start = match.start(1) + 1

                        # Create source location (1-based line and column)
                        location = SourceLocation(
                            file=file_path,
                            line=i,
                            column=col_start
                        )

                        # Create symbol without using target for detail
                        symbol = Symbol(
                            name=symbol_name,
                            kind=kind_str,
                            loc=location
                        )
                        symbols.append(symbol)

        return symbols


class SyntaxHighlighter:
    """Simple syntax highlighter for C++ and Java using regex."""
    
    def __init__(self, text_widget, language="cpp"):
        self.text_widget = text_widget
        self.language = language
        self.setup_tags()
    
    def setup_tags(self):
        """Configure text tags for syntax highlighting."""
        # Define colors for different elements
        self.text_widget.tag_configure("keyword", foreground="#FF0000", font=("Consolas", 10, "bold"))
        self.text_widget.tag_configure("comment", foreground="#008000")
        self.text_widget.tag_configure("string", foreground="#800080")
        self.text_widget.tag_configure("type", foreground="#0000FF")
        self.text_widget.tag_configure("identifier", foreground="#000000")
        
    def highlight(self):
        """Apply syntax highlighting to the text widget content."""
        # Clear existing tags
        for tag in ["keyword", "comment", "string", "type", "identifier"]:
            self.text_widget.tag_remove(tag, "1.0", tk.END)
            
        content = self.text_widget.get("1.0", tk.END)
        lines = content.split('\n')
        
        # Define keywords and types for each language
        keywords = {
            "cpp": [
                "auto", "break", "case", "char", "const", "continue", "default", "do", "double",
                "else", "enum", "extern", "float", "for", "goto", "if", "int", "long", "register",
                "return", "short", "signed", "sizeof", "static", "struct", "switch", "typedef",
                "union", "unsigned", "void", "volatile", "while", "bool", "true", "false", "nullptr",
                "class", "delete", "explicit", "friend", "inline", "mutable", "new", "operator",
                "private", "protected", "public", "template", "this", "throw", "try", "catch", "using",
                "namespace", "virtual", "override", "final", "constexpr", "decltype"
            ],
            "java": [
                "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class",
                "const", "continue", "default", "do", "double", "else", "enum", "extends", "final",
                "finally", "float", "for", "goto", "if", "implements", "import", "instanceof", "int",
                "interface", "long", "native", "new", "package", "private", "protected", "public",
                "return", "short", "static", "strictfp", "super", "switch", "synchronized", "this",
                "throw", "throws", "transient", "try", "void", "volatile", "while", "true", "false", "null"
            ]
        }
        
        types = {
            "cpp": [
                "void", "bool", "char", "int", "float", "double", "short", "long", "unsigned", "signed",
                "wchar_t", "size_t", "ptrdiff_t", "nullptr_t"
            ],
            "java": [
                "void", "boolean", "char", "byte", "short", "int", "long", "float", "double", "String"
            ]
        }
        
        lang_keywords = set(keywords.get(self.language, []))
        lang_types = set(types.get(self.language, []))
        
        start_line = 1
        for line_num, line in enumerate(lines, start_line):
            line_start = f"{line_num}.0"
            line_end = f"{line_num}.end"
            
            # Highlight comments
            if self.language == "cpp":
                # Single-line comments // ...
                comment_match = re.search(r'//.*$', line)
                if comment_match:
                    start_col = comment_match.start()
                    end_col = comment_match.end()
                    self.text_widget.tag_add("comment", f"{line_num}.{start_col}", f"{line_num}.{end_col}")
                
                # Multi-line comments /* ... */
                ml_comment_matches = list(re.finditer(r'/\*.*?\*/', line))
                for match in ml_comment_matches:
                    start_col = match.start()
                    end_col = match.end()
                    self.text_widget.tag_add("comment", f"{line_num}.{start_col}", f"{line_num}.{end_col}")
            elif self.language == "java":
                # Single-line comments // ...
                comment_match = re.search(r'//.*$', line)
                if comment_match:
                    start_col = comment_match.start()
                    end_col = comment_match.end()
                    self.text_widget.tag_add("comment", f"{line_num}.{start_col}", f"{line_num}.{end_col}")
                
                # Multi-line comments /* ... */
                ml_comment_matches = list(re.finditer(r'/\*.*?\*/', line))
                for match in ml_comment_matches:
                    start_col = match.start()
                    end_col = match.end()
                    self.text_widget.tag_add("comment", f"{line_num}.{start_col}", f"{line_num}.{end_col}")
            
            # Highlight strings
            for string_match in re.finditer(r'"([^"]|"")*"', line):
                start_col = string_match.start()
                end_col = string_match.end()
                self.text_widget.tag_add("string", f"{line_num}.{start_col}", f"{line_num}.{end_col}")
            
            # Highlight keywords and types
            for word_match in re.finditer(r'\b\w+\b', line):
                word_start, word_end = word_match.span()
                word = word_match.group()
                
                # Check if it's a keyword
                if word in lang_keywords:
                    self.text_widget.tag_add("keyword", f"{line_num}.{word_start}", f"{line_num}.{word_end}")
                # Check if it's a type
                elif word in lang_types:
                    self.text_widget.tag_add("type", f"{line_num}.{word_start}", f"{line_num}.{word_end}")


class TUCompletionGUI:
    """Main GUI class for TU/AST completion testing."""
    
    def __init__(self, root, initial_file=None):
        self.root = root
        self.current_file = initial_file
        self.language = tk.StringVar(value="cpp")  # Default to C++
        self.setup_ui()
        self.symbol_extractor = None
        self.completion_provider = None
        self.clang_adapter = ClangCompletionAdapter()

        if initial_file:
            self.load_file(initial_file)
    
    def setup_ui(self):
        """Set up the main UI components."""
        self.root.title("TU/AST Completion GUI")
        self.root.geometry("1000x700")
        
        # Top frame for controls
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # File controls
        file_btn = ttk.Button(top_frame, text="Load File", command=self.load_file_dialog)
        file_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        save_btn = ttk.Button(top_frame, text="Save File", command=self.save_file_dialog)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Language selection
        ttk.Label(top_frame, text="Language:").pack(side=tk.LEFT, padx=(10, 5))
        lang_combo = ttk.Combobox(top_frame, textvariable=self.language, values=["cpp", "java"])
        lang_combo.pack(side=tk.LEFT, padx=(0, 10))
        lang_combo.bind('<<ComboboxSelected>>', self.on_language_change)
        
        # Completion button
        completion_btn = ttk.Button(top_frame, text="Complete", command=self.trigger_completion)
        completion_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Text editor area with scrollbar
        text_frame = ttk.Frame(self.root)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, undo=True)
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind Ctrl+Space to trigger completion
        self.root.bind('<Control-space>', lambda e: self.trigger_completion())
        
        # Initialize syntax highlighter
        self.highlighter = SyntaxHighlighter(self.text_widget, self.language.get())
        self.text_widget.bind('<KeyRelease>', self.on_text_change)
        
        # Completion listbox (initially hidden)
        self.completion_list = tk.Listbox(self.root, height=10, width=40)
        self.completion_list.bind('<Double-Button-1>', self.select_completion)
        self.completion_list.bind('<Return>', self.select_completion)
        self.completion_list.bind('<Escape>', self.hide_completion_list)

    def _extract_prefix(self, line_text: str, col: int) -> str:
        """
        Extract identifier prefix ending at the given column (Tk columns are 0-based).
        Returns an empty string if nothing identifier-like is to the left.
        """
        if not line_text or col <= 0:
            return ""
        idx = min(col - 1, len(line_text) - 1)
        chars = []
        while idx >= 0:
            ch = line_text[idx]
            if ch.isalnum() or ch == '_':
                chars.append(ch)
                idx -= 1
            else:
                break
        return "".join(reversed(chars))
        
    def on_text_change(self, event=None):
        """Trigger syntax highlighting on text change."""
        self.highlighter.highlight()
    
    def on_language_change(self, event):
        """Update syntax highlighter when language changes."""
        self.highlighter.language = self.language.get()
        self.highlighter.setup_tags()  # Reset tags
        self.highlighter.highlight()  # Reapply highlights
    
    def load_file_dialog(self):
        """Open file dialog to load a file."""
        file_path = filedialog.askopenfilename(
            title="Select source file",
            filetypes=[("Source files", "*.cpp *.h *.hpp *.cc *.cxx *.java"), ("All files", "*.*")]
        )
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path):
        """Load content from a file into the text editor."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(1.0, content)
            self.highlighter.highlight()
            self.current_file = file_path
            self.root.title(f"TU/AST Completion GUI - {os.path.basename(file_path)}")
            self.status_var.set(f"Loaded: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load file: {str(e)}")
    
    def save_file_dialog(self):
        """Open file dialog to save a file."""
        if self.current_file:
            file_path = self.current_file
        else:
            file_path = filedialog.asksaveasfilename(
                title="Save source file",
                defaultextension=".cpp",
                filetypes=[("C++ files", "*.cpp *.h *.hpp *.cc *.cxx"), ("Java files", "*.java"), ("All files", "*.*")]
            )
            if not file_path:
                return
        
        if file_path:
            self.save_file(file_path)
    
    def save_file(self, file_path):
        """Save content from the text editor to a file."""
        try:
            content = self.text_widget.get(1.0, tk.END + '-1c')  # Exclude the final newline
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.current_file = file_path
            self.root.title(f"TU/AST Completion GUI - {os.path.basename(file_path)}")
            self.status_var.set(f"Saved: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file: {str(e)}")
    
    def trigger_completion(self):
        """Trigger completion with language-specific logic."""
        try:
            # Get current content and cursor position
            content = self.text_widget.get("1.0", tk.END + "-1c")
            cursor_pos = self.text_widget.index(tk.INSERT)
            line, col = map(int, cursor_pos.split('.'))

            # Determine file path (use current file or create a temporary one)
            file_path = self.current_file or f"/tmp/current_buffer.{self.language.get()}"

            # Extract prefix at cursor - safely walk backward allowing empty prefix
            current_line = self.text_widget.get(f"{line}.0", f"{line}.end")
            prefix = self._extract_prefix(current_line, col)

            # Determine language-specific completion logic
            language = self.language.get()

            clang_completions = []
            fallback_completions = []

            if language == "cpp":
                # For C++, try clang completion first then fall back to regex
                clang_completions = self.clang_adapter.get_clang_completions(
                    content, file_path, line, col, prefix, language
                )

                if not clang_completions:
                    self.status_var.set("Clang completion failed, falling back to regex...")
                    fallback_completions = self._get_fallback_completions(content, file_path, line, col, prefix)
                else:
                    # Also get fallback completions to merge with clang results
                    fallback_completions = self._get_fallback_completions(content, file_path, line, col, prefix)

                    # Merge completions: clang first, then fallback (avoiding duplicates)
                    all_completions = []
                    seen_labels = set()

                    for comp in clang_completions:
                        all_completions.append(comp)
                        seen_labels.add(comp.label)

                    for comp in fallback_completions:
                        if comp.label not in seen_labels:
                            all_completions.append(comp)
                            seen_labels.add(comp.label)

                    completions = all_completions

            elif language == "java":
                # For Java, just use fallback
                completions = self._get_fallback_completions(content, file_path, line, col, prefix)
            else:
                # For any other language, use fallback
                completions = self._get_fallback_completions(content, file_path, line, col, prefix)

            # Show completions
            if completions:
                self.show_completions(completions, prefix, line, col)
                self.status_var.set(f"Found {len(completions)} completions for '{prefix}'")
            else:
                self.status_var.set(f"No completions found for '{prefix}' (language: {language})")

        except Exception as e:
            self.status_var.set(f"Completion failed: {str(e)}")

    def _get_fallback_completions(self, content: str, file_path: str, line: int, col: int, prefix: str):
        """Get completions using the fallback symbol extractor."""
        # Initialize symbol extractor
        self.symbol_extractor = FallbackSymbolExtractor(self.language.get())
        extracted_symbols = self.symbol_extractor.extract_symbols(content, file_path)

        # Build a minimal AST document for the current buffer
        root_loc = SourceLocation(file=file_path, line=1, column=1)
        root_node = ASTNode(
            kind="TranslationUnit",
            name=os.path.basename(file_path) or "<buffer>",
            loc=root_loc,
            children=[]
        )
        ast_doc = ASTDocument(root=root_node, symbols=extracted_symbols)

        # Create symbol table and add document with extracted symbols
        symbol_table = SymbolTable()
        symbol_table.add_document(ast_doc)

        # Initialize completion provider with symbol table and documents
        documents = {file_path: ast_doc}
        self.completion_provider = CompletionProvider(symbol_table, documents, use_clang_completion=False)

        # Get completions using the internal method
        completions = self.completion_provider.get_completion_items(
            file_path=file_path,
            line=line,
            column=col,
            prefix=prefix
        )
        return completions
    
    def show_completions(self, completions, prefix, line, col):
        """Display completions in a listbox near the cursor."""
        # Clear previous completions
        self.completion_list.delete(0, tk.END)

        # Store completions for later retrieval when one is selected
        self.current_completions = completions

        # Add completions to listbox
        for comp in completions:
            loc = getattr(comp, "location", None)
            loc_file = os.path.basename(loc.file) if loc else ""

            # For clang completion results, show more descriptive detail
            if comp.kind == "clang":
                detail = comp.detail or loc_file
                detail_text = f" - {detail}" if detail else ""
            else:
                # For symbol table completions, use file location
                detail = comp.detail or loc_file
                detail_text = f" - {detail}" if detail else ""

            display_text = f"{comp.label} ({comp.kind}){detail_text}"
            self.completion_list.insert(tk.END, display_text)

        # Position the listbox near the cursor
        text_coords = self.text_widget.bbox(f"{line}.{col}")
        if text_coords:
            x, y, width, height = text_coords
            # Convert text widget coordinates to window coordinates
            text_x = self.text_widget.winfo_rootx() + x
            text_y = self.text_widget.winfo_rooty() + y + height

            # Position the listbox
            self.completion_list.place(x=text_x, y=text_y)
            self.completion_list.lift()
            self.completion_list.focus_set()

            # Select the first item
            if self.completion_list.size() > 0:
                self.completion_list.selection_set(0)

        # Bind escape key to hide
        self.root.bind('<Escape>', self.hide_completion_list)
    
    def hide_completion_list(self, event=None):
        """Hide the completion listbox."""
        self.completion_list.place_forget()
        self.text_widget.focus_set()
    
    def select_completion(self, event):
        """Insert selected completion at cursor position."""
        # Get selected index
        selection = self.completion_list.curselection()
        if not selection:
            self.hide_completion_list()
            return

        index = selection[0]
        # For simplicity, get the prefix again - safely walk backward
        cursor_pos = self.text_widget.index(tk.INSERT)
        line, col = map(int, cursor_pos.split('.'))
        current_line = self.text_widget.get(f"{line}.0", f"{line}.end")

        # Find the prefix
        prefix = self._extract_prefix(current_line, col)

        # Remove prefix from text
        new_col = col - len(prefix)
        self.text_widget.delete(f"{line}.{new_col}", f"{line}.{col}")

        # Insert selected completion
        # Use the actual completion item stored
        if 0 <= index < len(self.current_completions):
            completion_item = self.current_completions[index]
            # Use insert_text if available, otherwise use label
            insert_text = getattr(completion_item, 'insert_text', None) or completion_item.label
            self.text_widget.insert(f"{line}.{new_col}", insert_text)

        # Hide the listbox
        self.hide_completion_list()


def main():
    """Main entry point for the application."""
    import argparse

    parser = argparse.ArgumentParser(description="TU/AST Completion GUI Tester")
    parser.add_argument("file", nargs="?", help="Optional file to load initially")
    args = parser.parse_args()

    root = tk.Tk()
    app = TUCompletionGUI(root, initial_file=args.file)
    root.mainloop()


if __name__ == "__main__":
    main()

"""
Stub LSP server for Maestro that integrates with TU modules.
Provides basic LSP capabilities using in-process calls.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import socket
import selectors
from typing import List, Optional, Dict, Any
from pathlib import Path
from .ast_nodes import ASTDocument, SourceLocation, Symbol
from .symbol_table import SymbolTable
from .symbol_resolver import SymbolResolver
from .completion import CompletionProvider
from .tu_builder import TUBuilder


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MaestroLSPServer:
    """
    A stub LSP server that provides basic language server functionality
    using in-process calls to TU modules.
    """
    
    def __init__(self, tu_builder: TUBuilder):
        """
        Initialize the LSP server.

        Args:
            tu_builder: TUBuilder instance to use for building translation units
        """
        self.tu_builder = tu_builder
        self.symbol_table = SymbolTable()
        self.documents: Dict[str, ASTDocument] = {}
        self.completion_provider: Optional[CompletionProvider] = None
        self.tcp_server_socket = None
        self.tcp_selector = selectors.DefaultSelector()
        self.client_connections = {}
        self.session_registry = {}

        # Buffer for receiving data from clients
        self.recv_buffers = {}
        # Buffer for sending data to clients
        self.send_buffers = {}
    
    def reload_documents(self, files: List[str], compile_flags: Optional[List[str]] = None) -> None:
        """
        Reload documents using the TUBuilder.
        
        Args:
            files: List of file paths to reload
            compile_flags: Optional compilation flags
        """
        # Build documents with symbol resolution
        self.documents = self.tu_builder.build_with_symbols(
            files, 
            compile_flags=compile_flags
        )
        
        # Rebuild symbol table
        self.symbol_table = SymbolTable()
        for doc in self.documents.values():
            self.symbol_table.add_document(doc)
        
        # Create/update completion provider
        self.completion_provider = CompletionProvider(self.symbol_table, self.documents)
    
    def get_definition(self, file: str, line: int, column: int) -> Optional[SourceLocation]:
        """
        Get the definition location for the symbol at the given position.
        
        Args:
            file: File path
            line: Line number (1-based)
            column: Column number (1-based)
            
        Returns:
            SourceLocation of the definition or None if not found
        """
        abs_file_path = str(Path(file).resolve())
        
        # Get the document for the given file
        doc = self.documents.get(abs_file_path)
        if not doc:
            return None
        
        # Find the symbol at the given position
        target_symbol = self._find_symbol_at_position(doc, line, column)
        if not target_symbol or not target_symbol.target:
            return None
        
        # Look up the target symbol in the symbol table
        target_symbol_obj = self.symbol_table.get_symbol_by_id(target_symbol.target)
        if not target_symbol_obj:
            return None
        
        return target_symbol_obj.loc
    
    def get_references(self, file: str, line: int, column: int) -> List[SourceLocation]:
        """
        Get all reference locations for the symbol at the given position.
        
        Args:
            file: File path
            line: Line number (1-based)
            column: Column number (1-based)
            
        Returns:
            List of SourceLocation objects representing reference positions
        """
        abs_file_path = str(Path(file).resolve())
        
        # Find the symbol at the given position
        doc = self.documents.get(abs_file_path)
        if not doc:
            return []
        
        target_symbol = self._find_symbol_at_position(doc, line, column)
        if not target_symbol:
            return []
        
        # Get the symbol ID that this symbol refers to
        symbol_id = None
        if target_symbol.target:
            symbol_id = target_symbol.target
        elif target_symbol.refers_to:
            symbol_id = target_symbol.refers_to
        else:
            # If it's a definition, use its own symbol ID
            symbol_id = self.symbol_table.make_symbol_id(target_symbol)
        
        # If we have a symbol ID, find all references to it
        if not symbol_id:
            return []
        
        # Find all symbols that refer to this symbol ID
        references = []
        for doc_path, doc in self.documents.items():
            for symbol in doc.symbols:
                if (symbol.refers_to == symbol_id) or (symbol.target == symbol_id) or self.symbol_table.make_symbol_id(symbol) == symbol_id:
                    references.append(symbol.loc)
        
        return references
    
    def get_completions(self, file: str, line: int, column: int, 
                       prefix: Optional[str] = None, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Get completion suggestions for the given position.
        
        Args:
            file: File path
            line: Line number (1-based)
            column: Column number (1-based)
            prefix: Optional prefix to filter results
            max_results: Maximum number of results to return
            
        Returns:
            List of completion items as dictionaries
        """
        if not self.completion_provider:
            return []
        
        completion_items = self.completion_provider.get_completion_items(
            file, line, column, prefix, max_results
        )
        
        # Convert to dictionaries for easy serialization
        result = []
        for item in completion_items:
            result.append({
                'label': item.label,
                'kind': item.kind,
                'detail': item.detail,
                'documentation': item.documentation,
                'insert_text': item.insert_text
            })
        
        return result
    
    def _find_symbol_at_position(self, doc: ASTDocument, line: int, column: int) -> Optional[Symbol]:
        """
        Find the symbol at the given position in the document.

        Args:
            doc: ASTDocument to search
            line: Line number (1-based)
            column: Column number (1-based)

        Returns:
            Symbol object or None if not found
        """
        # Search for symbols near the given position
        for symbol in doc.symbols:
            if (symbol.loc.line == line and
                symbol.loc.column <= column <= symbol.loc.column + len(symbol.name)):
                return symbol

        # Also check if the position is near the beginning of a symbol name
        for symbol in doc.symbols:
            if symbol.loc.line == line:
                # Consider symbols that start a bit before the cursor position
                if abs(symbol.loc.column - column) <= len(symbol.name):
                    # Check if cursor is within or right after the symbol name
                    end_column = symbol.loc.column + len(symbol.name)
                    if symbol.loc.column <= column <= end_column:
                        return symbol

        return None

    def start_tcp(self, port: int) -> None:
        """
        Start the TCP server on the specified port.

        Args:
            port: Port number to listen on
        """
        logger.info(f"Starting TCP server on port {port}")

        # Create TCP server socket
        self.tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_server_socket.bind(('localhost', port))
        self.tcp_server_socket.listen()
        self.tcp_server_socket.setblocking(False)

        # Register server socket with selector
        self.tcp_selector.register(self.tcp_server_socket, selectors.EVENT_READ, data=None)

        logger.info(f"TCP server listening on localhost:{port}")

        try:
            while True:
                events = self.tcp_selector.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        # Accept new connection
                        self._accept_connection(key.fileobj)
                    else:
                        # Handle client data
                        self._service_connection(key, mask)
        except KeyboardInterrupt:
            print("Caught keyboard interrupt. Exiting...")
        finally:
            self.tcp_selector.close()
            if self.tcp_server_socket:
                self.tcp_server_socket.close()

    def _accept_connection(self, server_socket):
        """Accept a new client connection."""
        conn, addr = server_socket.accept()
        logger.info(f"Accepted connection from {addr}")
        conn.setblocking(False)

        # Register new connection with selector
        self.tcp_selector.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, data=addr)

        # Initialize buffers for this connection
        self.recv_buffers[conn] = b""
        self.send_buffers[conn] = b""

        # Generate a unique session ID for this connection
        import uuid
        session_id = str(uuid.uuid4())
        self.session_registry[addr] = session_id
        logger.info(f"Assigned session ID {session_id} to connection {addr}")

    def _service_connection(self, key, mask):
        """Service a client connection."""
        sock = key.fileobj

        if mask & selectors.EVENT_READ:
            # Receive data from client
            recv_data = sock.recv(1024)
            if recv_data:
                self.recv_buffers[sock] += recv_data

                # Process complete messages (newline delimited)
                while b'\n' in self.recv_buffers[sock]:
                    message, self.recv_buffers[sock] = self.recv_buffers[sock].split(b'\n', 1)
                    try:
                        decoded_message = message.decode('utf-8')
                        parsed_message = json.loads(decoded_message)

                        # Route message based on session
                        response = self._handle_message(parsed_message)

                        # Send response back to client
                        if response:
                            response_bytes = (json.dumps(response) + '\n').encode('utf-8')
                            self.send_buffers[sock] += response_bytes
                    except json.JSONDecodeError:
                        # Send error message to client
                        error_msg = {
                            "type": "error",
                            "data": {
                                "error_code": "INVALID_JSON",
                                "message": "Invalid JSON received"
                            }
                        }
                        response_bytes = (json.dumps(error_msg) + '\n').encode('utf-8')
                        self.send_buffers[sock] += response_bytes
                    except Exception as e:
                        # Send error message to client
                        error_msg = {
                            "type": "error",
                            "data": {
                                "error_code": "INTERNAL_ERROR",
                                "message": f"Internal error: {str(e)}"
                            }
                        }
                        response_bytes = (json.dumps(error_msg) + '\n').encode('utf-8')
                        self.send_buffers[sock] += response_bytes
            else:
                # Client disconnected
                logger.info(f"Client {key.data} disconnected")
                self._close_connection(sock)

        if mask & selectors.EVENT_WRITE and self.send_buffers[sock]:
            # Send buffered data to client
            sent = sock.send(self.send_buffers[sock])
            self.send_buffers[sock] = self.send_buffers[sock][sent:]

    def _handle_message(self, message: dict):
        """Handle an incoming message and produce a response."""
        msg_type = message.get('type', '')
        session_id = message.get('session_id', '')

        # Validate session ID
        if not session_id:
            # For initial handshake, session_id might not be provided yet
            if msg_type == 'session_start':
                import uuid
                session_id = str(uuid.uuid4())
                message['session_id'] = session_id
                # Store session mapping
                client_addr = None
                for addr, sid in self.session_registry.items():
                    if sid == session_id:
                        client_addr = addr
                        break
                if client_addr:
                    self.session_registry[client_addr] = session_id
            else:
                # Return error for messages without session_id
                return {
                    "type": "error",
                    "data": {
                        "error_code": "MISSING_SESSION_ID",
                        "message": "Session ID is required for this message type"
                    }
                }

        # Route based on message type
        if msg_type == 'session_start':
            # Handle session start
            return {
                "type": "session_confirmation",
                "session_id": session_id,
                "data": {
                    "status": "active",
                    "connection_time": "2025-01-10T12:00:00.000Z"
                }
            }
        elif msg_type == 'session_end':
            # Handle session end
            return {
                "type": "session_closed",
                "session_id": session_id,
                "data": {
                    "status": "closed"
                }
            }
        elif msg_type.startswith('tool_'):
            # Handle tool events
            # This would route to appropriate handler based on the specific tool type
            return self._handle_tool_event(message)
        elif msg_type.startswith('message_') or msg_type.startswith('content_block_'):
            # Handle LLM stream events
            # For now, just acknowledge receipt
            return {
                "type": "ack",
                "session_id": session_id,
                "correlation_id": message.get('correlation_id'),
                "data": {
                    "status": "received"
                }
            }
        else:
            # Unknown message type
            return {
                "type": "error",
                "session_id": session_id,
                "data": {
                    "error_code": "UNKNOWN_MESSAGE_TYPE",
                    "message": f"Unknown message type: {msg_type}"
                }
            }

    def _handle_tool_event(self, message: dict):
        """Handle tool-related events."""
        msg_type = message.get('type', '')

        if msg_type == 'tool_call_request':
            # Process tool call request
            call_id = message.get('data', {}).get('call_id')
            tool_name = message.get('data', {}).get('name')
            tool_args = message.get('data', {}).get('args', {})

            # For now, simulate tool execution
            result = self._execute_tool(tool_name, tool_args)

            # Return tool response
            return {
                "type": "tool_call_response",
                "session_id": message.get('session_id'),
                "correlation_id": message.get('correlation_id'),
                "data": {
                    "call_id": call_id,
                    "result": result,
                    "error": None,
                    "execution_time_ms": 10
                }
            }
        elif msg_type == 'tool_call_confirmation':
            # Handle tool confirmation request
            return {
                "type": "tool_confirmation_response",
                "session_id": message.get('session_id'),
                "correlation_id": message.get('correlation_id'),
                "data": {
                    "confirmed": True,
                    "message": "Action confirmed by user"
                }
            }
        else:
            # Other tool event types
            return {
                "type": "ack",
                "session_id": message.get('session_id'),
                "correlation_id": message.get('correlation_id'),
                "data": {
                    "status": "processed"
                }
            }

    def _execute_tool(self, tool_name: str, tool_args: dict):
        """Execute a tool with given arguments."""
        # Placeholder implementation for tool execution
        if tool_name == 'read_file':
            file_path = tool_args.get('file_path')
            if file_path:
                try:
                    with open(file_path, 'r') as f:
                        return f.read()
                except Exception as e:
                    return f"Error reading file: {str(e)}"
            else:
                return "Missing file_path argument"
        elif tool_name == 'write_file':
            file_path = tool_args.get('file_path')
            content = tool_args.get('content')
            if file_path and content is not None:
                try:
                    with open(file_path, 'w') as f:
                        f.write(content)
                        return f"Successfully wrote to {file_path}"
                except Exception as e:
                    return f"Error writing file: {str(e)}"
            else:
                return "Missing file_path or content argument"
        elif tool_name == 'list_files':
            import os
            directory = tool_args.get('directory', '.')
            try:
                files = os.listdir(directory)
                return files
            except Exception as e:
                return f"Error listing directory: {str(e)}"
        else:
            # Default case for unknown tools
            return f"Unknown tool: {tool_name}"

    def _close_connection(self, conn):
        """Close a client connection and clean up resources."""
        self.tcp_selector.unregister(conn)
        conn.close()

        # Clean up buffers
        if conn in self.recv_buffers:
            del self.recv_buffers[conn]
        if conn in self.send_buffers:
            del self.send_buffers[conn]

        # Remove from client connections
        if conn in self.client_connections:
            del self.client_connections[conn]
# TCP Server API Design Document

## Table of Contents
1. [Overview](#overview)
2. [Connection Roles](#connection-roles)
3. [Handshake and Session Registration](#handshake-and-session-registration)
4. [Authentication and Shared-Secret Requirements](#authentication-and-shared-secret-requirements)
5. [API Surface Definition](#api-surface-definition)
6. [Security Considerations](#security-considerations)
7. [Error Handling](#error-handling)
8. [Implementation Notes](#implementation-notes)

## Overview

This document defines the API surface for the TCP server component of the AI CLI Live Tool Protocol. The TCP server facilitates network-based communication between AI agents and CLI tools, supporting remote orchestration scenarios in the Maestro system.

The server is designed to handle multiple concurrent connections while maintaining proper session isolation and message routing. It follows the protocol specification outlined in AI_CLI_LIVE_TOOL_PROTOCOL.md with additional considerations for network transport.

## Connection Roles

### Agent Role
- **Responsibility**: Initiates connections to the TCP server and sends tool requests
- **Capabilities**:
  - Establish new sessions with the server
  - Send tool call requests to the server
  - Receive tool execution responses and status updates
  - Subscribe to live event streams
  - Manage session lifecycle through protocol messages

### Client Role
- **Responsibility**: Connects to the TCP server to monitor and receive event streams
- **Capabilities**:
  - Listen to session events and tool call data
  - Inject input into active sessions (with appropriate permissions)
  - Subscribe to filtered event streams
  - Monitor multiple sessions simultaneously
  - Receive aggregated statistics and metadata

### Distinction Between Roles
- AgI've created a comprehensive TCP Server API Design document that covers all the required aspects:

1. Connection roles (agent vs client)
2. Handshake and session registration payloads
3. Authentication and shared-secret requirements
4. API surface definition with detailed class interfaces
5. Security considerations
6. Error handling strategies

The document provides a complete specification for the TCP server that aligns with the existing AI CLI Live Tool Protocol while defining the specific network transport implementation details needed for the Maestro system.
pe": "handshake_request",
  "version": "1.0",
  "role": "agent|client",
  "client_info": {
    "name": "string",
    "version": "string",
    "capabilities": ["capability1", "capability2"]
  },
  "session_id": "string (optional)",
  "timestamp": "ISO 8601 timestamp"
}
```

#### Handshake Response (Server → Client)
```json
{
  "type": "handshake_response",
  "success": true|false,
  "session_id": "string (assigned if not provided)",
  "server_info": {
    "name": "Maestro TCP Server",
    "version": "string",
    "protocol_version": "string"
  },
  "supported_features": ["feature1", "feature2"],
  "max_message_size": integer,
  "heartbeat_interval": integer (seconds),
  "timestamp": "ISO 8601 timestamp",
  "error": "error details if success is false"
}
```

### Session Registration and Configuration

After a successful handshake, the server registers the session and applies role-specific configurations:

1. **Role Validation**: Ensures the client's requested role is permitted
2. **Session Creation**: Creates a new session if none was specified or validates existing session
3. **Capability Negotiation**: Establishes which protocol features are available
4. **Subscription Setup**: Initializes event subscription filters based on role
5. **Resource Allocation**: Assigns buffers and connection tracking resources

### Session Properties
- **Unique Identifier**: Generated UUID for session tracking
- **Creation Timestamp**: When the session was established
- **Last Activity**: Time of most recent message exchange
- **Role Binding**: The established role for this session
- **Event Filters**: Subscription criteria for message routing
- **Connection Metadata**: IP address, client info, etc.

## Authentication and Shared-Secret Requirements

### Authentication Strategy

The TCP server implements a flexible authentication system supporting both token-based and shared-secret approaches:

#### Option 1: Pre-Shared Token Authentication
- A fixed token configured on both client and server
- Simple to deploy in controlled environments
- Appropriate for development and testing

#### Option 2: Per-Session Dynamic Tokens
- Server generates temporary tokens for each session
- More secure for production deployments
- Requires a bootstrap authentication mechanism

#### Option 3: TLS Client Certificates (Recommended for Production)
- Certificate-based authentication using TLS
- Highest security level
- Recommended for public-facing deployments

### Authentication Message Flow

#### Auth Request (after handshake)
```json
{
  "type": "auth_request",
  "auth_method": "token|shared_secret|tls_cert",
  "credentials": "credential_data (encrypted/hashed as appropriate)",
  "timestamp": "ISO 8601 timestamp"
}
```

#### Auth Response (from server)
```json
{
  "type": "auth_response",
  "success": true|false,
  "auth_id": "string (opaque identifier for authenticated session)",
  "permissions": {
    "can_subscribe_events": true|false,
    "can_send_tool_requests": true|false,
    "can_inject_input": true|false,
    "allowed_sessions": ["session_id1", "session_id2"] | "all"
  },
  "expires_at": "ISO 8601 timestamp (optional)",
  "error": "error details if unsuccessful"
}
```

### Shared Secret Configuration

#### Server Configuration
```json
{
  "tcp_server": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8080,
    "auth_required": true,
    "shared_secret": "pre_shared_secret_value",
    "auth_tokens": [
      {
        "token": "generated_token_1",
        "permissions": {
          "can_subscribe_events": true,
          "can_send_tool_requests": true,
          "can_inject_input": false,
          "allowed_sessions": "all"
        },
        "expires_at": "ISO 8601 timestamp"
      }
    ]
  }
}
```

### Security Best Practices
- Never transmit shared secrets in plaintext
- Rotate shared secrets regularly
- Implement rate limiting on authentication attempts
- Log authentication failures for security monitoring
- Use TLS encryption for all transmissions

## API Surface Definition

### TCP Server Class Interface

```python
import asyncio
from typing import Optional, Callable, Dict, Any
from enum import Enum

class ConnectionRole(Enum):
    AGENT = "agent"
    CLIENT = "client"

class TCPServerAuthMethod(Enum):
    TOKEN = "token"
    SHARED_SECRET = "shared_secret"
    TLS_CERT = "tls_cert"

class TCPSession:
    def __init__(self, session_id: str, role: ConnectionRole, client_info: Dict[str, Any]):
        self.session_id = session_id
        self.role = role
        self.client_info = client_info
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.authenticated = False
        self.permissions = {}
        self.event_filters = {}

class MaestroTCPServer:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the TCP server with the specified configuration.
        
        Args:
            config: Server configuration including host, port, authentication settings
        """
        self.config = config
        self.sessions: Dict[str, TCPSession] = {}
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 8080)
        self.auth_required = config.get("auth_required", True)
        self.shared_secret = config.get("shared_secret")
        self.auth_tokens = config.get("auth_tokens", [])
        self.event_router = EventRouter()
        self.message_validator = MessageValidator()
    
    async def start(self):
        """
        Start the TCP server and begin accepting connections.
        """
        server = await asyncio.start_server(
            self.handle_client_connection,
            self.host,
            self.port
        )
        
        print(f"TCP Server listening on {self.host}:{self.port}")
        
        async with server:
            await server.serve_forever()
    
    async def handle_client_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        Handle a new client connection, performing handshake and authentication.
        """
        try:
            # Perform handshake
            handshake_data = await self.read_handshake(reader)
            session = await self.process_handshake(handshake_data, reader, writer)
            
            # Handle authentication if required
            if self.auth_required and not session.authenticated:
                auth_result = await self.authenticate_session(session, reader, writer)
                if not auth_result.success:
                    await self.send_auth_response(writer, auth_result.error)
                    writer.close()
                    return
            
            # Register session and start message processing loop
            self.sessions[session.session_id] = session
            await self.handle_session_messages(session, reader, writer)
        except Exception as e:
            print(f"Error handling client connection: {e}")
        finally:
            if session and session.session_id in self.sessions:
                del self.sessions[session.session_id]
    
    async def process_handshake(self, handshake_data: Dict[str, Any], 
                               reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> TCPSession:
        """
        Process the handshake request and establish a session.
        """
        # Validate handshake data
        if handshake_data.get("version") != "1.0":
            await self.send_handshake_response(writer, success=False, error="Unsupported protocol version")
            raise ValueError("Unsupported protocol version")
        
        role = ConnectionRole(handshake_data.get("role"))
        session_id = handshake_data.get("session_id") or str(uuid.uuid4())
        
        # Create and register session
        session = TCPSession(
            session_id=session_id,
            role=role,
            client_info=handshake_data.get("client_info", {})
        )
        
        # Send successful handshake response
        response = {
            "type": "handshake_response",
            "success": True,
            "session_id": session_id,
            "server_info": {
                "name": "Maestro TCP Server",
                "version": "1.0",
                "protocol_version": "1.0"
            },
            "supported_features": ["event_subscription", "streaming", "heartbeats"],
            "max_message_size": 1024 * 1024,  # 1MB
            "heartbeat_interval": 30
        }
        await self.send_json(writer, response)
        
        return session
    
    async def authenticate_session(self, session: TCPSession, 
                                  reader: asyncio.StreamReader, 
                                  writer: asyncio.StreamWriter) -> Dict[str, Any]:
        """
        Authenticate a session using the configured authentication method.
        """
        auth_request = await self.read_json(reader)
        
        if auth_request.get("type") != "auth_request":
            return {"success": False, "error": "Invalid authentication message"}
        
        auth_method = auth_request.get("auth_method")
        credentials = auth_request.get("credentials")
        
        if auth_method == "token":
            return self.validate_token(credentials, session)
        elif auth_method == "shared_secret":
            return self.validate_shared_secret(credentials, session)
        else:
            return {"success": False, "error": f"Unsupported auth method: {auth_method}"}
    
    async def handle_session_messages(self, session: TCPSession,
                                     reader: asyncio.StreamReader,
                                     writer: asyncio.StreamWriter):
        """
        Handle message exchange for an authenticated session.
        """
        while True:
            try:
                message = await self.read_json(reader)
                
                # Update session activity
                session.last_activity = datetime.utcnow()
                
                # Validate message format
                if not self.message_validator.is_valid(message):
                    error_msg = {
                        "type": "error",
                        "session_id": session.session_id,
                        "data": {
                            "error_code": "INVALID_MESSAGE_FORMAT",
                            "message": "Message validation failed",
                            "severity": "error"
                        }
                    }
                    await self.send_json(writer, error_msg)
                    continue
                
                # Route message based on type and session permissions
                await self.route_message(session, message)
                
                # Send heartbeat periodically
                if self.should_send_heartbeat(session):
                    heartbeat_msg = {
                        "type": "heartbeat",
                        "session_id": session.session_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await self.send_json(writer, heartbeat_msg)
                    
            except asyncio.IncompleteReadError:
                # Connection closed by client
                break
            except Exception as e:
                error_msg = {
                    "type": "error",
                    "session_id": session.session_id,
                    "data": {
                        "error_code": "CONNECTION_ERROR",
                        "message": f"Connection error: {str(e)}",
                        "severity": "error"
                    }
                }
                await self.send_json(writer, error_msg)
                break
    
    async def route_message(self, session: TCPSession, message: Dict[str, Any]):
        """
        Route a received message based on its type and the session's role/permissions.
        """
        msg_type = message.get("type")
        
        if msg_type == "tool_call_request" and session.role == ConnectionRole.AGENT:
            # Forward tool requests to appropriate handler
            await self.event_router.forward_tool_request(session, message)
        elif msg_type == "subscribe_events":
            # Handle event subscription requests
            await self.handle_event_subscription(session, message)
        elif msg_type == "unsubscribe_events":
            # Handle event unsubscription requests
            await self.handle_event_unsubscription(session, message)
        else:
            # Forward other messages appropriately based on type and permissions
            await self.event_router.forward_message(session, message)
    
    def validate_token(self, token: str, session: TCPSession) -> Dict[str, Any]:
        """
        Validate a token against the configured list of valid tokens.
        """
        for valid_token in self.auth_tokens:
            if valid_token["token"] == token:
                # Check if token is expired
                if "expires_at" in valid_token:
                    expires_at = datetime.fromisoformat(valid_token["expires_at"])
                    if datetime.utcnow() > expires_at:
                        return {"success": False, "error": "Token has expired"}
                
                # Apply permissions
                session.authenticated = True
                session.permissions = valid_token.get("permissions", {})
                return {"success": True}
        
        return {"success": False, "error": "Invalid token"}
    
    def validate_shared_secret(self, secret: str, session: TCPSession) -> Dict[str, Any]:
        """
        Validate a shared secret against the configured value.
        """
        if secret == self.shared_secret:
            session.authenticated = True
            # Apply default permissions for shared secret auth
            session.permissions = {
                "can_subscribe_events": True,
                "can_send_tool_requests": True,
                "can_inject_input": False,
                "allowed_sessions": "all"
            }
            return {"success": True}
        else:
            return {"success": False, "error": "Invalid shared secret"}
    
    # Utility methods for sending/receiving JSON messages
    async def send_json(self, writer: asyncio.StreamWriter, data: Dict[str, Any]):
        """
        Send a JSON message to the client.
        """
        json_str = json.dumps(data) + '\n'
        writer.write(json_str.encode())
        await writer.drain()
    
    async def read_json(self, reader: asyncio.StreamReader) -> Dict[str, Any]:
        """
        Read a JSON message from the client.
        """
        line = await reader.readline()
        return json.loads(line.decode())
    
    async def read_handshake(self, reader: asyncio.StreamReader) -> Dict[str, Any]:
        """
        Read and validate the initial handshake message.
        """
        return await self.read_json(reader)
    
    async def send_handshake_response(self, writer: asyncio.StreamWriter, 
                                    success: bool, error: Optional[str] = None):
        """
        Send a handshake response to the client.
        """
        response = {
            "type": "handshake_response",
            "success": success,
            "server_info": {
                "name": "Maestro TCP Server",
                "version": "1.0",
                "protocol_version": "1.0"
            },
            "supported_features": [],
            "max_message_size": 1024 * 1024,
            "heartbeat_interval": 30
        }
        
        if error:
            response["error"] = error
        
        await self.send_json(writer, response)
    
    async def send_auth_response(self, writer: asyncio.StreamWriter, error: Optional[str] = None):
        """
        Send an authentication response to the client.
        """
        response = {
            "type": "auth_response",
            "success": error is None
        }
        
        if error:
            response["error"] = error
        
        await self.send_json(writer, response)
    
    def should_send_heartbeat(self, session: TCPSession) -> bool:
        """
        Determine if a heartbeat should be sent for the session.
        """
        return (datetime.utcnow() - session.last_activity).total_seconds() > 20
```

### Public API Methods

#### Basic Server Operations
- `start()`: Start the TCP server and begin accepting connections
- `stop()`: Gracefully shut down the server and close all connections
- `get_session_stats()`: Retrieve statistics about active sessions
- `reload_config(config)`: Reload server configuration without restarting

#### Session Management
- `get_active_sessions()`: List all currently connected sessions
- `terminate_session(session_id)`: Forcefully terminate a specific session
- `broadcast_message(message)`: Broadcast a message to all connected clients

#### Event Routing
- `register_event_handler(handler)`: Register a handler for specific event types
- `route_event(event_data)`: Manually route an event to subscribed sessions
- `subscribe_to_session_events(session_id, event_types)`: Subscribe to events for a specific session

## Security Considerations

### Encryption
- All TCP communications should use TLS encryption in production
- Support for TLS 1.2 and higher recommended
- Certificate pinning for enhanced security

### Network Security
- Support for IP whitelisting/blacklisting
- Rate limiting to prevent abuse
- Firewall integration for restricting access

### Data Protection
- Sensitive information in messages should be encrypted
- Logs should not contain sensitive data
- Proper session cleanup to prevent data leakage

## Error Handling

### Connection-Level Errors
- Implement proper connection timeout handling
- Graceful degradation when resources are exhausted
- Detailed error logging for debugging

### Message-Level Errors
- Validate all incoming messages against schema
- Implement message size limits to prevent abuse
- Respond with appropriate error codes as defined in the protocol

### Recovery Strategies
- Implement automatic reconnection for transient failures
- Session state persistence for graceful recovery
- Circuit breaker pattern for handling cascading failures

## Implementation Notes

### Architecture
The TCP server implementation should follow an asynchronous, event-driven architecture using asyncio to handle multiple concurrent connections efficiently.

### Performance Considerations
- Implement message buffering to optimize throughput
- Use connection pooling where appropriate
- Monitor resource consumption and implement throttling

### Testing Strategy
- Unit tests for message handling and validation
- Integration tests for end-to-end scenarios
- Load testing to validate performance under scale
- Security tests for authentication and authorization
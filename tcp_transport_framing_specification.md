# TCP Transport and Framing Specification

## Overview
This document specifies the TCP transport layer and message framing protocol used in the Maestro system. It defines how messages are framed, transmitted, and processed over TCP connections, including considerations for message size limits, error handling, and flow control mechanisms.

## Table of Contents
1. [Message Framing](#message-framing)
2. [Maximum Message Size](#maximum-message-size)
3. [Truncation Rules](#truncation-rules)
4. [Backpressure Strategy](#backpressure-strategy)
5. [Buffer Limits](#buffer-limits)
6. [Implementation Considerations](#implementation-considerations)

## Message Framing

### Frame Format
All messages sent over TCP connections in the Maestro system follow a length-prefixed frame format:

```
[FRAME_SIZE][MESSAGE_PAYLOAD]
| 4 bytes  | Variable bytes |
```

- **FRAME_SIZE** (4 bytes): A big-endian unsigned 32-bit integer representing the size of the MESSAGE_PAYLOAD in bytes
- **MESSAGE_PAYLOAD** (variable bytes): The actual message content to be transmitted

### Frame Processing
1. **Sending Side**:
   - Serialize the message payload into bytes
   - Calculate the byte length of the message payload
   - Encode the length as a 4-byte big-endian unsigned integer
   - Concatenate the length prefix and the message payload
   - Write the frame to the TCP socket

2. **Receiving Side**:
   - Read the first 4 bytes to determine the expected payload size
   - Decode the frame size from the 4-byte big-endian unsigned integer
   - Validate the frame size against maximum allowed sizes
   - Read the remaining bytes of the specified size
   - Process the message payload

### Error Handling for Frame Parsing
- If FRAME_SIZE exceeds the maximum allowed message size, the connection MUST be closed with error
- If the connection is closed before reading the expected payload bytes, the frame is considered corrupted and SHOULD be discarded
- If invalid frame size values are detected (e.g., negative values when interpreted as signed integers), the connection MUST be closed

## Maximum Message Size

### Default Limits
- **Maximum Message Payload Size**: 16 MiB (16,777,216 bytes)
- **Maximum Frame Size**: 16,777,220 bytes (including 4-byte header)
- **Recommended Message Size**: <= 1 MiB for optimal performance

### Configuration
- The maximum message size SHOULD be configurable per deployment
- The minimum allowed maximum message size is 1 KiB
- The maximum allowed maximum message size is 1 GiB
- Any attempt to send a message exceeding the maximum size MUST result in an error at the application level before transmission

### Considerations
- Large messages increase memory pressure on both sender and receiver
- Network buffers may be exhausted when transmitting large payloads
- Consider message splitting for payloads approaching the maximum size

## Truncation Rules

### Message Truncation Policy
**The system MUST NOT automatically truncate messages**. Instead, the following policy applies:

1. **Pre-transmission Validation**:
   - Messages are validated against the maximum size before transmission
   - Applications attempting to send oversized messages receive an error
   - No partial transmission occurs for oversized messages

2. **Transmission Failures**:
   - If a message exceeds the frame size limit during transmission, the connection is closed
   - The sending application receives a transmission error notification
   - No partially received frames are processed at the receiving end

3. **Recovery**:
   - Applications SHOULD implement message splitting for large payloads
   - Retry logic SHOULD handle connection closures due to size violations
   - Logging SHOULD capture size violation attempts for debugging

## Backpressure Strategy

### Flow Control Mechanism
The system implements a hybrid flow control approach combining application-level signals and TCP backpressure:

1. **TCP Backpressure**:
   - Leverages TCP's built-in flow control mechanisms
   - Buffer overflow causes TCP window to shrink, naturally applying backpressure
   - Slow receivers implicitly limit sender throughput

2. **Application-Level Signals**:
   - Receiver maintains a queue of incoming messages with configurable maximum length
   - When the queue approaches capacity (configurable threshold), the receiver publishes a flow control signal
   - Senders monitor for flow control signals and adjust their transmission rate accordingly
   - Flow control signals can be implemented as side-channel notifications or integrated into the message protocol

### Congestion Avoidance
1. **Adaptive Window Sizing**:
   - Senders dynamically adjust the number of outstanding messages based on round-trip times and acknowledgments
   - Implement slow-start behavior when connections are initially established

2. **Priority Queuing**:
   - Critical system messages (e.g., flow control, heartbeat, error reports) are prioritized over regular application messages
   - Priority levels are encoded in message headers with defined priorities:
     - Level 0: Critical system messages
     - Level 1: High priority application messages
     - Level 2: Normal priority application messages
     - Level 9: Low priority application messages

### Resource Allocation
- Each connection maintains separate input and output buffers
- Resources are allocated based on connection priority and historical usage
- Connection pools limit the number of concurrent connections to prevent resource exhaustion

## Buffer Limits

### Per-Connection Buffers
1. **Send Buffer**:
   - Default size: 64 KiB
   - Configurable range: 8 KiB to 1 MiB
   - Used to queue messages before transmission
   - Overflow triggers connection-level backpressure

2. **Receive Buffer**:
   - Default size: 64 KiB
   - Configurable range: 8 KiB to 1 MiB
   - Used to accumulate incoming data before frame parsing
   - Overflow results in connection closure

3. **Message Queue**:
   - Default maximum queued messages: 256
   - Configurable range: 16 to 8192 messages
   - Stores parsed messages awaiting processing
   - Overflow triggers application-level backpressure

### System-Wide Limits
1. **Total Memory Limit**:
   - Maximum total buffer memory per node: 512 MiB
   - Configurable based on available system memory
   - Enforced across all connections and queues

2. **Connection Pool Limits**:
   - Default maximum connections: 1024
   - Configurable range: 8 to 16384 connections
   - Includes protection against connection exhaustion attacks

### Buffer Management Strategy
1. **Memory Management**:
   - Implement buffer pooling to minimize allocations/deallocations
   - Use zero-copy techniques where possible to improve performance
   - Release buffers immediately after processing where appropriate

2. **Garbage Collection**:
   - Monitor buffer utilization and trigger garbage collection when thresholds exceeded
   - Implement timeout mechanisms for incomplete frames
   - Detect and recover from connection leaks

## Implementation Considerations

### Performance Optimization
1. **Frame Assembly**:
   - Use vectorized I/O (e.g., writev/readv) when available to reduce system calls
   - Minimize memory copies during frame serialization and deserialization

2. **Connection Management**:
   - Implement connection reuse with keep-alive mechanisms
   - Support graceful degradation under high load conditions

3. **Error Recovery**:
   - Design for partial failure scenarios
   - Implement retry mechanisms with exponential backoff
   - Maintain consistent state across distributed components

### Security Implications
1. **Resource Exhaustion Prevention**:
   - Apply buffer limits consistently to prevent denial-of-service attacks
   - Implement connection rate limiting to prevent connection flooding
   - Validate frame sizes before allocating memory for frame payloads

2. **Authentication and Integrity**:
   - Frame protocol operates at a lower level than authentication
   - Encryption and authentication should be implemented at higher layers
   - Frame boundaries must remain intact when encryption is applied

### Testing Requirements
1. **Load Testing**:
   - Test behavior at maximum frame sizes
   - Simulate high-throughput scenarios
   - Validate graceful degradation under resource pressure

2. **Failure Scenarios**:
   - Connection interruption during frame transmission
   - Buffer overflow scenarios
   - Invalid frame format injection
   - Concurrent connection limits testing

## Version Compatibility
- Future versions of this protocol should maintain backward compatibility where possible
- Version negotiation mechanism (to be defined in separate specification) should handle protocol differences
- Major version changes may introduce new frame types or extensions to the basic frame format

## Compliance Verification
- All implementations MUST pass the standardized conformance test suite
- Implementations MUST correctly handle all error cases defined in this specification
- Performance benchmarks MUST be met under standard operating conditions
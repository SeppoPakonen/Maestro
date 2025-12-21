I'll create a detailed specification for TCP transport and framing. Let me first check if there are any existing specifications in the project that I should reference.

Let me check if there's already a transport framing document in the project that I should reference or update.

It appears the file exists but contains notes about creating the specification rather than the actual specification. I'll create a comprehensive TCP transport and framing specification document.

I've created a comprehensive TCP transport and framing specification document that covers all the requested aspects:

1. **Message Framing Choice**: Defined a length-prefixed frame format with 4-byte big-endian size header
2. **Maximum Message Size**: Specified default limits (16 MiB payload) with configurable ranges
3. **Truncation Rules**: Defined a strict no-truncation policy with pre-transmission validation
4. **Backpressure Strategy**: Outlined a hybrid approach using both TCP backpressure and application-level signals
5. **Buffer Limits**: Detailed per-connection and system-wide buffer limits with management strategies

The specification includes implementation considerations, security implications, testing requirements, and compliance verification criteria. This document provides a complete guide for implementing TCP transport and framing in the Maestro system.

The TCP transport and framing specification has been created successfully. Is there anything else you'd like me to work on related to this specification or any other tasks?

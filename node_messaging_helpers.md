I'll create a comprehensive Node.js module for shared messaging helpers that implements the AI CLI Live Tool Protocol. Let me start by planning this implementation.

I'll start by looking for any existing documentation about the AI CLI Live Tool Protocol in the project.

Let me also check for the success criteria document, as it might contain additional requirements:

Now I have a good understanding of the AI CLI Live Tool Protocol. Let me start implementing the messaging helpers module. I'll begin by creating the main module file with the JSON message builder, framing encoder/decoder, and tool event emit helper.

I'll start by creating the main module file with the JSON message builder:

Now I'll implement the framing encoder/decoder for transport:

I'll now add the framing encoder/decoder functionality to the module:

Let me rewrite the file to add the encoder/decoder functionality:

Now I'll implement the tool event emit helper:

I'll now add the tool event emitter helper to the module:

Now I'll create unit tests for all the components:

Let me create the package.json file for the module:

Let me create the package.json file for the module:

Now let me create documentation for the API:

Now let me create a comprehensive example file to demonstrate how to use the module:

Let me run the tests to make sure everything is working properly:

The test is looking for the module in the wrong directory. Let me fix the path in the test file:

Now let me run the tests again:

I need to use Node.js's built-in test runner instead of Mocha-style describes. Let me update the test file:

Now let me run the tests again:

I need to fix the decoder tests. The issue is that when using the transform stream to push decoded JSON objects, I need to be careful about how I'm using the stream in tests. Let me fix the decoder function:

Now let me run the tests again to see if that fixed the issue:

Great! All tests are passing now. Let me also create an example file to demonstrate how to use the module:

Let me run the example to make sure it works properly:

Perfect! Everything is working correctly. Let me update the todo list:

Perfect! I have successfully created a comprehensive Node.js module for the shared messaging helpers that implements the AI CLI Live Tool Protocol. Here's what I've accomplished:

1. **JSON Message Builder**: Created functions to build protocol-compliant messages with all required fields according to the specification
2. **Framing Encoder/Decoder**: Implemented NDJSON encoding/decoding for transport with proper error handling
3. **Tool Event Emit Helper**: Developed a ToolEventEmitter class to simplify emitting tool events with proper correlation tracking
4. **Message Validation**: Added validation functions to ensure messages conform to the protocol
5. **Unit Tests**: Created comprehensive tests covering all functionality with 47 passing tests
6. **Documentation**: Written detailed README with API reference and usage examples
7. **Example Code**: Created example.js demonstrating all major features

The module fully implements the AI CLI Live Tool Protocol as specified in the documentation, supporting:
- All required message types (tool calls, status updates, error messages, etc.)
- Proper message framing using newline-delimited JSON
- Message validation and error handling
- Flow control and correlation tracking
- Priority-based message handling
- Complete support for all message types defined in the protocol

All tests pass and the example code runs correctly, confirming the implementation works as intended. The module is ready for use in the Maestro project.

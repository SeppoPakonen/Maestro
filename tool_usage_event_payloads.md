# Tool Usage Event Payloads in Qwen-Code

This document provides sample JSON messages for tool usage events (start/end/updates) extracted from the qwen-code project, with field lists indicating required/optional tags.

## 1. Tool Call Request Event

This event is emitted when a tool call is requested by the model.

### Sample JSON:
```json
{
  "type": "tool_call_request",
  "value": {
    "callId": "read_file-1692345678901-0.1234567890123456",
    "name": "read_file",
    "args": {
      "file_path": "/path/to/file.txt"
    },
    "isClientInitiated": false,
    "prompt_id": "prompt-12345",
    "response_id": "response-67890"
  }
}
```

### Field List:
- `type`: (Required) Always "tool_call_request"
- `value`: (Required) Object containing the tool call details
  - `callId`: (Required) Unique identifier for this tool call
  - `name`: (Required) Name of the tool being called
  - `args`: (Required) Arguments for the tool call (structure varies by tool)
  - `isClientInitiated`: (Required) Boolean indicating if call was initiated by client
  - `prompt_id`: (Required) ID of the prompt that triggered this tool call
  - `response_id`: (Optional) ID of the response containing this tool call

## 2. Tool Call Confirmation Event

This event is emitted when a tool call requires confirmation before execution.

### Sample JSON:
```json
{
  "type": "tool_call_confirmation",
  "value": {
    "request": {
      "callId": "edit_file-1692345678901-0.1234567890123456",
      "name": "edit_file",
      "args": {
        "file_path": "/path/to/file.txt",
        "content": "new content"
      },
      "isClientInitiated": false,
      "prompt_id": "prompt-12345",
      "response_id": "response-67890"
    },
    "details": {
      "type": "edit",
      "title": "File Edit Confirmation",
      "onConfirm": "function reference",
      "fileName": "file.txt",
      "filePath": "/path/to/file.txt",
      "fileDiff": "@@ -1,3 +1,3 @@\n-old content\n+new content\n unchanged line",
      "originalContent": "old content\nunchanged line",
      "newContent": "new content\nunchanged line",
      "isModifying": true
    }
  }
}
```

### Field List:
- `type`: (Required) Always "tool_call_confirmation"
- `value`: (Required) Object containing the request and confirmation details
  - `request`: (Required) The original tool call request (same structure as tool_call_request)
  - `details`: (Required) Confirmation details object
    - `type`: (Required) Type of confirmation ("edit", "exec", "mcp", "info", "plan")
    - `title`: (Required) Title for the confirmation UI
    - `onConfirm`: (Required) Function reference to call when confirmed
    - `fileName`: (Conditional) Required for "edit" type - name of the file
    - `filePath`: (Conditional) Required for "edit" type - path of the file
    - `fileDiff`: (Conditional) Required for "edit" type - diff showing changes
    - `originalContent`: (Conditional) Required for "edit" type - original file content
    - `newContent`: (Conditional) Required for "edit" type - new file content
    - `isModifying`: (Optional) Boolean indicating if the edit is modifiable
    - `command`: (Conditional) Required for "exec" type - command to execute
    - `rootCommand`: (Conditional) Required for "exec" type - root command
    - `serverName`: (Conditional) Required for "mcp" type - name of the MCP server
    - `toolName`: (Conditional) Required for "mcp" type - name of the tool
    - `toolDisplayName`: (Conditional) Required for "mcp" type - display name of the tool
    - `prompt`: (Conditional) Required for "info" type - prompt to display
    - `urls`: (Optional) For "info" type - array of URLs to include
    - `plan`: (Conditional) Required for "plan" type - the plan to confirm

## 3. Tool Call Response Event

This event is emitted when a tool call completes and returns a result.

### Sample JSON:
```json
{
  "type": "tool_call_response",
  "value": {
    "callId": "read_file-1692345678901-0.1234567890123456",
    "responseParts": [
      {
        "text": "File content: Hello, World!"
      }
    ],
    "resultDisplay": "File content: Hello, World!",
    "error": null,
    "errorType": null,
    "outputFile": null,
    "contentLength": 13
  }
}
```

### Field List:
- `type`: (Required) Always "tool_call_response"
- `value`: (Required) Object containing the tool call response details
  - `callId`: (Required) ID of the call this is a response to
  - `responseParts`: (Required) Array of response parts (can be text, function responses, etc.)
  - `resultDisplay`: (Required) Display representation of the result (string, FileDiff, TodoResultDisplay, etc.)
  - `error`: (Optional) Error message if the tool call failed
  - `errorType`: (Optional) Type of error (ToolErrorType enum)
  - `outputFile`: (Optional) Path to an output file if generated
  - `contentLength`: (Optional) Length of the content returned

## 4. Stream Events for Tool Usage

When using stream-json output format with include-partial-messages, additional stream events may be included.

### Message Start Event:
```json
{
  "type": "message_start",
  "message": {
    "id": "msg-12345",
    "role": "assistant",
    "model": "gemini-1.5-pro"
  }
}
```

### Content Block Start Event:
```json
{
  "type": "content_block_start",
  "index": 0,
  "content_block": {
    "type": "tool_use",
    "id": "toolu-12345",
    "name": "read_file",
    "input": {
      "file_path": "/path/to/file.txt"
    }
  }
}
```

### Content Block Delta Event:
```json
{
  "type": "content_block_delta",
  "index": 0,
  "delta": {
    "type": "input_json_delta",
    "partial_json": "{\"file_path\": \"/path/to/"
  }
}
```

### Content Block Stop Event:
```json
{
  "type": "content_block_stop",
  "index": 0
}
```

### Message Stop Event:
```json
{
  "type": "message_stop"
}
```

### Field Lists for Stream Events:
- **Message Start Event:**
  - `type`: (Required) Always "message_start"
  - `message`: (Required) Object containing message details
    - `id`: (Required) Message ID
    - `role`: (Required) Always "assistant"
    - `model`: (Required) Model name

- **Content Block Start Event:**
  - `type`: (Required) Always "content_block_start"
  - `index`: (Required) Index of the content block
  - `content_block`: (Required) The content block being started
    - `type`: (Required) "text", "thinking", "tool_use", or "tool_result"
    - `id`: (Conditional) Required for "tool_use" - tool use ID
    - `name`: (Conditional) Required for "tool_use" - tool name
    - `input`: (Conditional) Required for "tool_use" - tool arguments
    - `tool_use_id`: (Conditional) Required for "tool_result" - ID of associated tool use
    - `content`: (Optional) For "tool_result" - result content
    - `is_error`: (Optional) For "tool_result" - boolean indicating error

- **Content Block Delta Event:**
  - `type`: (Required) Always "content_block_delta"
  - `index`: (Required) Index of the content block
  - `delta`: (Required) The delta content
    - `type`: (Required) "text_delta", "thinking_delta", or "input_json_delta"
    - `text`: (Conditional) Required for "text_delta" and "thinking_delta"
    - `partial_json`: (Conditional) Required for "input_json_delta"

- **Content Block Stop Event:**
  - `type`: (Required) Always "content_block_stop"
  - `index`: (Required) Index of the content block

- **Message Stop Event:**
  - `type`: (Required) Always "message_stop"

## 5. SDK Message Wrapper

When events are sent through the SDK, they are wrapped in a specific message format:

```json
{
  "type": "stream_event",
  "uuid": "uuid-12345",
  "session_id": "session-67890",
  "event": {
    // One of the event types described above
  },
  "parent_tool_use_id": null
}
```

### Field List for SDK Wrapper:
- `type`: (Required) Always "stream_event"
- `uuid`: (Required) Unique identifier for this message
- `session_id`: (Required) ID of the session this message belongs to
- `event`: (Required) The actual event payload
- `parent_tool_use_id`: (Optional) ID of parent tool use if this is a nested call
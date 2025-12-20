# Phase CLI3: AI Discussion System 📋 **[Planned]**

"phase_id": "cli-tpt-3"
"track": "Track/Phase/Task CLI and AI Discussion System"
"track_id": "cli-tpt"
"status": "planned"
"completion": 0
"duration": "2-3 weeks"
"dependencies": ["cli-tpt-1", "cli-tpt-2"]
"priority": "P0"

**Objective**: Implement a unified AI discussion interface that works across all track/phase/task contexts, supporting both editor-based and terminal stream modes, with JSON action processing for automated task management.

## Background

AI discussion is a core feature that allows natural language planning and task management:
- **Context-aware**: Each discussion knows if it's about a track, phase, or task
- **Flexible interface**: Use $EDITOR for thoughtful planning or terminal for quick interactions
- **Action-based**: AI generates JSON actions that modify track/phase/task data
- **Unified**: Same discussion module used everywhere, reducing code duplication

This enables workflows like:
```bash
# Plan a new track
maestro track discuss
> "I need to add Python build system support"
> /done
# → AI creates new track with phases

# Discuss a specific phase
maestro phase cli-tpt-1 discuss
> "Help me break down the parser implementation"
> /done
# → AI adds tasks to phase

# Quick task question
maestro task cli-tpt-1-1 discuss
> "What regex should I use for quoted values?"
# → AI provides guidance
```

## Tasks

### Task cli3.1: Core Discussion Module

"task_id": "cli-tpt-3-1"
"priority": "P0"
"estimated_hours": 16

Create the unified discussion engine that all AI interactions use.

- [ ] **cli3.1.1: Discussion Module Structure**
  - [ ] Create `maestro/ai/discussion.py`
  - [ ] Define `DiscussionContext` dataclass:
    - `context_type`: "track" | "phase" | "task" | "general"
    - `context_id`: Optional track/phase/task ID
    - `allowed_actions`: List of JSON action types allowed in this context
    - `system_prompt`: Context-specific instructions for AI
  - [ ] Define `DiscussionMode` enum:
    - `EDITOR`: Use $EDITOR with # comments
    - `TERMINAL`: Interactive terminal stream
  - [ ] Define `Discussion` class with methods:
    - `__init__(context: DiscussionContext, mode: DiscussionMode)`
    - `start() -> DiscussionResult`
    - `add_user_message(msg: str)`
    - `add_ai_message(msg: str)`
    - `process_command(cmd: str) -> bool`  # Returns True if should exit

- [ ] **cli3.1.2: Context Builders**
  - [ ] Implement `build_track_context(track_id: Optional[str]) -> DiscussionContext`
    - Load track data if ID provided
    - Set allowed actions: track.add, track.edit, phase.add
    - Build system prompt with track info
  - [ ] Implement `build_phase_context(phase_id: str) -> DiscussionContext`
    - Load phase and parent track data
    - Set allowed actions: phase.edit, task.add, task.edit
    - Build system prompt with phase info
  - [ ] Implement `build_task_context(task_id: str) -> DiscussionContext`
    - Load task, phase, and track data
    - Set allowed actions: task.edit, task.complete
    - Build system prompt with task info

- [ ] **cli3.1.3: Discussion Result**
  - [ ] Define `DiscussionResult` dataclass:
    - `messages`: List of user/AI message pairs
    - `actions`: List of JSON actions to execute
    - `completed`: bool (True if /done, False if /quit)
  - [ ] Implement result serialization to docs/discussions/*.md

### Task cli3.2: Editor Mode

"task_id": "cli-tpt-3-2"
"priority": "P0"
"estimated_hours": 12

Implement editor-based discussion mode using $EDITOR.

- [ ] **cli3.2.1: Editor Interface**
  - [ ] Implement `EditorDiscussion` class (inherits from `Discussion`)
  - [ ] Create temporary markdown file format:
    ```markdown
    # Discussion: <context-description>

    # Context: <track/phase/task details>
    # Type your message below, then save and exit.
    # Previous AI responses are shown as # comments.
    # Special commands: /done (finish and apply), /quit (cancel)

    <user types here>

    # AI response from previous turn:
    # <AI message line 1>
    # <AI message line 2>
    ```
  - [ ] Parse user input from non-comment lines
  - [ ] Detect special commands (/done, /quit)

- [ ] **cli3.2.2: Editor Loop**
  - [ ] Implement main loop:
    1. Write current state to temp file
    2. Open $EDITOR on temp file
    3. Parse user input when editor exits
    4. Check for commands (/done, /quit)
    5. Send to AI if not a command
    6. Append AI response as comments
    7. Repeat until command received
  - [ ] Handle editor errors (file not saved, editor crash)
  - [ ] Support $VISUAL fallback if $EDITOR not set

- [ ] **cli3.2.3: AI Response Integration**
  - [ ] Call AI API with user message and context
  - [ ] Parse AI response for:
    - Natural language reply
    - Embedded JSON actions (```json...``` blocks)
  - [ ] Append AI reply as # comments for next iteration
  - [ ] Extract and queue JSON actions

### Task cli3.3: Terminal Stream Mode

"task_id": "cli-tpt-3-3"
"priority": "P0"
"estimated_hours": 12

Implement terminal-based discussion mode with real-time interaction.

- [ ] **cli3.3.1: Terminal Interface**
  - [ ] Implement `TerminalDiscussion` class (inherits from `Discussion`)
  - [ ] Use readline for input handling
  - [ ] Key bindings:
    - `<Enter>`: Send message
    - `<Ctrl+J>` or `<Ctrl+Enter>`: Insert newline
    - `<Ctrl+C>`: Cancel discussion (same as /quit)
    - `<Up/Down>`: History navigation
  - [ ] Display formatting:
    - User messages: `You: <message>`
    - AI messages: `AI: <message>`
    - System messages: `[System] <message>`

- [ ] **cli3.3.2: Multi-line Input**
  - [ ] Implement multi-line input buffer
  - [ ] Show continuation prompt for multi-line: `...`
  - [ ] Handle Ctrl+J to add newline without sending
  - [ ] Handle pasted text with embedded newlines correctly

- [ ] **cli3.3.3: Streaming AI Responses**
  - [ ] Support streaming AI API responses
  - [ ] Display AI response in real-time as tokens arrive
  - [ ] Show typing indicator while waiting: `AI: ...`
  - [ ] Allow Ctrl+C to cancel mid-response

- [ ] **cli3.3.4: Command Handling**
  - [ ] Detect commands: `/done`, `/quit`, `/help`
  - [ ] Implement `/help` to show available commands
  - [ ] Clear indication when command is processed:
    ```
    You: /done
    [System] Processing actions and exiting...
    ```

### Task cli3.4: JSON Action Processor

"task_id": "cli-tpt-3-4"
"priority": "P0"
"estimated_hours": 16

Implement the action processor that executes AI-generated JSON actions.

- [ ] **cli3.4.1: Action Schema**
  - [ ] Define JSON action format:
    ```json
    {
      "actions": [
        {
          "type": "track.add",
          "data": {"name": "...", "description": "...", "priority": 1}
        },
        {
          "type": "phase.add",
          "data": {"track_id": "...", "name": "...", "duration": "..."}
        },
        {
          "type": "task.add",
          "data": {"phase_id": "...", "name": "...", "priority": "P0"}
        }
      ]
    }
    ```
  - [ ] Define all action types:
    - `track.add`, `track.edit`, `track.remove`
    - `phase.add`, `phase.edit`, `phase.remove`
    - `task.add`, `task.edit`, `task.complete`, `task.remove`

- [ ] **cli3.4.2: Action Validators**
  - [ ] Implement validator for each action type
  - [ ] Check required fields
  - [ ] Validate references (track_id exists, phase_id exists, etc.)
  - [ ] Check permissions (only allowed actions for context)

- [ ] **cli3.4.3: Action Executors**
  - [ ] Implement executor for each action type
  - [ ] Use markdown writer to update docs/todo.md
  - [ ] Create/update docs/phases/*.md as needed
  - [ ] Handle errors gracefully (rollback on failure)

- [ ] **cli3.4.4: Action Processing Pipeline**
  - [ ] Implement `ActionProcessor` class:
    - `validate_actions(actions: List, context: DiscussionContext) -> List[str]`
      - Returns list of validation errors, empty if valid
    - `execute_actions(actions: List) -> ActionResult`
      - Execute all actions in order
      - Rollback on failure
      - Return summary of changes
  - [ ] Transaction support (all-or-nothing execution)
  - [ ] Preview mode (`--dry-run`) to show what would happen

### Task cli3.5: Discussion Commands

"task_id": "cli-tpt-3-5"
"priority": "P0"
"estimated_hours": 8

Implement the CLI commands for starting discussions.

- [ ] **cli3.5.1: Track Discussion**
  - [ ] Implement `maestro track discuss`
    - General track planning (no specific track)
    - Can create new tracks
  - [ ] Implement `maestro track <id> discuss`
    - Discussion about specific track
    - Can add phases, edit track details

- [ ] **cli3.5.2: Phase Discussion**
  - [ ] Implement `maestro phase <id> discuss`
    - Discussion about specific phase
    - Can add tasks, edit phase details
  - [ ] Implement `maestro discuss` (contextual)
    - If current_phase is set, discuss that phase
    - Otherwise, general discussion

- [ ] **cli3.5.3: Task Discussion**
  - [ ] Implement `maestro task <id> discuss`
    - Discussion about specific task
    - Can edit task, add subtasks

- [ ] **cli3.5.4: Mode Selection**
  - [ ] Add `--mode <editor|terminal>` flag to all discuss commands
  - [ ] Respect default from `docs/config.md`: `"discussion_mode"`
  - [ ] Auto-detect: use editor if $EDITOR set, terminal otherwise

### Task cli3.6: AI Integration

"task_id": "cli-tpt-3-6"
"priority": "P1"
"estimated_hours": 12

Integrate with AI APIs (OpenAI, Anthropic, local models).

- [ ] **cli3.6.1: AI Client Abstraction**
  - [ ] Create `maestro/ai/client.py`
  - [ ] Define `AIClient` abstract base class:
    - `send_message(messages: List, context: str) -> str`
    - `stream_message(messages: List, context: str) -> Iterator[str]`
  - [ ] Support multiple providers:
    - OpenAI (GPT-4)
    - Anthropic (Claude)
    - Local (Ollama, llama.cpp)

- [ ] **cli3.6.2: System Prompts**
  - [ ] Design system prompt template:
    ```
    You are a project planning assistant for Maestro.

    Context: {context_type}
    {context_details}

    The user wants to discuss: {user_query}

    You can suggest actions in JSON format:
    {action_schema}

    Allowed actions: {allowed_actions}

    Provide helpful guidance and suggest concrete actions.
    ```
  - [ ] Include context-specific details (track/phase/task info)
  - [ ] Include examples of valid JSON actions

- [ ] **cli3.6.3: Response Parsing**
  - [ ] Extract natural language from AI response
  - [ ] Extract JSON blocks (```json...```)
  - [ ] Handle mixed responses (text + JSON)
  - [ ] Validate JSON syntax

- [ ] **cli3.6.4: Configuration**
  - [ ] Add AI config to docs/config.md:
    - `"ai_provider"`: "openai" | "anthropic" | "local"
    - `"ai_model"`: model name
    - `"ai_api_key"`: API key (or path to key file)
    - `"ai_context_window"`: max tokens for context
  - [ ] Implement `maestro settings ai` to configure

## Deliverables

- `maestro/ai/discussion.py` - Core discussion engine
- `maestro/ai/editor.py` - Editor mode implementation
- `maestro/ai/terminal.py` - Terminal mode implementation
- `maestro/ai/actions.py` - Action processor
- `maestro/ai/client.py` - AI client abstraction
- `maestro/commands/discuss.py` - Discussion commands
- `docs/discussions/*.md` - Discussion history storage
- `tests/ai/test_discussion.py` - Discussion tests
- `tests/ai/test_actions.py` - Action processor tests

## Test Criteria

- Editor mode works with various $EDITOR values
- Terminal mode handles multi-line input correctly
- JSON actions are validated and executed correctly
- AI responses are parsed correctly
- Discussions are saved to docs/discussions/*.md
- Context is correctly provided to AI
- Rollback works on action execution failure

## Dependencies

- Phase CLI1 (Markdown Data Backend) must be complete
- Phase CLI2 (Track/Phase/Task Commands) must be complete

## Notes

- AI discussion is the most complex part of the CLI track
- Start with simple actions and expand
- Consider rate limiting for API calls
- Handle network errors gracefully
- Store conversation history for learning/debugging

## Estimated Complexity: High (2-3 weeks total)

- Week 1: Core module (3.1), Editor mode (3.2)
- Week 2: Terminal mode (3.3), Action processor (3.4)
- Week 3: Commands (3.5), AI integration (3.6)

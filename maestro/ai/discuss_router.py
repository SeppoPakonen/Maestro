"""Unified discussion router for all AI chat interactions."""

import json
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass

from maestro.config.settings import get_settings
from maestro.ai.manager import AiEngineManager
from maestro.ai.types import AiEngineName, PromptRef, RunOpts
from maestro.ai.runner import run_engine_command


class PatchOperationType(Enum):
    """Types of allowed patch operations."""
    ADD_TRACK = "add_track"
    ADD_PHASE = "add_phase"
    ADD_TASK = "add_task"
    MOVE_TASK = "move_task"
    EDIT_TASK_FIELDS = "edit_task_fields"
    MARK_DONE = "mark_done"
    MARK_TODO = "mark_todo"


@dataclass
class PatchOperation:
    """A single patch operation."""
    op_type: PatchOperationType
    data: Dict[str, Any]


@dataclass
class JsonContract:
    """Definition of a JSON contract for validation."""
    schema_id: str
    validation_func: Callable[[Any], bool]
    allowed_operations: List[PatchOperationType]
    description: str = ""


class DiscussionRouter:
    """Unified router for all AI discussion interactions."""

    def __init__(self, manager: AiEngineManager):
        self.manager = manager
        self.settings = get_settings()
        self.last_json_error: Optional[str] = None

    def run_discussion(
        self,
        engine: AiEngineName,
        initial_prompt: str,
        mode: Optional[str] = None,
        json_contract: Optional[JsonContract] = None,
        safe_mode: bool = False,
        model: Optional[str] = None
    ) -> List[PatchOperation]:
        """
        Run a discussion with the specified engine and settings.

        Args:
            engine: The AI engine to use
            initial_prompt: Initial prompt to start the discussion
            mode: Discussion mode ('editor' or 'terminal'), defaults to settings
            json_contract: Optional JSON contract for validation
            safe_mode: If True, disables dangerous permissions
            model: Optional model override

        Returns:
            List of patch operations if JSON contract is provided
        """
        # Reset JSON error state for this run
        self.last_json_error = None

        # Determine mode from parameter or settings
        discussion_mode = mode or self.settings.discussion_mode or "terminal"

        # Build run options
        opts = RunOpts(
            dangerously_skip_permissions=not safe_mode and self.settings.ai_dangerously_skip_permissions,
            continue_latest=False,
            resume_id=None,
            stream_json=True,  # Enable streaming for consistent output
            quiet=False,
            model=model
        )

        if discussion_mode == "editor":
            return self._run_editor_discussion(engine, initial_prompt, opts, json_contract)
        else:
            return self._run_terminal_discussion(engine, initial_prompt, opts, json_contract)

    def extract_json_from_text(self, response: str) -> Optional[str]:
        """Expose JSON extraction for replay and tests."""
        return self._extract_json_from_response(response)

    def process_json_payload(
        self,
        payload: Any,
        json_contract: JsonContract
    ) -> List[PatchOperation]:
        """Validate and convert a JSON payload into patch operations."""
        self.last_json_error = None

        if payload is None:
            self.last_json_error = "No JSON payload provided."
            print(self.last_json_error)
            return []

        if isinstance(payload, str):
            json_content = self._extract_json_from_response(payload) or payload
            if not json_content or not json_content.strip():
                self.last_json_error = "Empty JSON payload provided."
                print(self.last_json_error)
                return []
            try:
                parsed_json = json.loads(json_content)
            except json.JSONDecodeError as e:
                self.last_json_error = f"Error parsing JSON: {e}"
                print(self.last_json_error)
                return []
        else:
            parsed_json = payload

        if not json_contract.validation_func(parsed_json):
            self.last_json_error = "JSON does not match the required schema."
            print(self.last_json_error)
            return []

        return self._convert_to_patch_operations(parsed_json, json_contract.allowed_operations)

    def _run_editor_discussion(
        self,
        engine: AiEngineName,
        initial_prompt: str,
        opts: RunOpts,
        json_contract: Optional[JsonContract]
    ) -> List[PatchOperation]:
        """Run discussion in editor mode."""
        print(f"Editor mode discussion with {engine}")
        print(f"Initial prompt: {initial_prompt}")

        # This would normally open an editor with a template
        # For now, just return an empty list or handle the basic case
        return []

    def _run_terminal_discussion(
        self,
        engine: AiEngineName,
        initial_prompt: str,
        opts: RunOpts,
        json_contract: Optional[JsonContract]
    ) -> List[PatchOperation]:
        """Run discussion in terminal mode."""
        print(f"Starting terminal discussion with {engine}")
        print("Enter your message (use '/done' to finish, '/quit' to exit, Ctrl+J for newline):")

        # Process initial prompt if provided
        if initial_prompt:
            prompt_ref = PromptRef(source=initial_prompt)
            try:
                cmd = self.manager.build_command(engine, prompt_ref, opts)
                result = run_engine_command(engine, cmd, stream=True, stream_json=opts.stream_json, quiet=opts.quiet)
                print(f"Response: {result.stdout_text}")
            except ValueError as e:
                print(f"Error: {e}")
                return []
            except NotImplementedError as e:
                print(f"Transport mode error: {e}")
                return []

        # Main chat loop
        conversation_history = [initial_prompt] if initial_prompt else []

        while True:
            try:
                user_input = self._read_multiline_input()
            except KeyboardInterrupt:
                print("\n[Interrupted]")
                return []

            if user_input.lower() == '/quit':
                print("Exiting chat...")
                return []
            elif user_input.lower() == '/done':
                print("Finishing discussion...")
                if json_contract:
                    # Process final JSON output
                    return self._process_json_contract(engine, user_input, json_contract, opts)
                else:
                    return []
            elif user_input.lower() == '/help':
                self._print_help()
                continue

            # Process the user input
            prompt_ref = PromptRef(source=user_input)
            try:
                cmd = self.manager.build_command(engine, prompt_ref, opts)
                result = run_engine_command(engine, cmd, stream=True, stream_json=opts.stream_json, quiet=opts.quiet)
                print(f"AI: {result.stdout_text}")
                conversation_history.append(user_input)
            except ValueError as e:
                print(f"Error: {e}")
            except NotImplementedError as e:
                print(f"Transport mode error: {e}")

        return []

    def _read_multiline_input(self) -> str:
        """Read multiline input from terminal."""
        lines = []
        print("You: ", end='', flush=True)

        try:
            line = input()
            lines.append(line)
        except EOFError:
            pass

        return '\n'.join(lines)

    def _print_help(self) -> None:
        """Print help information."""
        print("Commands:")
        print("  /done  - finish and process final output")
        print("  /quit  - exit without finishing")
        print("  /help  - show this help")
        print("Note: Use \\n in text for newlines if needed.")

    def _process_json_contract(
        self,
        engine: AiEngineName,
        final_input: str,
        json_contract: JsonContract,
        opts: RunOpts
    ) -> List[PatchOperation]:
        """Process the final JSON output based on the contract."""
        # Create a prompt asking for JSON output
        json_prompt = f"{final_input}\n\nPlease respond with a JSON object that matches the required schema. Only return the JSON, nothing else."
        prompt_ref = PromptRef(source=json_prompt)

        try:
            cmd = self.manager.build_command(engine, prompt_ref, opts)
            result = run_engine_command(engine, cmd, stream=False, stream_json=opts.stream_json, quiet=True)

            if result.exit_code != 0:
                print(f"Error getting JSON response: {result.stderr_text}")
                return []

            # Extract and parse the JSON from the response
            response_text = result.stdout_text.strip()

            # Find JSON in the response (might be surrounded by other text)
            json_content = self._extract_json_from_response(response_text)

            if not json_content:
                self.last_json_error = "No valid JSON found in response."
                print(self.last_json_error)
                return []

            # Check if the response is empty before attempting JSON parsing
            if not json_content.strip():
                self.last_json_error = "Empty JSON payload returned by engine."
                print("Qwen returned no assistant payload; enable -v to see stream events and stderr.")
                return []

            try:
                parsed_json = json.loads(json_content)
            except json.JSONDecodeError as e:
                self.last_json_error = f"Error parsing JSON: {e}"
                print(self.last_json_error)
                print("Qwen returned no assistant payload; enable -v to see stream events and stderr.")
                return []

            # Validate the JSON against the contract
            if not json_contract.validation_func(parsed_json):
                self.last_json_error = "JSON does not match the required schema."
                print(self.last_json_error)
                return []

            # Convert the JSON to patch operations based on allowed operations
            return self._convert_to_patch_operations(parsed_json, json_contract.allowed_operations)

        except ValueError as e:
            self.last_json_error = f"Error processing JSON contract: {e}"
            print(self.last_json_error)
            return []
        except NotImplementedError as e:
            self.last_json_error = f"Transport mode error: {e}"
            print(self.last_json_error)
            return []

    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """Extract JSON content from AI response which may contain other text."""
        # Try to find JSON within the response
        lines = response.split('\n')

        # Look for JSON delimiters
        json_start = -1
        json_end = -1

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('{') or stripped.startswith('['):
                json_start = i
                break
            elif stripped.startswith('```json'):
                json_start = i + 1
                break
            elif stripped.startswith('```'):
                json_start = i + 1
                break

        if json_start != -1:
            # Look for the end of the JSON
            brace_count = 0
            bracket_count = 0
            in_json = False

            for i, line in enumerate(lines[json_start:], start=json_start):
                for char in line:
                    if char == '{':
                        brace_count += 1
                        in_json = True
                    elif char == '}':
                        brace_count -= 1
                    elif char == '[':
                        bracket_count += 1
                        in_json = True
                    elif char == ']':
                        bracket_count -= 1

                if in_json and brace_count == 0 and bracket_count == 0:
                    json_end = i + 1
                    break

            if json_end != -1:
                extracted = '\n'.join(lines[json_start:json_end])
                return extracted.strip()

        # If we couldn't identify specific delimiters, try to parse the whole response
        try:
            # Test if the entire response is valid JSON
            json.loads(response)
            return response
        except json.JSONDecodeError:
            pass

        return None

    def _convert_to_patch_operations(self, json_data: Any, allowed_operations: List[PatchOperationType]) -> List[PatchOperation]:
        """Convert JSON data to patch operations based on allowed operations."""
        operations = []

        if isinstance(json_data, list):
            # If it's a list, process each item
            for item in json_data:
                ops = self._convert_single_item(item, allowed_operations)
                operations.extend(ops)
        elif isinstance(json_data, dict):
            # If it's a single object, process it
            operations = self._convert_single_item(json_data, allowed_operations)

        # Filter operations to only allow those in the contract
        filtered_operations = [
            op for op in operations
            if op.op_type in allowed_operations
        ]

        return filtered_operations

    def _convert_single_item(self, item: Dict[str, Any], allowed_operations: List[PatchOperationType]) -> List[PatchOperation]:
        """Convert a single JSON item to patch operations."""
        operations = []

        if not isinstance(item, dict):
            return operations

        # Check for operation type in the item
        op_type_str = item.get("op_type", item.get("operation", item.get("type", "")))

        try:
            op_type = PatchOperationType(op_type_str)

            # Add the operation if it's allowed
            if op_type in allowed_operations:
                operation = PatchOperation(
                    op_type=op_type,
                    data={k: v for k, v in item.items() if k not in ["op_type", "operation", "type"]}
                )
                operations.append(operation)
        except ValueError:
            # If the op_type is not recognized, try to infer from keys
            if "track_name" in item and "add_track" in [op.value for op in allowed_operations]:
                operations.append(PatchOperation(
                    op_type=PatchOperationType.ADD_TRACK,
                    data=item
                ))
            elif "phase_name" in item and "add_phase" in [op.value for op in allowed_operations]:
                operations.append(PatchOperation(
                    op_type=PatchOperationType.ADD_PHASE,
                    data=item
                ))
            elif "task_name" in item and "add_task" in [op.value for op in allowed_operations]:
                operations.append(PatchOperation(
                    op_type=PatchOperationType.ADD_TASK,
                    data=item
                ))
            elif "status" in item and item["status"] in ["done", "completed"] and "mark_done" in [op.value for op in allowed_operations]:
                operations.append(PatchOperation(
                    op_type=PatchOperationType.MARK_DONE,
                    data=item
                ))
            elif "status" in item and item["status"] in ["todo", "pending"] and "mark_todo" in [op.value for op in allowed_operations]:
                operations.append(PatchOperation(
                    op_type=PatchOperationType.MARK_TODO,
                    data=item
                ))

        return operations

    def save_transcript(self, topic: str, content: str) -> Path:
        """Save discussion transcript to artifacts."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        transcript_dir = Path("docs/maestro/ai/transcripts") / topic
        transcript_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{timestamp}_transcript.json"
        filepath = transcript_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"timestamp": timestamp, "content": content}, f, indent=2)

        return filepath

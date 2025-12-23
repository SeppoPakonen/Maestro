"""Chat interface for the unified AI Engine Manager."""

import sys
from typing import Optional, List
from .manager import AiEngineManager
from .types import AiEngineName, PromptRef, RunOpts
from .runner import run_engine_command


def run_interactive_chat(
    manager: AiEngineManager,
    engine: AiEngineName,
    opts: RunOpts,
    initial_prompt: Optional[str] = None
) -> None:
    """
    Run an interactive chat session with the specified engine.
    """
    print(f"Starting interactive chat with {engine} engine")
    if initial_prompt:
        print(f"Initial prompt: {initial_prompt}")

    # Process initial prompt if provided
    if initial_prompt:
        prompt_ref = PromptRef(source=initial_prompt)
        try:
            if engine == "qwen":
                # For Qwen, we need to handle transport mode
                cmd = manager.build_command(engine, prompt_ref, opts)
                result = run_engine_command(engine, cmd, stream=True, stream_json=opts.stream_json, quiet=opts.quiet)
            else:
                cmd = manager.build_command(engine, prompt_ref, opts)
                result = run_engine_command(engine, cmd, stream=True, stream_json=opts.stream_json, quiet=opts.quiet)
            print(f"Exit code: {result.exit_code}")
            if result.session_id:
                print(f"Session ID: {result.session_id}")
        except ValueError as e:
            print(f"Error: {e}")
            return
        except NotImplementedError as e:
            print(f"Transport mode error: {e}")
            return

    # Main chat loop
    print("Enter your message (use '/done' to finish, '/quit' to exit, Ctrl+J for newline):")
    while True:
        try:
            user_input = _read_multiline_input()
        except KeyboardInterrupt:
            print("\n[Interrupted]")
            break

        if user_input.lower() == '/quit':
            print("Exiting chat...")
            break
        elif user_input.lower() == '/done':
            print("Done.")
            break
        elif user_input.lower() == '/help':
            _print_help()
            continue

        # Process the user input
        prompt_ref = PromptRef(source=user_input)
        try:
            if engine == "qwen":
                # For Qwen, we need to handle transport mode
                cmd = manager.build_command(engine, prompt_ref, opts)
                result = run_engine_command(engine, cmd, stream=True, stream_json=opts.stream_json, quiet=opts.quiet)
            else:
                cmd = manager.build_command(engine, prompt_ref, opts)
                result = run_engine_command(engine, cmd, stream=True, stream_json=opts.stream_json, quiet=opts.quiet)
            print(f"Exit code: {result.exit_code}")
            if result.session_id:
                print(f"Session ID: {result.session_id}")
        except ValueError as e:
            print(f"Error: {e}")
        except NotImplementedError as e:
            print(f"Transport mode error: {e}")


def run_one_shot(
    manager: AiEngineManager,
    engine: AiEngineName,
    prompt: str,
    opts: RunOpts
) -> None:
    """
    Run a one-shot query with the specified engine.
    """
    prompt_ref = PromptRef(source=prompt)
    try:
        if engine == "qwen":
            # For Qwen, we need to handle transport mode
            cmd = manager.build_command(engine, prompt_ref, opts)
            result = run_engine_command(engine, cmd, stream=True, stream_json=opts.stream_json, quiet=opts.quiet)
        else:
            cmd = manager.build_command(engine, prompt_ref, opts)
            result = run_engine_command(engine, cmd, stream=True, stream_json=opts.stream_json, quiet=opts.quiet)
        print(f"Exit code: {result.exit_code}")
        if result.session_id:
            print(f"Session ID: {result.session_id}")
        return result
    except ValueError as e:
        print(f"Error: {e}")
    except NotImplementedError as e:
        print(f"Transport mode error: {e}")


def _read_multiline_input() -> str:
    """
    Read multiline input from user.
    Allows for Ctrl+J-like functionality by using special syntax.
    """
    lines: List[str] = []
    print("You: ", end='', flush=True)

    # For now, we'll read a single line
    # In a more advanced implementation, we might support multiline input
    line = input()

    # Process special commands that might span multiple lines
    # For now, just return the single line
    return line


def _print_help() -> None:
    """Print help information for the chat interface."""
    print("Commands:")
    print("  /done  - finish and exit")
    print("  /quit  - exit without finishing")
    print("  /help  - show this help")
    print("Note: Use \\n in text for newlines if needed.")
"""Chat interface for the unified AI Engine Manager."""

import sys
from typing import Optional, List
from .manager import AiEngineManager
from .types import AiEngineName, PromptRef, RunOpts
from .runner import run_engine_command
from .stream_render import StreamRenderer


def run_interactive_chat(
    manager: AiEngineManager,
    engine: AiEngineName,
    opts: RunOpts,
    initial_prompt: Optional[str] = None
) -> None:
    """
    Run an interactive chat session with the specified engine.
    """
    verbose = getattr(opts, 'verbose', False)
    renderer = StreamRenderer(engine, verbose=verbose)

    print(f"Starting interactive chat with {engine} engine")
    if initial_prompt:
        print(f"Initial prompt: {initial_prompt}")

    # Process initial prompt if provided
    if initial_prompt:
        prompt_ref = PromptRef(source=initial_prompt)
        try:
            result = manager.run_once(engine, prompt_ref, opts)
            renderer.finalize(result.exit_code)
        except ValueError as e:
            print(f"Error: {e}")
            renderer.handle_interrupt()
            return
        except NotImplementedError as e:
            print(f"Transport mode error: {e}")
            renderer.handle_interrupt()
            return
        except KeyboardInterrupt:
            renderer.handle_interrupt()
            return

    # Main chat loop
    print("Enter your message (use '/done' to finish, '/quit' to exit, Ctrl+J for newline):")
    while True:
        try:
            user_input = _read_multiline_input()
        except KeyboardInterrupt:
            renderer.handle_interrupt()
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
            # Update opts to use the session ID from the session manager if available
            updated_opts = opts
            if opts.continue_latest and not opts.resume_id:
                # If continue_latest is set and no specific resume_id, get the last session ID
                last_session_id = manager.session_manager.get_last_session_id(engine)
                if last_session_id:
                    updated_opts = RunOpts(
                        dangerously_skip_permissions=opts.dangerously_skip_permissions,
                        continue_latest=False,  # We're now using a specific session ID
                        resume_id=last_session_id,
                        stream_json=opts.stream_json,
                        quiet=opts.quiet,
                        model=opts.model,
                        extra_args=opts.extra_args,
                        verbose=opts.verbose if hasattr(opts, 'verbose') else False
                    )

            result = manager.run_once(engine, prompt_ref, updated_opts)
            renderer.finalize(result.exit_code)
        except ValueError as e:
            print(f"Error: {e}")
        except NotImplementedError as e:
            print(f"Transport mode error: {e}")
        except KeyboardInterrupt:
            renderer.handle_interrupt()
            break


def run_one_shot(
    manager: AiEngineManager,
    engine: AiEngineName,
    prompt: str,
    opts: RunOpts
) -> None:
    """
    Run a one-shot query with the specified engine.
    """
    verbose = getattr(opts, 'verbose', False)
    renderer = StreamRenderer(engine, verbose=verbose)

    prompt_ref = PromptRef(source=prompt)
    try:
        # Update opts to use the session ID from the session manager if available
        updated_opts = opts
        if opts.continue_latest and not opts.resume_id:
            # If continue_latest is set and no specific resume_id, get the last session ID
            last_session_id = manager.session_manager.get_last_session_id(engine)
            if last_session_id:
                updated_opts = RunOpts(
                    dangerously_skip_permissions=opts.dangerously_skip_permissions,
                    continue_latest=False,  # We're now using a specific session ID
                    resume_id=last_session_id,
                    stream_json=opts.stream_json,
                    quiet=opts.quiet,
                    model=opts.model,
                    extra_args=opts.extra_args,
                    verbose=opts.verbose if hasattr(opts, 'verbose') else False
                )

        result = manager.run_once(engine, prompt_ref, updated_opts)

        # Check if Qwen returned an empty assistant payload
        if engine == "qwen" and result.stdout_path:
            # Read the stdout to check if it's empty
            try:
                with open(result.stdout_path, 'r', encoding='utf-8') as f:
                    stdout_content = f.read()
                    if not stdout_content.strip():
                        print("Qwen returned no assistant payload; enable -v to see stream events and stderr.")
            except:
                pass  # If we can't read the file, continue normally

        renderer.finalize(result.exit_code)
        return result
    except ValueError as e:
        print(f"Error: {e}")
        renderer.handle_interrupt()
    except NotImplementedError as e:
        print(f"Transport mode error: {e}")
        renderer.handle_interrupt()
    except KeyboardInterrupt:
        renderer.handle_interrupt()


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
#!/usr/bin/env python3
"""
Stub qwen for deterministic testing.

Reads a prompt from stdin and outputs deterministic stream-json responses.
"""

import json
import sys


def main():
    # Read prompt from stdin
    prompt = sys.stdin.read()

    # Deterministic responses based on prompt content
    if "first step" in prompt.lower() or "starting" in prompt.lower():
        # Initial prompt - respond with help command
        response = {
            "next_command": "maestro --help",
            "note": "Starting with top-level help",
            "done": False
        }
        print(json.dumps(response))

    elif "maestro --help" in prompt and "exit code" in prompt.lower():
        # After seeing maestro --help output
        response = {
            "next_command": "maestro runbook --help",
            "note": "Exploring runbook subcommand",
            "done": False
        }
        print(json.dumps(response))

    elif "maestro runbook --help" in prompt:
        # After seeing runbook help
        response = {
            "next_command": "maestro runbook list",
            "note": "Checking existing runbooks",
            "done": False
        }
        print(json.dumps(response))

    elif "maestro runbook list" in prompt:
        # After seeing runbook list
        response = {
            "done": True,
            "note": "Goal accomplished: explored runbook commands"
        }
        print(json.dumps(response))

    else:
        # Default: emit done
        response = {
            "done": True,
            "note": "Unknown state, stopping"
        }
        print(json.dumps(response))


if __name__ == '__main__':
    main()

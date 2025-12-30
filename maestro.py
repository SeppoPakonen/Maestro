#!/usr/bin/env python3
"""
Maestro - AI Task Management CLI

This is the main entry point for the Maestro AI task orchestrator.
"""

import os
import sys


def _has_help_flag(argv):
    return "-h" in argv or "--help" in argv


def _resolve_help_command(argv):
    if not argv:
        return None
    raw = argv[0]
    if raw.startswith("-"):
        return None
    alias_map = {
        "b": "make",
        "build": "make",
        "m": "make",
        "s": "session",
        "u": "understand",
        "r": "rules",
        "p": "phase",
        "t": "track",
        "l": "log",
        "c": "convert",
        "wk": "work",
        "ws": "wsession",
        "runba": "runbook",
        "rb": "runbook",
    }
    return alias_map.get(raw, raw)


def _legacy_enabled():
    value = os.environ.get("MAESTRO_ENABLE_LEGACY", "0").lower()
    return value in ("1", "true", "yes")


def _print_legacy_disabled(command_name, replacement):
    print(f"[DEPRECATED] '{command_name}' command is not available.", file=sys.stderr)
    print(f"Use: maestro {replacement} instead.", file=sys.stderr)
    print("", file=sys.stderr)
    print("To enable legacy commands (for backward compatibility):", file=sys.stderr)
    print("  export MAESTRO_ENABLE_LEGACY=1", file=sys.stderr)
    print("", file=sys.stderr)
    print("See: docs/workflows/v3/cli/CLI_SURFACE_CONTRACT.md", file=sys.stderr)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if _has_help_flag(argv):
        from maestro.modules.cli_parser import create_main_parser

        raw_command = argv[0] if argv else None
        help_command = _resolve_help_command(argv)
        legacy_commands = {"session", "resume", "rules", "root", "understand"}
        include_legacy = None
        if help_command in legacy_commands:
            if not _legacy_enabled():
                legacy_map = {
                    "session": "wsession",
                    "understand": "repo resolve / runbook export",
                    "resume": "discuss resume / work resume",
                    "rules": "repo conventions / solutions",
                    "root": "track / phase / task",
                }
                replacement = legacy_map.get(help_command, "canonical commands")
                _print_legacy_disabled(help_command, replacement)
                sys.exit(1)
            include_legacy = True

        help_argv = list(argv)
        if raw_command in ("build", "b"):
            print(
                "Warning: 'maestro build' is deprecated; use 'maestro make' instead. "
                "This alias will be removed after two minor releases.",
                file=sys.stderr,
            )
            if help_argv:
                help_argv[0] = "make"
            help_command = "make"
        elif help_command in legacy_commands:
            legacy_map = {
                "session": "wsession",
                "understand": "repo resolve / runbook export",
                "resume": "discuss resume / work resume",
                "rules": "repo conventions / solutions",
                "root": "track / phase / task",
            }
            replacement = legacy_map.get(help_command, "canonical commands")
            print(f"Warning: '{help_command}' is deprecated; use '{replacement}' instead.", file=sys.stderr)

        commands_to_load = [help_command] if help_command else None
        parser = create_main_parser(
            commands_to_load=commands_to_load,
            include_legacy=include_legacy,
            show_banner=False,
        )
        parser.parse_args(help_argv)
        sys.exit(0)

    from maestro.main import main

    main()

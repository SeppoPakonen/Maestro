#!/usr/bin/env python3
"""
Entry point for running maestro as a module: python -m maestro
"""

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


if __name__ == '__main__':
    argv = sys.argv[1:]
    if _has_help_flag(argv):
        from maestro.modules.cli_parser import create_main_parser

        raw_command = argv[0] if argv else None
        help_command = _resolve_help_command(argv)
        include_legacy = None
        legacy_commands = {"session", "resume", "rules", "root", "understand"}
        if help_command in legacy_commands:
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

        commands_to_load = [help_command] if help_command else None
        parser = create_main_parser(
            commands_to_load=commands_to_load,
            include_legacy=include_legacy,
        )
        parser.parse_args(help_argv)
        sys.exit(0)

    from maestro.main import main

    main()

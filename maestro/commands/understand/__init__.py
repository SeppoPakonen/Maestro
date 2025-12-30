"""
Understand command module for Maestro CLI commands.
This wrapper keeps import-time side effects minimal for fast help paths.
"""


def add_understand_parser(subparsers):
    from maestro.understand.parser import add_understand_parser as _add_understand_parser

    return _add_understand_parser(subparsers)


def handle_understand_dump(*args, **kwargs):
    from maestro.understand.command import handle_understand_dump as _handle_understand_dump

    return _handle_understand_dump(*args, **kwargs)


__all__ = [
    "handle_understand_dump",
    "add_understand_parser",
]

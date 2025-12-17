"""
UI-facing helper for running the Maestro `make` command family.
"""
from __future__ import annotations

import argparse
import io
import os
import shlex
from contextlib import redirect_stdout, redirect_stderr
from typing import Tuple

from maestro.commands.make import add_make_parser, MakeCommand


def run_make_command(command_line: str, cwd: str | None = None) -> Tuple[int, str]:
    """
    Run a make subcommand and capture its output.

    Args:
        command_line: The make subcommand line (e.g. "methods", "config detect", "build PkgX").
        cwd: Optional working directory to run the command from.

    Returns:
        (exit_code, combined_output)
    """
    if not command_line or not command_line.strip():
        return (
            1,
            "No make subcommand provided. Try one of: methods, config detect, build <pkg>, clean <pkg>.",
        )

    # Tokenize the command line and strip a leading "make"/"m" if present.
    args_list = shlex.split(command_line)
    if args_list and args_list[0] in ("make", "m"):
        args_list = args_list[1:]

    output_buffer = io.StringIO()
    exit_code = 0

    # Build a parser that mimics the CLI structure and grab the make parser.
    root_parser = argparse.ArgumentParser(prog="maestro-make", add_help=False)
    subparsers = root_parser.add_subparsers(dest="command")
    make_parser = add_make_parser(subparsers)

    original_cwd = os.getcwd()
    try:
        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
            try:
                parsed_args = make_parser.parse_args(args_list)
            except SystemExit as exc:
                # argparse already wrote help/error to buffer
                code = exc.code if isinstance(exc.code, int) else 1
                return code, output_buffer.getvalue()

            if not getattr(parsed_args, "make_subcommand", None):
                make_parser.print_help()
                return 1, output_buffer.getvalue()

            if cwd:
                os.chdir(cwd)

            make_cmd = MakeCommand()
            try:
                exit_code = make_cmd.execute(parsed_args)
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else 1
    finally:
        if cwd:
            os.chdir(original_cwd)

    return exit_code, output_buffer.getvalue()

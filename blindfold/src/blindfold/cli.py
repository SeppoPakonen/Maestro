"""Blindfold CLI module."""

import sys
import argparse
from .core import run, run_admin

def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--HIDDEN", action="store_true")
    parser.add_argument("--FEEDBACK", action="store_true")

    # Parse known args to allow for blind command tokens
    args, remainder = parser.parse_known_args()

    if args.version:
        print("0.0.0")
        sys.exit(0)

    # Read stdin fully
    stdin_text = sys.stdin.read()

    # Determine mode and call core.run
    if args.HIDDEN:
        if not remainder:
            # --HIDDEN alone (no subcommand) should print help for admin subcommands and exit 4
            print("usage: python -m blindfold --HIDDEN <subcommand> [args]")
            print("subcommands:")
            print("  list-errors")
            print("  show-error <cookie>")
            print("  list-feedback")
            print("  show-feedback <cookie>")
            print("  add-mapping --argv \"<space separated tokens>\" --interface <filename.yaml> [--id <id>] [--notes <text>]")
            print("  gc --older-than <duration>")
            sys.exit(4)

        # Parse admin subcommand
        subcommand = remainder[0]
        subcommand_args = remainder[1:]

        exit_code, stdout_text, stderr_text = run_admin(subcommand, subcommand_args)
    elif args.FEEDBACK:
        # For feedback mode, the first remainder item is the cookie
        if len(remainder) == 0:
            sys.stderr.write("missing cookie for --FEEDBACK\n")
            sys.exit(3)
        elif len(remainder) > 1:
            # For now, ignore additional arguments but could error if desired
            pass

        # Use only the first argument as the cookie
        cookie_arg = [remainder[0]]
        exit_code, stdout_text, stderr_text = run(mode="feedback", command_argv=cookie_arg, stdin_text=stdin_text)
    else:
        # Default behavior: if remainder is empty, run blind with no command; otherwise treat as blind command attempt
        if len(remainder) == 0:
            exit_code, stdout_text, stderr_text = run(mode="blind", command_argv=remainder, stdin_text=stdin_text)
        else:
            exit_code, stdout_text, stderr_text = run(mode="blind", command_argv=remainder, stdin_text=stdin_text)

    # Write outputs
    sys.stdout.write(stdout_text)
    if stderr_text:
        sys.stderr.write(stderr_text)

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
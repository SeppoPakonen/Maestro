"""
Import-safe entrypoint for Maestro TUI.

MC2 mode must be able to run without Textual installed.
"""

import argparse
import os
import sys


def parse_args(argv=None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Maestro TUI")
    parser.add_argument("--smoke", action="store_true", help="Run in smoke test mode (exit after rendering)")
    parser.add_argument(
        "--smoke-seconds",
        type=float,
        default=0.5,
        help="Time to keep smoke mode alive before exiting (default: 0.5)",
    )
    parser.add_argument("--smoke-out", type=str, help="File path to write success marker (optional)")
    parser.add_argument("--mc", action="store_true", help="Run in MC shell mode")
    parser.add_argument("--mc2", action="store_true", help="Run in MC2 curses mode (alternative MC implementation)")
    parser.add_argument("--render-debug", action="store_true", help="Show MC2 render debug overlay/counters")
    parser.add_argument("--ide", action="store_true", help="Start directly in IDE view (alias for --navigation ide)")
    parser.add_argument(
        "--navigation",
        type=str,
        help="Start in a specific navigation target (e.g. ide, repo, home, tasks, build)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show verbose error output")
    return parser.parse_args(argv)


def _print_textual_missing():
    message = (
        "Textual UI requires the optional dependency 'textual'.\n"
        "Install it with: pip install .[tui]\n"
        "Or run MC2 mode: python -m maestro.tui --mc2\n"
    )
    print(message, file=sys.stderr)


def _run_textual(args):
    try:
        from maestro.tui.app import main as textual_main
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.split(".")[0] == "textual":
            if args.verbose:
                raise
            _print_textual_missing()
            raise SystemExit(1) from None
        raise

    navigation_target = args.navigation or ("ide" if args.ide else None)

    textual_main(
        smoke_mode=args.smoke,
        smoke_seconds=args.smoke_seconds,
        smoke_out=args.smoke_out,
        mc_shell=args.mc,
        mc2_mode=False,
        render_debug=args.render_debug,
        navigation_target=navigation_target,
    )


def main(argv=None):
    """Main function called from entrypoints."""
    if argv is None:
        argv = sys.argv[1:]
        if len(argv) >= 2 and argv[0] == "-m" and argv[1].startswith("maestro.tui"):
            argv = argv[2:]
        elif argv and argv[0].startswith("maestro.tui"):
            argv = argv[1:]

    args = parse_args(argv)

    if args.smoke_out:
        os.environ["MAESTRO_SMOKE_SUCCESS_FILE"] = args.smoke_out

    if args.smoke and not sys.stdout.isatty() and not args.mc and not args.mc2:
        from maestro.tui_mc2.app import main as mc2_main

        status = mc2_main(
            smoke_mode=True,
            smoke_seconds=args.smoke_seconds,
            smoke_out=args.smoke_out,
            mc2_mode=True,
            render_debug=args.render_debug,
        )
        if isinstance(status, int) and status != 0:
            raise SystemExit(status)
        return

    if args.mc2:
        from maestro.tui_mc2.app import main as mc2_main

        status = mc2_main(
            smoke_mode=args.smoke,
            smoke_seconds=args.smoke_seconds,
            smoke_out=args.smoke_out,
            mc2_mode=True,
            render_debug=args.render_debug,
        )
        if isinstance(status, int) and status != 0:
            raise SystemExit(status)
        return

    _run_textual(args)

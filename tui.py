#!/usr/bin/env python3
"""
Maestro TUI Main Entry Point

This module serves as the primary entry point to launch the Maestro Text-based User Interface.
"""

import argparse
import os

from maestro.tui.app import main


def parse_args():
    """Parse CLI arguments for direct script usage."""
    parser = argparse.ArgumentParser(description="Maestro TUI")
    parser.add_argument("--smoke", action="store_true", help="Run in smoke test mode (exit after rendering)")
    parser.add_argument(
        "--smoke-seconds",
        type=float,
        default=0.5,
        help="Time to keep smoke mode alive before exiting (default: 0.5)",
    )
    parser.add_argument("--smoke-out", type=str, help="File path to write success marker (optional)")
    parser.add_argument("--mc", action="store_true", help="Start in Midnight Commander shell")
    return parser.parse_args()


def run_tui():
    """Launch the Maestro TUI application."""
    args = parse_args()
    if args.smoke_out:
        os.environ["MAESTRO_SMOKE_SUCCESS_FILE"] = args.smoke_out
    main(smoke_mode=args.smoke, smoke_seconds=args.smoke_seconds, smoke_out=args.smoke_out, mc_shell=args.mc)


if __name__ == "__main__":
    run_tui()

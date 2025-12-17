"""
Module entry point for Maestro TUI.

This allows running the TUI with:
  python -m maestro.tui [options]
"""

import sys
import argparse
from .app import main

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Maestro TUI")
    parser.add_argument("--smoke", action="store_true", help="Run in smoke test mode (exit after rendering)")
    parser.add_argument("--smoke-seconds", type=float, default=0.5, help="Time to keep smoke mode alive before exiting (default: 0.5)")
    parser.add_argument("--smoke-out", type=str, help="File path to write success marker (optional)")
    parser.add_argument("--mc", action="store_true", help="Run in MC shell mode")
    parser.add_argument("--mc2", action="store_true", help="Run in MC2 curses mode (alternative MC implementation)")

    return parser.parse_args()

def main_module():
    """Main function called when running as a module."""
    args = parse_args()

    # Set environment variable for success file if specified
    if args.smoke_out:
        import os
        os.environ["MAESTRO_SMOKE_SUCCESS_FILE"] = args.smoke_out

    # Call the app's main function with smoke parameters and mc mode
    main(smoke_mode=args.smoke, smoke_seconds=args.smoke_seconds, smoke_out=args.smoke_out, mc_shell=args.mc, mc2_mode=args.mc2)

if __name__ == "__main__":
    main_module()

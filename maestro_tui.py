#!/usr/bin/env python3
"""
Maestro TUI Entry Point

This serves as the main entry point for the Text-based User Interface.
It provides an interactive human interface that complements the CLI.
"""

import sys
import argparse
from maestro.tui.app import main

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Maestro TUI")
    parser.add_argument("--smoke", action="store_true", help="Run in smoke test mode (exit after rendering)")
    parser.add_argument("--smoke-seconds", type=float, default=0.5, help="Time to keep smoke mode alive before exiting (default: 0.5)")

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(smoke_mode=args.smoke, smoke_seconds=args.smoke_seconds)
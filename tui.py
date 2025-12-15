#!/usr/bin/env python3
"""
Maestro TUI Main Entry Point

This module serves as the primary entry point to launch the Maestro Text-based User Interface.
"""

from maestro.tui.app import main


def run_tui():
    """
    Launch the Maestro TUI application.
    """
    main()


if __name__ == "__main__":
    run_tui()
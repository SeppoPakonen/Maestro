"""
Onboarding utilities for Maestro TUI

Manages first-run onboarding flow and state persistence
"""
import json
import os
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class OnboardingStep:
    """Represents a single step in the onboarding flow."""
    id: str
    title: str
    description: str
    key_bindings: List[str]
    next_hint: str = ""


class OnboardingManager:
    """Manages the onboarding state and flow."""

    def __init__(self, config_dir: str = "~/.maestro"):
        self.config_dir = Path(config_dir).expanduser()
        self.config_file = self.config_dir / "tui_config.json"
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """Ensure the config directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def is_onboarding_completed(self) -> bool:
        """Check if onboarding has been completed."""
        config = self._load_config()
        return config.get("onboarding_completed", False)

    def mark_onboarding_completed(self) -> None:
        """Mark onboarding as completed."""
        config = self._load_config()
        config["onboarding_completed"] = True
        self._save_config(config)

    def is_legacy_mode_enabled(self) -> bool:
        """Check if legacy mode is enabled."""
        config = self._load_config()
        return config.get("legacy_mode", False)

    def set_legacy_mode(self, enabled: bool) -> None:
        """Enable or disable legacy mode."""
        config = self._load_config()
        config["legacy_mode"] = enabled
        self._save_config(config)

    def _load_config(self) -> Dict[str, Any]:
        """Load the config file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save the config file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except IOError:
            # If we can't save config, log but don't fail the app
            print(f"Warning: Could not save config to {self.config_file}")
    
    @property
    def steps(self) -> List[OnboardingStep]:
        """Get the list of onboarding steps."""
        return [
            OnboardingStep(
                id="welcome",
                title="Welcome to Maestro TUI!",
                description="This is the Maestro orchestration system. It coordinates AI agents to perform complex software development tasks.",
                key_bindings=[],
                next_hint="Press Enter to continue to status indicators..."
            ),
            OnboardingStep(
                id="status_indicators",
                title="Status Indicators",
                description="At the top, you see important status:\n  • Root: Project root directory\n  • Session: Current active session\n  • Phase: Current active phase\n  • Build: Active build target\nThese show your current working context.",
                key_bindings=[],
                next_hint="Press Enter to continue to visual indicators..."
            ),
            OnboardingStep(
                id="visual_indicators",
                title="Visual Status Indicators",
                description="In the interface, you'll see visual indicators:\n  • ✅ Green checkmark for completed items\n  • 🚧 Orange construction for in-progress items\n  • 📋 Clipboard for planned items\n  • 💡 Light bulb for proposed items\n  • Progress bars showing completion\n  • P0/P1/P2 priority indicators with colors\nThese help you quickly understand status.",
                key_bindings=[],
                next_hint="Press Enter to continue to navigation..."
            ),
            OnboardingStep(
                id="navigation",
                title="Navigation",
                description="Use the left sidebar to navigate between different system areas:\n  • Home: Main dashboard\n  • Sessions: Manage work sessions\n  • Phases: Phase tree visualization\n  • Tasks: Individual task management\n  • Convert: Format conversion workflows\n  • And many more...",
                key_bindings=["Home", "Sessions", "Phases", "Tasks"],
                next_hint="Press Enter to continue to read vs write actions..."
            ),
            OnboardingStep(
                id="read_write",
                title="Read vs Write Actions",
                description="Actions are either read-only (safe) or write (potentially dangerous).\n  • Read-only: View information, check status\n  • Write: Create, modify, delete operations\nPay attention to confirmation dialogs for write actions.",
                key_bindings=[],
                next_hint="Press Enter to continue to command palette..."
            ),
            OnboardingStep(
                id="command_palette",
                title="Command Palette",
                description="Press Ctrl+P to open the command palette - a quick way to access any function in the system. Type to search commands, then press Enter to execute.",
                key_bindings=["Ctrl+P"],
                next_hint="Press Enter to continue to completion..."
            ),
            OnboardingStep(
                id="completion",
                title="Onboarding Complete!",
                description="You now know the basics:\n  • Status indicators at the top\n  • Visual status indicators (✅ 🚧 📋 💡)\n  • Navigation on the left\n  • Command palette with Ctrl+P\n  • Read vs write actions\n\nYou can always press ? for help. Happy orchestrating!",
                key_bindings=["?"],
                next_hint="Press Enter to start using Maestro..."
            )
        ]


# Global onboarding manager instance
onboarding_manager = OnboardingManager()
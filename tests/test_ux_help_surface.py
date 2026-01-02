"""
Tests for UX help surface discovery.

All tests are deterministic and use static help text fixtures (no real subprocess).
"""

import pytest
import hashlib
from maestro.ux.help_surface import HelpSurface, HelpNode, DiscoveryBudget


# Fixture: Static help texts for testing
FAKE_MAESTRO_HELP = """usage: maestro [-h] [--version] {plan,repo,ops} ...

Maestro - AI Task Management CLI

optional arguments:
  -h, --help     show this help message and exit
  --version      Show version information

Available commands:
  {plan,repo,ops}
    plan         Plan management commands
    repo         Repository management
    ops          Operations automation
"""

FAKE_PLAN_HELP = """usage: maestro plan [-h] {list,add,show} ...

Plan management commands

optional arguments:
  -h, --help          show this help message and exit

Subcommands:
  {list,add,show}
    list              List all plans
    add               Add a new plan
    show              Show plan details
"""

FAKE_REPO_HELP = """usage: maestro repo [-h] {resolve,refresh} ...

Repository management

optional arguments:
  -h, --help        show this help message and exit

Subcommands:
  {resolve,refresh}
    resolve           Resolve repository structure
    refresh           Refresh repository cache
"""


class FakeHelpSurface(HelpSurface):
    """Test-only HelpSurface that uses fake help text instead of subprocess."""

    def __init__(self, help_map: dict, budget=None, verbose=False):
        """
        Initialize with a map of command_path -> help_text.

        Args:
            help_map: Dictionary mapping tuple(command_path) to help text
        """
        super().__init__(
            maestro_bin="fake_maestro",
            budget=budget,
            verbose=verbose
        )
        self.help_map = help_map

    def _get_help_text(self, command_path):
        """Override to use fake help text."""
        cmd_tuple = tuple(command_path)
        if cmd_tuple in self.help_map:
            self.help_call_count += 1
            return self.help_map[cmd_tuple]
        else:
            # Unknown command
            warning = f"Unknown command: {' '.join(command_path)}"
            self.warnings.append(warning)
            return None


def test_help_surface_basic_discovery():
    """Test basic help surface discovery with fixed help texts."""
    help_map = {
        ('maestro',): FAKE_MAESTRO_HELP,
        ('maestro', 'plan'): FAKE_PLAN_HELP,
        ('maestro', 'repo'): FAKE_REPO_HELP,
    }

    surface = FakeHelpSurface(help_map, verbose=False)
    discovered = surface.discover()

    # Should discover 3 nodes
    assert len(discovered) == 3

    # Check maestro root
    assert ('maestro',) in discovered
    root_node = discovered[('maestro',)]
    assert 'plan' in root_node.discovered_subcommands
    assert 'repo' in root_node.discovered_subcommands
    assert 'ops' in root_node.discovered_subcommands

    # Check plan subcommand
    assert ('maestro', 'plan') in discovered
    plan_node = discovered[('maestro', 'plan')]
    assert 'list' in plan_node.discovered_subcommands
    assert 'add' in plan_node.discovered_subcommands
    assert 'show' in plan_node.discovered_subcommands


def test_help_surface_deterministic_hashes():
    """Test that help hashes are deterministic."""
    help_map = {
        ('maestro',): FAKE_MAESTRO_HELP,
    }

    surface1 = FakeHelpSurface(help_map)
    discovered1 = surface1.discover()

    surface2 = FakeHelpSurface(help_map)
    discovered2 = surface2.discover()

    # Hashes should be identical
    assert discovered1[('maestro',)].help_hash == discovered2[('maestro',)].help_hash

    # Verify hash matches expected SHA256
    expected_hash = hashlib.sha256(FAKE_MAESTRO_HELP.encode('utf-8')).hexdigest()
    assert discovered1[('maestro',)].help_hash == expected_hash


def test_help_surface_budget_max_nodes():
    """Test that max_nodes budget is enforced."""
    # Create help map with many commands
    help_map = {
        ('maestro',): FAKE_MAESTRO_HELP,
        ('maestro', 'plan'): FAKE_PLAN_HELP,
        ('maestro', 'repo'): FAKE_REPO_HELP,
        ('maestro', 'ops'): "ops help",
        ('maestro', 'plan', 'list'): "list help",
        ('maestro', 'plan', 'add'): "add help",
        ('maestro', 'plan', 'show'): "show help",
    }

    # Set budget to max 3 nodes
    budget = DiscoveryBudget(max_nodes=3)
    surface = FakeHelpSurface(help_map, budget=budget, verbose=False)
    discovered = surface.discover()

    # Should stop at 3 nodes
    assert len(discovered) <= 3


def test_help_surface_budget_max_help_bytes():
    """Test that max_help_bytes budget is enforced."""
    # Create large help text
    large_help = "x" * 50000  # 50KB

    help_map = {
        ('maestro',): large_help,
        ('maestro', 'plan'): large_help,
        ('maestro', 'repo'): large_help,
    }

    # Set budget to max 100KB
    budget = DiscoveryBudget(max_help_bytes=100_000)
    surface = FakeHelpSurface(help_map, budget=budget, verbose=False)
    discovered = surface.discover()

    # Should stop when total bytes exceed 100KB
    assert surface.total_help_bytes <= 100_000 + 50000  # Allow one node over


def test_help_surface_extract_subcommands():
    """Test subcommand extraction from help text."""
    surface = FakeHelpSurface({})

    # Test brace pattern: {cmd1,cmd2,cmd3}
    help_with_braces = "Available commands: {list,add,show,remove}"
    subcommands = surface._extract_subcommands(help_with_braces)
    assert 'list' in subcommands
    assert 'add' in subcommands
    assert 'show' in subcommands
    assert 'remove' in subcommands

    # Test line pattern: "  command    Description"
    help_with_lines = """Subcommands:
  list        List all items
  add         Add a new item
  show        Show item details
"""
    subcommands = surface._extract_subcommands(help_with_lines)
    assert 'list' in subcommands
    assert 'add' in subcommands
    assert 'show' in subcommands

    # Test filtering of non-commands (like "usage", "options")
    help_with_noise = """
usage: maestro plan [options]

optional arguments:
  -h, --help    Show help
"""
    subcommands = surface._extract_subcommands(help_with_noise)
    # Should NOT extract "usage" or "optional" or "arguments"
    assert 'usage' not in subcommands
    assert 'optional' not in subcommands


def test_help_surface_warnings():
    """Test that warnings are recorded for unknown commands."""
    help_map = {
        ('maestro',): FAKE_MAESTRO_HELP,
        # Missing ('maestro', 'plan') - will trigger warning
    }

    surface = FakeHelpSurface(help_map, verbose=False)
    discovered = surface.discover()

    # Should have warnings about unknown commands
    assert len(surface.warnings) > 0
    assert any('plan' in warning.lower() for warning in surface.warnings)


def test_help_surface_stable_order():
    """Test that discovered subcommands are returned in stable order."""
    help_map = {
        ('maestro',): FAKE_MAESTRO_HELP,
    }

    surface1 = FakeHelpSurface(help_map)
    discovered1 = surface1.discover()

    surface2 = FakeHelpSurface(help_map)
    discovered2 = surface2.discover()

    # Subcommand lists should be in same order
    assert discovered1[('maestro',)].discovered_subcommands == \
           discovered2[('maestro',)].discovered_subcommands

    # Order should be alphabetical (from sorted())
    subcommands = discovered1[('maestro',)].discovered_subcommands
    assert subcommands == sorted(subcommands)

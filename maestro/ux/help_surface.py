"""
Help surface discovery module for UX evaluation.

Discovers Maestro CLI command surface by crawling help text only (no parser introspection).
"""

import subprocess
import hashlib
import json
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Optional, Set


@dataclass
class DiscoveryBudget:
    """Budget constraints for help surface discovery."""
    max_nodes: int = 80  # Maximum number of command nodes to discover
    max_help_bytes: int = 300_000  # Maximum total help text bytes (300KB)
    per_call_timeout: float = 5.0  # Timeout for each subprocess call (seconds)
    max_depth: int = 4  # Maximum recursion depth for subcommand discovery


@dataclass
class HelpNode:
    """A single command node discovered from help text."""
    command_path: List[str]  # e.g., ['maestro', 'plan', 'decompose']
    help_text: str  # Full help text for this command
    help_hash: str  # SHA256 hash of help text (for determinism)
    discovered_subcommands: List[str] = field(default_factory=list)  # Subcommand names found in help


class HelpSurface:
    """
    Discovers CLI surface by crawling help text.

    This class runs subprocess calls to MAESTRO_BIN and builds a command tree
    by parsing --help output. It enforces budgets to prevent unbounded exploration.
    """

    def __init__(
        self,
        maestro_bin: str,
        budget: Optional[DiscoveryBudget] = None,
        verbose: bool = False
    ):
        """
        Initialize HelpSurface discovery.

        Args:
            maestro_bin: Path to maestro executable (or command like "maestro.py")
            budget: Discovery budget constraints (uses defaults if None)
            verbose: Whether to print progress messages
        """
        self.maestro_bin = maestro_bin
        self.budget = budget or DiscoveryBudget()
        self.verbose = verbose

        self.nodes: Dict[tuple, HelpNode] = {}  # key: tuple(command_path)
        self.total_help_bytes: int = 0
        self.help_call_count: int = 0
        self.warnings: List[str] = []

    def discover(self) -> Dict[tuple, HelpNode]:
        """
        Discover the command surface by crawling help text.

        Returns:
            Dictionary mapping command_path tuples to HelpNode objects
        """
        if self.verbose:
            print("Starting help surface discovery...")
            print(f"MAESTRO_BIN: {self.maestro_bin}")
            print(f"Budget: {self.budget.max_nodes} nodes, {self.budget.max_help_bytes} bytes")

        # Start with root command
        self._discover_node(['maestro'], depth=0)

        if self.verbose:
            print(f"Discovery complete: {len(self.nodes)} nodes, {self.total_help_bytes} bytes")

        return self.nodes

    def _discover_node(self, command_path: List[str], depth: int) -> None:
        """
        Discover a single command node and its subcommands recursively.

        Args:
            command_path: Command path to discover (e.g., ['maestro', 'plan'])
            depth: Current recursion depth
        """
        # Budget checks
        if len(self.nodes) >= self.budget.max_nodes:
            if self.verbose:
                print(f"  Budget reached: max_nodes={self.budget.max_nodes}")
            return

        if self.total_help_bytes >= self.budget.max_help_bytes:
            if self.verbose:
                print(f"  Budget reached: max_help_bytes={self.budget.max_help_bytes}")
            return

        if depth >= self.budget.max_depth:
            if self.verbose:
                print(f"  Max depth reached: {depth}")
            return

        # Skip if already discovered
        node_key = tuple(command_path)
        if node_key in self.nodes:
            return

        # Get help text
        help_text = self._get_help_text(command_path)
        if help_text is None:
            return  # Failed to get help

        # Create node
        help_hash = hashlib.sha256(help_text.encode('utf-8')).hexdigest()
        subcommands = self._extract_subcommands(help_text)

        node = HelpNode(
            command_path=command_path,
            help_text=help_text,
            help_hash=help_hash,
            discovered_subcommands=subcommands
        )

        self.nodes[node_key] = node
        self.total_help_bytes += len(help_text)

        if self.verbose:
            cmd_str = ' '.join(command_path)
            print(f"  Discovered: {cmd_str} ({len(subcommands)} subcommands)")

        # Recursively discover subcommands
        for subcmd in subcommands:
            self._discover_node(command_path + [subcmd], depth=depth+1)

    def _get_help_text(self, command_path: List[str]) -> Optional[str]:
        """
        Get help text for a command by running subprocess.

        Args:
            command_path: Command path (e.g., ['maestro', 'plan'])

        Returns:
            Help text or None if failed
        """
        # Build command: replace 'maestro' with actual bin path
        cmd_parts = [self.maestro_bin] + command_path[1:] + ['--help']

        try:
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=self.budget.per_call_timeout,
                check=False
            )

            self.help_call_count += 1

            # Accept both stdout and stderr (some CLIs print help to stderr)
            help_text = result.stdout if result.stdout.strip() else result.stderr

            if not help_text.strip():
                warning = f"Empty help text for: {' '.join(command_path)}"
                self.warnings.append(warning)
                if self.verbose:
                    print(f"  Warning: {warning}")
                return None

            return help_text

        except subprocess.TimeoutExpired:
            warning = f"Timeout for: {' '.join(command_path)}"
            self.warnings.append(warning)
            if self.verbose:
                print(f"  Warning: {warning}")
            return None

        except FileNotFoundError:
            warning = f"MAESTRO_BIN not found: {self.maestro_bin}"
            self.warnings.append(warning)
            if self.verbose:
                print(f"  Error: {warning}")
            return None

        except Exception as e:
            warning = f"Error getting help for {' '.join(command_path)}: {e}"
            self.warnings.append(warning)
            if self.verbose:
                print(f"  Error: {warning}")
            return None

    def _extract_subcommands(self, help_text: str) -> List[str]:
        """
        Extract subcommand names from help text.

        Looks for common patterns like:
        - "Available commands:"
        - "{subcommand1,subcommand2,subcommand3}"
        - Lines with leading spaces followed by command names

        Args:
            help_text: Help text to parse

        Returns:
            List of discovered subcommand names
        """
        subcommands: Set[str] = set()

        # Pattern 1: {cmd1,cmd2,cmd3} format
        # Example: "{list,show,add,edit,rm}"
        brace_pattern = r'\{([a-zA-Z0-9_,|-]+)\}'
        for match in re.finditer(brace_pattern, help_text):
            cmds = match.group(1).split(',')
            for cmd in cmds:
                cmd = cmd.strip()
                if cmd and '|' not in cmd:  # Skip alternations like {-h|--help}
                    subcommands.add(cmd)

        # Pattern 2: Lines starting with 2-4 spaces followed by a command name
        # Example: "  list        List all plans"
        # Exclude lines that start with "-" (flags)
        line_pattern = r'^  ([a-zA-Z][a-zA-Z0-9_-]*)\s+'
        for line in help_text.split('\n'):
            match = re.match(line_pattern, line)
            if match:
                cmd = match.group(1)
                # Filter out common non-command keywords
                if cmd not in ('usage', 'options', 'optional', 'positional', 'arguments', 'examples', 'description'):
                    subcommands.add(cmd)

        return sorted(subcommands)

    def save_surface(self, output_dir: Path) -> None:
        """
        Save discovered surface to JSON and text files.

        Args:
            output_dir: Directory to write surface files
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save surface.json (compact structure with hashes)
        surface_data = {
            'maestro_bin': self.maestro_bin,
            'budget': asdict(self.budget),
            'total_nodes': len(self.nodes),
            'total_help_bytes': self.total_help_bytes,
            'help_call_count': self.help_call_count,
            'warnings': self.warnings,
            'nodes': [
                {
                    'command_path': node.command_path,
                    'help_hash': node.help_hash,
                    'discovered_subcommands': node.discovered_subcommands
                }
                for node in self.nodes.values()
            ]
        }

        surface_json_path = output_dir / 'surface.json'
        with open(surface_json_path, 'w', encoding='utf-8') as f:
            json.dump(surface_data, f, indent=2)

        if self.verbose:
            print(f"Saved surface.json: {surface_json_path}")

        # Save surface.txt (bounded readable excerpts)
        surface_txt_path = output_dir / 'surface.txt'
        with open(surface_txt_path, 'w', encoding='utf-8') as f:
            f.write("# Maestro CLI Surface Discovery\n\n")
            f.write(f"MAESTRO_BIN: {self.maestro_bin}\n")
            f.write(f"Discovered nodes: {len(self.nodes)}\n")
            f.write(f"Total help bytes: {self.total_help_bytes}\n")
            f.write(f"Help calls: {self.help_call_count}\n")
            f.write(f"\n")

            if self.warnings:
                f.write(f"Warnings ({len(self.warnings)}):\n")
                for warning in self.warnings[:10]:  # Bounded to 10
                    f.write(f"  - {warning}\n")
                if len(self.warnings) > 10:
                    f.write(f"  ... and {len(self.warnings) - 10} more\n")
                f.write(f"\n")

            f.write("## Discovered Commands\n\n")

            # Sort nodes by command path for stable output
            sorted_nodes = sorted(self.nodes.values(), key=lambda n: n.command_path)

            for node in sorted_nodes:
                cmd_str = ' '.join(node.command_path)
                f.write(f"### {cmd_str}\n\n")

                if node.discovered_subcommands:
                    f.write(f"Subcommands: {', '.join(node.discovered_subcommands)}\n")

                # Write bounded help excerpt (first 500 chars)
                help_excerpt = node.help_text[:500]
                if len(node.help_text) > 500:
                    help_excerpt += "\n... (truncated)"
                f.write(f"\n```\n{help_excerpt}\n```\n\n")

        if self.verbose:
            print(f"Saved surface.txt: {surface_txt_path}")

#!/usr/bin/env python3
"""
Create WF to Commands mapping from intent YAML files
"""

import yaml
import sys
from pathlib import Path
from collections import defaultdict

def extract_command_stem(cmd_str):
    """Extract command stem from full command string.

    Examples:
        'maestro init' -> 'init'
        'maestro track add' -> 'track'
        'maestro repo resolve' -> 'repo'
        'git init' -> None (not maestro)
    """
    if not cmd_str.startswith('maestro '):
        return None

    parts = cmd_str.split()
    if len(parts) < 2:
        return None

    return parts[1]  # Command stem is second part

def main():
    # Paths
    wf_dir = Path(__file__).parent.parent.parent / 'docs' / 'workflows' / 'v2' / 'ir' / 'wf'
    output_file = Path(__file__).parent.parent.parent / 'docs' / 'workflows' / 'v2' / 'ir' / 'maps' / 'wf_to_commands.yaml'

    # Find all WF intent files
    wf_files = sorted(wf_dir.glob('WF-*.intent.yaml'))

    if not wf_files:
        print(f"ERROR: No WF intent files found in {wf_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(wf_files)} WF intent files")

    # Extract command mappings
    wf_to_commands = {}

    for wf_file in wf_files:
        wf_id = wf_file.stem.replace('.intent', '')

        try:
            with open(wf_file) as f:
                data = yaml.safe_load(f)

            # Extract commands from 'commands' field
            commands = data.get('commands', [])

            # Extract unique command stems
            cmd_stems = set()
            for cmd in commands:
                stem = extract_command_stem(cmd)
                if stem:
                    cmd_stems.add(f"CMD-{stem}")

            # Sort for consistency
            wf_to_commands[wf_id] = sorted(list(cmd_stems))

            print(f"  {wf_id}: {len(cmd_stems)} commands -> {', '.join(sorted(cmd_stems)) if cmd_stems else '(none)'}")

        except Exception as e:
            print(f"  ERROR processing {wf_file}: {e}", file=sys.stderr)
            continue

    # Create output data structure
    output_data = {
        'description': 'Mapping from workflow IDs to command IDs they use',
        'version': '2.0',
        'wf_to_commands': wf_to_commands
    }

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        f.write('# Workflow to Commands Mapping\n')
        f.write('#\n')
        f.write('# This file maps workflow IDs (WF-XX) to the command IDs (CMD-name) they use.\n')
        f.write('# Generated automatically from WF intent YAML files.\n')
        f.write('#\n\n')
        yaml.dump(output_data, f, default_flow_style=False, sort_keys=False)

    print(f"\n✓ Mapping file created: {output_file}")
    print(f"  Total workflows: {len(wf_to_commands)}")
    print(f"  Unique commands: {len(set(sum(wf_to_commands.values(), [])))}")

if __name__ == '__main__':
    main()

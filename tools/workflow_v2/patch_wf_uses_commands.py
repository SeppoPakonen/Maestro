#!/usr/bin/env python3
"""
Patch WF intent files with uses_commands field
"""

import yaml
import sys
from pathlib import Path

def patch_wf_file(wf_file, commands_list):
    """Patch a single WF intent file with uses_commands field."""

    # Read current content
    with open(wf_file) as f:
        content = f.read()

    # Parse YAML
    data = yaml.safe_load(content)

    # Add uses_commands field if not already present
    if 'uses_commands' not in data:
        data['uses_commands'] = commands_list

        # Write back with preserved formatting where possible
        # Insert uses_commands after storage_backend field
        lines = content.split('\n')
        new_lines = []
        inserted = False

        for i, line in enumerate(lines):
            new_lines.append(line)

            # Insert after storage_backend line
            if line.startswith('storage_backend:') and not inserted:
                new_lines.append('')
                new_lines.append('uses_commands:')
                for cmd in commands_list:
                    new_lines.append(f'  - {cmd}')
                inserted = True

        # If we didn't find storage_backend (shouldn't happen), append at end before first section
        if not inserted:
            # Find first major section (description, nodes, etc.)
            insert_pos = 0
            for i, line in enumerate(new_lines):
                if line.startswith('description:') or line.startswith('nodes:'):
                    insert_pos = i
                    break

            if insert_pos > 0:
                new_lines.insert(insert_pos, '')
                new_lines.insert(insert_pos + 1, 'uses_commands:')
                for cmd in commands_list:
                    new_lines.insert(insert_pos + 2, f'  - {cmd}')
                new_lines.insert(insert_pos + 2 + len(commands_list), '')

        # Write back
        with open(wf_file, 'w') as f:
            f.write('\n'.join(new_lines))

        return True
    else:
        # Already has uses_commands
        return False

def main():
    # Paths
    wf_dir = Path(__file__).parent.parent.parent / 'docs' / 'workflows' / 'v2' / 'ir' / 'wf'
    mapping_file = Path(__file__).parent.parent.parent / 'docs' / 'workflows' / 'v2' / 'ir' / 'maps' / 'wf_to_commands.yaml'

    # Load mapping
    with open(mapping_file) as f:
        mapping_data = yaml.safe_load(f)

    wf_to_commands = mapping_data.get('wf_to_commands', {})

    print(f"Patching {len(wf_to_commands)} WF intent files...")

    patched_count = 0
    skipped_count = 0

    for wf_id, commands in sorted(wf_to_commands.items()):
        wf_file = wf_dir / f'{wf_id}.intent.yaml'

        if not wf_file.exists():
            print(f"  ⚠ {wf_id}: File not found", file=sys.stderr)
            continue

        try:
            if patch_wf_file(wf_file, commands):
                print(f"  ✓ {wf_id}: Added uses_commands ({len(commands)} commands)")
                patched_count += 1
            else:
                print(f"  - {wf_id}: Already has uses_commands")
                skipped_count += 1

        except Exception as e:
            print(f"  ✗ {wf_id}: ERROR - {e}", file=sys.stderr)

    print(f"\n✓ Patching complete:")
    print(f"  Patched: {patched_count}")
    print(f"  Skipped: {skipped_count}")

if __name__ == '__main__':
    main()

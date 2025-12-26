#!/usr/bin/env python3
"""
Validate all YAML IR files
"""

import yaml
import sys
from pathlib import Path

def validate_yaml_file(file_path):
    """Validate a single YAML file."""
    try:
        with open(file_path) as f:
            yaml.safe_load(f)
        return True, None
    except Exception as e:
        return False, str(e)

def main():
    # Paths to check
    base_dir = Path(__file__).parent.parent.parent / 'docs' / 'workflows' / 'v2' / 'ir'

    # Find all YAML files
    wf_files = sorted((base_dir / 'wf').glob('*.yaml'))
    cmd_files = sorted((base_dir / 'cmd').glob('*.yaml'))
    map_files = sorted((base_dir / 'maps').glob('*.yaml'))

    all_files = wf_files + cmd_files + map_files

    print(f"Validating {len(all_files)} YAML files...")
    print(f"  WF intent files: {len(wf_files)}")
    print(f"  CMD files: {len(cmd_files)}")
    print(f"  Map files: {len(map_files)}")
    print()

    valid_count = 0
    invalid_count = 0
    errors = []

    for yaml_file in all_files:
        is_valid, error = validate_yaml_file(yaml_file)

        if is_valid:
            print(f"  ✓ {yaml_file.relative_to(base_dir)}")
            valid_count += 1
        else:
            print(f"  ✗ {yaml_file.relative_to(base_dir)}: {error}", file=sys.stderr)
            invalid_count += 1
            errors.append((yaml_file, error))

    print()
    print("=" * 70)
    print(f"Valid: {valid_count}")
    print(f"Invalid: {invalid_count}")

    if invalid_count > 0:
        print()
        print("ERRORS:")
        for file_path, error in errors:
            print(f"  {file_path.name}:")
            print(f"    {error}")

        sys.exit(1)
    else:
        print()
        print("✓ All YAML files are valid!")
        sys.exit(0)

if __name__ == '__main__':
    main()

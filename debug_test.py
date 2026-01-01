import tempfile
import os
from pathlib import Path
from maestro.repo.scanner import scan_upp_repo_v2
from maestro.commands.repo import write_repo_artifacts
from maestro.repo.storage import load_repo_model

# Create a simple test similar to the failing test
with tempfile.TemporaryDirectory() as temp_dir:
    temp_path = Path(temp_dir)
    
    # Create test directory structure similar to BatchScriptShell
    docs_dir = temp_path / 'docs'
    tests_dir = temp_path / 'tests'
    
    docs_dir.mkdir()
    tests_dir.mkdir()
    
    # Create some test files
    (docs_dir / 'index.md').write_text('# Docs')
    (tests_dir / 'test.sh').write_text('#!/bin/bash\necho test')
    (temp_path / 'script.bat').write_text('@echo off\necho Hello')
    (temp_path / 'main.cpp').write_text('int main() { return 0; }')
    
    # Set MAESTRO_DOCS_ROOT to point to docs/maestro in temp directory
    os.environ['MAESTRO_DOCS_ROOT'] = str(temp_path / 'docs' / 'maestro')
    
    # Run the repo scan using the same internal API used by `m repo resolve`
    scan_result = scan_upp_repo_v2(
        str(temp_path),
        verbose=False,
        include_user_config=False,
        collect_files=True,
        scan_unknown_paths=True,
    )
    
    # Write the repo artifacts
    write_repo_artifacts(str(temp_path), scan_result, verbose=False)
    
    # Load the repo model to verify the results
    repo_model = load_repo_model(str(temp_path))
    
    # Find assemblies and packages in the model
    assemblies = repo_model.get('assemblies', [])
    packages = repo_model.get('packages', [])
    
    print('Assemblies found:')
    for asm in assemblies:
        print(f'  {asm["name"]} (kind: {asm["kind"]}) - {len(asm["package_ids"])} packages')
    
    print('\nPackages found:')
    for pkg in packages:
        print(f'  {pkg["name"]} (build_system: {pkg["build_system"]}) -> assembly_id: {pkg["assembly_id"]}')
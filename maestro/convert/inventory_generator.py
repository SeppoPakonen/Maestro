import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
import json

def get_file_hash(filepath: str) -> str:
    """Calculate SHA256 hash of a file."""
    hash_sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read file in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def detect_language(filepath: str) -> str:
    """Detect programming language based on file extension."""
    ext_map = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.cs': 'C#',
        '.go': 'Go',
        '.rs': 'Rust',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.html': 'HTML',
        '.css': 'CSS',
        '.json': 'JSON',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.toml': 'TOML',
        '.xml': 'XML',
        '.md': 'Markdown',
        '.txt': 'Text',
        '.sh': 'Shell',
        '.sql': 'SQL',
        '.dockerfile': 'Dockerfile',
        'dockerfile': 'Dockerfile',
        '.cfg': 'Configuration',
        '.conf': 'Configuration',
        '.ini': 'Configuration',
        '.env': 'Environment',
        '.bat': 'Batch',
        '.ps1': 'PowerShell',
        '.zsh': 'Zsh',
        '.bash': 'Bash',
        '.pl': 'Perl',
        '.lua': 'Lua',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.hs': 'Haskell',
        '.clj': 'Clojure',
        '.cljs': 'ClojureScript',
        '.erl': 'Erlang',
        '.ex': 'Elixir',
        '.exs': 'Elixir',
        '.elm': 'Elm',
        '.dart': 'Dart',
        '.jl': 'Julia',
        '.f': 'Fortran',
        '.fs': 'F#',
        '.vb': 'Visual Basic',
        '.sol': 'Solidity',
        '.v': 'Verilog',
        '.sv': 'SystemVerilog',
        '.tf': 'Terraform',
        '.hcl': 'HCL',
    }
    
    path = Path(filepath.lower())
    ext = path.suffix
    name = path.name
    
    # Special case for files without extensions but known names
    if ext == '' and name in ext_map:
        return ext_map[name]
    elif ext in ext_map:
        return ext_map[ext]
    else:
        return 'Unknown'

def classify_file_role(filepath: str, language: str) -> List[str]:
    """Classify file role based on path and filename heuristics."""
    roles = []
    path_lower = filepath.lower()
    name_lower = Path(filepath).name.lower()
    
    # Check for build files
    if any(build_word in path_lower for build_word in [
        'build', 'cmake', 'make', 'gradle', 'pom', 'cargo', 'package', 'setup', 'requirements', 
        'pyproject', 'poetry', 'gemfile', 'bower', 'composer', 'stack', 'mix'
    ]):
        roles.append('build')
    
    # Check for configuration files
    if any(config_word in path_lower for config_word in [
        'config', 'setting', 'cfg', 'conf', 'env', 'environment', 'rc', 'ini', 'prop', 'properties'
    ]) and language != 'Unknown':
        roles.append('configuration')
    
    # Check for test files
    if any(test_word in name_lower for test_word in [
        'test', 'spec', 'testing', '_test', '.test', 'unit', 'integration'
    ]):
        roles.append('test')
    
    # Check for documentation files
    if any(doc_word in name_lower for doc_word in [
        'readme', 'doc', 'documentation', 'guide', 'tutorial', 'manual', 'license', 'changelog',
        'contributing', 'history', 'authors', 'notes'
    ]):
        roles.append('documentation')
    
    # Check for entry points
    if any(entry_word in name_lower for entry_word in [
        'main', 'index', 'app', 'start', 'server', 'init', '__main__', 'entry', 'bootstrap'
    ]):
        roles.append('entrypoint')
    
    # Add language-specific roles
    if language == 'Python' and name_lower in ['setup.py', 'requirements.txt', 'pyproject.toml']:
        if 'build' not in roles:
            roles.append('build')
    
    if language == 'JavaScript' and name_lower in ['package.json', 'webpack.config.js', 'gulpfile.js', 'gruntfile.js']:
        if 'build' not in roles:
            roles.append('build')
    
    if language == 'Dockerfile' or name_lower.startswith('dockerfile'):
        roles.append('infrastructure')
    
    # If no specific role was detected, default to 'source' for code files
    if len(roles) == 0 and language != 'Unknown' and language not in ['Markdown', 'Text', 'Configuration', 'JSON', 'YAML']:
        roles.append('source')
    
    # Classify unknown files based on path
    if len(roles) == 0:
        if 'bin' in path_lower or 'exec' in path_lower:
            roles.append('executable')
        elif 'asset' in path_lower or 'static' in path_lower:
            roles.append('asset')
        elif 'temp' in path_lower or 'tmp' in path_lower:
            roles.append('temporary')
        elif 'lib' in path_lower:
            roles.append('library')
        else:
            roles.append('unknown')
    
    return roles

def generate_inventory(repo_path: str) -> Dict:
    """Generate a comprehensive inventory of files in the repository."""
    inventory = {
        'repository_path': repo_path,
        'files': [],
        'total_count': 0,
        'by_extension': {},
        'by_language': {},
        'by_role': {},
        'by_directory': {},
        'size_summary': {
            'total_bytes': 0,
            'largest_files': []
        }
    }
    
    if not os.path.exists(repo_path):
        return inventory
    
    # Walk through the repository and collect file information
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden directories like .git, .vscode, etc.
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            filepath = os.path.join(root, file)
            
            # Skip hidden files
            if file.startswith('.'):
                continue
                
            try:
                # Get file stats
                stat_info = os.stat(filepath)
                file_size = stat_info.st_size
                file_hash = get_file_hash(filepath)
                
                # Determine language and roles
                language = detect_language(file)
                roles = classify_file_role(filepath, language)
                
                # Get relative path from repo root
                relative_path = os.path.relpath(filepath, repo_path)
                
                # Update counts and mappings
                file_info = {
                    'path': relative_path,
                    'full_path': filepath,
                    'size': file_size,
                    'hash': file_hash,
                    'language': language,
                    'roles': roles
                }
                
                inventory['files'].append(file_info)
                inventory['total_count'] += 1
                inventory['size_summary']['total_bytes'] += file_size
                
                # Track by extension
                ext = Path(file).suffix.lower()
                inventory['by_extension'][ext] = inventory['by_extension'].get(ext, 0) + 1
                
                # Track by language
                inventory['by_language'][language] = inventory['by_language'].get(language, 0) + 1
                
                # Track by role
                for role in roles:
                    inventory['by_role'][role] = inventory['by_role'].get(role, 0) + 1
                
                # Track by directory
                directory = os.path.dirname(relative_path).lower()
                if directory == '.':
                    directory = '/'
                inventory['by_directory'][directory] = inventory['by_directory'].get(directory, 0) + 1
                
            except Exception as e:
                print(f"Warning: Could not process file {filepath}: {str(e)}")
                continue
    
    # Sort largest files
    sorted_files = sorted(inventory['files'], key=lambda x: x['size'], reverse=True)[:10]
    inventory['size_summary']['largest_files'] = sorted_files[:5]  # Top 5 largest files
    
    # Generate summary statistics
    inventory['summary'] = {
        'total_files': inventory['total_count'],
        'total_size_bytes': inventory['size_summary']['total_bytes'],
        'average_file_size': inventory['size_summary']['total_bytes'] / inventory['total_count'] if inventory['total_count'] > 0 else 0,
        'top_languages': dict(sorted(inventory['by_language'].items(), key=lambda x: x[1], reverse=True)[:10]),
        'top_roles': dict(sorted(inventory['by_role'].items(), key=lambda x: x[1], reverse=True)[:10]),
        'top_directories': dict(sorted(inventory['by_directory'].items(), key=lambda x: x[1], reverse=True)[:10]),
        'top_extensions': dict(sorted(inventory['by_extension'].items(), key=lambda x: x[1], reverse=True)[:10])
    }
    
    return inventory

def save_inventory(inventory: Dict, output_path: str):
    """Save inventory dictionary to a JSON file."""
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False)

def load_inventory(input_path: str) -> Optional[Dict]:
    """Load inventory from a JSON file."""
    if not os.path.exists(input_path):
        return None
        
    with open(input_path, 'r', encoding='utf-8') as f:
        return json.load(f)

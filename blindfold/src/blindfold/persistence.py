"""Blindfold persistence module.

This module handles paths for data, state, and cache directories.
Uses XDG paths for proper system integration.
"""

import os
from importlib import resources

def get_default_paths():
    """
    Get default paths for data, state, and cache directories using XDG specifications.

    Returns:
        dict: A dictionary with keys 'data_dir', 'state_dir', 'cache_dir'
    """
    # Use XDG environment variables or defaults
    xdg_data_home = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
    xdg_state_home = os.environ.get('XDG_STATE_HOME', os.path.expanduser('~/.local/state'))
    xdg_cache_home = os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache'))

    # Create blindfold subdirectories
    data_dir = os.path.join(xdg_data_home, 'blindfold')
    state_dir = os.path.join(xdg_state_home, 'blindfold')
    cache_dir = os.path.join(xdg_cache_home, 'blindfold')

    return {
        "data_dir": data_dir,
        "state_dir": state_dir,
        "cache_dir": cache_dir
    }

def ensure_dirs(paths):
    """
    Ensure that the directories exist.

    Args:
        paths (dict): Dictionary with directory paths
    """
    for path in paths.values():
        os.makedirs(path, exist_ok=True)


def bootstrap_packaged_data(data_dir: str) -> None:
    """
    Bootstrap packaged data files into the XDG data directory.

    Args:
        data_dir: The XDG data directory path
    """
    import os
    from importlib import resources

    # Ensure the directories exist
    interfaces_dir = os.path.join(data_dir, "interfaces")
    mappings_dir = os.path.join(data_dir, "mappings")
    os.makedirs(interfaces_dir, exist_ok=True)
    os.makedirs(mappings_dir, exist_ok=True)

    # Check if demo.yaml exists, if not copy from packaged data
    demo_path = os.path.join(interfaces_dir, "demo.yaml")
    if not os.path.exists(demo_path):
        demo_content = resources.files("blindfold.data.interfaces").joinpath("demo.yaml").read_text()
        with open(demo_path, 'w', encoding='utf-8') as f:
            f.write(demo_content)

    # Check if mappings.yaml exists, if not copy from packaged data
    mappings_path = os.path.join(mappings_dir, "mappings.yaml")
    if not os.path.exists(mappings_path):
        mappings_content = resources.files("blindfold.data.mappings").joinpath("mappings.yaml").read_text()
        with open(mappings_path, 'w', encoding='utf-8') as f:
            f.write(mappings_content)

    # Check if redaction.yaml exists, if not copy from packaged data
    redaction_path = os.path.join(data_dir, "redaction.yaml")
    if not os.path.exists(redaction_path):
        redaction_content = resources.files("blindfold.data").joinpath("redaction.yaml").read_text()
        with open(redaction_path, 'w', encoding='utf-8') as f:
            f.write(redaction_content)
"""Interface loader module for blindfold.

This module handles loading interface YAML files as text.
"""

import os


def load_interface_text(data_dir: str, interface_filename: str) -> str:
    """
    Load the text content of an interface file.
    
    Args:
        data_dir: The XDG data directory path
        interface_filename: Name of the interface file to load
        
    Returns:
        Raw text content of the interface file
        
    Raises:
        FileNotFoundError: If the interface file does not exist
    """
    interface_path = os.path.join(data_dir, "interfaces", interface_filename)
    with open(interface_path, 'r', encoding='utf-8') as f:
        return f.read()
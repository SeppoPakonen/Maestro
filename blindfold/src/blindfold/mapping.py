"""Mapping module for blindfold.

This module handles loading and matching command mappings to interface files.
"""

import yaml
import os


def load_mappings(mapping_file: str) -> list[dict]:
    """
    Load mappings from a YAML file.
    
    Args:
        mapping_file: Path to the mappings YAML file
        
    Returns:
        List of mapping dictionaries
    """
    if not os.path.exists(mapping_file):
        return []
    
    with open(mapping_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        data = yaml.safe_load(content)
        if isinstance(data, list):
            return data
        else:
            return []
    except yaml.YAMLError:
        return []


def find_mapping(argv_tokens: list[str], mappings: list[dict]) -> dict | None:
    """
    Find a mapping that matches the given argv tokens.
    
    Args:
        argv_tokens: List of command arguments
        mappings: List of mapping dictionaries
        
    Returns:
        Matching mapping dictionary or None if no match found
    """
    for mapping in mappings:
        if isinstance(mapping.get("argv"), list) and mapping["argv"] == argv_tokens:
            return mapping
    return None
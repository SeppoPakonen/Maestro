"""Redaction module for sanitizing sensitive data from logs and feedback."""

import os
import re
import yaml
from typing import List, Tuple


def load_redaction_rules(data_dir: str) -> List[Tuple[str, str]]:
    """
    Load redaction rules from the redaction.yaml configuration file.
    
    Args:
        data_dir: The XDG data directory path
        
    Returns:
        List of (pattern, replace) tuples for redaction
    """
    redaction_file = os.path.join(data_dir, "redaction.yaml")
    
    if not os.path.exists(redaction_file):
        return []
    
    try:
        with open(redaction_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except (yaml.YAMLError, IOError):
        # If there's an error loading the file, return empty list
        return []
    
    if not config or 'patterns' not in config or not config['patterns']:
        return []
    
    rules = []
    for pattern_entry in config['patterns']:
        if 'pattern' in pattern_entry and 'replace' in pattern_entry:
            rules.append((pattern_entry['pattern'], pattern_entry['replace']))
    
    return rules


def redact_text(text: str, rules: List[Tuple[str, str]]) -> str:
    """
    Apply redaction rules to the provided text.

    Args:
        text: Text to redact
        rules: List of (pattern, replace) tuples

    Returns:
        Redacted text
    """
    if not text or not rules:
        return text

    redacted_text = text
    for pattern, replacement in rules:
        try:
            # Use re.sub - the pattern can include inline flags like (?i)
            redacted_text = re.sub(pattern, replacement, redacted_text)
        except re.error:
            # If a regex fails to compile, skip it (do not raise)
            continue

    return redacted_text
"""Feedback handling module for storing operator feedback with error cookies."""

import json
import os
import yaml


def parse_feedback_text(text: str) -> dict:
    """
    Parse feedback text from stdin as YAML or JSON.
    
    Args:
        text: Text to parse as feedback
        
    Returns:
        dict: Parsed feedback data
        
    Raises:
        ValueError: If text is empty, parsing fails, or result is not a dict
    """
    if not text.strip():
        raise ValueError("empty feedback")
    
    # First try YAML
    try:
        result = yaml.safe_load(text)
        if result is None:
            raise ValueError("empty feedback")
        if not isinstance(result, dict):
            raise ValueError("feedback must be a mapping/object")
        return result
    except yaml.YAMLError:
        # If YAML fails, try JSON
        try:
            result = json.loads(text)
            if not isinstance(result, dict):
                raise ValueError("feedback must be a mapping/object")
            return result
        except json.JSONDecodeError:
            raise ValueError("feedback must be a mapping/object")


def write_feedback(state_dir: str, cookie: str, feedback: dict) -> str:
    """
    Write feedback to state directory as YAML.
    
    Args:
        state_dir: Base state directory
        cookie: Error cookie ID
        feedback: Feedback data to store
        
    Returns:
        str: Full path to the created YAML file
    """
    # Create feedback directory if it doesn't exist
    feedback_dir = os.path.join(state_dir, "feedback")
    os.makedirs(feedback_dir, exist_ok=True)
    
    # Add cookie to feedback if not present
    feedback_out = dict(feedback)
    feedback_out.setdefault("cookie", cookie)
    
    # Write to YAML file
    feedback_file_path = os.path.join(feedback_dir, f"{cookie}.yaml")
    with open(feedback_file_path, "w", encoding="utf-8") as f:
        yaml.dump(feedback_out, f, default_flow_style=False, allow_unicode=True)
    
    return feedback_file_path
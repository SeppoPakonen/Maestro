"""
AI Stacking Mode Enforcement

This module implements the logic for enforcing AI stacking modes (managed vs handsoff).
"""

import json
from typing import Any, Dict, Optional
from maestro.config.settings import get_settings


def is_managed_mode() -> bool:
    """Check if the current stacking mode is 'managed'."""
    settings = get_settings()
    return settings.ai_stacking_mode == 'managed'


def is_handsoff_mode() -> bool:
    """Check if the current stacking mode is 'handsoff'."""
    settings = get_settings()
    return settings.ai_stacking_mode == 'handsoff'


def validate_planner_output(output: str) -> Dict[str, Any]:
    """
    Validate planner output based on the current stacking mode.
    
    In 'managed' mode, the planner output must be a valid JSON plan.
    In 'handsoff' mode, any output is accepted.
    
    Args:
        output: The planner output string
        
    Returns:
        Parsed JSON plan if valid, otherwise raises an exception in managed mode
        
    Raises:
        ValueError: If in managed mode and output is not valid JSON plan
    """
    settings = get_settings()
    
    if settings.ai_stacking_mode == 'managed':
        # In managed mode, the output must be a valid JSON plan
        try:
            parsed_output = json.loads(output)
            # Validate that it's a proper plan structure
            # This is a basic check - you may want to implement more specific validation
            if isinstance(parsed_output, dict) and ('tasks' in parsed_output or 'plan' in parsed_output):
                return parsed_output
            else:
                raise ValueError("Managed mode requires a full JSON plan. Switch to handsoff or rerun planning.")
        except json.JSONDecodeError:
            raise ValueError("Managed mode requires a full JSON plan. Switch to handsoff or rerun planning.")
    else:
        # In handsoff mode, just return the output as-is
        return {"raw_output": output}


def enforce_stacking_mode(output: str) -> Optional[Dict[str, Any]]:
    """
    Enforce stacking mode rules on planner output.
    
    Args:
        output: The planner output string
        
    Returns:
        Parsed output if valid, None if should be handled differently
    """
    if is_managed_mode():
        try:
            return validate_planner_output(output)
        except ValueError as e:
            raise e  # Re-raise the validation error
    else:
        # In handsoff mode, return the raw output
        return {"raw_output": output}
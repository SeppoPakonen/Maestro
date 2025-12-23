"""
Decoder for the Plan Operations pipeline.

This module implements the decoder that converts canonical PlanOpsResult JSON
into validated objects that Maestro can process.
"""

from typing import Dict, Any, List, Union
from .schemas import validate_plan_ops_result
from .operations import Selector, CreatePlan, DeletePlan, AddPlanItem, RemovePlanItem, Commentary


class DecodeError(Exception):
    """Exception raised when decoding nested JSON fails."""
    pass


def decode_plan_ops_json(raw: Union[str, Dict]) -> Dict[str, Any]:
    """
    Decode canonical PlanOpsResult JSON.

    Args:
        raw: Either a JSON string or already parsed dict containing the PlanOpsResult

    Returns:
        The validated PlanOpsResult as a dictionary

    Raises:
        DecodeError: If the JSON is invalid or doesn't match schemas
    """
    try:
        # Validate the PlanOpsResult
        validated_data = validate_plan_ops_result(raw)
    except Exception as e:
        raise DecodeError(f"PlanOpsResult JSON invalid: {str(e)}")

    return validated_data
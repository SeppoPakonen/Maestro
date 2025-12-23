"""
Decoder for the Project Operations pipeline.

This module implements the decoder that converts canonical ProjectOpsResult JSON
into validated objects that Maestro can process.
"""

from typing import Dict, Any, List, Union
from .schemas import validate_project_ops_result


class DecodeError(Exception):
    """Exception raised when decoding ProjectOpsResult JSON fails."""
    pass


def decode_project_ops_json(raw: Union[str, Dict]) -> Dict[str, Any]:
    """
    Decode canonical ProjectOpsResult JSON.

    Args:
        raw: Either a JSON string or already parsed dict containing the ProjectOpsResult

    Returns:
        The validated ProjectOpsResult as a dictionary

    Raises:
        DecodeError: If the JSON is invalid or doesn't match schemas
    """
    try:
        # Validate the ProjectOpsResult
        validated_data = validate_project_ops_result(raw)
    except Exception as e:
        raise DecodeError(f"ProjectOpsResult JSON invalid: {str(e)}")

    return validated_data
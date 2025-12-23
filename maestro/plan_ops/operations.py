"""
Typed operations for the Plan Operations pipeline.

This module defines internal operation objects that represent
actions to be performed on plans.
"""

from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class Selector:
    """Selector to identify a specific plan."""
    title: Optional[str] = None
    index: Optional[int] = None

    def __post_init__(self):
        """Validate that at least one selection criterion is provided."""
        if self.title is None and self.index is None:
            raise ValueError("Selector must have either title or index")
        if self.title is not None and self.index is not None:
            raise ValueError("Selector cannot have both title and index")


@dataclass
class CreatePlan:
    """Operation to create a new plan."""
    title: str


@dataclass
class DeletePlan:
    """Operation to delete an existing plan."""
    selector: Selector


@dataclass
class AddPlanItem:
    """Operation to add an item to a plan."""
    selector: Selector
    text: str


@dataclass
class RemovePlanItem:
    """Operation to remove an item from a plan."""
    selector: Selector
    item_index: int


@dataclass
class Commentary:
    """Operation for commentary (ignored by executor)."""
    text: str
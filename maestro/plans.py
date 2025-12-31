"""
Plan storage and parsing module for Maestro.

This module handles the canonical Markdown storage format for plans with strict validation.
"""

import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PlanItem:
    """Represents a single item in a plan."""
    text: str
    number: int = None  # For tracking position when needed


@dataclass
class Plan:
    """Represents a single plan with its items."""
    title: str
    items: List[PlanItem]

    def __post_init__(self):
        """Validate the plan after initialization."""
        if not self.title.strip():
            raise ValueError("Plan title cannot be empty")
        if not isinstance(self.items, list):
            raise ValueError("Plan items must be a list")


class PlanStore:
    """Handles loading, saving, and validating plans in canonical Markdown format."""
    
    def __init__(self, file_path: str = "docs/plans.md"):
        path = Path(file_path)
        if not path.is_absolute():
            try:
                path = (Path.cwd() / path).resolve()
            except FileNotFoundError:
                path = (Path(__file__).resolve().parents[1] / path).resolve()
        self.file_path = path
        # Ensure the docs directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> List[Plan]:
        """Load plans from the Markdown file."""
        if not self.file_path.exists():
            return []
        
        content = self.file_path.read_text(encoding='utf-8')
        return self._parse_content(content)
    
    def save(self, plans: List[Plan]) -> None:
        """Save plans to the Markdown file."""
        content = self._format_content(plans)
        self.file_path.write_text(content, encoding='utf-8')
    
    def _parse_content(self, content: str) -> List[Plan]:
        """Parse Markdown content into Plan objects with strict validation."""
        lines = content.splitlines()
        plans = []
        current_plan = None
        current_items = []

        # Track titles to check for duplicates
        titles = set()

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for plan title (## heading)
            if line.startswith('## ') and line[3:].strip():
                # If we were processing a previous plan, save it
                if current_plan is not None:
                    plan = Plan(title=current_plan, items=current_items)
                    plans.append(plan)

                title = line[3:].strip()  # Remove '## ' prefix

                # Validate no duplicate titles (case-insensitive)
                if any(t.lower() == title.lower() for t in titles):
                    raise ValueError(f"Duplicate plan title found: '{title}' (case-insensitive)")

                titles.add(title)
                current_plan = title
                current_items = []

            # Check for list items under the plan
            elif current_plan and (line.startswith('- ') or line.startswith('* ')):
                # Extract the item text (remove '- ' or '* ' prefix)
                item_text = line[2:].strip()
                current_items.append(PlanItem(text=item_text))

            # If we encounter a line that's not a plan header or list item
            # and we're inside a plan, it might be a continuation of the last item
            elif current_plan and line.strip() and not line.startswith('#'):
                # This could be a continuation of the previous item (multi-line item)
                # For now, we'll skip these as they're not part of the simple format
                pass

            # If we encounter a top-level heading (# Plans) or another section not related to plans,
            # continue processing but don't treat it as a plan
            elif line.startswith('# ') or (not current_plan and not line.startswith('- ') and not line.startswith('* ') and line.strip()):
                # This is content outside of plan sections, skip it for now
                pass

            i += 1

        # Don't forget the last plan if it exists
        if current_plan is not None:
            plan = Plan(title=current_plan, items=current_items)
            plans.append(plan)

        # Validate that each plan has a bullet list (even if empty)
        for plan in plans:
            if not isinstance(plan.items, list):
                raise ValueError(f"Plan '{plan.title}' must have a bullet list section")

        return plans
    
    def _format_content(self, plans: List[Plan]) -> str:
        """Format Plan objects into Markdown content."""
        if not plans:
            return "# Plans\n"

        lines = ["# Plans", ""]

        for plan in plans:
            lines.append(f"## {plan.title}")
            if plan.items:
                for item in plan.items:
                    lines.append(f"- {item.text}")
            else:
                # Even if no items, we still include an empty list to maintain structure
                pass  # We don't add empty items, just the plan header
            lines.append("")  # Empty line after each plan

        # Remove the last empty line to avoid trailing newline after the last plan
        if lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)
    
    def add_plan(self, title: str) -> Plan:
        """Add a new plan with the given title."""
        plans = self.load()
        
        # Check for duplicate titles (case-insensitive)
        if any(p.title.lower() == title.lower() for p in plans):
            raise ValueError(f"Plan with title '{title}' already exists (case-insensitive)")
        
        new_plan = Plan(title=title, items=[])
        plans.append(new_plan)
        self.save(plans)
        return new_plan
    
    def remove_plan(self, title: str) -> bool:
        """Remove a plan by title. Returns True if found and removed."""
        plans = self.load()
        original_count = len(plans)
        
        # Case-insensitive matching
        plans = [p for p in plans if p.title.lower() != title.lower()]
        
        if len(plans) == original_count:
            return False  # Plan not found
        
        self.save(plans)
        return True
    
    def get_plan(self, title_or_number: str) -> Optional[Plan]:
        """Get a plan by title or number. Returns None if not found."""
        plans = self.load()
        
        # Try to interpret as a number first
        try:
            number = int(title_or_number)
            if 1 <= number <= len(plans):
                return plans[number - 1]
        except ValueError:
            # Not a number, treat as title
            for plan in plans:
                if plan.title.lower() == title_or_number.lower():
                    return plan
        
        return None
    
    def add_item_to_plan(self, title_or_number: str, item_text: str) -> bool:
        """Add an item to a plan. Returns True if successful."""
        plans = self.load()
        
        # Find the plan
        target_plan = None
        plan_idx = -1
        
        # Try to interpret as a number first
        try:
            number = int(title_or_number)
            if 1 <= number <= len(plans):
                target_plan = plans[number - 1]
                plan_idx = number - 1
        except ValueError:
            # Not a number, treat as title
            for i, plan in enumerate(plans):
                if plan.title.lower() == title_or_number.lower():
                    target_plan = plan
                    plan_idx = i
                    break
        
        if target_plan is None:
            return False
        
        target_plan.items.append(PlanItem(text=item_text))
        self.save(plans)
        return True
    
    def remove_item_from_plan(self, title_or_number: str, item_number: int) -> bool:
        """Remove an item from a plan by its number (1-indexed). Returns True if successful."""
        plans = self.load()
        
        # Find the plan
        target_plan = None
        plan_idx = -1
        
        # Try to interpret as a number first
        try:
            number = int(title_or_number)
            if 1 <= number <= len(plans):
                target_plan = plans[number - 1]
                plan_idx = number - 1
        except ValueError:
            # Not a number, treat as title
            for i, plan in enumerate(plans):
                if plan.title.lower() == title_or_number.lower():
                    target_plan = plan
                    plan_idx = i
                    break
        
        if target_plan is None or item_number < 1 or item_number > len(target_plan.items):
            return False
        
        # Remove the item (adjusting for 1-indexed input)
        del target_plan.items[item_number - 1]
        self.save(plans)
        return True

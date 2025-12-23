"""
Executor for the Plan Operations pipeline.

This module implements the executor that can preview and apply operations
to the PlanStore with dry-run capability.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from .operations import CreatePlan, DeletePlan, AddPlanItem, RemovePlanItem, Commentary, Selector
from ..plans import PlanStore, Plan, PlanItem
from .decoder import DecodeError


@dataclass
class PreviewResult:
    """Result of a dry-run operation preview."""
    changes: List[str]  # Description of changes that would be made
    before_state: str   # State before operations
    after_state: str    # State after operations (if applied)


class PlanOpsExecutor:
    """Executor for plan operations with dry-run and apply functionality."""
    
    def __init__(self, plan_store: PlanStore = None):
        self.plan_store = plan_store or PlanStore()
    
    def _resolve_selector(self, selector: Selector, plans: List[Plan]) -> Optional[Plan]:
        """Resolve a selector to a specific plan."""
        if selector.index is not None:
            # Index is 1-based
            if 1 <= selector.index <= len(plans):
                return plans[selector.index - 1]
            else:
                raise DecodeError(f"Index {selector.index} out of range, only {len(plans)} plans exist")
        elif selector.title is not None:
            # Find plan by title (case-insensitive)
            for plan in plans:
                if plan.title.lower() == selector.title.lower():
                    return plan
            raise DecodeError(f"Plan with title '{selector.title}' not found")
        else:
            raise DecodeError("Selector must have either title or index")
    
    def _preview_create_plan(self, op: CreatePlan, plans: List[Plan]) -> List[str]:
        """Preview a CreatePlan operation."""
        # Check if plan already exists
        for plan in plans:
            if plan.title.lower() == op.title.lower():
                raise DecodeError(f"Plan with title '{op.title}' already exists")
        
        return [f"Create plan: '{op.title}'"]
    
    def _preview_delete_plan(self, op: DeletePlan, plans: List[Plan]) -> List[str]:
        """Preview a DeletePlan operation."""
        target_plan = self._resolve_selector(op.selector, plans)
        if target_plan:
            return [f"Delete plan: '{target_plan.title}'"]
        else:
            raise DecodeError(f"Plan not found for deletion: {op.selector}")
    
    def _preview_add_plan_item(self, op: AddPlanItem, plans: List[Plan]) -> List[str]:
        """Preview an AddPlanItem operation."""
        target_plan = self._resolve_selector(op.selector, plans)
        if target_plan:
            return [f"Add item to plan '{target_plan.title}': '{op.text}'"]
        else:
            raise DecodeError(f"Plan not found for adding item: {op.selector}")
    
    def _preview_remove_plan_item(self, op: RemovePlanItem, plans: List[Plan]) -> List[str]:
        """Preview a RemovePlanItem operation."""
        target_plan = self._resolve_selector(op.selector, plans)
        if not target_plan:
            raise DecodeError(f"Plan not found for removing item: {op.selector}")
        
        if op.item_index < 1 or op.item_index > len(target_plan.items):
            raise DecodeError(f"Item index {op.item_index} out of range for plan '{target_plan.title}', "
                            f"only {len(target_plan.items)} items exist")
        
        item_text = target_plan.items[op.item_index - 1].text
        return [f"Remove item {op.item_index} from plan '{target_plan.title}': '{item_text}'"]
    
    def _apply_create_plan(self, op: CreatePlan, plans: List[Plan]) -> List[Plan]:
        """Apply a CreatePlan operation."""
        # Check if plan already exists
        for plan in plans:
            if plan.title.lower() == op.title.lower():
                raise DecodeError(f"Plan with title '{op.title}' already exists")
        
        new_plan = Plan(title=op.title, items=[])
        plans.append(new_plan)
        return plans
    
    def _apply_delete_plan(self, op: DeletePlan, plans: List[Plan]) -> List[Plan]:
        """Apply a DeletePlan operation."""
        target_plan = self._resolve_selector(op.selector, plans)
        plans = [p for p in plans if p.title.lower() != target_plan.title.lower()]
        return plans
    
    def _apply_add_plan_item(self, op: AddPlanItem, plans: List[Plan]) -> List[Plan]:
        """Apply an AddPlanItem operation."""
        target_plan = self._resolve_selector(op.selector, plans)
        target_plan.items.append(PlanItem(text=op.text))
        return plans
    
    def _apply_remove_plan_item(self, op: RemovePlanItem, plans: List[Plan]) -> List[Plan]:
        """Apply a RemovePlanItem operation."""
        target_plan = self._resolve_selector(op.selector, plans)
        
        if op.item_index < 1 or op.item_index > len(target_plan.items):
            raise DecodeError(f"Item index {op.item_index} out of range for plan '{target_plan.title}', "
                            f"only {len(target_plan.items)} items exist")
        
        # Remove the item (adjusting for 1-indexed input)
        del target_plan.items[op.item_index - 1]
        return plans
    
    def preview_ops(self, ops: List) -> PreviewResult:
        """Preview what changes would be made by applying operations."""
        # Load current state
        current_plans = self.plan_store.load()
        before_state = self.plan_store._format_content(current_plans)

        # Create a deep copy of the plans to simulate changes without modifying the original
        from copy import deepcopy
        simulated_plans = deepcopy(current_plans)

        changes = []
        for op in ops:
            if isinstance(op, CreatePlan):
                changes.extend(self._preview_create_plan(op, simulated_plans))
                simulated_plans = self._apply_create_plan(op, simulated_plans)
            elif isinstance(op, DeletePlan):
                changes.extend(self._preview_delete_plan(op, simulated_plans))
                simulated_plans = self._apply_delete_plan(op, simulated_plans)
            elif isinstance(op, AddPlanItem):
                changes.extend(self._preview_add_plan_item(op, simulated_plans))
                simulated_plans = self._apply_add_plan_item(op, simulated_plans)
            elif isinstance(op, RemovePlanItem):
                changes.extend(self._preview_remove_plan_item(op, simulated_plans))
                simulated_plans = self._apply_remove_plan_item(op, simulated_plans)
            elif isinstance(op, Commentary):
                # Commentary operations don't change the plan state
                continue
            else:
                raise DecodeError(f"Unknown operation type: {type(op)}")

        after_state = self.plan_store._format_content(simulated_plans)

        return PreviewResult(
            changes=changes,
            before_state=before_state,
            after_state=after_state
        )
    
    def apply_ops(self, ops: List, dry_run: bool = False) -> PreviewResult:
        """
        Apply operations to the PlanStore.
        
        Args:
            ops: List of operations to apply
            dry_run: If True, only preview changes without applying them
            
        Returns:
            PreviewResult with details of changes made
        """
        if dry_run:
            return self.preview_ops(ops)
        
        # Actually apply the operations
        # First, load the current plans
        plans = self.plan_store.load()

        # Process operations in order, but handle them directly rather than using PlanStore methods
        # that might expect the plan to exist already
        for op in ops:
            if isinstance(op, CreatePlan):
                # Check if plan already exists
                if any(p.title.lower() == op.title.lower() for p in plans):
                    raise DecodeError(f"Plan with title '{op.title}' already exists")
                # Add the new plan
                new_plan = Plan(title=op.title, items=[])
                plans.append(new_plan)

            elif isinstance(op, DeletePlan):
                # Find and remove the plan
                target_plan = self._resolve_selector(op.selector, plans)
                plans = [p for p in plans if p.title.lower() != target_plan.title.lower()]

            elif isinstance(op, AddPlanItem):
                # Find the target plan and add the item
                target_plan = self._resolve_selector(op.selector, plans)
                target_plan.items.append(PlanItem(text=op.text))

            elif isinstance(op, RemovePlanItem):
                # Find the target plan and remove the item
                target_plan = self._resolve_selector(op.selector, plans)

                if op.item_index < 1 or op.item_index > len(target_plan.items):
                    raise DecodeError(f"Item index {op.item_index} out of range for plan '{target_plan.title}', "
                                    f"only {len(target_plan.items)} items exist")

                # Remove the item (adjusting for 1-indexed input)
                del target_plan.items[op.item_index - 1]

            elif isinstance(op, Commentary):
                # Commentary operations don't change the plan state
                continue
            else:
                raise DecodeError(f"Unknown operation type: {type(op)}")

        # Save the updated plans all at once
        self.plan_store.save(plans)
        
        # Return a preview result showing the changes
        after_plans = self.plan_store.load()
        after_state = self.plan_store._format_content(after_plans)
        
        # For apply mode, we return changes but don't calculate before state again
        # since apply already modified the file
        non_commentary_ops = [op for op in ops if not isinstance(op, Commentary)]
        return PreviewResult(
            changes=[f"Applied {len(non_commentary_ops)} operations"],
            before_state="",  # Not calculated for apply mode
            after_state=after_state
        )
"""
Prompt contract for Plan Discuss command.

This module defines the prompt template specifically for Plan Discuss that includes:
- The selected plan title + current items (numbered)
- Allowed actions (create plan? optional; primarily edit selected plan)
- The canonical JSON schema summary
- Hard constraints:

  * respond with **only** the JSON (no prose)
  * action list must be minimal and intentional
  * selectors must target the selected plan (unless explicitly allowed otherwise)

Make the prompt "engine-neutral"; AI-manager chooses the engine.
"""

def get_plan_discuss_prompt(plan_title: str, plan_items: list) -> str:
    """
    Generate the prompt for plan discussion AI interaction.
    
    Args:
        plan_title: The title of the plan being discussed
        plan_items: List of plan items with their numbers and text
        
    Returns:
        Formatted prompt string for the AI
    """
    # Format the plan items for the prompt
    items_text = ""
    for item in plan_items:
        items_text += f"  {item['number']}. {item['text']}\n"
    
    prompt = f"""
You are a planning assistant. The user wants to discuss and potentially modify the following plan:

Plan Title: {plan_title}
Plan Items:
{items_text}

Your task is to suggest changes to this plan by returning a JSON object in the following canonical PlanOpsResult format:

{{
  "kind": "plan_ops",
  "version": 1,
  "scope": "plan",
  "actions": [
    {{
      "action": "plan_item_add",
      "selector": {{"title": "{plan_title}"}},
      "text": "New item text"
    }},
    {{
      "action": "plan_item_remove", 
      "selector": {{"title": "{plan_title}"}},
      "item_index": 1
    }}
  ],
  "notes": "Brief description of changes"
}}

Valid actions:
- plan_create: Create a new plan (title: string)
- plan_delete: Delete a plan (selector: {{title: string}} or {{index: number}})
- plan_item_add: Add an item to a plan (selector: {{title: string}} or {{index: number}}, text: string)
- plan_item_remove: Remove an item from a plan (selector: {{title: string}} or {{index: number}}, item_index: number)
- commentary: Add commentary (text: string) - ignored by executor

Constraints:
- Respond with ONLY the JSON object, no other text
- All selectors must target the selected plan unless explicitly asked to modify others
- Actions must be minimal and intentional
- Use the exact field names and structure shown in the example
- Use 1-based indexing for item numbers
- Only return actions that make sense for the user's request

Example of what NOT to do:
- Do not return prose or explanations outside the JSON
- Do not return multiple JSON objects
- Do not use invalid action types
"""
    return prompt.strip()
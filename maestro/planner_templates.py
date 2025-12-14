"""
Maestro Planner Prompt Templates

This module contains the three canonical planner prompt templates for:
1. Build target planning
2. Fix rulebook planning  
3. Conversion pipeline planning

Each template follows the Task 4 prompt contract and ensures JSON-only output.
"""

from typing import List, Dict, Any, Optional


def build_prompt_template(goal: str, context: str, requirements: str, acceptance: str, deliverables: str) -> str:
    """
    Generic prompt builder that follows the Task 4 contract.
    
    Args:
        goal: The specific goal of the prompt
        context: All relevant context information
        requirements: Specific requirements for the response
        acceptance: Acceptance criteria for the response
        deliverables: Expected deliverables from the response
        
    Returns:
        Formatted prompt string
    """
    return f"""[GOAL]
{goal}

[CONTEXT]
{context}

[REQUIREMENTS]
{requirements}

[ACCEPTANCE CRITERIA]
{acceptance}

[DELIVERABLES]
{deliverables}

[IMPORTANT]
- Return ONLY the requested JSON object with no additional text or explanations
- The response must be valid JSON that can be parsed without errors
- Do not include markdown code blocks or any formatting beyond the JSON structure
- All necessary fields must be properly structured according to the schema
"""


# Template for build target planning
BUILD_TARGET_PLANNER_TEMPLATE = """
[GOAL]
Produce or modify a build target JSON definition that specifies how to build the software, including pipeline steps, patterns to match errors, and execution environment.

[CONTEXT]
Repo root: {{repo_root}}
Current active build target JSON (if exists): {{current_target_json}}
User builder goals (from root summary/categories if available): {{user_goals}}
Any existing pipeline run summary (optional): {{pipeline_summary}}

[REQUIREMENTS]
- Strict JSON output only with no additional text
- Schema fields required: name, target_id, categories, description, why, pipeline steps with id/cmd/optional, patterns section if used, environment (optional)
- Each pipeline step must have: id (string), cmd (array of strings), optional (boolean)
- Pattern section may include: error_extract (array of regex strings), ignore (array of regex strings)  
- Environment may include: vars (object with key-value pairs), cwd (string)
- Must not invent file paths that don't exist (propose placeholders clearly if needed)
- Return only the complete JSON object with no markdown ```json ``` wrappers

[ACCEPTANCE CRITERIA]
- Output parses as valid JSON
- Includes at least one 'build' step in the pipeline
- All required schema fields are present and properly structured
- Contains no additional text or explanations outside the JSON object
- JSON can be parsed without errors

[DELIVERABLES]
- Final JSON object only containing the complete build target specification
- Must include target_id, name, categories, description, why, pipeline, and optional patterns/environment
- Pipeline steps with proper id, cmd, and optional fields
- No markdown formatting or extra text
"""


# Template for fix rulebook planning
FIX_RULEBOOK_PLANNER_TEMPLATE = """
[GOAL]
Produce or modify a fix rulebook JSON definition that contains reactive rules for automatically fixing diagnostic issues.

[CONTEXT]
Current rulebook JSON (if exists): {{current_rulebook_json}}
Examples of diagnostic signatures/messages (if available): {{diagnostic_examples}}
Repo mapping info (which repos will use it): {{repo_info}}

[REQUIREMENTS]
- Strict JSON output only with no additional text
- Schema fields required: rulebook name, description, version, rules array
- Each rule in rules[] must have: id, enabled, priority, match (with contains/regex), confidence, explanation, actions[], verify strategy
- Rule actions can be: hint, prompt_patch, structure_fix with appropriate configuration
- Verify strategy should indicate how to confirm the fix worked (signature gone, build step pass, etc.)
- Each rule must include match logic and appropriate actions
- Return only the complete JSON object with no markdown ```json ``` wrappers

[ACCEPTANCE CRITERIA]
- Output parses as valid JSON
- At least 1 rule exists in the rules array
- Rules include proper match logic and actions
- All required schema fields are present and properly structured
- Contains no additional text or explanations outside the JSON object
- JSON can be parsed without errors

[DELIVERABLES]
- Final JSON object only containing the complete rulebook specification
- Must include version, name, description, and rules array
- Each rule with id, enabled, priority, match, confidence, explanation, actions, and verify
- No markdown formatting or extra text
"""


# Template for conversion pipeline planning
CONVERSION_PIPELINE_PLANNER_TEMPLATE = """
[GOAL]
Produce a conversion pipeline plan with stages and success criteria for converting from source technology to target technology.

[CONTEXT]
Repo inventory summary (if available): {{repo_inventory}}
Target conversion goal A→B: {{conversion_goal}}
Constraints (build system, language, minimal compile requirements): {{constraints}}

[REQUIREMENTS]
- Strict JSON output only with no additional text
- Required stages: overview, core_builds, grow_from_main, full_tree_check
- Each stage must include: entry criteria, exit criteria, artifacts produced, failure handling
- Stage structure: name, status, entry_criteria (array), exit_criteria (array), artifacts (array), failure_handling (string), details (object)
- Return only the complete JSON object with no markdown ```json ``` wrappers

[ACCEPTANCE CRITERIA]
- JSON parses successfully without errors
- All required stages exist (overview, core_builds, grow_from_main, full_tree_check)
- Each stage has defined exit criteria
- All required schema fields are present and properly structured
- Contains no additional text or explanations outside the JSON object
- JSON can be parsed without errors

[DELIVERABLES]
- Final JSON object only containing the complete conversion pipeline specification
- Must include all required stages with entry/exit criteria and failure handling
- Each stage properly structured with name, status, criteria, artifacts, and handling
- No markdown formatting or extra text
"""


def format_build_target_template(repo_root: str = "", current_target_json: str = "{}", user_goals: str = "", pipeline_summary: str = "") -> str:
    """
    Format the build target planner template with specific context values.
    
    Args:
        repo_root: Repository root path
        current_target_json: Current build target JSON (if exists)  
        user_goals: User builder goals from root summary/categories
        pipeline_summary: Existing pipeline run summary (if any)
        
    Returns:
        Formatted prompt string
    """
    return BUILD_TARGET_PLANNER_TEMPLATE.format(
        repo_root=repo_root or "(not specified)",
        current_target_json=current_target_json,
        user_goals=user_goals or "(not specified)",
        pipeline_summary=pipeline_summary or "(no previous summary)"
    )


def format_fix_rulebook_template(current_rulebook_json: str = "{}", diagnostic_examples: str = "", repo_info: str = "") -> str:
    """
    Format the fix rulebook planner template with specific context values.
    
    Args:
        current_rulebook_json: Current rulebook JSON (if exists)
        diagnostic_examples: Examples of diagnostic signatures/messages
        repo_info: Information about which repos will use the rulebook
        
    Returns:
        Formatted prompt string
    """
    return FIX_RULEBOOK_PLANNER_TEMPLATE.format(
        current_rulebook_json=current_rulebook_json,
        diagnostic_examples=diagnostic_examples or "(no examples provided)",
        repo_info=repo_info or "(not specified)"
    )


def format_conversion_pipeline_template(repo_inventory: str = "", conversion_goal: str = "", constraints: str = "") -> str:
    """
    Format the conversion pipeline planner template with specific context values.
    
    Args:
        repo_inventory: Repository inventory summary
        conversion_goal: Target conversion goal A→B
        constraints: Constraints (build system, language, requirements)
        
    Returns:
        Formatted prompt string
    """
    return CONVERSION_PIPELINE_PLANNER_TEMPLATE.format(
        repo_inventory=repo_inventory or "(not specified)",
        conversion_goal=conversion_goal or "(not specified)",
        constraints=constraints or "(no constraints specified)"
    )
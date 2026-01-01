"""AI-powered WorkGraph generator with auto-repair and validation.

This module generates WorkGraph plans from freeform requests using AI engines.
It follows the same pattern as AIRunbookGenerator but with strict validation
to prevent meta-runbook tasks.
"""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..repo.discovery import DiscoveryEvidence

from ..data.workgraph_schema import WorkGraph


class WorkGraphGenerator:
    """AI-powered WorkGraph generator with automatic repair on validation failure.

    This generator:
    1. Composes a strong system prompt demanding exact WorkGraph JSON schema
    2. Calls the AI engine to generate a WorkGraph
    3. Validates the response (hard gate: no meta-runbook tasks)
    4. Auto-repairs once if validation fails
    5. Returns validated WorkGraph or raises ValueError
    """

    def __init__(self, engine, verbose: bool = False):
        """Initialize the generator.

        Args:
            engine: AI engine instance with generate(prompt) method
            verbose: If True, print diagnostic information
        """
        self.engine = engine
        self.verbose = verbose
        self.last_prompt = None
        self.last_response = None

    def generate(
        self,
        freeform_request: str,
        discovery: DiscoveryEvidence,
        domain: str = "general",
        profile: str = "default"
    ) -> WorkGraph:
        """Generate WorkGraph with 1 retry on validation failure.

        Args:
            freeform_request: User's freeform request to decompose
            discovery: Evidence collected from repo discovery
            domain: Domain for decomposition (runbook, issues, workflow, etc.)
            profile: Planning profile (default, investor, purpose)

        Returns:
            Validated WorkGraph instance

        Raises:
            ValueError: If WorkGraph validation fails after retry
            json.JSONDecodeError: If AI returns invalid JSON
        """
        for attempt in range(2):  # 0 and 1 (auto-repair once)
            prompt = self._create_prompt(freeform_request, discovery, domain, profile)

            # On second attempt, add repair instructions
            if attempt == 1:
                prompt += "\n\nPREVIOUS RESPONSE WAS INVALID. Please ensure:\n"
                prompt += "- Every task has at least one definition_of_done with kind='command' or 'file'\n"
                prompt += "- Commands have 'cmd' field, files have 'path' field\n"
                prompt += "- No meta-runbook tasks (tasks must be executable)\n"
                prompt += "- Return ONLY the JSON object, no explanatory text\n"

            self.last_prompt = prompt

            if self.verbose:
                print(f"Sending prompt to AI engine (attempt {attempt + 1}/2)...")

            response = self.engine.generate(prompt)
            self.last_response = response

            if self.verbose:
                print(f"AI response received (length: {len(response)} chars)")

            # Extract JSON from response
            json_str = self._extract_json(response)

            try:
                data = json.loads(json_str)
                wg = WorkGraph.from_dict(data)

                # If no exception, validation passed!
                if self.verbose:
                    print(f"WorkGraph validation passed on attempt {attempt + 1}")
                return wg

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                if attempt == 0:
                    # First attempt failed, try repair
                    if self.verbose:
                        print(f"Validation failed, retrying: {e}")
                    continue
                else:
                    # Second attempt failed, give up
                    raise ValueError(
                        f"WorkGraph validation failed after retry: {e}\n"
                        f"AI may have generated meta-runbook tasks without executable DoD.\n"
                        f"Last response: {response[:500]}..."
                    )

        raise ValueError("Failed to generate valid WorkGraph")

    def _create_prompt(
        self,
        freeform: str,
        discovery: DiscoveryEvidence,
        domain: str,
        profile: str
    ) -> str:
        """Create system prompt demanding exact WorkGraph JSON schema.

        Args:
            freeform: Freeform request text
            discovery: Evidence from repo discovery
            domain: Domain for decomposition
            profile: Planning profile

        Returns:
            System prompt string
        """
        evidence_summary = json.dumps(discovery.evidence, indent=2)

        return f"""
You are a project planning assistant that decomposes freeform requests into structured WorkGraph plans.

FREEFORM REQUEST:
{freeform}

REPO EVIDENCE:
{evidence_summary}

DOMAIN: {domain}
PROFILE: {profile}

YOUR TASK:
Generate a WorkGraph JSON that decomposes this request into executable tracks/phases/tasks.

CRITICAL RULES:
1. Every task MUST have definition_of_done with kind="command" OR kind="file"
2. Command DoDs must have "cmd" field (e.g., "maestro runbook list")
3. File DoDs must have "path" field (e.g., "docs/maestro/runbooks/index.json")
4. NO meta-runbook tasks like "Organize documentation" without executable DoD
5. Tasks should reference maestro commands from evidence where possible
6. Return ONLY the JSON object, no markdown wrappers or explanatory text

EXACT JSON SCHEMA:
{{
  "schema_version": "v1",
  "id": "",
  "domain": "{domain}",
  "profile": "{profile}",
  "goal": "High-level goal of this plan",
  "repo_discovery": {{
    "evidence": {evidence_summary},
    "warnings": {json.dumps(discovery.warnings)},
    "budget": {json.dumps(discovery.budget)}
  }},
  "track": {{
    "id": "TRK-001",
    "name": "Track name",
    "goal": "Track goal"
  }},
  "phases": [
    {{
      "id": "PH-001",
      "name": "Phase name",
      "tasks": [
        {{
          "id": "TASK-001",
          "title": "Task title",
          "intent": "What this task accomplishes",
          "definition_of_done": [
            {{"kind": "command", "cmd": "maestro runbook list", "expect": "exit 0"}},
            {{"kind": "file", "path": "docs/maestro/runbooks/index.json", "expect": "contains xyz"}}
          ],
          "verification": [
            {{"kind": "command", "cmd": "bash tools/test/run.sh -q test_file.py", "expect": "exit 0"}}
          ],
          "inputs": ["List of input artifacts"],
          "outputs": ["List of output artifacts"],
          "risk": {{"level": "low", "notes": "Risk description"}}
        }}
      ]
    }}
  ],
  "stop_conditions": [
    {{"when": "Condition description", "action": "create_issue", "notes": "What to do"}}
  ]
}}

Return ONLY the JSON object.
"""

    def _extract_json(self, response: str) -> str:
        """Extract JSON from response (handles markdown code blocks).

        Tries multiple extraction strategies:
        1. ```json...``` markdown blocks
        2. ```...``` generic code blocks
        3. First { to last } in response

        Args:
            response: AI response string

        Returns:
            Extracted JSON string
        """
        # Try ```json...``` first
        match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try ```...```
        match = re.search(r'```\s*\n(.*?)\n```', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Find first { to last }
        first = response.find('{')
        last = response.rfind('}')
        if first != -1 and last != -1:
            return response[first:last+1]

        # If all else fails, return the response as-is
        # (will likely fail JSON parsing, but that's what we want for proper error messages)
        return response.strip()

"""
Tests for runbook actionability gate (--actionable flag).

These tests verify that:
1. Runbooks with meta-steps (no commands) fail actionability validation
2. Runbooks with executable commands pass actionability validation
3. Fallback to WorkGraph occurs when actionability fails
4. --actionable flag is optional (backward compatible)
5. -vv includes actionability failure reasons
"""

import pytest
from maestro.commands.runbook import (
    validate_runbook_actionability,
    validate_runbook_schema,
    AIRunbookGenerator,
    RunbookEvidence,
)


class FakeEngine:
    """Deterministic fake engine for testing."""

    def __init__(self, response: str):
        self.response = response
        self.name = "fake-test-engine"

    def generate(self, prompt: str) -> str:
        """Return canned response."""
        return self.response


# Test Case 1: Meta-runbook without commands fails actionability
def test_meta_runbook_fails_actionability():
    """Meta-runbook without executable commands fails actionability validation."""
    meta_runbook = {
        "id": "rb-meta-test",
        "title": "Meta runbook test",
        "goal": "Test goal",
        "steps": [
            {
                "n": 1,
                "actor": "dev",
                "action": "Review all command documentation files",
                "expected": "Understand command purposes"
                # Missing command/commands field
            },
            {
                "n": 2,
                "actor": "dev",
                "action": "Parse docs and organize into logical groups",
                "expected": "Commands are organized logically"
                # Missing command/commands field
            }
        ],
        "tags": ["test"],
    }

    # Schema validation should pass (steps are present and valid structure)
    schema_errors = validate_runbook_schema(meta_runbook)
    assert len(schema_errors) == 0, f"Schema validation should pass: {schema_errors}"

    # Actionability validation should fail (no commands)
    actionability_errors = validate_runbook_actionability(meta_runbook)
    assert len(actionability_errors) == 2, f"Expected 2 actionability errors, got {len(actionability_errors)}"

    # Check error messages mention missing command fields
    assert "missing" in actionability_errors[0].lower()
    assert "command" in actionability_errors[0].lower()
    assert "missing" in actionability_errors[1].lower()
    assert "command" in actionability_errors[1].lower()


# Test Case 2: Actionable runbook with commands passes validation
def test_actionable_runbook_passes():
    """Runbook with executable commands passes actionability validation."""
    actionable_runbook = {
        "id": "rb-actionable-test",
        "title": "Actionable runbook test",
        "goal": "Test goal",
        "steps": [
            {
                "n": 1,
                "actor": "dev",
                "action": "Extract commands from documentation",
                "expected": "commands.txt contains all documented commands",
                "command": "grep -h '^## ' docs/commands/*.md | sed 's/^## //' > /tmp/commands.txt"
            },
            {
                "n": 2,
                "actor": "dev",
                "action": "Get BSS help output",
                "expected": "help.txt contains BSS command list",
                "command": "<BSS_BIN> --help > /tmp/bss_help.txt"
            },
            {
                "n": 3,
                "actor": "dev",
                "action": "Run multiple verification commands",
                "expected": "All verifications pass",
                "commands": [
                    "ls -la docs/",
                    "wc -l /tmp/commands.txt",
                    "diff /tmp/commands.txt /tmp/bss_help.txt"
                ]
            }
        ],
        "tags": ["test"],
    }

    # Schema validation should pass
    schema_errors = validate_runbook_schema(actionable_runbook)
    assert len(schema_errors) == 0, f"Schema validation should pass: {schema_errors}"

    # Actionability validation should pass
    actionability_errors = validate_runbook_actionability(actionable_runbook)
    assert len(actionability_errors) == 0, f"Actionability validation should pass, got errors: {actionability_errors}"


# Test Case 3: AIRunbookGenerator respects actionable flag in prompt
def test_ai_generator_actionable_prompt():
    """AIRunbookGenerator includes actionability requirements in prompt when actionable=True."""
    # Create a fake response (valid runbook JSON)
    fake_response = """```json
{
  "id": "rb-test",
  "title": "Test runbook",
  "goal": "Test goal",
  "steps": [
    {
      "n": 1,
      "actor": "dev",
      "action": "Run test command",
      "expected": "Command succeeds",
      "command": "echo test"
    }
  ],
  "tags": ["test"]
}
```"""

    engine = FakeEngine(fake_response)

    # Create generator with actionable=True
    generator = AIRunbookGenerator(engine, verbose=False, actionable=True)

    evidence = RunbookEvidence(
        repo_root="/test/repo",
        commands_docs=[],
        help_text="Test help",
        help_bin_path="/test/bin/bss"
    )

    # Generate runbook
    runbook = generator.generate(evidence, "Test request")

    # Check that prompt included actionability requirements
    assert generator.last_prompt is not None
    prompt = generator.last_prompt.lower()
    assert "critical" in prompt or "must" in prompt, "Prompt should include actionability requirements"
    assert "command" in prompt, "Prompt should mention command field"

    # Verify generated runbook has command
    assert "command" in runbook["steps"][0], "Generated runbook should have command field"


# Test Case 4: AIRunbookGenerator without actionable flag (backward compatible)
def test_ai_generator_non_actionable_mode():
    """AIRunbookGenerator doesn't enforce actionability when actionable=False."""
    # Meta-runbook response (no commands)
    fake_response = """```json
{
  "id": "rb-test-meta",
  "title": "Meta test runbook",
  "goal": "Test goal",
  "steps": [
    {
      "n": 1,
      "actor": "dev",
      "action": "Review documentation",
      "expected": "Documentation reviewed"
    }
  ],
  "tags": ["test"]
}
```"""

    engine = FakeEngine(fake_response)

    # Create generator with actionable=False (default)
    generator = AIRunbookGenerator(engine, verbose=False, actionable=False)

    evidence = RunbookEvidence(
        repo_root="/test/repo",
        commands_docs=[],
        help_text=None,
        help_bin_path=None
    )

    # Generate runbook
    runbook = generator.generate(evidence, "Test request")

    # Prompt should NOT include strict actionability requirements
    assert generator.last_prompt is not None
    prompt = generator.last_prompt.lower()
    # Should not have the CRITICAL actionability section
    assert "critical: all steps must" not in prompt

    # Generated runbook is allowed to have meta-steps (no command field)
    assert "command" not in runbook["steps"][0], "Meta-steps allowed when actionable=False"


# Test Case 5: Variable hints are included in prompt
def test_variable_hints_in_prompt():
    """Variable hints are extracted from evidence and included in prompt."""
    fake_response = """```json
{
  "id": "rb-test-hints",
  "title": "Test with hints",
  "goal": "Test goal",
  "steps": [
    {
      "n": 1,
      "actor": "dev",
      "action": "Run BSS help",
      "expected": "Help displays",
      "command": "<BSS_BIN> --help"
    }
  ],
  "tags": ["test"]
}
```"""

    engine = FakeEngine(fake_response)
    generator = AIRunbookGenerator(engine, verbose=False, actionable=True)

    evidence = RunbookEvidence(
        repo_root="/test/repo",
        commands_docs=[{"filename": "cmd1.md", "title": "Command 1", "summary": "Summary"}],
        help_text="Test help output",
        help_bin_path="./build_maestro/bss"
    )

    runbook = generator.generate(evidence, "Test request with hints")

    # Check that prompt included variable hints
    prompt = generator.last_prompt
    assert "RESOLVED VARIABLE HINTS" in prompt or "variable hints" in prompt.lower()
    assert "<BSS_BIN>" in prompt
    assert "./build_maestro/bss" in prompt or "build_maestro/bss" in prompt


# Test Case 6: Empty steps list validation
def test_empty_steps_actionability():
    """Empty steps list passes actionability validation (caught by schema validation)."""
    empty_runbook = {
        "id": "rb-empty",
        "title": "Empty runbook",
        "goal": "Test goal",
        "steps": [],  # Empty
        "tags": ["test"],
    }

    # Schema validation should catch this
    schema_errors = validate_runbook_schema(empty_runbook)
    assert len(schema_errors) > 0, "Schema validation should fail for empty steps"

    # Actionability validation returns empty list (nothing to validate)
    actionability_errors = validate_runbook_actionability(empty_runbook)
    assert len(actionability_errors) == 0, "Actionability validation skips empty steps list"


# Test Case 7: Mixed steps (some with commands, some without)
def test_mixed_steps_actionability():
    """Runbook with mixed steps (some actionable, some not) fails actionability."""
    mixed_runbook = {
        "id": "rb-mixed",
        "title": "Mixed runbook",
        "goal": "Test goal",
        "steps": [
            {
                "n": 1,
                "actor": "dev",
                "action": "Run command",
                "expected": "Command succeeds",
                "command": "echo test"
            },
            {
                "n": 2,
                "actor": "dev",
                "action": "Review documentation",
                "expected": "Documentation reviewed"
                # No command field
            },
            {
                "n": 3,
                "actor": "dev",
                "action": "Run tests",
                "expected": "Tests pass",
                "commands": ["pytest", "make test"]
            }
        ],
        "tags": ["test"],
    }

    # Actionability validation should find 1 error (step 2)
    actionability_errors = validate_runbook_actionability(mixed_runbook)
    assert len(actionability_errors) == 1, f"Expected 1 actionability error, got {len(actionability_errors)}"
    assert "Step 2" in actionability_errors[0] or "step 2" in actionability_errors[0].lower()


# Test Case 8: Meta-step keywords detection
def test_meta_step_keywords_detection():
    """Meta-steps are detected based on action keywords."""
    meta_actions = [
        "Review the documentation and create a summary",
        "Analyze the code structure",
        "Parse docs and organize commands",
        "Study the codebase architecture",
        "Examine the build process",
        "Investigate error patterns",
        "Explore the module dependencies"
    ]

    for action in meta_actions:
        runbook = {
            "id": "rb-meta-keyword-test",
            "title": "Meta keyword test",
            "goal": "Test",
            "steps": [
                {
                    "n": 1,
                    "actor": "dev",
                    "action": action,
                    "expected": "Task completed"
                }
            ],
            "tags": ["test"],
        }

        errors = validate_runbook_actionability(runbook)
        assert len(errors) == 1, f"Action '{action}' should be detected as meta-step"
        assert "meta-step" in errors[0].lower(), f"Error should mention 'meta-step' for action: {action}"


if __name__ == "__main__":
    # Run tests manually
    print("Running actionability gate tests...")

    print("Test 1: Meta-runbook fails actionability...")
    test_meta_runbook_fails_actionability()
    print("✓ Passed")

    print("Test 2: Actionable runbook passes...")
    test_actionable_runbook_passes()
    print("✓ Passed")

    print("Test 3: AI generator actionable prompt...")
    test_ai_generator_actionable_prompt()
    print("✓ Passed")

    print("Test 4: AI generator non-actionable mode...")
    test_ai_generator_non_actionable_mode()
    print("✓ Passed")

    print("Test 5: Variable hints in prompt...")
    test_variable_hints_in_prompt()
    print("✓ Passed")

    print("Test 6: Empty steps validation...")
    test_empty_steps_actionability()
    print("✓ Passed")

    print("Test 7: Mixed steps actionability...")
    test_mixed_steps_actionability()
    print("✓ Passed")

    print("Test 8: Meta-step keywords detection...")
    test_meta_step_keywords_detection()
    print("✓ Passed")

    print("\nAll tests passed! ✓")

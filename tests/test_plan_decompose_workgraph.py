"""Tests for plan decompose WorkGraph generation.

These tests use FakeEngine to avoid AI dependencies and ensure deterministic behavior.
"""
import pytest
from pathlib import Path
from maestro.data.workgraph_schema import WorkGraph, DefinitionOfDone, Task, Phase
from maestro.repo.discovery import discover_repo, DiscoveryBudget, DiscoveryEvidence
from maestro.builders.workgraph_generator import WorkGraphGenerator


class FakeEngine:
    """Deterministic fake engine for tests."""

    def __init__(self, response: str):
        self.response = response
        self.name = "fake"

    def generate(self, prompt: str) -> str:
        return self.response


def test_workgraph_schema_validation_success():
    """Test that valid WorkGraph passes validation."""
    dod = DefinitionOfDone(kind="command", cmd="maestro runbook list", expect="exit 0")
    task = Task(
        id="TASK-001",
        title="Test task",
        intent="Test intent",
        definition_of_done=[dod],
        verification=[],
        inputs=[],
        outputs=[],
        risk={}
    )
    phase = Phase(id="PH-001", name="Test phase", tasks=[task])
    wg = WorkGraph(
        goal="Test goal",
        track={"id": "TRK-001", "name": "Test track"},
        phases=[phase]
    )
    assert wg.id.startswith("wg-")
    assert wg.schema_version == "v1"


def test_workgraph_schema_validation_fails_no_dod():
    """Test that task without DoD fails validation."""
    with pytest.raises(ValueError, match="missing definition_of_done"):
        task = Task(
            id="TASK-001",
            title="Bad task",
            intent="Test",
            definition_of_done=[],  # Empty!
            verification=[],
            inputs=[],
            outputs=[],
            risk={}
        )


def test_workgraph_schema_validation_fails_invalid_dod_kind():
    """Test that invalid DoD kind fails validation."""
    with pytest.raises(ValueError, match="kind must be"):
        dod = DefinitionOfDone(kind="invalid", expect="exit 0")
        task = Task(
            id="TASK-001",
            title="Bad task",
            intent="Test",
            definition_of_done=[dod],
            verification=[],
            inputs=[],
            outputs=[],
            risk={}
        )


def test_workgraph_schema_validation_fails_command_dod_missing_cmd():
    """Test that command DoD without cmd field fails validation."""
    with pytest.raises(ValueError, match="Command DoD missing"):
        dod = DefinitionOfDone(kind="command", expect="exit 0")  # Missing cmd!


def test_workgraph_schema_validation_fails_file_dod_missing_path():
    """Test that file DoD without path field fails validation."""
    with pytest.raises(ValueError, match="File DoD missing"):
        dod = DefinitionOfDone(kind="file", expect="exists")  # Missing path!


def test_discovery_respects_budget(tmp_path):
    """Test that discovery respects file/byte budgets."""
    # Create fixture repo
    (tmp_path / "README.md").write_text("Test repo")
    (tmp_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)")

    budget = DiscoveryBudget(max_files=1, max_bytes=100)
    discovery = discover_repo(tmp_path, budget)

    assert discovery.budget["files_processed"] <= 1
    assert len(discovery.evidence) <= budget.max_files + 1  # +1 for structure entry


def test_discovery_finds_readme_files(tmp_path):
    """Test that discovery finds README files in deterministic order."""
    # Create test files
    (tmp_path / "README.md").write_text("Main README")
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "README.md").write_text("Docs README")

    budget = DiscoveryBudget()
    discovery = discover_repo(tmp_path, budget)

    # Check that we found the READMEs
    readme_evidence = [e for e in discovery.evidence if e["kind"] == "file" and "README" in e["path"]]
    assert len(readme_evidence) >= 1


def test_discovery_finds_build_systems(tmp_path):
    """Test that discovery detects build system files."""
    (tmp_path / "package.json").write_text('{"name": "test"}')
    (tmp_path / "Makefile").write_text("all:\n\techo hello")

    budget = DiscoveryBudget()
    discovery = discover_repo(tmp_path, budget)

    build_evidence = [
        e for e in discovery.evidence
        if e["kind"] == "file" and ("package.json" in e["path"] or "Makefile" in e["path"])
    ]
    assert len(build_evidence) >= 1


def test_workgraph_generator_with_fake_engine():
    """Test WorkGraph generation with FakeEngine."""
    fake_response = """```json
{
  "schema_version": "v1",
  "domain": "runbook",
  "profile": "default",
  "goal": "Generate runbooks from evidence",
  "repo_discovery": {"evidence": [], "warnings": [], "budget": {}},
  "track": {"id": "TRK-001", "name": "Runbook Generation", "goal": "Create runbooks"},
  "phases": [{
    "id": "PH-001",
    "name": "Discovery",
    "tasks": [{
      "id": "TASK-001",
      "title": "Collect evidence",
      "intent": "Gather repo evidence",
      "definition_of_done": [
        {"kind": "command", "cmd": "maestro repo scan", "expect": "exit 0"}
      ],
      "verification": [
        {"kind": "file", "path": "docs/maestro/repos/index.json", "expect": "exists"}
      ],
      "inputs": [],
      "outputs": ["Evidence files"],
      "risk": {"level": "low", "notes": ""}
    }]
  }],
  "stop_conditions": []
}
```"""

    engine = FakeEngine(fake_response)
    generator = WorkGraphGenerator(engine=engine)

    discovery = DiscoveryEvidence(evidence=[], warnings=[], budget={})

    wg = generator.generate("Generate runbooks", discovery)

    assert wg.domain == "runbook"
    assert len(wg.phases) == 1
    assert len(wg.phases[0].tasks) == 1
    assert wg.phases[0].tasks[0].title == "Collect evidence"


def test_workgraph_generator_auto_repair():
    """Test that generator retries once on validation failure."""
    # First response is invalid (no DoD), second is valid
    engine = FakeEngine("")

    # We'll simulate auto-repair by tracking call count
    call_count = [0]
    responses = [
        # First response: invalid (task without DoD)
        """```json
{
  "schema_version": "v1",
  "domain": "general",
  "profile": "default",
  "goal": "Test goal",
  "repo_discovery": {"evidence": [], "warnings": [], "budget": {}},
  "track": {"id": "TRK-001", "name": "Test", "goal": "Test"},
  "phases": [{
    "id": "PH-001",
    "name": "Phase",
    "tasks": [{
      "id": "TASK-001",
      "title": "Bad task",
      "intent": "Intent",
      "definition_of_done": [],
      "verification": [],
      "inputs": [],
      "outputs": [],
      "risk": {}
    }]
  }],
  "stop_conditions": []
}
```""",
        # Second response: valid (task with DoD)
        """```json
{
  "schema_version": "v1",
  "domain": "general",
  "profile": "default",
  "goal": "Test goal",
  "repo_discovery": {"evidence": [], "warnings": [], "budget": {}},
  "track": {"id": "TRK-001", "name": "Test", "goal": "Test"},
  "phases": [{
    "id": "PH-001",
    "name": "Phase",
    "tasks": [{
      "id": "TASK-001",
      "title": "Good task",
      "intent": "Intent",
      "definition_of_done": [
        {"kind": "command", "cmd": "echo test", "expect": "exit 0"}
      ],
      "verification": [],
      "inputs": [],
      "outputs": [],
      "risk": {}
    }]
  }],
  "stop_conditions": []
}
```"""
    ]

    def multi_response_generate(prompt):
        idx = call_count[0]
        call_count[0] += 1
        return responses[min(idx, len(responses) - 1)]

    engine.generate = multi_response_generate
    generator = WorkGraphGenerator(engine=engine)
    discovery = DiscoveryEvidence(evidence=[], warnings=[], budget={})

    # Should succeed on second try
    wg = generator.generate("Test request", discovery)
    assert wg.phases[0].tasks[0].title == "Good task"
    assert call_count[0] == 2  # Called twice (auto-repair)


def test_workgraph_generator_fails_after_retry():
    """Test that generator raises ValueError after failed retry."""
    # Both responses are invalid
    engine = FakeEngine("""```json
{
  "schema_version": "v1",
  "domain": "general",
  "profile": "default",
  "goal": "Test goal",
  "repo_discovery": {"evidence": [], "warnings": [], "budget": {}},
  "track": {"id": "TRK-001", "name": "Test", "goal": "Test"},
  "phases": [{
    "id": "PH-001",
    "name": "Phase",
    "tasks": [{
      "id": "TASK-001",
      "title": "Bad task",
      "intent": "Intent",
      "definition_of_done": [],
      "verification": [],
      "inputs": [],
      "outputs": [],
      "risk": {}
    }]
  }],
  "stop_conditions": []
}
```""")

    generator = WorkGraphGenerator(engine=engine)
    discovery = DiscoveryEvidence(evidence=[], warnings=[], budget={})

    # Should fail after retry
    with pytest.raises(ValueError, match="validation failed after retry"):
        wg = generator.generate("Test request", discovery)


def test_workgraph_to_dict_from_dict_roundtrip():
    """Test that to_dict/from_dict roundtrip preserves data."""
    dod = DefinitionOfDone(kind="file", path="test.txt", expect="exists")
    task = Task(
        id="TASK-001",
        title="Test task",
        intent="Test intent",
        definition_of_done=[dod],
        verification=[],
        inputs=["input1"],
        outputs=["output1"],
        risk={"level": "low", "notes": "test"}
    )
    phase = Phase(id="PH-001", name="Test phase", tasks=[task])
    wg = WorkGraph(
        goal="Test goal",
        domain="workflow",
        profile="investor",
        track={"id": "TRK-001", "name": "Test track", "goal": "Track goal"},
        phases=[phase],
        stop_conditions=[{"when": "test", "action": "abort", "notes": "notes"}]
    )

    # Roundtrip
    data = wg.to_dict()
    wg2 = WorkGraph.from_dict(data)

    # Verify
    assert wg2.goal == wg.goal
    assert wg2.domain == wg.domain
    assert wg2.profile == wg.profile
    assert len(wg2.phases) == 1
    assert wg2.phases[0].tasks[0].title == "Test task"
    assert wg2.phases[0].tasks[0].definition_of_done[0].kind == "file"
    assert wg2.phases[0].tasks[0].definition_of_done[0].path == "test.txt"

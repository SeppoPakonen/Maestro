"""
Tests for UX goal evaluator and attempt planner.

All tests are deterministic with no AI required.
"""

import pytest
from maestro.ux.help_surface import HelpNode
from maestro.ux.evaluator import GoalEvaluator, AttemptPlan


def create_fake_surface():
    """Create a fake help surface for testing."""
    surface = {}

    # Root command
    surface[('maestro',)] = HelpNode(
        command_path=['maestro'],
        help_text='Maestro - AI Task Management CLI. Commands: plan, repo, runbook, ops',
        help_hash='hash1',
        discovered_subcommands=['plan', 'repo', 'runbook', 'ops']
    )

    # Plan commands
    surface[('maestro', 'plan')] = HelpNode(
        command_path=['maestro', 'plan'],
        help_text='Plan management. Create, decompose, and enact plans. Subcommands: list, add, decompose, enact',
        help_hash='hash2',
        discovered_subcommands=['list', 'add', 'decompose', 'enact', 'sprint']
    )

    surface[('maestro', 'plan', 'decompose')] = HelpNode(
        command_path=['maestro', 'plan', 'decompose'],
        help_text='Decompose a goal into a WorkGraph with tasks and dependencies.',
        help_hash='hash3',
        discovered_subcommands=[]
    )

    # Runbook commands
    surface[('maestro', 'runbook')] = HelpNode(
        command_path=['maestro', 'runbook'],
        help_text='Runbook management. Create actionable runbooks. Subcommands: list, show, resolve',
        help_hash='hash4',
        discovered_subcommands=['list', 'show', 'resolve', 'add']
    )

    surface[('maestro', 'runbook', 'resolve')] = HelpNode(
        command_path=['maestro', 'runbook', 'resolve'],
        help_text='Create a runbook from a goal or repository analysis.',
        help_hash='hash5',
        discovered_subcommands=[]
    )

    # Repo commands
    surface[('maestro', 'repo')] = HelpNode(
        command_path=['maestro', 'repo'],
        help_text='Repository management and analysis.',
        help_hash='hash6',
        discovered_subcommands=['resolve', 'refresh']
    )

    return surface


def test_evaluator_keyword_extraction():
    """Test that keywords are extracted from goals."""
    surface = create_fake_surface()
    evaluator = GoalEvaluator(surface, verbose=False)

    goal = "Create an actionable runbook for building the project"
    keywords = evaluator._extract_goal_keywords(goal)

    # Should extract meaningful keywords
    assert 'actionable' in keywords
    assert 'runbook' in keywords
    assert 'building' in keywords
    assert 'project' in keywords

    # Should filter stop words
    assert 'the' not in keywords
    assert 'for' not in keywords


def test_evaluator_command_scoring():
    """Test that commands are scored based on keyword matches."""
    surface = create_fake_surface()
    evaluator = GoalEvaluator(surface, verbose=False)

    goal_keywords = {'runbook', 'actionable'}

    # Score runbook command (should have high score)
    runbook_score = evaluator._score_command(('maestro', 'runbook'), goal_keywords)
    assert runbook_score > 0  # Has "runbook" in command path

    # Score plan command (should have lower score)
    plan_score = evaluator._score_command(('maestro', 'plan'), goal_keywords)

    # Runbook should score higher than plan
    assert runbook_score >= plan_score


def test_evaluator_attempt_plan_generation():
    """Test that attempt plan is generated from goal."""
    surface = create_fake_surface()
    evaluator = GoalEvaluator(surface, verbose=False)

    goal = "Create a runbook for the repository"
    plan = evaluator.generate_attempt_plan(goal)

    # Should generate attempts
    assert len(plan.attempts) > 0

    # Should include runbook commands (high relevance)
    runbook_attempts = [
        attempt for attempt in plan.attempts
        if 'runbook' in attempt
    ]
    assert len(runbook_attempts) > 0

    # Should have reasoning
    assert plan.reasoning != ""
    assert 'runbook' in plan.reasoning.lower()


def test_evaluator_deterministic_ordering():
    """Test that attempt plans are deterministic (same input -> same output)."""
    surface = create_fake_surface()

    goal = "Decompose a goal into a WorkGraph"

    # Generate plan twice
    evaluator1 = GoalEvaluator(surface, verbose=False)
    plan1 = evaluator1.generate_attempt_plan(goal)

    evaluator2 = GoalEvaluator(surface, verbose=False)
    plan2 = evaluator2.generate_attempt_plan(goal)

    # Should generate identical attempts
    assert plan1.attempts == plan2.attempts
    assert plan1.reasoning == plan2.reasoning


def test_evaluator_uses_only_discovered_tokens():
    """Test that evaluator only uses commands discovered from help."""
    surface = create_fake_surface()
    evaluator = GoalEvaluator(surface, verbose=False)

    goal = "Create a plan and decompose it"
    plan = evaluator.generate_attempt_plan(goal)

    # Every attempt should be a command path that exists in surface
    for attempt in plan.attempts:
        cmd_tuple = tuple(attempt)
        assert cmd_tuple in surface, f"Attempt {attempt} not in discovered surface"


def test_evaluator_bounded_output():
    """Test that evaluator respects output bounds."""
    surface = create_fake_surface()
    evaluator = GoalEvaluator(surface, verbose=False)

    goal = "Do everything"
    plan = evaluator.generate_attempt_plan(goal)

    # Should not generate unbounded attempts (max 10 in code)
    assert len(plan.attempts) <= 10


def test_evaluator_scoring_weights():
    """Test that scoring weights are applied correctly."""
    surface = {}

    # Command with keyword in path (high weight)
    surface[('maestro', 'runbook')] = HelpNode(
        command_path=['maestro', 'runbook'],
        help_text='General help text',
        help_hash='hash1',
        discovered_subcommands=[]
    )

    # Command with keyword in subcommands (medium weight)
    surface[('maestro', 'plan')] = HelpNode(
        command_path=['maestro', 'plan'],
        help_text='General help text',
        help_hash='hash2',
        discovered_subcommands=['runbook-like']
    )

    # Command with keyword only in help text (low weight)
    surface[('maestro', 'repo')] = HelpNode(
        command_path=['maestro', 'repo'],
        help_text='This command is like a runbook',
        help_hash='hash3',
        discovered_subcommands=[]
    )

    evaluator = GoalEvaluator(surface, verbose=False)
    keywords = {'runbook'}

    score_path = evaluator._score_command(('maestro', 'runbook'), keywords)
    score_subcmd = evaluator._score_command(('maestro', 'plan'), keywords)
    score_help = evaluator._score_command(('maestro', 'repo'), keywords)

    # Path match should score highest
    assert score_path > score_subcmd
    assert score_path > score_help


def test_evaluator_empty_surface():
    """Test evaluator behavior with empty surface."""
    surface = {}
    evaluator = GoalEvaluator(surface, verbose=False)

    goal = "Do something"
    plan = evaluator.generate_attempt_plan(goal)

    # Should handle gracefully with no attempts
    assert len(plan.attempts) == 0
    assert plan.goal == goal


def test_evaluator_no_matching_keywords():
    """Test evaluator when goal has no matching keywords in surface."""
    surface = create_fake_surface()
    evaluator = GoalEvaluator(surface, verbose=False)

    # Goal with keywords not in surface
    goal = "Quantum entanglement blockchain synergy"
    plan = evaluator.generate_attempt_plan(goal)

    # May generate attempts with low scores, or none
    # Just verify it doesn't crash and produces valid structure
    assert isinstance(plan.attempts, list)
    assert isinstance(plan.reasoning, str)

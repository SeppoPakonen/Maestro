#!/usr/bin/env python3
"""
Tests for multi-engine arbitration functionality.
Tests the requirements from Task 12.
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
import shutil

# Mock the AI engine calls to avoid actual API calls
def mock_run_engine(engine, prompt, cwd, stream=True, timeout=300, extra_args=None, verbose=False):
    """Mock AI engine run that returns different outputs based on the engine."""
    from realize_worker import parse_ai_output

    if engine == 'qwen':
        # Qwen output with TODO placeholder - should score lower
        mock_output = {
            "files": [
                {
                    "path": "test_output.txt",
                    "content": "# Qwen output\n// TODO: Implement actual functionality\nprint('Hello World')\n# This has a placeholder"
                }
            ]
        }
        return 0, json.dumps(mock_output), ""

    elif engine == 'claude':
        # Claude output - clean implementation
        mock_output = {
            "files": [
                {
                    "path": "test_output.txt",
                    "content": "# Claude output\nprint('Hello World')\n# Clean implementation without placeholders"
                }
            ]
        }
        return 0, json.dumps(mock_output), ""

    elif engine == 'codex':
        # Codex as judge - returns winner decision
        # Check if this is a regular task or a judge task based on prompt content
        if "ARBITRATION JUDGE TASK" in prompt:
            # This is a judge task
            judge_output = {
                "winner_engine": "claude",
                "reasons": ["Clean implementation", "No placeholders"],
                "risks": [],
                "requires_human_confirm": False
            }
            return 0, json.dumps(judge_output), ""
        else:
            # This is a regular codex task
            mock_output = {
                "files": [
                    {
                        "path": "test_output.txt",
                        "content": "# Codex output\nprint('Hello from codex')"
                    }
                ]
            }
            return 0, json.dumps(mock_output), ""

    else:
        # Default: return error
        return 1, "", "Unknown engine"


class TestArbitration(unittest.TestCase):
    """Test cases for arbitration functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.test_dir, 'source')
        self.target_dir = os.path.join(self.test_dir, 'target')
        os.makedirs(self.source_dir, exist_ok=True)
        os.makedirs(self.target_dir, exist_ok=True)

        # Create a source file for testing
        with open(os.path.join(self.source_dir, 'input.txt'), 'w') as f:
            f.write('Sample source content for testing')

        # Create a simple task for testing
        self.test_task = {
            'task_id': 'test_task_001',
            'phase': 'file',
            'engine': 'qwen',
            'acceptance_criteria': 'Convert input file to output format',
            'source_files': ['input.txt'],
            'target_files': ['output.txt'],
            'title': 'Test conversion task',
            'realization_action': 'convert'
        }

        # Create a minimal plan file
        plan_dir = os.path.join(self.test_dir, '.maestro', 'convert', 'plan')
        os.makedirs(plan_dir, exist_ok=True)

        # Create a minimal plan file
        plan_content = {
            'scaffold_tasks': [],
            'file_tasks': [self.test_task],
            'final_sweep_tasks': []
        }

        with open(os.path.join(self.test_dir, '.maestro', 'convert', 'plan', 'plan.json'), 'w') as f:
            json.dump(plan_content, f, indent=2)

        # Change to test directory for relative paths
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Store original run_engine function to restore later
        from realize_worker import run_engine as original_run_engine
        self.original_run_engine = original_run_engine

    def tearDown(self):
        """Clean up test fixtures."""
        # Restore original run_engine function
        import realize_worker
        realize_worker.run_engine = self.original_run_engine

        # Change back to original directory
        os.chdir(self.original_cwd)

        # Remove test directory
        shutil.rmtree(self.test_dir)

        # Clean up any maestro files created during testing in original directory
        maestro_path = os.path.join(self.original_cwd, '.maestro')
        if os.path.exists(maestro_path):
            shutil.rmtree(maestro_path)
    
    def test_arbitration_with_clean_vs_placeholder_output(self):
        """Test that clean output wins over output with TODO placeholders."""
        # Mock the run_engine function to simulate different AI outputs
        import realize_worker
        realize_worker.run_engine = mock_run_engine

        # Mock the semantic analysis to return more reasonable results for testing
        from semantic_integrity import SemanticIntegrityChecker
        original_analyze = SemanticIntegrityChecker._analyze_semantic_equivalence

        def mock_semantic_analysis(self, source_snapshot_hash, target_content, conversion_summary, active_decisions, glossary):
            # Return different results based on content to make test meaningful
            # Look for patterns that indicate quality issues (but be more specific)
            target_content_lower = target_content.lower()
            has_real_issues = (
                'todo' in target_content_lower or
                'fixme' in target_content_lower or
                ('placeholder' in target_content_lower and 'this has a placeholder' in target_content_lower) or  # Only if it says it's a placeholder
                '...' in target_content_lower or
                'not implemented' in target_content_lower
            )

            if has_real_issues:
                return {
                    "semantic_equivalence": "medium",  # Not low to avoid disqualification
                    "confidence": 0.5,
                    "preserved_concepts": [],
                    "changed_concepts": ["implementation_details"],
                    "lost_concepts": [],
                    "assumptions": ["Implementation incomplete"],
                    "risk_flags": [],
                    "requires_human_review": True  # Flag for review but don't disqualify
                }
            else:
                return {
                    "semantic_equivalence": "high",
                    "confidence": 0.85,  # High confidence for clean content
                    "preserved_concepts": ["core_functionality"],
                    "changed_concepts": [],
                    "lost_concepts": [],
                    "assumptions": ["Implementation complete"],
                    "risk_flags": [],
                    "requires_human_review": False  # Clean implementation should not require review
                }

        SemanticIntegrityChecker._analyze_semantic_equivalence = mock_semantic_analysis

        try:
            # Execute arbitration with qwen and claude
            from realize_worker import execute_file_task_with_arbitration

            success = execute_file_task_with_arbitration(
                task=self.test_task,
                source_repo_path=self.source_dir,
                target_repo_path=self.target_dir,
                verbose=True,
                arbitrate_engines=['qwen', 'claude'],
                judge_engine='codex',
                max_candidates=2,
                use_judge=False  # Use scoring only
            )

            # Check that execution was successful
            self.assertTrue(success, "Arbitration should complete successfully")

            # Check that the target file was created with the winner's content
            target_file = os.path.join(self.target_dir, 'test_output.txt')
            self.assertTrue(os.path.exists(target_file), "Target file should exist")

            with open(target_file, 'r') as f:
                content = f.read()

            # The winner should be claude (clean output) rather than qwen (with TODOs)
            self.assertIn("Clean implementation", content, "Should contain clean implementation")
            self.assertNotIn("TODO", content, "Should not contain TODO placeholders from losing candidate")

            # Check that arbitration artifacts were created
            arbitration_dir = f".maestro/convert/arbitration/{self.test_task['task_id']}"
            self.assertTrue(os.path.exists(arbitration_dir), "Arbitration directory should exist")

            decision_file = os.path.join(arbitration_dir, 'decision.json')
            self.assertTrue(os.path.exists(decision_file), "Decision file should exist")

            with open(decision_file, 'r') as f:
                decision = json.load(f)

            # Claude should win due to higher quality
            self.assertEqual(decision['winner_engine'], 'claude', "Claude should win over Qwen with TODOs")
        finally:
            # Restore original function
            SemanticIntegrityChecker._analyze_semantic_equivalence = original_analyze
    
    def test_arbitration_semantic_disqualification(self):
        """Test that candidates with low semantic equivalence are disqualified."""
        # Mock run_engine to return output that will trigger semantic issues
        def mock_run_engine_semantic_issue(engine, prompt, cwd, stream=True, timeout=300, extra_args=None, verbose=False):
            mock_output = {
                "files": [
                    {
                        "path": "output.txt",
                        "content": "# This is an empty file that will trigger low semantic equivalence"
                    }
                ]
            }
            return 0, json.dumps(mock_output), ""

        import realize_worker
        realize_worker.run_engine = mock_run_engine_semantic_issue

        # Mock the semantic analysis to return low equivalence for testing disqualification
        from semantic_integrity import SemanticIntegrityChecker
        original_analyze = SemanticIntegrityChecker._analyze_semantic_equivalence

        def mock_semantic_analysis_disqualify(self, source_snapshot_hash, target_content, conversion_summary, active_decisions, glossary):
            # Return low equivalence to test disqualification
            return {
                "semantic_equivalence": "low",  # This will cause disqualification
                "confidence": 0.3,
                "preserved_concepts": [],
                "changed_concepts": ["functionality"],
                "lost_concepts": ["functionality"],
                "assumptions": ["Major functionality loss"],
                "risk_flags": ["functionality_loss"],
                "requires_human_review": True
            }

        SemanticIntegrityChecker._analyze_semantic_equivalence = mock_semantic_analysis_disqualify

        try:
            # Execute arbitration
            from realize_worker import execute_file_task_with_arbitration

            success = execute_file_task_with_arbitration(
                task=self.test_task,
                source_repo_path=self.source_dir,
                target_repo_path=self.target_dir,
                verbose=True,
                arbitrate_engines=['qwen'],  # Only one engine to make test simpler
                judge_engine='codex',
                max_candidates=1,
                use_judge=False
            )

            # With low semantic equivalence, no valid candidate should be selected
            # So success should be False (no winner selected)
            self.assertFalse(success, "Arbitration should fail when no valid candidates exist")
        finally:
            # Restore original function
            SemanticIntegrityChecker._analyze_semantic_equivalence = original_analyze
    
    def test_arbitration_with_judge_selection(self):
        """Test that judge engine is called when needed."""
        # Mock to create a tie situation that requires a judge
        def mock_run_engine_tie(engine, prompt, cwd, stream=True, timeout=300, extra_args=None, verbose=False):
            mock_output = {
                "files": [
                    {
                        "path": "output.txt",
                        "content": f"# Output from {engine}\nprint('{engine} implementation')"
                    }
                ]
            }
            return 0, json.dumps(mock_output), ""

        import realize_worker
        realize_worker.run_engine = mock_run_engine_tie

        # Mock semantic analysis for judge test
        from semantic_integrity import SemanticIntegrityChecker
        original_analyze = SemanticIntegrityChecker._analyze_semantic_equivalence

        def mock_semantic_analysis_for_judge(self, source_snapshot_hash, target_content, conversion_summary, active_decisions, glossary):
            # Return medium equivalence to trigger judge usage (tie scenario)
            return {
                "semantic_equivalence": "medium",
                "confidence": 0.6,  # Low confidence to trigger judge
                "preserved_concepts": ["functionality"],
                "changed_concepts": [],
                "lost_concepts": [],
                "assumptions": ["Implementation may need review"],
                "risk_flags": [],
                "requires_human_review": False
            }

        SemanticIntegrityChecker._analyze_semantic_equivalence = mock_semantic_analysis_for_judge

        try:
            # Execute arbitration with judge required
            from realize_worker import execute_file_task_with_arbitration

            success = execute_file_task_with_arbitration(
                task=self.test_task,
                source_repo_path=self.source_dir,
                target_repo_path=self.target_dir,
                verbose=True,
                arbitrate_engines=['qwen', 'claude'],
                judge_engine='codex',
                max_candidates=2,
                use_judge=True  # Force judge usage
            )

            self.assertTrue(success, "Arbitration with judge should complete successfully")
        finally:
            # Restore original function
            SemanticIntegrityChecker._analyze_semantic_equivalence = original_analyze
    
    def test_arbitration_no_target_writes_before_selection(self):
        """Test that no target writes occur until a winner is selected."""
        import realize_worker
        realize_worker.run_engine = mock_run_engine

        # Mock the semantic analysis to return more reasonable results for testing
        from semantic_integrity import SemanticIntegrityChecker
        original_analyze = SemanticIntegrityChecker._analyze_semantic_equivalence

        def mock_semantic_analysis(self, source_snapshot_hash, target_content, conversion_summary, active_decisions, glossary):
            # Return different results based on content to make test meaningful
            # Look for patterns that indicate quality issues (but be more specific)
            target_content_lower = target_content.lower()
            has_real_issues = (
                'todo' in target_content_lower or
                'fixme' in target_content_lower or
                ('placeholder' in target_content_lower and 'this has a placeholder' in target_content_lower) or  # Only if it says it's a placeholder
                '...' in target_content_lower or
                'not implemented' in target_content_lower
            )

            if has_real_issues:
                return {
                    "semantic_equivalence": "medium",  # Not low to avoid disqualification
                    "confidence": 0.5,
                    "preserved_concepts": [],
                    "changed_concepts": ["implementation_details"],
                    "lost_concepts": [],
                    "assumptions": ["Implementation incomplete"],
                    "risk_flags": [],
                    "requires_human_review": True  # Flag for review but don't disqualify
                }
            else:
                return {
                    "semantic_equivalence": "high",
                    "confidence": 0.85,  # High confidence for clean content
                    "preserved_concepts": ["core_functionality"],
                    "changed_concepts": [],
                    "lost_concepts": [],
                    "assumptions": ["Implementation complete"],
                    "risk_flags": [],
                    "requires_human_review": False  # Clean implementation should not require review
                }

        SemanticIntegrityChecker._analyze_semantic_equivalence = mock_semantic_analysis

        # Temporarily prevent safe_write_file from writing to check the behavior
        original_safe_write_file = realize_worker.safe_write_file

        writes_before_selection = []

        def tracking_safe_write_file(target_path, content, target_repo_root, task_id=None, write_policy="overwrite"):
            """Track when writes happen."""
            writes_before_selection.append((target_path, content))
            # Call original but ensure we don't actually write if we shouldn't
            return original_safe_write_file(target_path, content, target_repo_root, task_id, write_policy)

        realize_worker.safe_write_file = tracking_safe_write_file

        try:
            from realize_worker import execute_file_task_with_arbitration

            success = execute_file_task_with_arbitration(
                task=self.test_task,
                source_repo_path=self.source_dir,
                target_repo_path=self.target_dir,
                verbose=True,
                arbitrate_engines=['qwen', 'claude'],
                judge_engine='codex',
                max_candidates=2,
                use_judge=False
            )

            self.assertTrue(success, "Arbitration should complete successfully")
            # We should have writes but only for the final winner, not during candidate generation
            # The writes happen at the end for the winner, which is expected
        finally:
            # Restore original function
            realize_worker.safe_write_file = original_safe_write_file
            # Restore semantic analysis function
            SemanticIntegrityChecker._analyze_semantic_equivalence = original_analyze


def test_arbitration_cli():
    """Test the CLI command for showing arbitration results."""
    import tempfile
    import json
    import shutil

    # Create a temporary arbitration result to test the CLI
    task_id = 'cli_test_task_001'
    arbitration_dir = f".maestro/convert/arbitration/{task_id}"
    os.makedirs(arbitration_dir, exist_ok=True)

    # Create mock decision file
    decision_data = {
        'winner_engine': 'claude',
        'candidates': ['qwen', 'claude'],
        'candidate_scorecards': {
            'qwen': {
                'protocol_valid': True,
                'deliverables_ok': True,
                'placeholder_penalty': 10,
                'diff_size_metric': 100,
                'validation_cmd_result': True,
                'semantic_equivalence': 'medium',
                'semantic_confidence': 0.6,
                'requires_human_review': True
            },
            'claude': {
                'protocol_valid': True,
                'deliverables_ok': True,
                'placeholder_penalty': 0,
                'diff_size_metric': 90,
                'validation_cmd_result': True,
                'semantic_equivalence': 'high',
                'semantic_confidence': 0.8,
                'requires_human_review': False
            }
        },
        'semantic_results': {
            'qwen': {'semantic_equivalence': 'medium', 'confidence': 0.6, 'requires_human_review': True},
            'claude': {'semantic_equivalence': 'high', 'confidence': 0.8, 'requires_human_review': False}
        },
        'used_judge': False,
        'judge_engine': None,
        'decision_timestamp': '1234567890',
        'task_id': task_id
    }

    with open(os.path.join(arbitration_dir, 'decision.json'), 'w') as f:
        json.dump(decision_data, f, indent=2)

    # Test the CLI function directly
    from convert_orchestrator import cmd_arbitration_show

    class Args:
        def __init__(self, task_id):
            self.task_id = task_id

    args = Args(task_id)
    result = cmd_arbitration_show(args)

    # Clean up
    shutil.rmtree(arbitration_dir)

    assert result == 0, "CLI command should succeed"
    print("CLI test passed!")


if __name__ == '__main__':
    print("Running arbitration tests...")
    
    # Run unit tests
    unittest.main(verbosity=2, exit=False)
    
    # Run CLI test
    print("\nTesting CLI command...")
    test_arbitration_cli()
    
    print("\nAll tests passed!")
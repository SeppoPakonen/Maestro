"""
Long-Run Stability Tests for Conversion Memory System

Tests that the conversion memory system remains stable across many tasks,
with consistent conventions, decision enforcement, and context limits.
"""

import os
import tempfile
import shutil
from pathlib import Path
from conversion_memory import ConversionMemory, TaskSummary
from context_builder import ContextBuilder, ContextSizeExceededException


def test_memory_initialization():
    """Test that memory store initializes correctly."""
    print("Testing memory initialization...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        memory_path = os.path.join(temp_dir, ".maestro", "convert", "memory")
        memory = ConversionMemory(base_path=memory_path)
        
        # Check that all memory files exist
        assert os.path.exists(os.path.join(memory_path, "decisions.json"))
        assert os.path.exists(os.path.join(memory_path, "conventions.json"))
        assert os.path.exists(os.path.join(memory_path, "open_issues.json"))
        assert os.path.exists(os.path.join(memory_path, "glossary.json"))
        assert os.path.exists(os.path.join(memory_path, "summary.log"))
        
        # Check that they start empty
        assert len(memory.load_decisions()) == 0
        assert len(memory.load_conventions()) == 0
        assert len(memory.load_open_issues()) == 0
        assert len(memory.load_glossary()) == 0
        assert len(memory.load_summary_log()) == 0
        
        print("  ✓ Memory initialization test passed")


def test_decision_storage_and_retrieval():
    """Test that decisions are stored and retrieved correctly."""
    print("Testing decision storage and retrieval...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        memory_path = os.path.join(temp_dir, ".maestro", "convert", "memory")
        memory = ConversionMemory(base_path=memory_path)
        
        # Add a decision
        decision_id = memory.add_decision(
            category="language_target",
            description="Target language for conversion",
            value="python",
            justification="Project requirements specify Python as target"
        )
        
        # Retrieve all decisions
        decisions = memory.load_decisions()
        assert len(decisions) == 1
        assert decisions[0]['decision_id'] == decision_id
        assert decisions[0]['category'] == "language_target"
        assert decisions[0]['value'] == "python"
        
        # Retrieve specific decision
        retrieved = memory.get_decision_by_id(decision_id)
        assert retrieved is not None
        assert retrieved['value'] == "python"
        
        print("  ✓ Decision storage and retrieval test passed")


def test_convention_storage_and_retrieval():
    """Test that conventions are stored and retrieved correctly."""
    print("Testing convention storage and retrieval...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        memory_path = os.path.join(temp_dir, ".maestro", "convert", "memory")
        memory = ConversionMemory(base_path=memory_path)
        
        # Add a convention
        convention_id = memory.add_convention(
            category="naming",
            rule="Use snake_case for function names",
            applies_to="all functions"
        )
        
        # Retrieve all conventions
        conventions = memory.load_conventions()
        assert len(conventions) == 1
        assert conventions[0]['convention_id'] == convention_id
        assert conventions[0]['category'] == "naming"
        assert conventions[0]['rule'] == "Use snake_case for function names"
        
        print("  ✓ Convention storage and retrieval test passed")


def test_glossary_storage_and_retrieval():
    """Test that glossary entries are stored and retrieved correctly."""
    print("Testing glossary storage and retrieval...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        memory_path = os.path.join(temp_dir, ".maestro", "convert", "memory")
        memory = ConversionMemory(base_path=memory_path)
        
        # Add a glossary entry
        term_id = memory.add_glossary_entry(
            source_term="class",
            target_term="struct",
            definition="A blueprint for creating objects",
            usage_context="Object-oriented programming"
        )
        
        # Retrieve all glossary entries
        glossary = memory.load_glossary()
        assert len(glossary) == 1
        assert glossary[0]['term_id'] == term_id
        assert glossary[0]['source_term'] == "class"
        assert glossary[0]['target_term'] == "struct"
        
        print("  ✓ Glossary storage and retrieval test passed")


def test_summary_storage():
    """Test that summaries are stored correctly."""
    print("Testing summary storage...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        memory_path = os.path.join(temp_dir, ".maestro", "convert", "memory")
        summaries_path = os.path.join(temp_dir, ".maestro", "convert", "summaries")
        memory = ConversionMemory(base_path=memory_path)
        
        # Create a task summary
        summary = TaskSummary(
            task_id="test_task_001",
            source_files=["src/main.js"],
            target_files=["target/main.py"]
        )
        summary.add_semantic_decision("Converted JavaScript to Python syntax")
        summary.add_warning("Some functions may need manual review")
        
        # Save to file
        summary_path = summary.save_to_file(base_path=summaries_path)
        assert os.path.exists(summary_path)
        
        # Add to memory log
        entry_id = memory.add_summary_entry("test_task_001", "Converted JavaScript to Python")
        summary_log = memory.load_summary_log()
        assert len(summary_log) == 1
        assert summary_log[0]['task_id'] == "test_task_001"
        assert summary_log[0]['entry_id'] == entry_id
        
        print("  ✓ Summary storage test passed")


def test_decision_conflict_detection():
    """Test that decision conflicts are detected."""
    print("Testing decision conflict detection...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        memory_path = os.path.join(temp_dir, ".maestro", "convert", "memory")
        memory = ConversionMemory(base_path=memory_path)
        
        # Add initial decision
        memory.add_decision(
            category="language_target",
            description="Target language for conversion",
            value="python",
            justification="Project requirements specify Python as target"
        )
        
        # Check for conflict with different value
        conflicting_decision = memory.check_decision_conflict("language_target", "java")
        assert conflicting_decision is not None
        assert conflicting_decision['value'] == "python"
        
        # Check for no conflict with same value
        non_conflicting_decision = memory.check_decision_conflict("language_target", "python")
        assert non_conflicting_decision is None
        
        print("  ✓ Decision conflict detection test passed")


def test_long_run_stability():
    """Test stability across many tasks with consistent conventions."""
    print("Testing long-run stability across multiple tasks...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        memory_path = os.path.join(temp_dir, ".maestro", "convert", "memory")
        memory = ConversionMemory(base_path=memory_path)
        
        # Establish some base decisions and conventions
        memory.add_decision(
            category="language_target",
            description="Target language for conversion",
            value="python",
            justification="Project requirements specify Python as target"
        )
        
        memory.add_convention(
            category="naming",
            rule="Use snake_case for function names",
            applies_to="all functions"
        )
        
        memory.add_glossary_entry(
            source_term="function",
            target_term="def",
            definition="A reusable block of code",
            usage_context="Function definitions"
        )
        
        # Simulate running 25 tasks
        for i in range(25):
            task_id = f"task_{i:03d}"
            
            # Create task object
            task = {
                "task_id": task_id,
                "source_files": [f"src/file_{i}.js"],
                "target_files": [f"target/file_{i}.py"],  # Consistent with language_target decision
                "engine": "codex",  # Consistent engine
            }
            
            # Check compliance - should pass since we're following decisions
            violations = memory.check_task_compliance(task)
            assert len(violations) == 0, f"Task {task_id} has violations: {violations}"
            
            # Add a summary entry
            memory.add_summary_entry(task_id, f"Processed file_{i}")
        
        # Verify memory state after all tasks
        decisions = memory.load_decisions()
        conventions = memory.load_conventions()
        glossary = memory.load_glossary()
        summary_log = memory.load_summary_log()
        
        assert len(decisions) == 1
        assert len(conventions) == 1
        assert len(glossary) == 1
        assert len(summary_log) == 25  # All summaries should be preserved
        
        print("  ✓ Long-run stability test passed")


def test_context_compression_limits():
    """Test that context compression enforces size limits."""
    print("Testing context compression limits...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        memory_path = os.path.join(temp_dir, ".maestro", "convert", "memory")
        memory = ConversionMemory(base_path=memory_path)
        
        # Add many decisions to potentially exceed limits
        for i in range(50):
            memory.add_decision(
                category="test_category",
                description=f"Test decision {i}",
                value=f"value_{i}" * 100,  # Create large values
                justification=f"Justification for test decision {i}" * 50
            )
        
        # Create a context builder with small limits to force exception
        context_builder = ContextBuilder(memory, planner_context_limit=1000, worker_context_limit=500)
        
        # Try to build context - should fail due to size limits
        try:
            context_builder.build_context_for_planner()
            assert False, "Expected ContextSizeExceededException was not raised"
        except ContextSizeExceededException:
            pass  # Expected
        
        try:
            context_builder.build_context_for_worker("task_001")
            assert False, "Expected ContextSizeExceededException was not raised"
        except ContextSizeExceededException:
            pass  # Expected
        
        print("  ✓ Context compression limits test passed")


def test_memory_usage_info():
    """Test that memory usage info is correctly calculated."""
    print("Testing memory usage information...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        memory_path = os.path.join(temp_dir, ".maestro", "convert", "memory")
        memory = ConversionMemory(base_path=memory_path)
        
        # Add some data
        memory.add_decision("language_target", "Target language", "python", "Project requirement")
        memory.add_convention("naming", "Use snake_case", "functions")
        memory.add_glossary_entry("var", "variable", "declaration", "variables")
        
        # Get memory usage
        usage = memory.get_memory_usage_info()
        
        assert usage['decisions_count'] == 1
        assert usage['conventions_count'] == 1
        assert usage['glossary_count'] == 1
        assert usage['open_issues_count'] == 0
        assert usage['summary_log_count'] == 0
        assert usage['decisions_size'] > 0
        assert usage['conventions_size'] > 0
        assert usage['glossary_size'] > 0
        
        print("  ✓ Memory usage info test passed")


def run_all_tests():
    """Run all tests."""
    print("Running conversion memory stability tests...\n")
    
    test_memory_initialization()
    test_decision_storage_and_retrieval()
    test_convention_storage_and_retrieval()
    test_glossary_storage_and_retrieval()
    test_summary_storage()
    test_decision_conflict_detection()
    test_long_run_stability()
    test_context_compression_limits()
    test_memory_usage_info()
    
    print("\n✓ All tests passed! Conversion memory system is stable for long runs.")


if __name__ == "__main__":
    run_all_tests()
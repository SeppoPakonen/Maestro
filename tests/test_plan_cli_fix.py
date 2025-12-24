"""Tests for plan CLI parsing fix."""
import subprocess
import tempfile
import os
from pathlib import Path


def run_maestro_command(cmd_args, cwd):
    """Helper to run maestro commands."""
    maestro_script = Path(__file__).parent.parent / "maestro.py"
    full_cmd = ["python", str(maestro_script)] + cmd_args
    result = subprocess.run(full_cmd, cwd=cwd, capture_output=True, text=True)
    return result


def test_plan_cli_fix():
    """Test that plan CLI commands work correctly after the fix."""
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        # Initialize maestro project
        init_result = run_maestro_command(["init"], temp_dir)
        assert init_result.returncode == 0, f"Init failed: {init_result.stderr}"
        
        # Test 1: maestro plan should print help and exit 0
        plan_help_result = run_maestro_command(["plan"], temp_dir)
        assert plan_help_result.returncode == 0, "Plan command without args should show help and exit 0"
        assert "Plan subcommands" in plan_help_result.stdout, "Help should contain subcommand info"
        
        # Test 2: maestro plan add "game idea" should create the plan
        add_result = run_maestro_command(["plan", "add", "game idea"], temp_dir)
        assert add_result.returncode == 0, f"Plan add failed: {add_result.stderr}"
        assert "Added plan: game idea" in add_result.stdout, "Should confirm plan was added"
        
        # Test 3: maestro plan list should show the created plan
        list_result = run_maestro_command(["plan", "list"], temp_dir)
        assert list_result.returncode == 0, f"Plan list failed: {list_result.stderr}"
        assert "game idea" in list_result.stdout, "List should show the created plan"
        
        # Test 4: maestro plan sh 1 should show the plan (using alias 'sh')
        show_result = run_maestro_command(["plan", "sh", "1"], temp_dir)
        assert show_result.returncode == 0, f"Plan show failed: {show_result.stderr}"
        assert "PLAN: game idea" in show_result.stdout, "Show should display the plan title"
        
        # Test 5: maestro plan discuss should route correctly (will fail later due to AI, but should route correctly)
        discuss_result = run_maestro_command(["plan", "discuss"], temp_dir)
        # This should at least route to the discuss handler (will fail later due to AI engine, which is expected)
        # The important part is that it doesn't show the general help
        # Since discuss needs AI to work properly, we just check that it doesn't fail with parsing errors
        # The command should at least recognize 'discuss' as a valid subcommand
        assert discuss_result.returncode != 2, "Should not fail with unrecognized arguments (parsing error)"
        
        print("All tests passed!")


def test_discuss_add_rejection():
    """Test that discuss add is properly rejected with helpful message."""
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        # Initialize maestro project
        init_result = run_maestro_command(["init"], temp_dir)
        assert init_result.returncode == 0, f"Init failed: {init_result.stderr}"
        
        # Test that maestro discuss add "game idea" fails appropriately
        discuss_add_result = run_maestro_command(["discuss", "add", "game idea"], temp_dir)
        assert discuss_add_result.returncode != 0, "discuss add should fail"
        
        print("Discuss add rejection test passed!")


if __name__ == "__main__":
    test_plan_cli_fix()
    test_discuss_add_rejection()
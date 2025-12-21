"""
Render loop test for MC2 TUI
Tests that the curses render loop doesn't crash
"""
import subprocess
import sys
import time


def test_render_loop():
    """Test that the MC2 render loop runs without crashing"""
    try:
        # Run the MC2 app for a short period in smoke mode
        result = subprocess.run([
            sys.executable, "-c",
            """
import sys
sys.path.insert(0, '.')
from maestro.tui_mc2.app import MC2App

# Create app in smoke mode to prevent hanging
app = MC2App(smoke_mode=True, smoke_seconds=0.2)
try:
    app.run()
    print("Render loop completed successfully")
except Exception as e:
    print(f"Render loop failed with error: {e}")
    sys.exit(1)
            """
        ], capture_output=True, text=True, timeout=5)
        
        # Check that it exited successfully
        assert result.returncode == 0, f"Render loop failed with return code {result.returncode}: {result.stderr}"
        
        # Check that normal completion was indicated
        output = result.stdout + result.stderr
        assert "Render loop completed successfully" in output or "MAESTRO_TUI_SMOKE_OK" in output, f"Expected success message not found in output: {output}"
        
        print("✓ Render loop test passed")
        return True
        
    except subprocess.TimeoutExpired:
        print("✗ Render loop test timed out - may indicate rendering issues")
        return False
    except Exception as e:
        print(f"✗ Render loop test failed with error: {e}")
        return False


def test_render_with_session_data():
    """Test that the render loop works with real session data"""
    try:
        # Create a test environment with minimal session data
        result = subprocess.run([
            sys.executable, "-c",
            """
import sys
sys.path.insert(0, '.')
from maestro.tui_mc2.app import MC2App

# Create app and ensure it can handle session data in panes
app = MC2App(smoke_mode=True, smoke_seconds=0.3)

# Manually test that the session pane can render
from maestro.tui_mc2.panes.sessions import SessionsPane
from maestro.tui_mc2.app import AppContext

context = AppContext(smoke_mode=True)
left_pane = SessionsPane(position="left", context=context)
right_pane = SessionsPane(position="right", context=context)

# Test that panes can be created and refreshed without errors
try:
    left_pane.refresh_data()
    right_pane.refresh_data()
    print("Session panes created and refreshed successfully")
except Exception as e:
    print(f"Session pane error: {e}")
    sys.exit(1)

# Now test the full app
try:
    app.run()
    print("Full app render loop completed")
except Exception as e:
    print(f"Full app render failed: {e}")
    sys.exit(1)
            """
        ], capture_output=True, text=True, timeout=5)
        
        # Check that it exited successfully
        assert result.returncode == 0, f"Render loop with data failed with return code {result.returncode}: {result.stderr}"
        
        # Check that normal completion was indicated
        output = result.stdout + result.stderr
        assert "Session panes created and refreshed successfully" in output or "MAESTRO_TUI_SMOKE_OK" in output, f"Expected success message not found in output: {output}"
        
        print("✓ Render loop with session data test passed")
        return True
        
    except subprocess.TimeoutExpired:
        print("✗ Render loop with data test timed out")
        return False
    except Exception as e:
        print(f"✗ Render loop with data test failed with error: {e}")
        return False


if __name__ == "__main__":
    print("Running MC2 render loop tests...")
    
    success = True
    success &= test_render_loop()
    success &= test_render_with_session_data()
    
    if success:
        print("\n✓ All MC2 render loop tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some MC2 render loop tests failed!")
        sys.exit(1)
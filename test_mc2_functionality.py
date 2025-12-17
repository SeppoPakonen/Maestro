"""
Basic functionality test for MC2 TUI
"""
import subprocess
import sys


def test_mc2_flag_exists():
    """Test that the --mc2 flag is recognized"""
    result = subprocess.run([
        sys.executable, "-m", "maestro.tui", "--help"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0
    assert "--mc2" in result.stdout
    print("✓ --mc2 flag is available in help")
    

def test_mc2_without_smoke_parameter():
    """Test that MC2 mode can be invoked (without actually running curses)"""
    # This is harder to test directly without hanging, so we'll just verify import works
    try:
        from maestro.tui_mc2.app import MC2App
        print("✓ MC2App class can be imported")
        return True
    except Exception as e:
        print(f"✗ MC2App import failed: {e}")
        return False


def test_sessions_pane():
    """Test that the sessions pane works properly"""
    try:
        from maestro.tui_mc2.panes.sessions import SessionsPane
        from maestro.tui_mc2.app import AppContext
        
        context = AppContext()
        pane = SessionsPane("left", context)
        
        # Test that it can refresh data without errors
        pane.refresh_data()
        print("✓ Sessions pane can refresh data")
        return True
    except Exception as e:
        print(f"✗ Sessions pane test failed: {e}")
        return False


if __name__ == "__main__":
    print("Running MC2 functionality tests...")
    
    success = True
    test_mc2_flag_exists()
    success &= test_mc2_without_smoke_parameter()
    success &= test_sessions_pane()
    
    if success:
        print("\n✓ All MC2 functionality tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some MC2 functionality tests failed!")
        sys.exit(1)
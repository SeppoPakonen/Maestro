"""
Integration test for screen lifecycle and navigation to ensure no "Error loading screen content" appears.
"""
import asyncio
import tempfile
import os
from textual.app import App
from maestro.tui.app import MaestroTUI


async def test_screen_navigation_integration():
    """
    Integration test that navigates through all screens using the actual app.
    This test runs the application briefly to ensure screen switching works properly.
    """
    success_file = tempfile.mktemp()
    
    # Create the app in smoke mode
    app = MaestroTUI(
        smoke_mode=True, 
        smoke_seconds=2.0,  # Run for 2 seconds to allow for screen switches
        smoke_out=success_file
    )
    
    # Run the app - this will trigger the smoke test
    try:
        await app.run_async(headless=True)
    except Exception as e:
        print(f"App run failed: {e}")
        raise
    
    # Check that the success marker was written
    if os.path.exists(success_file):
        with open(success_file, 'r') as f:
            content = f.read().strip()
        if content == "MAESTRO_TUI_SMOKE_OK":
            print("Smoke test completed successfully!")
        else:
            raise AssertionError(f"Unexpected content in success file: {content}")
    else:
        raise AssertionError("Success file was not created")
    
    print("Integration smoke test passed!")


def test_manual_screen_switching():
    """
    Test manual screen switching to ensure no errors occur.
    """
    from maestro.tui.screens.home import HomeScreen
    from maestro.tui.screens.sessions import SessionsScreen
    from maestro.tui.screens.tasks import TasksScreen
    from maestro.tui.screens.build import BuildScreen
    
    # Create an app instance
    app = MaestroTUI(smoke_mode=True, smoke_seconds=0.1, smoke_out="/tmp/test_smoke")
    
    # Check that screens can be created and composed without error
    screens = [
        HomeScreen(),
        SessionsScreen(), 
        TasksScreen(),
        BuildScreen()
    ]
    
    for i, screen in enumerate(screens):
        try:
            # Test that compose() doesn't raise exceptions
            widgets = list(screen.compose())
            print(f"Screen {i+1} composed successfully with {len(widgets)} widgets")
            
            # Test that load_data() doesn't raise exceptions if it exists
            if hasattr(screen, 'load_data'):
                screen.load_data()
                print(f"Screen {i+1} load_data() executed successfully")
                
        except Exception as e:
            raise AssertionError(f"Screen {i+1} failed: {str(e)}")
    
    print("Manual screen testing passed!")


def test_error_message_format():
    """
    Test that error messages have proper structure and content.
    """
    from maestro.tui.utils import ErrorNormalizer
    
    # Test different exception types
    test_exceptions = [
        (ValueError("Invalid input"), "test validation"),
        (FileNotFoundError("File not found"), "loading config"),
        (PermissionError("Access denied"), "reading file"),
    ]
    
    for exc, context in test_exceptions:
        error_msg = ErrorNormalizer.normalize_exception(exc, context)
        
        assert error_msg.title is not None and error_msg.title != ""
        assert error_msg.message is not None and error_msg.message != ""
        print(f"✓ Error normalization for {type(exc).__name__} works correctly")
    
    print("Error message format test passed!")


if __name__ == "__main__":
    # Run sync tests
    test_manual_screen_switching()
    test_error_message_format()
    
    # Run async test
    import asyncio
    asyncio.run(test_screen_navigation_integration())
    
    print("\nAll integration tests completed successfully!")
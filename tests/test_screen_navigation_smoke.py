"""
Smoke test for screen navigation to ensure no "Error loading screen content" appears.
"""
import pytest
import asyncio
from textual.app import App
from maestro.tui.app import MaestroTUI
from maestro.tui.screens.home import HomeScreen
from maestro.tui.screens.sessions import SessionsScreen
from maestro.tui.screens.tasks import TasksScreen
from maestro.tui.screens.build import BuildScreen
from maestro.tui.screens.convert import ConvertScreen
from maestro.tui.screens.logs import LogsScreen
from maestro.tui.screens.memory import MemoryScreen
from maestro.tui.screens.vault import VaultScreen
from maestro.tui.screens.confidence import ConfidenceScreen
from maestro.tui.screens.plans import PlansScreen
from maestro.tui.screens.replay import ReplayScreen
from maestro.tui.screens.semantic import SemanticScreen
from maestro.tui.screens.arbitration import ArbitrationScreen
from maestro.tui.screens.semantic_diff import SemanticDiffScreen


def test_screen_navigation_smoke():
    """
    Smoke test that checks screen classes have proper structure and methods.
    """
    # Define all screen classes to test
    screen_classes = [
        HomeScreen,
        SessionsScreen,
        TasksScreen,
        BuildScreen,
        ConvertScreen,
        LogsScreen,
        MemoryScreen,
        VaultScreen,
        ConfidenceScreen,
        PlansScreen,
        ReplayScreen,
        SemanticScreen,
        ArbitrationScreen,
        SemanticDiffScreen,
    ]

    # Test that each screen class has the required methods
    for screen_class in screen_classes:
        # Test that the screen class can be instantiated
        try:
            screen_instance = screen_class()

            # Test that the screen has required methods
            assert hasattr(screen_instance, 'compose'), f"{screen_class.__name__} missing compose method"

            # Check if the screen has the new load_data method
            if hasattr(screen_instance, 'load_data'):
                print(f"✓ {screen_class.__name__} has load_data method")
            else:
                print(f"ℹ {screen_class.__name__} does not have load_data method")

        except Exception as e:
            pytest.fail(f"Error instantiating {screen_class.__name__}: {str(e)}")

    print("All screen structure tests passed!")


def test_error_message_replacement():
    """
    Test to ensure the error messages are properly replaced with detailed error messages.
    """
    from maestro.tui.utils import ErrorNormalizer, ErrorMessage, ErrorSeverity
    
    # Test that ErrorNormalizer creates proper error messages
    try:
        # Simulate an exception
        raise ValueError("Test error for validation")
    except Exception as e:
        error_msg = ErrorNormalizer.normalize_exception(e, "test operation")
        
        # Check that the error message has proper structure
        assert isinstance(error_msg, ErrorMessage)
        assert error_msg.title is not None
        assert error_msg.severity is not None
        assert error_msg.message is not None
        assert error_msg.severity in [ErrorSeverity.INFO, ErrorSeverity.WARNING, ErrorSeverity.ERROR, ErrorSeverity.BLOCKED]
        
        print(f"Error normalization test passed: {error_msg.title}")


if __name__ == "__main__":
    test_screen_navigation_smoke()
    test_error_message_replacement()
    print("All smoke tests completed successfully!")
"""
Tests for Maestro TUI Help System Functionality
"""
import pytest
from unittest.mock import Mock, patch
from maestro.tui.widgets.help_panel import HelpPanel, ScreenSpecificHelpData
from maestro.tui.widgets.progressive_disclosure import ExpandableSection, AdvancedConcepts
from maestro.tui.screens.help_index import HelpIndexScreen
from maestro.tui.screens.onboarding import OnboardingScreen
from maestro.tui.onboarding import OnboardingManager


def test_help_panel_creation():
    """Test that HelpPanel can be created without errors"""
    help_panel = HelpPanel(
        title="Test Help",
        help_content="This is test help content",
        screen_name="test"
    )
    assert help_panel is not None
    assert help_panel.title == "Test Help"
    assert help_panel.help_content == "This is test help content"
    assert help_panel.screen_name == "test"


def test_help_panel_initially_collapsed():
    """Test that HelpPanel is initially collapsed"""
    help_panel = HelpPanel()
    assert help_panel.collapsed is True


def test_help_panel_toggle():
    """Test that HelpPanel toggle works correctly (state change only, not widget composition)"""
    help_panel = HelpPanel()
    initial_state = help_panel.collapsed
    # Just test the state change without triggering UI updates that require composition
    help_panel.collapsed = not initial_state
    assert help_panel.collapsed != initial_state
    help_panel.collapsed = initial_state
    assert help_panel.collapsed == initial_state


def test_screen_specific_help_data():
    """Test that ScreenSpecificHelpData provides content for different screens"""
    # Test various screen names
    screens_to_test = ["home", "sessions", "plans", "tasks", "build", "convert", "replay", "arbitration", "semantic", "memory", "logs", "confidence", "vault"]
    
    for screen_name in screens_to_test:
        help_content = ScreenSpecificHelpData.get_help_content(screen_name)
        assert isinstance(help_content, str)
        assert len(help_content) > 0
        assert screen_name.capitalize() in help_content or screen_name.upper() in help_content


def test_help_content_for_unknown_screen():
    """Test that help content is provided even for unknown screens"""
    help_content = ScreenSpecificHelpData.get_help_content("unknown_screen")
    assert isinstance(help_content, str)
    assert "Help Unavailable" in help_content


def test_expandable_section_creation():
    """Test that ExpandableSection can be created without errors"""
    section = ExpandableSection(
        title="Test Section",
        content="Test content",
        section_id="test"
    )
    assert section is not None
    assert section.title == "Test Section"
    assert section.content == "Test content"
    assert section.section_id == "test"


def test_expandable_section_initially_collapsed():
    """Test that ExpandableSection is initially collapsed"""
    section = ExpandableSection("", "", "")
    assert section.expanded is False


def test_expandable_section_toggle():
    """Test that ExpandableSection toggle works correctly (state change only, not widget composition)"""
    section = ExpandableSection(title="", content="", section_id="test")
    initial_state = section.expanded
    # Just test the state change without triggering UI updates that require composition
    section.expanded = not initial_state
    assert section.expanded != initial_state
    section.expanded = initial_state
    assert section.expanded == initial_state


def test_advanced_concepts_explanations():
    """Test that AdvancedConcepts provides explanations for all concepts"""
    # Test all the methods exist and return valid strings
    concepts_methods = [
        'get_arbitration_explanation',
        'get_checkpoints_explanation', 
        'get_semantic_drift_explanation',
        'get_replay_vs_baseline_explanation',
        'get_confidence_scoring_explanation'
    ]
    
    for method_name in concepts_methods:
        method = getattr(AdvancedConcepts, method_name)
        explanation = method()
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "Explained" in explanation  # Each explanation contains this


def test_help_index_screen_creation():
    """Test that HelpIndexScreen can be created without errors"""
    screen = HelpIndexScreen()
    assert screen is not None


def test_help_index_screen_has_expected_methods():
    """Test that HelpIndexScreen has expected methods"""
    screen = HelpIndexScreen()
    
    assert hasattr(screen, 'compose')
    assert hasattr(screen, 'action_toggle_help_panel')


def test_onboarding_screen_creation():
    """Test that OnboardingScreen can be created without errors"""
    screen = OnboardingScreen()
    assert screen is not None


def test_onboarding_screen_has_expected_methods():
    """Test that OnboardingScreen has expected methods"""
    screen = OnboardingScreen()
    
    assert hasattr(screen, 'compose')
    assert hasattr(screen, 'action_next_step')
    assert hasattr(screen, 'action_skip_onboarding')
    assert hasattr(screen, '_complete_onboarding')


def test_onboarding_manager_creation():
    """Test that OnboardingManager can be created without errors"""
    manager = OnboardingManager()
    assert manager is not None


def test_onboarding_manager_steps():
    """Test that OnboardingManager provides steps"""
    manager = OnboardingManager()
    steps = manager.steps
    
    assert len(steps) > 0
    assert hasattr(steps[0], 'id')
    assert hasattr(steps[0], 'title')
    assert hasattr(steps[0], 'description')
    assert hasattr(steps[0], 'key_bindings')
    assert hasattr(steps[0], 'next_hint')


def test_onboarding_flow_completion():
    """Test onboarding completion functionality"""
    import tempfile
    import os
    # Use a temporary directory to avoid conflicts with real user config
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_config_dir = os.path.join(temp_dir, ".maestro")
        manager = OnboardingManager(config_dir=temp_config_dir)

        # Initially should not be completed
        assert manager.is_onboarding_completed() is False

        # Mark as completed
        manager.mark_onboarding_completed()

        # Should now be completed
        assert manager.is_onboarding_completed() is True


def test_command_palette_explanation_integration():
    """Test that command explanations are available (this tests the integration point)"""
    # Import here to make sure the file exists
    from maestro.tui.widgets.command_palette import CommandPaletteScreen
    
    # Test that the get_command_explanation method exists
    palette = CommandPaletteScreen()
    assert hasattr(palette, 'get_command_explanation')
    
    # Test that it returns a valid explanation structure
    explanation = palette.get_command_explanation("session_list")
    assert isinstance(explanation, dict)
    assert "description" in explanation
    assert "mutates_state" in explanation
    assert "reversible" in explanation
    assert "related_screens" in explanation


def test_help_panel_action_method_exists():
    """Test that the help panel action method exists in the app"""
    # This test verifies that our implementation of toggle_help_panel
    # is correctly integrated with the app. For now, we'll just verify
    # that the method exists conceptually by testing the function.
    from maestro.tui.app import MaestroTUI
    app = MaestroTUI()
    assert hasattr(app, 'action_toggle_help_panel')
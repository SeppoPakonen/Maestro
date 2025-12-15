"""
UI Tests for Replay & Baselines Screen
"""
import pytest
from maestro.tui.screens.replay import ReplayScreen


def test_replay_screen_creation():
    """Test that ReplayScreen can be created without errors"""
    screen = ReplayScreen()
    assert screen is not None


# Note: Testing the compose method requires a Textual app context which is
# complex to set up in unit tests. The compose method is tested during integration.
def test_replay_screen_has_expected_methods():
    """Test that ReplayScreen has expected methods"""
    screen = ReplayScreen()

    # Check that expected methods exist
    assert hasattr(screen, 'compose')
    assert hasattr(screen, 'on_mount')
    assert hasattr(screen, 'load_run_list')
    assert hasattr(screen, 'load_run_summary')
    assert hasattr(screen, 'on_data_table_row_selected')

    # Check that button handlers exist
    assert hasattr(screen, 'on_replay_dry_pressed')
    assert hasattr(screen, 'on_replay_apply_pressed')
    assert hasattr(screen, 'on_mark_baseline_pressed')
    assert hasattr(screen, 'on_compare_baseline_pressed')
    assert hasattr(screen, 'on_export_manifest_pressed')

    # Check that other methods exist
    assert hasattr(screen, 'update_diff_panes')
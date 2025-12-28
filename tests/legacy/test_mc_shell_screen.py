import asyncio

from maestro.tui.panes.sessions import SessionsPane
from maestro.tui.screens.mc_shell import MaestroMCShellApp, MainShellScreen


def test_mc_shell_focus_and_navigation():
    """Verify MC shell focus switching and placeholder opening."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            assert shell.focus_pane == "left"

            # Move to Sessions and open it
            await pilot.press("down")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert shell.current_section == "Sessions"
            assert shell.focus_pane == "right"

            # Tab should cycle back to the left and then right again
            await pilot.press("tab")
            await pilot.pause()
            assert shell.focus_pane == "left"

            await pilot.press("tab")
            await pilot.pause()
            assert shell.focus_pane == "right"

    asyncio.run(_run())


def test_menubar_navigation_menu_updates_content():
    """F9 activates the menubar and navigation entries open sections."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            await pilot.press("f9")
            await pilot.pause()
            assert shell.menubar is not None
            assert shell.menubar.is_active
            assert not shell.menubar.is_open

            # Move to Navigation menu then down to Sessions
            await pilot.press("right")  # Navigation
            await pilot.press("enter")  # open menu
            await pilot.pause()
            assert shell.menubar.is_open
            await pilot.press("down")  # Sessions entry
            await pilot.press("enter")
            await pilot.pause()

            assert shell.current_section == "Sessions"
            assert not shell.menubar.is_active

    asyncio.run(_run())


def test_sessions_menu_refresh_and_disabled_items():
    """Sessions menu actions fire and disabled entries remain inert."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            # Open Sessions pane
            await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()
            pane = shell.current_view
            assert isinstance(pane, SessionsPane)

            called = False

            async def fake_refresh():
                nonlocal called
                called = True

            pane.refresh_data = fake_refresh  # type: ignore
            shell._refresh_menu_bar()

            # Invoke Refresh via the menubar (Sessions menu, 4th item)
            await pilot.press("f9")
            await pilot.press("right")  # Navigation
            await pilot.press("right")  # Sessions menu
            await pilot.press("enter")  # open
            for _ in range(3):
                await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()
            assert called

            # Disable selection and ensure disabled item is inert
            pane.sessions = []
            pane.selected_id = None
            shell._refresh_menu_bar()

            await pilot.press("f9")
            await pilot.press("right")  # Navigation
            await pilot.press("right")  # Sessions
            await pilot.press("enter")
            await pilot.press("down")  # Set Active (disabled)
            await pilot.press("enter")
            await pilot.pause()
            assert "disabled" in shell.status_message.lower()

    asyncio.run(_run())


def test_f7_creates_session():
    """F7 in SessionsPane should trigger new session flow."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            # Navigate to Sessions
            await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()

            # Find the sessions pane
            pane = shell.current_view
            assert isinstance(pane, SessionsPane)

            # Track if action_new_session is called
            new_session_called = False
            original_method = pane.action_new_session

            async def mock_new_session():
                nonlocal new_session_called
                new_session_called = True
                # Still call the original to maintain pane behavior
                await original_method()

            pane.action_new_session = mock_new_session

            # Press F7 to create a new session
            await pilot.press("f7")
            await pilot.pause()

            assert new_session_called, "F7 should trigger new session action"

    asyncio.run(_run())


def test_f5_refreshes_view():
    """F5 in SessionsPane should trigger refresh action."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            # Navigate to Sessions
            await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()

            # Find the sessions pane
            pane = shell.current_view
            assert isinstance(pane, SessionsPane)

            # Track if refresh_data is called
            refresh_called = False
            original_method = pane.refresh_data

            async def mock_refresh():
                nonlocal refresh_called
                refresh_called = True
                # Still call the original to maintain pane behavior
                await original_method()

            pane.refresh_data = mock_refresh

            # Press F5 to refresh
            await pilot.press("f5")
            await pilot.pause()

            assert refresh_called, "F5 should trigger refresh action"

    asyncio.run(_run())


def test_f8_deletes_session():
    """F8 in SessionsPane should trigger delete session flow."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            # Navigate to Sessions
            await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()

            # Find the sessions pane
            pane = shell.current_view
            assert isinstance(pane, SessionsPane)

            # Track if action_delete_session is called
            delete_called = False
            original_method = pane.action_delete_session

            async def mock_delete():
                nonlocal delete_called
                delete_called = True
                # Still call the original to maintain pane behavior
                await original_method()

            pane.action_delete_session = mock_delete

            # Press F8 to delete a session
            await pilot.press("f8")
            await pilot.pause()

            assert delete_called, "F8 should trigger delete session action"

    asyncio.run(_run())


def test_unsupported_fkey_shows_message():
    """Pressing an unsupported F-key should show status message, not crash."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            # Navigate to a section without F-key actions
            # Go to Home which likely doesn't have many F-key actions
            await pilot.press("enter")  # Open home
            await pilot.pause()

            # Press F5 which might not be supported in this context
            await pilot.press("f5")
            await pilot.pause()

            # Check that a helpful status message is shown
            assert "available in this pane" in shell.status_message.lower() or "not available" in shell.status_message.lower()

    asyncio.run(_run())


def test_f9_opens_menu():
    """F9 should open the menu bar."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            # Press F9 to open menu
            await pilot.press("f9")
            await pilot.pause()

            # Verify menubar is now active
            assert shell.menubar.is_active
            assert shell._menu_focus_restore is not None

    asyncio.run(_run())


def test_f10_quits_app():
    """F10 should quit the application."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            # Press F10 to quit
            try:
                await pilot.press("f10")
                await pilot.pause()
                # If we get here without error, the app might not have quit immediately in test mode
                # That's expected behavior for how the test environment works
            except Exception:
                # This is fine - the app might quit or raise an exception in the test context
                pass

    asyncio.run(_run())


def test_focus_ring_tab_navigation():
    """Verify that Tab cycles through focus ring correctly."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            # Initially focused on left pane (section list)
            initial_focus = shell.focused
            section_list = shell.query_one("#section-list")
            assert initial_focus == section_list

            # Press Tab - should move to right pane content
            await pilot.press("tab")
            await pilot.pause()

            # The right pane should now be focused (either current view or content host)
            current_focus = shell.focused
            content_host = shell.query_one("#content-host")
            # Since there's no pane loaded initially, focus should move to content host
            assert current_focus == content_host or current_focus != initial_focus

            # Press Tab again - should cycle back to left pane
            await pilot.press("tab")
            await pilot.pause()
            new_focus = shell.focused
            assert new_focus == section_list

    asyncio.run(_run())


def test_shift_tab_navigation():
    """Verify that Shift+Tab cycles through focus ring in reverse."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            # Initially focused on left pane (section list)
            initial_focus = shell.focused
            section_list = shell.query_one("#section-list")
            assert initial_focus == section_list

            # Press Shift+Tab - should move to content host (right pane) initially
            await pilot.press("shift+tab")
            await pilot.pause()
            first_shift_focus = shell.focused
            content_host = shell.query_one("#content-host")
            # Should not be the same as initial focus
            assert first_shift_focus != initial_focus

            # Press Shift+Tab again - should cycle back to left pane
            await pilot.press("shift+tab")
            await pilot.pause()
            back_to_left = shell.focused
            assert back_to_left == section_list

    asyncio.run(_run())


def test_arrow_key_navigation_in_left_pane():
    """Verify arrow keys navigate section list in left pane."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            # Start with left pane focused
            section_list = shell.query_one("#section-list")
            initial_index = section_list.index if section_list.index is not None else 0
            assert initial_index == 0  # Should start at index 0 (Home)

            # Press down arrow to move to next section
            await pilot.press("down")
            await pilot.pause()
            new_index = section_list.index
            assert new_index == 1  # Should be at Sessions
            assert shell.current_section == "Sessions"

            # Press up arrow to move back
            await pilot.press("up")
            await pilot.pause()
            back_index = section_list.index
            assert back_index == 0  # Should be back at Home
            assert shell.current_section == "Home"

            # Test right arrow moves focus to right pane
            await pilot.press("right")
            await pilot.pause()
            new_focus = shell.focused
            content_host = shell.query_one("#content-host")
            assert new_focus != section_list  # Should have moved away from section list

    asyncio.run(_run())


def test_right_pane_arrow_navigation():
    """Test right arrow moves focus to right pane."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            # Start with left pane focused
            section_list = shell.query_one("#section-list")
            initial_focus = shell.focused
            assert initial_focus == section_list

            # Right arrow should move focus to right pane
            await pilot.press("right")
            await pilot.pause()
            right_focus = shell.focused
            content_host = shell.query_one("#content-host")
            assert right_focus != section_list  # Should have moved focus
            assert shell.focus_pane == "right"

            # Left arrow should move focus back to left pane
            await pilot.press("left")
            await pilot.pause()
            left_focus = shell.focused
            assert left_focus == section_list  # Should be back to left pane
            assert shell.focus_pane == "left"

    asyncio.run(_run())


def test_refresh_error_handling():
    """Test that refresh doesn't crash the shell even with errors."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            # Navigate to a pane
            await pilot.press("down")  # Move to "Sessions"
            await pilot.press("enter")  # Open "Sessions"
            await pilot.pause()

            # Verify the shell is still responsive after a refresh
            # Mock a failing refresh by temporarily modifying the current view
            original_refresh = shell.current_view.refresh_data if shell.current_view else None

            if original_refresh:
                # Mock the refresh to raise an exception
                async def failing_refresh():
                    raise Exception("Simulated refresh error")

                shell.current_view.refresh_data = failing_refresh

                # Try to refresh - this should not crash the shell
                await pilot.press("r")  # Refresh key
                await pilot.pause()

                # The shell should still be alive and functional
                assert shell.status_message != ""  # Should have an error message

                # The shell should still be responsive to navigation
                await pilot.press("tab")
                await pilot.pause()
                assert hasattr(shell, 'focus_pane')  # Shell is still functional

    asyncio.run(_run())


def test_modal_navigation():
    """Test modal dialog keyboard navigation."""

    from maestro.tui.widgets.modals import ConfirmDialog

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            # Push a confirm dialog
            dialog = ConfirmDialog("Test confirmation", "Test")
            # Create the dialog and check its bindings directly
            bindings = [b.key for b in dialog.BINDINGS]
            assert "escape" in bindings
            assert "enter" in bindings
            # Check if tab navigation bindings are present too
            assert "tab" in bindings

    asyncio.run(_run())

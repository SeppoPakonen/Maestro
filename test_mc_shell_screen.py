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

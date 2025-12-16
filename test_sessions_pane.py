import asyncio

from maestro.tui.screens.mc_shell import MaestroMCShellApp, MainShellScreen
from maestro.tui.panes.sessions import SessionsPane


def test_sessions_pane_mounts_and_refreshes():
    """Sessions pane should mount and refresh without errors."""

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

            assert isinstance(shell.current_view, SessionsPane)

            # Ensure refresh_data completes
            await shell.current_view.refresh_data()

    asyncio.run(_run())

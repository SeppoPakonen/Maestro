import asyncio
from textual.widgets import ListView

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
            list_view = shell.query_one("#section-list", ListView)
            assert list_view.index == 1

            await pilot.press("enter")
            await pilot.pause()
            assert shell.current_section == "Sessions"

            # Tab to right pane and confirm focus indicator updates
            await pilot.press("tab")
            await pilot.pause()
            assert shell.focus_pane == "right"

            await pilot.press("enter")
            assert "No action yet" in shell.status_message

            # Shift+Tab back and ensure list navigation still works
            await pilot.press("shift+tab")
            await pilot.pause()
            assert shell.focus_pane == "left"

            list_view = shell.query_one("#section-list", ListView)
            await pilot.press("down")
            await pilot.press("down")
            await pilot.press("up")
            assert list_view.index == 2  # zero-based index; should land on Plans

    asyncio.run(_run())


def test_menubar_navigation_menu_updates_content():
    """F9 opens the menu and navigation entries sync with panes."""

    async def _run():
        app = MaestroMCShellApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            shell = app.screen
            assert isinstance(shell, MainShellScreen)

            await pilot.press("f9")
            await pilot.pause()
            assert shell.menubar is not None
            assert shell.menubar.is_open

            # Move to Navigation menu then down to Sessions
            await pilot.press("right")
            await pilot.pause()
            await pilot.press("down")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert not shell.menubar.is_open
            assert shell.current_section == "Sessions"

            # Esc should close the menu without changing selection
            await pilot.press("f9")
            await pilot.pause()
            assert shell.menubar.is_open
            await pilot.press("escape")
            await pilot.pause()
            assert not shell.menubar.is_open
            assert shell.current_section == "Sessions"

    asyncio.run(_run())

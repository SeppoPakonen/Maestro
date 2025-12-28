"""
Test cases for MC-style mouse support and menubar navigation.
"""
import asyncio
from maestro.tui.screens.mc_shell import MaestroMCShellApp, MainShellScreen


async def _menubar_creation():
    """Test that the menubar is properly created with all required menus."""
    async with MaestroMCShellApp().run_test() as pilot:
        # Get the main screen
        screen = pilot.app.screen
        assert isinstance(screen, MainShellScreen)

        # Wait for mount to complete the initialization
        await pilot.pause()

        # Check that all required menus exist
        assert hasattr(screen, 'menu_bar_model')
        assert screen.menu_bar_model is not None

        # Menu bar should have Maestro, Navigation, View, and Help menus at minimum
        assert len(screen.menu_bar_model.menus) >= 4  # Maestro, Navigation, View, Help

        # Verify View menu exists for pane switching
        view_menu = None
        for menu in screen.menu_bar_model.menus:
            if menu.label == "View":
                view_menu = menu
                break

        assert view_menu is not None, "View menu should exist for pane switching"
        assert len(view_menu.items) > 0, "View menu should have items for pane switching"

        print("✓ Test menubar creation passed")


async def _menubar_view_menu_items():
    """Test that View menu has correct pane switching items."""
    async with MaestroMCShellApp().run_test() as pilot:
        screen = pilot.app.screen
        assert isinstance(screen, MainShellScreen)

        await pilot.pause()

        # Find the View menu
        view_menu = None
        for menu in screen.menu_bar_model.menus:
            if menu.label == "View":
                view_menu = menu
                break

        assert view_menu is not None

        # Check that View menu has all the sections
        expected_sections = set(screen.sections)
        actual_sections = set(item.id for item in view_menu.items if hasattr(item, 'id'))

        # Not all items in the menu might be sections (could be separators)
        # but all sections should be available in the View menu
        for section in screen.sections:
            found = False
            for item in view_menu.items:
                if hasattr(item, 'id') and item.id == section:
                    found = True
                    break
            assert found, f"Section '{section}' should be in View menu"

        print("✓ Test menubar view menu items passed")


async def _menubar_mouse_activation():
    """Test that menubar can be activated with mouse click."""
    async with MaestroMCShellApp().run_test() as pilot:
        screen = pilot.app.screen
        assert isinstance(screen, MainShellScreen)

        await pilot.pause()

        # Initially, menubar should not be active
        assert screen.menubar is not None
        assert not screen.menubar.is_active

        # Click on the menubar to activate it
        await pilot.click("#menu-row")

        # After click, menubar should be active
        assert screen.menubar.is_active

        print("✓ Test menubar mouse activation passed")


async def _menubar_keyboard_activation():
    """Test that menubar can be activated with F9 key."""
    async with MaestroMCShellApp().run_test() as pilot:
        screen = pilot.app.screen
        assert isinstance(screen, MainShellScreen)

        await pilot.pause()

        # Initially, menubar should not be active
        assert screen.menubar is not None
        assert not screen.menubar.is_active

        # Simulate F9 key press
        await pilot.press("f9")

        # After F9, menubar should be active
        assert screen.menubar.is_active

        print("✓ Test menubar keyboard activation passed")


async def _menu_item_activation():
    """Test that menu item activation works properly."""
    async with MaestroMCShellApp().run_test() as pilot:
        screen = pilot.app.screen
        assert isinstance(screen, MainShellScreen)

        await pilot.pause()

        # Check that the _handle_view_menu method can be called without error
        # Using a section that exists in the screen
        if len(screen.sections) > 1:
            test_section = screen.sections[1]
            # Call the method that handles view menu selections
            screen._handle_view_menu(type('MockItem', (), {'id': test_section})())

            # Check that section has changed
            assert screen.current_section == test_section
            assert screen.focus_pane == "right"  # Focus should move to right pane after selection

        print("✓ Test menu item activation passed")


async def _menubar_contains_correct_sections():
    """Test that Navigation menu contains all sections."""
    async with MaestroMCShellApp().run_test() as pilot:
        screen = pilot.app.screen
        assert isinstance(screen, MainShellScreen)

        await pilot.pause()

        # Find the Navigation menu
        nav_menu = None
        for menu in screen.menu_bar_model.menus:
            if menu.label == "Navigation":
                nav_menu = menu
                break

        assert nav_menu is not None

        # Verify all sections are available in Navigation menu
        for section in screen.sections:
            found = False
            for item in nav_menu.items:
                if hasattr(item, 'id') and item.id == section:
                    found = True
                    break
            assert found, f"Section '{section}' should be in Navigation menu"

        print("✓ Test menubar contains correct sections passed")


async def run_all_tests():
    """Run all tests."""
    await _menubar_creation()
    await _menubar_view_menu_items()
    await _menubar_mouse_activation()
    await _menubar_keyboard_activation()
    await _menu_item_activation()
    await _menubar_contains_correct_sections()

    print("\n✓ All mouse and menubar tests passed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())


def test_menubar_creation():
    asyncio.run(_menubar_creation())


def test_menubar_view_menu_items():
    asyncio.run(_menubar_view_menu_items())


def test_menubar_mouse_activation():
    asyncio.run(_menubar_mouse_activation())


def test_menubar_keyboard_activation():
    asyncio.run(_menubar_keyboard_activation())


def test_menu_item_activation():
    asyncio.run(_menu_item_activation())


def test_menubar_contains_correct_sections():
    asyncio.run(_menubar_contains_correct_sections())

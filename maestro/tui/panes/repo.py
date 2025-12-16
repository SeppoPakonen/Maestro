"""
RepoPane - Repository Analysis and Resolution Pane for MC shell.

Implements repository analysis features including:
- repo resolve: scanning U++ repo for packages, assemblies, and internal packages
- repo show: showing repository scan results from .maestro/repo/
- repo pkg: package query and inspection commands
"""
from __future__ import annotations

import asyncio
from typing import List, Optional
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Label, ListItem, ListView, Static, Button, Input
from textual.message import Message
from textual.reactive import reactive

from maestro.tui.panes.base import PaneView
from maestro.tui.menubar.model import Menu, MenuItem, Separator
from maestro.tui.utils import ErrorModal, ErrorNormalizer, memoization_cache
from maestro.tui.panes.registry import register_pane
from maestro.ui_facade.repo import (
    resolve_repository,
    get_repo_scan_results,
    list_repo_packages,
    get_repo_package_info,
    search_repo_packages,
    get_repo_assemblies,
    get_unknown_path_summary,
    RepoPackageInfo,
    RepoAssemblyInfo,
    RepoScanSummary,
    RepoScanDetails
)


class RepoPane(PaneView):
    """Repository analysis and resolution view embedded in the right pane."""

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("enter", "select_item", "Select"),
        ("shift+tab", "focus_left", "Back to sections"),
        ("f5", "refresh", "Refresh"),
        ("f6", "resolve_repo", "Resolve Repository"),
        ("f7", "search_packages", "Search Packages"),
        ("f9", "open_menu", "Menu"),
    ]

    DEFAULT_CSS = """
    RepoPane {
        layout: vertical;
    }

    #repo-header {
        height: 1;
        content-align: left middle;
        text-style: bold;
    }

    #repo-body {
        height: 1fr;
    }

    #repo-list-pane, #repo-detail-pane {
        height: 1fr;
        border: solid $primary 40%;
        padding: 1;
    }

    #repo-list-pane {
        width: 45%;
    }

    #repo-detail-pane {
        width: 55%;
    }

    #repo-status {
        height: 1;
        content-align: left middle;
        color: $text 80%;
    }

    #repo-packages-list {
        height: 1fr;
    }

    #repo-search-pane {
        height: 3;
        width: 100%;
        layout: horizontal;
        padding: 1;
    }

    #repo-search-input {
        width: 1fr;
    }

    #repo-search-button {
        width: 15;
    }

    .repo-status-completed {
        color: $success;
    }

    .repo-status-failed {
        color: $error;
    }

    .repo-status-in-progress {
        color: $warning;
    }
    """

    def __init__(self, repo_path: Optional[str] = None) -> None:
        super().__init__()
        self.pane_id = "repo"  # Required for the contract
        self.pane_title = "Repo"  # Required for the contract
        self.repo_path = repo_path
        self.scan_summary: Optional[RepoScanSummary] = None
        self.scan_details: Optional[RepoScanDetails] = None
        self.packages: List[RepoPackageInfo] = []
        self.assemblies: List[RepoAssemblyInfo] = []
        self.selected_item: Optional[str] = None  # Could be package name or assembly name
        self.selected_type: Optional[str] = None  # "package" or "assembly"
        
        # Search functionality
        self.search_term: str = ""

    def on_mount(self) -> None:
        """Called when the pane is mounted to the DOM. Initialize UI elements and event handlers here."""
        self.call_after_refresh(self._load_initial_data)

    def _load_initial_data(self) -> None:
        """Load initial data after mount."""
        async def _async_load():
            await self.refresh_data()
        self.app.call_later(_async_load)

    def on_focus(self) -> None:
        """Called when the pane receives focus. Perform focus-specific operations."""
        # Refresh data when pane comes into focus
        self.refresh()

    def on_blur(self) -> None:
        """Called when the pane loses focus. Perform cleanup of focus-specific resources."""
        # No special cleanup needed for this pane
        pass

    def refresh_data(self) -> None:
        """Refresh pane data and UI. This is for explicit refresh requests."""
        self.call_after_refresh(self._refresh_data_async)

    def _refresh_data_async(self) -> None:
        """Call the async refresh method."""
        async def _async_refresh():
            await self.refresh_data()
        self.app.call_later(_async_refresh)

    def get_menu_spec(self) -> Menu:
        """Return the menu specification for this pane."""
        return Menu(
            label=self.pane_title,
            items=[
                MenuItem(
                    "refresh",
                    "Refresh",
                    action=self.refresh_data,
                    key_hint="F5",
                    fkey="F5",
                    action_id="repo.refresh",
                    trust_label="[RO]",
                ),
                Separator(),
                MenuItem(
                    "resolve_repo",
                    "Resolve Repository (scan for packages)",
                    action=self.resolve_repository_action,
                    key_hint="F6",
                    fkey="F6",
                    action_id="repo.resolve",
                    trust_label="[MUT]",
                    requires_confirmation=True,
                    confirmation_label="Run repository scan? This may take a while.",
                ),
                Separator(),
                MenuItem(
                    "search_packages",
                    "Search Packages",
                    action=self.search_packages_action,
                    key_hint="F7",
                    fkey="F7",
                    action_id="repo.search",
                    trust_label="[RO]",
                ),
                MenuItem(
                    "list_packages",
                    "List All Packages",
                    action=self.list_packages_action,
                    key_hint="",
                    action_id="repo.list_packages",
                    trust_label="[RO]",
                ),
                MenuItem(
                    "list_assemblies",
                    "List Assemblies",
                    action=self.list_assemblies_action,
                    key_hint="",
                    action_id="repo.list_assemblies",
                    trust_label="[RO]",
                ),
                Separator(),
                MenuItem(
                    "menu",
                    "Menu",
                    action=self.menu_action,
                    key_hint="F9",
                    fkey="F9",
                    action_id="repo.menu",
                    trust_label="[RO]",
                ),
            ]
        )

    def compose(self) -> ComposeResult:
        try:
            yield Label("Repository Analysis", id="repo-header")
            
            # Search bar for package search
            with Horizontal(id="repo-search-pane"):
                yield Input(placeholder="Search packages...", id="repo-search-input")
                yield Button("Search", id="repo-search-button")
            
            with Horizontal(id="repo-body"):
                with Vertical(id="repo-list-pane"):
                    yield Label("Repository Items", id="repo-list-title")
                    yield ListView(id="repo-packages-list")
                with Vertical(id="repo-detail-pane"):
                    yield Label("Details", id="repo-detail-title")
                    yield Static("Select an item to view details.", id="repo-detail")
            yield Label("", id="repo-status")
        except Exception as e:
            # This is critical - never let a pane crash the shell
            try:
                yield Label(f"[RED]Error:[/RED] Failed to compose RepoPane: {str(e)}", id="error-label")
            except Exception:
                # If even the error display fails, yield a simple static
                yield Static("RepoPane failed to load")

    async def refresh_data(self) -> None:
        """Refresh repository data and UI."""
        try:
            # Load scan results
            self.scan_details = get_repo_scan_results(self.repo_path)
            if self.scan_details:
                self.packages = self.scan_details.packages_detected
                self.assemblies = self.scan_details.assemblies_detected
            else:
                # If no scan results available, just get packages list
                self.packages = list_repo_packages(self.repo_path)
                self.assemblies = get_repo_assemblies(self.repo_path)

            # If we have no packages and no assemblies, try a simple scan to get basic info
            if not self.packages and not self.assemblies:
                summary = resolve_repository(self.repo_path, no_write=True)  # Dry run to test access
                if summary:
                    self.scan_summary = summary

        except Exception as exc:
            await self._show_error(exc, "loading repository data")
            # Still render empty state
            self.packages = []
            self.assemblies = []
            return

        self._render_list()
        await self._load_details_for_selection()

        # Show status
        total_items = len(self.packages) + len(self.assemblies)
        if total_items > 0:
            self.notify_status(f"Repository loaded: {len(self.packages)} packages, {len(self.assemblies)} assemblies")
        else:
            self.notify_status("No repository data available. Run 'Resolve Repository' to scan.")

        self.request_menu_refresh()

    def _render_list(self) -> None:
        """Render the ListView from repository data."""
        try:
            list_view = self.query_one("#repo-packages-list", ListView)
            list_view.clear()

            if not self.packages and not self.assemblies:
                list_view.append(ListItem(Label("No repository items found [RO]")))
                list_view.index = 0
                self.selected_item = None
                self.selected_type = None
                self.request_menu_refresh()
                return

            # Add packages to the list
            for package in self.packages:
                # Format status with icon
                type_icon = "📦" if package.type == "upp" else "📦(I)"  # Internal package indicator
                short_dir = package.dir.split('/')[-1] if '/' in package.dir else package.dir
                label = f"{type_icon} {package.name[:30]} ({short_dir})"
                list_view.append(ListItem(Label(label), id=f"pkg-{package.name}"))

            # Add assemblies to the list
            for assembly in self.assemblies:
                type_icon = "🏛️"  # Assembly icon
                short_path = assembly.root_path.split('/')[-1] if '/' in assembly.root_path else assembly.root_path
                label = f"{type_icon} {assembly.name[:30]} ({short_path})"
                list_view.append(ListItem(Label(label), id=f"asm-{assembly.name}"))

            # Restore selection if possible
            if self.selected_item:
                item_ids = [f"pkg-{pkg.name}" for pkg in self.packages] + [f"asm-{asm.name}" for asm in self.assemblies]
                if self.selected_item in item_ids:
                    list_view.index = item_ids.index(self.selected_item)

            self.request_menu_refresh()
        except Exception as e:
            # Add error to the list view if possible
            try:
                list_view = self.query_one("#repo-packages-list", ListView)
                list_view.clear()
                list_view.append(ListItem(Label(f"[RED]Error updating list: {str(e)}[/]")))
            except Exception:
                # If we can't update the list, just pass
                pass

    async def _load_details_for_selection(self) -> None:
        """Load details for the currently selected item (package or assembly)."""
        detail_widget = self.query_one("#repo-detail", Static)

        if not self.selected_item or not self.selected_type:
            detail_widget.update("No item selected.")
            return

        try:
            if self.selected_type == "package":
                # Find the selected package
                package = next((pkg for pkg in self.packages if f"pkg-{pkg.name}" == self.selected_item), None)
                if not package:
                    detail_widget.update("Package not found.")
                    return

                # Format package details
                detail_lines = [
                    f"[b]Package:[/b] {package.name}",
                    f"[b]Type:[/b] {package.type}",
                    f"[b]Directory:[/b] {package.dir}",
                ]

                if package.upp_path:
                    detail_lines.append(f"[b]Upp File:[/b] {package.upp_path}")

                # Show first 5 files
                if package.files:
                    detail_lines.append(f"[b]Files:[/b]")
                    for file_path in package.files[:5]:
                        detail_lines.append(f"  • {file_path}")
                    if len(package.files) > 5:
                        detail_lines.append(f"  ... and {len(package.files) - 5} more")

                # If it's a UPP package, show UPP content details
                if package.upp and package.type == "upp":
                    detail_lines.append(f"[b]UPP Details:[/b]")
                    if "uses" in package.upp:
                        detail_lines.append(f"  Uses: {', '.join(package.upp.get('uses', []))}")
                    if "target" in package.upp:
                        detail_lines.append(f"  Targets: {', '.join(package.upp.get('target', []))}")

                detail_widget.update("\n".join(detail_lines))

            elif self.selected_type == "assembly":
                # Find the selected assembly
                assembly = next((asm for asm in self.assemblies if f"asm-{asm.name}" == self.selected_item), None)
                if not assembly:
                    detail_widget.update("Assembly not found.")
                    return

                # Format assembly details
                detail_lines = [
                    f"[b]Assembly:[/b] {assembly.name}",
                    f"[b]Path:[/b] {assembly.root_path}",
                ]

                if assembly.package_folders:
                    detail_lines.append(f"[b]Package Folders:[/b]")
                    for folder in assembly.package_folders[:5]:
                        detail_lines.append(f"  • {folder}")
                    if len(assembly.package_folders) > 5:
                        detail_lines.append(f"  ... and {len(assembly.package_folders) - 5} more")

                if assembly.evidence_refs:
                    detail_lines.append(f"[b]Evidence References:[/b]")
                    for ref in assembly.evidence_refs[:5]:
                        detail_lines.append(f"  • {ref}")

                detail_widget.update("\n".join(detail_lines))

            else:
                detail_widget.update("Unknown item type selected.")

        except Exception as exc:
            await self._show_error(exc, "loading item details")
            detail_widget.update(f"Error loading details for selected item")

    def _sync_selection_from_list(self) -> None:
        """Update selected_item and selected_type from ListView and refresh details."""
        try:
            list_view = self.query_one("#repo-packages-list", ListView)
            if list_view.index is None or (not self.packages and not self.assemblies):
                return

            # Get the item ID from the list - combine packages and assemblies
            all_items = [(f"pkg-{pkg.name}", "package") for pkg in self.packages] + \
                        [(f"asm-{asm.name}", "assembly") for asm in self.assemblies]
            
            if 0 <= list_view.index < len(all_items):
                self.selected_item, self.selected_type = all_items[list_view.index]

                # Refresh the details panel
                self.call_after_refresh(self._load_details_for_selection)
            self.request_menu_refresh()
        except Exception as e:
            # Log error but don't crash the pane
            pass

    async def action_cursor_up(self) -> None:
        """Move selection up in the list."""
        list_view = self.query_one("#repo-packages-list", ListView)
        list_view.action_cursor_up()
        self._sync_selection_from_list()

    async def action_cursor_down(self) -> None:
        """Move selection down in the list."""
        list_view = self.query_one("#repo-packages-list", ListView)
        list_view.action_cursor_down()
        self._sync_selection_from_list()

    async def action_select_item(self) -> None:
        """Select the current item (equivalent to enter key)."""
        self._sync_selection_from_list()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle mouse/enter selection."""
        if event.list_view.id != "repo-packages-list":
            return
        self._sync_selection_from_list()

    def action_focus_left(self) -> None:
        """Tab returns focus to the left navigation."""
        self.request_focus_left()

    def action_open_menu(self) -> None:
        """Expose menubar toggle from inside the pane."""
        try:
            if hasattr(self.app, "screen") and hasattr(self.app.screen, "action_toggle_menu"):
                self.app.screen.action_toggle_menu()  # type: ignore
        except Exception:
            pass

    def notify_status(self, message: str) -> None:
        """Update local status and inform shell."""
        try:
            self.query_one("#repo-status", Label).update(message)
        except Exception:
            pass
        super().notify_status(message)
        self.request_menu_refresh()

    async def _show_error(self, exc: Exception, context: str) -> None:
        """Normalize and show an error modal."""
        error_msg = ErrorNormalizer.normalize_exception(exc, context)
        self.notify_status(error_msg.message)
        self.app.push_screen(ErrorModal(error_msg))

    # Action methods for menu items
    def resolve_repository_action(self) -> None:
        """Action to resolve repository (scan for packages)."""
        try:
            summary = resolve_repository(self.repo_path)
            if summary.status == "completed":
                self.notify_status(f"Repository scan completed: {summary.packages_found} packages, {summary.assemblies_found} assemblies")
                # Refresh data to show the new scan results
                self.call_after_refresh(self._refresh_data_async)
            else:
                self.notify_status("Repository scan failed")
        except Exception as e:
            self.notify_status(f"Error running repository scan: {str(e)}")

    def search_packages_action(self) -> None:
        """Action to search for packages."""
        # In TUI context, we can't easily show a modal input, so we'll just use a notification
        # In a real implementation, this would likely show an input modal
        self.notify_status("Enter search term in the search box above")

    def list_packages_action(self) -> None:
        """Action to show all packages."""
        # Just refresh to show the package list
        self.call_after_refresh(self._refresh_data_async)

    def list_assemblies_action(self) -> None:
        """Action to show all assemblies."""
        # Just refresh to show the assembly list
        self.call_after_refresh(self._refresh_data_async)

    def menu_action(self) -> None:
        """Action for menu."""
        self.action_open_menu()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission."""
        if event.input.id == "repo-search-input":
            self.search_term = event.value
            self._perform_search()

    def _perform_search(self) -> None:
        """Perform the actual package search."""
        if not self.search_term.strip():
            # If search is empty, go back to showing all items
            self.call_after_refresh(self._refresh_data_async)
            return

        try:
            # Search for packages
            search_results = search_repo_packages(self.search_term, self.repo_path)
            
            # Update the list to show only search results
            self._update_list_with_search_results(search_results)
            
            self.notify_status(f"Search results: {len(search_results)} packages matching '{self.search_term}'")
        except Exception as e:
            self.notify_status(f"Search failed: {str(e)}")

    def _update_list_with_search_results(self, results: List[RepoPackageInfo]) -> None:
        """Update the list view to show search results."""
        try:
            list_view = self.query_one("#repo-packages-list", ListView)
            list_view.clear()

            if not results:
                list_view.append(ListItem(Label("No matching packages found [RO]")))
                list_view.index = 0
                self.selected_item = None
                self.selected_type = None
                return

            # Add search results to the list
            for package in results:
                type_icon = "📦" if package.type == "upp" else "📦(I)"  # Internal package indicator
                short_dir = package.dir.split('/')[-1] if '/' in package.dir else package.dir
                label = f"{type_icon} {package.name[:30]} ({short_dir})"
                list_view.append(ListItem(Label(label), id=f"pkg-{package.name}"))

            # Select the first result
            if results:
                self.selected_item = f"pkg-{results[0].name}"
                self.selected_type = "package"
                list_view.index = 0

            # Load details for the first result
            self.call_after_refresh(self._load_details_for_selection)
            
        except Exception as e:
            self.notify_status(f"Error updating search results: {str(e)}")


# Register with the global pane registry
register_pane("repo", lambda: RepoPane())

# IMPORT-SAFE: no side effects allowed
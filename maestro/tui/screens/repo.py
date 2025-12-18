"""
Repository screen for the Textual TUI (option 1).
"""
from __future__ import annotations

import os
import re
from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.events import Click
from textual.widgets import Static
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    RichLog,
    Static,
)

from maestro.main import init_maestro_dir
from maestro.ui_facade.repo import (
    RepoAssemblyInfo,
    RepoPackageInfo,
    find_repo_root_from_path,
    get_repo_assemblies,
    get_repo_scan_results,
    list_repo_packages,
    resolve_repository,
    search_repo_packages,
)
from maestro.tui.utils import ErrorModal, ErrorNormalizer
from maestro.ui_facade.ide import save_last_package_name


class LinkLabel(Static):
    """Simple clickable label used as a link-style control."""

    can_focus = True

    def __init__(self, label: str, action: str, *args, **kwargs) -> None:
        super().__init__(label, *args, **kwargs)
        self.action = action


class RepoScreen(Static):
    """Browse repository packages and assemblies."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("f6", "resolve", "Resolve"),
        ("i", "init_repo", "Init .maestro"),
        ("/", "focus_search", "Search"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.repo_root: Optional[str] = None
        self.packages: list[RepoPackageInfo] = []
        self.assemblies: list[RepoAssemblyInfo] = []
        self.render_seq: int = 0
        self.last_selected_package_name: Optional[str] = None

    def compose(self) -> ComposeResult:
        header = Header()

        # Create top bar with links like the IDE view
        top_bar = Horizontal(
            LinkLabel("← Back", action="back", id="repo-back", classes="ide-link ide-top-link"),
            Label("Repo", id="repo-title", classes="repo-title"),
            LinkLabel("Refresh", action="refresh", id="repo-refresh", classes="ide-link ide-top-link"),
            LinkLabel("Resolve", action="resolve", id="repo-resolve", classes="ide-link ide-top-link"),
            LinkLabel("Init .maestro", action="init", id="repo-init", classes="ide-link ide-top-link"),
            id="repo-top-bar",
        )

        search_bar = Horizontal(
            Input(placeholder="Search packages...", id="repo-search-input"),
            Button("Search", id="repo-search-btn"),
            id="repo-search",
        )

        list_pane = Vertical(
            Label("Repository Items", id="repo-list-title"),
            ListView(id="repo-items"),
            id="repo-list-pane",
        )

        detail_pane = Vertical(
            Label("Details", id="repo-detail-title"),
            LinkLabel("Open in IDE", action="open_ide", id="repo-open-ide", classes="repo-open-ide"),
            RichLog(id="repo-detail-log", wrap=True),
            id="repo-detail-pane",
        )

        main_row = Horizontal(
            list_pane,
            detail_pane,
            id="repo-main",
        )

        status = Static("", id="repo-status")

        body = Container(
            top_bar,
            search_bar,
            main_row,
            status,
            id="repo-screen",
        )

        footer = Footer()

        yield header
        yield body
        yield footer

    def on_mount(self) -> None:
        self._refresh_repo_root()
        self._load_data()

    def _refresh_repo_root(self) -> None:
        try:
            self.repo_root = find_repo_root_from_path()
        except Exception:
            self.repo_root = None

    def _load_data(self, search_term: Optional[str] = None) -> None:
        try:
            if not self.repo_root and not search_term:
                self.packages = []
                self.assemblies = []
                self._render_list()
                self._update_status("Repository not initialized. Use Init .maestro.")
                return

            if search_term:
                self.packages = search_repo_packages(search_term, self.repo_root)
                self.assemblies = []
            else:
                scan_details = get_repo_scan_results(self.repo_root)
                if scan_details:
                    self.packages = scan_details.packages_detected
                    self.assemblies = scan_details.assemblies_detected
                else:
                    self.packages = list_repo_packages(self.repo_root)
                    self.assemblies = get_repo_assemblies(self.repo_root)

            self._render_list()
            self._update_status(
                f"Loaded {len(self.packages)} packages, {len(self.assemblies)} assemblies"
                if self.packages or self.assemblies
                else "No repository data found. Resolve or Init may be required."
            )
        except Exception as exc:
            error_msg = ErrorNormalizer.normalize_exception(exc, "loading repository data")
            self.app.push_screen(ErrorModal(error_msg))
            self._render_empty_state(error_msg.message)

    def _render_empty_state(self, message: str) -> None:
        list_view = self.query_one("#repo-items", ListView)
        list_view.clear()
        list_view.append(ListItem(Label(message, id="repo-empty-message")))

    def _render_list(self) -> None:
        list_view = self.query_one("#repo-items", ListView)

        # Store the previously selected package name to restore after reload
        previous_selected_package_name = self.last_selected_package_name

        list_view.clear()
        self.render_seq += 1

        if not self.packages and not self.assemblies:
            if self.repo_root:
                self._render_empty_state("No repository items. Run Resolve to scan.")
            else:
                self._render_empty_state("Repository not initialized. Use Init .maestro.")
            return

        def safe_id(prefix: str, name: str) -> str:
            # Textual IDs: letters, numbers, underscores, hyphens; cannot start with invalid char
            cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", name)
            cleaned = cleaned.strip("-")
            if not cleaned:
                cleaned = "item"
            return f"{prefix}-{cleaned}"

        def unique_id(base_id: str, idx: int) -> str:
            return f"{base_id}-r{self.render_seq}-{idx}"

        for idx, package in enumerate(self.packages):
            short_dir = os.path.basename(package.dir) if package.dir else ""
            text = f"[PKG] {package.name} ({package.type})"
            if short_dir:
                text += f" [{short_dir}]"
            item = ListItem(Label(text), id=unique_id(safe_id("pkg", package.name), idx))
            item.data = ("pkg", package.name)  # store lookup key without invalid characters
            list_view.append(item)

        pkg_count = len(self.packages)

        for idx, assembly in enumerate(self.assemblies):
            short_path = os.path.basename(assembly.root_path) if assembly.root_path else ""
            text = f"[ASM] {assembly.name}"
            if short_path:
                text += f" [{short_path}]"
            item = ListItem(Label(text), id=unique_id(safe_id("asm", assembly.name), pkg_count + idx))
            item.data = ("asm", assembly.name)
            list_view.append(item)

        # After reloading the list, restore the selection if applicable
        restored = False
        if previous_selected_package_name:
            # Find if the previously selected package is still present in the new list
            for idx, pkg in enumerate(self.packages):
                if pkg.name == previous_selected_package_name:
                    list_view.index = idx
                    selected_item = list_view.children[idx] if idx < len(list_view.children) else None
                    if selected_item:
                        self._show_details(selected_item)
                        self.last_selected_package_name = previous_selected_package_name
                        restored = True
                    break
            else:
                self.last_selected_package_name = None
        if not restored and self.packages:
            # Default to first package when nothing was restored so IDE button stays usable
            list_view.index = 0
            selected_item = list_view.children[0] if list_view.children else None
            if selected_item:
                item_type, item_name = getattr(selected_item, "data", (None, None))
                if item_type == "pkg":
                    self.last_selected_package_name = item_name
                self._show_details(selected_item)
        elif not restored:
            self.last_selected_package_name = None

    def _show_details(self, item: ListItem) -> None:
        detail_log = self.query_one("#repo-detail-log", RichLog)
        detail_log.clear()

        item_type, name = getattr(item, "data", (None, None))

        # Fallback to legacy id parsing
        if not item_type and item.id and item.id.startswith("pkg-"):
            item_type = "pkg"
            name = item.id.split("pkg-", 1)[1]
        elif not item_type and item.id and item.id.startswith("asm-"):
            item_type = "asm"
            name = item.id.split("asm-", 1)[1]

        # Track the last selected package name for IDE persistence
        if item_type == "pkg" and name:
            self.last_selected_package_name = name

        # Enable/disable the IDE link based on item type
        ide_link = self.query_one("#repo-open-ide", LinkLabel)
        if item_type == "pkg":
            ide_link.can_focus = True  # Enable interaction
            # Update the styling to show it's enabled
            ide_link.remove_class("disabled")
        else:
            ide_link.can_focus = False  # Disable interaction
            # Update the styling to show it's disabled
            ide_link.add_class("disabled")

        if item_type == "pkg" and name:
            package = next((p for p in self.packages if p.name == name), None)
            if not package:
                detail_log.write("Package not found.")
                return

            detail_log.write(f"Package: {package.name}")
            detail_log.write(f"Type: {package.type}")
            if package.dir:
                detail_log.write(f"Directory: {package.dir}")
            if package.upp_path:
                detail_log.write(f"UPP: {package.upp_path}")
            if package.files:
                detail_log.write("Files:")
                for file_path in package.files[:5]:
                    detail_log.write(f"  - {file_path}")
                if len(package.files) > 5:
                    detail_log.write(f"  ... and {len(package.files) - 5} more")

        elif item_type == "asm" and name:
            assembly = next((a for a in self.assemblies if a.name == name), None)
            if not assembly:
                detail_log.write("Assembly not found.")
                return

            detail_log.write(f"Assembly: {assembly.name}")
            detail_log.write(f"Root: {assembly.root_path}")
            if assembly.package_folders:
                detail_log.write("Package folders:")
                for folder in assembly.package_folders[:10]:
                    detail_log.write(f"  - {folder}")
                if len(assembly.package_folders) > 10:
                    detail_log.write(f"  ... and {len(assembly.package_folders) - 10} more")
            if assembly.evidence_refs:
                detail_log.write("Evidence references:")
                for ref in assembly.evidence_refs[:5]:
                    detail_log.write(f"  - {ref}")

    @on(ListView.Selected, "#repo-items")
    def _handle_selection(self, event: ListView.Selected) -> None:
        self._show_details(event.item)

    @on(Click, "#repo-open-ide")
    def _open_ide_clicked(self, _: Click) -> None:
        # Only open IDE if a package is selected (not an assembly)
        if hasattr(self, 'last_selected_package_name') and self.last_selected_package_name:
            # Save the last package name for persistence
            save_last_package_name(self.last_selected_package_name)
            # Call the app's open_ide_for_package method
            self.app.open_ide_for_package(self.last_selected_package_name)

    @on(Button.Pressed, "#repo-refresh")
    def _refresh_clicked(self, _: Button.Pressed) -> None:
        self.action_refresh()

    @on(Button.Pressed, "#repo-resolve")
    def _resolve_clicked(self, _: Button.Pressed) -> None:
        self.action_resolve()

    @on(Button.Pressed, "#repo-init")
    def _init_clicked(self, _: Button.Pressed) -> None:
        self.action_init_repo()

    @on(Button.Pressed, "#repo-search-btn")
    def _search_clicked(self, _: Button.Pressed) -> None:
        search_value = self.query_one("#repo-search-input", Input).value.strip()
        self._load_data(search_value or None)

    @on(Input.Submitted, "#repo-search-input")
    def _search_submitted(self, event: Input.Submitted) -> None:
        self._search_clicked(None)

    def action_refresh(self) -> None:
        self._refresh_repo_root()
        self._load_data()

    def action_resolve(self) -> None:
        try:
            summary = resolve_repository(self.repo_root)
            status_text = getattr(summary, "status", "") or ""
            if status_text.lower() == "completed":
                msg = (
                    f"Resolve completed: {summary.packages_found} packages, "
                    f"{summary.assemblies_found} assemblies"
                )
            else:
                msg = "Repository resolve failed or incomplete."
            self._update_status(msg)
            self._load_data()
        except Exception as exc:
            error_msg = ErrorNormalizer.normalize_exception(exc, "resolving repository")
            self.app.push_screen(ErrorModal(error_msg))
            self._update_status(error_msg.message)

    def action_init_repo(self) -> None:
        target_dir = self.repo_root or os.getcwd()
        try:
            init_maestro_dir(target_dir, verbose=False)
            self._update_status(f"Initialized .maestro at {target_dir}")
            self._refresh_repo_root()
            self._load_data()
        except Exception as exc:
            error_msg = ErrorNormalizer.normalize_exception(exc, "initializing repository")
            self.app.push_screen(ErrorModal(error_msg))
            self._update_status(error_msg.message)

    def action_focus_search(self) -> None:
        try:
            self.query_one("#repo-search-input", Input).focus()
        except Exception:
            pass

    @on(Click, "#repo-top-bar .ide-link")
    def _on_link_clicked(self, event: Click) -> None:
        """Handle clicks on link-style controls."""
        # In Textual, the clicked widget can be accessed via event.control
        clicked_widget = event.control
        action = getattr(clicked_widget, "action", None) or clicked_widget.id

        if not action:
            return

        # Map the action to the appropriate method
        if action == "back":
            # Go back to the previous screen
            if hasattr(self.app, 'switch_back_from_ide'):
                # If we're in the middle of navigation, go back
                self.app.switch_back_from_ide()
            else:
                # Go back to home screen
                from maestro.tui.screens.home import HomeScreen
                self.app._switch_main_content(HomeScreen())
        elif action == "refresh":
            self.action_refresh()
        elif action == "resolve":
            self.action_resolve()
        elif action == "init":
            self.action_init_repo()
        elif action == "open_ide":
            self._open_ide_clicked(None)

    def _update_status(self, message: str) -> None:
        status_widget = self.query_one("#repo-status", Static)
        status_widget.update(message)

    def load_data(self, search_term: Optional[str] = None) -> None:
        """Public method to load data, allowing the app to reuse this functionality."""
        self._load_data(search_term)

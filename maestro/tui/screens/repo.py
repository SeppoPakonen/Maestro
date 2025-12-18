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

    def compose(self) -> ComposeResult:
        header = Header()

        controls = Horizontal(
            Button("Refresh", id="repo-refresh", variant="primary"),
            Button("Resolve", id="repo-resolve", variant="success"),
            Button("Init .maestro", id="repo-init", variant="warning"),
            id="repo-controls",
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
            controls,
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

    def _update_status(self, message: str) -> None:
        status_widget = self.query_one("#repo-status", Static)
        status_widget.update(message)

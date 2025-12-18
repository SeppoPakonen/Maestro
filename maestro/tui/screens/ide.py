"""IDE Screen for the Maestro TUI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Type

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, RichLog, Static

from maestro.ui_facade.ide import (
    get_last_package_name,
    get_package_with_dependencies,
    read_file_safely,
    save_last_package_name,
)
from maestro.ui_facade.repo import RepoPackageInfo, find_repo_root_from_path


class IdeScreen(Static):
    """IDE Screen showing packages, files, and a simple editor view."""

    def __init__(self, package_name: str, previous_screen_cls: Optional[Type[Static]] = None, resume_mode: bool = False):
        super().__init__()
        self.package_name = package_name
        self.previous_screen_cls = previous_screen_cls
        # If we are resuming from navigation with a previously saved package, avoid auto-opening a file
        self.resume_mode = resume_mode
        self.repo_root: Optional[str] = None
        self.packages: list[RepoPackageInfo] = []
        self.current_package: Optional[RepoPackageInfo] = None
        self.current_file_path: Optional[str] = None
        self.render_seq: int = 0

    def compose(self) -> ComposeResult:
        """Compose the IDE screen layout."""
        yield Header()

        with Container(id="ide-screen"):
            with Horizontal(id="ide-top-bar"):
                yield Button("← Back", id="ide-back", variant="default")
                yield Label("IDE", id="ide-title")
                yield Button("Refresh", id="ide-refresh")

            with Horizontal(id="ide-body"):
                with Vertical(id="ide-side-panel"):
                    yield Label("Packages", classes="section-label")
                    yield ListView(id="ide-package-list")

                    yield Label("Files", classes="section-label")
                    yield ListView(id="ide-file-list")

                with Vertical(id="ide-main-panel"):
                    yield Static("No file selected", id="ide-editor-title")
                    yield RichLog(
                        id="ide-editor",
                        wrap=False,
                        highlight=False,
                        markup=False,
                        classes="editor",
                    )

                    with Container(id="ide-bottom"):
                        with Horizontal(id="ide-tab-buttons"):
                            yield Button("Log", id="ide-tab-log", variant="primary")
                            yield Button("Errors", id="ide-tab-errors", variant="default")
                            yield Button("Search", id="ide-tab-search", variant="default")
                            yield Button("Calc", id="ide-tab-calc", variant="default")
                            yield Button("Debug", id="ide-tab-debug", variant="default")
                            yield Button("Hide", id="ide-toggle-bottom", variant="default")

                        yield Static("Log content goes here...", id="ide-tab-content")

        yield Footer()

    def on_mount(self) -> None:
        """Load the IDE data after mounting."""
        self.repo_root = find_repo_root_from_path(Path.cwd())
        if not self.repo_root:
            self._show_status("No repository root found.")
            return

        target_package = self.package_name or get_last_package_name()
        if not target_package:
            self._show_status("No package selected. Pick a package in Repo first.")
            return

        self.package_name = target_package
        save_last_package_name(target_package)
        self._update_title()
        self.refresh_content()

    def _show_status(self, message: str) -> None:
        """Display a status message in the editor area."""
        editor = self.query_one("#ide-editor", RichLog)
        editor.clear()
        editor.write(message, markup=False)
        self.query_one("#ide-editor-title", Static).update("Status")

    def _update_title(self) -> None:
        """Refresh the title label with current package name."""
        title = self.query_one("#ide-title", Label)
        active = self.package_name or "IDE"
        title.update(f"IDE: {active}")

    def _safe_id(self, prefix: str, name: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-") or "item"
        self.render_seq += 1
        return f"{prefix}-{cleaned}-r{self.render_seq}"

    def refresh_content(self) -> None:
        """Reload package/dependency data and rebuild UI lists."""
        try:
            self.packages = get_package_with_dependencies(self.package_name, self.repo_root)
        except Exception as exc:
            self._show_status(f"Failed to load packages: {exc}")
            return

        package_list = self.query_one("#ide-package-list", ListView)
        package_list.clear()

        for pkg in self.packages:
            item = ListItem(Label(pkg.name), id=self._safe_id("pkg", pkg.name))
            item.data = pkg
            package_list.append(item)

        if self.packages:
            self._select_package(self.packages[0])
            package_list.index = 0
        else:
            self._show_status("No packages found for IDE.")

    def _select_package(self, package: RepoPackageInfo) -> None:
        """Select a package and update the file list."""
        self.current_package = package
        self.package_name = package.name
        save_last_package_name(package.name)
        self._update_title()
        auto_open = not self.resume_mode
        # After the first selection in resume mode, revert to normal behavior
        self.resume_mode = False
        self._update_file_list(package, auto_open=auto_open)

    def _update_file_list(self, package: RepoPackageInfo, auto_open: bool = False) -> None:
        file_list = self.query_one("#ide-file-list", ListView)
        file_list.clear()

        # Skip .upp files in the file list; they are configuration rather than source
        files = [
            f for f in list(getattr(package, "files", []) or [])
            if not str(f).lower().endswith(".upp")
        ]

        for rel_path in files:
            display_text = rel_path
            item = ListItem(Label(display_text), id=self._safe_id("file", rel_path))
            item.data = (package, rel_path)
            file_list.append(item)

        # Clear editor when switching package
        editor = self.query_one("#ide-editor", RichLog)
        editor.clear()
        self.query_one("#ide-editor-title", Static).update(f"{package.name} (no file selected)")

        # Auto-open the first non-.upp file (or .upp if none) unless we are resuming
        if auto_open and files:
            target = files[0]
            # Update selection to match the auto-opened file
            for idx, item in enumerate(file_list.children):
                if getattr(item, "data", None) and item.data[1] == target:
                    file_list.index = idx
                    break
            self._open_file(package, target)

    @on(ListView.Selected, "#ide-package-list")
    def _package_selected(self, event: ListView.Selected) -> None:
        pkg = getattr(event.item, "data", None)
        if pkg:
            self._select_package(pkg)

    @on(ListView.Selected, "#ide-file-list")
    def _file_selected(self, event: ListView.Selected) -> None:
        data = getattr(event.item, "data", None)
        if not data:
            return
        package, rel_path = data
        self._open_file(package, rel_path)

    def _resolve_file_path(self, package: RepoPackageInfo, rel_path: str) -> Path:
        """Resolve absolute or relative file paths, avoiding double-prefixing the package directory."""
        base_dir = Path(package.dir)
        path_obj = Path(rel_path)

        candidates: list[Path] = []

        if path_obj.is_absolute():
            candidates.append(path_obj)
        else:
            parts = path_obj.parts
            if parts and parts[0] == base_dir.name:
                # rel_path already starts with the package dir name; avoid duplicating it
                candidates.append(base_dir.parent / path_obj)
            candidates.append(base_dir / path_obj)
            candidates.append(base_dir / path_obj.name)

        for cand in candidates:
            if cand.exists():
                return cand

        return candidates[0] if candidates else base_dir / path_obj

    def _open_file(self, package: RepoPackageInfo, rel_path: str) -> None:
        full_path = self._resolve_file_path(package, rel_path)

        content = read_file_safely(str(full_path))
        if content == "" and full_path.exists():
            # Fallback if file is empty or failed to read but exists
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                content = "[Unable to read file contents]"
        elif not full_path.exists():
            content = f"[File not found: {full_path}]"

        editor_title = self.query_one("#ide-editor-title", Static)
        editor_title.update(str(full_path))

        editor = self.query_one("#ide-editor", RichLog)
        editor.clear()
        editor.write(content)
        self.current_file_path = str(full_path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ide-back":
            self.app.switch_back_from_ide(self.previous_screen_cls)
        elif event.button.id == "ide-refresh":
            self.refresh_content()
        elif event.button.id == "ide-toggle-bottom":
            self.toggle_bottom_pane()
        elif event.button.id and event.button.id.startswith("ide-tab-"):
            self.switch_tab(event.button.id)

    def toggle_bottom_pane(self) -> None:
        bottom = self.query_one("#ide-bottom", Container)
        if "hidden" in bottom.classes:
            bottom.remove_class("hidden")
        else:
            bottom.add_class("hidden")

    def switch_tab(self, tab_id: str) -> None:
        for btn_id in ["ide-tab-log", "ide-tab-errors", "ide-tab-search", "ide-tab-calc", "ide-tab-debug", "ide-toggle-bottom"]:
            btn = self.query_one(f"#{btn_id}", Button)
            btn.variant = "default"

        if tab_id != "ide-toggle-bottom":
            selected_btn = self.query_one(f"#{tab_id}", Button)
            selected_btn.variant = "primary"

        content = self.query_one("#ide-tab-content", Static)
        if tab_id == "ide-tab-log":
            content.update("Log content goes here...")
        elif tab_id == "ide-tab-errors":
            content.update("Error/Warning messages would appear here...")
        elif tab_id == "ide-tab-search":
            content.update("Search results would appear here...")
        elif tab_id == "ide-tab-calc":
            content.update("Calculator/evaluator results would appear here...")
        elif tab_id == "ide-tab-debug":
            content.update("Debugger output would appear here...")

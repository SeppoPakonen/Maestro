"""IDE Screen for the Maestro TUI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Type

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.events import Click
from textual.widgets import Footer, Header, Label, ListItem, ListView, RichLog, Static

from maestro.ui_facade.ide import (
    get_last_package_name,
    get_package_with_dependencies,
    read_file_safely,
    save_last_package_name,
)
from maestro.ui_facade.repo import RepoPackageInfo, find_repo_root_from_path


class LinkLabel(Static):
    """Simple clickable label used as a link-style control."""

    can_focus = True

    def __init__(self, label: str, action: str, *args, **kwargs) -> None:
        super().__init__(label, *args, **kwargs)
        self.action = action


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
                yield LinkLabel("← Back", action="back", id="ide-back", classes="ide-link ide-top-link")
                yield Label("IDE", id="ide-title")
                yield LinkLabel("Refresh", action="refresh", id="ide-refresh", classes="ide-link ide-top-link")

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
                            yield LinkLabel("Log", action="tab-log", id="ide-tab-log", classes="ide-link ide-tab-link active")
                            yield LinkLabel("Errors", action="tab-errors", id="ide-tab-errors", classes="ide-link ide-tab-link")
                            yield LinkLabel("Search", action="tab-search", id="ide-tab-search", classes="ide-link ide-tab-link")
                            yield LinkLabel("Calc", action="tab-calc", id="ide-tab-calc", classes="ide-link ide-tab-link")
                            yield LinkLabel("Debug", action="tab-debug", id="ide-tab-debug", classes="ide-link ide-tab-link")
                            yield LinkLabel("Hide", action="toggle-bottom", id="ide-toggle-bottom", classes="ide-link ide-tab-link")

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

        # Auto-open the first non-.upp file unless we are resuming
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
            if parts and parts[0] == base_dir.name and len(parts) > 1:
                stripped = Path(*parts[1:])
                candidates.append(base_dir / stripped)
                candidates.append(base_dir.parent / stripped)
            candidates.append(base_dir.parent / path_obj)
            candidates.append(base_dir / path_obj)
            candidates.append(base_dir / path_obj.name)

        deduped: list[Path] = []
        seen: set[str] = set()
        for cand in candidates:
            key = str(cand)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(cand)

        for cand in deduped:
            if cand.exists():
                return cand

        return deduped[0] if deduped else base_dir / path_obj

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

    @on(Click, ".ide-link")
    def _on_link_clicked(self, event: Click) -> None:
        """Handle clicks on link-style controls."""
        # In Textual, the clicked widget can be accessed via event.control
        clicked_widget = event.control
        action = getattr(clicked_widget, "action", None) or clicked_widget.id
        if not action:
            return
        if action == "back":
            self.app.switch_back_from_ide(self.previous_screen_cls)
        elif action == "refresh":
            self.refresh_content()
        elif action == "toggle-bottom":
            self.toggle_bottom_pane()
        elif action.startswith("tab-"):
            self.switch_tab(action)

        # Temporarily remove focus capability and then restore it to clear focus
        # This ensures that after clicking, the element doesn't remain in focused state
        clicked_widget.can_focus = False
        self.set_timer(0.01, lambda: setattr(clicked_widget, 'can_focus', True))
        event.stop()

    def toggle_bottom_pane(self) -> None:
        bottom = self.query_one("#ide-bottom", Container)
        if "hidden" in bottom.classes:
            bottom.remove_class("hidden")
        else:
            bottom.add_class("hidden")

    def switch_tab(self, tab_action: str) -> None:
        tab_ids = ["ide-tab-log", "ide-tab-errors", "ide-tab-search", "ide-tab-calc", "ide-tab-debug", "ide-toggle-bottom"]
        for tab_id in tab_ids:
            tab_widget = self.query_one(f"#{tab_id}", LinkLabel)
            tab_widget.remove_class("active")

        if tab_action != "toggle-bottom":
            target_id = f"ide-{tab_action}" if not tab_action.startswith("ide-") else tab_action
            tab_widget = self.query_one(f"#{target_id}", LinkLabel)
            tab_widget.add_class("active")

        content = self.query_one("#ide-tab-content", Static)
        if tab_action in ("tab-log", "ide-tab-log"):
            content.update("Log content goes here...")
        elif tab_action in ("tab-errors", "ide-tab-errors"):
            content.update("Error/Warning messages would appear here...")
        elif tab_action in ("tab-search", "ide-tab-search"):
            content.update("Search results would appear here...")
        elif tab_action in ("tab-calc", "ide-tab-calc"):
            content.update("Calculator/evaluator results would appear here...")
        elif tab_action in ("tab-debug", "ide-tab-debug"):
            content.update("Debugger output would appear here...")

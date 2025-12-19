"""
Vault Screen for Maestro TUI
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, ListView, ListItem, Input, Static, Button
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual import on, work
from maestro.ui_facade.vault import VaultItem, VaultFilter, list_items, get_available_source_types, get_available_subsystems
from typing import List, Optional
import json


class SourceSelector(Vertical):
    """Left panel for source type and subsystem selection"""

    def __init__(self) -> None:
        super().__init__()
        self.source_types = get_available_source_types()
        self.subsystems = get_available_subsystems()
        self.selected_source_types: List[str] = []
        self.selected_subsystems: List[str] = []
        self.time_range = "all"  # "recent" or "all"

    def compose(self) -> ComposeResult:
        yield Label("[b]Source Type[/b]", classes="filter-title")
        for src_type in self.source_types:
            yield Label(f"☐ {src_type}", id=f"src-{src_type}", classes="filter-option")

        yield Label("[b]Subsystem[/b]", classes="filter-title", margin_top=1)
        for subsystem in self.subsystems:
            yield Label(f"☐ {subsystem}", id=f"sub-{subsystem}", classes="filter-option")

        yield Label("[b]Time Range[/b]", classes="filter-title", margin_top=1)
        yield Label("☐ All", id="time-all", classes="filter-option")
        yield Label("☐ Recent", id="time-recent", classes="filter-option")


class ItemList(Vertical):
    """Center-left panel for listing vault items"""

    def __init__(self) -> None:
        super().__init__()
        self.items: List[VaultItem] = []
        self.search_query = ""

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search items...", id="item-search", classes="search-input")
        yield ListView(id="items-list-view", classes="items-list")

    def set_items(self, items: List[VaultItem]) -> None:
        """Set the list of items to display"""
        self.items = items
        list_view = self.query_one("#items-list-view", ListView)
        list_view.clear()

        for item in items:
            # Create a formatted label for each item
            timestamp_short = item.timestamp.split("T")[1][:8] if "T" in item.timestamp else item.timestamp
            size_mb = item.size / (1024 * 1024) if item.size > 1024 * 1024 else item.size / 1024
            size_unit = "MB" if item.size > 1024 * 1024 else "KB"

            item_text = f"{timestamp_short} | {item.source_type} | {item.origin[:20]} | {item.description[:30]} | {size_mb:.1f}{size_unit}"
            list_item = ListItem(Label(item_text), id=f"item-{item.id}")
            list_view.append(list_item)


class ViewerPane(VerticalScroll):
    """Center-right panel for viewing item content"""

    def __init__(self) -> None:
        super().__init__()
        self.current_item: Optional[VaultItem] = None

    def compose(self) -> ComposeResult:
        yield Label("[b]Content Viewer[/b]", id="viewer-title")
        yield Static("", id="content-display", classes="content-display")

    def set_item(self, item: Optional[VaultItem]) -> None:
        """Display content for the given item"""
        self.current_item = item
        if item is None:
            self.query_one("#content-display", Static).update("Select an item to view its content")
            self.query_one("#viewer-title").update("[b]Content Viewer[/b]")
            return

        self.query_one("#viewer-title").update(f"[b]Content Viewer - {item.description}[/b]")

        try:
            content = self.format_content(item)
            self.query_one("#content-display", Static).update(content)
        except Exception as e:
            self.query_one("#content-display", Static).update(f"Error loading content: {str(e)}")

    def format_content(self, item: VaultItem) -> str:
        """Format the content based on the item type"""
        try:
            from maestro.ui_facade.vault import get_item_content
            content = get_item_content(item.id)

            if item.subtype == "json":
                try:
                    parsed = json.loads(content)
                    return json.dumps(parsed, indent=2)
                except json.JSONDecodeError:
                    pass  # If it's not valid JSON, just return as text

            # For diff files, return content as is
            # In a real implementation, we'd add syntax highlighting for diffs
            return content
        except Exception as e:
            return f"Error reading content: {str(e)}"


class MetadataPane(Vertical):
    """Right panel for metadata and actions"""

    def __init__(self) -> None:
        super().__init__()
        self.current_item: Optional[VaultItem] = None

    def compose(self) -> ComposeResult:
        yield Label("[b]Metadata & Actions[/b]", classes="metadata-title")
        yield Vertical(
            Label("Path: ", id="meta-path", classes="meta-field"),
            Label("Size: ", id="meta-size", classes="meta-field"),
            Label("Created: ", id="meta-created", classes="meta-field"),
            Label("Origin: ", id="meta-origin", classes="meta-field"),
            Label("Type: ", id="meta-type", classes="meta-field"),
            id="metadata-fields"
        )

        yield Vertical(
            Label("[b]Actions[/b]", classes="actions-title"),
            Button("Copy to Clipboard", id="action-copy", variant="primary", classes="action-item"),
            Button("Open Directory", id="action-open-dir", variant="default", classes="action-item"),
            Button("Export Item", id="action-export", variant="success", classes="action-item"),
            Button("Show Related", id="action-related", variant="default", classes="action-item"),
            id="actions-list"
        )

    def set_item(self, item: Optional[VaultItem]) -> None:
        """Update metadata display for the given item"""
        self.current_item = item
        if item is None:
            # Clear all metadata fields
            for widget_id in ["meta-path", "meta-size", "meta-created", "meta-origin", "meta-type"]:
                self.query_one(f"#{widget_id}", Label).update("")
            return

        # Update metadata fields
        self.query_one("#meta-path", Label).update(f"Path: {item.path}")
        size_mb = item.size / (1024 * 1024) if item.size > 1024 * 1024 else item.size / 1024
        size_unit = "MB" if item.size > 1024 * 1024 else "KB"
        self.query_one("#meta-size", Label).update(f"Size: {size_mb:.1f}{size_unit}")
        self.query_one("#meta-created", Label).update(f"Created: {item.timestamp}")
        self.query_one("#meta-origin", Label).update(f"Origin: {item.origin}")
        self.query_one("#meta-type", Label).update(f"Type: {item.source_type} - {item.subtype}")


class VaultScreen(Screen):
    """Vault screen of the Maestro TUI with four-panel layout."""

    def compose(self) -> ComposeResult:
        """Create child widgets for the vault screen."""
        yield Header()

        with Horizontal(id="vault-layout"):
            with Vertical(id="source-selector-container", classes="panel"):
                yield SourceSelector()

            with Vertical(id="item-list-container", classes="panel"):
                yield ItemList()

            with Vertical(id="viewer-container", classes="panel"):
                yield ViewerPane()

            with Vertical(id="metadata-container", classes="panel"):
                yield MetadataPane()

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the vault screen."""
        # Load initial items
        self.load_items()

        # Set up event bindings
        self._setup_event_bindings()

    def _setup_event_bindings(self) -> None:
        """Set up event bindings for the vault screen."""
        # Bind click events for source type selectors
        for src_type in get_available_source_types():
            try:
                widget = self.query_one(f"#src-{src_type}", Label)
                widget.styles.cursor = "pointer"
                widget.on("click", lambda w=widget, st=src_type: self._toggle_source_type(st))
            except Exception:
                pass  # Widget might not exist if query fails

        # Bind click events for subsystem selectors
        for subsystem in get_available_subsystems():
            try:
                widget = self.query_one(f"#sub-{subsystem}", Label)
                widget.styles.cursor = "pointer"
                widget.on("click", lambda w=widget, sb=subsystem: self._toggle_subsystem(sb))
            except Exception:
                pass  # Widget might not exist if query fails

        # Bind time range selectors
        try:
            time_all = self.query_one("#time-all", Label)
            time_all.styles.cursor = "pointer"
            time_all.on("click", lambda: self._set_time_range("all"))
        except Exception:
            pass

        try:
            time_recent = self.query_one("#time-recent", Label)
            time_recent.styles.cursor = "pointer"
            time_recent.on("click", lambda: self._set_time_range("recent"))
        except Exception:
            pass

        # Bind search input
        try:
            search_input = self.query_one("#item-search", Input)
            search_input.on("changed", self._on_search_changed)
        except Exception:
            pass

        # Bind action buttons
        try:
            copy_btn = self.query_one("#action-copy", Button)
            copy_btn.on("click", self._copy_to_clipboard)
        except Exception:
            pass

        try:
            open_dir_btn = self.query_one("#action-open-dir", Button)
            open_dir_btn.on("click", self._open_directory)
        except Exception:
            pass

        try:
            export_btn = self.query_one("#action-export", Button)
            export_btn.on("click", self._export_item)
        except Exception:
            pass

        try:
            related_btn = self.query_one("#action-related", Button)
            related_btn.on("click", self._show_related)
        except Exception:
            pass

    def _toggle_source_type(self, source_type: str) -> None:
        """Toggle selection of a source type."""
        selector = self.query_one(SourceSelector)
        if source_type in selector.selected_source_types:
            selector.selected_source_types.remove(source_type)
            # Update the label to show unchecked
            label = self.query_one(f"#src-{source_type}", Label)
            label.update(f"☐ {source_type}")
        else:
            selector.selected_source_types.append(source_type)
            # Update the label to show checked
            label = self.query_one(f"#src-{source_type}", Label)
            label.update(f"☑ {source_type}")

        # Reload items based on new filters
        self.load_items()

    def _toggle_subsystem(self, subsystem: str) -> None:
        """Toggle selection of a subsystem."""
        selector = self.query_one(SourceSelector)
        if subsystem in selector.selected_subsystems:
            selector.selected_subsystems.remove(subsystem)
            # Update the label to show unchecked
            label = self.query_one(f"#sub-{subsystem}", Label)
            label.update(f"☐ {subsystem}")
        else:
            selector.selected_subsystems.append(subsystem)
            # Update the label to show checked
            label = self.query_one(f"#sub-{subsystem}", Label)
            label.update(f"☑ {subsystem}")

        # Reload items based on new filters
        self.load_items()

    def _set_time_range(self, time_range: str) -> None:
        """Set the time range filter."""
        selector = self.query_one(SourceSelector)
        selector.time_range = time_range

        # Update both time labels
        all_label = self.query_one("#time-all", Label)
        recent_label = self.query_one("#time-recent", Label)

        if time_range == "all":
            all_label.update("☑ All")
            recent_label.update("☐ Recent")
        else:
            all_label.update("☐ All")
            recent_label.update("☑ Recent")

        # Reload items based on new filters
        self.load_items()

    def _on_search_changed(self, event) -> None:
        """Handle search input changes."""
        item_list = self.query_one(ItemList)
        item_list.search_query = event.value
        self.load_items()

    @work(thread=True)
    def load_items(self) -> None:
        """Load items based on current filters (in a separate thread to avoid UI blocking)."""
        selector = self.query_one(SourceSelector)
        item_list = self.query_one(ItemList)

        # Create filter object
        vault_filter = VaultFilter(
            source_types=selector.selected_source_types if selector.selected_source_types else None,
            subsystems=selector.selected_subsystems if selector.selected_subsystems else None,
            time_range=selector.time_range,
            search_text=item_list.search_query if item_list.search_query else None
        )

        # Get items from facade
        items = list_items(vault_filter)

        # Update the UI on the main thread
        self.call_from_thread(self._update_item_list, items)

    def _update_item_list(self, items: List[VaultItem]) -> None:
        """Update the item list with new items."""
        item_list = self.query_one(ItemList)
        item_list.set_items(items)

        # Add click handlers for the list items
        for item in items:
            try:
                list_item = self.query_one(f"#item-{item.id}", ListItem)
                list_item.on("click", lambda i=item: self._on_item_selected(i))
            except Exception:
                pass  # Item may have been removed or changed

    def _on_item_selected(self, item: VaultItem) -> None:
        """Handle selection of an item in the list."""
        # Update viewer and metadata panes
        viewer = self.query_one(ViewerPane)
        metadata = self.query_one(MetadataPane)

        viewer.set_item(item)
        metadata.set_item(item)

    def _copy_to_clipboard(self) -> None:
        """Copy the current item's content to clipboard."""
        viewer = self.query_one(ViewerPane)
        if viewer.current_item:
            content = viewer.format_content(viewer.current_item)
            # In a real implementation, we'd copy to clipboard
            # For now, we'll just print to console
            print(f"Content copied to clipboard: {len(content)} characters")

    def _open_directory(self) -> None:
        """Open the directory containing the current item."""
        metadata = self.query_one(MetadataPane)
        if metadata.current_item:
            import os
            directory = os.path.dirname(metadata.current_item.path)
            # In a real implementation, we'd open the file manager
            print(f"Opening directory: {directory}")

    def _export_item(self) -> None:
        """Export the current item."""
        metadata = self.query_one(MetadataPane)
        if metadata.current_item:
            from maestro.ui_facade.vault import export_items
            path = export_items([metadata.current_item.id])
            print(f"Item exported to: {path}")

    def _show_related(self) -> None:
        """Show related items for the current item."""
        metadata = self.query_one(MetadataPane)
        if metadata.current_item:
            from maestro.ui_facade.vault import find_related
            related_items = find_related(metadata.current_item.id)
            print(f"Found {len(related_items)} related items")
            # In a real implementation, we'd display these in a separate view
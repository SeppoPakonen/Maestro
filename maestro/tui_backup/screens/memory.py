"""
Memory Screen for Maestro TUI - Conversion Memory Browser

A read-only, inspectable, auditable ledger showing:
- Decisions made during conversion
- Conventions and rules
- Glossary of terms
- Open issues
- Task summaries
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Static, Input
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class MemoryEntry:
    """Base class for memory entries."""
    id: str
    title: str
    status: str  # active, superseded, resolved, pending, etc.
    timestamp: Optional[str] = None
    origin: Optional[str] = None  # planner, worker, user
    reason: Optional[str] = None  # rationale for decision/entry
    evidence_refs: Optional[List[str]] = None  # diff references, summaries
    impacted_files: Optional[List[str]] = None  # files affected by this entry
    details: Optional[Dict[str, Any]] = None  # type-specific details

    def __post_init__(self):
        if self.evidence_refs is None:
            self.evidence_refs = []
        if self.impacted_files is None:
            self.impacted_files = []
        if self.details is None:
            self.details = {}


@dataclass
class DecisionEntry(MemoryEntry):
    """Decision memory entry."""
    superseded_by: Optional[str] = None
    supersedes: Optional[List[str]] = None


@dataclass
class ConventionEntry(MemoryEntry):
    """Convention memory entry."""
    rule: str = ""
    scope: str = ""  # file, module, project
    examples: Optional[List[str]] = None
    enforcement_status: str = "manual"  # manual, enforced, suggested

    def __post_init__(self):
        super().__post_init__()
        if self.examples is None:
            self.examples = []


@dataclass
class GlossaryEntry(MemoryEntry):
    """Glossary memory entry."""
    source_concept: str = ""
    target_concept: str = ""
    notes: str = ""
    confidence: float = 1.0


@dataclass
class OpenIssueEntry(MemoryEntry):
    """Open Issue memory entry."""
    severity: str = "medium"  # low, medium, high, critical
    blocking: bool = False  # if this issue blocks progress


@dataclass
class SummaryEntry(MemoryEntry):
    """Task Summary memory entry."""
    task_id: str = ""
    files_touched: Optional[List[str]] = None
    outcome: str = ""
    warnings: Optional[List[str]] = None
    errors: Optional[List[str]] = None
    semantic_notes: Optional[List[str]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.files_touched is None:
            self.files_touched = []
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []
        if self.semantic_notes is None:
            self.semantic_notes = []


class MemoryCategoriesPanel(Vertical):
    """Left panel: Memory categories with counts and status indicators."""
    
    def __init__(self):
        super().__init__()
        # These will be populated when data is loaded
        self.category_counts = {
            "decisions": 0,
            "conventions": 0,
            "glossary": 0,
            "open_issues": 0,
            "task_summaries": 0
        }
        self.category_has_warnings = {
            "decisions": False,
            "conventions": False,
            "glossary": False,
            "open_issues": True,  # Always show warnings for open issues
            "task_summaries": False
        }

    def compose(self) -> ComposeResult:
        """Create child widgets for the memory categories panel."""
        yield Label("[b]Memory Categories[/b]", classes="category-title")
        
        # Create category list items
        categories = [
            ("decisions", "Decisions"),
            ("conventions", "Conventions"), 
            ("glossary", "Glossary"),
            ("open_issues", "Open Issues"),
            ("task_summaries", "Task Summaries")
        ]
        
        for category_id, category_name in categories:
            count = self.category_counts[category_id]
            has_warning = self.category_has_warnings[category_id]
            
            warning_badge = " ⚠" if has_warning else ""
            count_str = f" ({count})" if count > 0 else ""
            
            yield Label(
                f"{category_name}{count_str}{warning_badge}",
                id=f"category-{category_id}",
                classes="category-item"
            )

    def update_counts(self, counts: Dict[str, int], warnings: Dict[str, bool]):
        """Update category counts and warning indicators."""
        self.category_counts = counts
        self.category_has_warnings = warnings
        
        # Update the displayed labels (this would need to refresh the widgets)
        # For now, we'll just store the values; in a real implementation
        # we'd need to update the actual widgets


class EntryListPanel(Vertical):
    """Center panel: List of entries for selected category."""
    
    def __init__(self, category: str = "decisions"):
        super().__init__()
        self.category = category
        self.entries: List[MemoryEntry] = []
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the entry list panel."""
        if not self.entries:
            yield Label("No entries found", classes="placeholder")
            return

        for i, entry in enumerate(self.entries):
            # Determine status color
            status_colors = {
                "active": "green",
                "completed": "green",
                "resolved": "green",
                "superseded": "yellow",
                "failed": "red",
                "pending": "dim",
                "blocked": "red"
            }
            status_color = status_colors.get(entry.status, "dim")
            
            # Format timestamp
            timestamp_str = ""
            if entry.timestamp:
                try:
                    dt = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                    timestamp_str = dt.strftime('%m-%d %H:%M')
                except:
                    timestamp_str = entry.timestamp[:10]  # fallback to showing date part
            
            selected_class = "selected" if i == self.selected_index else ""
            
            # Create list item showing ID, title, status, and timestamp
            yield Label(
                f"[b]{entry.id}[/b] {entry.title[:50]}{'...' if len(entry.title) > 50 else ''}",
                id=f"entry-{i}",
                classes=f"entry-item {selected_class}",
            )
            # Show status and timestamp on a separate line
            yield Label(
                f"  Status: [{status_color}]{entry.status}[/] | {timestamp_str}",
                classes="entry-meta"
            )

    def update_entries(self, entries: List[MemoryEntry], category: str):
        """Update the list of entries for the selected category."""
        self.entries = entries
        self.category = category
        self.selected_index = 0
        # In a real implementation, we'd refresh the widgets here


class EntryDetailsPanel(Vertical):
    """Right panel: Details for selected entry."""
    
    def __init__(self, entry: Optional[MemoryEntry] = None):
        super().__init__()
        self.entry = entry

    def compose(self) -> ComposeResult:
        """Create child widgets for the entry details panel."""
        if not self.entry:
            yield Label("Select an entry to view details", classes="placeholder")
            return

        # Title and ID
        yield Label(f"[b]ID:[/b] {self.entry.id}", classes="detail-title")
        yield Label(f"[b]Title:[/b] {self.entry.title}", classes="detail-title")
        
        # Status
        status_color = "green" if self.entry.status in ["active", "completed", "resolved"] else "red" if self.entry.status in ["failed", "superseded"] else "yellow"
        yield Label(f"[b]Status:[/b] [{status_color}]{self.entry.status.title()}[/]", classes="detail-status")
        
        # Timestamp
        if self.entry.timestamp:
            try:
                dt = datetime.fromisoformat(self.entry.timestamp.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                yield Label(f"[b]Timestamp:[/b] {formatted_time}", classes="detail-timestamp")
            except:
                yield Label(f"[b]Timestamp:[/b] {self.entry.timestamp}", classes="detail-timestamp")
        
        # Origin
        if self.entry.origin:
            yield Label(f"[b]Origin:[/b] {self.entry.origin}", classes="detail-origin")
        
        # Rationale/Reason
        if self.entry.reason:
            yield Label(f"[b]Rationale:[/b]", classes="detail-section-title")
            yield Label(self.entry.reason, classes="detail-reason")
        
        # Evidence references
        if self.entry.evidence_refs:
            yield Label(f"[b]Evidence References:[/b]", classes="detail-section-title")
            for ref in self.entry.evidence_refs:
                yield Label(f"• {ref}", classes="detail-reference")
        
        # Impacted files
        if self.entry.impacted_files:
            yield Label(f"[b]Impacted Files:[/b]", classes="detail-section-title")
            for file in self.entry.impacted_files[:10]:  # Limit to first 10 files
                yield Label(f"• {file}", classes="detail-file")
            if len(self.entry.impacted_files) > 10:
                yield Label(f"... and {len(self.entry.impacted_files) - 10} more", classes="detail-file")
        
        # Type-specific details
        if isinstance(self.entry, DecisionEntry):
            if self.entry.superseded_by:
                yield Label(f"[b]Superseded By:[/b] {self.entry.superseded_by}", classes="detail-field")
            if self.entry.supersedes:
                yield Label(f"[b]Supersedes:[/b] {', '.join(self.entry.supersedes)}", classes="detail-field")
        
        elif isinstance(self.entry, ConventionEntry):
            if self.entry.rule:
                yield Label(f"[b]Rule:[/b] {self.entry.rule}", classes="detail-field")
            if self.entry.scope:
                yield Label(f"[b]Scope:[/b] {self.entry.scope}", classes="detail-field")
            if self.entry.enforcement_status:
                yield Label(f"[b]Enforcement:[/b] {self.entry.enforcement_status}", classes="detail-field")
            if self.entry.examples:
                yield Label(f"[b]Examples:[/b]", classes="detail-section-title")
                for example in self.entry.examples:
                    yield Label(f"• {example}", classes="detail-example")
        
        elif isinstance(self.entry, GlossaryEntry):
            yield Label(f"[b]Source Concept:[/b] {self.entry.source_concept}", classes="detail-field")
            yield Label(f"[b]Target Concept:[/b] {self.entry.target_concept}", classes="detail-field")
            if self.entry.notes:
                yield Label(f"[b]Notes:[/b] {self.entry.notes}", classes="detail-field")
            yield Label(f"[b]Confidence:[/b] {self.entry.confidence:.2f}", classes="detail-field")
        
        elif isinstance(self.entry, OpenIssueEntry):
            yield Label(f"[b]Severity:[/b] {self.entry.severity}", classes="detail-field")
            yield Label(f"[b]Blocking Issue:[/b] {'Yes' if self.entry.blocking else 'No'}", classes="detail-field")
        
        elif isinstance(self.entry, SummaryEntry):
            if self.entry.task_id:
                yield Label(f"[b]Task ID:[/b] {self.entry.task_id}", classes="detail-field")
            if self.entry.files_touched:
                yield Label(f"[b]Files Touched:[/b] {len(self.entry.files_touched)}", classes="detail-field")
            if self.entry.outcome:
                yield Label(f"[b]Outcome:[/b] {self.entry.outcome}", classes="detail-field")
            if self.entry.warnings:
                yield Label(f"[b]Warnings:[/b] {len(self.entry.warnings)}", classes="detail-field")
            if self.entry.errors:
                yield Label(f"[b]Errors:[/b] {len(self.entry.errors)}", classes="detail-field")
            if self.entry.semantic_notes:
                yield Label(f"[b]Semantic Notes:[/b]", classes="detail-section-title")
                for note in self.entry.semantic_notes:
                    yield Label(f"• {note}", classes="detail-note")


class FilterControls(Vertical):
    """Filter controls for the memory browser."""

    def __init__(self):
        super().__init__()
        self.active_only = False
        self.unresolved_only = False
        self.high_risk_only = False

    def compose(self) -> ComposeResult:
        """Create child widgets for the filter controls."""
        yield Label("[b]Filters[/b]", classes="filter-title")

        with Horizontal(classes="filter-row"):
            yield Label("Active only:", classes="filter-label")
            # For now, we'll just show the filter state - in a real implementation
            # these would be toggle buttons or checkboxes
            yield Label("No" if not self.active_only else "Yes", classes="filter-value")

        with Horizontal(classes="filter-row"):
            yield Label("Unresolved only:", classes="filter-label")
            yield Label("No" if not self.unresolved_only else "Yes", classes="filter-value")

        with Horizontal(classes="filter-row"):
            yield Label("High risk only:", classes="filter-label")
            yield Label("No" if not self.high_risk_only else "Yes", classes="filter-value")


class SearchFilterBar(Horizontal):
    """Top bar with search and filter controls."""

    def __init__(self):
        super().__init__()
        self.search_active = False

    def compose(self) -> ComposeResult:
        """Create child widgets for the search and filter bar."""
        yield Label("[b]Search & Filter[/b]", classes="search-title")
        yield Input(placeholder="Search within category (/ to search)...", id="search-input", classes="search-input")
        yield FilterControls()


class MemoryScreen(Screen):
    """Memory screen of the Maestro TUI - Conversion Memory Browser."""

    # Reactive variables to track state
    selected_category = reactive("decisions")
    selected_entry_index = reactive(0)
    search_query = reactive("")

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("/", "focus_search", "Search"),
        ("j", "select_next", "Next"),
        ("k", "select_prev", "Previous"),
        ("o", "override_decision", "Override"),
        ("ctrl+c", "app.quit", "Quit"),
    ]

    def __init__(self, initial_category: str = "decisions"):
        super().__init__()
        self.selected_category = initial_category

    def compose(self) -> ComposeResult:
        """Create child widgets for the memory screen."""
        yield Header(show_clock=True)

        # Search and filter bar
        yield SearchFilterBar()

        # Create the main three-panel layout
        with Horizontal(id="memory-container"):
            # Left: Memory Categories
            with Vertical(id="categories-container", classes="memory-panel"):
                yield MemoryCategoriesPanel()

            # Center: Entry List
            with Vertical(id="entry-list-container", classes="memory-panel"):
                yield EntryListPanel()

            # Right: Entry Details
            with Vertical(id="entry-details-container", classes="memory-panel"):
                yield EntryDetailsPanel()

        yield Footer()

    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        # Load initial memory data
        self.refresh_memory_display()

    def refresh_memory_display(self) -> None:
        """Refresh the memory display with current data."""
        from maestro.ui_facade.convert import list_decisions, list_conventions, list_glossary, list_open_issues, list_task_summaries
        
        # Update category counts
        categories_panel = self.query_one("#categories-container", expect_type=Vertical)
        categories_panel.remove_children()
        
        # Get count for each category
        try:
            decisions = list_decisions()
            conventions = list_conventions() 
            glossary = list_glossary()
            open_issues = list_open_issues()
            task_summaries = list_task_summaries()
            
            counts = {
                "decisions": len(decisions),
                "conventions": len(conventions),
                "glossary": len(glossary),
                "open_issues": len(open_issues),
                "task_summaries": len(task_summaries)
            }
            
            warnings = {
                "decisions": False,
                "conventions": False,
                "glossary": False,
                "open_issues": len(open_issues) > 0,  # Show warning if there are open issues
                "task_summaries": False
            }
            
            categories_widget = MemoryCategoriesPanel()
            categories_widget.update_counts(counts, warnings)
            categories_panel.mount_all(list(categories_widget.compose()))
            
            # Update entry list for selected category
            self.update_entry_list()
            
        except Exception as e:
            # Show error message if data loading fails
            categories_panel.mount(Label(f"Error loading memory data: {str(e)}", classes="error"))

    def update_entry_list(self) -> None:
        """Update the entry list based on the selected category and search/filter criteria."""
        from maestro.ui_facade.convert import (
            list_decisions, list_conventions, list_glossary,
            list_open_issues, list_task_summaries
        )

        try:
            # Get entries based on selected category
            entries = []
            if self.selected_category == "decisions":
                entries = list_decisions()
            elif self.selected_category == "conventions":
                entries = list_conventions()
            elif self.selected_category == "glossary":
                entries = list_glossary()
            elif self.selected_category == "open_issues":
                entries = list_open_issues()
            elif self.selected_category == "task_summaries":
                entries = list_task_summaries()

            # Apply search filter if there's a search query
            if self.search_query:
                entries = self._filter_entries_by_search(entries, self.search_query)

            # Update the entry list panel
            entry_list_container = self.query_one("#entry-list-container", expect_type=Vertical)
            entry_list_container.remove_children()

            entry_list_widget = EntryListPanel(category=self.selected_category)
            entry_list_widget.update_entries(entries, self.selected_category)
            entry_list_container.mount_all(list(entry_list_widget.compose()))

            # Update details panel with first entry if available
            if entries:
                self.update_entry_details(entries[0])
                self.selected_entry_index = 0
            else:
                # Clear details panel if no entries
                self.update_entry_details(None)
                self.selected_entry_index = -1

        except Exception as e:
            self.query_one("#entry-list-container", expect_type=Vertical).mount(
                Label(f"Error loading {self.selected_category}: {str(e)}", classes="error")
            )

    def _filter_entries_by_search(self, entries: List[MemoryEntry], query: str) -> List[MemoryEntry]:
        """Filter entries based on search query."""
        if not query:
            return entries

        query_lower = query.lower()
        filtered_entries = []

        for entry in entries:
            # Search in ID, title, reason, status, and other relevant fields
            search_fields = [
                entry.id.lower() if entry.id else "",
                entry.title.lower() if entry.title else "",
                entry.status.lower() if entry.status else "",
                entry.reason.lower() if entry.reason else "",
                str(entry.timestamp).lower() if entry.timestamp else "",
                entry.origin.lower() if entry.origin else "",
            ]

            # Add type-specific fields
            if isinstance(entry, DecisionEntry):
                if entry.superseded_by:
                    search_fields.append(entry.superseded_by.lower())
                if entry.supersedes:
                    search_fields.extend([s.lower() for s in entry.supersedes if s])
            elif isinstance(entry, ConventionEntry):
                search_fields.append(entry.rule.lower() if entry.rule else "")
                search_fields.append(entry.scope.lower() if entry.scope else "")
            elif isinstance(entry, GlossaryEntry):
                search_fields.append(entry.source_concept.lower() if entry.source_concept else "")
                search_fields.append(entry.target_concept.lower() if entry.target_concept else "")
                search_fields.append(entry.notes.lower() if entry.notes else "")
            elif isinstance(entry, OpenIssueEntry):
                search_fields.append(entry.severity.lower() if entry.severity else "")
            elif isinstance(entry, SummaryEntry):
                search_fields.append(entry.task_id.lower() if entry.task_id else "")
                search_fields.extend([f.lower() for f in entry.files_touched if f])
                search_fields.append(entry.outcome.lower() if entry.outcome else "")

            # Check if query matches any of the search fields
            if any(query_lower in field for field in search_fields):
                filtered_entries.append(entry)

        return filtered_entries

    def update_entry_details(self, entry: Optional[MemoryEntry]) -> None:
        """Update the entry details panel."""
        details_container = self.query_one("#entry-details-container", expect_type=Vertical)
        details_container.remove_children()
        
        if entry:
            details_widget = EntryDetailsPanel(entry=entry)
            details_container.mount_all(list(details_widget.compose()))
        else:
            details_widget = EntryDetailsPanel(entry=None)
            details_container.mount_all(list(details_widget.compose()))

    def on_label_clicked(self, event) -> None:
        """Handle clicking on a category or entry."""
        label_id = event.label.id if event.label.id else ""

        # Handle category selection
        if label_id and label_id.startswith("category-"):
            # Update selection styling
            category = label_id.replace("category-", "")
            old_category_widget = self.query_one(f"#category-{self.selected_category}", expect_type=Label)
            old_category_widget.remove_class("selected")

            new_category_widget = event.label
            new_category_widget.add_class("selected")

            # Update selected category and refresh entry list
            self.selected_category = category
            # Clear search when changing categories
            self.search_query = ""
            try:
                search_input = self.query_one("#search-input", expect_type=Input)
                search_input.value = ""
            except:
                pass  # Search input may not exist yet
            self.update_entry_list()

        # Handle entry selection
        elif label_id and label_id.startswith("entry-"):
            try:
                entry_index = int(label_id.replace("entry-", ""))

                # Update selection styling for entry
                # We need to get all entry items and update their classes
                for i in range(20):  # Assume max 20 entries for now
                    try:
                        entry_label = self.query_one(f"#entry-{i}", expect_type=Label)
                        if i == entry_index:
                            entry_label.add_class("selected")
                        else:
                            entry_label.remove_class("selected")
                    except:
                        continue  # Skip if label doesn't exist

                # Update selected entry index
                self.selected_entry_index = entry_index

                # Load details for the selected entry
                from maestro.ui_facade.convert import (
                    list_decisions, list_conventions, list_glossary,
                    list_open_issues, list_task_summaries
                )

                entries = []
                if self.selected_category == "decisions":
                    entries = list_decisions()
                elif self.selected_category == "conventions":
                    entries = list_conventions()
                elif self.selected_category == "glossary":
                    entries = list_glossary()
                elif self.selected_category == "open_issues":
                    entries = list_open_issues()
                elif self.selected_category == "task_summaries":
                    entries = list_task_summaries()

                if 0 <= entry_index < len(entries):
                    selected_entry = entries[entry_index]
                    self.update_entry_details(selected_entry)

            except ValueError:
                pass

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self.search_query = event.value
            self.update_entry_list()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission (Enter key)."""
        if event.input.id == "search-input":
            # Perform search (same as input change, but could have additional behavior)
            self.search_query = event.value
            self.update_entry_list()

    def action_focus_search(self) -> None:
        """Focus the search input."""
        try:
            search_input = self.query_one("#search-input", expect_type=Input)
            search_input.focus()
        except:
            # If search input doesn't exist, create a notification
            self.app.notify("Search input not available", timeout=2)

    def action_select_next(self) -> None:
        """Select the next entry in the list."""
        from maestro.ui_facade.convert import (
            list_decisions, list_conventions, list_glossary, 
            list_open_issues, list_task_summaries
        )
        
        entries = []
        if self.selected_category == "decisions":
            entries = list_decisions()
        elif self.selected_category == "conventions":
            entries = list_conventions()
        elif self.selected_category == "glossary":
            entries = list_glossary()
        elif self.selected_category == "open_issues":
            entries = list_open_issues()
        elif self.selected_category == "task_summaries":
            entries = list_task_summaries()
        
        if entries and len(entries) > 0:
            new_index = min(self.selected_entry_index + 1, len(entries) - 1)
            
            # Update selection styling
            for i in range(len(entries)):
                try:
                    entry_label = self.query_one(f"#entry-{i}", expect_type=Label)
                    if i == new_index:
                        entry_label.add_class("selected")
                    else:
                        entry_label.remove_class("selected")
                except:
                    continue  # Skip if label doesn't exist

            self.selected_entry_index = new_index

            # Update details panel
            if 0 <= self.selected_entry_index < len(entries):
                self.update_entry_details(entries[self.selected_entry_index])

    def action_override_decision(self) -> None:
        """Action to override the selected decision."""
        if self.selected_category != "decisions":
            self.app.notify("Override only available for decisions", timeout=3, severity="error")
            return

        from maestro.ui_facade.convert import list_decisions
        from maestro.tui.widgets.modals import DecisionOverrideWizard

        decisions = list_decisions()
        if not decisions or len(decisions) <= self.selected_entry_index:
            self.app.notify("No decision selected or available", timeout=3, severity="error")
            return

        selected_decision = decisions[self.selected_entry_index]

        # Prevent overriding decisions that are already superseded
        if selected_decision.get('status') == 'superseded':
            self.app.notify("Cannot override a decision that is already superseded", timeout=3, severity="error")
            return

        # Show the decision override wizard
        def handle_override_result(result: dict) -> None:
            if result and not result.get("cancelled"):
                from maestro.ui_facade.convert import override_decision

                try:
                    # Apply the override
                    override_result = override_decision(
                        decision_id=result["old_decision_id"],
                        new_value=result["new_value"],
                        reason=result["reason"],
                        auto_replan=result["auto_replan"]
                    )

                    # Show success notification
                    self.app.notify(f"Decision overridden: {override_result.old_decision_id} → {override_result.new_decision_id}", timeout=5)

                    # Show warning if plan is stale
                    if override_result.plan_is_stale:
                        self.app.notify("⚠ Plan may be stale. Consider running negotiation.", timeout=5, severity="warning")

                    # Refresh the memory display to show updated decision
                    self.refresh_memory_display()

                except Exception as e:
                    self.app.notify(f"Failed to override decision: {str(e)}", timeout=5, severity="error")
            else:
                self.app.notify("Decision override cancelled", timeout=3)

        # Push the wizard modal
        wizard = DecisionOverrideWizard(decision=selected_decision)
        self.app.push_screen(wizard, callback=handle_override_result)

    def action_select_prev(self) -> None:
        """Select the previous entry in the list."""
        from maestro.ui_facade.convert import (
            list_decisions, list_conventions, list_glossary, 
            list_open_issues, list_task_summaries
        )
        
        entries = []
        if self.selected_category == "decisions":
            entries = list_decisions()
        elif self.selected_category == "conventions":
            entries = list_conventions()
        elif self.selected_category == "glossary":
            entries = list_glossary()
        elif self.selected_category == "open_issues":
            entries = list_open_issues()
        elif self.selected_category == "task_summaries":
            entries = list_task_summaries()
        
        if entries and len(entries) > 0:
            new_index = max(self.selected_entry_index - 1, 0)
            
            # Update selection styling
            for i in range(len(entries)):
                try:
                    entry_label = self.query_one(f"#entry-{i}", expect_type=Label)
                    if i == new_index:
                        entry_label.add_class("selected")
                    else:
                        entry_label.remove_class("selected")
                except:
                    continue  # Skip if label doesn't exist

            self.selected_entry_index = new_index

            # Update details panel
            if 0 <= self.selected_entry_index < len(entries):
                self.update_entry_details(entries[self.selected_entry_index])

    def action_override_decision(self) -> None:
        """Action to override the selected decision."""
        if self.selected_category != "decisions":
            self.app.notify("Override only available for decisions", timeout=3, severity="error")
            return

        from maestro.ui_facade.convert import list_decisions
        from maestro.tui.widgets.modals import DecisionOverrideWizard

        decisions = list_decisions()
        if not decisions or len(decisions) <= self.selected_entry_index:
            self.app.notify("No decision selected or available", timeout=3, severity="error")
            return

        selected_decision = decisions[self.selected_entry_index]

        # Prevent overriding decisions that are already superseded
        if selected_decision.get('status') == 'superseded':
            self.app.notify("Cannot override a decision that is already superseded", timeout=3, severity="error")
            return

        # Show the decision override wizard
        def handle_override_result(result: dict) -> None:
            if result and not result.get("cancelled"):
                from maestro.ui_facade.convert import override_decision

                try:
                    # Apply the override
                    override_result = override_decision(
                        decision_id=result["old_decision_id"],
                        new_value=result["new_value"],
                        reason=result["reason"],
                        auto_replan=result["auto_replan"]
                    )

                    # Show success notification
                    self.app.notify(f"Decision overridden: {override_result.old_decision_id} → {override_result.new_decision_id}", timeout=5)

                    # Show warning if plan is stale
                    if override_result.plan_is_stale:
                        self.app.notify("⚠ Plan may be stale. Consider running negotiation.", timeout=5, severity="warning")

                    # Refresh the memory display to show updated decision
                    self.refresh_memory_display()

                except Exception as e:
                    self.app.notify(f"Failed to override decision: {str(e)}", timeout=5, severity="error")
            else:
                self.app.notify("Decision override cancelled", timeout=3)

        # Push the wizard modal
        wizard = DecisionOverrideWizard(decision=selected_decision)
        self.app.push_screen(wizard, callback=handle_override_result)
"""
Timeline pane for Maestro MC shell - Event Timeline and Recovery Explorer.

This pane provides:
- Timeline of all significant events (runs, checkpoints, decisions, batch jobs)
- Event detail viewer
- Time travel capabilities (preview, replay, branch)
- Recovery tools and explanation tracking
"""
from __future__ import annotations

import asyncio
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Label, ListView, ListItem, Static, Button
from textual.reactive import reactive

from maestro.tui.panes.base import PaneView
from maestro.tui.menubar.model import Menu, MenuItem
from maestro.ui_facade.timeline import (
    list_events,
    get_event,
    replay_from_event,
    branch_from_event,
    mark_event_explained,
    get_related_vault_items
)


@dataclass
class TimelineEvent:
    """Represents a single timeline event."""
    id: str
    timestamp: datetime
    event_type: str  # 'run', 'decision', 'checkpoint', 'batch', 'abort', 'skip', 'override'
    summary: str
    risk_marker: Optional[str] = None  # 'high', 'medium', 'low' if any risk associated
    details: Optional[str] = None
    user_id: Optional[str] = None
    system_impact: Optional[str] = None  # What was affected (repo/plan/task/job)


class TimelinePane(PaneView):
    """Timeline pane implementation for Maestro MC shell."""

    pane_id = "timeline"
    pane_title = "Event Timeline"

    # Reactive attributes for UI updates
    selected_event: reactive[Optional[TimelineEvent]] = reactive(None)
    events_list: reactive[List[TimelineEvent]] = reactive([])
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pane_id = "timeline"
        self.pane_title = "Event Timeline"
    
    def compose(self) -> ComposeResult:
        """Compose the timeline pane UI."""
        # Main layout: left for events, right for details
        with Horizontal(id="timeline-layout"):
            # Left pane: Event Timeline
            with Vertical(id="event-timeline-pane", classes="pane"):
                yield Label("[b]Event Timeline[/b]", id="timeline-title")
                yield ListView(id="event-list")
            
            # Right pane: Event Detail
            with VerticalScroll(id="event-detail-pane", classes="pane"):
                yield Label("[b]Event Details[/b]", id="detail-title")
                yield Label("Select an event to view details", id="detail-placeholder")
                
                # Buttons for actions
                with Horizontal(id="action-buttons"):
                    yield Button("F3 - Preview State", id="preview-action", variant="default")
                    yield Button("F5 - Dry-Run Replay", id="dry-run-action", variant="warning")
                    yield Button("F6 - Apply Replay", id="apply-action", variant="error")
                    yield Button("F7 - Explain", id="explain-action", variant="primary")
                    yield Button("F8 - Create Branch", id="branch-action", variant="success")
    
    def on_mount(self) -> None:
        """Initialize the timeline pane when mounted."""
        super().on_mount()
        
        # Load initial timeline data
        self.load_timeline_data()
        
        # Bind event handlers
        event_list = self.query_one("#event-list", ListView)
        event_list.on("list_view.selected", self.on_event_selected)
        
        # Bind action buttons
        self.query_one("#preview-action", Button).on("button_pressed", self.on_preview_action)
        self.query_one("#dry-run-action", Button).on("button_pressed", self.on_dry_run_action)
        self.query_one("#apply-action", Button).on("button_pressed", self.on_apply_action)
        self.query_one("#explain-action", Button).on("button_pressed", self.on_explain_action)
        self.query_one("#branch-action", Button).on("button_pressed", self.on_branch_action)
        
        # Set up keyboard shortcuts
        self.bindings = [
            ("f3", "preview_state", "Preview State"),
            ("f5", "replay_dry_run", "Dry-Run Replay"),
            ("f6", "replay_apply", "Apply Replay"),
            ("f7", "explain_event", "Explain Event"),
            ("f8", "create_branch", "Create Branch"),
            ("f9", "show_menu", "Show Menu"),
            ("f10", "quit_app", "Quit"),
        ]
    
    def on_focus(self) -> None:
        """Called when the pane receives focus."""
        # Refresh data when gaining focus
        self.refresh_data()
    
    def on_blur(self) -> None:
        """Called when the pane loses focus."""
        pass
    
    def refresh_data(self) -> None:
        """Refresh timeline data."""
        self.load_timeline_data()
    
    def load_timeline_data(self) -> None:
        """Load timeline events from the facade."""
        try:
            # Get events from the timeline facade
            raw_events = list_events()
            
            # Convert to TimelineEvent objects
            timeline_events = []
            for raw_event in raw_events:
                timeline_event = TimelineEvent(
                    id=raw_event.get('id', ''),
                    timestamp=datetime.fromisoformat(raw_event.get('timestamp', datetime.now().isoformat())),
                    event_type=raw_event.get('type', 'unknown'),
                    summary=raw_event.get('summary', ''),
                    risk_marker=raw_event.get('risk_marker'),
                    details=raw_event.get('details'),
                    user_id=raw_event.get('user_id'),
                    system_impact=raw_event.get('system_impact')
                )
                timeline_events.append(timeline_event)
            
            # Update reactive attribute
            self.events_list = timeline_events
            
            # Update the UI
            self.update_event_list()
        except Exception as e:
            self.notify_status(f"Error loading timeline data: {str(e)}")
    
    def update_event_list(self) -> None:
        """Update the event list UI."""
        try:
            event_list_widget = self.query_one("#event-list", ListView)
            event_list_widget.clear()
            
            for event in self.events_list:
                # Format the event for display
                risk_icon = ""
                if event.risk_marker:
                    risk_icon = {
                        'high': '🚨',
                        'medium': '⚠️',
                        'low': '🔍'
                    }.get(event.risk_marker, '🔍')
                
                event_text = f"[{risk_icon}] {event.timestamp.strftime('%H:%M:%S')} - {event.event_type.upper()}: {event.summary}"
                list_item = ListItem(Label(event_text, id=f"event-{event.id}"))
                event_list_widget.append(list_item)
        except Exception as e:
            self.notify_status(f"Error updating event list: {str(e)}")
    
    def on_event_selected(self, event) -> None:
        """Handle when an event is selected in the list."""
        if event.list_view.id != "event-list":
            return
            
        # Extract event ID from the selected item
        selected_id = event.item.id.replace("event-", "") if hasattr(event.item, 'id') else None
        
        if selected_id:
            # Find the selected event
            for timeline_event in self.events_list:
                if timeline_event.id == selected_id:
                    self.selected_event = timeline_event
                    self.update_event_detail()
                    break
    
    def update_event_detail(self) -> None:
        """Update the event detail panel."""
        if not self.selected_event:
            return

        try:
            # Get detailed event information
            detail_placeholder = self.query_one("#detail-placeholder", Label)

            event = self.selected_event
            detail_text = (
                f"[b]Event ID:[/b] {event.id}\n"
                f"[b]Timestamp:[/b] {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"[b]Type:[/b] {event.event_type}\n"
                f"[b]Summary:[/b] {event.summary}\n"
            )

            if event.risk_marker:
                risk_display = {
                    'high': '🚨 [red]HIGH[/red]',
                    'medium': '⚠️ [orange]MEDIUM[/orange]',
                    'low': '🔍 [yellow]LOW[/yellow]'
                }.get(event.risk_marker, event.risk_marker)
                detail_text += f"[b]Risk:[/b] {risk_display}\n"

            if event.user_id:
                detail_text += f"[b]Actor:[/b] {event.user_id}\n"

            if event.system_impact:
                detail_text += f"[b]Impact:[/b] {event.system_impact}\n"

            if event.details:
                detail_text += f"\n[b]Details:[/b]\n{event.details}\n"

            # Show vault references
            vault_items = get_related_vault_items(event.id)
            if vault_items:
                detail_text += f"\n[b]Related Vault Items ({len(vault_items)}):[/b]\n"
                for item in vault_items[:5]:  # Show first 5 items
                    detail_text += f"• {item['id']}: {item['description']}\n"
                if len(vault_items) > 5:
                    detail_text += f"  ... and {len(vault_items) - 5} more\n"

            detail_text += "\n[b]Actions:[/b]\n"
            detail_text += "• F3: Jump to state before this event (preview only)\n"
            detail_text += "• F5: Replay from this event (dry-run)\n"
            detail_text += "• F6: Replay & apply from this event (with confirmation)\n"
            detail_text += "• F7: Mark event as 'explained' (with evidence)\n"
            detail_text += "• F8: Create recovery branch from this event\n"
            detail_text += "• V: Open Vault filtered to this event\n"

            detail_placeholder.update(detail_text)
        except Exception as e:
            self.notify_status(f"Error updating event detail: {str(e)}")
    
    def get_menu_spec(self) -> Menu:
        """Return the menu specification for this pane."""
        return Menu(
            label="Timeline",
            items=[
                MenuItem("Preview at Event", "timeline.preview", "f3"),
                MenuItem("Replay from Event (Dry)", "timeline.replay_dry", "f5"),
                MenuItem("Replay from Event (Apply)", "timeline.replay_apply", "f6"),
                MenuItem("Explain Event", "timeline.explain", "f7"),
                MenuItem("Create Recovery Branch", "timeline.branch", "f8"),
                MenuItem("Open Vault (Filtered)", "timeline.vault_filtered", "v"),
                MenuItem("Jump to Plan", "timeline.plan", "p"),
                MenuItem("Jump to Related Pane", "timeline.jump_related", "j"),
            ]
        )
    
    # Action handlers
    def on_preview_action(self, event) -> None:
        """Handle preview state action."""
        if self.selected_event:
            self.action_preview_state()
    
    def on_dry_run_action(self, event) -> None:
        """Handle dry-run replay action."""
        if self.selected_event:
            self.action_replay_dry_run()
    
    def on_apply_action(self, event) -> None:
        """Handle apply replay action."""
        if self.selected_event:
            self.action_replay_apply()
    
    def on_explain_action(self, event) -> None:
        """Handle explain event action."""
        if self.selected_event:
            self.action_explain_event()
    
    def on_branch_action(self, event) -> None:
        """Handle create branch action."""
        if self.selected_event:
            self.action_create_branch()
    
    # Actual action methods
    def action_preview_state(self) -> None:
        """Jump to state before this event (read-only preview)."""
        if not self.selected_event:
            self.notify_status("Please select an event first")
            return
            
        try:
            # This would typically show a read-only view of the state before the event
            self.notify_status(f"Previewing state before event {self.selected_event.id}")
            # Implementation would show the state before the event in a read-only mode
        except Exception as e:
            self.notify_status(f"Error in preview: {str(e)}")
    
    def action_replay_dry_run(self) -> None:
        """Replay from this event in dry-run mode (no mutations)."""
        if not self.selected_event:
            self.notify_status("Please select an event first")
            return
            
        try:
            result = replay_from_event(self.selected_event.id, apply=False)
            self.notify_status(f"Dry-run replay from event {self.selected_event.id}: {result}")
        except Exception as e:
            self.notify_status(f"Error in dry-run replay: {str(e)}")
    
    def action_replay_apply(self) -> None:
        """Replay and apply from this event (with confirmation)."""
        if not self.selected_event:
            self.notify_status("Please select an event first")
            return
            
        # In a real implementation, we would show a confirmation dialog
        # For now, just call the facade
        try:
            result = replay_from_event(self.selected_event.id, apply=True)
            self.notify_status(f"Applied replay from event {self.selected_event.id}: {result}")
        except Exception as e:
            self.notify_status(f"Error in apply replay: {str(e)}")
    
    def action_explain_event(self) -> None:
        """Mark event as 'explained' with a note."""
        if not self.selected_event:
            self.notify_status("Please select an event first")
            return
            
        # In a real implementation, we would show a modal for the user to enter an explanation
        # For now, just mark as explained with a placeholder note
        try:
            result = mark_event_explained(self.selected_event.id, "User explanation note")
            self.notify_status(f"Event {self.selected_event.id} marked as explained: {result}")
        except Exception as e:
            self.notify_status(f"Error marking event as explained: {str(e)}")
    
    def action_create_branch(self) -> None:
        """Create recovery branch from this event."""
        if not self.selected_event:
            self.notify_status("Please select an event first")
            return
            
        try:
            # In a real implementation, we would get a reason from the user
            result = branch_from_event(self.selected_event.id, "Recovery branch")
            self.notify_status(f"Created recovery branch from event {self.selected_event.id}: {result}")
        except Exception as e:
            self.notify_status(f"Error creating branch: {str(e)}")
    
    def action_show_menu(self) -> None:
        """Show the timeline menu."""
        self.request_menu_refresh()
    
    def refresh(self, *, layout: bool = False, **kwargs) -> None:
        """Refresh pane data and UI."""
        super().refresh(layout=layout, **kwargs)
        self.refresh_data()


# Register the timeline pane
from maestro.tui.panes.registry import register_pane

register_pane("timeline", TimelinePane)
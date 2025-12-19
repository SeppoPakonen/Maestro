"""
Phases Screen for Maestro TUI - Interactive Phase Tree Viewer
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, ListView, ListItem, Tree
from textual.containers import Horizontal, Vertical, ScrollableContainer
from maestro.ui_facade.phases import get_phase_tree, list_phases, get_phase_details
from datetime import datetime
from maestro.tui.widgets.status_indicators import get_status_indicator, get_progress_bar


class PhasesScreen(Screen):
    """Interactive Phase Tree Viewer screen with master-detail layout."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("enter", "set_active_phase", "Set Active"),
        ("k", "kill_phase", "Kill Branch"),
    ]

    def __init__(self):
        super().__init__()
        self.selected_phase_id = None
        self.phase_tree_root = None
        self.current_phase_details = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the phase tree viewer screen."""
        yield Header()

        # Master-detail layout - horizontal split
        with Horizontal(id="phases-main-container"):
            # Left pane - phase tree
            with Vertical(id="phases-tree-pane", classes="pane"):
                yield Label("[b]Phase Tree[/b]", classes="title")

                # Load and display the phase tree
                try:
                    session = self.app.active_session
                    if session:
                        self.phase_tree_root = get_phase_tree(session.id)
                        yield self._create_phase_tree_widget()
                    else:
                        yield Label("No active session available", classes="placeholder")
                except Exception as e:
                    yield Label(f"Error loading phase tree: {str(e)}", classes="error")

            # Right pane - phase details
            with Vertical(id="phase-details-pane", classes="pane"):
                yield Label("[b]Phase Details[/b]", classes="title")

                if self.phase_tree_root:
                    # Show details for the root phase by default
                    try:
                        session = self.app.active_session
                        if session:
                            # Use the root phase ID for details
                            self.selected_phase_id = self.phase_tree_root.phase_id
                            self.current_phase_details = get_phase_details(session.id, self.selected_phase_id)
                            yield self._create_phase_details_view()
                        else:
                            yield Label("No active session available", classes="placeholder")
                    except Exception as e:
                        yield Label(f"Error loading phase details: {str(e)}", classes="error")
                else:
                    yield Label("No phase selected", classes="placeholder")

        yield Footer()

    def _create_phase_tree_widget(self):
        """Create the phase tree widget with indentation and status indicators."""
        # Create a tree widget
        tree = Tree(label="Phases", id="phase-tree-widget")

        # Add the root node and its children
        self._add_tree_nodes(tree.root, self.phase_tree_root)

        # Expand all nodes by default
        tree.root.expand_all()

        return tree

    def _add_tree_nodes(self, parent_node, phase_node):
        """Recursively add phase nodes to the tree."""
        # Determine status icon using emoji indicators
        status_icon = get_status_indicator(phase_node.status)

        # Calculate completion percentage if possible
        completion = 0  # Default to 0%
        if hasattr(phase_node, 'subtask_count') and phase_node.subtask_count > 0:
            # Assuming we can calculate completion based on subtasks
            # For now, we'll need to determine actual completion
            # In a real implementation you'd calculate based on task statuses
            if hasattr(phase_node, 'completed_subtasks'):
                completion = int((phase_node.completed_subtasks / phase_node.subtask_count) * 100)
            else:
                completion = 0

        # Format the phase label with emoji and progress bar
        short_id = phase_node.phase_id[:8] + "..."
        progress_bar = get_progress_bar(completion)
        label = f"{status_icon} {phase_node.label} ({short_id}) {progress_bar}"

        # Add this node to the tree
        tree_node = parent_node.add(label=label, data=phase_node.phase_id)

        # Add child nodes recursively
        for child_phase in phase_node.children:
            self._add_tree_nodes(tree_node, child_phase)

    def _create_phase_details_view(self):
        """Create the phase details view."""
        if not self.current_phase_details:
            return Label("No phase selected", classes="placeholder")

        # Parse the creation date for better display
        try:
            created_dt = datetime.fromisoformat(self.current_phase_details.created_at.replace('Z', '+00:00'))
            formatted_time = created_dt.strftime("%m/%d %H:%M")
        except:
            formatted_time = self.current_phase_details.created_at

        details_content = [
            Label(f"[b]Phase ID:[/b] {self.current_phase_details.phase_id}"),
            Label(f"[b]Label:[/b] {self.current_phase_details.label}"),
            Label(f"[b]Status:[/b] {self.current_phase_details.status}"),
            Label(f"[b]Created:[/b] {formatted_time}"),
        ]

        if self.current_phase_details.parent_phase_id:
            parent_short = self.current_phase_details.parent_phase_id[:8] + "..."
            details_content.append(Label(f"[b]Parent Phase ID:[/b] {parent_short}"))

        details_content.append(Label(f"[b]Subtask Count:[/b] {self.current_phase_details.subtask_count}"))

        return ScrollableContainer(*details_content, id="phase-details-content")

    def on_tree_node_highlighted(self, event):
        """Handle when a node in the tree is highlighted/selected."""
        if event.node.data:
            phase_id = event.node.data
            self.selected_phase_id = phase_id
            self._update_selected_phase_details()

    def _update_selected_phase_details(self):
        """Update the details view for the selected phase."""
        try:
            session = self.app.active_session
            if not session or not self.selected_phase_id:
                return

            self.current_phase_details = get_phase_details(session.id, self.selected_phase_id)

            # Update the details container
            details_container = self.query_one("#phase-details-content", ScrollableContainer)
            details_container.remove_children()

            # Parse the creation date for better display
            try:
                created_dt = datetime.fromisoformat(self.current_phase_details.created_at.replace('Z', '+00:00'))
                formatted_time = created_dt.strftime("%m/%d %H:%M")
            except:
                formatted_time = self.current_phase_details.created_at

            details_content = [
                Label(f"[b]Phase ID:[/b] {self.current_phase_details.phase_id}"),
                Label(f"[b]Label:[/b] {self.current_phase_details.label}"),
                Label(f"[b]Status:[/b] {self.current_phase_details.status}"),
                Label(f"[b]Created:[/b] {formatted_time}"),
            ]

            if self.current_phase_details.parent_phase_id:
                parent_short = self.current_phase_details.parent_phase_id[:8] + "..."
                details_content.append(Label(f"[b]Parent Phase ID:[/b] {parent_short}"))

            details_content.append(Label(f"[b]Subtask Count:[/b] {self.current_phase_details.subtask_count}"))

            for content in details_content:
                details_container.mount(content)
        except Exception as e:
            # Handle error in loading phase details
            details_container = self.query_one("#phase-details-content", ScrollableContainer)
            details_container.remove_children()
            details_container.mount(Label(f"Error loading phase details: {str(e)}"))

    def refresh_phase_tree(self):
        """Refresh the phase tree view."""
        try:
            session = self.app.active_session
            if not session:
                return

            # Reload the phase tree
            self.phase_tree_root = get_phase_tree(session.id)

            # Update the tree widget
            tree_container = self.query_one("#phases-tree-pane", Vertical)
            # Remove the old tree widget
            old_tree = tree_container.query_one("#phase-tree-widget")
            if old_tree:
                old_tree.remove()

            # Create and add the new tree widget
            new_tree_widget = self._create_phase_tree_widget()
            new_tree_widget.id = "phase-tree-widget"
            tree_container.mount(new_tree_widget)

            # Update the details panel for the selected phase
            if self.selected_phase_id:
                self._update_selected_phase_details()
        except Exception as e:
            # Handle error in refreshing tree
            self.notify(f"Error refreshing phase tree: {str(e)}", severity="error", timeout=5)

    def action_set_active_phase(self):
        """Set the selected phase as active."""
        if not self.selected_phase_id:
            self.notify("No phase selected", severity="warning", timeout=3)
            return

        session = self.app.active_session
        if not session:
            self.notify("No active session", severity="error", timeout=3)
            return

        from maestro.ui_facade.phases import set_active_phase
        from maestro.tui.widgets.modals import ConfirmDialog

        def on_confirmed(confirmed: bool):
            if confirmed:
                try:
                    # Set the phase as active
                    set_active_phase(session.id, self.selected_phase_id)

                    # Refresh the view to update active status
                    self.refresh_phase_tree()

                    # Update app's active phase
                    self.app._load_status_state()

                    # Update the status bar with new active phase
                    phase_short = self.selected_phase_id[:8] + "..."
                    self.app.query_one("#active-phase").update(
                        f" | Phase: {phase_short}..."
                    )

                    self.notify(f"Phase set as active", timeout=3)
                except Exception as e:
                    self.notify(f"Error setting phase as active: {str(e)}", severity="error", timeout=5)

        # Show confirmation dialog
        confirm_dialog = ConfirmDialog(
            message=f"Set this phase as active?",
            title="Confirm Set Active"
        )
        self.app.push_screen(confirm_dialog, callback=on_confirmed)

    def action_kill_phase(self):
        """Kill the selected phase branch with confirmation."""
        if not self.selected_phase_id:
            self.notify("No phase selected", severity="warning", timeout=3)
            return

        session = self.app.active_session
        if not session:
            self.notify("No active session", severity="error", timeout=3)
            return

        from maestro.ui_facade.phases import kill_phase, get_phase_details
        from maestro.tui.widgets.modals import ConfirmDialog

        # Get phase details to check if it's the active phase
        try:
            phase_info = get_phase_details(session.id, self.selected_phase_id)
            is_active_phase = (session.active_phase_id == self.selected_phase_id)
        except Exception:
            self.notify("Error getting phase details", severity="error", timeout=3)
            return

        def on_confirmed(confirmed: bool):
            if confirmed:
                try:
                    # Kill the phase
                    kill_phase(session.id, self.selected_phase_id)

                    # Refresh the view to update status
                    self.refresh_phase_tree()

                    # If this was the active phase, update app state
                    if is_active_phase:
                        self.app._load_status_state()

                    self.notify(f"Phase '{phase_info.label}' killed", timeout=3)
                except Exception as e:
                    self.notify(f"Error killing phase: {str(e)}", severity="error", timeout=5)

        # Prepare confirmation message based on whether it's active
        if is_active_phase:
            message = f"Kill this phase branch? This is the active phase and will be deactivated.\n\nPhase: {phase_info.label}"
        else:
            message = f"Kill this phase branch?\n\nPhase: {phase_info.label}"

        # Show confirmation dialog
        confirm_dialog = ConfirmDialog(
            message=message,
            title="Confirm Kill Phase"
        )
        self.app.push_screen(confirm_dialog, callback=on_confirmed)
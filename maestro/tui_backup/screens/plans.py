"""
Plans Screen for Maestro TUI - Interactive Plan Tree Viewer
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, ListView, ListItem, Tree
from textual.containers import Horizontal, Vertical, ScrollableContainer
from maestro.ui_facade.phases import get_phase_tree, list_phases, get_phase_details
from datetime import datetime


class PlansScreen(Screen):
    """Interactive Plan Tree Viewer screen with master-detail layout."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("enter", "set_active_plan", "Set Active"),
        ("k", "kill_plan", "Kill Branch"),
    ]

    def __init__(self):
        super().__init__()
        self.selected_plan_id = None
        self.plan_tree_root = None
        self.current_plan_details = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the plan tree viewer screen."""
        yield Header()

        # Master-detail layout - horizontal split
        with Horizontal(id="plans-main-container"):
            # Left pane - plan tree
            with Vertical(id="plans-tree-pane", classes="pane"):
                yield Label("[b]Plan Tree[/b]", classes="title")

                # Load and display the plan tree
                try:
                    session = self.app.active_session
                    if session:
                        self.plan_tree_root = get_phase_tree(session.id)
                        yield self._create_plan_tree_widget()
                    else:
                        yield Label("No active session available", classes="placeholder")
                except Exception as e:
                    yield Label(f"Error loading plan tree: {str(e)}", classes="error")

            # Right pane - plan details
            with Vertical(id="plan-details-pane", classes="pane"):
                yield Label("[b]Plan Details[/b]", classes="title")

                if self.plan_tree_root:
                    # Show details for the root plan by default
                    try:
                        session = self.app.active_session
                        if session:
                            # Use the root plan ID for details
                            self.selected_plan_id = self.plan_tree_root.plan_id
                            self.current_plan_details = get_plan_details(session.id, self.selected_plan_id)
                            yield self._create_plan_details_view()
                        else:
                            yield Label("No active session available", classes="placeholder")
                    except Exception as e:
                        yield Label(f"Error loading plan details: {str(e)}", classes="error")
                else:
                    yield Label("No plan selected", classes="placeholder")

        yield Footer()

    def _create_plan_tree_widget(self):
        """Create the plan tree widget with indentation and status indicators."""
        # Create a tree widget
        tree = Tree(label="Plans", id="plan-tree-widget")

        # Add the root node and its children
        self._add_tree_nodes(tree.root, self.plan_tree_root)

        # Expand all nodes by default
        tree.root.expand_all()

        return tree

    def _add_tree_nodes(self, parent_node, plan_node):
        """Recursively add plan nodes to the tree."""
        # Determine status icon
        if plan_node.status == "active":
            status_icon = "●"  # Active
        elif plan_node.status == "dead":
            status_icon = "×"  # Dead
        else:  # inactive
            status_icon = "○"  # Inactive

        # Format the plan label
        short_id = plan_node.plan_id[:8] + "..."
        label = f"{status_icon} {plan_node.label} ({short_id})"

        # Add this node to the tree
        tree_node = parent_node.add(label=label, data=plan_node.plan_id)

        # Add child nodes recursively
        for child_plan in plan_node.children:
            self._add_tree_nodes(tree_node, child_plan)

    def _create_plan_details_view(self):
        """Create the plan details view."""
        if not self.current_plan_details:
            return Label("No plan selected", classes="placeholder")

        # Parse the creation date for better display
        try:
            created_dt = datetime.fromisoformat(self.current_plan_details.created_at.replace('Z', '+00:00'))
            formatted_time = created_dt.strftime("%m/%d %H:%M")
        except:
            formatted_time = self.current_plan_details.created_at

        details_content = [
            Label(f"[b]Plan ID:[/b] {self.current_plan_details.plan_id}"),
            Label(f"[b]Label:[/b] {self.current_plan_details.label}"),
            Label(f"[b]Status:[/b] {self.current_plan_details.status}"),
            Label(f"[b]Created:[/b] {formatted_time}"),
        ]

        if self.current_plan_details.parent_plan_id:
            parent_short = self.current_plan_details.parent_plan_id[:8] + "..."
            details_content.append(Label(f"[b]Parent Plan ID:[/b] {parent_short}"))

        details_content.append(Label(f"[b]Subtask Count:[/b] {self.current_plan_details.subtask_count}"))

        return ScrollableContainer(*details_content, id="plan-details-content")

    def on_tree_node_highlighted(self, event):
        """Handle when a node in the tree is highlighted/selected."""
        if event.node.data:
            plan_id = event.node.data
            self.selected_plan_id = plan_id
            self._update_selected_plan_details()

    def _update_selected_plan_details(self):
        """Update the details view for the selected plan."""
        try:
            session = self.app.active_session
            if not session or not self.selected_plan_id:
                return

            self.current_plan_details = get_plan_details(session.id, self.selected_plan_id)

            # Update the details container
            details_container = self.query_one("#plan-details-content", ScrollableContainer)
            details_container.remove_children()

            # Parse the creation date for better display
            try:
                created_dt = datetime.fromisoformat(self.current_plan_details.created_at.replace('Z', '+00:00'))
                formatted_time = created_dt.strftime("%m/%d %H:%M")
            except:
                formatted_time = self.current_plan_details.created_at

            details_content = [
                Label(f"[b]Plan ID:[/b] {self.current_plan_details.plan_id}"),
                Label(f"[b]Label:[/b] {self.current_plan_details.label}"),
                Label(f"[b]Status:[/b] {self.current_plan_details.status}"),
                Label(f"[b]Created:[/b] {formatted_time}"),
            ]

            if self.current_plan_details.parent_plan_id:
                parent_short = self.current_plan_details.parent_plan_id[:8] + "..."
                details_content.append(Label(f"[b]Parent Plan ID:[/b] {parent_short}"))

            details_content.append(Label(f"[b]Subtask Count:[/b] {self.current_plan_details.subtask_count}"))

            for content in details_content:
                details_container.mount(content)
        except Exception as e:
            # Handle error in loading plan details
            details_container = self.query_one("#plan-details-content", ScrollableContainer)
            details_container.remove_children()
            details_container.mount(Label(f"Error loading plan details: {str(e)}"))

    def refresh_plan_tree(self):
        """Refresh the plan tree view."""
        try:
            session = self.app.active_session
            if not session:
                return

            # Reload the plan tree
            self.plan_tree_root = get_plan_tree(session.id)

            # Update the tree widget
            tree_container = self.query_one("#plans-tree-pane", Vertical)
            # Remove the old tree widget
            old_tree = tree_container.query_one("#plan-tree-widget")
            if old_tree:
                old_tree.remove()

            # Create and add the new tree widget
            new_tree_widget = self._create_plan_tree_widget()
            new_tree_widget.id = "plan-tree-widget"
            tree_container.mount(new_tree_widget)

            # Update the details panel for the selected plan
            if self.selected_plan_id:
                self._update_selected_plan_details()
        except Exception as e:
            # Handle error in refreshing tree
            self.notify(f"Error refreshing plan tree: {str(e)}", severity="error", timeout=5)

    def action_set_active_plan(self):
        """Set the selected plan as active."""
        if not self.selected_plan_id:
            self.notify("No plan selected", severity="warning", timeout=3)
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
                    set_active_phase(session.id, self.selected_plan_id)

                    # Refresh the view to update active status
                    self.refresh_plan_tree()

                    # Update app's active plan
                    self.app._load_status_state()

                    # Update the status bar with new active plan
                    plan_short = self.selected_plan_id[:8] + "..."
                    self.app.query_one("#active-plan").update(
                        f" | Plan: {plan_short}..."
                    )

                    self.notify(f"Phase set as active", timeout=3)
                except Exception as e:
                    self.notify(f"Error setting phase as active: {str(e)}", severity="error", timeout=5)

        # Show confirmation dialog
        confirm_dialog = ConfirmDialog(
            message=f"Set this plan as active?",
            title="Confirm Set Active"
        )
        self.app.push_screen(confirm_dialog, callback=on_confirmed)

    def action_kill_plan(self):
        """Kill the selected plan branch with confirmation."""
        if not self.selected_plan_id:
            self.notify("No plan selected", severity="warning", timeout=3)
            return

        session = self.app.active_session
        if not session:
            self.notify("No active session", severity="error", timeout=3)
            return

        from maestro.ui_facade.phases import kill_phase, get_phase_details
        from maestro.tui.widgets.modals import ConfirmDialog

        # Get plan details to check if it's the active plan
        try:
            plan_info = get_phase_details(session.id, self.selected_plan_id)
            is_active_plan = (session.active_plan_id == self.selected_plan_id)
        except Exception:
            self.notify("Error getting plan details", severity="error", timeout=3)
            return

        def on_confirmed(confirmed: bool):
            if confirmed:
                try:
                    # Kill the phase
                    kill_phase(session.id, self.selected_plan_id)

                    # Refresh the view to update status
                    self.refresh_plan_tree()

                    # If this was the active plan, update app state
                    if is_active_plan:
                        self.app._load_status_state()

                    self.notify(f"Phase '{plan_info.label}' killed", timeout=3)
                except Exception as e:
                    self.notify(f"Error killing phase: {str(e)}", severity="error", timeout=5)

        # Prepare confirmation message based on whether it's active
        if is_active_plan:
            message = f"Kill this phase branch? This is the active plan and will be deactivated.\n\nPhase: {plan_info.label}"
        else:
            message = f"Kill this phase branch?\n\nPhase: {plan_info.label}"

        # Show confirmation dialog
        confirm_dialog = ConfirmDialog(
            message=message,
            title="Confirm Kill Phase"
        )
        self.app.push_screen(confirm_dialog, callback=on_confirmed)
"""
Help Panel Widget for Maestro TUI

Provides collapsible contextual help for each screen
"""
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Button, Label
from textual.reactive import reactive
from textual import on
from typing import Dict, Optional


class HelpPanel(Vertical):
    """A collapsible help panel widget."""
    
    # Reactive property to track collapsed state
    collapsed = reactive(True)
    
    def __init__(self,
                 title: str = "Contextual Help",
                 help_content: str = "No help content provided",
                 screen_name: str = "",
                 id: str = None,
                 classes: str = ""):
        super().__init__(id=id, classes=classes)
        self.title = title
        self.help_content = help_content
        self.screen_name = screen_name
        
    def compose(self) -> ComposeResult:
        """Create child widgets for the help panel."""
        # Toggle button with arrow indicating state
        arrow = "▶" if self.collapsed else "▼"
        yield Horizontal(
            Label(f"{arrow} {self.title}", id="help-panel-title"),
            Button("Hide", variant="default", id="toggle-help", classes="toggle-button"),
            id="help-panel-header"
        )
        
        # Help content container (visible only when expanded)
        with Vertical(id="help-panel-content", classes="help-content" + (" hidden" if self.collapsed else "")):
            yield Static(self.help_content, id="help-text")
    
    def on_mount(self) -> None:
        """Set up initial state."""
        self._update_visibility()
    
    def toggle_collapsed(self) -> None:
        """Toggle the collapsed state."""
        self.collapsed = not self.collapsed
        self._update_visibility()
        
    def _update_visibility(self) -> None:
        """Update the UI based on collapsed state."""
        # Update the toggle button text
        toggle_button = self.query_one("#toggle-help", Button)
        toggle_button.label = "Show" if self.collapsed else "Hide"
        
        # Update the arrow in the title
        arrow = "▶" if self.collapsed else "▼"
        title_label = self.query_one("#help-panel-title", Label)
        title_label.update(f"{arrow} {self.title}")
        
        # Update content visibility
        content_container = self.query_one("#help-panel-content", Vertical)
        if self.collapsed:
            content_container.add_class("hidden")
        else:
            content_container.remove_class("hidden")
    
    @on(Button.Pressed, "#toggle-help")
    def on_toggle_button_pressed(self, event: Button.Pressed) -> None:
        """Handle toggle button press."""
        self.toggle_collapsed()


class ScreenSpecificHelpData:
    """Provides screen-specific help content."""
    
    @staticmethod
    def get_help_content(screen_name: str) -> str:
        """Get help content for a specific screen."""
        help_texts = {
            "home": """**Home Dashboard**

This is the main dashboard showing an overview of your session status.

**What this screen is for:**
- Provides a quick overview of your current session
- Shows active phase and build target
- Displays key metrics and status indicators

**Common actions:**
- Navigate to other screens using the left sidebar
- Press `r` to refresh status information
- Check active session, phase, and build target status

**Safe vs Dangerous:**
- All actions here are read-only
- No destructive operations possible""",
            
            "sessions": """**Sessions Management**

Manage multiple work sessions that maintain state across runs.

**What this screen is for:**
- Create new sessions for different projects
- Switch between active sessions
- View session history and status

**Common actions:**
- List existing sessions
- Create new sessions
- Set active session
- Remove old sessions

**Safe vs Dangerous:**
- Creating sessions is safe
- Removing sessions is irreversible and will delete all associated data
- Setting active session is safe and reversible

**What NOT to do accidentally:**
- Don't remove sessions with important work""",
            
            "phases": """**Phases Visualization**

Interactive view of the phase tree with branching and subtasks.

**What this screen is for:**
- Visualize the phase hierarchy and branches
- Set active phase for current work
- Kill/terminate phase branches

**Visual Indicators:**
- ✅ Done phases
- 🚧 In-progress phases
- 📋 Planned phases
- 💡 Proposed phases
- Progress bars show completion percentage

**Common actions:**
- Browse phase tree structure
- Set active phase (enter key on phase)
- Kill phase branch (k key on phase)

**Safe vs Dangerous:**
- Browsing phase tree is safe
- Setting active phase is safe and reversible
- Killing a phase branch is irreversible and will terminate all subtasks

**What NOT to do accidentally:**
- Don't kill the active phase without confirming it's the right one""",

            "plans": """**Plans Overview**

Manage planning artifacts and discussion outputs before they become tasks.

**What this screen is for:**
- Review existing plans and their status
- Inspect plan details and assumptions
- Decide which plans to keep or discard

**Common actions:**
- List plans
- Show plan details
- Remove outdated plans

**Safe vs Dangerous:**
- Viewing plan details is safe
- Removing plans is irreversible and will delete plan content""",

            "tasks": """**Tasks Management**

Manage individual tasks within the active phase.

**What this screen is for:**
- View and manage individual tasks
- Start/stop task execution
- Monitor task status and progress

**Visual Indicators:**
- ✅ Done tasks
- 🚧 In-progress tasks
- 📋 Planned tasks
- 💡 Proposed tasks
- P0 tasks shown in red (critical)
- P1 tasks shown in yellow (high priority)
- P2 tasks in normal text (normal priority)

**Common actions:**
- Start all tasks
- Resume interrupted tasks
- Stop current execution
- View task details

**Safe vs Dangerous:**
- Viewing and monitoring tasks is safe
- Stopping execution may interrupt work
- Resuming tasks is safe""",
            
            "build": """**Build Targets**

Configure and execute build operations for your project.

**What this screen is for:**
- Manage build targets and configurations
- Execute builds and monitor status
- Run fix loops to resolve build issues

**Common actions:**
- Set active build target
- Run builds
- Run fix loops
- Check build status

**Safe vs Dangerous:**
- Checking status is safe
- Running builds may modify project files
- Running fix loops may make significant changes to code""",
            
            "convert": """**Format Conversion**

Convert and transform project files between formats.

**What this screen is for:**
- Rehearse and promote format conversions
- Manage conversion checkpoints
- Monitor conversion progress

**Common actions:**
- Start conversion run
- Rehearse conversion (dry run)
- Approve/reject checkpoints
- Promote conversion to production

**Safe vs Dangerous:**
- Rehearsing conversion is safe (dry run)
- Approving checkpoints commits changes
- Promoting conversion makes permanent changes

**What NOT to do accidentally:**
- Don't approve checkpoints without reviewing changes""",
            
            "replay": """**Replay System**

Replay and compare previous runs with baselines.

**What this screen is for:**
- Replay previous runs for verification
- Compare runs against baselines
- Manage baseline versions

**Common actions:**
- List all runs
- Show run details
- Replay runs (dry or apply)
- Set run as baseline

**Safe vs Dangerous:**
- Showing run details is safe
- Replay dry run is safe
- Replay with apply makes changes
- Setting baseline affects future comparisons""",
            
            "arbitration": """**Arbitration Arena**

Compare and select between different implementation approaches.

**What this screen is for:**
- Compare multiple implementations
- Select the best solution
- Review arbitration decisions

**Common actions:**
- List arbitrated tasks
- Show arbitration details
- Choose winner
- Explain arbitration decision

**Safe vs Dangerous:**
- Reviewing arbitration is safe
- Choosing a winner commits to that implementation
- This decision affects which code changes are kept""",
            
            "semantic": """**Semantic Integrity**

Monitor semantic correctness and prevent breaking changes.

**What this screen is for:**
- Track semantic findings and violations
- Accept/reject semantic changes
- Monitor for breaking changes

**Common actions:**
- List semantic findings
- Show finding details
- Accept/reject findings
- Defer handling of findings

**Safe vs Dangerous:**
- Reviewing findings is safe
- Accepting findings marks them as resolved
- Rejecting may block pipeline progress""",
            
            "memory": """**Memory System**

Access and manage stored knowledge and decisions.

**What this screen is for:**
- Browse stored decisions and conventions
- Access project knowledge base
- Manage memory entries

**Common actions:**
- Show decision types (conventions, issues, summaries)
- Search memory entries
- Override decisions
- Show specific decision details""",
            
            "logs": """**System Logs**

View detailed logs for debugging and monitoring.

**What this screen is for:**
- Monitor system activity
- Debug issues with operations
- Track system behavior

**Common actions:**
- Filter logs by type
- Search log content
- Export logs for analysis

**Safe vs Dangerous:**
- All actions here are read-only
- No destructive operations possible""",
            
            "confidence": """**Confidence Scoreboard**

Track confidence metrics and quality gates.

**What this screen is for:**
- Monitor confidence scores across components
- View quality gate status
- Track confidence evolution over time

**Common actions:**
- Show overall confidence
- Show confidence for specific runs
- Show confidence gates and thresholds
- Explain confidence components""",
            
            "vault": """**Artifacts Vault**

Browse and manage stored logs, diffs, and artifacts.

**What this screen is for:**
- Browse stored artifacts and logs
- Search through historical data
- Export artifacts for analysis

**Common actions:**
- Browse different artifact types (logs, diffs, snapshots)
- Search vault contents
- Export items
- View artifact details

**Safe vs Dangerous:**
- Browsing is safe
- Exporting is safe
- Some operations may access large amounts of data""",
        }
        
        return help_texts.get(screen_name, """**Help Unavailable**

No specific help content is available for this screen.

**General Information:**
- Press `?` for general help
- Use `Ctrl+P` to open command palette
- Navigation keys: arrow keys, enter, escape
- Press `q` or `Ctrl+C` to quit""")

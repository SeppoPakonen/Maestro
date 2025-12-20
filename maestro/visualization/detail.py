"""
Detail view formatter for comprehensive session information.
"""
from typing import List, Dict, Any
from datetime import datetime
from ..work_session import WorkSession
from ..breadcrumb import Breadcrumb
from ..stats.session_stats import SessionStats, calculate_session_stats


class SessionDetailFormatter:
    """Format detailed session information."""

    def __init__(self):
        pass

    def format_details(
        self,
        session: WorkSession,
        include_breadcrumbs: bool = True,
        include_children: bool = True,
        show_all_breadcrumbs: bool = False
    ) -> str:
        """Format comprehensive session details."""
        lines = []
        
        # Header
        header_line = "═" * 80
        lines.extend([
            header_line,
            f"Session: {session.session_id}",
            header_line,
            ""
        ])

        # Basic Information
        lines.append("Basic Information:")
        lines.extend([
            f"  Type:           {session.session_type}",
            f"  Status:         {session.status}",
            f"  Created:        {session.created}",
            f"  Modified:       {session.modified}",
        ])

        # Calculate duration
        try:
            created_dt = datetime.fromisoformat(session.created.replace('Z', '+00:00'))
            modified_dt = datetime.fromisoformat(session.modified.replace('Z', '+00:00'))
            duration = modified_dt - created_dt
            duration_str = str(duration)
            lines.append(f"  Duration:       {duration_str}")
        except ValueError:
            lines.append("  Duration:       Could not calculate")
        
        lines.append("")

        # Related Entity
        if session.related_entity:
            lines.append("Related Entity:")
            for key, value in session.related_entity.items():
                lines.append(f"  {key.replace('_', ' ').title()}: {value}")
            lines.append("")

        # Parent Session
        if session.parent_session_id:
            lines.append("Parent Session:")
            lines.append(f"  ID:             {session.parent_session_id}")
            # Note: We don't fetch parent session details here to avoid circular dependencies
            lines.append("  (Details available with: maestro wsession show <parent-id>)")
            lines.append("")
        
        # Include children info
        if include_children:
            # To get children, we need to look in the file system for sessions with this as parent
            # This would require calling the work_session functions, but let's defer that for now
            # as we may have issues with circular imports
            lines.append("Child Sessions: (To be implemented based on filesystem check)")
            lines.append("")

        # Breadcrumbs
        if include_breadcrumbs:
            lines.append("Breadcrumbs:")
            from ..breadcrumb import list_breadcrumbs
            try:
                breadcrumbs = list_breadcrumbs(session.session_id)
                lines.append(f"  Total: {len(breadcrumbs)}")
                
                if breadcrumbs:
                    lines.append("  Latest:")
                    # Show only the most recent breadcrumbs unless requested to show all
                    breadcrumbs_to_show = breadcrumbs if show_all_breadcrumbs else breadcrumbs[-3:]
                    for breadcrumb in reversed(breadcrumbs_to_show):
                        timestamp = breadcrumb.timestamp[:15]  # First 15 chars for date/time
                        timestamp_formatted = f"{timestamp[:8]} {timestamp[9:11]}:{timestamp[11:13]}:{timestamp[13:15]}"
                        lines.append(f"    - {timestamp_formatted} - {breadcrumb.model_used} ({breadcrumb.token_count.get('input', 0) + breadcrumb.token_count.get('output', 0)} tokens)")
            except Exception as e:
                lines.append(f"  Error loading breadcrumbs: {str(e)}")
            lines.append("")

        # Statistics
        try:
            stats = calculate_session_stats(session)
            lines.append("Statistics:")
            lines.extend([
                f"  Total breadcrumbs:     {stats.total_breadcrumbs}",
                f"  Total tokens:          {stats.total_tokens_input + stats.total_tokens_output:,} (input: {stats.total_tokens_input:,}, output: {stats.total_tokens_output:,})",
                f"  Estimated cost:        ${stats.estimated_cost:.2f}",
                f"  Files modified:        {stats.files_modified}",
                f"  Tools called:          {stats.tools_called}",
                f"  Duration (seconds):    {int(stats.duration_seconds)}",
                f"  Success rate:          {stats.success_rate:.1f}%"
            ])
        except Exception as e:
            lines.append(f"  Statistics error: {str(e)}")
        
        return "\n".join(lines)

    def format_breadcrumb_summary(self, breadcrumbs: List[Breadcrumb]) -> str:
        """Format breadcrumb summary."""
        if not breadcrumbs:
            return "No breadcrumbs to summarize."
        
        lines = [f"Breadcrumb Summary ({len(breadcrumbs)} total):"]
        
        total_input_tokens = sum(b.token_count.get('input', 0) for b in breadcrumbs)
        total_output_tokens = sum(b.token_count.get('output', 0) for b in breadcrumbs)
        total_cost = sum(b.cost or 0 for b in breadcrumbs)
        
        lines.extend([
            f"  Tokens: Input: {total_input_tokens:,}, Output: {total_output_tokens:,}",
            f"  Estimated Cost: ${total_cost:.2f}",
            f"  Files Modified: {sum(len(b.files_modified) for b in breadcrumbs)}",
            f"  Tools Called: {sum(len(b.tools_called) for b in breadcrumbs)}"
        ])
        
        return "\n".join(lines)

    def format_statistics(self, session: WorkSession) -> str:
        """Format session statistics."""
        try:
            stats = calculate_session_stats(session)
            return f"""
Statistics for {session.session_id}:
  Total Breadcrumbs: {stats.total_breadcrumbs}
  Tokens (Input/Output): {stats.total_tokens_input:,} / {stats.total_tokens_output:,}
  Estimated Cost: ${stats.estimated_cost:.2f}
  Files Modified: {stats.files_modified}
  Tools Called: {stats.tools_called}
  Duration (seconds): {int(stats.duration_seconds)}
  Success Rate: {stats.success_rate:.1f}%
            """.strip()
        except Exception as e:
            return f"Error calculating statistics: {str(e)}"
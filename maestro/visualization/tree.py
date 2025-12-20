"""
Tree renderer for session hierarchy visualization.
"""
from typing import Dict, Any, List
from ..work_session import WorkSession


class SessionTreeRenderer:
    """Render session hierarchy as ASCII tree."""

    def __init__(self, color: bool = True):
        self.color = color
        self.status_emoji = {
            "running": "🔄",
            "paused": "⏸️",
            "completed": "✅",
            "failed": "❌",
            "interrupted": "⏹️"
        }
        self.status_colors = {
            "running": "green",
            "paused": "yellow", 
            "completed": "blue",
            "failed": "red",
            "interrupted": "gray"
        }

    def render(self, tree: Dict[str, Any], depth: int = 0, max_depth: int = None) -> str:
        """Render tree structure."""
        output = []
        
        # If this is the root, process all root sessions
        if "root" in tree:
            output.append("📊 Work Sessions")
            output.append("│")
            for i, root_node in enumerate(tree["root"]):
                is_last = i == len(tree["root"]) - 1
                output.append(self._render_node_recursive(root_node, is_last, "", max_depth))
        else:
            # This is part of a recursive call, just render this node
            output.append(self._render_node_recursive(tree, True, "", max_depth))
        
        return "\n".join(output)

    def _render_node_recursive(self, node: Dict[str, Any], is_last: bool, prefix: str, max_depth: int = None, current_depth: int = 0) -> str:
        """Recursively render tree node."""
        if max_depth is not None and current_depth > max_depth:
            return ""
            
        session = node["session"]
        children = node.get("children", [])
        
        # Determine the connector to use
        connector = "└─ " if is_last else "├─ "
        
        # Get status emoji and potentially color
        status_emoji = self.status_emoji.get(session.status, "?")
        
        # Build the main node line
        node_info = f"{status_emoji} {session.session_id} ({session.session_type}: {session.related_entity.get('name', 'unnamed')}) [{session.status}]"
        
        # Start the line with prefix and connector
        line = f"{prefix}{connector}{node_info}"
        
        if current_depth == 0:
            # For top-level items, no extra indentation before the child level
            child_prefix = prefix + ("    " if is_last else "│   ")
        else:
            child_prefix = prefix + ("    " if is_last else "│   ")
        
        # Process children if any
        result_lines = [line]
        for i, child in enumerate(children):
            is_child_last = i == len(children) - 1
            child_str = self._render_node_recursive(child, is_child_last, child_prefix, max_depth, current_depth + 1)
            if child_str:  # Only add if not empty (due to depth limit)
                result_lines.append(child_str)
        
        return "\n".join(result_lines)

    def _colorize(self, text: str, color: str) -> str:
        """Apply color if enabled."""
        if not self.color:
            return text
            
        # This is a simplified colorization that would work with a real color library
        # For now, we'll just return the text as is
        return text
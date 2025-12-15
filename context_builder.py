"""
Context Builder with Compression for Conversion Memory

Implements context compression with hard limits to prevent context rot
and ensure deterministic context size for AI tasks.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from conversion_memory import ConversionMemory


class ContextBuilder:
    """Builds compressed context for AI tasks with hard size limits."""
    
    def __init__(self, memory: ConversionMemory, 
                 planner_context_limit: int = 12 * 1024,  # 12KB
                 worker_context_limit: int = 8 * 1024):   # 8KB
        self.memory = memory
        self.planner_context_limit = planner_context_limit
        self.worker_context_limit = worker_context_limit
    
    def build_context_for_planner(self, max_summary_entries: int = 10) -> str:
        """Build compressed context for planner AI with size limits."""
        context_parts = []
        
        # Always include relevant decisions
        decisions = self.memory.load_decisions()
        if decisions:
            decisions_context = self._format_decisions_context(decisions)
            context_parts.append(decisions_context)
        
        # Include relevant conventions
        conventions = self.memory.load_conventions()
        if conventions:
            conventions_context = self._format_conventions_context(conventions)
            context_parts.append(conventions_context)
        
        # Include glossary entries
        glossary = self.memory.load_glossary()
        if glossary:
            glossary_context = self._format_glossary_context(glossary)
            context_parts.append(glossary_context)
        
        # Include recent summary entries (chronological)
        recent_summaries = self.memory.load_summary_log()[-max_summary_entries:]  # Get last N entries
        if recent_summaries:
            summaries_context = self._format_summaries_context(recent_summaries)
            context_parts.append(summaries_context)
        
        # Include open issues that might affect planning
        open_issues = self.memory.load_open_issues()
        open_issues = [issue for issue in open_issues if issue.get('status') in ['open', 'investigating']]
        if open_issues:
            issues_context = self._format_issues_context(open_issues)
            context_parts.append(issues_context)
        
        # Join all parts and enforce size limit
        full_context = "\n\n".join(context_parts)
        
        # Compress if too large
        compressed_context = self._enforce_size_limit(full_context, self.planner_context_limit, "planner")
        
        return compressed_context
    
    def build_context_for_worker(self, task_id: str, max_dependency_summaries: int = 5) -> str:
        """Build compressed context for worker AI with size limits."""
        context_parts = []
        
        # Always include relevant decisions
        decisions = self.memory.load_decisions()
        if decisions:
            decisions_context = self._format_decisions_context(decisions)
            context_parts.append(decisions_context)
        
        # Include relevant conventions
        conventions = self.memory.load_conventions()
        if conventions:
            conventions_context = self._format_conventions_context(conventions)
            context_parts.append(conventions_context)
        
        # Include glossary entries relevant to this task
        glossary = self.memory.load_glossary()
        if glossary:
            glossary_context = self._format_glossary_context(glossary)
            context_parts.append(glossary_context)
        
        # Include summaries of direct dependencies and recent relevant work
        # For now, we'll include recent summaries related to dependencies
        summary_log = self.memory.load_summary_log()
        
        # Find summaries related to this task's dependencies (if any in plan)
        # This would require access to the plan to identify dependencies
        # For now, we'll include recent summaries
        recent_summaries = summary_log[-max_dependency_summaries:]
        if recent_summaries:
            summaries_context = self._format_summaries_context(recent_summaries)
            context_parts.append(summaries_context)
        
        # Include open issues that might affect this specific task
        open_issues = self.memory.load_open_issues()
        # Filter for issues related to this task
        task_related_issues = [issue for issue in open_issues 
                              if issue.get('status') in ['open', 'investigating'] 
                              and task_id in issue.get('related_tasks', [])]
        
        if task_related_issues:
            issues_context = self._format_issues_context(task_related_issues)
            context_parts.append(issues_context)
        
        # Join all parts and enforce size limit
        full_context = "\n\n".join(context_parts)
        
        # Compress if too large
        compressed_context = self._enforce_size_limit(full_context, self.worker_context_limit, "worker")
        
        return compressed_context
    
    def _format_decisions_context(self, decisions: List[Dict]) -> str:
        """Format decisions for context."""
        if not decisions:
            return ""
        
        formatted = ["## RELEVANT DECISIONS", ""]
        for decision in decisions:
            formatted.append(f"- {decision.get('description', '')}: {decision.get('value', '')}")
            formatted.append(f"  Justification: {decision.get('justification', '')}")
        
        return "\n".join(formatted)
    
    def _format_conventions_context(self, conventions: List[Dict]) -> str:
        """Format conventions for context."""
        if not conventions:
            return ""
        
        formatted = ["## ESTABLISHED CONVENTIONS", ""]
        for convention in conventions:
            formatted.append(f"- {convention.get('rule', '')}")
            formatted.append(f"  Applies to: {convention.get('applies_to', '')}")
        
        return "\n".join(formatted)
    
    def _format_glossary_context(self, glossary: List[Dict]) -> str:
        """Format glossary entries for context."""
        if not glossary:
            return ""
        
        formatted = ["## CONCEPT MAPPINGS", ""]
        for entry in glossary:
            formatted.append(f"- {entry.get('source_term', '')} → {entry.get('target_term', '')}")
            formatted.append(f"  Definition: {entry.get('definition', '')}")
        
        return "\n".join(formatted)
    
    def _format_summaries_context(self, summaries: List[Dict]) -> str:
        """Format summary entries for context."""
        if not summaries:
            return ""
        
        formatted = ["## RECENT TASK SUMMARIES", ""]
        for summary in summaries:
            formatted.append(f"- Task {summary.get('task_id', '')} ({summary.get('timestamp', '')}): {summary.get('summary', '')}")
        
        return "\n".join(formatted)
    
    def _format_issues_context(self, issues: List[Dict]) -> str:
        """Format open issues for context."""
        if not issues:
            return ""
        
        formatted = ["## OPEN ISSUES", ""]
        for issue in issues:
            formatted.append(f"- {issue.get('description', '')}")
            formatted.append(f"  Severity: {issue.get('severity', '')}, Status: {issue.get('status', '')}")
            if issue.get('related_tasks'):
                formatted.append(f"  Related tasks: {', '.join(issue.get('related_tasks', []))}")
        
        return "\n".join(formatted)
    
    def _enforce_size_limit(self, context: str, limit: int, context_type: str) -> str:
        """Enforce size limit on context with intelligent truncation."""
        if len(context.encode('utf-8')) <= limit:
            return context
        
        # If it exceeds the limit, we have several options:
        # 1. Fail with clear error (as required)
        # 2. Truncate intelligently (not allowed per requirements)
        
        # According to the requirements: "If context exceeds limits: fail with a clear error"
        raise ContextSizeExceededException(
            f"{context_type.capitalize()} context size ({len(context.encode('utf-8'))} bytes) "
            f"exceeds limit ({limit} bytes). Context needs to be refined to fit within limits."
        )
    
    def get_context_info(self) -> Dict[str, Any]:
        """Get information about the current context size and composition."""
        decisions = self.memory.load_decisions()
        conventions = self.memory.load_conventions()
        glossary = self.memory.load_glossary()
        summaries = self.memory.load_summary_log()
        open_issues = self.memory.load_open_issues()
        
        context_info = {
            "decisions_count": len(decisions),
            "conventions_count": len(conventions),
            "glossary_count": len(glossary),
            "summaries_count": len(summaries),
            "open_issues_count": len(open_issues),
            "estimated_planner_size": len(self._build_raw_context(decisions, conventions, glossary, summaries, open_issues).encode('utf-8')),
            "planner_limit": self.planner_context_limit,
            "estimated_worker_size": len(self._build_raw_context(decisions, conventions, glossary, summaries[:5], open_issues).encode('utf-8')),  # Using last 5 summaries
            "worker_limit": self.worker_context_limit
        }
        
        return context_info
    
    def _build_raw_context(self, decisions: List[Dict], conventions: List[Dict], 
                          glossary: List[Dict], summaries: List[Dict], issues: List[Dict]) -> str:
        """Build raw context string for size estimation."""
        context_parts = []
        
        if decisions:
            decisions_context = self._format_decisions_context(decisions)
            context_parts.append(decisions_context)
        
        if conventions:
            conventions_context = self._format_conventions_context(conventions)
            context_parts.append(conventions_context)
        
        if glossary:
            glossary_context = self._format_glossary_context(glossary)
            context_parts.append(glossary_context)
        
        if summaries:
            summaries_context = self._format_summaries_context(summaries)
            context_parts.append(summaries_context)
        
        if issues:
            issues_context = self._format_issues_context(issues)
            context_parts.append(issues_context)
        
        return "\n\n".join(context_parts)


class ContextSizeExceededException(Exception):
    """Exception raised when context size exceeds the hard limits."""
    pass